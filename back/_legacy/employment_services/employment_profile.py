from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class JobEntry(BaseModel):
    """A single work or volunteer position."""
    title: str                          # normalized job title
    raw_title: str = ""                 # what they actually wrote/said
    employer: str = ""
    industry: str = ""
    is_volunteer: bool = False
    start_date: str = ""                # "2019-03" or "about 3 years ago"
    end_date: str = ""                  # "" = current
    is_current: bool = False
    responsibilities: list[str] = []    # what they actually did
    skills_demonstrated: list[str] = [] # mapped to competencies
    tools_used: list[str] = []          # software, equipment, etc.
    achievements: list[str] = []        # quantifiable where possible
    reason_left: str = ""               # optional, useful for interview prep


class EducationEntry(BaseModel):
    """Formal or informal education."""
    institution: str = ""
    credential: str = ""                # "Certification in progress", "Some college", "Certificate"
    field: str = ""
    status: str = ""                    # "completed", "in_progress", "incomplete"
    year: str = ""
    relevant_coursework: list[str] = []


class CertificationEntry(BaseModel):
    """Professional certifications, licenses, training."""
    name: str
    issuer: str = ""
    year: str = ""
    is_current: bool = True
    relevance: str = ""                 # how it maps to target roles


class WorkProfile(BaseModel):
    """The complete professional profile built from real learner data.
    This is NOT fabricated. Every field comes from either:
    - Parsed resume text
    - Conversational probing
    - Direct learner input
    """
    learner_id: str

    # Source tracking
    resume_raw_text: str = ""           # original pasted/extracted text
    resume_uploaded: bool = False
    intake_method: str = ""             # "resume_upload", "resume_paste", "conversation", "hybrid"
    intake_complete: bool = False

    # Work history
    jobs: list[JobEntry] = []
    total_years_experience: float = 0.0
    industries: list[str] = []          # unique industries worked in

    # Education
    education: list[EducationEntry] = []
    curriculum_id: str = ""              # which curriculum the learner is on
    curriculum_status: str = "in_progress"  # from the platform itself

    # Certifications & training
    certifications: list[CertificationEntry] = []

    # Skills (extracted from actual history, NOT assumed)
    hard_skills: list[str] = []         # specific tools, software, techniques
    soft_skills_claimed: list[str] = [] # what they say they're good at
    soft_skills_demonstrated: dict[str, float] = {}  # mapped to 12 competencies from platform data
    languages: list[str] = []

    # Career goals (from the learner, not from us)
    desired_field: str = ""             # specific field or "" if open
    open_to_suggestions: bool = False   # true if they said "I don't know" or "whatever pays well"
    fields_of_interest: list[str] = []  # even if open, what sounds appealing
    salary_current: int = 0             # what they make now (if shared)
    salary_target: int = 0              # what they want
    timeline_months: int = 0            # how soon they want to transition
    geographic_constraints: str = ""    # location, remote preference, commute limit
    schedule_constraints: str = ""      # full-time, part-time, shifts, etc.
    dealbreakers: list[str] = []        # things they won't do

    # Analysis (generated after intake)
    transferable_skills: list[dict] = []   # skill → which roles it transfers to
    competency_gaps: dict[str, float] = {} # competency → gap size relative to target
    bridge_opportunities: list[dict] = []  # roles that pay more with minimal delta
