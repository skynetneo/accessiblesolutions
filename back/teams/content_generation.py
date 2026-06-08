"""
praxis/teams/content_generation.py

Content Generation Team.

Pattern: Orchestrator-worker (simplified to sequential for MVP,
parallelizable via Send API later).

Pipeline: seed_lookup → generate → validate → cache_or_regen → deliver

The content team takes an item spec from session_manager and returns
a validated, themed, employment-integrated learning item. It:
1. Fetches the seed item for the target skill/step
2. Checks the content cache for a pre-generated match
3. If miss: generates a themed variant using glm-5 (cheapest SOTA)
4. Validates via cross-provider (gemini-3.1-pro)
5. On fail: regeneration loop (max 3 attempts, then fallback to seed)
6. Caches the validated item
7. Returns the item to the coaching team

The content team is NOT conversational — it's invoked as a tool by the
master orchestrator and returns structured content.

Usage:
    from teams.content_generation import build_content_team

    team = build_content_team(checkpointer)
    result = team.invoke(
        {"messages": [{"role": "user", "content": json.dumps(item_spec)}]},
        context=LearnerContext(learner_id="abc", session_id="s1"),
    )
"""

from __future__ import annotations

import json
import os
from typing import Callable
from typing import Any, cast
from typing_extensions import NotRequired

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import (
    wrap_model_call,
    ModelRequest,
    ModelResponse,
)
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage, SystemMessage
from langgraph.types import Command

from db.client import db
from db.tools_bridge import LearnerContext
from model_factory import DEFAULT_BASE_MODEL, init_praxis_chat_model
from orchestration.validator import ContentValidator, RegenerationLoop


# ──────────────────────────────────────────────────────────────
# State
# ──────────────────────────────────────────────────────────────

class ContentState(AgentState):
    """State for the content generation agent."""
    current_seed: NotRequired[dict]
    generated_item: NotRequired[dict]
    validation_result: NotRequired[dict]
    learner_profile: NotRequired[dict]
    item_spec: NotRequired[dict]


# ──────────────────────────────────────────────────────────────
# Shared instances (initialized once)
# ──────────────────────────────────────────────────────────────

_validator = ContentValidator()
_generator = None
GENERATOR_MODEL = os.environ.get(
    "PRAXIS_CONTENT_MODEL",
    os.environ.get("UPSKILL_CONTENT_MODEL", DEFAULT_BASE_MODEL),
)


def _get_generator():
    global _generator
    if _generator is None:
        _generator = init_praxis_chat_model(GENERATOR_MODEL)
    return _generator


# ──────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────

@tool
def lookup_seed(
    skill_id: str,
    chain_step: int,
    runtime: ToolRuntime[LearnerContext, ContentState],
) -> Command:
    """Fetch the seed item for a given skill and chain step.

    Seeds are the structurally validated templates from the curriculum.
    They contain the correct answer, distractors, difficulty params,
    and the core pedagogical structure.

    Args:
        skill_id: The skill to generate content for
        chain_step: Which step in the skill's learning chain
    """
    result = db.client.table("seed_items") \
        .select("*") \
        .eq("skill_id", skill_id) \
        .eq("chain_step", chain_step) \
        .maybe_single() \
        .execute()

    seed = cast(dict[str, Any] | None, result.data if result else None)
    if not seed:
        return Command(update={
            "messages": [ToolMessage(
                content=f"No seed found for {skill_id} step {chain_step}. Cannot generate.",
                tool_call_id=runtime.tool_call_id,
            )],
        })

    return Command(update={
        "messages": [ToolMessage(
            content=f"Seed loaded: {seed.get('seed_id', 'unknown')}. Check cache or generate.",
            tool_call_id=runtime.tool_call_id,
        )],
        "current_seed": seed,
    })


@tool
def check_cache(
    skill_id: str,
    chain_step: int,
    runtime: ToolRuntime[LearnerContext, ContentState],
) -> Command:
    """Check if a validated, themed item already exists in the cache.

    Loads the cached item into state if found, or reports 'CACHE_MISS' if not.
    Cache lookup is always scoped to the authenticated runtime learner context.

    Args:
        skill_id: Skill to check
        chain_step: Chain step to check
    """
    learner_id = runtime.context.learner_id
    result = db.client.table("content_cache") \
        .select("*") \
        .eq("skill_id", skill_id) \
        .eq("chain_step", chain_step) \
        .eq("learner_id", learner_id) \
        .eq("validated", True) \
        .maybe_single() \
        .execute()

    if result and result.data:
        seed = runtime.state.get("current_seed")
        cached_item = {
            **(seed if isinstance(seed, dict) else {}),
            **(result.data if isinstance(result.data, dict) else {}),
        }
        return Command(update={
            "messages": [ToolMessage(
                content="CACHE_HIT: cached item loaded. Call deliver_item.",
                tool_call_id=runtime.tool_call_id,
            )],
            "generated_item": cached_item,
        })

    return Command(update={
        "messages": [ToolMessage(
            content="CACHE_MISS: call generate_themed_item.",
            tool_call_id=runtime.tool_call_id,
        )],
    })


@tool
def generate_themed_item(
    runtime: ToolRuntime[LearnerContext, ContentState],
) -> Command:
    """Generate a themed variant of the current seed item.

    Uses the learner's profile (interests, career goals) to theme
    the seed into a personalized item. Generation uses glm-5.
    """
    seed = runtime.state.get("current_seed", {})
    if not seed:
        return Command(update={
            "messages": [ToolMessage(
                content="No seed loaded. Call lookup_seed first.",
                tool_call_id=runtime.tool_call_id,
            )],
        })

    # Load learner profile for theming context
    learner_id = runtime.context.learner_id
    profile_result = db.client.table("learner_profiles") \
        .select("interests, modality_preference, coaching_tone, skill_levels") \
        .eq("learner_id", learner_id) \
        .maybe_single() \
        .execute()

    profile_data = profile_result.data if profile_result else None
    profile = profile_data if isinstance(profile_data, dict) else {}
    interests = profile.get("interests", [])
    active_interest = interests[0] if isinstance(interests, list) and interests else "everyday life"

    # Static generation prompt first, dynamic variables at end (cache-friendly)
    gen_prompt = (
        "You are an educational content generator. Generate a themed variant of the seed item below.\n\n"
        "RULES:\n"
        "- Preserve the EXACT mathematical/factual structure of the seed\n"
        "- The correct answer must remain correct\n"
        "- Distractors must remain plausible but wrong\n"
        "- Theme the surface context to the learner's interest\n"
        "- Weave in workplace vocabulary naturally\n"
        "- Match the stated difficulty level\n"
        "- Include scaffold_level (integer 1-5) from the seed\n"
        "  1=full_model, 2=partial_model, 3=verbal, 4=positional, 5=independent\n"
        "- Output valid JSON with keys: question_text, choices, correct_answer, explanation, scaffold_level\n\n"
        "SEED ITEM:\n"
        f"{json.dumps(seed, indent=2)}\n\n"
        f"LEARNER INTEREST: {active_interest}\n"
        f"DIFFICULTY: {seed.get('difficulty_b', 0.0)}\n"
        f"SCAFFOLD_LEVEL: {seed.get('scaffold_level', 3)}\n"
    )

    result = _get_generator().invoke([{"role": "user", "content": gen_prompt}])

    # Parse the generated item
    try:
        raw_content = result.content
        if isinstance(raw_content, list):
            parts: list[str] = []
            for part in raw_content:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict):
                    text_part = part.get("text")
                    if isinstance(text_part, str):
                        parts.append(text_part)
            content = "\n".join(parts).strip()
        else:
            content = str(raw_content).strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        generated = json.loads(content)
    except (json.JSONDecodeError, IndexError):
        generated = {
            "question_text": str(result.content),
            "choices": seed.get("choices", []),
            "correct_answer": seed.get("correct_answer", ""),
            "explanation": "",
            "parse_error": True,
        }

    # Carry forward seed metadata
    generated["skill_id"] = seed.get("skill_id", "")
    generated["chain_step"] = seed.get("chain_step", 0)
    generated["seed_id"] = seed.get("seed_id", "")
    generated["subject"] = seed.get("subject", "")
    generated["difficulty_b"] = seed.get("difficulty_b", 0.0)
    generated["scaffold_level"] = seed.get("scaffold_level", 3)  # int 1-5
    generated["theme"] = active_interest

    return Command(update={
        "messages": [ToolMessage(
            content="Item generated. Call validate_item to check quality.",
            tool_call_id=runtime.tool_call_id,
        )],
        "generated_item": generated,
        "learner_profile": profile,
    })


@tool
async def validate_item(
    runtime: ToolRuntime[LearnerContext, ContentState],
) -> Command:
    """Validate the generated item using cross-provider validation.

    If validation fails, enters the regeneration loop (max 3 attempts).
    If all attempts fail, falls back to the original seed.
    """
    generated = runtime.state.get("generated_item", {})
    seed = runtime.state.get("current_seed", {})
    profile = runtime.state.get("learner_profile", {})

    if not generated:
        return Command(update={
            "messages": [ToolMessage(
                content="No generated item. Call generate_themed_item first.",
                tool_call_id=runtime.tool_call_id,
            )],
        })

    # Validate
    result = await _validator.validate(
        item=generated,
        seed=seed,
        learner_profile=profile,
        generator_model=GENERATOR_MODEL,
    )

    if result.passed:
        # Cache the validated item
        _cache_item(runtime.context.learner_id, generated)
        return Command(update={
            "messages": [ToolMessage(
                content=f"Validation PASSED (score: {result.overall_score:.2f}). Item ready.",
                tool_call_id=runtime.tool_call_id,
            )],
            "validation_result": {"passed": True, "score": result.overall_score},
        })

    # Validation failed — enter regeneration loop
    regen_loop = RegenerationLoop(
        generator_model=GENERATOR_MODEL,
        validator=_validator,
    )
    final_item = await regen_loop.regenerate(
        failed_item=generated,
        feedback=result,
        seed=seed,
        learner_profile=profile,
    )

    if final_item:
        _cache_item(runtime.context.learner_id, final_item)
        return Command(update={
            "messages": [ToolMessage(
                content="Regeneration succeeded. Item ready.",
                tool_call_id=runtime.tool_call_id,
            )],
            "generated_item": final_item,
            "validation_result": {"passed": True, "regenerated": True},
        })

    # All attempts failed — fallback to seed
    return Command(update={
        "messages": [ToolMessage(
            content="Regeneration exhausted. Falling back to seed item.",
            tool_call_id=runtime.tool_call_id,
        )],
        "generated_item": seed,
        "validation_result": {"passed": False, "fallback": True},
    })


@tool
def deliver_item(
    runtime: ToolRuntime[LearnerContext, ContentState],
) -> str:
    """Return the final validated item as JSON for the coaching team.

    This is the terminal tool — its output goes back to the orchestrator
    which passes it to the coaching team's present_content tool.
    """
    item = runtime.state.get("generated_item", {})
    seed = runtime.state.get("current_seed", {})
    final = item if item else seed

    return json.dumps({
        "skill_id": final.get("skill_id", ""),
        "chain_step": final.get("chain_step", 0),
        "question_text": final.get("question_text", ""),
        "choices": final.get("choices", []),
        "correct_answer": final.get("correct_answer", ""),
        "explanation": final.get("explanation", ""),
        "theme": final.get("theme", ""),
        "difficulty_b": final.get("difficulty_b", 0.0),
        "scaffold_level": final.get("scaffold_level", 3),  # int 1-5, synced with prompt_hierarchy
        "subject": final.get("subject", ""),
        "is_seed_fallback": not bool(item),
    })


# ──────────────────────────────────────────────────────────────
# Cache helper
# ──────────────────────────────────────────────────────────────

def _cache_item(learner_id: str, item: dict):
    """Write a validated item to the content cache."""
    import time
    db.client.table("content_cache").upsert({
        "learner_id": learner_id,
        "skill_id": item.get("skill_id", ""),
        "chain_step": item.get("chain_step", 0),
        "question_text": item.get("question_text", ""),
        "choices": item.get("choices", []),
        "correct_answer": item.get("correct_answer", ""),
        "explanation": item.get("explanation", ""),
        "theme": item.get("theme", ""),
        "validated": True,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }).execute()


# ──────────────────────────────────────────────────────────────
# Middleware (cache-optimized prompt: static first, no dynamic vars)
# ──────────────────────────────────────────────────────────────

CONTENT_SYSTEM_PROMPT = SystemMessage(
    content=(
        "You are the content generation orchestrator. Your job is to produce "
        "a single validated, themed learning item from a seed.\n\n"
        "PIPELINE (follow in order):\n"
        "1. lookup_seed — load the seed for the requested skill/step\n"
        "2. check_cache — see if a valid cached item exists "
        "(scoped to runtime.context.learner_id)\n"
        "3. If cache hit: check_cache loads the cached item; call deliver_item\n"
        "4. If cache miss: call generate_themed_item\n"
        "5. Call validate_item (handles regeneration automatically)\n"
        "6. Call deliver_item to return the final content\n\n"
        "Do NOT deviate from this pipeline. Do NOT generate content yourself — "
        "use the tools. The tools handle cross-provider validation internally."
    )
)


@wrap_model_call
def apply_content_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    return handler(request.override(system_message=CONTENT_SYSTEM_PROMPT))


# ──────────────────────────────────────────────────────────────
# Build function
# ──────────────────────────────────────────────────────────────

def build_content_team(checkpointer=None, model: str = DEFAULT_BASE_MODEL):
    """Build the content generation agent.

    Uses the configured base model for orchestration.
    Actual generation uses the configured content generator via the tools. Validation uses
    gemini-3.1-pro via ContentValidator.
    """
    return create_agent(
        model=init_praxis_chat_model(model),
        tools=[
            lookup_seed,
            check_cache,
            generate_themed_item,
            validate_item,
            deliver_item,
        ],
        state_schema=ContentState,
        context_schema=LearnerContext,
        middleware=cast(Any, [apply_content_config]),
        checkpointer=checkpointer,
    )
