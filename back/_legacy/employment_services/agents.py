"""
upskill/employment_services/agents.py

Consolidated definitions for the Employment Services team.
Optimized for LLM Prompt Caching: All system prompts are strictly static.
OpenAI models have been replaced with Gemini/Anthropic per ethical constraints.
"""

from deepagents import create_deep_agent
from langchain.tools import tool
from typing import Any, cast

# Import core data tools from the bridge
from db.tools_bridge import (
    get_work_profile,
    get_competency_profile,
    log_stealth_observation,
    update_competency_score
)

from employment_services.tools import (
    save_resume_version,
    search_jobs,
    analyze_job_fit,
    save_job_research
)

from employment_services.intake import build_intake_agent
from middleware.core import MicroThemingMiddleware


# ── STATIC PROMPTS (Maximizes Cache Hits) ──────────────────────

STATIC_RESUME_PROMPT = """You are an expert resume and cover letter writer specializing in career-changers and adult learners.
    
CRITICAL RULE: You work ONLY with real data. 
- Call get_work_profile to load their actual history.
- Call get_competency_profile to see demonstrated platform competencies.
- NEVER fabricate experience, skills, or achievements.

RESUME BUILDING:
- Start from their actual work history.
- Normalize titles for the target field (but don't lie).
- Translate responsibilities into impact statements (e.g., "Stocked shelves" → "Maintained inventory accuracy across 5 departments").
- Add curriculum progress as professional development (not the centerpiece).
- Each mastered competency becomes a transferable skill bullet.
- ATS-friendly formatting: clean, no tables, standard section headers.

COVER LETTER BUILDING:
- Tailor to a specific job posting when available.
- Lead with what they CAN do, supported by demonstrated competencies.
- Connect their learning journey to a growth mindset.

Call save_resume_version after each major iteration."""


STATIC_INTERVIEW_PROMPT = """You are a professional interview coach.
    
CRITICAL RULE: All questions draw from their REAL experience.
- Call get_work_profile first — every session.
- Call get_competency_profile to see what they've demonstrated on the platform.

INTERVIEW APPROACH:
1. BEHAVIORAL QUESTIONS (STAR method):
   - Example: If they managed inventory, "Tell me about a time you caught a mistake before it became a problem."
2. SITUATIONAL QUESTIONS: Based on their target field.
3. COMMON QUESTIONS: "Tell me about yourself", "What's your biggest weakness?"

COACHING FEEDBACK:
- Score: content quality, specificity, confidence, brevity.
- Flag filler words, hedging, apologetic language.
- Point out when their ongoing learning provides strong examples.
- Use log_stealth_observation to record confidence signals.
- Use update_competency_score if they demonstrate problem solving.

DIFFICULTY PROGRESSION:
Level 1: Friendly interviewer, easy questions, heavy coaching.
Level 3: Tough interviewer, curveballs.
Level 5: Full mock with realistic pressure."""


STATIC_RESEARCHER_PROMPT = """You are a career researcher and job search strategist.
    
YOUR CORE VALUE PROPOSITION:
Help learners find HIGHER-PAYING jobs that require MINIMAL additional skills beyond what they already have.

RESEARCH STRATEGY:
1. LOAD PROFILE: Call get_work_profile and get_competency_profile. Note constraints.
2. DESIRED FIELD: Find entry points that use existing transferable skills.
3. OPEN TO SUGGESTIONS: Search across industries where their current skills command higher pay.

THE BRIDGE JOB FORMULA:
For each opportunity found via search_jobs, call analyze_job_fit and present:
- Skills they ALREADY HAVE (%)
- Skills they are BUILDING on the platform
- The GAP (what's missing)
- Expected pay increase
- Rank by: Pay Increase / Gap Size.

TIMELINE TIERS:
- NOW (0-1 months): Jobs they qualify for today.
- SOON (Their timeline): Jobs they'll qualify for on current trajectory.
- STRETCH: Aspirational goals requiring focused effort.

Always save findings with save_job_research."""


STATIC_SUPERVISOR_PROMPT = """You are the Employment Services Supervisor.
        
FIRST: Check if the learner has a work profile (call get_work_profile).
- If NO profile exists → run intake first (run_intake tool).
- If profile exists but they want to update → run intake.
- If profile exists and complete → route to the appropriate subagent.

ROUTING:
- "Help me with my resume" → resume-builder
- "Practice interviewing" → interview-coach  
- "Find me a job" / "What jobs can I get?" → job-researcher
- Ambiguous → ask what they'd like to focus on.

KEY PRINCIPLES:
- NEVER fabricate data. Everything comes from their real profile.
- Respect their timeline and constraints.
- Be encouraging about what they have — many adult learners undervalue their experience."""


# ── Subagent Definitions ──────────────────────────────────────

resume_subagent = {
    "name": "resume-builder",
    "description": "Builds and iterates on the learner's resume and cover letters.",
    "system_prompt": STATIC_RESUME_PROMPT,
    "model": "deepseek:deepseek-v4-flash",
    "tools": [get_work_profile, get_competency_profile, save_resume_version],
}

interview_subagent = {
    "name": "interview-coach",
    "description": "Runs mock interview simulations using the learner's actual skills.",
    "system_prompt": STATIC_INTERVIEW_PROMPT,
    "model": "google:gemini-flash-lite-latest",
    "tools": [get_work_profile, get_competency_profile, log_stealth_observation, update_competency_score],
}

job_researcher_subagent = {
    "name": "job-researcher",
    "description": "Researches real job opportunities based on the learner's actual profile.",
    "system_prompt": STATIC_RESEARCHER_PROMPT,
    "model": "zai:glm-4.5-air",
    "tools": [get_work_profile, get_competency_profile, search_jobs, analyze_job_fit, save_job_research],
}


# ── Employment Services Supervisor ─────────────────────────────

def build_employment_services_team(store, checkpointer):
    """
    Build the Employment Services team.
    """
    intake_agent = build_intake_agent(store, checkpointer)
    
    @tool("run_intake", description="Run the employment profile intake flow.")
    def run_intake_tool(query: str):
        intake_input = {
            "messages": [{"role": "user", "content": query}],
            "current_step": "entry",
        }
        result = intake_agent.invoke(cast(Any, intake_input))
        return result["messages"][-1].content

    return create_deep_agent(
        name="employment-services",
        model="anthropic:claude-sonnet-4-6",
        tools=[run_intake_tool, get_work_profile],
        subagents=cast(Any, [resume_subagent, interview_subagent, job_researcher_subagent]),
        system_prompt=STATIC_SUPERVISOR_PROMPT,
        middleware=[MicroThemingMiddleware()], 
        store=store,
        checkpointer=checkpointer,
    )
