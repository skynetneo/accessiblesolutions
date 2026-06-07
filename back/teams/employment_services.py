"""
praxis/teams/employment_services.py

Employment Services Team.

Pattern: Handoffs (intake) → Subagents (ongoing services)
The intake flow uses conversational handoffs to build a WorkProfile.
Once built, subagents handle resume building, interview coaching,
and job research — all grounded in the learner's REAL data.

Usage:
    from teams.employment_services import build_employment_services_team

    team = build_employment_services_team(checkpointer)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Callable, cast
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

from deepagents import create_deep_agent
from db.client import db
from db.tools_bridge import LearnerContext, log_stealth_observation
from model_factory import DEFAULT_BASE_MODEL, init_praxis_chat_model
from middleware.core import MicroThemingMiddleware


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


EMPLOYMENT_MODEL = os.environ.get("PRAXIS_EMPLOYMENT_MODEL", DEFAULT_BASE_MODEL)
EMPLOYMENT_SUMMARIZATION_MODEL = os.environ.get(
    "PRAXIS_EMPLOYMENT_SUMMARIZATION_MODEL",
    EMPLOYMENT_MODEL,
)
RESUME_MODEL = os.environ.get("PRAXIS_RESUME_MODEL", EMPLOYMENT_MODEL)
INTERVIEW_MODEL = os.environ.get("PRAXIS_INTERVIEW_MODEL", EMPLOYMENT_MODEL)
JOB_RESEARCH_MODEL = os.environ.get("PRAXIS_JOB_RESEARCH_MODEL", EMPLOYMENT_MODEL)


# ══════════════════════════════════════════════════════════════
# Part 1: Intake Agent (Handoffs Pattern)
# ══════════════════════════════════════════════════════════════

class IntakeState(AgentState):
    """State for the intake handoffs agent."""
    current_step: NotRequired[str]           # entry | resume_processing | probing | goal_setting | analysis | complete
    learner_id: NotRequired[str]
    resume_raw: NotRequired[str]
    work_profile_draft: NotRequired[dict]
    probing_areas_remaining: NotRequired[list]
    goals_set: NotRequired[bool]


# ── Intake tools ──────────────────────────────────────────────

@tool
def accept_resume_text(
    text: str,
    runtime: ToolRuntime[LearnerContext, IntakeState],
) -> Command:
    """Accept pasted resume text from the learner."""
    return Command(update={
        "messages": [ToolMessage(
            content="Resume text received. Processing...",
            tool_call_id=runtime.tool_call_id,
        )],
        "resume_raw": text,
        "current_step": "resume_processing",
    })


@tool
def skip_resume(
    runtime: ToolRuntime[LearnerContext, IntakeState],
) -> Command:
    """Learner doesn't have a resume — skip to conversational probing."""
    return Command(update={
        "messages": [ToolMessage(
            content="No problem — let's build your profile through conversation.",
            tool_call_id=runtime.tool_call_id,
        )],
        "current_step": "probing",
        "probing_areas_remaining": [
            "work_history", "volunteer", "education",
            "certifications", "skills", "tools_software",
        ],
    })


@tool
def save_parsed_profile(
    profile_data: dict,
    gaps_to_probe: list[str],
    runtime: ToolRuntime[LearnerContext, IntakeState],
) -> Command:
    """Save structured profile parsed from resume, with gaps to probe.

    Args:
        profile_data: Extracted structured work data
        gaps_to_probe: Areas the resume didn't cover
    """
    next_step = "probing" if gaps_to_probe else "goal_setting"
    return Command(update={
        "messages": [ToolMessage(
            content=f"Profile parsed. {len(gaps_to_probe)} areas to explore.",
            tool_call_id=runtime.tool_call_id,
        )],
        "work_profile_draft": profile_data,
        "probing_areas_remaining": gaps_to_probe,
        "current_step": next_step,
    })


@tool
def record_probed_info(
    area: str,
    data: dict,
    runtime: ToolRuntime[LearnerContext, IntakeState],
) -> Command:
    """Record info gathered from conversational probing for one area.

    Args:
        area: Which area was probed (work_history, volunteer, etc.)
        data: Structured data extracted from conversation
    """
    remaining = [a for a in runtime.state.get("probing_areas_remaining", []) if a != area]
    draft = dict(runtime.state.get("work_profile_draft", {}))

    merge_map = {
        "work_history": ("jobs", "jobs"),
        "volunteer": ("jobs", "volunteer_positions"),
        "education": ("education", "education"),
        "certifications": ("certifications", "certifications"),
        "skills": ("hard_skills", "skills"),
        "tools_software": ("hard_skills", "tools"),
    }
    target_key, source_key = merge_map.get(area, (area, area))
    draft.setdefault(target_key, []).extend(data.get(source_key, []))

    next_step = "probing" if remaining else "goal_setting"
    return Command(update={
        "messages": [ToolMessage(
            content=f"{area} recorded. {'Moving on...' if remaining else 'Almost done — lets talk goals.'}",
            tool_call_id=runtime.tool_call_id,
        )],
        "work_profile_draft": draft,
        "probing_areas_remaining": remaining,
        "current_step": next_step,
    })


@tool
def record_career_goals(
    desired_field: str,
    open_to_suggestions: bool,
    fields_of_interest: list[str],
    timeline_months: int,
    salary_current: int,
    salary_target: int,
    geographic_constraints: str,
    schedule_constraints: str,
    dealbreakers: list[str],
    runtime: ToolRuntime[LearnerContext, IntakeState],
) -> Command:
    """Record the learner's career goals and constraints.
    Use 0 or '' for anything not discussed.

    Args:
        desired_field: Target career field or '' if open
        open_to_suggestions: True if learner said 'I don't know'
        fields_of_interest: Fields that sound appealing
        timeline_months: How soon they want to transition
        salary_current: Current pay (0 if not shared)
        salary_target: Target pay (0 if not shared)
        geographic_constraints: Location/remote preferences
        schedule_constraints: Full-time, part-time, shifts
        dealbreakers: Things they won't do
    """
    draft = dict(runtime.state.get("work_profile_draft", {}))
    draft.update({
        "desired_field": desired_field,
        "open_to_suggestions": open_to_suggestions,
        "fields_of_interest": fields_of_interest,
        "timeline_months": timeline_months,
        "salary_current": salary_current,
        "salary_target": salary_target,
        "geographic_constraints": geographic_constraints,
        "schedule_constraints": schedule_constraints,
        "dealbreakers": dealbreakers,
    })
    return Command(update={
        "messages": [ToolMessage(
            content="Goals recorded. Analyzing your profile now.",
            tool_call_id=runtime.tool_call_id,
        )],
        "work_profile_draft": draft,
        "goals_set": True,
        "current_step": "analysis",
    })


@tool
def finalize_work_profile(
    transferable_skills: list[dict],
    competency_gaps: dict,
    bridge_opportunities: list[dict],
    runtime: ToolRuntime[LearnerContext, IntakeState],
) -> Command:
    """Finalize the work profile with analysis and persist to DB.

    Args:
        transferable_skills: Skill → which roles it transfers to
        competency_gaps: Competency → gap size relative to target
        bridge_opportunities: Roles that pay more with minimal delta
    """
    learner_id = runtime.context.learner_id
    draft = dict(runtime.state.get("work_profile_draft", {}))
    draft.update({
        "intake_complete": True,
        "transferable_skills": transferable_skills,
        "competency_gaps": competency_gaps,
        "bridge_opportunities": bridge_opportunities,
    })

    # Persist to Supabase
    db.client.table("work_profiles").upsert({
        "learner_id": learner_id,
        "profile_data": json.dumps(draft),
        "intake_complete": True,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }).execute()

    return Command(update={
        "messages": [ToolMessage(
            content="Profile complete and saved. Ready for resume, interview, or job services.",
            tool_call_id=runtime.tool_call_id,
        )],
        "work_profile_draft": draft,
        "current_step": "complete",
    })


# ── Intake middleware ─────────────────────────────────────────

# All prompts: static instructions first, dynamic state vars at end
INTAKE_CONFIGS = {
    "entry": {
        "prompt": (
            "You're starting the employment profile intake.\n\n"
            "Ask the learner how they'd like to share their work history:\n"
            "1. Paste their resume text into the chat\n"
            "2. Just talk through it conversationally\n\n"
            "Be warm and low-pressure. Many adult learners feel anxious about resumes.\n"
            "If they don't have one, say so explicitly — 'No resume? No problem.'\n"
            "Do NOT ask for all options. Let them pick ONE path.\n"
        ),
        "tools": [accept_resume_text, skip_resume],
    },
    "resume_processing": {
        "prompt": (
            "Parse the learner's resume text into structured data.\n\n"
            "Extract: job titles, employers, dates, responsibilities, achievements,\n"
            "education, certifications, skills, tools, languages.\n\n"
            "RULES:\n"
            "- Normalize job titles ('cashier/stocker' → combined entry)\n"
            "- Preserve original wording in raw fields\n"
            "- Don't invent anything not in the text\n"
            "- Identify GAPS to probe: missing dates, vague duties, no volunteer\n"
            "  section, no certifications, no tools/software mentioned\n\n"
            "Call save_parsed_profile with structured data AND gaps list.\n"
        ),
        "tools": [save_parsed_profile],
    },
    "probing": {
        "prompt": (
            "You're filling in gaps through natural conversation.\n\n"
            "RULES:\n"
            "- Ask about ONE area at a time, use open-ended questions\n"
            "- Listen for hidden skills they don't realize they have:\n"
            "  'I trained the new people' → training/mentoring/communication\n"
            "  'I counted the drawer' → cash handling/accuracy\n"
            "  'I dealt with angry customers' → conflict resolution\n"
            "- 'What did a typical day look like?' > 'List your responsibilities'\n"
            "- After enough for one area, call record_probed_info\n"
            "- Accept whatever they tell you. Don't push.\n"
        ),
        "tools": [record_probed_info],
    },
    "goal_setting": {
        "prompt": (
            "Now ask about career goals. Key questions:\n\n"
            "1. FIELD: 'What kind of work interests you? Or open to suggestions?'\n"
            "2. TIMELINE: 'How soon are you looking to make a move?'\n"
            "3. MONEY: 'Comfortable sharing what you make now and hoping for?'\n"
            "4. CONSTRAINTS: 'Anything that's a must-have or dealbreaker?'\n\n"
            "Gather conversationally. Don't make it feel like a form.\n"
            "Once you have enough, call record_career_goals.\n"
        ),
        "tools": [record_career_goals],
    },
    "analysis": {
        "prompt": (
            "Analyze the learner's complete work profile.\n\n"
            "1. TRANSFERABLE SKILLS: Map responsibilities → target roles\n"
            "2. COMPETENCY MAPPING: Score 12 competencies 0-1 from evidence only\n"
            "3. BRIDGE OPPORTUNITIES: pay_increase / gap_size — higher = better\n"
            "4. GAP ANALYSIS: Prioritize gaps the platform can close\n\n"
            "Call finalize_work_profile with the analysis.\n"
        ),
        "tools": [finalize_work_profile],
    },
    "complete": {
        "prompt": (
            "Intake is done. Present a brief summary: what you found in their\n"
            "background, strongest transferable skills, 2-3 immediate opportunities,\n"
            "and what the platform will help them build toward.\n"
            "Be encouraging without patronizing. Concrete, not vague.\n"
        ),
        "tools": [],
    },
}


@wrap_model_call
def apply_intake_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    step = request.state.get("current_step", "entry")
    config = INTAKE_CONFIGS.get(step, INTAKE_CONFIGS["entry"])

    # Append dynamic state context at the END for cache efficiency
    dynamic_suffix = ""
    if step == "resume_processing":
        raw = request.state.get("resume_raw", "")
        dynamic_suffix = f"\n\nRESUME TEXT:\n{raw}\n"
    elif step == "probing":
        remaining = request.state.get("probing_areas_remaining", [])
        dynamic_suffix = f"\n\nAREAS REMAINING: {remaining}\nCURRENT AREA: {remaining[0] if remaining else 'none'}\n"
    elif step in ("goal_setting", "analysis", "complete"):
        draft = request.state.get("work_profile_draft", {})
        dynamic_suffix = f"\n\nPROFILE SO FAR:\n{_format_draft(draft)}\n"

    prompt = config["prompt"] + dynamic_suffix
    return handler(
        request.override(
            system_message=SystemMessage(content=prompt),
            tools=config["tools"],
        )
    )


def _format_draft(draft: dict) -> str:
    if not draft:
        return "(No data yet)"
    parts = []
    jobs = draft.get("jobs", [])
    if jobs:
        parts.append(f"JOBS ({len(jobs)}):")
        for j in jobs[:5]:
            title = j.get("title", j.get("raw_title", "Unknown"))
            parts.append(f"  - {title}" + (f" at {j.get('employer', '')}" if j.get("employer") else ""))
    edu = draft.get("education", [])
    if edu:
        parts.append(f"EDUCATION: {len(edu)} entries")
    skills = draft.get("hard_skills", [])
    if skills:
        parts.append(f"SKILLS: {', '.join(skills[:10])}")
    field = draft.get("desired_field", "")
    if field:
        parts.append(f"TARGET: {field}")
    elif draft.get("open_to_suggestions"):
        parts.append("TARGET: Open to suggestions")
    return "\n".join(parts) if parts else "(Minimal data)"


def build_intake_agent(checkpointer=None):
    all_tools = [
        accept_resume_text, skip_resume, save_parsed_profile,
        record_probed_info, record_career_goals, finalize_work_profile,
    ]
    return create_agent(
        model=init_praxis_chat_model(EMPLOYMENT_MODEL),
        tools=all_tools,
        state_schema=IntakeState,
        context_schema=LearnerContext,
        middleware=cast(Any, [
            apply_intake_config,
            SummarizationMiddleware(
                model=init_praxis_chat_model(EMPLOYMENT_SUMMARIZATION_MODEL),
                trigger=("tokens", 4000),
                keep=("messages", 20),
                token_counter=lambda messages: count_tokens_approximately(messages),
            ),
        ]),
        checkpointer=checkpointer,
    )


# ══════════════════════════════════════════════════════════════
# Part 2: Service Subagents
# ══════════════════════════════════════════════════════════════

# ── Shared tools ──────────────────────────────────────────────

@tool
def get_work_profile(
    runtime: ToolRuntime[LearnerContext],
) -> str:
    """Retrieve the learner's complete work profile."""
    result = db.client.table("work_profiles") \
        .select("*") \
        .eq("learner_id", runtime.context.learner_id) \
        .maybe_single() \
        .execute()
    row = _as_dict(getattr(result, "data", None))
    if row:
        profile_data = row.get("profile_data", "{}")
        return profile_data if isinstance(profile_data, str) else "{}"
    return "No work profile found. Run intake first."


@tool
def get_competency_data(
    runtime: ToolRuntime[LearnerContext],
) -> str:
    """Retrieve demonstrated competencies from platform activity."""
    result = db.client.table("learner_competencies") \
        .select("*") \
        .eq("learner_id", runtime.context.learner_id) \
        .execute()
    return json.dumps(result.data or [])


@tool
def save_resume_version(
    resume_content: dict,
    version_notes: str,
    runtime: ToolRuntime[LearnerContext],
) -> str:
    """Save a new version of the learner's resume.

    Args:
        resume_content: The structured resume data
        version_notes: What changed in this version
    """
    learner_id = runtime.context.learner_id
    version_id = f"v_{int(time.time())}"
    db.client.table("resume_versions").insert({
        "learner_id": learner_id,
        "version_id": version_id,
        "content": json.dumps(resume_content),
        "notes": version_notes,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }).execute()
    return f"Resume saved as {version_id}"


# ── Subagent definitions ──────────────────────────────────────

resume_subagent = {
    "name": "resume-builder",
    "description": (
        "Builds and iterates on resumes and cover letters using the "
        "learner's REAL work history and demonstrated competencies."
    ),
    "system_prompt": (
        "You are an expert resume and cover letter writer.\n\n"
        "CRITICAL: Work ONLY with real data.\n"
        "- Call get_work_profile to load their actual history\n"
        "- Call get_competency_data for platform-demonstrated competencies\n"
        "- NEVER fabricate experience, skills, or achievements\n\n"
        "RESUME RULES:\n"
        "- Translate responsibilities into impact statements\n"
        "- Add ongoing learning progress as professional development (not centerpiece)\n"
        "- ATS-friendly: clean, no tables, standard headers\n"
        "- Call save_resume_version after each iteration\n\n"
        "COVER LETTER: Tailored to specific posting, lead with relevant "
        "experience, one page, 3-4 paragraphs.\n"
    ),
    "model": RESUME_MODEL,
    "tools": [get_work_profile, get_competency_data, save_resume_version],
}

interview_subagent = {
    "name": "interview-coach",
    "description": (
        "Runs mock interviews using the learner's REAL work history. "
        "Teaches them to articulate what they've actually done."
    ),
    "system_prompt": (
        "You are a professional interview coach.\n\n"
        "CRITICAL: All questions draw from their REAL experience.\n"
        "- Call get_work_profile first — every session\n"
        "- Questions must reference things they actually did\n\n"
        "APPROACH:\n"
        "1. BEHAVIORAL (STAR method) from actual work history\n"
        "2. SITUATIONAL based on target field\n"
        "3. COMMON questions everyone needs (tell me about yourself, etc.)\n\n"
        "FEEDBACK: Score content quality, specificity, confidence.\n"
        "Flag filler words, hedging. Teach quantification.\n\n"
        "LEVELS: 1=friendly+coaching → 5=full mock with pressure\n"
    ),
    "model": INTERVIEW_MODEL,
    "tools": [get_work_profile, get_competency_data, log_stealth_observation],
}

job_researcher_subagent = {
    "name": "job-researcher",
    "description": (
        "Researches real job opportunities based on the learner's actual "
        "profile, desired field, and timeline. Finds bridge jobs."
    ),
    "system_prompt": (
        "You are a career researcher and job search strategist.\n\n"
        "CRITICAL: Everything grounded in the learner's real data.\n"
        "- Call get_work_profile FIRST\n"
        "- Respect timeline, constraints, and dealbreakers\n\n"
        "STRATEGY:\n"
        "1. Load profile → identify transferable skills\n"
        "2. If desired field: search matching roles at their level\n"
        "3. If open: search across industries for skill premium\n"
        "4. BRIDGE FORMULA: pay_increase / gap_size\n"
        "5. TIMELINE TIERS: NOW (0-1mo), SOON (timeline), STRETCH (2x)\n\n"
        "Be concrete: titles, salary ranges, requirements.\n"
        "Respect dealbreakers absolutely.\n"
    ),
    "model": JOB_RESEARCH_MODEL,
    "tools": [get_work_profile, get_competency_data],
}


# ══════════════════════════════════════════════════════════════
# Part 3: Complete Team (Supervisor Deep Agent)
# ══════════════════════════════════════════════════════════════

def build_employment_services_team(checkpointer=None):
    """Build the complete employment services team.

    Intake agent (handoffs) for profile building.
    Subagents (resume, interview, jobs) for ongoing services.
    Supervisor routes between them.
    """
    intake_agent = build_intake_agent(checkpointer)

    @tool("run_intake", description=(
        "Run the employment profile intake. Use for NEW learners or "
        "when a learner wants to update their profile with new experience."
    ))
    def run_intake_tool(
        query: str,
        runtime: ToolRuntime[LearnerContext],
    ):
        learner_context = LearnerContext(
            learner_id=runtime.context.learner_id,
            session_id=runtime.context.session_id,
            curriculum_id=runtime.context.curriculum_id,
        )
        intake_thread_id = (
            f"employment_intake_{runtime.context.learner_id}_"
            f"{runtime.context.session_id or 'default'}"
        )
        result = intake_agent.invoke(
            {
                "messages": [{"role": "user", "content": query}],
            },
            config={"configurable": {"thread_id": intake_thread_id}},
            context=learner_context,
        )
        return result["messages"][-1].content

    subagents = [
        {**resume_subagent, "model": init_praxis_chat_model(RESUME_MODEL)},
        {**interview_subagent, "model": init_praxis_chat_model(INTERVIEW_MODEL)},
        {**job_researcher_subagent, "model": init_praxis_chat_model(JOB_RESEARCH_MODEL)},
    ]

    return create_deep_agent(
        name="employment-services",
        model=init_praxis_chat_model(EMPLOYMENT_MODEL),
        tools=[run_intake_tool, get_work_profile],
        subagents=cast(Any, subagents),
        system_prompt=(
            "You are the Employment Services Supervisor.\n\n"
            "FIRST: Check if the learner has a work profile (call get_work_profile).\n"
            "- No profile → run intake first\n"
            "- Profile exists but wants to update → run intake\n"
            "- Profile complete → route to appropriate service\n\n"
            "ROUTING:\n"
            "- 'Help me with my resume' → resume-builder\n"
            "- 'Practice interviewing' → interview-coach\n"
            "- 'Find me a job' → job-researcher\n"
            "- 'New job/cert/experience' → run_intake (update)\n\n"
            "NEVER fabricate data. Be encouraging about what they have.\n"
        ),
        middleware=[MicroThemingMiddleware()],
        checkpointer=checkpointer,
    )
