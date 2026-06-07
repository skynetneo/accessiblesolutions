"""
upskill/content_team/schemas.py

Data models for the Content Generation Team.

Key principle: Content is always generated from a seed (DB) + learner profile,
never from scratch. Generated items go through cross-provider validation before
reaching the learner or being cached.
"""

from __future__ import annotations
from typing import Annotated, Literal, Optional
from pydantic import BaseModel, Field
from operator import add
import uuid


# ---------------------------------------------------------------------------
# Content type taxonomy
# ---------------------------------------------------------------------------

QuestionType = Literal[
    "multiple_choice",      # Standard 4-option MC
    "drag_drop",            # Ordering / matching
    "fill_in_blank",        # Short answer numeric or text
    "select_area",          # Click on diagram region
    "drop_down",            # Inline select from options
    "extended_response",    # Essay / long-form response
]

# Subject identifiers are validated at runtime against the active CurriculumProfile.
SubjectKey = str

ScaffoldLevel = Literal[
    "independent",          # No hint, just the question
    "general_strategy",     # Level 1: broad approach hint
    "specific_direction",   # Level 2: pointed hint
    "worked_example",       # Level 3: similar solved problem
    "step_by_step",         # Level 4: guided decomposition
]

ContentStatus = Literal[
    "draft",                # Generated, not yet validated
    "validated",            # Passed cross-provider validation
    "rejected",             # Failed validation (with reason)
    "cached",               # In DB pool, available for other learners
    "delivered",            # Sent to a learner
]


# ---------------------------------------------------------------------------
# Seed item (from DB) — the template content generation is based on
# ---------------------------------------------------------------------------

class SeedItem(BaseModel):
    """
    A validated, authoritative seed example from the content DB.
    Content agents generate themed variations of these.
    """
    seed_id: str
    subject: SubjectKey
    skill_id: str
    question_type: QuestionType
    
    # IRT parameters (established from pilot data)
    difficulty_b: float          # -3 to +3
    discrimination_a: float      # 0.5 to 2.5
    
    # The canonical question (unthemed, plain English)
    question_text: str
    choices: list[str]           # For MC; empty for extended_response
    correct_answer: str
    correct_rationale: str       # Why the answer is correct
    
    # Distractor rationales (what misconception each wrong answer represents)
    distractor_rationales: dict[str, str] = Field(default_factory=dict)
    
    # Curriculum standard alignment
    curriculum_standard: str            # e.g. "MP.1" or "RLA.R.2.1"
    
    # Employment contexts this skill maps to
    employment_contexts: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Generated content item
# ---------------------------------------------------------------------------

class GeneratedItem(BaseModel):
    """
    A themed, learner-specific content item generated from a seed.
    Must pass validation before delivery.
    """
    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    seed_id: str                         # Which seed this was based on
    
    subject: SubjectKey
    skill_id: str
    question_type: QuestionType
    
    # IRT parameters inherited from seed (theme doesn't change difficulty)
    difficulty_b: float
    discrimination_a: float
    
    # Themed content
    theme_applied: str                   # e.g. "gaming", "hello kitty"
    freeform_interest: Optional[str]     # e.g. "rick and morty"
    
    # The themed question
    question_text: str
    
    # For MC: themed choices; for extended_response: prompt text
    choices: list[str] = Field(default_factory=list)
    correct_answer: str
    correct_rationale: str
    distractor_rationales: dict[str, str] = Field(default_factory=dict)
    
    # Scaffolding hints at each level
    hints: dict[ScaffoldLevel, str] = Field(default_factory=dict)
    
    # Modality assets (descriptions of what to generate/fetch)
    visual_asset_description: Optional[str] = None   # For visual learners
    audio_script: Optional[str] = None               # For auditory learners
    
    # Employment bridge text (shown when employment_context_preferred=True)
    employment_bridge: Optional[str] = None
    
    # Validation state
    status: ContentStatus = "draft"
    validation_score: Optional[float] = None         # 0.0-1.0
    validation_feedback: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    # Cacheable for other learners with same theme/skill?
    cacheable: bool = True
    
    # Generation metadata
    generator_model: str = ""            # Which model generated this
    validator_model: str = ""            # Which model validated this
    generation_attempts: int = 1


# ---------------------------------------------------------------------------
# Lesson plan — sequence of items for a session
# ---------------------------------------------------------------------------

class LessonPlan(BaseModel):
    """
    An ordered sequence of content items for a learning session.
    Built by the LessonDesignerAgent from the learner's ZPD and skill gaps.
    """
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    learner_id: str
    session_id: str
    subject: SubjectKey
    
    # Target skill for this lesson
    target_skill_id: str
    
    # Warm-up: 1-2 mastered items (behavioral momentum)
    warmup_item_ids: list[str] = Field(default_factory=list)
    
    # Core instruction sequence
    instruction_item_ids: list[str] = Field(default_factory=list)
    
    # Practice items at target difficulty
    practice_item_ids: list[str] = Field(default_factory=list)
    
    # Generalization: same skill, different context (employment bridge)
    generalization_item_ids: list[str] = Field(default_factory=list)
    
    # Estimated session duration in minutes
    estimated_minutes: int = 25
    
    # ZPD target: items calibrated to this theta range
    target_theta_min: float = -0.5
    target_theta_max: float = 0.5


# ---------------------------------------------------------------------------
# Validation result from cross-provider validator
# ---------------------------------------------------------------------------

class ValidationResult(BaseModel):
    """
    Result from the cross-provider content validator.
    Generator: GLM-4 (or similar)
    Validator: Gemini Pro (different provider — bias removal)
    """
    item_id: str
    
    # Core accuracy check
    math_correct: Optional[bool] = None         # Only for math items
    answer_unambiguous: bool = True             # Is correct answer clearly correct?
    distractors_plausible: bool = True          # Do wrong answers represent real errors?
    
    # Curriculum alignment
    matches_seed_difficulty: bool = True        # Generated difficulty ≈ seed difficulty
    matches_curriculum_standard: bool = True           # Still tests the right skill
    
    # Theme/content quality
    theme_coherent: bool = True                 # Theming makes sense, not forced
    employment_bridge_accurate: bool = True     # Employment context is factually correct
    age_appropriate: bool = True                # Appropriate for adult learners
    
    # Scaffolding quality
    hints_progressive: bool = True             # Each hint level adds more support
    hints_accurate: bool = True                # Hints don't reveal answer prematurely
    
    # Overall
    approved: bool = False
    confidence_score: float = 0.0              # 0.0-1.0
    rejection_reasons: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    validator_model: str = ""


# ---------------------------------------------------------------------------
# Content generation graph state
# ---------------------------------------------------------------------------

class ContentGraphState(BaseModel):
    """State schema for the Content Generation Team LangGraph."""
    
    # Input: learner context (read from LearnerProfile)
    learner_id: str = ""
    subject: SubjectKey = "math"
    target_skill_id: str = ""
    target_theta: float = 0.0
    theme: str = "gaming"
    freeform_interests: list[str] = Field(default_factory=list)
    learning_style: str = "visual"
    employment_goal: str = "default"
    employment_context_preferred: bool = True
    
    # Seeds fetched from DB
    seed_items: list[SeedItem] = Field(default_factory=list)
    
    # Generated items (accumulate via reducer)
    generated_items: Annotated[list[GeneratedItem], add] = Field(default_factory=list)
    
    # Validated items (passed cross-provider check)
    validated_items: Annotated[list[GeneratedItem], add] = Field(default_factory=list)
    
    # Rejected items with feedback (for regeneration loop)
    rejected_items: Annotated[list[dict], add] = Field(default_factory=list)
    
    # Final lesson plan
    lesson_plan: Optional[LessonPlan] = None
    
    # Scaffolding items generated alongside content
    scaffold_items: Annotated[list[dict], add] = Field(default_factory=list)
    
    # Generation loop control
    generation_attempts: int = 0
    max_attempts: int = 3
    
    # How many validated items we need before building lesson plan
    items_needed: int = 8
    
    # Messages (for debugging / supervisor review)
    messages: Annotated[list[dict], add] = Field(default_factory=list)
    
    # Errors
    errors: Annotated[list[str], add] = Field(default_factory=list)
