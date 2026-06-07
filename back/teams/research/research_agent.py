import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Literal, cast

from deepagents import create_deep_agent
from model_factory import DEFAULT_BASE_MODEL, init_praxis_chat_model

try:
    from tavily import TavilyClient
except Exception as exc:  # pragma: no cover - optional dependency
    TavilyClient = None  # type: ignore[assignment]
    _TAVILY_IMPORT_ERROR = str(exc)
else:
    _TAVILY_IMPORT_ERROR = ""

try:
    from duckduckgo_search import DDGS
except Exception as exc:  # pragma: no cover - optional dependency
    DDGS = None  # type: ignore[assignment]
    _DUCKDUCKGO_IMPORT_ERROR = str(exc)
else:
    _DUCKDUCKGO_IMPORT_ERROR = ""


ALLOWED_DEFAULT_METHODS = {"forward", "backward", "total_task"}
TOP_LEVEL_REQUIRED_KEYS = [
    "chain_id",
    "subject",
    "skill_id",
    "name",
    "description",
    "default_method",
    "standard_code",
    "steps",
    "total_minutes",
    "created_at",
]
STEP_REQUIRED_KEYS = [
    "name",
    "description",
    "step_number",
    "trials_required",
    "sessions_required",
    "accuracy_criterion",
    "observable_behavior",
    "initial_prompt_level",
    "employment_micro_context",
]

_SUBJECT_ALIASES = {
    # ── GED / academic core ───────────────────────────────────────
    "mathematics": "math",
    "maths": "math",
    "math": "math",
    "arithmetic": "math",
    "algebra": "math",
    "geometry": "math",
    "ela": "rla",
    "rla": "rla",
    "reading": "rla",
    "writing": "rla",
    "language_arts": "rla",
    "english_language_arts": "rla",
    "english": "rla",
    "literacy": "rla",
    "social_studies": "social_studies",
    "social_study": "social_studies",
    "history": "social_studies",
    "civics": "social_studies",
    "geography": "social_studies",
    "economics": "social_studies",
    "science": "science",
    "biology": "science",
    "chemistry": "science",
    "physics": "science",
    "earth_science": "science",
    # ── Information technology ────────────────────────────────────
    "it": "it_fundamentals",
    "it_fundamentals": "it_fundamentals",
    "information_technology": "it_fundamentals",
    "computer_hardware": "it_fundamentals",
    "comptia_a_plus": "it_fundamentals",
    "networking": "networking",
    "network_fundamentals": "networking",
    "comptia_network_plus": "networking",
    "cybersecurity": "cybersecurity",
    "security": "cybersecurity",
    "comptia_security_plus": "cybersecurity",
    "information_security": "cybersecurity",
    # ── Programming / software ────────────────────────────────────
    "programming": "programming",
    "coding": "programming",
    "software_development": "programming",
    "python": "programming",
    "javascript": "programming",
    "web_development": "programming",
    "databases": "programming",
    "sql": "programming",
    # ── Healthcare / medical ──────────────────────────────────────
    "healthcare": "healthcare",
    "medical": "healthcare",
    "nursing": "healthcare",
    "cna": "healthcare",
    "phlebotomy": "healthcare",
    "medical_assistant": "healthcare",
    "pharmacy_technician": "healthcare",
    # ── Business / finance ────────────────────────────────────────
    "business": "business",
    "accounting": "business",
    "bookkeeping": "business",
    "finance": "business",
    "marketing": "business",
    "customer_service": "business",
    "project_management": "business",
    # ── Trades / vocational ───────────────────────────────────────
    "trades": "trades",
    "electrical": "trades",
    "plumbing": "trades",
    "hvac": "trades",
    "carpentry": "trades",
    "welding": "trades",
    "automotive": "trades",
    "construction": "trades",
    # ── General / catch-all ───────────────────────────────────────
    "general": "general",
    "vocational": "general",
    "life_skills": "general",
    "workplace_readiness": "general",
}

_tavily_client: Any | None = None
_duckduckgo_client: Any | None = None


def _slugify(value: str, fallback: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
    return text or fallback


def slugify_skill_id(skill_id: str) -> str:
    return _slugify(skill_id, fallback="unknown_skill")


def normalize_subject(subject: str) -> str:
    normalized = _slugify(subject, fallback="general")
    return _SUBJECT_ALIASES.get(normalized, normalized)


_DEFAULT_CURRICULUM = "ged"


def derive_chain_id(subject: str, skill_id: str, curriculum_id: str | None = None) -> str:
    subject_slug = normalize_subject(subject)
    skill_slug = slugify_skill_id(skill_id)
    # Only prefix non-default curricula to preserve backward compat with existing GED chain_ids
    # (e.g. chain_math_basic_algebra, not chain_ged_math_basic_algebra).
    if curriculum_id and curriculum_id != _DEFAULT_CURRICULUM:
        curriculum_slug = _slugify(curriculum_id, fallback="general")
        return f"chain_{curriculum_slug}_{subject_slug}_{skill_slug}"
    return f"chain_{subject_slug}_{skill_slug}"


def _default_created_at() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00")


def _to_string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    result = str(value).strip()
    return result if result else default


def _to_int(value: Any, default: int, errors: list[str], field: str) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError("bool is not valid int")
        return int(value)
    except (TypeError, ValueError):
        errors.append(f"{field} must be an integer")
        return default


def _to_float(value: Any, default: float, errors: list[str], field: str) -> float:
    try:
        if isinstance(value, bool):
            raise ValueError("bool is not valid float")
        return float(value)
    except (TypeError, ValueError):
        errors.append(f"{field} must be numeric")
        return default


def _normalize_steps(steps: Any, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(steps, list):
        errors.append("steps must be a list")
        return []

    normalized_steps: list[dict[str, Any]] = []
    raw_numbers: list[int] = []

    for index, raw_step in enumerate(steps, start=1):
        if not isinstance(raw_step, dict):
            errors.append(f"steps[{index}] must be an object")
            continue

        for key in STEP_REQUIRED_KEYS:
            if key not in raw_step:
                errors.append(f"steps[{index}] missing required key '{key}'")

        raw_number = _to_int(raw_step.get("step_number", index), index, errors, f"steps[{index}].step_number")
        raw_numbers.append(raw_number)

        step = {
            "name": _to_string(raw_step.get("name"), f"Step {index}"),
            "description": _to_string(raw_step.get("description"), ""),
            "step_number": raw_number,
            "trials_required": max(1, _to_int(raw_step.get("trials_required", 5), 5, errors, f"steps[{index}].trials_required")),
            "sessions_required": max(1, _to_int(raw_step.get("sessions_required", 1), 1, errors, f"steps[{index}].sessions_required")),
            "accuracy_criterion": _to_float(raw_step.get("accuracy_criterion", 0.8), 0.8, errors, f"steps[{index}].accuracy_criterion"),
            "observable_behavior": _to_string(raw_step.get("observable_behavior"), ""),
            "initial_prompt_level": min(5, max(1, _to_int(raw_step.get("initial_prompt_level", 2), 2, errors, f"steps[{index}].initial_prompt_level"))),
            "employment_micro_context": _to_string(raw_step.get("employment_micro_context"), ""),
        }
        normalized_steps.append(step)

    normalized_steps.sort(key=lambda s: s["step_number"])

    expected = list(range(1, len(normalized_steps) + 1))
    if raw_numbers and sorted(raw_numbers) != expected:
        errors.append("step_number values must be contiguous starting at 1")

    for idx, step in enumerate(normalized_steps, start=1):
        step["step_number"] = idx

    return normalized_steps


def normalize_skill_chain_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Normalize payload into skill_chains row shape."""
    errors: list[str] = []

    subject = normalize_subject(_to_string(payload.get("subject"), "general"))
    skill_source = _to_string(payload.get("skill_id"), _to_string(payload.get("name"), "unknown_skill"))
    skill_id = slugify_skill_id(skill_source)
    steps = _normalize_steps(payload.get("steps", []), errors)

    default_method = _slugify(_to_string(payload.get("default_method"), "forward"), "forward")
    if default_method not in ALLOWED_DEFAULT_METHODS:
        errors.append("default_method must be one of: forward, backward, total_task")
        default_method = "forward"

    total_minutes = _to_int(payload.get("total_minutes", 0), 0, errors, "total_minutes")
    if total_minutes <= 0:
        total_minutes = sum(step["sessions_required"] * 3 for step in steps) if steps else 15

    created_at = _to_string(payload.get("created_at"), _default_created_at())

    # Accept either "standard_code" (new) or "ged_standard" (legacy CSV field name)
    standard_code = _to_string(
        payload.get("standard_code") or payload.get("ged_standard"),
        "UNSPECIFIED",
    )

    normalized = {
        "chain_id": derive_chain_id(subject, skill_id),
        "subject": subject,
        "skill_id": skill_id,
        "name": _to_string(payload.get("name"), "Untitled Skill"),
        "description": _to_string(payload.get("description"), ""),
        "default_method": default_method,
        "ged_standard": standard_code,  # DB column is named ged_standard
        "steps": steps,
        "total_minutes": int(total_minutes),
        "created_at": created_at,
    }

    return normalized, errors


def validate_skill_chain_payload(payload: dict[str, Any]) -> list[str]:
    """Validate normalized payload deterministically."""
    errors: list[str] = []

    db_required_keys = [k if k != "standard_code" else "ged_standard" for k in TOP_LEVEL_REQUIRED_KEYS]
    for key in db_required_keys:
        if key not in payload:
            errors.append(f"missing required key '{key}'")

    if not isinstance(payload.get("chain_id"), str):
        errors.append("chain_id must be a string")
    if not isinstance(payload.get("subject"), str):
        errors.append("subject must be a string")
    if not isinstance(payload.get("skill_id"), str):
        errors.append("skill_id must be a string")
    if not isinstance(payload.get("name"), str):
        errors.append("name must be a string")
    if not isinstance(payload.get("description"), str):
        errors.append("description must be a string")

    default_method = payload.get("default_method")
    if default_method not in ALLOWED_DEFAULT_METHODS:
        errors.append("default_method must be one of: forward, backward, total_task")

    if not isinstance(payload.get("ged_standard"), str):
        errors.append("ged_standard must be a string")
    if not isinstance(payload.get("total_minutes"), int):
        errors.append("total_minutes must be an integer")
    if not isinstance(payload.get("created_at"), str):
        errors.append("created_at must be a string")

    steps = payload.get("steps")
    if not isinstance(steps, list):
        errors.append("steps must be a list")
        return errors

    step_numbers: list[int] = []
    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            errors.append(f"steps[{idx}] must be an object")
            continue

        for key in STEP_REQUIRED_KEYS:
            if key not in step:
                errors.append(f"steps[{idx}] missing required key '{key}'")

        if not isinstance(step.get("name"), str):
            errors.append(f"steps[{idx}].name must be a string")
        if not isinstance(step.get("description"), str):
            errors.append(f"steps[{idx}].description must be a string")
        if not isinstance(step.get("step_number"), int):
            errors.append(f"steps[{idx}].step_number must be an integer")
        else:
            step_numbers.append(step["step_number"])
        if not isinstance(step.get("trials_required"), int):
            errors.append(f"steps[{idx}].trials_required must be an integer")
        if not isinstance(step.get("sessions_required"), int):
            errors.append(f"steps[{idx}].sessions_required must be an integer")
        if not isinstance(step.get("accuracy_criterion"), (int, float)):
            errors.append(f"steps[{idx}].accuracy_criterion must be numeric")
        if not isinstance(step.get("observable_behavior"), str):
            errors.append(f"steps[{idx}].observable_behavior must be a string")
        if not isinstance(step.get("initial_prompt_level"), int):
            errors.append(f"steps[{idx}].initial_prompt_level must be an integer")
        if not isinstance(step.get("employment_micro_context"), str):
            errors.append(f"steps[{idx}].employment_micro_context must be a string")

    expected = list(range(1, len(steps) + 1))
    if step_numbers != expected:
        errors.append("step_number must be contiguous from 1 in final order")

    return errors


def validate_skill_chain_json(payload_json: str) -> dict[str, Any]:
    """Validate and normalize JSON string into required skill chain shape.

    Returns:
        {
          "ok": bool,
          "errors": list[str],
          "normalized": dict
        }
    """
    try:
        parsed = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "errors": [f"invalid_json: {exc}"],
            "normalized": {},
        }

    if not isinstance(parsed, dict):
        return {
            "ok": False,
            "errors": ["payload must be a JSON object"],
            "normalized": {},
        }

    normalized, normalize_errors = normalize_skill_chain_payload(parsed)
    validation_errors = validate_skill_chain_payload(normalized)
    errors = normalize_errors + validation_errors

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "normalized": normalized,
    }


def list_existing_chains(
    subject: str | None = None,
    curriculum_id: str = "ged",
) -> dict[str, Any]:
    """List skill chains already in the database to avoid re-researching duplicates.

    Args:
        subject: Filter by subject slug (e.g. "math", "rla", "science"). Pass None for all.
        curriculum_id: Curriculum scope (e.g. "ged", "comptia_a_plus").

    Returns:
        {"ok": bool, "count": int, "skill_ids": list[str], "chain_ids": list[str]}
    """
    try:
        from db.client import db  # local import — avoids circular deps at module load

        chains = db.fetch_all_chains(subject=subject, curriculum_id=curriculum_id)
        return {
            "ok": True,
            "count": len(chains),
            "skill_ids": [c.get("skill_id", "") for c in chains],
            "chain_ids": [c.get("chain_id", "") for c in chains],
        }
    except Exception as exc:
        return {
            "ok": False,
            "count": 0,
            "skill_ids": [],
            "chain_ids": [],
            "error": str(exc),
        }


def write_skill_chain(
    payload_json: str,
    curriculum_id: str = "ged",
) -> dict[str, Any]:
    """Validate and write a skill chain to the database.

    Call this AFTER validate_skill_chain_json returns ok=True.
    Re-validates the payload as a safety net before writing.

    Args:
        payload_json: JSON string produced by the research workflow.
        curriculum_id: Curriculum scope for the chain (e.g. "ged", "comptia_a_plus").

    Returns:
        {"ok": bool, "chain_id": str, "skill_id": str, "error": str | None}
    """
    result = validate_skill_chain_json(payload_json)
    if not result["ok"]:
        return {
            "ok": False,
            "chain_id": "",
            "skill_id": "",
            "error": f"Validation failed: {result['errors']}",
        }

    normalized = result["normalized"]
    row = dict(normalized)
    row["curriculum_id"] = curriculum_id
    row["chain_id"] = derive_chain_id(
        subject=row.get("subject", "general"),
        skill_id=row.get("skill_id", "unknown_skill"),
        curriculum_id=curriculum_id,
    )

    try:
        from db.client import db

        db.table("skill_chains").upsert(row, on_conflict="chain_id").execute()
        return {
            "ok": True,
            "chain_id": row["chain_id"],
            "skill_id": row["skill_id"],
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "chain_id": row.get("chain_id", ""),
            "skill_id": row.get("skill_id", ""),
            "error": str(exc),
        }


def _get_tavily_client() -> tuple[Any | None, str | None]:
    global _tavily_client

    if _tavily_client is not None:
        return _tavily_client, None

    if TavilyClient is None:
        details = _TAVILY_IMPORT_ERROR or "tavily package is not installed"
        return None, f"Tavily unavailable: {details}"

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return None, "Tavily unavailable: TAVILY_API_KEY is not set"

    try:
        _tavily_client = TavilyClient(api_key=api_key)
        return _tavily_client, None
    except Exception as exc:  # pragma: no cover - runtime env specific
        return None, f"Tavily unavailable: failed to initialize client ({exc})"


def _get_duckduckgo_client() -> tuple[Any | None, str | None]:
    global _duckduckgo_client

    if _duckduckgo_client is not None:
        return _duckduckgo_client, None

    if DDGS is None:
        details = _DUCKDUCKGO_IMPORT_ERROR or "duckduckgo-search package is not installed"
        return None, f"DuckDuckGo unavailable: {details}"

    try:
        _duckduckgo_client = DDGS()
        return _duckduckgo_client, None
    except Exception as exc:  # pragma: no cover - runtime env specific
        return None, f"DuckDuckGo unavailable: failed to initialize client ({exc})"


def _normalize_duckduckgo_results(results: Any, include_raw_content: bool) -> list[dict[str, Any]]:
    if not isinstance(results, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue

        title = _to_string(item.get("title"), "")
        url = _to_string(item.get("href"), _to_string(item.get("url"), ""))
        content = _to_string(item.get("body"), _to_string(item.get("snippet"), ""))

        entry: dict[str, Any] = {
            "title": title,
            "url": url,
            "content": content,
        }
        if include_raw_content:
            entry["raw_content"] = content
        normalized.append(entry)
    return normalized


def _search_duckduckgo(
    query: str,
    max_results: int = 5,
    include_raw_content: bool = False,
) -> tuple[list[dict[str, Any]] | None, Any | None, str | None]:
    client, error = _get_duckduckgo_client()
    if error:
        return None, None, error
    if client is None:
        return None, None, "DuckDuckGo unavailable: failed to initialize client"

    try:
        raw_iterable = client.text(keywords=query, max_results=max_results)
        raw_results = list(raw_iterable) if raw_iterable is not None else []
        normalized_results = _normalize_duckduckgo_results(raw_results, include_raw_content)
        return normalized_results, raw_results, None
    except Exception as exc:  # pragma: no cover - network/runtime specific
        return None, None, f"DuckDuckGo search failed ({exc})"


def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search with Tavily first and DuckDuckGo fallback."""
    client, error = _get_tavily_client()
    tavily_error_details: str | None = error

    if client is not None and not error:
        try:
            search_docs = client.search(
                query,
                max_results=max_results,
                include_raw_content=include_raw_content,
                topic=topic,
            )
            return {
                "ok": True,
                "query": query,
                "results": search_docs.get("results", []) if isinstance(search_docs, dict) else search_docs,
                "raw": search_docs,
                "provider": "tavily",
                "fallback_used": False,
            }
        except Exception as exc:  # pragma: no cover - network/runtime specific
            tavily_error_details = f"Tavily search failed ({exc})"

    fallback_results, fallback_raw, fallback_error = _search_duckduckgo(
        query=query,
        max_results=max_results,
        include_raw_content=include_raw_content,
    )
    if fallback_error is None and fallback_results is not None:
        return {
            "ok": True,
            "query": query,
            "results": fallback_results,
            "raw": fallback_raw,
            "provider": "duckduckgo",
            "fallback_used": True,
        }

    detail_parts: list[str] = []
    if tavily_error_details:
        detail_parts.append(tavily_error_details)
    if fallback_error:
        detail_parts.append(fallback_error)

    return {
        "ok": False,
        "error": "internet_search_failed",
        "details": " | ".join(detail_parts) if detail_parts else "No search providers available",
        "query": query,
        "results": [],
        "provider": "none",
        "fallback_used": True,
    }


sub_research_prompt = """You are a dedicated topic researcher for academic and vocational skill design.
You receive one topic at a time and gather concise, factual material that can inform
curriculum step design.

Requirements:
- Focus on core concepts, common misconceptions, prerequisite knowledge, and practical contexts
- Include credible source links in plain text
- Return clear findings that can be transformed into a skill chain with 3-8 discrete learnable steps
- Note any official standards or certification codes relevant to the topic"""

research_sub_agent = {
    "name": "research-agent",
    "description": (
        "Researches one academic or vocational topic deeply and returns factual findings "
        "to support skill-chain authoring."
    ),
    "system_prompt": sub_research_prompt,
    "model": DEFAULT_BASE_MODEL,
    "tools": [internet_search],
}


research_instructions = """You are an academic and vocational curriculum chain generator.
Your task is to produce ONE complete skill-chain record and save it to the database.

## Workflow

1) **Check for duplicates** — call list_existing_chains with the relevant subject and
   curriculum_id. If the skill_id already exists, report it and stop.

2) **Research** — use internet_search and/or the research-agent subagent to gather:
   - Core concepts and prerequisite knowledge
   - Common learner misconceptions
   - Practical/employment contexts for each sub-skill
   - Any official standard or certification code (GED code, CompTIA objective, etc.)

3) **Draft** — produce a single JSON object matching the required shape below.

4) **Validate** — call validate_skill_chain_json on your draft. Repair and re-validate
   until it returns ok=true. Never skip this step.

5) **Write** — call write_skill_chain with the validated JSON and the correct curriculum_id.
   Report the returned chain_id and any error.

## Required JSON shape

Top-level keys:
- chain_id        (derived automatically from curriculum_id + subject + skill_id;
                   you may omit it; the tool fills it in)
- subject         (slug: "math", "rla", "science", "social_studies", or a custom slug)
- skill_id        (short slug, e.g. "basic_algebra", "network_fundamentals")
- name            (human-readable title, ≤ 60 chars)
- description     (one sentence describing learner mastery)
- default_method  (one of: forward, backward, total_task)
- standard_code   (relevant standard/objective code — GED code, CompTIA obj, CCSS, etc.;
                   use "GENERAL" if no official code applies)
- steps           (list of 3–8 step objects, see below)
- total_minutes   (estimated total instruction time as integer; omit to auto-calculate)
- created_at      (omit — filled automatically)

Each step object:
- name                    (brief step title)
- description             (what the learner does in this step)
- step_number             (1-based integer, contiguous)
- trials_required         (integer ≥ 1)
- sessions_required       (integer ≥ 1)
- accuracy_criterion      (float 0.0–1.0, typically 0.80)
- observable_behavior     (measurable, observable learner action)
- initial_prompt_level    (integer 1–5; 1 = independent, 5 = full guidance)
- employment_micro_context (one-sentence workplace/employment relevance)

## Constraints
- default_method must be: forward, backward, or total_task
- step_number must be contiguous starting at 1
- total_minutes must be a positive integer
- accuracy_criterion must be numeric

## Quality bar
- Steps must be discrete, teachable sub-skills (not vague phases)
- Each step must have a concrete observable_behavior
- employment_micro_context must connect to a realistic adult work scenario
- Aim for 4–6 steps for most skills

## Output policy
After write_skill_chain succeeds, respond with a brief plain-text summary:
  chain_id, skill_id, subject, step count, curriculum_id written.
Do NOT output the raw JSON to the user.
"""


agent = create_deep_agent(
    model=init_praxis_chat_model(
        os.environ.get("PRAXIS_RESEARCH_MODEL", DEFAULT_BASE_MODEL)
    ),
    tools=[
        internet_search,
        validate_skill_chain_json,
        list_existing_chains,
        write_skill_chain,
    ],
    system_prompt=research_instructions,
    subagents=cast(Any, [
        {
            **research_sub_agent,
            "model": init_praxis_chat_model(
                os.environ.get("PRAXIS_RESEARCH_SUBAGENT_MODEL", DEFAULT_BASE_MODEL)
            ),
        }
    ]),
)
