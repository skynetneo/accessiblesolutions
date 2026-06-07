"""
praxis/orchestration/session_controller.py

Algorithmic session controller — the "game engine" layer.

Unifies all deterministic decisions into one place:
  - Fading/thickening (scaffold level adjustment)
  - Item selection (what to teach next)
  - Momentum management (mastered/target ratio)
  - Reinforcement scheduling (XP, badges)
  - Spaced retrieval (review timing)
  - Modality selection (audio/visual/interactive mix)
  - Session pacing (breaks, skill switches)

The LLM only handles:
  - Content generation (theming, narration, explanation)
  - Signal enrichment (reading emotional state, detecting misconceptions)

Two-tier LLM integration:
  - Tier 1 (Groq/Llama 3.3 70B): signal enrichment after every learner response.
  - Tier 2 (sonnet-4.6, gemini-3.1-pro): content generation.
"""

from __future__ import annotations

import json
import math
import random
import time
import asyncio
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Optional

from curriculum.skill_graph import SkillGraph
from orchestration.lesson_sequencer import LessonSequencer, LessonPlan
from orchestration.momentum import (
    MomentumCalculator,
    MomentumState,
    ItemType,
)
from scaffolding.fading import (
    FadingEngine,
    FadingDecision,
    FadingAction,
    AcquisitionProfile,
)
from scaffolding.mastery import MasteryEngine, MasteryStatus
from db.client import db


# ──────────────────────────────────────────────────────────────
# Data types
# ──────────────────────────────────────────────────────────────

class CoachingDirective(str, Enum):
    """What the LLM should do with this turn."""
    EXPLAIN = "explain"            # Teach a new concept
    PRACTICE = "practice"          # Present a practice item
    REVIEW = "review"              # Spaced retrieval probe
    ENCOURAGE = "encourage"        # Momentum boost (mastered item)
    SCAFFOLD = "scaffold"          # Re-explain with more support
    CHALLENGE = "challenge"        # Push beyond current level
    COOLDOWN = "cooldown"          # Session winding down
    CONVERSATION = "conversation"  # Free conversation (intake, check-in)


@dataclass
class TurnPlan:
    """The controller's complete decision for the next turn."""
    skill_id: str
    chain_step: int
    seed_item: dict                     
    item_type: ItemType                 

    scaffold_level: int                 
    directive: CoachingDirective        
    theme: str                          
    competency_focus: list[str]         

    modality_mix: dict = field(default_factory=lambda: {
        "narration": True,
        "highlighting": True,
        "animation": False,
        "interactive": False,
    })

    reinforcement: Optional[dict] = None   

    fading_decision: Optional[FadingDecision] = None
    acquisition_profile: AcquisitionProfile = AcquisitionProfile.STANDARD
    mastery_probability: float = 0.5
    turn_number: int = 0


@dataclass
class TurnPlanOverride:
    """LLM's structured request to modify the controller's plan.
    Restricted strictly to surface/environmental variables."""
    field: str                             # Only "theme" or "modality_mix"
    new_value: Any
    reason: str                            
    confidence: float = 0.5                


class EmotionalState(str, Enum):
    ENGAGED = "engaged"
    FRUSTRATED = "frustrated"
    CONFUSED = "confused"
    BORED = "bored"
    CONFIDENT = "confident"
    ANXIOUS = "anxious"


@dataclass
class LLMSignals:
    """Structured output from the Groq signal enrichment call."""
    correct: bool                          
    emotional_state: EmotionalState = EmotionalState.ENGAGED
    engagement_level: float = 0.7          
    misconception: Optional[str] = None    
    connection_made: Optional[str] = None  

    showed_understanding: bool = False     
    is_guessing: bool = False              
    needs_different_approach: bool = False 

    override: Optional[TurnPlanOverride] = None


@dataclass
class SessionState:
    """Complete state for an active learning session.
    Designed to be compatible with LangGraph state reducers."""
    learner_id: str
    session_id: str

    lesson_plan: LessonPlan = field(default_factory=LessonPlan)
    momentum: MomentumState = field(default_factory=MomentumState)

    turn_number: int = 0
    current_target_idx: int = 0            
    items_on_current_skill: int = 0        

    skill_levels: dict[str, int] = field(default_factory=dict)

    interests: list[str] = field(default_factory=list)
    modality_preference: str = "balanced"
    theta_estimates: dict[str, float] = field(default_factory=dict)

    started_at: float = 0.0
    max_duration_minutes: int = 20

    signal_history: list[LLMSignals] = field(default_factory=list)

    items_since_last_reinforcement: int = 0
    total_xp_awarded: int = 0

    # In-session cache: avoids redundant DB round-trips for the same skill/step
    mastery_cache: dict = field(default_factory=dict)


# ──────────────────────────────────────────────────────────────
# Controller
# ──────────────────────────────────────────────────────────────

class SessionController:
    """Algorithmic brain for the learning session."""

    def __init__(
        self,
        skill_graph: Optional[SkillGraph] = None,
    ):
        self.fading = FadingEngine()
        self.mastery = MasteryEngine()
        self.momentum_calc = MomentumCalculator()
        self.sequencer = LessonSequencer(
            skill_graph=skill_graph,
            momentum=self.momentum_calc,
        )

    # ── Session lifecycle ─────────────────────────────────────

    async def start_session(
        self,
        learner_id: str,
        session_id: str = "",
        subject: Optional[str] = None,
        session_minutes: int = 20,
    ) -> SessionState:
        plan = await self.sequencer.plan_session(
            learner_id=learner_id,
            subject=subject,
            session_minutes=session_minutes,
        )

        profile = await self._load_profile(learner_id)
        interests = profile.get("interests", [])
        modality = profile.get("modality_preference", "balanced")
        skill_levels_raw = profile.get("skill_levels", {})
        if isinstance(skill_levels_raw, str):
            skill_levels_raw = json.loads(skill_levels_raw)

        mastery_data = await self._load_mastery(learner_id)
        scaffold_levels = {}
        for row in mastery_data:
            key = row["skill_id"]
            scaffold_levels[key] = row.get("prompt_level", 3)

        momentum = MomentumState(
            ratio=plan.initial_ratio,
            review_items_due=len(plan.review_items),
        )

        return SessionState(
            learner_id=learner_id,
            session_id=session_id or f"s_{int(time.time())}",
            lesson_plan=plan,
            momentum=momentum,
            skill_levels=scaffold_levels,
            interests=interests,
            modality_preference=modality,
            theta_estimates=skill_levels_raw,
            started_at=time.time(),
            max_duration_minutes=session_minutes,
        )

    # ── Turn-by-turn decision ─────────────────────────────────

    async def next_turn(
        self,
        session: SessionState,
        signals: Optional[LLMSignals] = None,
    ) -> TurnPlan:
        """Produce the next TurnPlan asynchronously."""
        session.turn_number += 1

        if signals:
            session.signal_history.append(signals)
            if len(session.signal_history) > 10:
                session.signal_history = session.signal_history[-10:]

            self._apply_emotional_adjustments(session, signals)

        elapsed_min = (time.time() - session.started_at) / 60
        if elapsed_min >= session.max_duration_minutes - 2:
            return self._cooldown_plan(session)

        item_type = self.momentum_calc.select_next_item_type(session.momentum)
        
        # Async IO operation patched
        skill_id, chain_step, seed_item = await self._select_item(session, item_type)

        scaffold = session.skill_levels.get(skill_id, 3)
        directive = self._choose_directive(session, item_type, signals)
        theme = self._pick_theme(session)
        modality = self._compute_modality(session, scaffold, seed_item)
        reinforcement = self._check_reinforcement(session, signals)

        mastery_row = await self._get_mastery_row_cached(session, skill_id, chain_step)
        fade_history = mastery_row.get("fade_history", []) if mastery_row else []
        if isinstance(fade_history, str):
            fade_history = json.loads(fade_history)
        profile = self.fading._estimate_profile(fade_history)

        theta = session.theta_estimates.get(
            skill_id,
            session.theta_estimates.get(skill_id.split(".")[0], 0.0),
        )
        mastery_prob = FadingEngine.mastery_probability_from_theta(theta)

        plan = TurnPlan(
            skill_id=skill_id,
            chain_step=chain_step,
            seed_item=seed_item,
            item_type=item_type,
            scaffold_level=scaffold,
            directive=directive,
            theme=theme,
            competency_focus=session.lesson_plan.competency_focus,
            modality_mix=modality,
            reinforcement=reinforcement,
            acquisition_profile=profile,
            mastery_probability=mastery_prob,
            turn_number=session.turn_number,
        )

        if signals and signals.override:
            plan = self._apply_override(plan, signals.override)

        return plan

    # ── Record outcome (after learner responds) ───────────────

    async def record_outcome(
        self,
        session: SessionState,
        plan: TurnPlan,
        signals: LLMSignals,
    ) -> FadingDecision:
        correct = signals.correct

        mastery_row = await self._get_mastery_row_cached(
            session, plan.skill_id, plan.chain_step
        )
        fade_history = mastery_row.get("fade_history", []) if mastery_row else []
        if isinstance(fade_history, str):
            fade_history = json.loads(fade_history)

        response_quality = self._compute_quality(signals)

        theta = session.theta_estimates.get(
            plan.skill_id,
            session.theta_estimates.get(plan.skill_id.split(".")[0], 0.0),
        )
        mastery_prob = FadingEngine.mastery_probability_from_theta(theta)

        if mastery_row:
            consec_errors = 0 if correct else mastery_row.get("consecutive_errors", 0) + 1
        else:
            consec_errors = 0 if correct else 1

        decision = self.fading.evaluate(
            current_level=plan.scaffold_level,
            mastery_probability=mastery_prob,
            response_quality=response_quality,
            consecutive_errors=consec_errors,
            skill_id=plan.skill_id,
            fade_history=fade_history,
        )

        # Mutate the dictionary explicitly for LangGraph state reduction tracking
        session.skill_levels[plan.skill_id] = decision.new_level

        session.momentum = self.momentum_calc.adjust_ratio(
            session.momentum, plan.item_type, correct
        )

        session.items_on_current_skill += 1
        session.items_since_last_reinforcement += 1

        return decision

    # ── Signal enrichment ─────────────────────────────────────

    async def enrich_signals(
        self,
        learner_response: str,
        session: SessionState,
        current_plan: TurnPlan,
    ) -> LLMSignals:
        import httpx

        system_prompt = SIGNAL_ENRICHMENT_SYSTEM_PROMPT

        user_content = (
            f"<question>\n{current_plan.seed_item.get('question_text', '')}\n</question>\n"
            f"<correct_answer>{current_plan.seed_item.get('correct_answer', '')}</correct_answer>\n"
            f"<scaffold_level>{current_plan.scaffold_level}</scaffold_level>\n"
            f"<learner_context>\n"
            f"  interests: {session.interests}\n"
            f"  acquisition_profile: {current_plan.acquisition_profile.value}\n"
            f"  recent_emotions: {[s.emotional_state.value for s in session.signal_history[-3:]]}\n"
            f"</learner_context>\n"
            f"<learner_response>{learner_response}</learner_response>"
        )

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {_get_groq_api_key()}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 300,
                        "response_format": {"type": "json_object"},
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                text = data["choices"][0]["message"]["content"]
                parsed = json.loads(text)

                return LLMSignals(
                    correct=parsed.get("correct", False),
                    emotional_state=EmotionalState(parsed.get("emotional_state", "engaged")),
                    engagement_level=parsed.get("engagement_level", 0.7),
                    misconception=parsed.get("misconception"),
                    connection_made=parsed.get("connection_made"),
                    showed_understanding=parsed.get("showed_understanding", False),
                    is_guessing=parsed.get("is_guessing", False),
                    needs_different_approach=parsed.get("needs_different_approach", False),
                    override=self._parse_override(parsed.get("override")),
                )

        except Exception:
            return LLMSignals(
                correct=self._algorithmic_correctness_check(
                    learner_response, current_plan.seed_item
                ),
            )

    # ── Internal helpers ──────────────────────────────────────

    def _apply_emotional_adjustments(
        self, session: SessionState, signals: LLMSignals
    ):
        if signals.emotional_state == EmotionalState.FRUSTRATED:
            session.momentum.ratio = min(0.85, session.momentum.ratio + 0.10)
        elif signals.emotional_state == EmotionalState.BORED:
            session.momentum.ratio = max(0.15, session.momentum.ratio - 0.08)
        elif signals.emotional_state == EmotionalState.ANXIOUS:
            session.momentum.ratio = min(0.85, session.momentum.ratio + 0.05)

    async def _select_item(
        self,
        session: SessionState,
        item_type: ItemType,
    ) -> tuple[str, int, dict]:
        """Select the actual skill/item to present (Async implementation)."""
        plan = session.lesson_plan

        if item_type == ItemType.REVIEW and plan.review_items:
            item = plan.review_items[
                session.momentum.review_items_served % len(plan.review_items)
            ]
            seed = await self._fetch_seed_async(item["skill_id"], item["chain_step"])
            return item["skill_id"], item["chain_step"], seed

        if item_type == ItemType.MASTERED and plan.mastered_pool:
            item = random.choice(plan.mastered_pool)
            seed = await self._fetch_seed_async(item["skill_id"], item["chain_step"])
            return item["skill_id"], item["chain_step"], seed

        if plan.target_skills:
            idx = session.current_target_idx % len(plan.target_skills)
            target = plan.target_skills[idx]

            if session.items_on_current_skill >= 5:
                session.current_target_idx = (idx + 1) % len(plan.target_skills)
                session.items_on_current_skill = 0

            seed = await self._fetch_seed_async(target["skill_id"], target["chain_step"])
            return target["skill_id"], target["chain_step"], seed

        if plan.mastered_pool:
            item = plan.mastered_pool[0]
            seed = await self._fetch_seed_async(item["skill_id"], item["chain_step"])
            return item["skill_id"], item["chain_step"], seed

        return "", 0, {}

    def _choose_directive(
        self,
        session: SessionState,
        item_type: ItemType,
        signals: Optional[LLMSignals],
    ) -> CoachingDirective:
        if item_type == ItemType.MASTERED:
            return CoachingDirective.ENCOURAGE
        if item_type == ItemType.REVIEW:
            return CoachingDirective.REVIEW

        if signals and signals.needs_different_approach:
            return CoachingDirective.SCAFFOLD
        if signals and signals.emotional_state == EmotionalState.CONFIDENT:
            return CoachingDirective.CHALLENGE

        scaffold = session.skill_levels.get(
            session.lesson_plan.target_skills[
                session.current_target_idx % max(1, len(session.lesson_plan.target_skills))
            ]["skill_id"] if session.lesson_plan.target_skills else "",
            3,
        )

        if scaffold <= 2:
            return CoachingDirective.EXPLAIN
        return CoachingDirective.PRACTICE

    def _pick_theme(self, session: SessionState) -> str:
        if not session.interests:
            return ""
        idx = session.turn_number % len(session.interests)
        return session.interests[idx]

    def _compute_modality(
        self, session: SessionState, scaffold: int, seed_item: dict
    ) -> dict:
        pref = session.modality_preference
        has_animation = bool(seed_item.get("default_animation_template"))

        base = {
            "narration": pref in ("auditory", "balanced"),
            "highlighting": scaffold <= 3,
            "animation": has_animation and pref in ("visual", "balanced"),
            "interactive": pref == "kinesthetic" or scaffold >= 4,
        }

        if scaffold <= 2:
            base["narration"] = True
            base["highlighting"] = True
            if has_animation:
                base["animation"] = True

        return base

    def _check_reinforcement(
        self, session: SessionState, signals: Optional[LLMSignals]
    ) -> Optional[dict]:
        if session.items_since_last_reinforcement < 2:
            return None

        threshold = max(1, 3 + random.randint(-1, 1))
        if session.items_since_last_reinforcement < threshold:
            return None

        session.items_since_last_reinforcement = 0
        xp = 5 + (session.momentum.consecutive_target_correct * 2)

        if signals and signals.showed_understanding:
            xp += 3

        session.total_xp_awarded += xp

        return {
            "xp": xp,
            "total_xp": session.total_xp_awarded,
            "message": "reinforcement",
        }

    def _compute_quality(self, signals: LLMSignals) -> float:
        score = 0.5 

        if signals.showed_understanding:
            score += 0.25
        if signals.is_guessing:
            score -= 0.30 
        if signals.engagement_level > 0.7:
            score += 0.10
        if signals.emotional_state == EmotionalState.ENGAGED:
            score += 0.05
        if signals.needs_different_approach:
            score -= 0.15
        if signals.connection_made:
            score += 0.15 

        return max(0.0, min(1.0, score))

    def _apply_override(
        self, plan: TurnPlan, override: TurnPlanOverride
    ) -> TurnPlan:
        """Apply an LLM override strictly to safe environmental variables."""
        OVERRIDABLE = {"theme", "modality_mix"}
        
        if override.field not in OVERRIDABLE:
            return plan

        if override.confidence < 0.6:
            return plan

        try:
            setattr(plan, override.field, override.new_value)
            plan.fading_decision = FadingDecision(
                action=FadingAction.HOLD,
                new_level=plan.scaffold_level,
                reason=f"LLM aesthetic override: {override.reason}",
                confidence=override.confidence,
                profile_used=plan.acquisition_profile,
            )
        except (AttributeError, TypeError):
            pass

        return plan

    def _cooldown_plan(self, session: SessionState) -> TurnPlan:
        return TurnPlan(
            skill_id="",
            chain_step=0,
            seed_item={},
            item_type=ItemType.MASTERED,
            scaffold_level=5,
            directive=CoachingDirective.COOLDOWN,
            theme=self._pick_theme(session),
            competency_focus=[],
            turn_number=session.turn_number,
        )

    def _parse_override(self, raw: Optional[dict]) -> Optional[TurnPlanOverride]:
        if not raw or not isinstance(raw, dict):
            return None
        if not raw.get("field") or not raw.get("reason"):
            return None
        return TurnPlanOverride(
            field=raw["field"],
            new_value=raw.get("new_value"),
            reason=raw["reason"],
            confidence=raw.get("confidence", 0.5),
        )

    def _algorithmic_correctness_check(
        self, response: str, seed_item: dict
    ) -> bool:
        correct = seed_item.get("correct_answer", "").strip().lower()
        response_clean = response.strip().lower()
        if not correct:
            return False
        return (
            response_clean == correct
            or response_clean.startswith(correct)
            or correct in response_clean
        )

    async def _get_mastery_row_cached(
        self, session: SessionState, skill_id: str, chain_step: int
    ) -> Optional[dict]:
        key = (skill_id, chain_step)
        if key not in session.mastery_cache:
            try:
                result = await asyncio.to_thread(
                    lambda: db.client.table("learner_mastery")
                    .select("*")
                    .eq("learner_id", session.learner_id)
                    .eq("skill_id", skill_id)
                    .eq("chain_step", chain_step)
                    .maybe_single()
                    .execute()
                )
                session.mastery_cache[key] = result.data
            except Exception:
                session.mastery_cache[key] = None
        return session.mastery_cache[key]

    async def _fetch_seed_async(self, skill_id: str, chain_step: int) -> dict:
        """Fetch a seed item from Supabase asynchronously to prevent event loop blocking."""
        try:
            result = await asyncio.to_thread(
                lambda: db.client.table("seed_items")
                .select("*")
                .eq("skill_id", skill_id)
                .eq("chain_step", chain_step)
                .maybe_single()
                .execute()
            )
            return result.data or {}
        except Exception:
            return {}

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


# ──────────────────────────────────────────────────────────────
# Flash-lite signal enrichment prompt
# ──────────────────────────────────────────────────────────────

SIGNAL_ENRICHMENT_SYSTEM_PROMPT = """You are a learning signal analyzer. Given a learner's response to a question, extract structured signals. You MUST respond with valid JSON only, no other text.

JSON schema:
{
  "correct": boolean,
  "emotional_state": "engaged" | "frustrated" | "confused" | "bored" | "confident" | "anxious",
  "engagement_level": float 0-1,
  "showed_understanding": boolean,
  "is_guessing": boolean,
  "needs_different_approach": boolean,
  "misconception": string | null,
  "connection_made": string | null,
  "override": null | {
    "field": "theme" | "modality_mix",
    "new_value": any,
    "reason": string,
    "confidence": float 0-1
  }
}

Rules for each field:
- correct: Does the response match or demonstrate understanding of the correct answer? Be generous with phrasing but strict with concepts.
- emotional_state: Read tone, word choice, punctuation. "idk" = bored/disengaged. "I hate this" = frustrated. "wait, so..." = confused. "oh! so that means..." = engaged. Short terse answers may indicate frustration OR confidence — use context.
- engagement_level: 0 = completely checked out, 1 = deeply invested. Long thoughtful responses = high. One-word answers = low.
- showed_understanding: Did they EXPLAIN their reasoning, not just give an answer?
- is_guessing: Correct answer but no evidence of understanding.
- needs_different_approach: The learner seems stuck in a way that repeating the same explanation won't fix.
- misconception: If the response reveals a specific misunderstanding, describe it concisely. null if no clear misconception.
- connection_made: If the learner connects the material to their real life, job, or interests, capture it. null otherwise.
- override: ONLY suggest if you have HIGH confidence (>0.7) that the environmental/aesthetic variables (theme or modality) are wrong for THIS learner RIGHT NOW. Do not attempt to override structural pedagogy."""


def _get_groq_api_key() -> str:
    import os
    return os.environ.get("GROQ_API_KEY", "")