"""Learning agent composition for Praxis."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, Callable, cast

from langchain.tools import ToolRuntime, tool
from langchain_core.tools import InjectedToolArg

try:
    from deepagents.graph import create_deep_agent
except ImportError:  # pragma: no cover - compatibility only
    from deepagents import create_deep_agent  # type: ignore

from deepagents.middleware.subagents import SubAgent
from db.tools_bridge import LearnerContext
from middleware.core import (
    EmploymentStructuralMiddleware,
    MicroThemingMiddleware,
    StealthAssessmentMiddleware,
    ZPDMiddleware,
)
from orchestration.momentum import ItemType
from orchestration.session_manager import SessionManager, SessionPhase
from teams.gamification import GamificationEngine


MISSING_LEARNER_CONTEXT_MESSAGE = (
    "I need a learner session before I can personalize lessons or save progress. "
    "Please log in or complete onboarding, then try again."
)

LEARNING_SYSTEM_PROMPT = """You are the Sol Learning Agent.

You handle only learning-session work: onboarding, placement, coaching, practice,
scaffolding, progress checks, and session wrap-up.

PRINCIPLES:
1. Personalize every interaction to the learner's interests, level, and goals.
2. Assessment is stealth: the learner should not feel tested.
3. Employment readiness is structural and woven into learning, not a separate module.
4. Scaffolding follows ABA principles with systematic prompt fading.
5. Never serve unvalidated curriculum content.
6. Keep the tone adult-appropriate, warm, direct, and practical.

FLOW:
- Use start_learning_session for explicit learning, onboarding, placement, practice,
  lesson, or progress-tracked requests.
- For onboarding, collect interests, learning preferences, and goals conversationally.
- Use assessment_session for onboarding and placement.
- For placement, run adaptive assessment lightly and keep it short.
- For learning, use coaching_session to deliver the lesson.
- At session end, use wrap_up_session.

BOUNDARIES:
- Do not handle resumes, job searches, cover letters, public resource searches,
  food, shelter, housing, legal aid, clinics, or general site navigation.
- If the user asks for those, return a concise handoff note so the supervisor can
  route to the correct subagent.
"""

InjectedLearnerRuntime = Annotated[ToolRuntime[LearnerContext], InjectedToolArg]


def _item_type_from_state(value: Any) -> ItemType:
    try:
        return ItemType(str(value or "target"))
    except ValueError:
        return ItemType.TARGET


def _get_runtime_context(runtime: ToolRuntime[LearnerContext] | None) -> LearnerContext | None:
    context = getattr(runtime, "context", None)
    learner_id = getattr(context, "learner_id", None)
    if isinstance(learner_id, str) and learner_id.strip():
        return cast(LearnerContext, context)
    return None


def build_learning_agent(
    *,
    model: Any,
    assessment_team: Any,
    coaching_team: Any,
    session_manager: SessionManager,
    gamification_engine: GamificationEngine,
    safe_middleware_factory: Callable[[], Any],
    checkpointer: Any = None,
):
    """Build the learning deep agent that owns session flow."""

    @tool("start_learning_session")
    async def start_learning_session(runtime: InjectedLearnerRuntime) -> str:
        """Initialize a learning session for the current learner."""
        context = _get_runtime_context(runtime)
        if context is None:
            return MISSING_LEARNER_CONTEXT_MESSAGE

        session = await session_manager.start_session(
            learner_id=context.learner_id,
            session_id=context.session_id,
        )

        if session.phase == SessionPhase.ONBOARDING:
            return (
                "NEW LEARNER detected. Start onboarding:\n"
                "1. Welcome them warmly. This is not school; it is their personal path.\n"
                "2. Ask what they are interested in for theming.\n"
                "3. Ask how they like to learn: visual, reading, doing, audio, mixed.\n"
                "4. Ask what brought them here: GED, job skills, both, or another goal.\n"
                "5. Keep it under 5 minutes, then hand off to placement.\n"
                "Use assessment_session with current_step='interest_harvest'."
            )

        if session.phase == SessionPhase.PLACEMENT:
            return (
                "Learner needs PLACEMENT assessment.\n"
                "Use adaptive questions to estimate their skill level per subject.\n"
                "Start with medium difficulty and adjust based on responses.\n"
                "15 items max. Use assessment_session with current_step='placement'."
            )

        if session.phase == SessionPhase.LEARNING and session.lesson_plan:
            plan = session.lesson_plan
            next_item = session_manager.get_next_item_spec(session)
            targets = [
                f"  - {t['skill_id']} step {t['chain_step']} (level {t['prompt_level']})"
                for t in plan.target_skills
            ]
            next_item_text = ""
            if next_item:
                next_item_text = (
                    "\nNext item spec: "
                    f"{next_item['skill_id']} step {next_item['chain_step']} "
                    f"({next_item['item_type']}, prompt level {next_item['prompt_level']})\n"
                )
            return (
                "RETURNING LEARNER - session planned.\n"
                "Phase: LEARNING\n"
                f"Ratio: {plan.initial_ratio:.0%} mastered / {1 - plan.initial_ratio:.0%} target\n"
                "Target skills:\n"
                + "\n".join(targets)
                + "\n"
                f"Mastered pool: {len(plan.mastered_pool)} items\n"
                f"Reviews due: {len(plan.review_items)} items\n"
                f"Competency focus: {', '.join(plan.competency_focus)}\n"
                f"Estimated items: {plan.estimated_items}\n"
                f"Session length: {plan.estimated_duration_minutes} minutes\n\n"
                f"{next_item_text}"
                "Use coaching_session to begin teaching."
            )

        return "Session initialized. Ready to begin."

    @tool("coaching_session")
    async def run_coaching_session(
        message: str,
        current_step: str = "teaching",
        *,
        runtime: InjectedLearnerRuntime,
    ) -> str:
        """Run an interactive coaching interaction through the coaching team."""
        context = _get_runtime_context(runtime)
        if context is None:
            return MISSING_LEARNER_CONTEXT_MESSAGE

        result = await asyncio.to_thread(
            lambda: cast(Any, coaching_team).invoke(
                {
                    "messages": [{"role": "user", "content": message}],
                    "current_step": current_step,
                },
                config={"configurable": {"thread_id": f"coaching_{context.session_id}"}},
                context=LearnerContext(
                    learner_id=context.learner_id,
                    session_id=context.session_id,
                ),
            )
        )

        session = session_manager.get_active_session(
            learner_id=context.learner_id,
            session_id=context.session_id,
        )
        correct = result.get("last_response_correct")
        if session is not None and isinstance(correct, bool):
            await session_manager.advance(
                session=session,
                item_type=_item_type_from_state(result.get("last_item_type")),
                correct=correct,
            )

        events = result.get("gamification_events", [])
        if session is not None and isinstance(events, list):
            new_events = events[session.gamification_events_processed :]
            if new_events:
                await gamification_engine.process_events(context.learner_id, new_events)
                session.gamification_events_processed = len(events)

        messages = result.get("messages", [])
        if messages:
            last = messages[-1]
            return last.content if hasattr(last, "content") else str(last)
        return "Coaching session active."

    @tool("assessment_session")
    async def run_assessment_session(
        message: str,
        current_step: str = "interest_harvest",
        *,
        runtime: InjectedLearnerRuntime,
    ) -> str:
        """Run onboarding and placement interactions through the assessment team."""
        context = _get_runtime_context(runtime)
        if context is None:
            return MISSING_LEARNER_CONTEXT_MESSAGE

        result = await asyncio.to_thread(
            lambda: cast(Any, assessment_team).invoke(
                input={
                    "messages": [{"role": "user", "content": message}],
                    "current_step": current_step,
                },
                config={"configurable": {"thread_id": f"assessment_{context.session_id}"}},
                context=LearnerContext(
                    learner_id=context.learner_id,
                    session_id=context.session_id,
                ),
            )
        )

        session = session_manager.get_active_session(
            learner_id=context.learner_id,
            session_id=context.session_id,
        )
        current_step_result = result.get("current_step")
        if session is not None:
            if session.phase == SessionPhase.ONBOARDING and current_step_result == "placement":
                await session_manager.post_onboarding(session)
            elif current_step_result == "complete":
                placement_results = result.get("placement_results", {})
                if isinstance(placement_results, dict) and placement_results:
                    await session_manager.post_placement(session, placement_results)

        messages = result.get("messages", [])
        if messages:
            last = messages[-1]
            return last.content if hasattr(last, "content") else str(last)
        return "Assessment session active."

    @tool("wrap_up_session")
    async def wrap_up_session(runtime: InjectedLearnerRuntime) -> str:
        """End the current learning session and save progress."""
        context = _get_runtime_context(runtime)
        if context is None:
            return MISSING_LEARNER_CONTEXT_MESSAGE

        session = session_manager.get_active_session(
            learner_id=context.learner_id,
            session_id=context.session_id,
        )
        if session is None:
            return "No active session found to wrap up."

        summary = await session_manager.wrap_up(session)
        next_up = summary.get("next_up", [])
        next_preview = ""
        if next_up:
            next_preview = "\n\nComing up next:\n" + "\n".join(
                f"  -> {n['skill_id']} step {n['step']}: {n.get('description', '')}"
                for n in next_up
            )

        return (
            "Session complete!\n"
            f"Duration: {summary.get('duration_minutes', 0)} minutes\n"
            f"Items completed: {summary.get('items_completed', 0)}\n"
            f"Skills mastered (total): {summary.get('skills_mastered_total', 0)}\n"
            f"Competencies practiced: {', '.join(summary.get('competency_focus', []))}"
            f"{next_preview}"
        )

    return create_deep_agent(
        name="learning",
        model=model,
        tools=[
            start_learning_session,
            run_assessment_session,
            run_coaching_session,
            wrap_up_session,
        ],
        middleware=cast(
            Any,
            [
                safe_middleware_factory(),
                EmploymentStructuralMiddleware(),
                MicroThemingMiddleware(),
                ZPDMiddleware(),
                StealthAssessmentMiddleware(),
            ],
        ),
        system_prompt=LEARNING_SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


def build_learning_subagent(
    *,
    model: Any,
    learning_agent: Any,
    safe_middleware_factory: Callable[[], Any],
    name: str = "learning",
) -> SubAgent:
    """Expose the learning deep agent as a supervisor-routable subagent."""

    @tool("learning_session", description="Run Praxis learning, onboarding, placement, coaching, or wrap-up.")
    async def learning_session(
        message: str,
        runtime: InjectedLearnerRuntime,
    ) -> str:
        context = _get_runtime_context(runtime)
        if context is None:
            return MISSING_LEARNER_CONTEXT_MESSAGE

        result = await asyncio.to_thread(
            lambda: cast(Any, learning_agent).invoke(
                {"messages": [{"role": "user", "content": message}]},
                config={"configurable": {"thread_id": f"learning_{context.session_id}"}},
                context=context,
            )
        )
        messages = result.get("messages", [])
        if messages:
            last = messages[-1]
            return last.content if hasattr(last, "content") else str(last)
        return "Learning session active."

    return {
        "name": name,
        "description": (
            "Handles learner onboarding, placement assessment, adaptive lessons, "
            "coaching, scaffolded practice, progress tracking, and session wrap-up."
        ),
        "system_prompt": (
            "You are the learning router inside Praxis. Forward all learning, "
            "onboarding, placement, coaching, practice, and wrap-up requests to "
            "learning_session. Do not handle career services or resource searches."
        ),
        "tools": [learning_session],
        "model": model,
        "middleware": cast(Any, [safe_middleware_factory()]),
    }
