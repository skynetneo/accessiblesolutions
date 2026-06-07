"""
praxis/scaffolding/prompt_hierarchy.py

The 10-level ABA prompt hierarchy for adaptive e-learning.
Pure data — no DB calls, no LLM calls.

Effective prompt fading is critical for e-learning and must adapt to each
learner. This hierarchy provides granular levels from maximum support
(full model) to full independence, with rich intermediate levels that
map to different instructional strategies.

The fading engine decides WHEN to change levels based on performance.
The coaching team's system prompt references these descriptions.
Individual learners may skip levels or spend extra time at certain levels
depending on their profile, learning style, and demonstrated mastery.

Levels:
    1  FULL_MODEL       — Complete solution walkthrough
    2  PARTIAL_MODEL    — First steps shown, learner completes
    3  WORKED_EXAMPLE   — Similar solved problem shown alongside target
    4  VERBAL           — Guiding questions only
    5  VISUAL_SCAFFOLD  — Diagrams, annotations, highlighted key info
    6  HINT             — Brief targeted hint
    7  GESTURAL         — Minimal visual emphasis on key parts
    8  STIMULUS_FADING  — Distractors made obviously wrong
    9  TIME_DELAY       — Problem presented, pause before any help
   10  INDEPENDENT      — No support at all

Usage:
    from scaffolding.prompt_hierarchy import PromptLevel, get_level_config
    config = get_level_config(4)
    # config.name == "verbal"
    # config.instruction == "Ask guiding questions..."
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class PromptLevel(IntEnum):
    FULL_MODEL = 1
    PARTIAL_MODEL = 2
    WORKED_EXAMPLE = 3
    VERBAL = 4
    VISUAL_SCAFFOLD = 5
    HINT = 6
    GESTURAL = 7
    STIMULUS_FADING = 8
    TIME_DELAY = 9
    INDEPENDENT = 10


@dataclass(frozen=True)
class LevelConfig:
    level: PromptLevel
    name: str
    instruction: str          # injected into coaching system prompt
    learner_visible: str      # what the learner experiences (for UX hints)
    support_ratio: float      # 1.0 = full support, 0.0 = none


LEVEL_MIN = 1
LEVEL_MAX = 10


LEVELS: dict[int, LevelConfig] = {
    1: LevelConfig(
        level=PromptLevel.FULL_MODEL,
        name="full_model",
        instruction=(
            "Show the COMPLETE solution with every step explained. "
            "Walk through the entire problem from start to finish. "
            "Use the learner's interest theme in your examples. "
            "Narrate your reasoning out loud so the learner sees the thought process."
        ),
        learner_visible="Here's how to solve this step by step.",
        support_ratio=1.0,
    ),
    2: LevelConfig(
        level=PromptLevel.PARTIAL_MODEL,
        name="partial_model",
        instruction=(
            "Show the first 2-3 steps of the solution, then ask the learner "
            "to complete the rest. If they get stuck, show one more step. "
            "Fade your support gradually within this single item."
        ),
        learner_visible="I'll start this one, you finish it.",
        support_ratio=0.80,
    ),
    3: LevelConfig(
        level=PromptLevel.WORKED_EXAMPLE,
        name="worked_example",
        instruction=(
            "Show a SIMILAR solved problem first (with clear steps), then "
            "present the actual target problem. Let the learner use the "
            "worked example as a reference. Do NOT solve the target for them. "
            "The example should use the same skill but different numbers/content."
        ),
        learner_visible="Here's a similar problem, then you'll try one.",
        support_ratio=0.65,
    ),
    4: LevelConfig(
        level=PromptLevel.VERBAL,
        name="verbal",
        instruction=(
            "Ask guiding questions only: 'What operation do we need here?' "
            "'What's the first step?' 'What do you notice about these numbers?' "
            "Do NOT show any part of the solution. Use Socratic questioning to "
            "lead the learner to discover the answer themselves."
        ),
        learner_visible="What do you think the first step is?",
        support_ratio=0.50,
    ),
    5: LevelConfig(
        level=PromptLevel.VISUAL_SCAFFOLD,
        name="visual_scaffold",
        instruction=(
            "Provide visual support: Highlight key information, underline important terms, "
            "or use formatting (bold, italics) to draw attention to critical parts of the problem. "
            "CRITICAL: Include the present_visual_animation tool if there is a relevant 'animation_id' "
            "(like 'fraction_bars', 'area_model', etc.). Do NOT explain the solution steps."
        ),
        learner_visible="I've highlighted some key information for you.",
        support_ratio=0.40,
    ),
    6: LevelConfig(
        level=PromptLevel.HINT,
        name="hint",
        instruction=(
            "Provide a single brief, targeted hint. Examples: 'Think about "
            "what happens when you multiply fractions.' or 'Look at the "
            "second paragraph again.' The hint should point toward the "
            "approach, NOT the answer. One sentence maximum."
        ),
        learner_visible="Here's a small hint.",
        support_ratio=0.30,
    ),
    7: LevelConfig(
        level=PromptLevel.GESTURAL,
        name="gestural",
        instruction=(
            "Highlight or bold ONE key part of the problem. Minimal words. "
            "Let the visual emphasis guide them without verbal explanation. "
            "This is the equivalent of pointing at something — draw their "
            "eye but say nothing about why."
        ),
        learner_visible="Take a close look at this part.",
        support_ratio=0.20,
    ),
    8: LevelConfig(
        level=PromptLevel.STIMULUS_FADING,
        name="stimulus_fading",
        instruction=(
            "Re-present the exact same question, but apply STIMULUS FADING to the distractors. "
            "Change the wrong answer choices to be mathematically/logically absurd or obviously incorrect "
            "(e.g., changing 1/5 to 34/199) so the correct answer becomes highly salient. "
            "The learner still must identify the correct answer — you're just removing noise."
        ),
        learner_visible="Let me show you this question again.",
        support_ratio=0.10,
    ),
    9: LevelConfig(
        level=PromptLevel.TIME_DELAY,
        name="time_delay",
        instruction=(
            "Present the problem clearly with NO immediate support. Wait for "
            "the learner to attempt an answer. If they respond within a "
            "reasonable time, evaluate normally. If they explicitly ask for "
            "help, drop down one support level. The goal is to give them "
            "space to retrieve the knowledge independently first."
        ),
        learner_visible="Take your time with this one.",
        support_ratio=0.05,
    ),
    10: LevelConfig(
        level=PromptLevel.INDEPENDENT,
        name="independent",
        instruction=(
            "Present the problem clearly and give space. No hints, no cues, "
            "no visual emphasis. Only respond after they attempt an answer. "
            "This is the target end state — the learner is performing independently."
        ),
        learner_visible="Give it a try.",
        support_ratio=0.0,
    ),
}


def get_level_config(level: int) -> LevelConfig:
    """Get the config for a prompt level (clamped to valid range)."""
    return LEVELS[max(LEVEL_MIN, min(LEVEL_MAX, level))]
