"""
praxis/orchestration/momentum.py

Behavioral momentum engine.

This is not gamification. This is clinical behavioral science.

The core insight: learners build "momentum" by experiencing success.
When a learner answers several mastered items correctly in a row, they
develop behavioral momentum that carries them through harder target items.
If they hit too many errors, momentum breaks and frustration sets in.

The ratio of mastered-to-target items IS the momentum mechanism:
  - High mastered ratio → learner experiences success → momentum builds
  - As momentum builds → shift ratio toward more challenge
  - If momentum breaks (errors) → shift back toward more success
  - This adjustment is ASYMMETRIC: thickening (more support) happens
    faster than fading (less support), because frustration compounds
    faster than boredom.

Usage:
    from orchestration.momentum import MomentumCalculator

    calc = MomentumCalculator()
    ratio = calc.calculate_ratio(learner_mastery_data)
    next_type = calc.select_next_item_type(session_state)
    new_ratio = calc.adjust_ratio(ratio, performance_window)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ItemType(str, Enum):
    """What kind of item to present next."""
    MASTERED = "mastered"      # Known item for momentum building
    TARGET = "target"          # New skill being learned
    REVIEW = "review"          # Spaced retrieval maintenance probe


@dataclass
class MomentumState:
    """Tracks momentum within a single session."""
    ratio: float = 0.7                     # current mastered-to-target ratio (0.0-1.0)
    items_presented: int = 0
    consecutive_target_correct: int = 0
    consecutive_target_errors: int = 0
    consecutive_mastered: int = 0          # how many mastered items in a row
    consecutive_targets: int = 0           # how many target items in a row
    recent_window: list[dict] = field(default_factory=list)  # last 10 items
    review_items_due: int = 0              # how many review items queued
    review_items_served: int = 0

    @property
    def accuracy_recent(self) -> float:
        """Accuracy over the recent window (target items only)."""
        targets = [r for r in self.recent_window if r.get("type") == "target"]
        if not targets:
            return 1.0
        correct = sum(1 for r in targets if r.get("correct"))
        return correct / len(targets)


class MomentumCalculator:
    """
    Calculates and manages the mastered-to-target item ratio.

    The ratio determines how often we present mastered items (easy wins)
    vs target items (new learning). It adapts based on performance.

    Configuration:
        FADE_THRESHOLD:    consecutive correct targets to REDUCE support (raise challenge)
        THICKEN_THRESHOLD: consecutive target errors to INCREASE support (lower challenge)
        Note: thicken threshold < fade threshold (asymmetric by design)

        MAX_CONSECUTIVE_TARGETS:  frustration guard — never more than this many hard items in a row
        MAX_CONSECUTIVE_MASTERED: boredom guard — never more than this many easy items in a row

        REVIEW_INJECTION_RATE: every N items, check if a review item is due
    """

    # ── Configuration ──────────────────────────────────────────
    FADE_THRESHOLD = 3              # 3 correct targets → shift toward more challenge
    THICKEN_THRESHOLD = 2           # 2 target errors → shift toward more support

    FADE_STEP = 0.05               # how much to shift ratio when fading
    THICKEN_STEP = 0.08            # how much to shift when thickening (FASTER)

    MAX_CONSECUTIVE_TARGETS = 3     # frustration guard
    MAX_CONSECUTIVE_MASTERED = 5    # boredom guard

    REVIEW_INJECTION_RATE = 7       # check for reviews every N items

    # Ratio bounds
    RATIO_MIN = 0.15               # never less than 15% mastered (even strong learners need wins)
    RATIO_MAX = 0.85               # never more than 85% mastered (always some challenge)

    # ── Initial ratio calculation ──────────────────────────────

    def calculate_initial_ratio(self, mastery_data: list[dict]) -> float:
        """Calculate the starting ratio for a session based on learner history.

        Args:
            mastery_data: List of learner_mastery rows from Supabase.
                          Each row has: mastered, consecutive_correct,
                          consecutive_errors, total_attempts, total_correct

        Returns:
            Initial mastered-to-target ratio (0.0-1.0).
            Higher = more mastered items = more support.
        """
        if not mastery_data:
            # Brand new learner: 80% mastered, 20% target (high support)
            return 0.80

        # Calculate overall accuracy on target (non-mastered) items
        target_rows = [r for r in mastery_data if not r.get("mastered", False)]
        if not target_rows:
            # Everything mastered: mostly review/challenge
            return 0.30

        total_attempts = sum(r.get("total_attempts", 0) for r in target_rows)
        total_correct = sum(r.get("total_correct", 0) for r in target_rows)

        if total_attempts == 0:
            return 0.75  # no data on targets yet, start supportive

        accuracy = total_correct / total_attempts

        # Check most recent session's error streaks
        max_recent_errors = max(
            (r.get("consecutive_errors", 0) for r in target_rows),
            default=0
        )

        # Map accuracy to ratio
        if accuracy < 0.40 or max_recent_errors >= 3:
            # Struggling: heavy support
            return 0.80
        elif accuracy < 0.60:
            # Below average: moderate support
            return 0.70
        elif accuracy < 0.75:
            # Progressing: balanced
            return 0.60
        elif accuracy < 0.85:
            # Strong: more challenge
            return 0.45
        else:
            # Very strong: mostly challenge
            return 0.30

    # ── Per-item selection ─────────────────────────────────────

    def select_next_item_type(self, state: MomentumState) -> ItemType:
        """Select what type of item to present next.

        Uses the current ratio for probabilistic selection, but applies
        hard guards against frustration (too many targets) and boredom
        (too many mastered items).

        Args:
            state: Current momentum state for this session

        Returns:
            ItemType indicating what kind of item to present
        """
        # 1. Check if review items are due
        if (
            state.review_items_due > state.review_items_served
            and state.items_presented > 0
            and state.items_presented % self.REVIEW_INJECTION_RATE == 0
        ):
            return ItemType.REVIEW

        # 2. Apply hard guards
        if state.consecutive_targets >= self.MAX_CONSECUTIVE_TARGETS:
            # Frustration guard: force a mastered item
            return ItemType.MASTERED

        if state.consecutive_mastered >= self.MAX_CONSECUTIVE_MASTERED:
            # Boredom guard: force a target item
            return ItemType.TARGET

        # 3. Probabilistic selection based on ratio
        roll = random.random()
        if roll < state.ratio:
            return ItemType.MASTERED
        else:
            return ItemType.TARGET

    # ── Ratio adjustment ───────────────────────────────────────

    def adjust_ratio(
        self,
        state: MomentumState,
        item_type: ItemType,
        correct: bool,
    ) -> MomentumState:
        """Update momentum state after a learner response.

        Adjusts the ratio based on performance on TARGET items.
        Mastered items don't affect the ratio (they're supposed to be easy).

        The adjustment is ASYMMETRIC:
          - Fading (reducing support): requires FADE_THRESHOLD consecutive correct
          - Thickening (increasing support): requires only THICKEN_THRESHOLD errors

        Args:
            state: Current momentum state
            item_type: What type of item was just presented
            correct: Whether the learner got it right

        Returns:
            Updated MomentumState
        """
        # Track the item in the recent window
        state.recent_window.append({
            "type": item_type.value,
            "correct": correct,
        })
        if len(state.recent_window) > 10:
            state.recent_window = state.recent_window[-10:]

        state.items_presented += 1

        # Track consecutive streaks by item type
        if item_type == ItemType.MASTERED:
            state.consecutive_mastered += 1
            state.consecutive_targets = 0
        elif item_type == ItemType.TARGET:
            state.consecutive_targets += 1
            state.consecutive_mastered = 0
        elif item_type == ItemType.REVIEW:
            state.review_items_served += 1
            # Reviews reset both counters (they're a break in the pattern)
            state.consecutive_mastered = 0
            state.consecutive_targets = 0

        # Only target items affect the ratio
        if item_type == ItemType.TARGET:
            if correct:
                state.consecutive_target_correct += 1
                state.consecutive_target_errors = 0

                # FADE: shift toward more challenge
                if state.consecutive_target_correct >= self.FADE_THRESHOLD:
                    state.ratio = max(
                        self.RATIO_MIN,
                        state.ratio - self.FADE_STEP
                    )
                    state.consecutive_target_correct = 0  # reset streak
            else:
                state.consecutive_target_errors += 1
                state.consecutive_target_correct = 0

                # THICKEN: shift toward more support (faster than fading)
                if state.consecutive_target_errors >= self.THICKEN_THRESHOLD:
                    state.ratio = min(
                        self.RATIO_MAX,
                        state.ratio + self.THICKEN_STEP
                    )
                    state.consecutive_target_errors = 0  # reset streak

        return state

    # ── Session summary ────────────────────────────────────────

    def get_session_summary(self, state: MomentumState) -> dict:
        """Summarize the momentum state for logging/analytics."""
        return {
            "items_presented": state.items_presented,
            "current_ratio": round(state.ratio, 3),
            "recent_accuracy": round(state.accuracy_recent, 3),
            "reviews_served": state.review_items_served,
            "reviews_remaining": max(0, state.review_items_due - state.review_items_served),
        }
