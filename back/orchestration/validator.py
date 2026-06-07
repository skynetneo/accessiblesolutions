"""
praxis/orchestration/validator.py

Cross-provider content validation with structured rubric.

Every generated content item passes through this validator BEFORE being
shown to a learner. The validator always uses a DIFFERENT AI provider than
the generator (cross-provider bias removal).

The validator scores items on a per-content-type rubric and returns a
structured ValidationResult. On failure, it provides specific per-criterion
feedback that the regeneration loop uses to fix the item.

The regeneration loop (also in this file) handles the evaluator-optimizer
cycle: generate → validate → if fail, regenerate with feedback → re-validate.
Max 3 attempts before falling back to the original seed.

Usage:
    from orchestration.validator import ContentValidator, RegenerationLoop

    validator = ContentValidator()
    result = await validator.validate(generated_item, seed_item, learner_profile)

    if not result.passed:
        loop = RegenerationLoop(generator_model, validator)
        final_item = await loop.regenerate(
            failed_item=generated_item,
            feedback=result,
            seed=seed_item,
            learner_profile=learner_profile,
        )
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Any

from model_factory import init_praxis_chat_model, model_provider_key


# ──────────────────────────────────────────────────────────────
# Validation rubric and results
# ──────────────────────────────────────────────────────────────

# Note: Subject keys are plain strings validated at runtime against
# the active CurriculumProfile. The RUBRICS dict below uses string
# keys with a DEFAULT_RUBRIC fallback for unknown subjects.


@dataclass
class CriterionScore:
    """Score for a single rubric criterion."""
    name: str
    score: float           # 0.0-1.0
    passed: bool           # score >= threshold
    feedback: str = ""     # specific feedback if failed


@dataclass
class ValidationResult:
    """Structured output from the validator."""
    item_id: str
    passed: bool
    overall_score: float          # weighted average of all criteria
    criteria: list[CriterionScore] = field(default_factory=list)
    validator_model: str = ""
    validated_at: str = ""

    @property
    def failed_criteria(self) -> list[CriterionScore]:
        return [c for c in self.criteria if not c.passed]

    @property
    def feedback_summary(self) -> str:
        """Formatted feedback for the regeneration loop."""
        if self.passed:
            return "All criteria passed."
        parts = ["VALIDATION FAILED. Fix these issues:"]
        for c in self.failed_criteria:
            parts.append(f"  - {c.name} ({c.score:.2f}): {c.feedback}")
        return "\n".join(parts)


# ──────────────────────────────────────────────────────────────
# Rubric definitions per content type
# ──────────────────────────────────────────────────────────────

# Each criterion: (name, weight, threshold)
# Weights must sum to 1.0 per content type

RUBRICS: dict[str, list[tuple[str, float, float]]] = {
    "math": [
        ("mathematical_accuracy", 0.30, 0.95),   # must be nearly perfect
        ("distractor_plausibility", 0.15, 0.70),  # distractors represent real errors
        ("difficulty_alignment", 0.15, 0.65),      # matches target IRT difficulty
        ("theming_naturalness", 0.10, 0.60),       # interest theme feels organic
        ("employment_integration", 0.10, 0.50),    # workplace context is realistic
        ("bias_check", 0.10, 0.80),                # free from stereotypes
        ("scaffold_alignment", 0.10, 0.60),        # matches learner's prompt level
    ],
    "rla": [
        ("reading_level", 0.20, 0.70),             # appropriate for learner
        ("question_validity", 0.25, 0.85),          # answerable from passage
        ("distractor_plausibility", 0.15, 0.70),
        ("difficulty_alignment", 0.10, 0.65),
        ("theming_naturalness", 0.10, 0.60),
        ("employment_integration", 0.10, 0.50),
        ("bias_check", 0.10, 0.80),
    ],
    "science": [
        ("scientific_accuracy", 0.30, 0.90),
        ("distractor_plausibility", 0.15, 0.70),
        ("difficulty_alignment", 0.15, 0.65),
        ("theming_naturalness", 0.10, 0.60),
        ("employment_integration", 0.10, 0.50),
        ("bias_check", 0.10, 0.80),
        ("scaffold_alignment", 0.10, 0.60),
    ],
    "social_studies": [
        ("factual_accuracy", 0.25, 0.85),
        ("argument_quality", 0.15, 0.70),           # for argument/evidence items
        ("distractor_plausibility", 0.15, 0.70),
        ("difficulty_alignment", 0.10, 0.65),
        ("theming_naturalness", 0.10, 0.60),
        ("employment_integration", 0.10, 0.50),
        ("bias_check", 0.15, 0.85),                 # higher threshold for social topics
    ],
}

# Default rubric if content type not recognized
DEFAULT_RUBRIC = [
    ("accuracy", 0.30, 0.85),
    ("distractor_plausibility", 0.20, 0.70),
    ("difficulty_alignment", 0.15, 0.65),
    ("theming_naturalness", 0.15, 0.60),
    ("bias_check", 0.20, 0.80),
]


# ──────────────────────────────────────────────────────────────
# Content Validator
# ──────────────────────────────────────────────────────────────

class ContentValidator:
    """
    Cross-provider content validation.

    CRITICAL RULE: The validator model is ALWAYS a different provider
    than the generator model. This is the cross-provider bias removal
    pattern — if OpenAI generates, Google validates. If Anthropic
    generates, OpenAI validates.

    Provider rotation:
        Generator: glm-5.1       → Validator: gemini-3.1-pro-preview
        Generator: gpt-5.2-mini  → Validator: gemini-3.1-pro-preview
        Generator: deepseek-v3   → Validator: sonnet-4.6
        Generator: sonnet-4.6    → Validator: gemini-3.1-pro-preview
    """

    # Map generator provider → validator model
    VALIDATOR_MAP: dict[str, str] = {
        "zai": "google_genai:gemini-3.1-pro-preview",
        "zhipu": "google_genai:gemini-3.1-pro-preview",
        "glm": "google_genai:gemini-3.1-pro-preview",
        "openai": "google_genai:gemini-3.1-pro-preview",
        "deepseek": "anthropic:claude-sonnet-4-6",
        "anthropic": "google_genai:gemini-3.1-pro-preview",
        "google": "anthropic:claude-sonnet-4-6",
    }
    DEFAULT_VALIDATOR = "google_genai:gemini-3.1-pro-preview"

    PASS_THRESHOLD = 0.75

    def __init__(self, validator_model: Optional[str] = None):
        """
        Args:
            validator_model: Override the validator model (for testing).
                             In production, this is auto-selected based on generator.
        """
        self._override_model = validator_model

    def _select_validator_model(self, generator_model: str) -> str:
        """Pick a validator model from a DIFFERENT provider than the generator."""
        if self._override_model:
            return self._override_model

        provider_key = model_provider_key(generator_model)
        if provider_key in self.VALIDATOR_MAP:
            return self.VALIDATOR_MAP[provider_key]

        return self.DEFAULT_VALIDATOR

    async def validate(
        self,
        item: dict,
        seed: dict,
        learner_profile: dict,
        generator_model: str = "unknown",
    ) -> ValidationResult:
        """Validate a generated content item against the rubric.

        Args:
            item: The generated item dict (question_text, choices, correct_answer, etc.)
            seed: The source seed this was generated from
            learner_profile: The learner's profile (for difficulty/scaffold checks)
            generator_model: Which model generated this (to pick cross-provider validator)

        Returns:
            ValidationResult with per-criterion scores and feedback
        """
        validator_model_id = self._select_validator_model(generator_model)

        # Select rubric based on content type
        subject = item.get("subject", seed.get("subject", ""))
        rubric = RUBRICS.get(subject, DEFAULT_RUBRIC)

        # Build the validation prompt
        prompt = self._build_validation_prompt(item, seed, learner_profile, rubric)

        # Call the validator model
        model = init_praxis_chat_model(validator_model_id)
        response = await asyncio.to_thread(
            lambda: model.invoke(prompt)
        )

        # Parse the structured response
        result = self._parse_validation_response(
            response.content,
            rubric,
            item.get("item_id", f"gen_{uuid.uuid4().hex[:8]}"),
            validator_model_id,
        )

        return result

    def _build_validation_prompt(
        self,
        item: dict,
        seed: dict,
        learner_profile: dict,
        rubric: list[tuple[str, float, float]],
    ) -> str:
        """Build the prompt for the validator model."""

        criteria_list = "\n".join(
            f"  {i+1}. {name} (weight={weight}, pass_threshold={threshold})"
            for i, (name, weight, threshold) in enumerate(rubric)
        )

        choices_str = "\n".join(item.get("choices", []))
        seed_choices_str = "\n".join(seed.get("choices", []))

        return f"""You are a content quality validator. Your job is to evaluate a generated
learning item against a source seed and a validation rubric. Be rigorous.

Score each criterion from 0.0 to 1.0. For any criterion below its pass threshold,
provide specific feedback on what's wrong and how to fix it.

CRITICAL CHECKS:
- For math: Is the correct answer actually correct? Does every distractor represent
  a specific, plausible misconception (not a random wrong number)?
- For RLA: Can the question be answered from the passage alone?
- For all: Is the theme applied naturally (not forced)? Is the content free from
  stereotypes and cultural bias?

Respond in this exact JSON format (no markdown, no backticks):
{{
  "scores": [
    {{"name": "criterion_name", "score": 0.85, "feedback": "specific feedback if score < threshold, empty string otherwise"}}
  ]
}}

=== VALIDATION CRITERIA ===
{criteria_list}

=== SOURCE SEED ===
Question: {seed.get('question_text', 'N/A')}
Choices:
{seed_choices_str}
Correct answer: {seed.get('correct_answer', 'N/A')}
Rationale: {seed.get('correct_rationale', 'N/A')}
Subject: {seed.get('subject', 'N/A')}
Skill: {seed.get('skill_id', 'N/A')}
Target difficulty (IRT b): {seed.get('difficulty_b', 'N/A')}

=== GENERATED ITEM ===
Question: {item.get('question_text', 'N/A')}
Choices:
{choices_str}
Correct answer: {item.get('correct_answer', 'N/A')}
Rationale: {item.get('correct_rationale', 'N/A')}
Theme applied: {item.get('theme_applied', 'none')}
Interest: {item.get('freeform_interest', 'none')}
Employment context: {item.get('employment_context', 'none')}

=== LEARNER CONTEXT ===
Target difficulty range: {learner_profile.get('zpd_ranges', 'N/A')}
Scaffold level: {item.get('prompt_level', 'N/A')}"""

    def _parse_validation_response(
        self,
        response_text: str,
        rubric: list[tuple[str, float, float]],
        item_id: str,
        validator_model: str,
    ) -> ValidationResult:
        """Parse the validator model's JSON response into a ValidationResult."""

        # Clean response (strip markdown fences if present)
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
            score_list = parsed.get("scores", [])
        except (json.JSONDecodeError, KeyError):
            # If parsing fails, return a failing result with feedback
            return ValidationResult(
                item_id=item_id,
                passed=False,
                overall_score=0.0,
                criteria=[CriterionScore(
                    name="parse_error",
                    score=0.0,
                    passed=False,
                    feedback=f"Validator response could not be parsed: {response_text[:200]}",
                )],
                validator_model=validator_model,
                validated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        # Build criterion scores
        rubric_map = {name: (weight, threshold) for name, weight, threshold in rubric}
        criteria = []
        weighted_sum = 0.0
        total_weight = 0.0

        for score_item in score_list:
            name = score_item.get("name", "")
            score = float(score_item.get("score", 0.0))
            feedback = score_item.get("feedback", "")

            weight, threshold = rubric_map.get(name, (0.1, 0.7))
            passed = score >= threshold

            criteria.append(CriterionScore(
                name=name,
                score=score,
                passed=passed,
                feedback=feedback if not passed else "",
            ))

            weighted_sum += score * weight
            total_weight += weight

        overall = weighted_sum / total_weight if total_weight > 0 else 0.0
        all_passed = all(c.passed for c in criteria) and overall >= self.PASS_THRESHOLD

        return ValidationResult(
            item_id=item_id,
            passed=all_passed,
            overall_score=round(overall, 4),
            criteria=criteria,
            validator_model=validator_model,
            validated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )


# ──────────────────────────────────────────────────────────────
# Regeneration Loop (evaluator-optimizer pattern)
# ──────────────────────────────────────────────────────────────

class RegenerationLoop:
    """
    Handles the evaluator-optimizer cycle for failed content.

    generate → validate → if fail → regenerate with feedback → re-validate
    Max MAX_ATTEMPTS before falling back to the original seed.

    The key insight: we don't just retry. We pass the SPECIFIC validation
    feedback to the generator so it knows exactly what to fix.
    """

    MAX_ATTEMPTS = 3

    def __init__(
        self,
        generator_model: str,
        validator: ContentValidator,
    ):
        self.generator_model = generator_model
        self.validator = validator
        self.model = init_praxis_chat_model(generator_model)

    async def regenerate(
        self,
        failed_item: dict,
        feedback: ValidationResult,
        seed: dict,
        learner_profile: dict,
        generation_prompt: str = "",
    ) -> dict:
        """Regenerate content that failed validation.

        Args:
            failed_item: The item that failed validation
            feedback: ValidationResult with specific failure reasons
            seed: The source seed
            learner_profile: The learner's profile
            generation_prompt: The original generation prompt (for context)

        Returns:
            Either a validated item dict, or the original seed (fallback)
        """
        current_item = failed_item
        current_feedback = feedback

        for attempt in range(self.MAX_ATTEMPTS):
            # Build regeneration prompt with specific feedback
            regen_prompt = self._build_regen_prompt(
                current_item, current_feedback, seed, learner_profile, attempt
            )

            # Regenerate
            response = await asyncio.to_thread(
                lambda: self.model.invoke(regen_prompt)
            )

            # Parse the regenerated item
            new_item = self._parse_regenerated_item(response.content, current_item)

            # Re-validate
            result = await self.validator.validate(
                new_item, seed, learner_profile, self.generator_model
            )

            if result.passed:
                new_item["validation_score"] = result.overall_score
                new_item["validator_model"] = result.validator_model
                new_item["regeneration_attempts"] = attempt + 1
                return new_item

            # Update for next attempt
            current_item = new_item
            current_feedback = result

        # All attempts failed → fall back to seed
        return self._fallback_to_seed(seed, learner_profile)

    def _build_regen_prompt(
        self,
        failed_item: dict,
        feedback: ValidationResult,
        seed: dict,
        learner_profile: dict,
        attempt: int,
    ) -> str:
        """Build a targeted regeneration prompt using validator feedback."""

        feedback_text = feedback.feedback_summary

        return f"""Your previous generated item FAILED quality validation. Fix the specific issues below.

Regenerate the item fixing ALL issues identified in the feedback. Keep the same skill, theme, and
employment context but fix the specific problems identified.

Respond in this exact JSON format (no markdown, no backticks):
{{
  "question_text": "...",
  "choices": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct_answer": "A",
  "correct_rationale": "...",
  "distractor_rationales": {{"B": "...", "C": "...", "D": "..."}},
  "passage_text": null
}}

=== ATTEMPT {attempt + 1} of {self.MAX_ATTEMPTS} ===

Theme: {failed_item.get('theme_applied', 'none')}
Interest: {failed_item.get('freeform_interest', 'none')}
Employment context: {failed_item.get('employment_context', 'none')}

=== SOURCE SEED (the canonical example — DO NOT modify the underlying skill being tested) ===
Question: {seed.get('question_text', '')}
Correct answer: {seed.get('correct_answer', '')}
Rationale: {seed.get('correct_rationale', '')}

=== YOUR FAILED ITEM ===
Question: {failed_item.get('question_text', '')}
Choices: {json.dumps(failed_item.get('choices', []))}
Correct answer: {failed_item.get('correct_answer', '')}

=== VALIDATION FEEDBACK (fix ALL of these) ===
{feedback_text}"""

    def _parse_regenerated_item(self, response_text: str, original: dict) -> dict:
        """Parse the model's regenerated item JSON."""
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            # If parsing fails, return original (it'll fail validation again → fallback)
            return original

        # Merge parsed fields into a copy of the original (preserving metadata)
        result = dict(original)
        for key in ["question_text", "choices", "correct_answer",
                     "correct_rationale", "distractor_rationales", "passage_text"]:
            if key in parsed:
                result[key] = parsed[key]

        result["item_id"] = f"regen_{uuid.uuid4().hex[:8]}"
        return result

    def _fallback_to_seed(self, seed: dict, learner_profile: dict) -> dict:
        """Fall back to the original seed with minimal theming.

        A wrong generated item is infinitely worse than an unthemed seed.
        When in doubt, serve the original.
        """
        return {
            "item_id": f"fallback_{uuid.uuid4().hex[:8]}",
            "question_text": seed.get("question_text", ""),
            "choices": seed.get("choices", []),
            "correct_answer": seed.get("correct_answer", ""),
            "correct_rationale": seed.get("correct_rationale", ""),
            "distractor_rationales": seed.get("distractor_rationales", {}),
            "passage_text": seed.get("passage_text"),
            "skill_id": seed.get("skill_id", ""),
            "chain_step": seed.get("chain_step"),
            "difficulty_b": seed.get("difficulty_b", 0.0),
            "discrimination_a": seed.get("discrimination_a", 1.0),
            "seed_id": seed.get("seed_id", ""),
            "theme_applied": "none",
            "freeform_interest": "",
            "employment_context": "",
            "modality_id": "",
            "validation_score": 0.0,
            "status": "seed_fallback",
            "cacheable": False,  # don't cache fallbacks
        }
