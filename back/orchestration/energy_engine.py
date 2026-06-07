"""
praxis/orchestration/energy_engine.py

Cognitive energy tracker — suggests breaks based on real fatigue signals.

Unlike a simple timer, this system measures COGNITIVE LOAD:
  - Error density (errors per recent window)
  - Latency increase (response time trending up = mental fatigue)
  - Time elapsed (baseline depletion)
  - Difficulty of items (hard items drain more than easy ones)

Energy is 0-100. The system suggests a break at 20, and gently
insists at 10. It never BLOCKS — the learner can always continue.

The key insight: a learner flying through easy items at 8 minutes
has plenty of energy. A learner struggling through hard items at
5 minutes may already be depleted.

Usage:
    from praxis.orchestration.energy_engine import EnergyEngine, EnergyState

    engine = EnergyEngine()
    state = engine.new_session()

    # After each item:
    state = engine.record_item(state, correct=True, latency_ms=4500, difficulty=0.3)
    # state.energy → 82
    # state.should_suggest_break → False
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


# ──────────────────────────────────────────────────────────────
# Types
# ──────────────────────────────────────────────────────────────

@dataclass
class EnergyState:
    """Mutable energy state for one session."""
    energy: float = 100.0         # 0-100
    items_completed: int = 0
    errors_recent: int = 0        # errors in last WINDOW_SIZE items
    total_errors: int = 0
    session_start: float = 0.0    # timestamp

    # Latency tracking
    latencies: list[float] = field(default_factory=list)  # last N response times in ms
    baseline_latency: float = 0.0  # average of first 3 items (calibration)

    # Status
    break_suggested: bool = False
    break_insisted: bool = False

    @property
    def should_suggest_break(self) -> bool:
        return self.energy <= 20

    @property
    def should_insist_break(self) -> bool:
        return self.energy <= 10

    @property
    def elapsed_minutes(self) -> float:
        if self.session_start == 0:
            return 0.0
        return (time.time() - self.session_start) / 60.0

    def to_dict(self) -> dict:
        return {
            "energy": round(self.energy, 1),
            "items_completed": self.items_completed,
            "errors_recent": self.errors_recent,
            "total_errors": self.total_errors,
            "elapsed_minutes": round(self.elapsed_minutes, 1),
            "should_suggest_break": self.should_suggest_break,
            "should_insist_break": self.should_insist_break,
            "break_suggested": self.break_suggested,
        }


# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────

# Base depletion per item (difficulty-weighted)
BASE_DRAIN_PER_ITEM = 5.0           # easy item at perfect performance
DIFFICULTY_MULTIPLIER = 8.0          # additional drain for hard items (0-1 scale)

# Error penalty: each error in the recent window drains extra
ERROR_DRAIN = 6.0

# Latency increase penalty: if current latency is >N% above baseline, drain extra
LATENCY_THRESHOLD_RATIO = 1.4       # 40% slower than baseline = fatigue signal
LATENCY_DRAIN = 4.0                 # extra drain when latency threshold is hit

# Time-based baseline drain (per minute)
TIME_DRAIN_PER_MINUTE = 1.5

# Recovery: correct answers give a small energy bump
CORRECT_RECOVERY = 2.0
STREAK_RECOVERY_BONUS = 1.0         # additional per consecutive correct

# Window size for recent error tracking
ERROR_WINDOW = 5

# Calibration: use first N items to establish baseline latency
CALIBRATION_ITEMS = 3


# ──────────────────────────────────────────────────────────────
# Engine
# ──────────────────────────────────────────────────────────────

class EnergyEngine:
    """Computes cognitive energy depletion from behavioral signals."""

    def new_session(self) -> EnergyState:
        return EnergyState(
            energy=100.0,
            session_start=time.time(),
        )

    def record_item(
        self,
        state: EnergyState,
        correct: bool,
        latency_ms: float = 0.0,
        difficulty: float = 0.5,       # 0-1 normalized difficulty
        consecutive_correct: int = 0,
    ) -> EnergyState:
        """Update energy after a learner completes an item.

        Args:
            state: Current energy state
            correct: Whether the answer was correct
            latency_ms: Time from question presentation to answer (ms)
            difficulty: Normalized difficulty 0-1
            consecutive_correct: Current correct streak (for recovery bonus)

        Returns:
            Updated EnergyState
        """
        state.items_completed += 1

        # ── Track latency ─────────────────────────────────────
        if latency_ms > 0:
            state.latencies.append(latency_ms)
            # Keep last 10 for trend analysis
            if len(state.latencies) > 10:
                state.latencies = state.latencies[-10:]

            # Calibrate baseline from first N items
            if state.items_completed <= CALIBRATION_ITEMS:
                state.baseline_latency = (
                    sum(state.latencies) / len(state.latencies)
                )

        # ── Track errors ──────────────────────────────────────
        if not correct:
            state.total_errors += 1
            state.errors_recent += 1
        # Decay recent errors (sliding window)
        if state.items_completed > ERROR_WINDOW:
            # Approximate: reduce by 1 every WINDOW_SIZE items
            # (In production, track a proper ring buffer)
            state.errors_recent = max(0, state.errors_recent - (1 if correct else 0))

        # ── Compute drains ────────────────────────────────────

        # 1. Base drain (difficulty-weighted)
        drain = BASE_DRAIN_PER_ITEM + (difficulty * DIFFICULTY_MULTIPLIER)

        # 2. Error density penalty
        if state.errors_recent >= 2:
            drain += ERROR_DRAIN * (state.errors_recent / ERROR_WINDOW)

        # 3. Latency increase penalty
        if (
            state.baseline_latency > 0
            and latency_ms > 0
            and len(state.latencies) >= CALIBRATION_ITEMS
        ):
            recent_avg = sum(state.latencies[-3:]) / min(len(state.latencies[-3:]), 3)
            if recent_avg > state.baseline_latency * LATENCY_THRESHOLD_RATIO:
                ratio = recent_avg / state.baseline_latency
                drain += LATENCY_DRAIN * min(ratio - 1.0, 2.0)  # cap at 2x

        # 4. Time-based drain
        drain += TIME_DRAIN_PER_MINUTE * max(0, state.elapsed_minutes - 2)  # grace period of 2 min

        # ── Compute recovery ──────────────────────────────────
        recovery = 0.0
        if correct:
            recovery = CORRECT_RECOVERY
            if consecutive_correct >= 3:
                recovery += STREAK_RECOVERY_BONUS

        # ── Apply ─────────────────────────────────────────────
        state.energy = max(0.0, min(100.0, state.energy - drain + recovery))

        # ── Update break suggestions ─────────────────────────
        if state.should_suggest_break and not state.break_suggested:
            state.break_suggested = True
        if state.should_insist_break:
            state.break_insisted = True

        return state

    def take_break(self, state: EnergyState, break_seconds: int = 60) -> EnergyState:
        """Restore some energy when the learner takes a break.

        Short breaks (30-60s) give moderate recovery.
        Longer breaks (2-5 min) give more.
        """
        recovery = min(30.0, break_seconds / 4.0)  # max 30 energy from a break
        state.energy = min(100.0, state.energy + recovery)
        state.break_suggested = False
        state.break_insisted = False
        state.errors_recent = max(0, state.errors_recent - 1)  # slight error window reset
        return state

    def get_session_summary(self, state: EnergyState) -> dict:
        """Summary for end-of-session display."""
        elapsed = state.elapsed_minutes
        accuracy = (
            (state.items_completed - state.total_errors) / max(state.items_completed, 1)
        )

        # Latency trend
        latency_trend = "stable"
        if len(state.latencies) >= 5 and state.baseline_latency > 0:
            recent = sum(state.latencies[-3:]) / 3
            if recent > state.baseline_latency * 1.3:
                latency_trend = "increasing"
            elif recent < state.baseline_latency * 0.8:
                latency_trend = "decreasing"

        return {
            "items_completed": state.items_completed,
            "accuracy": round(accuracy, 3),
            "total_errors": state.total_errors,
            "elapsed_minutes": round(elapsed, 1),
            "final_energy": round(state.energy, 1),
            "latency_trend": latency_trend,
            "breaks_taken": 1 if state.break_suggested and state.energy > 20 else 0,
        }
