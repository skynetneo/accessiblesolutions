"""
praxis/teams/coaching.py

Coaching Team.
The core instructional loop using the Evaluator-Optimizer and State Machine patterns.
Flow: teaching → checking → scaffolding (if incorrect) → encouraging (if correct)

Features Generative UI Tool Calls: 
The agent calls tools like `present_multiple_choice`. The frontend intercepts 
these tool calls and renders interactive React components instead of plain text.
"""

from __future__ import annotations

import os
import json
from typing import Callable, Any
from typing_extensions import NotRequired

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langchain_core.messages import SystemMessage
from langgraph.types import Command

from db.tools_bridge import LearnerContext, record_mastery_attempt
from model_factory import DEFAULT_BASE_MODEL, init_praxis_chat_model
from middleware.core import MicroThemingMiddleware, render_system_context


# ──────────────────────────────────────────────────────────────
# State Definition
# ──────────────────────────────────────────────────────────────

class CoachingState(AgentState):
    """State for the coaching agent."""
    current_step: NotRequired[str]           # teaching | checking | scaffolding | encouraging
    system_context: NotRequired[dict]
    current_item: NotRequired[dict]          # Tracks what is currently being presented
    gamification_events: NotRequired[list]   # Events to pass to gamification engine
    last_response_correct: NotRequired[bool]
    last_item_type: NotRequired[str]


# ──────────────────────────────────────────────────────────────
# Generative UI Presentation Tools
# ──────────────────────────────────────────────────────────────

@tool
async def present_multiple_choice(
    question: str,
    choices: list[str],
    correct_answer: str,
    skill_id: str,
    chain_step: int,
    prompt_level: int,
    runtime: ToolRuntime[LearnerContext, CoachingState],
) -> Command:
    """Present a multiple choice question to the learner using the interactive UI."""
    item = {
        "skill_id": skill_id,
        "chain_step": chain_step,
        "prompt_level": prompt_level,
        "question_type": "multiple_choice",
        "correct_answer": correct_answer
    }
    return Command(update={
        "current_item": item,
        "current_step": "checking",
        "messages": [ToolMessage(
            content="[UI Rendered] The interactive multiple choice question is now visible to the learner. Wait for their response.",
            tool_call_id=runtime.tool_call_id,
        )]
    })


@tool
async def present_fill_in_blank(
    template: str,
    blanks: list[dict],
    skill_id: str,
    chain_step: int,
    prompt_level: int,
    runtime: ToolRuntime[LearnerContext, CoachingState],
) -> Command:
    """Present a fill-in-the-blank interactive UI.
    Example template: 'The area of a {shape} is {formula}'
    Example blanks: [{'id': 'shape', 'correctAnswer': 'circle'}, {'id': 'formula', 'correctAnswer': 'pi * r^2'}]
    """
    item = {
        "skill_id": skill_id,
        "chain_step": chain_step,
        "prompt_level": prompt_level,
        "question_type": "fill_in_blank",
    }
    return Command(update={
        "current_item": item,
        "current_step": "checking",
        "messages": [ToolMessage(
            content="[UI Rendered] The fill-in-the-blank UI is now visible. Wait for response.",
            tool_call_id=runtime.tool_call_id,
        )]
    })


@tool
async def present_drag_sort(
    instruction: str,
    items: list[dict],
    skill_id: str,
    chain_step: int,
    prompt_level: int,
    runtime: ToolRuntime[LearnerContext, CoachingState],
) -> Command:
    """Present an interactive drag-and-drop sorting challenge.
    Example items: [{'id': 'step1', 'label': 'Preheat oven'}, {'id': 'step2', 'label': 'Mix batter'}]
    """
    item = {
        "skill_id": skill_id,
        "chain_step": chain_step,
        "prompt_level": prompt_level,
        "question_type": "drag_sort",
    }
    return Command(update={
        "current_item": item,
        "current_step": "checking",
        "messages": [ToolMessage(
            content="[UI Rendered] The drag-sort UI is now visible. Wait for response.",
            tool_call_id=runtime.tool_call_id,
        )]
    })


@tool
async def present_match_pairs(
    instruction: str,
    pairs: list[dict],
    skill_id: str,
    chain_step: int,
    prompt_level: int,
    runtime: ToolRuntime[LearnerContext, CoachingState],
) -> Command:
    """Present an interactive pair matching challenge.
    Example pairs: [{'id': 'p1', 'left': 'Apple', 'right': 'Fruit'}, {'id': 'p2', 'left': 'Carrot', 'right': 'Vegetable'}]
    """
    item = {
        "skill_id": skill_id,
        "chain_step": chain_step,
        "prompt_level": prompt_level,
        "question_type": "match_pairs",
    }
    return Command(update={
        "current_item": item,
        "current_step": "checking",
        "messages": [ToolMessage(
            content="[UI Rendered] The pair matching UI is now visible. Wait for response.",
            tool_call_id=runtime.tool_call_id,
        )]
    })


@tool
async def present_visual_animation(
    animation_id: str,
    props: dict,
    skill_id: str,
    chain_step: int,
    runtime: ToolRuntime[LearnerContext, CoachingState],
) -> Command:
    """Present a visual animation or interactive model to the learner.
    Perfect for VISUAL learners or when providing a VISUAL_SCAFFOLD.
    
    Valid animation_ids: 
    - 'fraction_bars': Visualizing fractions
    - 'area_model': Multiplication/division visualization
    - 'coordinate_plane': Graphing and geometry
    - 'number_line': Addition/subtraction and relative value
    - 'equation_balance': Algebra visualization
    - 'bar_chart': Data handling
    - 'passage_structure': Reading comprehension block structure
    - 'cause_effect': Event relationships
    """
    item = {
        "skill_id": skill_id,
        "chain_step": chain_step,
        "question_type": "visual_animation",
        "animation_id": animation_id,
    }
    return Command(update={
        "current_item": item,
        "messages": [ToolMessage(
            content=f"[UI Rendered] Visual animation ({animation_id}) is now visible. Wait for the learner's response.",
            tool_call_id=runtime.tool_call_id,
        )]
    })


@tool
async def present_audio_narration(
    text_segments: list[str],
    skill_id: str,
    chain_step: int,
    runtime: ToolRuntime[LearnerContext, CoachingState],
) -> Command:
    """Present an auditory lesson with recorded narration and highlighted text syncing.
    Perfect for AUDITORY and READING-focused learners.
    
    Pass a list of strings where each string is a coherent thought or sentence.
    The UI will narrate these segments in order.
    """
    item = {
        "skill_id": skill_id,
        "chain_step": chain_step,
        "question_type": "audio_narration",
        "segments": text_segments,
    }
    return Command(update={
        "current_item": item,
        "messages": [ToolMessage(
            content="[UI Rendered] Audio narration is playing. Wait for the learner to listen and respond.",
            tool_call_id=runtime.tool_call_id,
        )]
    })


# ──────────────────────────────────────────────────────────────
# ATOMIC State Tracking Tool
# ──────────────────────────────────────────────────────────────

@tool
async def record_response(
    correct: bool,
    runtime: ToolRuntime[LearnerContext, CoachingState],
) -> Command:
    """Record the learner's response to the current item and atomically persist to DB."""
    item = runtime.state.get("current_item", {})
    next_step = "encouraging" if correct else "scaffolding"

    skill_id = item.get("skill_id", "unknown")
    chain_step = item.get("chain_step", 1)
    prompt_level = item.get("prompt_level", 3)

    db_result = await record_mastery_attempt.coroutine(
        skill_id=skill_id,
        chain_step=chain_step,
        correct=correct,
        prompt_level=prompt_level,
        runtime=runtime,
    )

    return Command(update={
        "messages": [ToolMessage(
            content=(
                f"Response recorded and saved to DB successfully.\n"
                f"DB Output: {db_result}\n"
                f"Moving to {next_step} mode."
            ),
            tool_call_id=runtime.tool_call_id
        )],
        "current_step": next_step,
        "last_response_correct": correct,
        "last_item_type": item.get("item_type", "target"),
    })


@tool
def award_progress(
    xp: int,
    badge: str = "",
    runtime: ToolRuntime[LearnerContext, CoachingState] = None,
) -> Command:
    """Award XP or Badges to the learner for good effort or mastery."""
    events = list(runtime.state.get("gamification_events", []))
    events.append({
        "type": "xp_award",
        "amount": xp,
        "badge": badge,
    })
    return Command(update={
        "messages": [ToolMessage(
            content=f"Awarded {xp} XP and badge '{badge}'.",
            tool_call_id=runtime.tool_call_id,
        )],
        "gamification_events": events,
    })


# ──────────────────────────────────────────────────────────────
# Dynamic Configuration / State Machine
# ──────────────────────────────────────────────────────────────

COACHING_CONFIGS = {
    "teaching": {
        "prompt": (
            "You are in TEACHING mode. Introduce the concept clearly and concisely appropriate to the learner's age, level, interests and goals.\n"
            "CRITICAL: Tailor your presentation to the learner's modality_preference. \n"
            "- If VISUAL: Use the present_visual_animation tool.\n"
            "- If AUDITORY/READING: Use the present_audio_narration tool.\n"
            "- If KINESTHETIC: Use interactive drag-and-drop tools.\n"
            "Use the provided lesson content. If there is an interactive question, "
            "call the appropriate presentation tool (e.g., present_multiple_choice, present_drag_sort, present_visual_animation). "
            "Do NOT type out the question choices in text if you use the tool."
        ),
        "tools": [present_multiple_choice, present_fill_in_blank, present_drag_sort, present_match_pairs, present_visual_animation, present_audio_narration],
    },
    "checking": {
        "prompt": (
            "You are in CHECKING mode. The user is attempting to answer a question.\n"
            "Evaluate their answer. If correct, call record_response(correct=True). "
            "If incorrect, call record_response(correct=False).\n"
            "Do not explain the answer yet. Just record the response."
        ),
        "tools": [record_response],
    },
    "scaffolding": {
        "prompt": (
            "You are in SCAFFOLDING mode. The user answered incorrectly.\n"
            "Provide a hint based on their specific error. Do NOT give away the answer immediately.\n"
            "Walk them through it step-by-step. Ask them to try again. "
            "If the prompting level suggests VISUAL_SCAFFOLD, use present_visual_animation."
        ),
        "tools": [present_visual_animation],
    },
    "encouraging": {
        "prompt": (
            "You are in ENCOURAGING mode. The user answered correctly!\n"
            "Provide brief age/learner appropriate, enthusiastic praise. Call award_progress to give them 10 XP.\n"
            "Then, smoothly transition into the next topic or question."
        ),
        "tools": [award_progress, present_multiple_choice, present_fill_in_blank, present_drag_sort, present_match_pairs],
    },
}

@wrap_model_call
def apply_coaching_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    step = request.state.get("current_step", "teaching")
    config = COACHING_CONFIGS.get(step, COACHING_CONFIGS["teaching"])
    prompt = config["prompt"] + render_system_context(request.state)
    return handler(request.override(
        system_message=SystemMessage(content=prompt),
        tools=config["tools"],
    ))


COACHING_MODEL = os.environ.get(
    "PRAXIS_COACHING_MODEL",
    os.environ.get("UPSKILL_COACHING_MODEL", DEFAULT_BASE_MODEL),
)


def build_coaching_team(checkpointer=None, model: str = COACHING_MODEL):
    all_tools = [
        present_multiple_choice,
        present_fill_in_blank,
        present_drag_sort,
        present_match_pairs,
        present_visual_animation,
        present_audio_narration,
        record_response,
        award_progress,
    ]
    
    return create_agent(
        model=init_praxis_chat_model(model),
        tools=all_tools,
        state_schema=CoachingState,
        context_schema=LearnerContext,
        middleware=[
            apply_coaching_config,
            MicroThemingMiddleware(),
        ],
        checkpointer=checkpointer,
    )
