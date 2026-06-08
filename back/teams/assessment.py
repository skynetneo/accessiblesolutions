"""
praxis/teams/assessment.py

Assessment & Profiling Team.

Pattern: Handoffs (single agent, dynamic config per current_step)
Flow: interest_harvest → placement_test → profile_build → complete

The assessment team runs once for new learners. It:
1. Harvests interests conversationally (for micro-theming)
2. Runs adaptive placement via CATEngine (stealth — feels like a chat)
3. Builds the initial learner profile from results
4. Hands back to the master orchestrator with placement data

The CAT items are presented conversationally — the learner should never
feel like they're taking a test.

Usage:
    from teams.assessment import build_assessment_team

    team = build_assessment_team(checkpointer)
    result = team.invoke(
        {"messages": [...], "current_step": "interest_harvest"},
        context=LearnerContext(learner_id="abc", session_id="s1"),
    )
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import re
from typing import Callable, Any, cast
from typing_extensions import NotRequired

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import (
    wrap_model_call,
    ModelRequest,
    ModelResponse,
    SummarizationMiddleware,
)
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langchain_core.messages import SystemMessage
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.types import Command

from db.tools_bridge import (
    LearnerContext,
    fetch_seed_content,
    get_learner_profile,
    update_learner_profile,
    log_stealth_observation,
)
from assessment.cat_engine import CATEngine, CATItem, CATState
from curriculum.profile import get_current_curriculum
from model_factory import DEFAULT_BASE_MODEL, init_praxis_chat_model
from middleware.core import render_system_context

# ──────────────────────────────────────────────────────────────
# Assessment state
# ──────────────────────────────────────────────────────────────

class AssessmentState(AgentState):
    """State for the assessment agent."""
    current_step: NotRequired[str]           # interest_harvest | placement | profile_build | complete
    system_context: NotRequired[dict]
    interests_collected: NotRequired[list]   # raw interest strings from conversation
    modality_preference: NotRequired[str]
    career_goal: NotRequired[str]
    cat_state: NotRequired[dict]             # serialized CATState
    placement_results: NotRequired[dict]     # final theta + per-skill estimates
    subjects_to_assess: NotRequired[list]    # which curriculum subjects remain
    current_subject: NotRequired[str]        # subject being assessed now
    current_cat_item: NotRequired[dict]      # item awaiting learner response


# ──────────────────────────────────────────────────────────────
# Shared engine instance
# ──────────────────────────────────────────────────────────────

_cat_engine = CATEngine()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _as_str(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _as_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return default


def _normalize_answer_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_choice_letter(value: str) -> str | None:
    raw = str(value or "").strip().upper()
    if not raw:
        return None
    direct = re.match(r"^([A-Z])(?:\b|[\)\].:\-])", raw)
    if direct:
        return direct.group(1)
    contextual = re.search(r"\b(?:OPTION|CHOICE|ANSWER)\s*([A-Z])\b", raw)
    if contextual:
        return contextual.group(1)
    return None


def _is_correct_placement_response(
    learner_response: str,
    correct_answer: str,
    choices: list[Any],
) -> bool:
    normalized_response = _normalize_answer_text(learner_response)
    normalized_correct = _normalize_answer_text(correct_answer)
    if not normalized_response:
        return False

    if normalized_correct and normalized_response == normalized_correct:
        return True

    normalized_choices = [
        _normalize_answer_text(choice)
        for choice in choices
        if _normalize_answer_text(choice)
    ]

    correct_choice_idx: int | None = None
    if normalized_correct in normalized_choices:
        correct_choice_idx = normalized_choices.index(normalized_correct)
    else:
        answer_letter = _extract_choice_letter(correct_answer)
        if answer_letter:
            idx = ord(answer_letter) - ord("A")
            if 0 <= idx < len(normalized_choices):
                correct_choice_idx = idx

    response_letter = _extract_choice_letter(learner_response)
    if response_letter and correct_choice_idx is not None:
        return (ord(response_letter) - ord("A")) == correct_choice_idx

    if normalized_response in normalized_choices and correct_choice_idx is not None:
        return normalized_choices.index(normalized_response) == correct_choice_idx

    correct_letter = _extract_choice_letter(correct_answer)
    if response_letter and correct_letter:
        return response_letter == correct_letter

    return False


# ──────────────────────────────────────────────────────────────
# Transition tools
# ──────────────────────────────────────────────────────────────

@tool
def save_interests(
    interests: list[str],
    modality_preference: str,
    career_goal: str,
    runtime: ToolRuntime[LearnerContext, AssessmentState],
) -> Command:
    """Save harvested interests and preferences, transition to placement.

    Static instructions: Call this after conversationally learning what the
    learner is into. Interests drive micro-theming for the entire platform.
    Modality is 'visual', 'reading', 'kinesthetic', or 'balanced'.

    Args:
        interests: List of freeform interest strings
        modality_preference: How they prefer to learn
        career_goal: What brought them here (job, curriculum goal, both, unsure)
    """
    return Command(update={
        "messages": [ToolMessage(
            content=(
                f"Interests saved: {', '.join(interests)}. "
                f"Preference: {modality_preference}. Goal: {career_goal}. "
                "Starting placement — present items conversationally, NOT as a test."
            ),
            tool_call_id=runtime.tool_call_id,
        )],
        "interests_collected": interests,
        "modality_preference": modality_preference,
        "career_goal": career_goal,
        "current_step": "placement",
        "subjects_to_assess": [subj.id for subj in get_current_curriculum().subjects],
    })


@tool
def start_subject_placement(
    subject: str,
    runtime: ToolRuntime[LearnerContext, AssessmentState],
) -> Command:
    """Initialize CAT for a specific curriculum subject.

    Args:
        subject: A subject ID from the active curriculum profile
    """
    state = _cat_engine.new_session(subject=subject)
    return Command(update={
        "messages": [ToolMessage(
            content=f"Starting {subject} assessment. Select first item with get_next_placement_item.",
            tool_call_id=runtime.tool_call_id,
        )],
        "current_subject": subject,
        "cat_state": _serialize_cat_state(state),
    })


@tool
async def get_next_placement_item(
    runtime: ToolRuntime[LearnerContext, AssessmentState],
) -> str:
    """Get the next adaptive item for the current placement subject.

    Returns item details for the agent to present conversationally.
    The agent should weave collected interests into how it frames the question.
    """
    cat_state = _deserialize_cat_state(runtime.state.get("cat_state", {}))

    # Load item bank from seeds for this subject
    from db.client import db
    result = await asyncio.to_thread(
        lambda: db.client.table("seed_items")
        .select("*")
        .eq("subject", cat_state.subject)
        .execute()
    )
    seed_rows = _as_dict_list(getattr(result, "data", None))

    items = [
        CATItem(
            item_id=_as_str(row.get("seed_id")),
            skill_id=_as_str(row.get("skill_id")),
            difficulty_b=_as_float(row.get("difficulty_b"), 0.0),
            discrimination_a=_as_float(row.get("discrimination_a"), 1.0),
            subject=_as_str(row.get("subject"), ""),
            chain_step=_as_int(row.get("chain_step"), 0),
        )
        for row in seed_rows
        if _as_str(row.get("seed_id")) and _as_str(row.get("skill_id"))
    ]

    selected = _cat_engine.select_item(cat_state, items)
    if selected is None:
        return "No more items available for this subject. Call finish_subject_placement."

    # Load full question text
    seed = next((r for r in seed_rows if _as_str(r.get("seed_id")) == selected.item_id), {})

    return json.dumps({
        "item_id": selected.item_id,
        "skill_id": selected.skill_id,
        "question_text": seed.get("question_text", ""),
        "choices": seed.get("choices", []),
        "difficulty": selected.difficulty_b,
        "instruction": (
            "Present this conversationally. Do NOT say 'question 3 of 15'. "
            "Weave the learner's interests in if possible. "
            "After they respond, call record_placement_response with item_id and learner_response."
        ),
    })


@tool
async def record_placement_response(
    item_id: str,
    learner_response: str,
    runtime: ToolRuntime[LearnerContext, AssessmentState],
) -> Command:
    """Record a learner's response to a placement item and update CAT state.

    Args:
        item_id: The item that was answered
        learner_response: The learner's raw answer text (letter or free text)
    """
    cat_state = _deserialize_cat_state(runtime.state.get("cat_state", {}))

    if item_id in cat_state.administered_ids:
        return Command(update={
            "messages": [ToolMessage(
                content=(
                    f"Item {item_id} was already recorded. "
                    "Call get_next_placement_item to continue."
                ),
                tool_call_id=runtime.tool_call_id,
            )],
        })

    from db.client import db
    result = await asyncio.to_thread(
        lambda: db.client.table("seed_items")
        .select("*")
        .eq("seed_id", item_id)
        .maybe_single()
        .execute()
    )
    row = _as_dict(getattr(result, "data", None))
    if not row:
        return Command(update={
            "messages": [ToolMessage(
                content=(
                    f"Could not find seed item {item_id}. "
                    "Call get_next_placement_item to fetch a valid item."
                ),
                tool_call_id=runtime.tool_call_id,
            )],
        })

    item = CATItem(
        item_id=item_id,
        skill_id=_as_str(row.get("skill_id"), ""),
        difficulty_b=_as_float(row.get("difficulty_b"), 0.0),
        discrimination_a=_as_float(row.get("discrimination_a"), 1.0),
        subject=_as_str(row.get("subject"), ""),
    )
    correct = _is_correct_placement_response(
        learner_response=learner_response,
        correct_answer=_as_str(row.get("correct_answer"), ""),
        choices=row.get("choices", []) if isinstance(row.get("choices", []), list) else [],
    )

    cat_state = _cat_engine.record_response(cat_state, item, correct)
    should_stop = _cat_engine.should_stop(cat_state)

    n = len(cat_state.responses)
    msg = f"Recorded: {'correct' if correct else 'incorrect'} (item {n}, θ={cat_state.theta:.2f}, SE={cat_state.se:.2f}). "
    if should_stop:
        msg += "Stopping criterion met. Call finish_subject_placement."
    else:
        msg += "Call get_next_placement_item for the next one."

    return Command(update={
        "messages": [ToolMessage(content=msg, tool_call_id=runtime.tool_call_id)],
        "cat_state": _serialize_cat_state(cat_state),
    })


@tool
def finish_subject_placement(
    runtime: ToolRuntime[LearnerContext, AssessmentState],
) -> Command:
    """Finalize placement for the current subject and move to the next.

    Stores per-subject results and advances to the next subject,
    or transitions to profile_build if all subjects are done.
    """
    cat_state = _deserialize_cat_state(runtime.state.get("cat_state", {}))
    results = _cat_engine.get_results(cat_state)
    subject = runtime.state.get("current_subject", "")

    # Merge into cumulative placement results
    all_results = dict(runtime.state.get("placement_results", {}))
    all_results[subject] = results

    # Check remaining subjects
    remaining = list(runtime.state.get("subjects_to_assess", []))
    if subject in remaining:
        remaining.remove(subject)

    if remaining:
        next_step = "placement"
        msg = (
            f"{subject} placement done (θ={results['theta']:.2f}). "
            f"Remaining: {', '.join(remaining)}. "
            f"Call start_subject_placement for the next subject."
        )
    else:
        next_step = "profile_build"
        msg = (
            f"All placements complete. Results: "
            + ", ".join(f"{s}: θ={r['theta']:.2f}" for s, r in all_results.items())
            + ". Call build_learner_profile to finalize."
        )

    return Command(update={
        "messages": [ToolMessage(content=msg, tool_call_id=runtime.tool_call_id)],
        "placement_results": all_results,
        "subjects_to_assess": remaining,
        "current_step": next_step,
    })


@tool
async def build_learner_profile(
    runtime: ToolRuntime[LearnerContext, AssessmentState],
) -> Command:
    """Build and persist the initial learner profile from assessment data.

    Combines interests, placement results, and preferences into the
    learner_profiles table. This is the final step of assessment.
    """
    from db.client import db
    import time

    learner_id = runtime.context.learner_id
    interests = runtime.state.get("interests_collected", [])
    modality_preference = runtime.state.get("modality_preference", "balanced")
    career_goal = runtime.state.get("career_goal", "")
    placement = runtime.state.get("placement_results", {})

    # Build ZPD ranges from theta estimates (±0.5 around theta)
    zpd_ranges = {}
    skill_levels = {}
    for subject, results in placement.items():
        theta = results.get("theta", 0.0)
        zpd_ranges[subject] = {"min": theta - 0.5, "max": theta + 0.5}
        skill_levels[subject] = theta
        for skill_id, skill_theta in results.get("skill_estimates", {}).items():
            zpd_ranges[skill_id] = {"min": skill_theta - 0.5, "max": skill_theta + 0.5}
            skill_levels[skill_id] = skill_theta

    profile = {
        "learner_id": learner_id,
        "interests": interests,
        "skill_levels": json.dumps(skill_levels),
        "zpd_ranges": json.dumps(zpd_ranges),
        "scaffold_level": 3,
        "coaching_tone": "encouraging",
        "modality_preference": modality_preference,
        "career_goal": career_goal,
        "reinforcement_schedule": "VR-3",
        "sessions_completed": 0,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    placement_summary = ", ".join(
        f"{subject}={results.get('theta', 0.0):.1f}"
        for subject, results in placement.items()
    )

    await asyncio.to_thread(
        lambda: db.client.table("learner_profiles").upsert(profile).execute()
    )

    return Command(update={
        "messages": [ToolMessage(
            content=(
                f"Profile created for {learner_id}. "
                f"Interests: {', '.join(interests)}. "
                f"Placement: {placement_summary}. "
                "Assessment complete. The learner is ready for their first lesson."
            ),
            tool_call_id=runtime.tool_call_id,
        )],
        "current_step": "complete",
    })


# ──────────────────────────────────────────────────────────────
# CAT state serialization (TypedDict state must be JSON-safe)
# ──────────────────────────────────────────────────────────────

def _serialize_cat_state(state: CATState) -> dict:
    return {
        "subject": state.subject,
        "theta": state.theta,
        "se": state.se,
        "responses": state.responses,
        "administered_ids": list(state.administered_ids),
    }


def _deserialize_cat_state(data: dict) -> CATState:
    if not data:
        return CATState(subject="")
    return CATState(
        subject=data.get("subject", ""),
        theta=data.get("theta", 0.0),
        se=data.get("se", 3.0),
        responses=data.get("responses", []),
        administered_ids=set(data.get("administered_ids", [])),
    )


# ──────────────────────────────────────────────────────────────
# Dynamic configuration middleware (handoffs)
# ──────────────────────────────────────────────────────────────

# Static prompt content first, dynamic variables at the end (cache-friendly)
ASSESSMENT_CONFIGS = {
    "interest_harvest": {
        "prompt": (
            "You are starting a learner's first session on Praxis. Your job is to learn "
            "about them — what they're into, how they like to learn, and what brought them here.\n\n"
            "RULES:\n"
            "- Be warm, casual, and genuinely curious\n"
            "- Ask about hobbies, music, sports, games, shows — whatever they're into\n"
            "- Ask how they prefer to learn: seeing it, reading about it, or doing it\n"
            "- Ask what brought them here: certification/credential, better job, both, or just exploring\n"
            "- Dig into specifics ('What kind of music?' not just 'Do you like music?')\n"
            "- 3-5 exchanges max, then call save_interests with what you've gathered\n"
            "- Do NOT mention placement or testing\n"
        ),
        "tools": [save_interests, log_stealth_observation],
    },
    "placement": {
        "prompt": (
            "You are running an adaptive placement. The learner should NOT know this is a test.\n\n"
            "RULES:\n"
            "- Present each item conversationally, as if you're exploring what they know\n"
            "- Weave their interests into framing when possible\n"
            "- Never say 'question X of Y' or 'let me test you'\n"
            "- If they get one wrong, be encouraging: 'That's a tricky one'\n"
            "- The CAT engine handles difficulty selection — trust it\n"
            "- After each response, call record_placement_response\n"
            "- When told to stop, call finish_subject_placement\n\n"
            "FLOW:\n"
            "1. Call start_subject_placement for the next subject\n"
            "2. Call get_next_placement_item to get an item\n"
            "3. Present it conversationally\n"
            "4. After their answer, call record_placement_response with item_id and learner_response\n"
            "5. Repeat until told to stop\n"
        ),
        "tools": [
            start_subject_placement, get_next_placement_item,
            record_placement_response, finish_subject_placement,
            log_stealth_observation,
        ],
    },
    "profile_build": {
        "prompt": (
            "Placement is complete. Call build_learner_profile to create their profile.\n"
            "Then give them a brief, encouraging summary of what you learned about them "
            "and what they can expect from the platform. Keep it under 4 sentences.\n"
        ),
        "tools": [build_learner_profile],
    },
    "complete": {
        "prompt": (
            "Assessment is complete. The learner's profile has been created.\n"
            "Let the orchestrator know they're ready for their first lesson.\n"
        ),
        "tools": [],
    },
}


@wrap_model_call
def apply_assessment_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """Dynamic configuration based on current_step."""
    step = request.state.get("current_step", "interest_harvest")
    config = ASSESSMENT_CONFIGS.get(step, ASSESSMENT_CONFIGS["interest_harvest"])
    prompt = config["prompt"] + render_system_context(cast(dict[str, Any], request.state))
    return handler(request.override(
        system_message=SystemMessage(content=prompt),
        tools=config["tools"],
    ))


# ──────────────────────────────────────────────────────────────
# Build function
# ──────────────────────────────────────────────────────────────

ASSESSMENT_MODEL = os.environ.get(
    "PRAXIS_ASSESSMENT_MODEL",
    os.environ.get("UPSKILL_ASSESSMENT_MODEL", DEFAULT_BASE_MODEL),
)
SUMMARIZATION_MODEL = os.environ.get(
    "PRAXIS_SUMMARIZATION_MODEL",
    DEFAULT_BASE_MODEL,
)


def _available_summarization_model(configured: str) -> str:
    """Use configured summarization model only if its provider package exists."""
    provider = configured.split(":", 1)[0].split("/", 1)[0].strip().lower()
    provider_modules = {
        "anthropic": "langchain_anthropic",
        "deepseek": "langchain_deepseek",
        "google_genai": "langchain_google_genai",
        "google": "langchain_google_genai",
        "openai": "langchain_openai",
        "zai": "langchain_openai",
        "zhipu": "langchain_openai",
        "glm": "langchain_openai",
    }
    module_name = provider_modules.get(provider)
    if module_name and importlib.util.find_spec(module_name) is None:
        return "google_genai:gemini-3.5-flash"
    return configured


def build_assessment_team(checkpointer=None, model: str = ASSESSMENT_MODEL):
    """Build the assessment agent."""
    all_tools = [
        save_interests,
        start_subject_placement,
        get_next_placement_item,
        record_placement_response,
        finish_subject_placement,
        build_learner_profile,
        log_stealth_observation,
    ]

    return create_agent(
        model=init_praxis_chat_model(model),
        tools=all_tools,
        state_schema=AssessmentState,
        context_schema=LearnerContext,
        middleware=cast(Any, [
            apply_assessment_config,
            SummarizationMiddleware(
                model=init_praxis_chat_model(_available_summarization_model(SUMMARIZATION_MODEL)),
                trigger=("tokens", 4000),
                keep=("messages", 20),
                token_counter=lambda messages: count_tokens_approximately(messages),
            ),
        ]),
        checkpointer=checkpointer,
    )
