"""
praxis/curriculum/profile.py

Defines the structure of the curriculum a learner is studying.
This abstracts away hardcoded references to any specific curriculum,
allowing the platform to adapt to arbitrary domains (e.g., GED,
CompTIA A+, TEFL, etc.).

Key design decisions:
  - CurriculumProfile is a Pydantic model, not a DB row. It's loaded
    once at startup and referenced by ID throughout the session.
  - credential_name / credential_verb power dynamic prompt generation
    so agents can say "earn your GED" or "pass the CompTIA A+ exam"
    naturally without hardcoding.
  - The CURRICULUM_REGISTRY is the single source of truth. To add a
    new curriculum, add an entry here (later: load from DB).
"""

from typing import Optional
from pydantic import BaseModel, Field


class SubjectConfig(BaseModel):
    """A single subject within a curriculum."""
    id: str
    name: str
    description: str


class CurriculumProfile(BaseModel):
    """Complete definition of a learning curriculum.

    This model drives all curriculum-specific behavior across the platform:
    - Agent prompts use credential_name/credential_verb for natural language
    - Subject lists drive assessment routing, content lookup, and validation
    - Placement strategy determines initial assessment flow
    - employment_integration controls whether employment skills are woven in
    """
    id: str = Field(..., description="Unique ID for the curriculum (e.g., 'ged', 'comptia_a_plus')")
    name: str = Field(..., description="Human-readable name")
    target_audience: str = Field(..., description="e.g., 'adult learners', 'entry-level IT professionals'")
    assessment_standard: str = Field(..., description="e.g., 'GED testing standards', 'CompTIA objectives'")
    subjects: list[SubjectConfig] = Field(default_factory=list)

    # Credential metadata — powers dynamic prompt generation
    credential_name: str = Field("", description="What the learner earns (e.g., 'GED', 'CompTIA A+ Certification')")
    credential_verb: str = Field("earn", description="Action verb for prompts (e.g., 'earn your GED', 'pass the A+ exam')")

    # Session & pedagogy defaults
    session_length_default: int = Field(20, description="Default session length in minutes")
    employment_integration: bool = Field(True, description="Whether to weave employment competencies into learning")
    placement_strategy: str = Field("cat", description="Initial assessment type: 'cat', 'diagnostic', or 'self_report'")

    # Content configuration
    question_types: list[str] = Field(
        default_factory=lambda: ["multiple_choice", "drag_drop", "fill_in_blank"],
        description="Which question types this curriculum uses",
    )

    @property
    def subject_ids(self) -> list[str]:
        """Convenience: list of just the subject ID strings."""
        return [s.id for s in self.subjects]

    def get_subject(self, subject_id: str) -> Optional[SubjectConfig]:
        """Look up a subject by ID, or None if not found."""
        return next((s for s in self.subjects if s.id == subject_id), None)


# ──────────────────────────────────────────────────────────────
# Built-in curriculum profiles
# ──────────────────────────────────────────────────────────────

GED_PROFILE = CurriculumProfile(
    id="ged",
    name="GED",
    target_audience="adult learners seeking their high school equivalency",
    assessment_standard="GED testing standards",
    credential_name="GED",
    credential_verb="earn",
    session_length_default=20,
    employment_integration=True,
    placement_strategy="cat",
    question_types=["multiple_choice", "drag_drop", "fill_in_blank", "select_area", "drop_down", "extended_response"],
    subjects=[
        SubjectConfig(id="math", name="Mathematical Reasoning", description="Quantitative and algebraic problem solving"),
        SubjectConfig(id="rla", name="Reasoning Through Language Arts", description="Reading comprehension and writing"),
        SubjectConfig(id="science", name="Science", description="Life, physical, and earth/space science"),
        SubjectConfig(id="social_studies", name="Social Studies", description="History, economics, and geography"),
    ],
)


# ──────────────────────────────────────────────────────────────
# Curriculum registry — single source of truth
# ──────────────────────────────────────────────────────────────

CURRICULUM_REGISTRY: dict[str, CurriculumProfile] = {
    "ged": GED_PROFILE,
    # Future entries:
    # "comptia_a_plus": COMPTIA_A_PLUS_PROFILE,
    # "tefl": TEFL_PROFILE,
}

# Default curriculum ID used when no specific curriculum is set
DEFAULT_CURRICULUM_ID = "ged"


def get_curriculum(curriculum_id: str) -> CurriculumProfile:
    """Look up a curriculum profile by ID.

    Falls back to the default (GED) if the ID is not found.

    Args:
        curriculum_id: The curriculum to look up (e.g., 'ged', 'comptia_a_plus')

    Returns:
        The matching CurriculumProfile
    """
    return CURRICULUM_REGISTRY.get(curriculum_id, CURRICULUM_REGISTRY[DEFAULT_CURRICULUM_ID])


def get_current_curriculum() -> CurriculumProfile:
    """Get the default curriculum profile.

    DEPRECATED: Prefer get_curriculum(curriculum_id) with a specific ID
    from LearnerContext.curriculum_id. This function exists for backward
    compatibility during the migration.
    """
    return CURRICULUM_REGISTRY[DEFAULT_CURRICULUM_ID]
