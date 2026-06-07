"""Minimal mastery compatibility layer for the session controller."""

from __future__ import annotations

from enum import Enum


class MasteryStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    MASTERED = "mastered"


class MasteryEngine:
    """Compatibility shim.

    The current session controller instantiates a mastery engine but does not
    call into it yet. Keep the API surface small until the controller and the
    mastery model are unified.
    """

    def classify(
        self,
        total_attempts: int = 0,
        total_correct: int = 0,
        mastered: bool = False,
    ) -> MasteryStatus:
        if mastered:
            return MasteryStatus.MASTERED
        if total_attempts > 0 or total_correct > 0:
            return MasteryStatus.IN_PROGRESS
        return MasteryStatus.NOT_STARTED
