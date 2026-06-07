"""
praxis/middleware/core.py

Core middleware — v2. Uses system_context state key instead of
appending SystemMessages. Includes Bayesian decay for competency signals.

State contract — CoachingState must include:
    system_context: NotRequired[dict]  # keyed sections, overwritten each turn

The apply_coaching_config middleware reads system_context and merges
all sections into the system prompt as a suffix.

Performance: Profile and competency data is cached with a 5-minute TTL
and a max cache size to prevent unbounded memory growth.
"""

from __future__ import annotations

import json
import logging
import math
import time
import random
from time import time as _time
from typing import Any, Optional

from langchain.agents.middleware import AgentMiddleware, AgentState
from langgraph.runtime import Runtime

from db.client import db
from db.tools_bridge import LearnerContext


logger = logging.getLogger(__name__)


# ── Profile cache with TTL ────────────────────────────────────

_CACHE_TTL = 300       # 5 minutes
_MAX_CACHE_SIZE = 500  # max learners in cache before eviction

# Stored as {learner_id: (timestamp, data)}
_profile_cache: dict[str, tuple[float, Optional[dict]]] = {}
_competency_cache: dict[str, tuple[float, list[dict]]] = {}


def _evict_oldest(cache: dict[str, tuple[float, Any]]) -> None:
    """Evict the oldest cache entry to avoid full-cache flushes."""
    if not cache:
        return
    oldest_key = min(cache, key=lambda key: cache[key][0])
    cache.pop(oldest_key, None)


def _get_learner_id(runtime: Runtime[LearnerContext] | None) -> str | None:
    context = getattr(runtime, "context", None)
    learner_id = getattr(context, "learner_id", None)
    if isinstance(learner_id, str) and learner_id.strip():
        return learner_id
    return None


def _load_profile(runtime: Runtime[LearnerContext] | None) -> Optional[dict]:
    lid = _get_learner_id(runtime)
    if not lid:
        return None
    now = _time()
    if lid in _profile_cache:
        ts, data = _profile_cache[lid]
        if now - ts < _CACHE_TTL:
            return data
    # Evict one oldest entry when max size is reached.
    if len(_profile_cache) >= _MAX_CACHE_SIZE:
        _evict_oldest(_profile_cache)
    result = db.table("learner_profiles").select("*").eq("learner_id", lid).maybe_single().execute()
    _profile_cache[lid] = (now, result.data)
    return result.data


def _load_competencies(runtime: Runtime[LearnerContext] | None) -> list[dict]:
    lid = _get_learner_id(runtime)
    if not lid:
        return []
    now = _time()
    if lid in _competency_cache:
        ts, data = _competency_cache[lid]
        if now - ts < _CACHE_TTL:
            return data
    if len(_competency_cache) >= _MAX_CACHE_SIZE:
        _evict_oldest(_competency_cache)
    result = db.table("learner_competencies").select("*").eq("learner_id", lid).execute()
    comps = result.data or []
    _competency_cache[lid] = (now, comps)
    return comps


def clear_middleware_cache():
    """Clear all cached data. Call when a learner's profile is updated."""
    _profile_cache.clear()
    _competency_cache.clear()


def invalidate_learner_cache(learner_id: str):
    """Invalidate cache for a specific learner (e.g., after profile update)."""
    _profile_cache.pop(learner_id, None)
    _competency_cache.pop(learner_id, None)


# ── Helper: write to system_context ───────────────────────────

def _set_context(state: dict, key: str, text: str) -> dict:
    """Overwrite a keyed section in system_context (no accumulation)."""
    ctx = dict(state.get("system_context", {}))
    ctx[key] = text
    return {"system_context": ctx}


def render_system_context(state: dict[str, Any]) -> str:
    """Render middleware-produced context as a compact system prompt suffix."""
    ctx = state.get("system_context", {})
    if not isinstance(ctx, dict) or not ctx:
        return ""

    sections = [
        f"- {key}: {value}"
        for key, value in ctx.items()
        if isinstance(key, str) and isinstance(value, str) and value.strip()
    ]
    if not sections:
        return ""
    return "\n\nRuntime learner context:\n" + "\n".join(sections)


# ══════════════════════════════════════════════════════════════
# ZPD
# ══════════════════════════════════════════════════════════════

class ZPDMiddleware(AgentMiddleware):
    def before_model(self, state: AgentState, runtime: Runtime[LearnerContext]) -> dict[str, Any] | None:
        p = _load_profile(runtime)
        if not p:
            return None
        zpd = p.get("zpd_ranges", {})
        if isinstance(zpd, str):
            zpd = json.loads(zpd)
        sl = p.get("skill_levels", {})
        if isinstance(sl, str):
            sl = json.loads(sl)
        scaffold = state.get("scaffold_level", p.get("scaffold_level", 3))
        mod = p.get("modality_preference", "balanced")
        tone = state.get("coaching_tone", p.get("coaching_tone", "encouraging"))
        return _set_context(state, "zpd",
            f"scaffold={scaffold} modality={mod} tone={tone} "
            f"zpd={json.dumps(zpd)} levels={json.dumps(sl)} "
            "Stay within ZPD — not too easy, not too hard.")


# ══════════════════════════════════════════════════════════════
# MicroTheming
# ══════════════════════════════════════════════════════════════

class MicroThemingMiddleware(AgentMiddleware):
    def before_model(self, state: AgentState, runtime: Runtime[LearnerContext]) -> dict[str, Any] | None:
        p = _load_profile(runtime)
        if not p:
            return None
        interests = p.get("interests", [])
        if not interests:
            return None
        idx = len(state.get("messages", [])) % len(interests)
        active = interests[idx]
        return _set_context(state, "theming",
            f"Theme: '{active}'. Weave into examples naturally. Skip if forced.")


# ══════════════════════════════════════════════════════════════
# Employment Structural
# ══════════════════════════════════════════════════════════════

FRAMINGS = {
    "communication": "Frame as explaining to a coworker.",
    "problem_solving": "Present as a workplace problem to debug.",
    "teamwork": "Frame as team collaboration.",
    "time_management": "Add time/priority constraints.",
    "adaptability": "Present as a changed requirement.",
    "initiative": "Frame as proactive identification.",
    "attention_to_detail": "Emphasize precision and checking.",
    "customer_service": "Frame as helping a customer.",
    "technology": "Include a digital tool in the scenario.",
    "professionalism": "Frame as workplace communication.",
    "results_orientation": "Focus on measurable outcomes.",
    "critical_thinking": "Require evaluating options.",
    "integrity_accountability": "Frame around transparency and accuracy.",
    "self_time_management": "Add estimation or prioritization elements.",
    "collaboration": "Frame as integrating input from teammates.",
    "learning_agility": "Introduce a new constraint mid-problem.",
    "work_ethic": "Emphasize quality standards and double-checking.",
    "tech_fluency": "Embed in a digital tool context like a spreadsheet.",
    "interpersonal": "Frame around navigating a sensitive request.",
}

SIGNAL_PATTERNS = {
    "detailed_response": ("communication", 0.6),
    "asked_question": ("initiative", 0.5),
    "showed_work": ("attention_to_detail", 0.7),
    "alternative_approach": ("problem_solving", 0.6),
    "self_corrected": ("critical_thinking", 0.8),
    # Merged from employment_skills/middleware.py (legacy):
    "unprompted_planning": ("problem_solving", 0.8),
    "self_correction": ("integrity_accountability", 0.9),
    "self_directed_exploration": ("initiative", 0.7),
    "estimation_behavior": ("self_time_management", 0.6),
    "unprompted_summarization": ("communication", 0.8),
}

DECAY_LAMBDA = math.log(2) / 10  # half-life of ~10 interactions


class EmploymentStructuralMiddleware(AgentMiddleware):
    def before_model(self, state: AgentState, runtime: Runtime[LearnerContext]) -> dict[str, Any] | None:
        comps = _load_competencies(runtime)
        if not comps:
            weakest = ["communication", "problem_solving"]
        else:
            sorted_c = sorted(comps, key=lambda c: c.get("strength", 0.5))
            weakest = [c["competency"] for c in sorted_c[:2] if c.get("competency") in FRAMINGS]
            if not weakest:
                weakest = ["communication", "problem_solving"]
        framing = " ".join(FRAMINGS.get(c, "") for c in weakest)
        return _set_context(state, "employment", f"Focus: {', '.join(weakest)}. {framing}")

    def after_model(self, state: AgentState, runtime: Runtime[LearnerContext]) -> dict[str, Any] | None:
        msgs = state.get("messages", [])
        if len(msgs) < 2:
            return None
        human = next((m for m in reversed(msgs) if getattr(m, 'type', '') == "human"), None)
        if not human:
            return None
        content = getattr(human, 'content', "")
        if not content or len(content) < 10:
            return None

        signals = []
        lo = content.lower()
        if len(content.split()) > 30:
            signals.append("detailed_response")
        if "?" in content:
            signals.append("asked_question")
        if any(w in lo for w in ("because", "since", "step", "first")):
            signals.append("showed_work")
        if any(w in lo for w in ("another way", "alternatively", "instead")):
            signals.append("alternative_approach")
        if any(w in lo for w in ("wait", "actually", "let me fix", "correction")):
            signals.append("self_corrected")
        # Extended signal detection (merged from employment_skills/middleware.py):
        if any(w in lo for w in ("first i", "my plan is", "step 1", "i'll start by")):
            signals.append("unprompted_planning")
        if any(w in lo for w in ("i think i made a mistake", "wait, let me check", "that doesn't look right")):
            signals.append("self_correction")
        if any(w in lo for w in ("can i try", "what if", "could we also")):
            signals.append("self_directed_exploration")
        if any(w in lo for w in ("about", "roughly", "i estimate", "probably around")):
            signals.append("estimation_behavior")
        if any(w in lo for w in ("to summarize", "in short", "the main point is", "basically")):
            signals.append("unprompted_summarization")

        if not signals:
            return None

        pending = list(state.get("pending_competency_signals", []))
        turn = len(msgs) // 2
        for key in signals:
            if key not in SIGNAL_PATTERNS:
                continue
            comp, raw = SIGNAL_PATTERNS[key]
            decayed = raw * math.exp(-DECAY_LAMBDA * max(0, turn - 1))
            pending.append({
                "competency": comp, "strength": round(decayed, 4),
                "signal": key, "turn": turn, "timestamp": time.time(),
            })
        return {"pending_competency_signals": pending}


# ══════════════════════════════════════════════════════════════
# Stealth Assessment
# ══════════════════════════════════════════════════════════════

class StealthAssessmentMiddleware(AgentMiddleware):
    def after_model(self, state: AgentState, runtime: Runtime[LearnerContext]) -> dict[str, Any] | None:
        msgs = state.get("messages", [])
        if len(msgs) < 2:
            return None
        human = next((m for m in reversed(msgs) if getattr(m, 'type', '') == "human"), None)
        if not human:
            return None
        content = getattr(human, 'content', "")
        obs = list(state.get("stealth_observations", []))
        obs.append({
            "timestamp": time.time(),
            "response_length": len(content),
            "question_asked": "?" in content,
            "help_requested": any(w in content.lower() for w in ("help", "hint", "confused", "don't understand")),
        })
        return {"stealth_observations": obs}


# ══════════════════════════════════════════════════════════════
# ABA Reinforcement
# ══════════════════════════════════════════════════════════════

class ABAReinforcementMiddleware(AgentMiddleware):
    def after_model(self, state: AgentState, runtime: Runtime[LearnerContext]) -> dict[str, Any] | None:
        p = _load_profile(runtime)
        if not p:
            return None
        schedule = p.get("reinforcement_schedule", "VR-3")
        try:
            base = int(schedule.split("-")[1])
        except (IndexError, ValueError):
            base = 3
        jittered = max(1, base + random.randint(-1, 1))

        # Count recent correct streak from tool messages
        streak = 0
        for msg in reversed(state.get("messages", [])[-10:]):
            c = getattr(msg, 'content', "").lower()
            if "correct" in c:
                streak += 1
            elif "incorrect" in c:
                break

        if streak > 0 and streak % jittered == 0:
            events = list(state.get("gamification_events", []))
            events.append({
                "type": "reinforcement",
                "xp_award": 5 + (streak // 3),
                "streak": streak,
                "schedule": schedule,
            })
            return {"gamification_events": events}
        return None
