"""
praxis/teams/gamification.py

Gamification Team.

Pattern: Stateless utility (no agent — pure logic + DB persistence).
Why: Gamification doesn't need LLM calls. It's deterministic rules
applied to events emitted by other teams. Keeping it as functions
instead of an agent avoids unnecessary model invocations.

The coaching team emits gamification_events via award_progress and
ABAReinforcementMiddleware. This module processes those events,
applies rules, and persists state.

Usage:
    from teams.gamification import GamificationEngine

    engine = GamificationEngine()
    results = await engine.process_events(learner_id, events)
    # results = {
    #     "xp_awarded": 35,
    #     "new_badges": ["first_mastery"],
    #     "streak_current": 7,
    #     "level_up": False,
    # }
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from db.client import db


# ──────────────────────────────────────────────────────────────
# Badge definitions (static — cache-friendly)
# ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BadgeRule:
    badge_id: str
    name: str
    description: str
    condition: str      # key into CONDITION_CHECKS
    threshold: int

BADGES: dict[str, BadgeRule] = {
    "first_correct": BadgeRule(
        "first_correct", "First Steps",
        "Got your first answer right.", "total_correct", 1,
    ),
    "streak_3": BadgeRule(
        "streak_3", "Hat Trick",
        "3 correct answers in a row.", "streak", 3,
    ),
    "streak_7": BadgeRule(
        "streak_7", "On Fire",
        "7 correct in a row.", "streak", 7,
    ),
    "streak_15": BadgeRule(
        "streak_15", "Unstoppable",
        "15 correct in a row.", "streak", 15,
    ),
    "first_return": BadgeRule(
        "first_return", "First Return",
        "Returned for the first time.", "first_return", 2,
    ),
    "return_3": BadgeRule(
        "return_3", "Consistency is Key",
        "3 days in a row.", "days_learning", 3,
    ),
    "return_4": BadgeRule(
        "return_4", "On Fire",
        "4 days in a row.", "days_learning", 4,
    ),
    "return_5": BadgeRule(
        "return_5", "Unbelievable!",
        "5 days in a row.", "days_learning", 5,
    ),
    "return_10": BadgeRule(
        "return_10", "Unstoppable",
        "10 days in a row.", "days_learning", 10,
    ),
    "return_15": BadgeRule(
        "return_15", "Unstoppable",
        "15 days in a row.", "days_learning", 15,
    ),
    "return_20": BadgeRule(
        "return_20", "Unstoppable",
        "20 days in a row.", "days_learning", 20,
    ),
    "return_25": BadgeRule(
        "return_25", "Unstoppable",
        "25 days in a row.", "days_learning", 25,
    ),
    "return_30": BadgeRule(
        "return_30", "Unstoppable",
        "30 days in a row.", "days_learning", 30,
    ),
    "first_mastery": BadgeRule(
        "first_mastery", "Skill Unlocked",
        "Mastered your first skill.", "skills_mastered", 1,
    ),
    "mastery_5": BadgeRule(
        "mastery_5", "Building Momentum",
        "Mastered 5 skills.", "skills_mastered", 5,
    ),
    "mastery_20": BadgeRule(
        "mastery_20", "Knowledge Base",
        "Mastered 20 skills.", "skills_mastered", 20,
    ),
    "sessions_5": BadgeRule(
        "sessions_5", "Dedicated Learner",
        "Completed 5 learning sessions.", "sessions_completed", 5,
    ),
    "sessions_20": BadgeRule(
        "sessions_20", "Consistent",
        "Completed 20 sessions.", "sessions_completed", 20,
    ),
    "xp_100": BadgeRule(
        "xp_100", "Century",
        "Earned 100 XP.", "total_xp", 100,
    ),
    "xp_500": BadgeRule(
        "xp_500", "XP Hunter",
        "Earned 500 XP.", "total_xp", 500,
    ),
    "xp_1000": BadgeRule(
        "xp_1000", "Grinder",
        "Earned 1000 XP.", "total_xp", 1000,
    ),
    "employment_intake": BadgeRule(
        "employment_intake", "Career Ready",
        "Completed the employment profile intake.", "employment_intake_done", 1,
    ),
    "first_resume": BadgeRule(
        "first_resume", "Resume Builder",
        "Created your first resume.", "resume_versions", 1,
    ),
}

# XP level thresholds (cumulative)
LEVEL_THRESHOLDS = [0, 50, 150, 300, 500, 800, 1200, 1800, 2500, 3500, 5000]


# ──────────────────────────────────────────────────────────────
# Engine
# ──────────────────────────────────────────────────────────────

class GamificationEngine:
    """Processes gamification events and applies rules.

    Stateless — reads current state from DB, applies events,
    writes updated state back. Safe for concurrent sessions.
    """

    async def process_events(
        self,
        learner_id: str,
        events: list[dict],
    ) -> dict:
        """Process a batch of gamification events from a session.

        Args:
            learner_id: The learner
            events: List of event dicts from gamification_events state

        Returns:
            Summary of what happened (xp, badges, streak, level_up)
        """
        if not events:
            return {"xp_awarded": 0, "new_badges": [], "streak_current": 0, "level_up": False}

        state = await self._load_state(learner_id)
        xp_total = 0
        new_badges = []

        for event in events:
            event_type = event.get("type", "")

            if event_type == "xp_award":
                amount = event.get("amount", 0)
                xp_total += amount
                state["total_xp"] = state.get("total_xp", 0) + amount

            elif event_type == "reinforcement":
                amount = event.get("xp_award", 0)
                xp_total += amount
                state["total_xp"] = state.get("total_xp", 0) + amount

            elif event_type == "correct_answer":
                state["total_correct"] = state.get("total_correct", 0) + 1
                state["streak"] = state.get("streak", 0) + 1

            elif event_type == "incorrect_answer":
                state["streak"] = 0

            elif event_type == "skill_mastered":
                state["skills_mastered"] = state.get("skills_mastered", 0) + 1

            elif event_type == "session_complete":
                state["sessions_completed"] = state.get("sessions_completed", 0) + 1

        # Check badge eligibility
        earned = set(state.get("badges_earned", []))
        for badge_id, rule in BADGES.items():
            if badge_id in earned:
                continue
            value = state.get(rule.condition, 0)
            if value >= rule.threshold:
                earned.add(badge_id)
                new_badges.append(badge_id)
                # Bonus XP for earning a badge
                badge_xp = 25
                xp_total += badge_xp
                state["total_xp"] = state.get("total_xp", 0) + badge_xp

        state["badges_earned"] = list(earned)

        # Check level up
        old_level = state.get("level", 1)
        new_level = self._compute_level(state.get("total_xp", 0))
        level_up = new_level > old_level
        state["level"] = new_level

        # Persist
        await self._save_state(learner_id, state)

        # Log badge events
        for badge_id in new_badges:
            await self._log_badge(learner_id, badge_id)

        return {
            "xp_awarded": xp_total,
            "new_badges": new_badges,
            "streak_current": state.get("streak", 0),
            "level": new_level,
            "level_up": level_up,
            "total_xp": state.get("total_xp", 0),
        }

    def _compute_level(self, total_xp: int) -> int:
        """Determine level from cumulative XP."""
        level = 1
        for i, threshold in enumerate(LEVEL_THRESHOLDS):
            if total_xp >= threshold:
                level = i + 1
        return level

    def get_level_progress(self, total_xp: int) -> dict:
        """Get progress toward the next level."""
        level = self._compute_level(total_xp)
        if level >= len(LEVEL_THRESHOLDS):
            return {"level": level, "xp_current": total_xp, "xp_next": None, "progress": 1.0}
        current_threshold = LEVEL_THRESHOLDS[level - 1]
        next_threshold = LEVEL_THRESHOLDS[level]
        progress = (total_xp - current_threshold) / max(next_threshold - current_threshold, 1)
        return {
            "level": level,
            "xp_current": total_xp,
            "xp_for_level": current_threshold,
            "xp_next": next_threshold,
            "progress": round(min(1.0, progress), 3),
        }

    # ── Persistence ────────────────────────────────────────────

    async def _load_state(self, learner_id: str) -> dict:
        import asyncio
        result = await asyncio.to_thread(
            lambda: db.client.table("gamification_state")
            .select("*")
            .eq("learner_id", learner_id)
            .maybe_single()
            .execute()
        )
        if result.data:
            return result.data.get("state_data", {}) if isinstance(result.data.get("state_data"), dict) else {}
        return {}

    async def _save_state(self, learner_id: str, state: dict):
        import asyncio
        await asyncio.to_thread(
            lambda: db.client.table("gamification_state")
            .upsert({
                "learner_id": learner_id,
                "state_data": state,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            .execute()
        )

    async def _log_badge(self, learner_id: str, badge_id: str):
        import asyncio
        rule = BADGES.get(badge_id)
        await asyncio.to_thread(
            lambda: db.client.table("badge_log")
            .insert({
                "learner_id": learner_id,
                "badge_id": badge_id,
                "badge_name": rule.name if rule else badge_id,
                "earned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            .execute()
        )