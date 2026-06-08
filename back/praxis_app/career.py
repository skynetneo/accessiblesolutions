"""Career agent adapter for Praxis."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, Callable, cast

from langchain.tools import ToolRuntime, tool
from langchain_core.tools import InjectedToolArg

from deepagents.middleware.subagents import SubAgent
from db.tools_bridge import LearnerContext
from teams.employment_services import build_employment_services_team


InjectedCareerRuntime = Annotated[ToolRuntime[LearnerContext], InjectedToolArg]


def _get_runtime_context(runtime: ToolRuntime[LearnerContext] | None) -> LearnerContext | None:
    context = getattr(runtime, "context", None)
    learner_id = getattr(context, "learner_id", None)
    if isinstance(learner_id, str) and learner_id.strip():
        return cast(LearnerContext, context)
    return None


def build_career_subagent(
    *,
    model: Any,
    checkpointer: Any = None,
    safe_middleware_factory: Callable[[], Any],
) -> SubAgent:
    """Build access_career as an adapter over the employment-services team."""

    employment_team = build_employment_services_team(checkpointer=checkpointer)

    @tool("employment_services", description="Run resume, interview, job search, or career intake services.")
    async def employment_services(
        message: str,
        runtime: InjectedCareerRuntime,
    ) -> str:
        context = _get_runtime_context(runtime)
        if context is None:
            return (
                "I need a learner session before I can personalize career services "
                "or save career artifacts."
            )

        result = await asyncio.to_thread(
            lambda: cast(Any, employment_team).invoke(
                {"messages": [{"role": "user", "content": message}]},
                config={
                    "configurable": {
                        "thread_id": f"employment_services_{context.learner_id}_{context.session_id or 'default'}"
                    }
                },
                context=context,
            )
        )
        messages = result.get("messages", [])
        if messages:
            last = messages[-1]
            return last.content if hasattr(last, "content") else str(last)
        return "Career services session active."

    return {
        "name": "access_career",
        "description": "Specialist for jobs, resumes, cover letters, and interview preparation.",
        "system_prompt": (
            "You are the Praxis career adapter. Delegate all resume, cover letter, "
            "interview, job search, and career-planning work to employment_services. "
            "Career artifacts must use real profile data only; never invent "
            "employers, dates, certifications, salaries, degrees, or equipment experience."
        ),
        "tools": [employment_services],
        "model": model,
        "middleware": cast(Any, [safe_middleware_factory()]),
    }
