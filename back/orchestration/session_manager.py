"""
praxis/orchestration/session_manager.py

Session lifecycle state machine.

This is the entry point for every learner interaction. It determines:
  - Is this a new learner? → Route to onboarding/assessment
  - Returning with an interrupted session? → Resume from checkpoint
  - Returning after completing last session? → Plan a new lesson
  - Approaching session time limit? → Graceful wind-down
  - Time for employment services? → Periodic injection

The session manager does NOT handle individual item delivery (that's the
coaching team). It orchestrates the higher-level flow: what phase are we in,
what does the lesson plan look like, and when do we transition.

Usage:
    from orchestration.session_manager import SessionManager, SessionPhase

    manager = SessionManager()
    session = await manager.start_session(learner_id="abc123")

    # The session object tells the master orchestrator what to do
    print(session.phase)        # → SessionPhase.LEARNING
    print(session.lesson_plan)  # → LessonPlan(...)
    print(session.momentum)     # → MomentumState(ratio=0.7, ...)
"""

from __future__ import annotations

import asyncio
import time
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from curriculum.skill_graph import SkillGraph
from orchestration.lesson_sequencer import LessonSequencer, LessonPlan
from orchestration.momentum import (
    MomentumCalculator,
    MomentumState,
    ItemType,
)
from db.client import db


# ──────────────────────────────────────────────────────────────
# Session phases
# ──────────────────────────────────────────────────────────────

class SessionPhase(str, Enum):
    """What phase the session is currently in."""
    ONBOARDING = "onboarding"          # First-time learner: collect preferences
    PLACEMENT = "placement"            # CAT-based initial assessment
    LEARNING = "learning"              # Active learning loop (most time spent here)
    REVIEW = "review"                  # Focused spaced retrieval review
    EMPLOYMENT = "employment"          # Employment services interaction
    WRAP_UP = "wrap_up"                # Session ending: save progress, preview next
    RESUMING = "resuming"              # Resuming an interrupted session


# ──────────────────────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────────────────────

@dataclass
class Session:
    """Complete session state passed to the master orchestrator."""
    learner_id: str
    session_id: str
    phase: SessionPhase

    # Lesson plan (None during onboarding/placement)
    lesson_plan: Optional[LessonPlan] = None

    # Momentum state (live, updated after every item)
    momentum: Optional[MomentumState] = None

    # Timing
    started_at: float = 0.0
    session_length_minutes: int = 20
    items_completed: int = 0
    gamification_events_processed: int = 0

    # Profile snapshot for this session
    profile: dict = field(default_factory=dict)

    # Context for the coaching team
    current_target: Optional[dict] = None     # which target skill we're currently on
    current_item_type: Optional[str] = None   # "mastered", "target", "review"

    # Flags
    is_new_learner: bool = False
    needs_placement: bool = False
    employment_injected_this_session: bool = False

    @property
    def elapsed_minutes(self) -> float:
        if self.started_at == 0:
            return 0.0
        return (time.time() - self.started_at) / 60

    @property
    def time_remaining_minutes(self) -> float:
        return max(0, self.session_length_minutes - self.elapsed_minutes)

    @property
    def should_wrap_up(self) -> bool:
        """True if we're within 2 minutes of the time limit."""
        return self.time_remaining_minutes <= 2.0

    @property
    def should_inject_employment(self) -> bool:
        """Inject employment services every 3rd session, after item 10."""
        if self.employment_injected_this_session:
            return False
        sessions_completed = self.profile.get("sessions_completed", 0)
        return (
            sessions_completed > 0
            and sessions_completed % 3 == 0
            and self.items_completed >= 10
        )


# ──────────────────────────────────────────────────────────────
# Session Manager
# ──────────────────────────────────────────────────────────────

class SessionManager:
    """
    Manages the session lifecycle from start to finish.

    The master orchestrator calls start_session() at the beginning of
    every interaction. Based on the returned Session, it routes to
    the appropriate team (onboarding → assessment, learning → coaching,
    etc.).

    During the session, advance() is called after each item to determine
    what happens next: another item, phase transition, or wrap-up.
    """

    def __init__(
        self,
        skill_graph: Optional[SkillGraph] = None,
        sequencer: Optional[LessonSequencer] = None,
        momentum: Optional[MomentumCalculator] = None,
    ):
        self.skill_graph = skill_graph
        self.sequencer = sequencer
        self.momentum = momentum or MomentumCalculator()
        self._active_sessions: dict[tuple[str, str], Session] = {}

    async def _ensure_deps(self):
        """Lazy-load the skill graph and sequencer."""
        if self.skill_graph is None:
            self.skill_graph = await SkillGraph.build_from_db()
        if self.sequencer is None:
            self.sequencer = LessonSequencer(
                skill_graph=self.skill_graph,
                momentum=self.momentum,
            )

    def _session_key(self, learner_id: str, session_id: str) -> tuple[str, str]:
        return learner_id, session_id

    def _store_session(self, session: Session) -> Session:
        self._active_sessions[self._session_key(session.learner_id, session.session_id)] = session
        return session

    def get_active_session(
        self,
        learner_id: str,
        session_id: Optional[str] = None,
    ) -> Optional[Session]:
        if session_id:
            return self._active_sessions.get(self._session_key(learner_id, session_id))

        learner_sessions = [
            session for (lid, _sid), session in self._active_sessions.items()
            if lid == learner_id
        ]
        if not learner_sessions:
            return None
        return max(learner_sessions, key=lambda session: session.started_at)

    def _discard_session(self, session: Session):
        self._active_sessions.pop(self._session_key(session.learner_id, session.session_id), None)

    # ── Start session ──────────────────────────────────────────

    async def start_session(
        self,
        learner_id: str,
        session_id: Optional[str] = None,
    ) -> Session:
        """Initialize a session for a learner.

        Determines the starting phase based on learner state:
        1. No profile → ONBOARDING (new learner)
        2. Profile exists, no mastery data → PLACEMENT (needs assessment)
        3. Profile + mastery data → LEARNING (returning learner)

        Args:
            learner_id: The learner
            session_id: Optional session ID (generated if not provided)

        Returns:
            Session object ready for the master orchestrator
        """
        await self._ensure_deps()

        if session_id is None:
            existing = self.get_active_session(learner_id=learner_id)
            if existing is not None:
                return existing

        if session_id is None:
            session_id = f"session_{int(time.time())}_{learner_id[:8]}"

        existing = self.get_active_session(learner_id=learner_id, session_id=session_id)
        if existing is not None:
            return existing

        # Load profile
        profile = await self._load_profile(learner_id)

        if not profile:
            # ── NEW LEARNER ──────────────────────────────────
            return self._store_session(Session(
                learner_id=learner_id,
                session_id=session_id,
                phase=SessionPhase.ONBOARDING,
                started_at=time.time(),
                is_new_learner=True,
                needs_placement=True,
                session_length_minutes=15,  # shorter for onboarding
            ))

        # Load mastery data
        mastery_data = await self._load_mastery(learner_id)

        session_minutes = profile.get("session_length_preference", 20)

        if not mastery_data and not self._has_placement_results(profile):
            # ── NEEDS PLACEMENT ──────────────────────────────
            return self._store_session(Session(
                learner_id=learner_id,
                session_id=session_id,
                phase=SessionPhase.PLACEMENT,
                started_at=time.time(),
                profile=profile,
                needs_placement=True,
                session_length_minutes=session_minutes,
            ))

        # ── RETURNING LEARNER → PLAN A LESSON ────────────────
        lesson_plan = await self.sequencer.plan_session(
            learner_id=learner_id,
            session_minutes=session_minutes,
        )

        momentum_state = MomentumState(
            ratio=lesson_plan.initial_ratio,
            review_items_due=len(lesson_plan.review_items),
        )

        # Pick the first target
        current_target = lesson_plan.target_skills[0] if lesson_plan.target_skills else None

        return self._store_session(Session(
            learner_id=learner_id,
            session_id=session_id,
            phase=SessionPhase.LEARNING,
            lesson_plan=lesson_plan,
            momentum=momentum_state,
            started_at=time.time(),
            session_length_minutes=session_minutes,
            profile=profile,
            current_target=current_target,
        ))

    # ── Advance (called after each item) ───────────────────────

    async def advance(
        self,
        session: Session,
        item_type: ItemType,
        correct: bool,
    ) -> Session:
        """Advance the session after a learner response.

        Updates momentum, checks for phase transitions, and determines
        what happens next.

        Args:
            session: Current session state
            item_type: What type of item was just completed
            correct: Whether the learner answered correctly

        Returns:
            Updated session (may have changed phase)
        """
        session.items_completed += 1

        # Update momentum
        if session.momentum:
            session.momentum = self.momentum.adjust_ratio(
                session.momentum, item_type, correct
            )

        # ── Check for phase transitions ──────────────────────

        # 1. Time limit → wrap up
        if session.should_wrap_up:
            session.phase = SessionPhase.WRAP_UP
            return session

        # 2. Item count reached → wrap up
        if session.lesson_plan and session.items_completed >= session.lesson_plan.estimated_items:
            session.phase = SessionPhase.WRAP_UP
            return session

        # 3. Employment injection check
        if session.should_inject_employment:
            session.phase = SessionPhase.EMPLOYMENT
            session.employment_injected_this_session = True
            return session

        # 4. Determine next item type
        if session.momentum:
            session.current_item_type = self.momentum.select_next_item_type(
                session.momentum
            ).value

        return session

    # ── Get next item details ──────────────────────────────────

    def get_next_item_spec(self, session: Session) -> Optional[dict]:
        """Get the specification for the next item to present.

        Based on momentum's item type selection and the lesson plan,
        returns a dict that the content team can use to generate
        or retrieve the item.

        Returns:
            Dict with skill_id, chain_step, item_type, prompt_level,
            or None if session should end.
        """
        if session.phase != SessionPhase.LEARNING:
            return None

        if not session.momentum or not session.lesson_plan:
            return None

        item_type = self.momentum.select_next_item_type(session.momentum)
        plan = session.lesson_plan

        if item_type == ItemType.TARGET:
            # Use current target skill
            if session.current_target:
                return {
                    "skill_id": session.current_target["skill_id"],
                    "chain_id": session.current_target.get("chain_id", ""),
                    "chain_step": session.current_target["chain_step"],
                    "item_type": "target",
                    "prompt_level": session.current_target.get("prompt_level", 3),
                }
            # No target available — fall back to mastered
            item_type = ItemType.MASTERED

        if item_type == ItemType.MASTERED:
            if plan.mastered_pool:
                # Round-robin through mastered pool
                idx = session.items_completed % len(plan.mastered_pool)
                item = plan.mastered_pool[idx]
                return {
                    "skill_id": item["skill_id"],
                    "chain_step": item["chain_step"],
                    "item_type": "mastered",
                    "prompt_level": 5,  # mastered items always at independent level
                }

        if item_type == ItemType.REVIEW:
            served = session.momentum.review_items_served if session.momentum else 0
            if served < len(plan.review_items):
                item = plan.review_items[served]
                return {
                    "skill_id": item["skill_id"],
                    "chain_step": item["chain_step"],
                    "item_type": "review",
                    "prompt_level": 5,  # reviews are always independent
                }

        return None

    # ── Wrap up ────────────────────────────────────────────────

    async def wrap_up(self, session: Session) -> dict:
        """Finalize a session. Save progress, calculate summary stats.

        Args:
            session: The session being ended

        Returns:
            Summary dict for the frontend and analytics
        """
        # Update learner profile with session data
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        profile_updates = {"updated_at": now}
        if session.items_completed > 0:
            profile_updates.update({
                "sessions_completed": session.profile.get("sessions_completed", 0) + 1,
                "last_session_at": now,
            })

        await asyncio.to_thread(
            lambda: db.client.table("learner_profiles")
            .update(profile_updates)
            .eq("learner_id", session.learner_id)
            .execute()
        )

        # Build summary
        momentum_summary = {}
        if session.momentum:
            momentum_summary = self.momentum.get_session_summary(session.momentum)

        # Get updated progress
        mastery_data = await self._load_mastery(session.learner_id)
        mastered_count = sum(1 for r in mastery_data if r.get("mastered"))

        summary = {
            "session_id": session.session_id,
            "learner_id": session.learner_id,
            "duration_minutes": round(session.elapsed_minutes, 1),
            "items_completed": session.items_completed,
            "momentum": momentum_summary,
            "skills_mastered_total": mastered_count,
            "competency_focus": session.lesson_plan.competency_focus if session.lesson_plan else [],
        }

        # Calculate what's coming next session (preview for the learner)
        if self.skill_graph:
            mastered_set = {
                f"{r['skill_id']}:{r['chain_step']}"
                for r in mastery_data if r.get("mastered")
            }
            next_teachable = self.skill_graph.get_next_teachable(mastered_set)
            summary["next_up"] = [
                {
                    "skill_id": n.skill_id,
                    "step": n.chain_step,
                    "description": n.step_description,
                }
                for n in next_teachable[:3]
            ]

        self._discard_session(session)
        return summary

    # ── Return to learning after employment injection ──────────

    async def return_from_employment(self, session: Session) -> Session:
        """Resume learning after an employment services interaction."""
        session.phase = SessionPhase.LEARNING
        return self._store_session(session)

    # ── After placement, start learning ────────────────────────

    async def post_placement(
        self,
        session: Session,
        placement_results: dict,
    ) -> Session:
        """Transition from placement to learning after CAT assessment.

        Args:
            session: Current session (in PLACEMENT phase)
            placement_results: Dict of skill_id → theta estimates from CAT

        Returns:
            Updated session now in LEARNING phase with a lesson plan
        """
        await self._ensure_deps()

        # Save placement results to profile
        await asyncio.to_thread(
            lambda: db.client.table("learner_profiles")
            .update({
                "skill_levels": json.dumps(placement_results),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            .eq("learner_id", session.learner_id)
            .execute()
        )

        # Plan first real lesson
        lesson_plan = await self.sequencer.plan_session(
            learner_id=session.learner_id,
            session_minutes=session.session_length_minutes,
        )

        session.phase = SessionPhase.LEARNING
        session.lesson_plan = lesson_plan
        session.momentum = MomentumState(
            ratio=lesson_plan.initial_ratio,
            review_items_due=len(lesson_plan.review_items),
        )
        session.current_target = (
            lesson_plan.target_skills[0] if lesson_plan.target_skills else None
        )
        session.needs_placement = False

        return self._store_session(session)

    # ── After onboarding, route to placement ───────────────────

    async def post_onboarding(self, session: Session) -> Session:
        """Transition from onboarding to placement."""
        session.phase = SessionPhase.PLACEMENT
        session.is_new_learner = False
        # Reload the freshly-created profile
        session.profile = await self._load_profile(session.learner_id) or {}
        return self._store_session(session)

    # ── Data loading helpers ───────────────────────────────────

    async def _load_profile(self, learner_id: str) -> Optional[dict]:
        result = await asyncio.to_thread(
            lambda: db.client.table("learner_profiles")
            .select("*")
            .eq("learner_id", learner_id)
            .maybe_single()
            .execute()
        )
        return result.data

    def _has_placement_results(self, profile: dict) -> bool:
        skill_levels = profile.get("skill_levels")
        if isinstance(skill_levels, str):
            try:
                skill_levels = json.loads(skill_levels)
            except json.JSONDecodeError:
                return False
        return isinstance(skill_levels, dict) and bool(skill_levels)

    async def _load_mastery(self, learner_id: str) -> list[dict]:
        result = await asyncio.to_thread(
            lambda: db.client.table("learner_mastery")
            .select("*")
            .eq("learner_id", learner_id)
            .execute()
        )
        return result.data or []
