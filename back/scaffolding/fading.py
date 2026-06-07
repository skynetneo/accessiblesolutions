"""
praxis/scaffolding/fading.py

Asymmetric fading and thickening of prompt support.

This module now supports both the original simple interface and the richer
session-controller contract that estimates acquisition profile and uses
mastery probability plus response quality.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FadingAction(str, Enum):
    HOLD = "hold"
    FADE = "fade"          # reduce support (level goes UP toward 10)
    THICKEN = "thicken"    # increase support (level goes DOWN toward 1)


class AcquisitionProfile(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    FRAGILE = "fragile"


@dataclass
class FadingDecision:
    action: FadingAction
    new_level: int
    reason: str
    confidence: float = 0.5
    profile_used: AcquisitionProfile = AcquisitionProfile.STANDARD


class FadingEngine:
    """Decides when to fade or thicken prompt support."""

    FADE_THRESHOLD = 3
    THICKEN_THRESHOLD = 2
    LEVEL_MIN = 1
    LEVEL_MAX = 10

    PROFILE_PARAMS = {
        AcquisitionProfile.FAST: {"fade": 0.60, "thicken": 0.35},
        AcquisitionProfile.STANDARD: {"fade": 0.72, "thicken": 0.30},
        AcquisitionProfile.FRAGILE: {"fade": 0.82, "thicken": 0.25},
    }

    @staticmethod
    def mastery_probability_from_theta(theta: float) -> float:
        """Map a theta estimate to an interpretable 0..1 mastery probability."""
        clipped = max(-4.0, min(4.0, theta))
        return 1.0 / (1.0 + math.exp(-clipped))

    def _estimate_profile(self, fade_history: list[dict]) -> AcquisitionProfile:
        """Infer how aggressively to fade from prior support changes."""
        if not fade_history:
            return AcquisitionProfile.STANDARD

        recent = fade_history[-6:]
        fades = sum(1 for item in recent if item.get("action") == FadingAction.FADE.value)
        thickens = sum(1 for item in recent if item.get("action") == FadingAction.THICKEN.value)

        if fades >= 3 and thickens == 0:
            return AcquisitionProfile.FAST
        if thickens >= 2:
            return AcquisitionProfile.FRAGILE
        return AcquisitionProfile.STANDARD

    def evaluate(
        self,
        current_level: int,
        consecutive_correct: Optional[int] = None,
        consecutive_errors: int = 0,
        mastery_probability: Optional[float] = None,
        response_quality: Optional[float] = None,
        skill_id: str = "",
        fade_history: Optional[list[dict]] = None,
    ) -> FadingDecision:
        """Evaluate whether to change the prompt level.

        Supports both:
        - legacy streak-based calls
        - probability/quality-based calls from the session controller
        """
        fade_history = fade_history or []
        profile = self._estimate_profile(fade_history)
        params = self.PROFILE_PARAMS[profile]

        # Backward-compatible streak mode.
        if mastery_probability is None or response_quality is None:
            return self._evaluate_streaks(
                current_level=current_level,
                consecutive_correct=consecutive_correct or 0,
                consecutive_errors=consecutive_errors,
                profile=profile,
            )

        # Protect the learner first if errors or low-quality responses stack up.
        if consecutive_errors >= self.THICKEN_THRESHOLD or response_quality <= params["thicken"]:
            if current_level > self.LEVEL_MIN:
                return FadingDecision(
                    action=FadingAction.THICKEN,
                    new_level=current_level - 1,
                    reason=(
                        f"increase support for {skill_id or 'skill'} "
                        f"(quality={response_quality:.2f}, errors={consecutive_errors})"
                    ),
                    confidence=max(0.55, 1.0 - response_quality),
                    profile_used=profile,
                )

        if mastery_probability >= params["fade"] and response_quality >= 0.65:
            if current_level < self.LEVEL_MAX:
                return FadingDecision(
                    action=FadingAction.FADE,
                    new_level=current_level + 1,
                    reason=(
                        f"reduce support for {skill_id or 'skill'} "
                        f"(mastery={mastery_probability:.2f}, quality={response_quality:.2f})"
                    ),
                    confidence=min(0.95, max(mastery_probability, response_quality)),
                    profile_used=profile,
                )

        return FadingDecision(
            action=FadingAction.HOLD,
            new_level=current_level,
            reason="no prompt change",
            confidence=0.5,
            profile_used=profile,
        )

    def _evaluate_streaks(
        self,
        current_level: int,
        consecutive_correct: int,
        consecutive_errors: int,
        profile: AcquisitionProfile,
    ) -> FadingDecision:
        """Original streak-driven behavior retained for compatibility."""
        if consecutive_errors >= self.THICKEN_THRESHOLD and current_level > self.LEVEL_MIN:
            return FadingDecision(
                action=FadingAction.THICKEN,
                new_level=current_level - 1,
                reason=f"{consecutive_errors} consecutive errors -> adding support",
                confidence=0.7,
                profile_used=profile,
            )

        if consecutive_correct >= self.FADE_THRESHOLD and current_level < self.LEVEL_MAX:
            return FadingDecision(
                action=FadingAction.FADE,
                new_level=current_level + 1,
                reason=f"{consecutive_correct} consecutive correct -> reducing support",
                confidence=0.7,
                profile_used=profile,
            )

        return FadingDecision(
            action=FadingAction.HOLD,
            new_level=current_level,
            reason="no change",
            confidence=0.5,
            profile_used=profile,
        )
