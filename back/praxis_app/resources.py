"""Resource-navigation agent adapter for Praxis."""

from __future__ import annotations

from typing import Any, Callable, cast

from deepagents.middleware.subagents import SubAgent


def build_resources_subagent(
    *,
    model: Any,
    resource_tools: list[Any],
    web_search_tool: Any = None,
    safe_middleware_factory: Callable[[], Any],
) -> SubAgent:
    """Build the AccessFyndr/resource-navigation subagent."""

    tools = list(resource_tools)
    if web_search_tool is not None:
        tools.append(web_search_tool)

    return {
        "name": "access_fyndr",
        "description": (
            "Specialist for finding housing, food, legal aid, SNAP, utilities, "
            "medical, DV, and other local/community resources."
        ),
        "system_prompt": (
            "You are Sol, a practical case-work resource specialist.\n\n"
            "DECISION TREE:\n"
            "1. If the user describes a stressful life situation such as lost job, "
            "can't afford food, eviction, no power, DV, or medical need, first call "
            "recommend_assistance with the matching key: food_insecurity, lost_job, "
            "eviction_risk, domestic_violence, utilities, or medical.\n"
            "2. Then call find_agencies with the suggested search_query plus the "
            "user's location when available.\n"
            "3. If the user is simply filtering, such as 'food pantries near me' or "
            "'legal aid in 97401', call filter_agencies directly.\n"
            "4. If the location is outside Lane County, Oregon, use web search if "
            "available and then save_agencies to populate the map.\n\n"
            "Always summarize results with name, distance when known, fees, language "
            "support when known, and what the agency offers."
        ),
        "tools": tools,
        "model": model,
        "middleware": cast(Any, [safe_middleware_factory()]),
    }
