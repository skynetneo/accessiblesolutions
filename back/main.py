"""
unified_praxis_main.py

Unified FastAPI + CopilotKit entrypoint for Praxis.

Architecture:
    FastAPI
      ├─ REST endpoints: health, webhooks, narration, research, learner, resume, filter
      └─ /api CopilotKit endpoint
            └─ Supervisor Deep Agent
                 ├─ learning subagent      -> onboarding, placement, coaching
                 ├─ access_career subagent -> jobs, resume, cover letters
                 └─ access_fyndr subagent  -> food, housing, legal aid, community resources

This file assumes the existing repo modules from both source blocks still exist:
    orchestration/, teams/, curriculum/, middleware/, services/, db/, model_factory.py,
    tools.py, models.py, safe_agui_agent.py, etc.
"""

from __future__ import annotations

import atexit
import asyncio
import hmac
import importlib
import json
import math
import os
import socket
import time
from typing import Annotated, Any, Dict, List, NotRequired, Optional, cast
import sqlite3
from dotenv import load_dotenv

load_dotenv()

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# -----------------------------------------------------------------------------
# Compatibility patches
# -----------------------------------------------------------------------------

import langchain_core.tools

if not hasattr(langchain_core.tools, "InjectedToolCallId"):
    langchain_core.tools.InjectedToolCallId = getattr(
        langchain_core.tools,
        "InjectedToolArg",
        None,
    )

from langchain.tools import ToolRuntime, tool
from langchain_core.tools import InjectedToolArg

# Prefer the subagent-capable import used in AccessFyndr. Fall back for older code.
try:
    from deepagents.graph import create_deep_agent
except ImportError:  # pragma: no cover - compatibility only
    from deepagents import create_deep_agent  # type: ignore

from deepagents.backends.state import StateBackend
from deepagents.middleware.subagents import SubAgent

from copilotkit import CopilotKitMiddleware, CopilotKitState, LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint

try:
    from safe_agui_agent import SafeLangGraphAGUIAgent
except ImportError:  # pragma: no cover - optional local wrapper from Block 2
    SafeLangGraphAGUIAgent = LangGraphAGUIAgent  # type: ignore

try:
    from langchain_tavily import TavilySearch
except ImportError:  # pragma: no cover - app can run without fallback web search
    TavilySearch = None  # type: ignore

# Praxis imports
from curriculum.skill_graph import SkillGraph
from db.client import db, get_async_client
from db.tools_bridge import LearnerContext
from middleware.core import (
    EmploymentStructuralMiddleware,
    MicroThemingMiddleware,
    StealthAssessmentMiddleware,
    ZPDMiddleware,
)
from model_factory import DEFAULT_BASE_MODEL, init_praxis_chat_model
from orchestration.ikigai_engine import IkigaiEngine
from orchestration.momentum import ItemType
from orchestration.session_manager import SessionManager, SessionPhase
from teams.assessment import build_assessment_team
from teams.coaching import build_coaching_team
from teams.gamification import GamificationEngine
from teams.research.research_agent import agent as _research_agent

# AccessFyndr / AccessCareer imports from Block 2
from db.db import filter_resources
from models import REPLY_MODEL, ROUTING_MODEL
from tools import (
    filter_agencies,
    find_agencies,
    navigate_to_page,
    recommend_assistance,
    save_agencies,
    switch_career_view,
    update_career_state,
)


# -----------------------------------------------------------------------------
# Shared JSON safety / CopilotKit middleware
# -----------------------------------------------------------------------------


def _as_dict(value: Any) -> dict[str, Any]:
    """Safely narrow unknown JSON-like values to a dictionary."""
    return value if isinstance(value, dict) else {}


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    """Safely narrow unknown JSON-like values to a list of dictionaries."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _json_safe(value: Any) -> Any:
    """Convert CopilotKit frontend context into JSON-safe data."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "model_dump"):
        try:
            return _json_safe(value.model_dump())
        except Exception:
            pass
    if hasattr(value, "dict"):
        try:
            return _json_safe(value.dict())
        except Exception:
            pass
    return repr(value)


class SafeCopilotKitMiddleware(CopilotKitMiddleware):
    """CopilotKit middleware that never lets non-JSON context abort a stream."""

    def before_agent(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        if not isinstance(state, dict):
            return super().before_agent(state, runtime)

        copilotkit_state = state.get("copilotkit", {})
        if not isinstance(copilotkit_state, dict):
            copilotkit_state = {}

        app_context = copilotkit_state.get("context")

        # If no frontend context exists, do not fall back to runtime.context.
        # In this app runtime.context is operational state and can contain
        # non-serializable objects.
        if not app_context:
            return None

        # Avoid double-wrapping if the supervisor has already sanitized it.
        if isinstance(app_context, list):
            typed_context = app_context
        else:
            safe_context = _json_safe(app_context)
            try:
                json.dumps(safe_context)
            except TypeError:
                safe_context = repr(safe_context)
            typed_context = safe_context if isinstance(safe_context, list) else []

        next_state = {
            **state,
            "copilotkit": {
                **copilotkit_state,
                "context": typed_context,
            },
        }
        return super().before_agent(cast(Any, next_state), runtime)


# -----------------------------------------------------------------------------
# Runtime configuration
# -----------------------------------------------------------------------------

ORCHESTRATOR_MODEL = os.environ.get("PRAXIS_ORCHESTRATOR_MODEL", DEFAULT_BASE_MODEL)
ORCHESTRATOR_AGENT_NAME = os.environ.get(
    "PRAXIS_ORCHESTRATOR_AGENT_NAME",
    "praxis-supervisor",
)
LEARNING_AGENT_NAME = os.environ.get("PRAXIS_LEARNING_AGENT_NAME", "learning")
PUBLIC_AGENT_NAME = os.environ.get("PRAXIS_AGENT_NAME", "praxis")
SERVICE_NAME = os.environ.get("PRAXIS_SERVICE_NAME", "praxis")

CURRICULUM_WEBHOOK_BEARER_ENV = "PRAXIS_CURRICULUM_WEBHOOK_BEARER_TOKEN"
RESEARCH_SKILL_BEARER_ENV = "PRAXIS_RESEARCH_SKILL_BEARER_TOKEN"
NARRATION_BEARER_ENV = "PRAXIS_NARRATION_BEARER_TOKEN"

CHECKPOINTER_DB_URI_ENV_VARS = (
    "LANGGRAPH_DB_URI",
    "SUPABASE_DB_URI",
    "SUPABASE_POSTGRES_URL",
    "DATABASE_URL",
)
_checkpointer_context: Any = None


def _runtime_env_name() -> str:
    return (
        os.environ.get("PRAXIS_ENV")
        or os.environ.get("ENVIRONMENT")
        or os.environ.get("FASTAPI_ENV")
        or "development"
    ).strip().lower()


def _is_local_runtime() -> bool:
    return _runtime_env_name() in {"dev", "development", "local", "test"}


def _validate_required_env() -> None:
    required = ("SUPABASE_URL", "SUPABASE_SERVICE_KEY")
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))


def _build_bearer_auth_dependency(secret_env_var: str, *, required: bool = True):
    """Return a FastAPI dependency that validates a Bearer token."""

    async def _bearer_auth(
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> None:
        expected_token = os.environ.get(secret_env_var, "").strip()
        if not expected_token:
            if not required:
                return
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Server auth misconfiguration: {secret_env_var} is not set",
            )

        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )

        scheme, _, token = authorization.partition(" ")
        token = token.strip()
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not hmac.compare_digest(token, expected_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return _bearer_auth


require_curriculum_webhook_auth = _build_bearer_auth_dependency(CURRICULUM_WEBHOOK_BEARER_ENV)
require_research_skill_auth = _build_bearer_auth_dependency(RESEARCH_SKILL_BEARER_ENV)
require_narration_auth = _build_bearer_auth_dependency(
    NARRATION_BEARER_ENV,
    required=not _is_local_runtime(),
)


def _get_checkpointer_db_uri() -> str | None:
    for env_var in CHECKPOINTER_DB_URI_ENV_VARS:
        value = os.environ.get(env_var, "").strip()
        if value:
            return value
    return None


def get_checkpointer():
    """Return PostgresSaver in production-like configs, else MemorySaver."""
    db_uri = _get_checkpointer_db_uri()
    if db_uri:
        try:
            postgres_module = importlib.import_module("langgraph.checkpoint.postgres")
            PostgresSaver = postgres_module.PostgresSaver
        except ImportError as exc:
            raise RuntimeError(
                "Checkpoint persistence is configured, but the Postgres checkpointer "
                "dependency is missing. Install 'langgraph-checkpoint-postgres' and "
                f"set one of {CHECKPOINTER_DB_URI_ENV_VARS}."
            ) from exc

        global _checkpointer_context
        _checkpointer_context = PostgresSaver.from_conn_string(db_uri)
        checkpointer = _checkpointer_context.__enter__()
        atexit.register(_checkpointer_context.__exit__, None, None, None)
        return checkpointer

    from langgraph.checkpoint.memory import MemorySaver

    print(
        "[DEV] Using MemorySaver - sessions won't persist across restarts. "
        "Set SUPABASE_DB_URI or LANGGRAPH_DB_URI for durable checkpoints."
    )
    return MemorySaver()


# -----------------------------------------------------------------------------
# SkillGraph singleton
# -----------------------------------------------------------------------------

SKILL_GRAPH_TTL = int(os.environ.get("SKILL_GRAPH_TTL_SECONDS", "3600"))
_skill_graph: Optional[SkillGraph] = None
_skill_graph_ts: float = 0.0
_skill_graph_lock = asyncio.Lock()


async def get_skill_graph() -> SkillGraph:
    global _skill_graph, _skill_graph_ts
    now = time.time()
    if _skill_graph is not None and (now - _skill_graph_ts) <= SKILL_GRAPH_TTL:
        return _skill_graph

    async with _skill_graph_lock:
        now = time.time()
        if _skill_graph is None or (now - _skill_graph_ts) > SKILL_GRAPH_TTL:
            _skill_graph = await SkillGraph.build_from_db()
            _skill_graph_ts = now
        return _skill_graph


def invalidate_skill_graph() -> None:
    global _skill_graph, _skill_graph_ts
    _skill_graph = None
    _skill_graph_ts = 0.0


# -----------------------------------------------------------------------------
# Shared graph infrastructure
# -----------------------------------------------------------------------------

checkpointer = get_checkpointer()
backend_factory = lambda rt: StateBackend(runtime=rt)

assessment_team = build_assessment_team(checkpointer=checkpointer)
coaching_team = build_coaching_team(checkpointer=checkpointer)
session_manager = SessionManager()
gamification_engine = GamificationEngine()

web_search_tool = TavilySearch(max_results=3) if TavilySearch is not None else None


# -----------------------------------------------------------------------------
# Supervisor state
# -----------------------------------------------------------------------------

class SupervisorState(CopilotKitState):
    # Career UI state
    resume_markdown: NotRequired[Optional[str]]
    cover_letter_markdown: NotRequired[Optional[str]]
    job_listings: NotRequired[Optional[List[Dict[str, Any]]]]
    career_view: NotRequired[Optional[str]]

    # Fyndr UI state
    found_agencies: NotRequired[Optional[List[Dict[str, Any]]]]
    saved_agencies: NotRequired[Optional[List[Dict[str, Any]]]]
    selected_agency_id: NotRequired[Optional[str]]

    # Learning UI hints. Durable learning state remains in DB/session manager.
    current_phase: NotRequired[Optional[str]]
    lesson_progress: NotRequired[Optional[Dict[str, Any]]]

    # Generic UI navigation, if navigate_to_page writes it.
    current_page: NotRequired[Optional[str]]


# -----------------------------------------------------------------------------
# Learning tools
# -----------------------------------------------------------------------------

MISSING_LEARNER_CONTEXT_MESSAGE = (
    "I need a learner session before I can personalize lessons or save progress. "
    "Please log in or complete onboarding, then try again."
)

InjectedLearnerRuntime = Annotated[ToolRuntime[LearnerContext], InjectedToolArg]


def _item_type_from_state(value: Any) -> ItemType:
    try:
        return ItemType(str(value or "target"))
    except ValueError:
        return ItemType.TARGET


def _get_runtime_context(runtime: ToolRuntime[LearnerContext] | None) -> LearnerContext | None:
    context = getattr(runtime, "context", None)
    learner_id = getattr(context, "learner_id", None)
    if isinstance(learner_id, str) and learner_id.strip():
        return cast(LearnerContext, context)
    return None


@tool("start_learning_session")
async def start_learning_session(runtime: InjectedLearnerRuntime) -> str:
    """Initialize a learning session for the current learner."""
    context = _get_runtime_context(runtime)
    if context is None:
        return MISSING_LEARNER_CONTEXT_MESSAGE

    learner_id = context.learner_id
    session_id = context.session_id

    session = await session_manager.start_session(
        learner_id=learner_id,
        session_id=session_id,
    )

    if session.phase == SessionPhase.ONBOARDING:
        return (
            "NEW LEARNER detected. Start onboarding:\n"
            "1. Welcome them warmly. This is not school; it is their personal path.\n"
            "2. Ask what they are interested in for theming.\n"
            "3. Ask how they like to learn: visual, reading, doing, audio, mixed.\n"
            "4. Ask what brought them here: GED, job skills, both, or another goal.\n"
            "5. Keep it under 5 minutes, then hand off to placement.\n"
            "Use assessment_session with current_step='interest_harvest'."
        )

    if session.phase == SessionPhase.PLACEMENT:
        return (
            "Learner needs PLACEMENT assessment.\n"
            "Use adaptive questions to estimate their skill level per subject.\n"
            "Start with medium difficulty and adjust based on responses.\n"
            "15 items max. Use assessment_session with current_step='placement'."
        )

    if session.phase == SessionPhase.LEARNING and session.lesson_plan:
        plan = session.lesson_plan
        next_item = session_manager.get_next_item_spec(session)
        targets = [
            f"  - {t['skill_id']} step {t['chain_step']} (level {t['prompt_level']})"
            for t in plan.target_skills
        ]
        next_item_text = ""
        if next_item:
            next_item_text = (
                "\nNext item spec: "
                f"{next_item['skill_id']} step {next_item['chain_step']} "
                f"({next_item['item_type']}, prompt level {next_item['prompt_level']})\n"
            )
        return (
            "RETURNING LEARNER — session planned.\n"
            "Phase: LEARNING\n"
            f"Ratio: {plan.initial_ratio:.0%} mastered / {1 - plan.initial_ratio:.0%} target\n"
            "Target skills:\n"
            + "\n".join(targets)
            + "\n"
            f"Mastered pool: {len(plan.mastered_pool)} items\n"
            f"Reviews due: {len(plan.review_items)} items\n"
            f"Competency focus: {', '.join(plan.competency_focus)}\n"
            f"Estimated items: {plan.estimated_items}\n"
            f"Session length: {plan.estimated_duration_minutes} minutes\n\n"
            f"{next_item_text}"
            "Use coaching_session to begin teaching."
        )

    return "Session initialized. Ready to begin."


@tool("coaching_session")
async def run_coaching_session(
    message: str,
    current_step: str = "teaching",
    *,
    runtime: InjectedLearnerRuntime,
) -> str:
    """Run an interactive coaching interaction through the coaching team."""
    context = _get_runtime_context(runtime)
    if context is None:
        return MISSING_LEARNER_CONTEXT_MESSAGE

    learner_id = context.learner_id
    session_id = context.session_id

    result = await asyncio.to_thread(
        lambda: cast(Any, coaching_team).invoke(
            {
                "messages": [{"role": "user", "content": message}],
                "current_step": current_step,
            },
            config={"configurable": {"thread_id": f"coaching_{session_id}"}},
            context=LearnerContext(learner_id=learner_id, session_id=session_id),
        )
    )

    session = session_manager.get_active_session(
        learner_id=learner_id,
        session_id=session_id,
    )
    correct = result.get("last_response_correct")
    if session is not None and isinstance(correct, bool):
        await session_manager.advance(
            session=session,
            item_type=_item_type_from_state(result.get("last_item_type")),
            correct=correct,
        )

    events = result.get("gamification_events", [])
    if session is not None and isinstance(events, list):
        new_events = events[session.gamification_events_processed :]
        if new_events:
            await gamification_engine.process_events(learner_id, new_events)
            session.gamification_events_processed = len(events)

    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        return last.content if hasattr(last, "content") else str(last)
    return "Coaching session active."


@tool("assessment_session")
async def run_assessment_session(
    message: str,
    current_step: str = "interest_harvest",
    *,
    runtime: InjectedLearnerRuntime,
) -> str:
    """Run onboarding and placement interactions through the assessment team."""
    context = _get_runtime_context(runtime)
    if context is None:
        return MISSING_LEARNER_CONTEXT_MESSAGE

    learner_id = context.learner_id
    session_id = context.session_id

    result = await asyncio.to_thread(
        lambda: cast(Any, assessment_team).invoke(
            input={
                "messages": [{"role": "user", "content": message}],
                "current_step": current_step,
            },
            config={"configurable": {"thread_id": f"assessment_{session_id}"}},
            context=LearnerContext(learner_id=learner_id, session_id=session_id),
        )
    )

    session = session_manager.get_active_session(
        learner_id=learner_id,
        session_id=session_id,
    )
    current_step_result = result.get("current_step")
    if session is not None:
        if session.phase == SessionPhase.ONBOARDING and current_step_result == "placement":
            await session_manager.post_onboarding(session)
        elif current_step_result == "complete":
            placement_results = result.get("placement_results", {})
            if isinstance(placement_results, dict) and placement_results:
                await session_manager.post_placement(session, placement_results)

    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        return last.content if hasattr(last, "content") else str(last)
    return "Assessment session active."


@tool("wrap_up_session")
async def wrap_up_session(runtime: InjectedLearnerRuntime) -> str:
    """End the current learning session and save progress."""
    context = _get_runtime_context(runtime)
    if context is None:
        return MISSING_LEARNER_CONTEXT_MESSAGE

    learner_id = context.learner_id
    session_id = context.session_id

    session = session_manager.get_active_session(
        learner_id=learner_id,
        session_id=session_id,
    )
    if session is None:
        return "No active session found to wrap up."

    summary = await session_manager.wrap_up(session)
    next_up = summary.get("next_up", [])
    next_preview = ""
    if next_up:
        next_preview = "\n\nComing up next:\n" + "\n".join(
            f"  → {n['skill_id']} step {n['step']}: {n.get('description', '')}"
            for n in next_up
        )

    return (
        "Session complete!\n"
        f"Duration: {summary.get('duration_minutes', 0)} minutes\n"
        f"Items completed: {summary.get('items_completed', 0)}\n"
        f"Skills mastered (total): {summary.get('skills_mastered_total', 0)}\n"
        f"Competencies practiced: {', '.join(summary.get('competency_focus', []))}"
        f"{next_preview}"
    )


# -----------------------------------------------------------------------------
# Subagents
# -----------------------------------------------------------------------------

LEARNING_SYSTEM_PROMPT = """You are the Praxis Learning Subagent.

You handle only learning-session work: onboarding, placement, coaching, practice,
scaffolding, progress checks, and session wrap-up.

PRINCIPLES:
1. Personalize every interaction to the learner's interests, level, and goals.
2. Assessment is stealth: the learner should not feel tested.
3. Employment readiness is structural and woven into learning, not a separate module.
4. Scaffolding follows ABA principles with systematic prompt fading.
5. Never serve unvalidated curriculum content.
6. Keep the tone adult-appropriate, warm, direct, and practical.

FLOW:
- Use start_learning_session for explicit learning, onboarding, placement, practice,
  lesson, or progress-tracked requests.
- For onboarding, collect interests, learning preferences, and goals conversationally.
- Use assessment_session for onboarding and placement.
- For placement, run adaptive assessment lightly and keep it short.
- For learning, use coaching_session to deliver the lesson.
- At session end, use wrap_up_session.

BOUNDARIES:
- Do not handle resumes, job searches, cover letters, public resource searches,
  food, shelter, housing, legal aid, clinics, or general site navigation.
- If the user asks for those, return a concise handoff note so the supervisor can
  route to the correct subagent.
"""

learning_subagent: SubAgent = {
    "name": LEARNING_AGENT_NAME,
    "description": (
        "Handles learner onboarding, placement assessment, adaptive lessons, "
        "coaching, scaffolded practice, progress tracking, and session wrap-up."
    ),
    "system_prompt": LEARNING_SYSTEM_PROMPT,
    "tools": [
        start_learning_session,
        run_assessment_session,
        run_coaching_session,
        wrap_up_session,
    ],
    "model": init_praxis_chat_model(ORCHESTRATOR_MODEL),
    "middleware": cast(
        Any,
        [
            SafeCopilotKitMiddleware(),
            EmploymentStructuralMiddleware(),
            MicroThemingMiddleware(),
            ZPDMiddleware(),
            StealthAssessmentMiddleware(),
        ],
    ),
}

fyndr_tools: list[Any] = [
    recommend_assistance,
    find_agencies,
    filter_agencies,
    save_agencies,
]
if web_search_tool is not None:
    fyndr_tools.append(web_search_tool)

fyndr_agent: SubAgent = {
    "name": "access_fyndr",
    "description": (
        "Specialist for finding housing, food, legal aid, SNAP, utilities, "
        "medical, DV, and other local/community resources."
    ),
    "system_prompt": (
        "You are Fyndr, a practical case-work resource specialist.\n\n"
        "DECISION TREE:\n"
        "1. If the user describes a stressful life situation such as lost job, "
        "can't afford food, eviction, no power, DV, or medical need, first call "
        "recommend_assistance with the matching key: food_insecurity, lost_job, "
        "eviction_risk, domestic_violence, utilities, or medical.\n"
        "2. Then call find_agencies with the suggested search_query plus the "
        "user's location when available.\n"
        "3. If the user is simply filtering, such as 'food pantries near me' or "
        "'legal aid in 97401', call filter_agencies directly.\n"
        "4. If the location is outside Lane County, Oregon, use web search if "
        "available and then save_agencies to populate the map.\n\n"
        "Always summarize results with name, distance when known, fees, language "
        "support when known, and what the agency offers."
    ),
    "tools": fyndr_tools,
    "model": ROUTING_MODEL,
    "middleware": cast(Any, [SafeCopilotKitMiddleware()]),
}

career_tools: list[Any] = [update_career_state, switch_career_view]
if web_search_tool is not None:
    career_tools.append(web_search_tool)

career_agent: SubAgent = {
    "name": "access_career",
    "description": "Specialist for jobs, resumes, cover letters, and interview preparation.",
    "system_prompt": """
You are AccessCareer.

1. JOB SEARCH:
   - Use web search when available to find jobs.
   - Parse results into objects: {title, company, location, description, url, salary}.
   - Call update_career_state to set job_listings and career_view='jobs'.

2. RESUME:
   - Write or edit ATS-friendly resume markdown using only user-provided facts.
   - Call update_career_state to set resume_markdown and career_view='resume'.

3. COVER LETTER:
   - Write cover letter markdown using only user-provided facts plus the target job.
   - Call update_career_state to set cover_letter_markdown and career_view='cover_letter'.

4. INTERVIEW PREP:
   - Give direct practice, strong examples, and concise coaching.

Never invent employers, dates, certifications, salaries, degrees, or equipment experience.
Always update the relevant state keys when producing career artifacts.
""",
    "tools": career_tools,
    "model": REPLY_MODEL,
    "middleware": cast(Any, [SafeCopilotKitMiddleware()]),
}


SUPERVISOR_SYSTEM_PROMPT = """You are the Praxis Supervisor.

You are a fast router and light responder. The frontend sees only you, but you
should delegate real work to the correct subagent.

ROUTING:
- Learning, GED, lesson, assessment, placement, onboarding, practice, quiz,
  progress, coaching, skill mastery -> delegate to learning.
- Jobs, resume, cover letter, interview, applications, career planning ->
  delegate to access_career and navigate to the career page when useful.
- Food, shelter, housing, eviction, legal aid, SNAP, utilities, medical, DV,
  clinics, local resources -> delegate to access_fyndr and navigate to AccessFyndr
  or the map/resources page when useful.
- show map, donate, about, home, dashboard, career, learning -> use navigate_to_page.
- General questions -> answer briefly yourself.

Keep routing invisible. Do not explain the internal agent architecture to users.
Do not run learning middleware logic at the supervisor level.
"""


def build_supervisor_graph():
    supervisor_tools: list[Any] = [navigate_to_page]
    if web_search_tool is not None:
        supervisor_tools.append(web_search_tool)

    return create_deep_agent(
        name=ORCHESTRATOR_AGENT_NAME,
        model=ROUTING_MODEL,
        tools=supervisor_tools,
        subagents=[learning_subagent, career_agent, fyndr_agent],
        middleware=cast(Any, [SafeCopilotKitMiddleware()]),
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        backend=backend_factory,
    )


supervisor_graph = build_supervisor_graph()


# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------

app = FastAPI(
    title="Praxis",
    description="Unified adaptive learning, career, and resource-navigation platform",
    version="0.2.0",
)


def _parse_cors_origins(value: str | None) -> list[str]:
    if not value:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    return [origin.strip() for origin in value.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(
        os.environ.get("PRAXIS_CORS_ORIGINS")
        or os.environ.get("ACCESSFYNDR_CORS_ORIGINS")
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["authorization", "content-type"],
)


@app.on_event("startup")
async def validate_runtime_configuration() -> None:
    _validate_required_env()


add_langgraph_fastapi_endpoint(
    app=app,
    agent=SafeLangGraphAGUIAgent(
        name=PUBLIC_AGENT_NAME,
        description="Praxis unified supervisor for learning, career, and resources.",
        graph=supervisor_graph,
    ),
    path="/api",
)


# -----------------------------------------------------------------------------
# Health checks
# -----------------------------------------------------------------------------

@app.get("/health")
async def health():
    health_payload: dict[str, Any] = {
        "status": "ok",
        "service": SERVICE_NAME,
        "copilotkit_path": "/api",
        "skill_graph_size": 0,
        "supervisor": ORCHESTRATOR_AGENT_NAME,
        "subagents": [LEARNING_AGENT_NAME, "access_career", "access_fyndr"],
        "checkpointer": "postgres" if _get_checkpointer_db_uri() else "memory",
        "middleware": {
            "supervisor": ["SafeCopilotKit"],
            "learning": [
                "SafeCopilotKit",
                "EmploymentStructural",
                "MicroTheming",
                "ZPD",
                "StealthAssessment",
            ],
            "career": ["SafeCopilotKit"],
            "fyndr": ["SafeCopilotKit"],
        },
    }
    try:
        sg = await get_skill_graph()
        health_payload["skill_graph_size"] = len(sg.nodes) if hasattr(sg, "nodes") else 0
    except Exception as exc:
        health_payload["status"] = "degraded"
        health_payload["dependency_error"] = str(exc)
    return health_payload


@app.head("/health")
async def health_head():
    return Response(status_code=200)


# -----------------------------------------------------------------------------
# Ikigai API
# -----------------------------------------------------------------------------

ikigai_router = APIRouter(prefix="/api/ikigai", tags=["ikigai"])
_engine = IkigaiEngine()


@ikigai_router.get("/{learner_id}")
async def get_ikigai_state(learner_id: str):
    state = await _engine.compute(learner_id)
    return state.to_dict()


app.include_router(ikigai_router)


# -----------------------------------------------------------------------------
# Curriculum webhook
# -----------------------------------------------------------------------------

@app.post("/webhooks/curriculum-updated")
async def curriculum_webhook(_: None = Depends(require_curriculum_webhook_auth)):
    invalidate_skill_graph()
    asyncio.create_task(_pregenerate_seed_narrations())
    return {"status": "ok", "message": "Skill graph invalidated, narration pre-gen queued"}


async def _pregenerate_seed_narrations():
    from services.narration import NarrationService

    svc = NarrationService()
    client = await get_async_client()

    result = await (
        client.table("seed_items")
        .select("seed_id, skill_id, chain_step, scaffold_level, question_text, passage_text")
        .execute()
    )

    seeds = result.data or []
    total_queued = 0
    for raw_seed in seeds:
        seed = _as_dict(raw_seed)
        texts = []
        passage_text = seed.get("passage_text")
        if isinstance(passage_text, str) and passage_text:
            texts.extend(NarrationService.chunk_text(passage_text, role="setup"))
        question_text = seed.get("question_text")
        if isinstance(question_text, str) and question_text:
            texts.extend(NarrationService.chunk_text(question_text, role="question"))

        if texts:
            skill_id = seed.get("skill_id")
            chain_step = seed.get("chain_step")
            scaffold_level = seed.get("scaffold_level")
            total_queued += await svc.queue_batch(
                chunks=texts,
                skill_id=skill_id if isinstance(skill_id, str) else "",
                chain_step=chain_step if isinstance(chain_step, int) else 0,
                scaffold_level=scaffold_level if isinstance(scaffold_level, int) else 3,
                tier=1,
                priority=3,
            )

    print(f"[narration] pre-gen queued {total_queued} chunks for {len(seeds)} seeds")


# -----------------------------------------------------------------------------
# Narration API
# -----------------------------------------------------------------------------

class NarrationRequest(BaseModel):
    text: str = Field(..., max_length=500)
    voice: str = Field(default="female_teaching")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    scaffold_level: int = Field(default=3, ge=1, le=10)
    skill_id: str = Field(default="")
    chain_step: int = Field(default=0)
    theme: str | None = Field(default=None)


class NarrationPlanRequest(BaseModel):
    chunks: list[NarrationRequest]
    skill_id: str = Field(default="")
    chain_step: int = Field(default=0)
    scaffold_level: int = Field(default=3, ge=1, le=10)
    theme: str | None = Field(default=None)


@app.post("/api/narration/generate")
async def generate_narration(
    req: NarrationRequest,
    _: None = Depends(require_narration_auth),
):
    import logging
    from services.narration import NarrationService

    svc = NarrationService()
    try:
        result = await svc.get_or_generate(
            text=req.text,
            voice=req.voice,
            speed=req.speed,
            scaffold_level=req.scaffold_level,
            skill_id=req.skill_id,
            chain_step=req.chain_step,
            theme=req.theme,
        )
        return {
            "content_hash": result.content_hash,
            "audio_url": result.audio_url,
            "duration_ms": result.duration_ms,
            "word_timings": result.word_timings,
            "cached": result.cached,
        }
    except Exception as exc:
        logging.error("TTS generation failed: %s", exc)
        return {
            "content_hash": "error_fallback",
            "audio_url": "",
            "duration_ms": 0,
            "word_timings": [],
            "cached": False,
        }


@app.post("/api/narration/plan")
async def generate_narration_plan(
    req: NarrationPlanRequest,
    _: None = Depends(require_narration_auth),
):
    from services.narration import NarrationChunk, NarrationPlan, NarrationService

    svc = NarrationService()
    plan = NarrationPlan(
        chunks=[NarrationChunk(text=c.text, voice=c.voice, speed=c.speed) for c in req.chunks],
        skill_id=req.skill_id,
        chain_step=req.chain_step,
        scaffold_level=req.scaffold_level,
        theme=req.theme,
    )
    results = await svc.narrate_plan(plan)
    return {
        "chunks": [
            {
                "content_hash": r.content_hash,
                "audio_url": r.audio_url,
                "text": r.text,
                "duration_ms": r.duration_ms,
                "word_timings": r.word_timings,
                "cached": r.cached,
            }
            for r in results
        ],
        "total_duration_ms": sum(r.duration_ms for r in results),
    }


@app.post("/api/narration/chunk")
async def chunk_text_endpoint(
    text: str,
    max_chars: int = 300,
    voice: str = "female_teaching",
    _: None = Depends(require_narration_auth),
):
    from services.narration import NarrationService

    chunks = NarrationService.chunk_text(text, max_chars=max_chars, voice=voice)
    return {
        "chunks": [{"text": c.text, "role": c.role, "char_count": len(c.text)} for c in chunks],
        "count": len(chunks),
    }


# -----------------------------------------------------------------------------
# Research API
# -----------------------------------------------------------------------------

class ResearchSkillRequest(BaseModel):
    skill: str = Field(..., description="Human-readable skill name to research")
    subject: str = Field(default="general", description="Subject slug")
    curriculum_id: str = Field(default="ged", description="Curriculum scope")


@app.post("/api/research/skill")
async def research_skill(
    req: ResearchSkillRequest,
    _: None = Depends(require_research_skill_auth),
):
    import uuid

    thread_id = f"research_{uuid.uuid4().hex}"
    prompt = (
        "Research and create a skill chain for:\n"
        f"  Skill: {req.skill}\n"
        f"  Subject: {req.subject}\n"
        f"  Curriculum ID: {req.curriculum_id}\n\n"
        "Follow the full workflow: check for duplicates, research, validate, and write to the database."
    )

    try:
        result = await _research_agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"configurable": {"thread_id": thread_id}},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Research agent failed: {exc}") from exc

    messages = result.get("messages", [])
    final = messages[-1] if messages else None
    summary = final.content if final is not None and hasattr(final, "content") else str(final)
    wrote_ok = "chain_id" in summary.lower() or "chain_" in summary
    return {"ok": wrote_ok, "summary": summary, "thread_id": thread_id}


# -----------------------------------------------------------------------------
# Learner profile / bootstrap / resume save
# -----------------------------------------------------------------------------

@app.get("/api/learner/me")
async def get_learner_profile_summary(learner_id: str):
    client = await get_async_client()
    profile_res, gamification_res, competency_res = await asyncio.gather(
        client.table("learner_profiles")
        .select("learner_id, name, email, interests, learning_style, career_goal, created_at")
        .eq("learner_id", learner_id)
        .maybe_single()
        .execute(),
        client.table("gamification_state")
        .select("xp, level, streak_days, shields_available, badges_earned")
        .eq("learner_id", learner_id)
        .maybe_single()
        .execute(),
        client.table("learner_competencies")
        .select("competency, score, demonstrated_count")
        .eq("learner_id", learner_id)
        .execute(),
    )

    profile = _as_dict(getattr(profile_res, "data", None))
    gamification = _as_dict(getattr(gamification_res, "data", None))
    competency_rows = _as_dict_list(getattr(competency_res, "data", None))
    competencies = [
        {
            "competency": row.get("competency", ""),
            "score": row.get("score", row.get("strength", 0.0)),
            "demonstrated_count": row.get("demonstrated_count", row.get("count", 0)),
        }
        for row in competency_rows
        if row.get("competency")
    ]

    return {
        "learner_id": learner_id,
        "name": profile.get("name", ""),
        "email": profile.get("email", ""),
        "interests": profile.get("interests", []),
        "learning_style": profile.get("learning_style", "balanced"),
        "career_goal": profile.get("career_goal", ""),
        "xp": gamification.get("xp", 0),
        "level": gamification.get("level", 1),
        "streak_days": gamification.get("streak_days", 0),
        "shields_available": gamification.get("shields_available", 0),
        "badges_earned": gamification.get("badges_earned", []),
        "competencies": competencies,
    }


class LearnerBootstrapRequest(BaseModel):
    learner_id: str = Field(..., description="Supabase auth user UUID")
    email: str | None = Field(default=None)
    name: str | None = Field(default=None)
    career_goal: str | None = Field(default=None)
    interests: list[str] = Field(default_factory=list)
    extracted_skills: list[str] = Field(default_factory=list)


@app.post("/api/learner/bootstrap")
async def bootstrap_learner(req: LearnerBootstrapRequest):
    from datetime import datetime, timezone as tz

    client = await get_async_client()
    now = datetime.now(tz.utc).isoformat()

    existing_res = await (
        client.table("learner_profiles")
        .select("learner_id, name, email, interests, learning_style, career_goal")
        .eq("learner_id", req.learner_id)
        .maybe_single()
        .execute()
    )
    existing = _as_dict(getattr(existing_res, "data", None))

    merged_interests = list({*(existing.get("interests") or []), *req.interests, *req.extracted_skills})
    profile = {
        "learner_id": req.learner_id,
        "name": req.name or existing.get("name") or (req.email.split("@")[0] if req.email else "Learner"),
        "email": req.email or existing.get("email"),
        "interests": merged_interests,
        "learning_style": existing.get("learning_style", "balanced"),
        "career_goal": req.career_goal or existing.get("career_goal"),
        "updated_at": now,
    }
    if not existing:
        profile["created_at"] = now
        profile["sessions_completed"] = 0

    try:
        await asyncio.to_thread(lambda: db.client.table("learner_profiles").upsert(profile).execute())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to bootstrap learner: {exc}") from exc

    return {"ok": True, "learner_id": req.learner_id, "created": not existing}


class SessionStartRequest(BaseModel):
    learner_id: str = Field(..., description="Learner UUID")
    session_id: str | None = Field(default=None, description="Optional client session ID")


class SessionWrapUpRequest(BaseModel):
    learner_id: str = Field(..., description="Learner UUID")
    session_id: str | None = Field(default=None, description="Optional active session ID")


def _session_start_payload(session: Session) -> dict[str, Any]:
    next_item = session_manager.get_next_item_spec(session)
    return {
        "session_id": session.session_id,
        "learner_id": session.learner_id,
        "phase": session.phase.value,
        "is_new_learner": session.is_new_learner,
        "needs_placement": session.needs_placement,
        "items_completed": session.items_completed,
        "duration_minutes": round(session.elapsed_minutes, 1),
        "next_item": next_item,
    }


def _session_summary_payload(summary: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    momentum = _as_dict(summary.get("momentum"))
    items_completed = int(summary.get("items_completed") or 0)
    accuracy = float(momentum.get("recent_accuracy", 0.0)) if items_completed > 0 else 0.0
    next_up = _as_dict_list(summary.get("next_up"))
    next_recommendation = ""
    if next_up:
        first_next = next_up[0]
        next_recommendation = (
            f"Next up: {first_next.get('skill_id', 'your next skill')} "
            f"step {first_next.get('step', '')}".strip()
        )

    return {
        "session_id": summary.get("session_id", ""),
        "phase": SessionPhase.WRAP_UP.value,
        "items_completed": items_completed,
        "accuracy": accuracy,
        "xp_earned": 0,
        "xp_total": int(profile.get("xp") or 0),
        "streak": int(profile.get("streak_days") or 0),
        "skills_practiced": list(summary.get("competency_focus") or []) if items_completed > 0 else [],
        "ikigai_delta": 0.0,
        "duration_minutes": float(summary.get("duration_minutes") or 0.0),
        "next_recommendation": next_recommendation,
    }


@app.post("/api/session/start")
async def start_session_endpoint(req: SessionStartRequest):
    session = await session_manager.start_session(
        learner_id=req.learner_id,
        session_id=req.session_id,
    )
    return _session_start_payload(session)


@app.post("/api/session/wrap-up")
async def wrap_up_session_endpoint(req: SessionWrapUpRequest):
    session = session_manager.get_active_session(
        learner_id=req.learner_id,
        session_id=req.session_id,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="No active session found")

    summary = await session_manager.wrap_up(session)
    profile = await get_learner_profile_summary(req.learner_id)
    return _session_summary_payload(summary, profile)


class ResumeSaveRequest(BaseModel):
    learner_id: str = Field(..., description="Learner UUID")
    text: str = Field(..., description="Extracted plain-text resume content")
    filename: str = Field(default="resume", description="Original filename without extension")


@app.post("/api/resume/save")
async def save_resume(req: ResumeSaveRequest):
    from datetime import datetime, timezone as tz

    client = await get_async_client()
    now = datetime.now(tz.utc).isoformat()
    row = {
        "learner_id": req.learner_id,
        "filename": req.filename,
        "extracted_text": req.text,
        "created_at": now,
        "version": "latest",
    }
    try:
        await client.table("resume_versions").upsert(row, on_conflict="learner_id,version").execute()
        return {"ok": True, "learner_id": req.learner_id, "version": "latest"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save resume: {exc}") from exc


# -----------------------------------------------------------------------------
# Resource filter endpoint - keep Block 2 version, remove Praxis duplicate
# -----------------------------------------------------------------------------

class FilterRequest(BaseModel):
    service_type: Optional[str] = None
    agency_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    max_distance_miles: float = Field(default=15, ge=0, le=200)


@app.post("/filter")
async def http_filter(req: FilterRequest):
    results = await asyncio.to_thread(
        filter_resources,
        service_type=req.service_type,
        agency_name=req.agency_name,
        lat=req.latitude,
        lng=req.longitude,
        radius_miles=req.max_distance_miles,
    )
    return {"results": results, "count": len(results)}


# Optional compatibility endpoint if old clients called /api/filter.
@app.post("/api/filter")
async def http_filter_api(req: FilterRequest):
    return await http_filter(req)


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------

def main() -> None:
    port = int(os.environ.get("PORT", "8223"))
    reload_enabled = os.environ.get("PRAXIS_RELOAD", "0") == "1"

    def _is_port_available(candidate: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", candidate))
            except OSError:
                return False
            return True

    def _find_available_port(start_port: int, max_attempts: int = 20) -> int:
        for candidate in range(start_port, start_port + max_attempts):
            if _is_port_available(candidate):
                return candidate
        raise RuntimeError(
            f"No available port found in range {start_port}-{start_port + max_attempts - 1}"
        )

    selected_port = _find_available_port(port)
    if selected_port != port:
        print(f"[DEV] Port {port} is in use. Falling back to port {selected_port}.")

    uvicorn.run(app, host="0.0.0.0", port=selected_port, reload=reload_enabled)


if __name__ == "__main__":
    main()
