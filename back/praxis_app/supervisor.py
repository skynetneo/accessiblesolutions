"""Praxis supervisor agent composition."""

from __future__ import annotations

from typing import Any, Callable, cast

try:
    from deepagents.graph import create_deep_agent
except ImportError:  # pragma: no cover - compatibility only
    from deepagents import create_deep_agent  # type: ignore

from praxis_app.career import build_career_subagent
from praxis_app.learning import build_learning_agent, build_learning_subagent
from praxis_app.resources import build_resources_subagent


SUPERVISOR_SYSTEM_PROMPT = """You are Sol.

You are a fast router and light responder. The frontend sees only you, but you
should delegate real work to the correct subagent.

ROUTING:
- Learning, GED, lesson, assessment, placement, onboarding, practice, quiz,
  progress, coaching, skill mastery -> delegate to learning.
- Jobs, resume, cover letter, interview, applications, career planning ->
  delegate to access_career and navigate to the career page when useful.
- Food, shelter, housing, eviction, legal aid, SNAP, utilities, medical, DV,
  clinics, local resources -> delegate to access_fyndr and navigate to AccessFyndr
  or the map/resources page when useful.
- show map, donate, about, home, dashboard, career, learning -> use navigate_to_page.
- General questions -> answer briefly yourself.

Keep routing invisible. Do not explain the internal agent architecture to users.
Do not run learning middleware logic at the supervisor level.
"""


def build_praxis_supervisor(
    *,
    name: str,
    learning_name: str,
    routing_model: Any,
    learning_model: Any,
    career_model: Any,
    assessment_team: Any,
    coaching_team: Any,
    session_manager: Any,
    gamification_engine: Any,
    navigate_to_page: Any,
    resource_tools: list[Any],
    web_search_tool: Any = None,
    safe_middleware_factory: Callable[[], Any],
    checkpointer: Any = None,
    backend_factory: Callable[[Any], Any] | None = None,
):
    """Build the main Praxis supervisor and team-backed subagents."""

    learning_agent = build_learning_agent(
        model=learning_model,
        assessment_team=assessment_team,
        coaching_team=coaching_team,
        session_manager=session_manager,
        gamification_engine=gamification_engine,
        safe_middleware_factory=safe_middleware_factory,
        checkpointer=checkpointer,
    )
    learning_subagent = build_learning_subagent(
        name=learning_name,
        model=learning_model,
        learning_agent=learning_agent,
        safe_middleware_factory=safe_middleware_factory,
    )
    career_subagent = build_career_subagent(
        model=career_model,
        checkpointer=checkpointer,
        safe_middleware_factory=safe_middleware_factory,
    )
    resources_subagent = build_resources_subagent(
        model=routing_model,
        resource_tools=resource_tools,
        web_search_tool=web_search_tool,
        safe_middleware_factory=safe_middleware_factory,
    )

    supervisor_tools: list[Any] = [navigate_to_page]
    if web_search_tool is not None:
        supervisor_tools.append(web_search_tool)

    kwargs: dict[str, Any] = {}
    if backend_factory is not None:
        kwargs["backend"] = backend_factory

    return create_deep_agent(
        name=name,
        model=routing_model,
        tools=supervisor_tools,
        subagents=cast(Any, [learning_subagent, career_subagent, resources_subagent]),
        middleware=cast(Any, [safe_middleware_factory()]),
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        **kwargs,
    )
