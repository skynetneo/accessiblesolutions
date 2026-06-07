from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import (
    wrap_model_call, ModelRequest, ModelResponse,
    SummarizationMiddleware,
)
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langgraph.types import Command
from typing import Callable
from typing_extensions import NotRequired


# ── Intake State ───────────────────────────────────────────────

class IntakeState(AgentState):
    current_step: str       # "entry" | "resume_processing" | "probing" | "analysis" | "goal_setting" | "complete"
    learner_id: str
    resume_raw: NotRequired[str]
    work_profile_draft: NotRequired[dict]
    probing_areas_remaining: NotRequired[list[str]]
    goals_set: NotRequired[bool]


# ── Intake Tools (each transitions to next step) ──────────────

@tool
def accept_resume_text(
    text: str,
    runtime: ToolRuntime[None, IntakeState]
) -> Command:
    """Accept pasted resume text from the learner.
    Call this when the learner pastes their resume content."""
    return Command(update={
        "messages": [ToolMessage(
            content="Resume text received. Processing...",
            tool_call_id=runtime.tool_call_id,
        )],
        "resume_raw": text,
        "current_step": "resume_processing",
    })


@tool
def accept_uploaded_resume(
    extracted_text: str,
    file_format: str,
    runtime: ToolRuntime[None, IntakeState]
) -> Command:
    """Accept text extracted from an uploaded resume file.
    The frontend handles file upload and text extraction (PDF/DOCX→text).
    This receives the extracted text."""
    return Command(update={
        "messages": [ToolMessage(
            content=f"Resume uploaded ({file_format}). Extracted text received. Processing...",
            tool_call_id=runtime.tool_call_id,
        )],
        "resume_raw": extracted_text,
        "current_step": "resume_processing",
    })


@tool
def skip_resume(
    runtime: ToolRuntime[None, IntakeState]
) -> Command:
    """Learner doesn't have a resume or prefers to talk through their history.
    Skip to conversational probing."""
    return Command(update={
        "messages": [ToolMessage(
            content="No problem — let's build your profile through conversation.",
            tool_call_id=runtime.tool_call_id,
        )],
        "current_step": "probing",
        "probing_areas_remaining": [
            "work_history", "volunteer", "education",
            "certifications", "skills", "tools_software"
        ],
    })


@tool
def save_parsed_profile(
    profile_data: dict,
    gaps_to_probe: list[str],
    runtime: ToolRuntime[None, IntakeState]
) -> Command:
    """Save the structured profile parsed from resume text.
    Also identifies what's MISSING that we need to ask about.
    
    Args:
        profile_data: Structured work profile extracted from resume
        gaps_to_probe: Areas the resume didn't cover that we should ask about
            e.g. ["volunteer_work", "certifications", "tools_software", "reason_for_leaving"]
    """
    return Command(update={
        "messages": [ToolMessage(
            content=f"Profile parsed. {len(gaps_to_probe)} areas to explore conversationally.",
            tool_call_id=runtime.tool_call_id,
        )],
        "work_profile_draft": profile_data,
        "probing_areas_remaining": gaps_to_probe,
        "current_step": "probing" if gaps_to_probe else "goal_setting",
    })


@tool
def record_probed_info(
    area: str,
    data: dict,
    runtime: ToolRuntime[None, IntakeState]
) -> Command:
    """Record information gathered from conversational probing.
    
    Args:
        area: Which area was probed (e.g. "work_history", "certifications")
        data: Structured data extracted from the conversation
    """
    remaining = [a for a in runtime.state.get("probing_areas_remaining", []) if a != area]
    draft = runtime.state.get("work_profile_draft", {})
    
    # Merge new data into draft
    if area == "work_history":
        draft.setdefault("jobs", []).extend(data.get("jobs", []))
    elif area == "volunteer":
        draft.setdefault("jobs", []).extend(data.get("volunteer_positions", []))
    elif area == "education":
        draft.setdefault("education", []).extend(data.get("education", []))
    elif area == "certifications":
        draft.setdefault("certifications", []).extend(data.get("certifications", []))
    elif area == "skills":
        draft.setdefault("hard_skills", []).extend(data.get("skills", []))
    elif area == "tools_software":
        draft.setdefault("hard_skills", []).extend(data.get("tools", []))

    next_step = "probing" if remaining else "goal_setting"
    
    return Command(update={
        "messages": [ToolMessage(
            content=f"Got it — {area} recorded. {'Moving on...' if remaining else 'Almost done — lets talk about your goals.'}",
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
    runtime: ToolRuntime[None, IntakeState]
) -> Command:
    """Record the learner's career goals and constraints.
    All fields come from conversation — use 0 or "" for anything not discussed."""
    draft = runtime.state.get("work_profile_draft", {})
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
            content="Goals recorded. Let me analyze your profile and find opportunities.",
            tool_call_id=runtime.tool_call_id,
        )],
        "work_profile_draft": draft,
        "goals_set": True,
        "current_step": "analysis",
    })


@tool
def finalize_work_profile(
    analysis: dict,
    runtime: ToolRuntime[None, IntakeState]
) -> Command:
    """Finalize the work profile with analysis results and persist to store.
    
    Args:
        analysis: Contains transferable_skills, competency_gaps, bridge_opportunities
    """
    store = runtime.store
    user_id = runtime.state.get("learner_id", "")
    draft = runtime.state.get("work_profile_draft", {})
    
    # Merge analysis
    draft.update({
        "intake_complete": True,
        "transferable_skills": analysis.get("transferable_skills", []),
        "competency_gaps": analysis.get("competency_gaps", {}),
        "bridge_opportunities": analysis.get("bridge_opportunities", []),
    })
    
    # Persist to store
    store.put(("learners", "work_profile"), user_id, draft)
    
    return Command(update={
        "messages": [ToolMessage(
            content="Profile complete and saved. Ready for resume building, interview practice, or job research.",
            tool_call_id=runtime.tool_call_id,
        )],
        "work_profile_draft": draft,
        "current_step": "complete",
    })


# ── Intake Middleware (Dynamic Configuration per Step) ─────────

@wrap_model_call
def apply_intake_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """Dynamically configure the intake agent based on current_step."""
    step = request.state.get("current_step", "entry")
    
    # Define static parts of the prompt first
    configs = {
        "entry": {
            "prompt": """You're starting the employment profile intake.
            
            Ask the learner how they'd like to share their work history:
            1. Paste their resume text right into the chat
            2. Upload a resume file (PDF or Word)
            3. Just talk through it conversationally
            
            Be warm and low-pressure. Many adult learners feel anxious about resumes.
            If they don't have one, that's completely fine — say so explicitly.
            If they seem unsure, gently suggest talking through it: 
            "No resume? No problem. Let's just chat about what you've done."
            
            Do NOT ask for all three. Let them pick ONE path.""",
            "tools": [accept_resume_text, accept_uploaded_resume, skip_resume],
        },

        "resume_processing": {
            "prompt": """Parse this resume text into structured data.
            
            Extract EVERYTHING you can:
            - Job titles, employers, dates, responsibilities, achievements
            - Education, certifications, training
            - Skills, tools, software mentioned
            - Languages
            
            IMPORTANT: 
            - Normalize job titles (e.g., "cashier/stocker" → two entries or combined)
            - Preserve their original wording in raw_title
            - Don't invent anything not in the text
            - Identify GAPS — what's missing that we should ask about:
              * No dates? Flag for probing.
              * No education section? Flag.
              * Vague responsibilities ("various duties")? Flag for probing.
              * No volunteer/community work mentioned? Worth asking.
              * No certifications/training? Worth asking.
              * No tools/software mentioned? Worth asking.
            
            Call save_parsed_profile with the structured data AND the list of gaps.""",
            "tools": [save_parsed_profile],
        },

        "probing": {
            "prompt": """You're filling in gaps in the learner's work profile 
            through natural conversation.
            
            PROBING RULES:
            - Ask about ONE area at a time
            - Use open-ended questions, not checklists
            - Follow up on interesting details ("Oh you did inventory? Tell me more")
            - Listen for skills they don't realize they have:
              * "I trained the new people" → training/mentoring/communication
              * "I counted the drawer" → cash handling/accuracy/accountability
              * "I dealt with angry customers" → conflict resolution/interpersonal
            - When they say "I don't know" or "nothing special," probe gently:
              "What did a typical day look like?" is better than "List your responsibilities"
            - Accept whatever they tell you. Don't push if they're uncomfortable.
            - After gathering enough for one area, call record_probed_info
            
            AREA-SPECIFIC QUESTIONS:
            
            work_history:
              "What jobs have you had? Even short ones count."
              "What did you actually DO day to day?"
              "What were you good at? What did people come to you for?"
              
            volunteer:
              "Have you volunteered anywhere? Church, community, school events?"
              "Helped a neighbor's business? Coached a team? Organized anything?"
              
            education:
              "Any school beyond high school? Even if you didn't finish?"
              "Any training programs? Workshops? Online courses?"
              
            certifications:
              "Any licenses or certifications? Food handler, forklift, CPR, anything?"
              "Any company training you completed?"
              
            skills:
              "What are you good at that you could teach someone else?"
              "What do people ask you to help with?"
              
            tools_software:
              "What software or apps do you use for work? Even basics like email or spreadsheets count."
              "Any equipment you're trained on? POS systems, machinery, vehicles?"
            """,
            "tools": [record_probed_info],
        },

        "goal_setting": {
            "prompt": """Now let's talk about where the learner wants to go.
            
            Ask about their career goals. Key questions:
            
            1. FIELD: "What kind of work interests you? Or are you open to suggestions?"
               - If they name a field: great, record it
               - If they say "I don't know" or "whatever pays well": 
                 that's valid. Mark open_to_suggestions=True.
                 Ask what sounds APPEALING even if they're not sure.
                 "If you could shadow someone for a day, what job looks interesting?"
            
            2. TIMELINE: "How soon are you looking to make a move?"
               - "Right now, I need income" → 1-2 months
               - "After I get my credential" → align with their credential timeline
               - "Whenever" → 6 months default
            
            3. MONEY: "Are you comfortable sharing what you make now and what you're hoping for?"
               - If they share: record both
               - If they don't: that's fine, use 0. Don't push.
               
            4. CONSTRAINTS: "Anything that's a must-have or dealbreaker?"
               - Location, remote/in-person, schedule, physical limitations
               - "I can't work nights" is a dealbreaker
               - "I'd prefer days" is a preference (still record it)
            
            Gather all of this conversationally. Don't make it feel like a form.
            Once you have enough, call record_career_goals.""",
            "tools": [record_career_goals],
        },

        "analysis": {
            "prompt": """Analyze the learner's complete work profile and identify opportunities.
            
            ANALYSIS TASKS:
            
            1. TRANSFERABLE SKILLS: Map each job responsibility to roles it transfers to.
               - "Trained new employees" → Trainer, Team Lead, Onboarding Coordinator
               - "Managed inventory" → Logistics Coordinator, Supply Chain, Warehouse Manager
               - "Handled cash" → Bookkeeping, Accounts Receivable, Financial Services
               
            2. COMPETENCY MAPPING: Map their experience to the 12 workplace competencies.
               Score each 0.0-1.0 based on evidence from their actual history.
               Don't guess — only score what's supported by their reported experience.
               
            3. BRIDGE OPPORTUNITIES: Find roles that pay more with MINIMAL additional skills.
               The formula: (salary increase potential) / ( skills gap size)
               Higher ratio = better bridge opportunity.
               
            4. GAP ANALYSIS: What competencies/skills are weak relative to target roles?
               Prioritize gaps that the target curriculum + platform can actually close.
               
            Call finalize_work_profile with the analysis.""",
            "tools": [finalize_work_profile],
        },

        "complete": {
            "prompt": """Intake is complete. Present a summary to the learner.
            
            Show them:
            1. What you found in their background (validate them — they have more than they think)
            2. Their strongest transferable skills
            3. 2-3 immediate opportunities (bridge jobs within their timeline)
            4. What the platform will help them build toward
            
            Ask what they'd like to do next:
            - Work on their resume
            - Practice interviewing
            - Research specific job opportunities
            - Go back to learning (and come back to employment services later)
            
            Be encouraging without being patronizing. Concrete, not vague.""",
            "tools": [],
        },
    }

    config = configs.get(step, configs["entry"])
    prompt = config["prompt"]
    
    # Append dynamic state context at the END for cache efficiency
    dynamic_suffix = ""
    if step == "resume_processing":
        raw = request.state.get("resume_raw", "")
        dynamic_suffix = f"\n\nRESUME TEXT:\n{raw}"
    elif step == "probing":
        remaining = request.state.get("probing_areas_remaining", [])
        draft = request.state.get("work_profile_draft", {})
        dynamic_suffix = f"\n\nCURRENT PROFILE DRAFT:\n{_format_draft_summary(draft)}\n\nAREAS STILL TO EXPLORE: {remaining}\nCURRENT AREA TO PROBE: {remaining[0] if remaining else 'none'}"
    elif step == "goal_setting":
        draft = request.state.get("work_profile_draft", {})
        dynamic_suffix = f"\n\nTHEIR PROFILE SO FAR:\n{_format_draft_summary(draft)}"
    elif step == "analysis":
        draft = request.state.get("work_profile_draft", {})
        timeline = draft.get('timeline_months', 6)
        dynamic_suffix = f"\n\nFocus on their timeline constraint: {timeline} months.\n\nFULL PROFILE:\n{_format_draft_summary(draft)}"
    elif step == "complete":
        draft = request.state.get("work_profile_draft", {})
        dynamic_suffix = f"\n\nPROFILE SUMMARY:\n{_format_draft_summary(draft)}"
        
    final_prompt = prompt + dynamic_suffix

    return handler(request.override(
        system_prompt=final_prompt,
        tools=config["tools"],
    ))


def _format_draft_summary(draft: dict) -> str:
    """Format the work profile draft for injection into prompts."""
    if not draft:
        return "(No data collected yet)"
    
    parts = []
    jobs = draft.get("jobs", [])
    if jobs:
        parts.append(f"JOBS ({len(jobs)}):")
        for j in jobs:
            title = j.get("title", j.get("raw_title", "Unknown"))
            employer = j.get("employer", "")
            parts.append(f"  - {title}" + (f" at {employer}" if employer else ""))
            for r in j.get("responsibilities", [])[:3]:
                parts.append(f"    • {r}")
    
    edu = draft.get("education", [])
    if edu:
        parts.append(f"EDUCATION ({len(edu)}):")
        for e in edu:
            parts.append(f"  - {e.get('credential', '')} {e.get('institution', '')}")
    
    certs = draft.get("certifications", [])
    if certs:
        parts.append(f"CERTIFICATIONS: {', '.join(c.get('name', '') for c in certs)}")
    
    skills = draft.get("hard_skills", [])
    if skills:
        parts.append(f"SKILLS: {', '.join(skills)}")
    
    field = draft.get("desired_field", "")
    if field:
        parts.append(f"TARGET FIELD: {field}")
    elif draft.get("open_to_suggestions"):
        parts.append("TARGET FIELD: Open to suggestions")
        interests = draft.get("fields_of_interest", [])
        if interests:
            parts.append(f"  Interests: {', '.join(interests)}")
    
    timeline = draft.get("timeline_months", 0)
    if timeline:
        parts.append(f"TIMELINE: {timeline} months")
    
    return "\n".join(parts) if parts else "(Minimal data so far)"


# ── Build the Intake Agent ─────────────────────────────────────

def build_intake_agent(store, checkpointer):
    return create_agent(
        model="anthropic:claude-sonnet-4-6",  # Best at natural conversation
        tools=[
            accept_resume_text, accept_uploaded_resume, skip_resume,
            save_parsed_profile, record_probed_info,
            record_career_goals, finalize_work_profile,
        ],
        state_schema=IntakeState,
        middleware=[apply_intake_config],
        store=store,
        checkpointer=checkpointer,
        context_schema=LearnerContext,
    )
