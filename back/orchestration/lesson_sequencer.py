"""
praxis/orchestration/lesson_sequencer.py

Decides what to teach in the next session.

Given a learner's mastery state, the skill graph, and the momentum calculator,
produces a LessonPlan: which skills to target, which mastered items to
intersperse for momentum, which items are due for spaced retrieval review,
and which employment competencies to weave in.

The sequencer does NOT generate content. It produces a plan that the content
team uses to generate or retrieve the actual items.

Usage:
    from orchestration.lesson_sequencer import LessonSequencer, LessonPlan

    sequencer = LessonSequencer()
    plan = await sequencer.plan_session(learner_id="abc123")

    # During the session, get the next item type
    next_type = sequencer.get_next_item(momentum_state)
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Optional

from curriculum.skill_graph import SkillGraph, SkillNode
from orchestration.momentum import (
    MomentumCalculator,
    MomentumState,
    ItemType,
)
from db.client import db


# ──────────────────────────────────────────────────────────────
# Lesson Plan output
# ──────────────────────────────────────────────────────────────

@dataclass
class LessonItem:
    """A single item slot in the lesson plan."""
    skill_id: str
    chain_id: str
    chain_step: int
    item_type: str              # "target", "mastered", "review"
    seed_id: Optional[str] = None
    cached_item_id: Optional[str] = None
    prompt_level: int = 3       # current scaffold level for this skill


@dataclass
class LessonPlan:
    """Output of the lesson sequencer. Tells the content team what to build."""

    # Skills to teach (1-3 new skills per session)
    target_skills: list[dict] = field(default_factory=list)
    # Each: {"skill_id", "chain_id", "chain_step", "prompt_level", "difficulty_b"}

    # Mastered items for behavioral momentum interspersing
    mastered_pool: list[dict] = field(default_factory=list)
    # Each: {"skill_id", "chain_step"}

    # Spaced retrieval review items
    review_items: list[dict] = field(default_factory=list)
    # Each: {"skill_id", "chain_step", "last_interval_days"}

    # Employment competencies to weave in (structural layer)
    competency_focus: list[str] = field(default_factory=list)
    # 1-2 competency names: ["communication", "results_orientation"]

    # Momentum configuration
    initial_ratio: float = 0.7
    estimated_items: int = 15
    estimated_duration_minutes: int = 20

    # Metadata
    learner_id: str = ""
    subject: Optional[str] = None  # None = mixed subjects

    def summary(self) -> str:
        """Human-readable summary for logging."""
        return (
            f"LessonPlan for {self.learner_id}: "
            f"{len(self.target_skills)} targets, "
            f"{len(self.mastered_pool)} mastered pool, "
            f"{len(self.review_items)} reviews, "
            f"ratio={self.initial_ratio:.0%}, "
            f"competencies={self.competency_focus}, "
            f"~{self.estimated_duration_minutes}min"
        )


# ──────────────────────────────────────────────────────────────
# Lesson Sequencer
# ──────────────────────────────────────────────────────────────

class LessonSequencer:
    """
    Plans learning sessions by combining:
    1. Skill graph → what's teachable (prerequisites met)
    2. Mastery data → what's been mastered, what's in progress
    3. Momentum calculator → how to balance challenge vs support
    4. Spaced retrieval → what's due for review
    5. Competency profile → which employment skills need practice
    """

    def __init__(
        self,
        skill_graph: Optional[SkillGraph] = None,
        momentum: Optional[MomentumCalculator] = None,
        max_target_skills: int = 2,
        max_mastered_pool: int = 8,
        max_review_items: int = 3,
        default_session_items: int = 15,
        default_session_minutes: int = 20,
    ):
        self.skill_graph = skill_graph
        self.momentum = momentum or MomentumCalculator()
        self.max_target_skills = max_target_skills
        self.max_mastered_pool = max_mastered_pool
        self.max_review_items = max_review_items
        self.default_session_items = default_session_items
        self.default_session_minutes = default_session_minutes

    async def ensure_graph(self):
        """Build the skill graph if not already loaded."""
        if self.skill_graph is None:
            self.skill_graph = await SkillGraph.build_from_db()

    # ── Main planning method ───────────────────────────────────

    async def plan_session(
        self,
        learner_id: str,
        subject: Optional[str] = None,
        session_minutes: Optional[int] = None,
    ) -> LessonPlan:
        """Plan a complete learning session for a learner.

        Args:
            learner_id: The learner to plan for
            subject: Limit to a specific curriculum subject (None = any subject)
            session_minutes: Override session length preference

        Returns:
            LessonPlan with target skills, mastered pool, reviews, and competency focus
        """
        await self.ensure_graph()

        # 1. Load learner data
        mastery_data = await self._load_mastery(learner_id)
        profile = await self._load_profile(learner_id)
        competency_data = await self._load_competencies(learner_id)

        # Build the mastered set for skill graph queries
        mastered_set = set()
        for row in mastery_data:
            if row.get("mastered"):
                mastered_set.add(f"{row['skill_id']}:{row['chain_step']}")

        # 2. Select target skills (what to teach)
        targets = await self._select_targets(
            mastered_set, mastery_data, subject
        )

        # 3. Select mastered pool (for momentum interspersing)
        mastered_pool = self._select_mastered_pool(mastery_data, mastered_set)

        # 4. Select review items (spaced retrieval)
        reviews = self._select_reviews(mastery_data)

        # 5. Select competency focus (weakest employment skills)
        competencies = self._select_competencies(competency_data)

        # 6. Calculate momentum ratio
        ratio = self.momentum.calculate_initial_ratio(mastery_data)

        # 7. Estimate session size
        minutes = session_minutes or profile.get("session_length_preference", self.default_session_minutes)
        estimated_items = self._estimate_item_count(minutes)

        return LessonPlan(
            target_skills=targets,
            mastered_pool=mastered_pool,
            review_items=reviews,
            competency_focus=competencies,
            initial_ratio=ratio,
            estimated_items=estimated_items,
            estimated_duration_minutes=minutes,
            learner_id=learner_id,
            subject=subject,
        )

    # ── Target selection ───────────────────────────────────────

    async def _select_targets(
        self,
        mastered_set: set[str],
        mastery_data: list[dict],
        subject: Optional[str],
    ) -> list[dict]:
        """Select 1-2 target skills from the teachable frontier.

        Priority order:
        1. Skills already in progress (have attempts but not mastered)
        2. Skills at the frontier (prerequisites met, never attempted)
        3. Among equals, prefer skills that unlock the most other skills
        """
        # Find skills in progress (started but not mastered)
        in_progress = []
        for row in mastery_data:
            if not row.get("mastered") and row.get("total_attempts", 0) > 0:
                node_id = f"{row['skill_id']}:{row['chain_step']}"
                node = self.skill_graph.nodes.get(node_id)
                if node and (subject is None or node.subject == subject):
                    in_progress.append({
                        "skill_id": row["skill_id"],
                        "chain_id": node.chain_id,
                        "chain_step": row["chain_step"],
                        "prompt_level": row.get("prompt_level", 3),
                        "difficulty_b": 0.0,  # will be set from seed data
                        "consecutive_correct": row.get("consecutive_correct", 0),
                        "priority": "in_progress",
                    })

        # Sort in-progress by closest to mastery (highest consecutive correct)
        in_progress.sort(key=lambda x: x["consecutive_correct"], reverse=True)

        if len(in_progress) >= self.max_target_skills:
            return in_progress[:self.max_target_skills]

        # Fill remaining slots from the teachable frontier
        teachable = self.skill_graph.get_next_teachable(mastered_set, subject)
        frontier = []
        for node in teachable:
            if node.node_id not in {f"{t['skill_id']}:{t['chain_step']}" for t in in_progress}:
                # Score by how many skills this unlocks (maximize downstream value)
                unlock_count = len(node.unlocks)
                frontier.append({
                    "skill_id": node.skill_id,
                    "chain_id": node.chain_id,
                    "chain_step": node.chain_step,
                    "prompt_level": 3,  # default start at verbal
                    "difficulty_b": 0.0,
                    "unlock_count": unlock_count,
                    "priority": "frontier",
                })

        # Sort frontier by unlock potential (teach skills that unlock the most)
        frontier.sort(key=lambda x: x["unlock_count"], reverse=True)

        targets = in_progress + frontier
        return targets[:self.max_target_skills]

    # ── Mastered pool selection ────────────────────────────────

    def _select_mastered_pool(
        self,
        mastery_data: list[dict],
        mastered_set: set[str],
    ) -> list[dict]:
        """Select mastered items for behavioral momentum interspersing.

        Prefers recently mastered skills (more relevant, better reinforcement)
        over long-mastered ones.
        """
        mastered_rows = [
            r for r in mastery_data
            if r.get("mastered") and r.get("total_correct", 0) > 0
        ]

        # Sort by mastery recency (most recent first)
        mastered_rows.sort(
            key=lambda r: r.get("mastered_at", ""),
            reverse=True,
        )

        pool = []
        for row in mastered_rows[:self.max_mastered_pool]:
            pool.append({
                "skill_id": row["skill_id"],
                "chain_step": row.get("chain_step", 1),
            })

        return pool

    # ── Review selection ───────────────────────────────────────

    def _select_reviews(self, mastery_data: list[dict]) -> list[dict]:
        """Select mastered skills due for spaced retrieval maintenance.

        Uses expanding intervals: 1, 3, 7, 14, 30 days.
        We select up to max_review_items that are past their review date.
        """
        # In production, compare mastered_at + review_interval_days to now.
        # For simplicity, we select mastered items with the shortest intervals
        # (they're the most recently mastered and most at risk of decay).
        reviews = []
        for row in mastery_data:
            if row.get("mastered") and row.get("review_interval_days"):
                reviews.append({
                    "skill_id": row["skill_id"],
                    "chain_step": row.get("chain_step", 1),
                    "last_interval_days": row.get("review_interval_days", 1),
                })

        # Shortest interval = most urgently needs review
        reviews.sort(key=lambda r: r["last_interval_days"])
        return reviews[:self.max_review_items]

    # ── Competency selection ───────────────────────────────────

    def _select_competencies(self, competency_data: list[dict]) -> list[str]:
        """Select 1-2 employment competencies to reinforce in this session.

        Prioritizes weakest competencies (lowest strength scores).
        If no competency data exists yet, use defaults.
        """
        if not competency_data:
            # No data yet — start with the most universally useful
            return ["communication", "problem_solving"]

        # Sort by strength ascending (weakest first)
        sorted_comps = sorted(
            competency_data,
            key=lambda c: c.get("strength", 0.0),
        )

        # Take the 2 weakest
        return [c["competency"] for c in sorted_comps[:2]]

    # ── Duration estimation ────────────────────────────────────

    def _estimate_item_count(self, session_minutes: int) -> int:
        """Estimate how many items fit in a session.

        Rough heuristic: ~1.3 minutes per item on average
        (includes reading, thinking, responding, feedback).
        """
        items = int(session_minutes / 1.3)
        return max(5, min(items, 30))  # between 5 and 30 items

    # ── Data loading helpers ───────────────────────────────────

    async def _load_mastery(self, learner_id: str) -> list[dict]:
        """Load all mastery data for a learner from Supabase."""
        result = await asyncio.to_thread(
            lambda: db.client.table("learner_mastery")
            .select("*")
            .eq("learner_id", learner_id)
            .execute()
        )
        return result.data or []

    async def _load_profile(self, learner_id: str) -> dict:
        """Load learner profile from Supabase."""
        result = await asyncio.to_thread(
            lambda: db.client.table("learner_profiles")
            .select("*")
            .eq("learner_id", learner_id)
            .maybe_single()
            .execute()
        )
        return result.data or {}

    async def _load_competencies(self, learner_id: str) -> list[dict]:
        """Load competency data for a learner from Supabase."""
        result = await asyncio.to_thread(
            lambda: db.client.table("learner_competencies")
            .select("*")
            .eq("learner_id", learner_id)
            .execute()
        )
        return result.data or []
