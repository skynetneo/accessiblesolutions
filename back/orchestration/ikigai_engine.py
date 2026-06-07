"""
back/orchestration/ikigai_engine.py

Ikigai Convergence Engine — computes the four domain scores and
overall convergence for the Living Ikigai Dashboard.

The four Ikigai circles:
  PASSION  (what you love)    ← interests, engagement levels, chosen themes
  TALENT   (what you're good at) ← mastered skills, competencies, skill levels
  MISSION  (what the world needs) ← career demand data, market alignment
  VOCATION (what you can be paid for) ← salary potential, skill-to-career match

Convergence = how close the four circles are to overlapping.
A score of 0.0 means no overlap. A score of 1.0 means the learner
has found strong alignment across all four domains.

This engine is program-agnostic. It works with any curriculum —
GED, digital literacy, career prep, certifications — because it
reads from the shared learner_profiles, learner_mastery, and
work_profiles tables.

Usage:
    from orchestration.ikigai_engine import IkigaiEngine, IkigaiState

    engine = IkigaiEngine()
    state = await engine.compute(learner_id="abc123")
    # state.convergence → 0.42
    # state.passion → DomainScore(score=0.6, signals=[...])
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from typing import Optional

from db.client import db


# ──────────────────────────────────────────────────────────────
# Data types
# ──────────────────────────────────────────────────────────────

@dataclass
class DomainSignal:
    """A single data point contributing to a domain score."""
    source: str          # "interests", "mastery", "competency", "career_match", etc.
    label: str           # human-readable label for the UI
    value: float         # 0-1 contribution
    weight: float = 1.0  # importance multiplier


@dataclass
class DomainScore:
    """Score for one of the four Ikigai domains."""
    score: float = 0.0           # 0-1 normalized
    signals: list[DomainSignal] = field(default_factory=list)
    top_items: list[str] = field(default_factory=list)  # top 3 contributors

    def add(self, source: str, label: str, value: float, weight: float = 1.0):
        self.signals.append(DomainSignal(source=source, label=label, value=value, weight=weight))

    def compute(self):
        """Compute weighted average score from signals."""
        if not self.signals:
            self.score = 0.0
            return
        total_weight = sum(s.weight for s in self.signals)
        if total_weight == 0:
            self.score = 0.0
            return
        self.score = sum(s.value * s.weight for s in self.signals) / total_weight
        self.score = max(0.0, min(1.0, self.score))
        # Top items: highest-value signals
        ranked = sorted(self.signals, key=lambda s: s.value * s.weight, reverse=True)
        self.top_items = [s.label for s in ranked[:3]]


@dataclass
class IkigaiState:
    """Complete Ikigai state for a learner."""
    learner_id: str = ""
    passion: DomainScore = field(default_factory=DomainScore)    # what you love
    talent: DomainScore = field(default_factory=DomainScore)     # what you're good at
    mission: DomainScore = field(default_factory=DomainScore)    # what the world needs
    vocation: DomainScore = field(default_factory=DomainScore)   # what you can be paid for
    convergence: float = 0.0     # 0-1, how aligned the four domains are

    def to_dict(self) -> dict:
        return {
            "learner_id": self.learner_id,
            "convergence": round(self.convergence, 4),
            "passion": {
                "score": round(self.passion.score, 4),
                "top_items": self.passion.top_items,
            },
            "talent": {
                "score": round(self.talent.score, 4),
                "top_items": self.talent.top_items,
            },
            "mission": {
                "score": round(self.mission.score, 4),
                "top_items": self.mission.top_items,
            },
            "vocation": {
                "score": round(self.vocation.score, 4),
                "top_items": self.vocation.top_items,
            },
        }


# ──────────────────────────────────────────────────────────────
# Engine
# ──────────────────────────────────────────────────────────────

class IkigaiEngine:
    """Computes Ikigai convergence from learner data.

    Each domain is scored 0-1 from weighted signals.
    Convergence is the geometric mean of all four domain scores,
    so ALL domains must be strong for convergence to be high.
    A learner who's passionate but unskilled gets low convergence.
    """

    async def compute(self, learner_id: str) -> IkigaiState:
        """Compute the full Ikigai state for a learner."""
        # Load all data in parallel
        profile, mastery, competencies, work_profile = await asyncio.gather(
            self._load_profile(learner_id),
            self._load_mastery(learner_id),
            self._load_competencies(learner_id),
            self._load_work_profile(learner_id),
        )

        state = IkigaiState(learner_id=learner_id)

        self._compute_passion(state, profile)
        self._compute_talent(state, mastery, competencies)
        self._compute_mission(state, competencies, work_profile)
        self._compute_vocation(state, mastery, work_profile, profile)

        # Compute each domain's aggregate
        state.passion.compute()
        state.talent.compute()
        state.mission.compute()
        state.vocation.compute()

        # Convergence: geometric mean of all four
        scores = [state.passion.score, state.talent.score,
                  state.mission.score, state.vocation.score]

        # Geometric mean: (a * b * c * d) ^ (1/4)
        # Handles zeros gracefully (any zero → convergence is zero)
        product = 1.0
        for s in scores:
            product *= max(s, 0.001)  # floor to avoid log(0)
        state.convergence = max(0.0, min(1.0, product ** 0.25))

        return state

    # ── Domain: Passion (what you love) ───────────────────────

    def _compute_passion(self, state: IkigaiState, profile: dict):
        """Score based on identified interests, engagement, and exploration."""
        interests = profile.get("interests", [])
        if isinstance(interests, str):
            import json
            interests = json.loads(interests)

        # Interests discovered
        if interests:
            breadth = min(len(interests) / 5.0, 1.0)  # 5 interests = full score
            state.passion.add("interests", "Interests discovered", breadth, weight=2.0)
            for interest in interests[:3]:
                state.passion.add("interest_item", interest, 0.8, weight=0.5)

        # Interest depth (if tracked)
        depth = profile.get("interest_depth", {})
        if isinstance(depth, str):
            import json
            depth = json.loads(depth)
        if depth:
            avg_depth = sum(depth.values()) / max(len(depth), 1)
            state.passion.add("interest_depth", "Interest exploration depth", min(avg_depth, 1.0), weight=1.5)

        # Session engagement (more sessions = more invested)
        sessions = profile.get("sessions_completed", 0)
        engagement = min(sessions / 20.0, 1.0)  # 20 sessions = full engagement signal
        state.passion.add("engagement", "Session commitment", engagement, weight=1.0)

    # ── Domain: Talent (what you're good at) ──────────────────

    def _compute_talent(
        self, state: IkigaiState, mastery: list[dict], competencies: list[dict]
    ):
        """Score based on mastered skills and demonstrated competencies."""
        # Mastered skills
        mastered = [m for m in mastery if m.get("mastered")]
        total_skills = max(len(mastery), 1)

        if mastered:
            mastery_ratio = len(mastered) / total_skills
            state.talent.add("mastery_ratio", f"{len(mastered)} skills mastered", mastery_ratio, weight=2.5)

        # Overall accuracy
        total_attempts = sum(m.get("total_attempts", 0) for m in mastery)
        total_correct = sum(m.get("total_correct", 0) for m in mastery)
        if total_attempts > 0:
            accuracy = total_correct / total_attempts
            state.talent.add("accuracy", f"{accuracy:.0%} accuracy", accuracy, weight=1.5)

        # Competency strengths
        if competencies:
            strong = [c for c in competencies if c.get("strength", 0) >= 0.6]
            comp_score = len(strong) / max(len(competencies), 1)
            state.talent.add("competencies", f"{len(strong)} strong competencies", comp_score, weight=2.0)

            # Top competency
            if strong:
                best = max(strong, key=lambda c: c.get("strength", 0))
                state.talent.add(
                    "top_competency",
                    best.get("competency", "").replace("_", " ").title(),
                    best.get("strength", 0),
                    weight=0.5,
                )

        # Skill breadth (subjects attempted)
        subjects = set()
        for m in mastery:
            skill = m.get("skill_id", "")
            if "." in skill:
                subjects.add(skill.split(".")[0])
        if subjects:
            breadth = min(len(subjects) / 4.0, 1.0)  # 4 subjects = full breadth
            state.talent.add("breadth", f"{len(subjects)} subject areas", breadth, weight=1.0)

    # ── Domain: Mission (what the world needs) ────────────────

    def _compute_mission(
        self, state: IkigaiState, competencies: list[dict], work_profile: dict
    ):
        """Score based on alignment with market needs and social impact.

        Without external career data, we approximate from:
        - Employment competency coverage (the 12 skills employers want)
        - Career goal clarity (has the learner identified a direction?)
        - Transferable skills identified
        """
        # Employment competency coverage
        if competencies:
            covered = len([c for c in competencies if c.get("strength", 0) > 0.3])
            coverage = covered / 12.0  # 12 total employment competencies
            state.mission.add("competency_coverage", f"{covered}/12 employment skills", coverage, weight=2.0)

        # Career goal clarity
        if work_profile:
            has_field = bool(work_profile.get("desired_field"))
            has_interests = bool(work_profile.get("fields_of_interest"))
            intake_done = work_profile.get("intake_complete", False)

            if intake_done:
                state.mission.add("intake", "Career intake complete", 1.0, weight=1.0)
            if has_field:
                state.mission.add("career_goal", work_profile["desired_field"], 0.9, weight=1.5)
            elif has_interests:
                fields = work_profile.get("fields_of_interest", [])
                state.mission.add("exploring", f"Exploring {len(fields)} fields", 0.5, weight=1.0)

            # Transferable skills
            transferable = work_profile.get("transferable_skills", [])
            if isinstance(transferable, str):
                import json
                transferable = json.loads(transferable)
            if transferable:
                t_score = min(len(transferable) / 5.0, 1.0)
                state.mission.add("transferable", f"{len(transferable)} transferable skills", t_score, weight=1.5)

        # Baseline: if no work profile, give a small credit for being on the platform
        if not work_profile and not competencies:
            state.mission.add("baseline", "Journey started", 0.1, weight=0.5)

    # ── Domain: Vocation (what you can be paid for) ───────────

    def _compute_vocation(
        self, state: IkigaiState, mastery: list[dict],
        work_profile: dict, profile: dict,
    ):
        """Score based on earning potential and career readiness.

        Approximated from:
        - Program progress (closer to completion = closer to employability)
        - Work experience (existing foundation)
        - Skill-to-career alignment (do their skills match their goals?)
        - Resume readiness
        """
        # Program progress: ratio of mastered to total skills
        mastered = [m for m in mastery if m.get("mastered")]
        total = max(len(mastery), 1)
        if mastery:
            progress = len(mastered) / total
            state.vocation.add("program_progress", f"{len(mastered)}/{total} skills complete", progress, weight=2.0)

        # Work experience
        if work_profile:
            years = work_profile.get("total_years_experience", 0)
            exp_score = min(years / 5.0, 1.0)  # 5+ years = full credit
            if years > 0:
                state.vocation.add("experience", f"{years:.0f} years experience", exp_score, weight=1.5)

            # Resume readiness
            has_resume = bool(work_profile.get("resume_raw_text"))
            if has_resume:
                state.vocation.add("resume", "Resume on file", 0.8, weight=1.0)

            # Salary trajectory
            current = work_profile.get("salary_current", 0)
            target = work_profile.get("salary_target", 0)
            if target > 0 and current > 0:
                gap_ratio = current / target
                state.vocation.add("salary_progress", f"${current:,} → ${target:,} target", min(gap_ratio, 1.0), weight=1.0)
            elif target > 0:
                state.vocation.add("salary_goal", f"${target:,} target", 0.3, weight=0.5)

            # Certifications
            certs = work_profile.get("certifications", [])
            if isinstance(certs, str):
                import json
                certs = json.loads(certs)
            if certs:
                state.vocation.add("certifications", f"{len(certs)} certifications", min(len(certs) / 3.0, 1.0), weight=1.0)

        # XP as a proxy for overall platform investment
        xp = profile.get("xp_total", 0)
        if xp > 0:
            xp_score = min(xp / 500.0, 1.0)
            state.vocation.add("platform_xp", f"{xp} XP earned", xp_score, weight=0.5)

    # ── Data loading ──────────────────────────────────────────

    async def _load_profile(self, learner_id: str) -> dict:
        result = await asyncio.to_thread(
            lambda: db.client.table("learner_profiles")
            .select("*")
            .eq("learner_id", learner_id)
            .maybe_single()
            .execute()
        )
        return result.data or {}

    async def _load_mastery(self, learner_id: str) -> list[dict]:
        result = await asyncio.to_thread(
            lambda: db.client.table("learner_mastery")
            .select("*")
            .eq("learner_id", learner_id)
            .execute()
        )
        return result.data or []

    async def _load_competencies(self, learner_id: str) -> list[dict]:
        result = await asyncio.to_thread(
            lambda: db.client.table("learner_competencies")
            .select("*")
            .eq("learner_id", learner_id)
            .execute()
        )
        return result.data or []

    async def _load_work_profile(self, learner_id: str) -> dict:
        result = await asyncio.to_thread(
            lambda: db.client.table("work_profiles")
            .select("*")
            .eq("learner_id", learner_id)
            .maybe_single()
            .execute()
        )
        return result.data or {}