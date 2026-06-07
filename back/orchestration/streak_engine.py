"""
praxis/orchestration/streak_engine.py

Streak tracking with shields and recovery.

Unlike the Duolingo cliff-edge streak, this system:
  - Auto-activates a shield on the first missed day (no manual action)
  - Allows recovery within a configurable window (default 48h)
  - Earns shields by doing extra sessions (banking momentum)
  - Never guilt-trips. Messaging is always forward-looking.
  - Tracks "longest streak" separately so progress is never truly lost.

Streak milestones unlock real benefits:
  - 7 days  → first streak shield earned
  - 14 days → fire animation upgrade
  - 30 days → achievement badge + second shield slot
  - 60 days → badge + priority access to new content
  - 100 days → permanent badge

Usage:
    from praxis.orchestration.streak_engine import StreakEngine, StreakState

    engine = StreakEngine()
    state = await engine.check_in(learner_id="abc123")
    # state.current_streak → 12
    # state.shields_available → 1
    # state.status → "active"
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from db.client import db


# ──────────────────────────────────────────────────────────────
# Types
# ──────────────────────────────────────────────────────────────

class StreakStatus(str, Enum):
    ACTIVE = "active"                # streak is alive, session done today
    PENDING = "pending"              # streak alive, no session today yet
    SHIELDED = "shielded"            # missed yesterday, shield auto-activated
    RECOVERY = "recovery"            # shield expired, in recovery window
    BROKEN = "broken"                # recovery window passed, streak reset


@dataclass
class StreakState:
    """Complete streak state for a learner."""
    current_streak: int = 0
    longest_streak: int = 0
    shields_available: int = 0
    max_shields: int = 1               # increases at milestones
    shield_active: bool = False         # a shield is currently protecting the streak
    status: StreakStatus = StreakStatus.PENDING
    last_session_date: Optional[str] = None  # ISO date string (date only, no time)
    recovery_deadline: Optional[str] = None  # ISO datetime if in recovery
    streak_started_at: Optional[str] = None

    # Milestone flags
    fire_tier: int = 0                 # 0=none, 1=7d, 2=14d, 3=30d, 4=60d, 5=100d
    milestone_message: Optional[str] = None  # set when a milestone is just reached

    def to_dict(self) -> dict:
        return {
            "current_streak": self.current_streak,
            "longest_streak": self.longest_streak,
            "shields_available": self.shields_available,
            "max_shields": self.max_shields,
            "shield_active": self.shield_active,
            "status": self.status.value,
            "last_session_date": self.last_session_date,
            "recovery_deadline": self.recovery_deadline,
            "fire_tier": self.fire_tier,
            "milestone_message": self.milestone_message,
        }


# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────

RECOVERY_WINDOW_HOURS = 48

# Milestones: (streak_days, fire_tier, shield_slots, badge_id, message)
MILESTONES = [
    (7,   1, 1, "streak_7",   "7-day streak — you earned a Streak Shield!"),
    (14,  2, 1, "streak_14",  "14 days strong. Your momentum is building."),
    (30,  3, 2, "streak_30",  "30-day streak! You now carry 2 shields."),
    (60,  4, 2, "streak_60",  "60 days. That's real dedication."),
    (100, 5, 3, "streak_100", "100-day streak. Extraordinary commitment."),
]

# Shield earning: every N sessions beyond the daily minimum, earn a shield
SHIELD_EARN_SESSIONS = 3  # 3 extra sessions = 1 shield banked


# ──────────────────────────────────────────────────────────────
# Engine
# ──────────────────────────────────────────────────────────────

class StreakEngine:
    """Manages streak state with shields and recovery."""

    async def check_in(self, learner_id: str) -> StreakState:
        """Called when a learner opens the app or starts a session.

        Determines current streak status and applies shields/recovery
        as needed. Does NOT increment the streak — that happens in
        complete_session().
        """
        profile = await self._load_profile(learner_id)
        today = _today_str()

        state = StreakState(
            current_streak=profile.get("streak_current", 0),
            longest_streak=profile.get("streak_best", 0),
            shields_available=profile.get("streak_shields", 0),
            max_shields=profile.get("streak_max_shields", 1),
            shield_active=profile.get("streak_shield_active", False),
            last_session_date=profile.get("last_session_date"),
            recovery_deadline=profile.get("streak_recovery_deadline"),
            streak_started_at=profile.get("streak_started_at"),
        )

        last = state.last_session_date

        if not last:
            # Never had a session — fresh start
            state.status = StreakStatus.PENDING
            return state

        if last == today:
            # Already completed a session today
            state.status = StreakStatus.ACTIVE
            state.fire_tier = self._compute_fire_tier(state.current_streak)
            return state

        days_gap = _days_between(last, today)

        if days_gap == 1:
            # Yesterday was the last session — streak alive, pending today
            state.status = StreakStatus.PENDING
            state.shield_active = False  # clear any active shield
            state.fire_tier = self._compute_fire_tier(state.current_streak)
            return state

        if days_gap == 2:
            # Missed exactly one day
            if state.shield_active:
                # Shield was already activated — now in recovery window
                state.status = StreakStatus.RECOVERY
                if not state.recovery_deadline:
                    deadline = datetime.now(timezone.utc) + timedelta(hours=RECOVERY_WINDOW_HOURS)
                    state.recovery_deadline = deadline.isoformat()
                    await self._update_profile(learner_id, {"streak_recovery_deadline": state.recovery_deadline})
            elif state.shields_available > 0:
                # Auto-activate a shield
                state.shields_available -= 1
                state.shield_active = True
                state.status = StreakStatus.SHIELDED
                await self._update_profile(learner_id, {
                    "streak_shields": state.shields_available,
                    "streak_shield_active": True,
                })
            else:
                # No shields — start recovery window
                state.status = StreakStatus.RECOVERY
                deadline = datetime.now(timezone.utc) + timedelta(hours=RECOVERY_WINDOW_HOURS)
                state.recovery_deadline = deadline.isoformat()
                await self._update_profile(learner_id, {"streak_recovery_deadline": state.recovery_deadline})

            state.fire_tier = self._compute_fire_tier(state.current_streak)
            return state

        if days_gap >= 3:
            # More than 2 days missed — check recovery window
            if state.recovery_deadline:
                deadline = datetime.fromisoformat(state.recovery_deadline)
                if datetime.now(timezone.utc) < deadline:
                    state.status = StreakStatus.RECOVERY
                    state.fire_tier = self._compute_fire_tier(state.current_streak)
                    return state

            # Recovery expired or no recovery — streak breaks
            state.status = StreakStatus.BROKEN
            # Don't reset yet — complete_session will handle it
            state.fire_tier = 0
            return state

        state.fire_tier = self._compute_fire_tier(state.current_streak)
        return state

    async def complete_session(self, learner_id: str) -> StreakState:
        """Called when a learner finishes a session.

        Increments streak, checks milestones, awards shields,
        and persists the updated state.
        """
        state = await self.check_in(learner_id)
        today = _today_str()

        if state.last_session_date == today:
            # Already counted today — check for shield earning from extra sessions
            extra = await self._count_sessions_today(learner_id)
            if extra > 0 and extra % SHIELD_EARN_SESSIONS == 0:
                if state.shields_available < state.max_shields:
                    state.shields_available += 1
                    state.milestone_message = "Bonus session! You earned a Streak Shield."
            state.status = StreakStatus.ACTIVE
            await self._persist(learner_id, state)
            return state

        # New day — process based on status
        if state.status == StreakStatus.BROKEN:
            # Reset streak but preserve longest
            state.current_streak = 1
            state.streak_started_at = today
            state.shield_active = False
            state.recovery_deadline = None
        elif state.status in (StreakStatus.SHIELDED, StreakStatus.RECOVERY):
            # Recovered! Continue the streak
            state.current_streak += 1
            state.shield_active = False
            state.recovery_deadline = None
            state.milestone_message = "Streak recovered! Welcome back."
        else:
            # Normal continuation
            state.current_streak += 1
            if state.current_streak == 1:
                state.streak_started_at = today

        state.last_session_date = today
        state.status = StreakStatus.ACTIVE

        # Update longest
        if state.current_streak > state.longest_streak:
            state.longest_streak = state.current_streak

        # Check milestones
        milestone = self._check_milestone(state)
        if milestone:
            state.milestone_message = milestone["message"]
            state.max_shields = max(state.max_shields, milestone["shields"])
            # Award a shield at milestone if below cap
            if state.shields_available < state.max_shields:
                state.shields_available += 1

        state.fire_tier = self._compute_fire_tier(state.current_streak)

        await self._persist(learner_id, state)
        return state

    # ── Helpers ────────────────────────────────────────────────

    def _compute_fire_tier(self, streak: int) -> int:
        tier = 0
        for days, fire_tier, *_ in MILESTONES:
            if streak >= days:
                tier = fire_tier
        return tier

    def _check_milestone(self, state: StreakState) -> Optional[dict]:
        for days, fire_tier, shields, badge_id, message in MILESTONES:
            if state.current_streak == days:
                return {
                    "days": days,
                    "fire_tier": fire_tier,
                    "shields": shields,
                    "badge_id": badge_id,
                    "message": message,
                }
        return None

    # ── Persistence ───────────────────────────────────────────

    async def _persist(self, learner_id: str, state: StreakState):
        await self._update_profile(learner_id, {
            "streak_current": state.current_streak,
            "streak_best": state.longest_streak,
            "streak_shields": state.shields_available,
            "streak_max_shields": state.max_shields,
            "streak_shield_active": state.shield_active,
            "last_session_date": state.last_session_date,
            "streak_started_at": state.streak_started_at,
            "streak_recovery_deadline": state.recovery_deadline,
        })

    async def _load_profile(self, learner_id: str) -> dict:
        result = await asyncio.to_thread(
            lambda: db.client.table("learner_profiles")
            .select("*")
            .eq("learner_id", learner_id)
            .maybe_single()
            .execute()
        )
        return result.data or {}

    async def _update_profile(self, learner_id: str, patch: dict):
        await asyncio.to_thread(
            lambda: db.client.table("learner_profiles")
            .update(patch)
            .eq("learner_id", learner_id)
            .execute()
        )

    async def _count_sessions_today(self, learner_id: str) -> int:
        """Count sessions completed today (for shield earning)."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
        result = await asyncio.to_thread(
            lambda: db.client.table("stealth_observations")
            .select("id", count="exact")
            .eq("learner_id", learner_id)
            .eq("observation_type", "session_fatigue")  # one per session end
            .gte("created_at", today_start)
            .execute()
        )
        return result.count or 0


# ── Utilities ─────────────────────────────────────────────────

def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _days_between(date_str_a: str, date_str_b: str) -> int:
    a = datetime.strptime(date_str_a[:10], "%Y-%m-%d")
    b = datetime.strptime(date_str_b[:10], "%Y-%m-%d")
    return abs((b - a).days)
