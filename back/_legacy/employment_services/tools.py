"""
upskill/employment_services/tools.py

Consolidated custom tools for the Employment Services team.
Standardized to work with LangGraph's ToolRuntime and Store API
for document persistence (resumes, research), while relying on
tools_bridge.py for core relational data (profiles, competencies).
"""

import time
from langchain.tools import tool, ToolRuntime
from db.tools_bridge import LearnerContext


@tool
def save_resume_version(
    resume_content: dict,
    version_notes: str,
    runtime: ToolRuntime[LearnerContext]
) -> str:
    """Save a new version of the learner's resume.
    
    Args:
        resume_content: Structured resume data (sections, bullets, etc.)
        version_notes: Brief description of what changed in this version
    """
    store = runtime.store
    user_id = runtime.context.learner_id
    
    version_id = f"v_{int(time.time())}"
    
    # Save historical version
    store.put(
        (user_id, "resumes"),
        version_id,
        {
            "content": resume_content,
            "notes": version_notes,
            "timestamp": time.time()
        }
    )
    
    # Update the "latest" pointer
    store.put(
        (user_id, "resumes"),
        "latest",
        {
            "version": version_id,
            "content": resume_content
        }
    )
    
    return f"Resume successfully saved as {version_id}."


@tool
def search_jobs(
    query: str,
    location: str,
    salary_min: int,
    job_type: str = "any",
    runtime: ToolRuntime[LearnerContext] = None
) -> str:
    """Search for real job listings matching criteria.
    
    In a production environment, this connects to job board APIs 
    like Indeed, LinkedIn, or Adzuna.
    
    Args:
        query: Job title or keywords
        location: City/state or "remote"
        salary_min: Minimum salary/hourly rate
        job_type: "full_time", "part_time", "contract", or "any"
    """
    # TODO: Integrate real job board API here.
    # Returning a structured mock response for now so the agent can parse it.
    return (
        f"[MOCK API RESPONSE] Found 3 matching jobs for '{query}' in {location} "
        f"starting above ${salary_min}/yr. \n"
        f"1. Junior {query} - ACME Corp - ${salary_min + 5000}/yr - Skills needed: Communication, Excel\n"
        f"2. Associate {query} - Globex - ${salary_min + 2000}/yr - Skills needed: Project Management\n"
        f"3. {query} Coordinator - Initech - ${salary_min + 10000}/yr - Skills needed: Problem Solving, Logistics"
    )


@tool
def analyze_job_fit(
    job_description: str,
    job_title: str,
    runtime: ToolRuntime[LearnerContext] = None
) -> str:
    """Compare a specific job posting against the learner's actual profile.
    
    Args:
        job_description: The full job posting text
        job_title: The job title
    """
    # Rather than returning the profile to the LLM (which it already fetched), 
    # we return a structured directive forcing the LLM to output the exact delta.
    return (
        f"Please proceed to analyze the '{job_title}' role using the profile data you hold. "
        f"Ensure your response calculates and clearly formats: \n"
        f"1. Existing skill matches (%)\n"
        f"2. Gaps (what's missing)\n"
        f"3. Estimated time to close gap\n"
        f"4. Bridge viability score (Pay Increase / Gap Size)"
    )


@tool
def save_job_research(
    research_summary: dict,
    runtime: ToolRuntime[LearnerContext]
) -> str:
    """Save job research results for the learner to review later.
    
    Args:
        research_summary: Structured data containing the roles researched,
                          skill gaps, and recommended actions.
    """
    store = runtime.store
    user_id = runtime.context.learner_id
    
    research_id = f"research_{int(time.time())}"
    store.put(
        (user_id, "job_research"),
        research_id,
        {
            **research_summary,
            "timestamp": time.time()
        }
    )
    return f"Research saved successfully as {research_id}."
