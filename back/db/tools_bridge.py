"""
praxis/db/tools_bridge.py

Bridges the Supabase ContentDB to LangGraph's tool system.

Every agent in the platform needs curriculum data (seeds, chains, cached items)
and learner data (profiles, mastery, competencies). The ContentDB in client.py
speaks Supabase. The agents speak ToolRuntime. This file translates between them.

All tools use asyncio.to_thread() to wrap the synchronous Supabase client
for compatibility with LangGraph's async execution model.

Context: agents receive a LearnerContext at invocation time containing the
learner_id. Tools use this to scope all queries to the current learner.

Usage:
    from db.tools_bridge import (
        fetch_seed_content,
        check_content_cache,
        save_validated_content,
        fetch_skill_chain,
        fetch_learning_style_guidance,
        get_learner_profile,
        update_learner_profile,
        get_learner_mastery,
        update_learner_mastery,
        get_competency_profile,
        update_competency_observation,
        log_stealth_observation,
    )

    agent = create_agent(
        model="...",
        tools=[fetch_seed_content, check_content_cache, ...],
        context_schema=LearnerContext,
    )
"""

from __future__ import annotations

import asyncio
import time
import uuid
import json
from dataclasses import dataclass
from typing import Optional, Any

from langchain.tools import tool, ToolRuntime
from langgraph.types import Command

from db.client import db
from scaffolding.prompt_hierarchy import LEVEL_MAX as PROMPT_LEVEL_INDEPENDENT


# ──────────────────────────────────────────────────────────────
# Context schema — passed at invocation time to every agent
# ──────────────────────────────────────────────────────────────

@dataclass
class LearnerContext:
    """Immutable context injected at agent invocation.
    Every tool can read this via runtime.context.

    curriculum_id determines which CurriculumProfile is active for this
    session. Use get_curriculum(context.curriculum_id) to load it.
    """
    learner_id: str
    session_id: str = ""
    curriculum_id: str = "ged"


# ──────────────────────────────────────────────────────────────
# Curriculum Tools (seeds, chains, generated content cache)
# ──────────────────────────────────────────────────────────────

@tool
async def fetch_seed_content(
    subject: str,
    skill_id: str,
    chain_step: Optional[int] = None,
    difficulty_min: Optional[float] = None,
    difficulty_max: Optional[float] = None,
    fluency_probe_only: bool = False,
    limit: int = 5,
    runtime: ToolRuntime[LearnerContext] = None,
) -> str:
    """Fetch expert-authored seed items from the curriculum database.

    Seeds are the canonical examples that content generators use as templates.
    Each seed contains a question stem, choices, correct answer, rationale,
    distractor rationales, IRT parameters, and employment context hooks.

    Args:
        subject: Curriculum subject area (e.g., math, rla, hardware, software)
        skill_id: Specific skill (e.g. fractions_decimals, inference)
        chain_step: Specific step in the skill chain (None = any step)
        difficulty_min: Minimum IRT difficulty parameter b
        difficulty_max: Maximum IRT difficulty parameter b
        fluency_probe_only: Only return fluency probe seeds
        limit: Maximum seeds to return
    """
    seeds = await asyncio.to_thread(
        db.fetch_seeds,
        subject=subject,
        skill_id=skill_id,
        curriculum_id=runtime.context.curriculum_id if runtime else "ged",
        chain_step=chain_step,
        fluency_probe_only=fluency_probe_only,
        difficulty_min=difficulty_min,
        difficulty_max=difficulty_max,
        limit=limit,
    )
    if not seeds:
        return f"No seeds found for {subject}/{skill_id} (step={chain_step})"

    # Format for agent consumption — structured but readable
    formatted = []
    for s in seeds:
        entry = (
            f"--- SEED: {s.get('seed_id', 'unknown')} ---\n"
            f"skill: {s.get('skill_id')}, step: {s.get('chain_step')}\n"
            f"difficulty_b: {s.get('difficulty_b')}, discrimination_a: {s.get('discrimination_a')}\n"
            f"question_type: {s.get('question_type')}\n"
        )
        if s.get("passage_text"):
            entry += f"passage: {s['passage_text'][:500]}\n"
        entry += f"question: {s.get('question_text')}\n"
        choices = s.get("choices", [])
        if choices:
            entry += "choices:\n" + "\n".join(f"  {c}" for c in choices) + "\n"
        entry += f"correct: {s.get('correct_answer')}\n"
        entry += f"rationale: {s.get('correct_rationale')}\n"
        distractors = s.get("distractor_rationales", {})
        if distractors:
            entry += "distractor_rationales:\n"
            for letter, reason in distractors.items():
                entry += f"  {letter}: {reason}\n"
        emp = s.get("employment_contexts", [])
        if emp:
            entry += f"employment_hooks: {', '.join(emp)}\n"
        formatted.append(entry)

    return "\n".join(formatted)


@tool
async def fetch_seeds_for_session(
    subject: str,
    skill_id: str,
    chain_id: str,
    step_numbers: list[int],
    runtime: ToolRuntime[LearnerContext] = None,
) -> str:
    """Fetch seeds for multiple chain steps at once.
    Used by the LessonDesigner when planning a full session.

    Args:
        subject: Curriculum subject area
        skill_id: Skill being taught
        chain_id: The skill chain identifier
        step_numbers: List of step numbers to fetch seeds for
    """
    seeds_by_step = await asyncio.to_thread(
        db.fetch_seeds_for_step_range,
        subject=subject,
        skill_id=skill_id,
        chain_id=chain_id,
        step_numbers=step_numbers,
        curriculum_id=runtime.context.curriculum_id if runtime else "ged",
    )

    parts = []
    for step, seeds in seeds_by_step.items():
        parts.append(f"=== STEP {step} ({len(seeds)} seeds) ===")
        for s in seeds:
            parts.append(
                f"  [{s.get('seed_id')}] "
                f"b={s.get('difficulty_b')}, "
                f"q={s.get('question_text', '')[:80]}..."
            )
    return "\n".join(parts) if parts else "No seeds found for specified steps."


@tool
async def check_content_cache(
    skill_id: str,
    item_role: str = "target",
    theme: Optional[str] = None,
    freeform_interest: Optional[str] = None,
    chain_step: Optional[int] = None,
    modality_id: Optional[str] = None,
    min_validation_score: float = 0.75,
    limit: int = 8,
    runtime: ToolRuntime[LearnerContext] = None,
) -> str:
    """Check if validated generated content exists before generating new items.

    A cache hit avoids a full generation + cross-provider validation round.
    Returns cached items if available, or signals that generation is needed.

    Args:
        skill_id: Skill to check cache for
        item_role: "target" (new learning) or "mastered" (review)
        theme: Theme category to match
        freeform_interest: Specific learner interest for micro-theming
        chain_step: Specific chain step
        modality_id: Learning modality (visual, auditory, kinesthetic)
        min_validation_score: Minimum quality threshold
        limit: Max items to return
    """
    # First check if we have enough cached items
    is_miss = await asyncio.to_thread(
        db.cache_miss,
        skill_id=skill_id,
        item_role=item_role,
        theme=theme,
        chain_step=chain_step,
        modality_id=modality_id,
        min_validation_score=min_validation_score,
    )

    if is_miss:
        return (
            f"CACHE_MISS: Fewer than 3 validated items for "
            f"skill={skill_id}, step={chain_step}, theme={theme}, modality={modality_id}. "
            f"Content generation needed."
        )

    # Cache hit — fetch the items
    items = await asyncio.to_thread(
        db.fetch_cached_items,
        skill_id=skill_id,
        item_role=item_role,
        theme=theme,
        freeform_interest=freeform_interest,
        chain_step=chain_step,
        modality_id=modality_id,
        min_validation_score=min_validation_score,
        limit=limit,
    )

    parts = [f"CACHE_HIT: {len(items)} validated items available."]
    for item in items:
        parts.append(
            f"  [{item.get('item_id', '?')}] "
            f"score={item.get('validation_score', 0):.2f}, "
            f"theme={item.get('theme_applied', 'none')}, "
            f"interest={item.get('freeform_interest', 'none')}"
        )
    return "\n".join(parts)


@tool
async def save_validated_content(
    item_id: str,
    skill_id: str,
    chain_step: Optional[int],
    item_role: str,
    question_text: str,
    choices: list[str],
    correct_answer: str,
    correct_rationale: str,
    theme_applied: str,
    freeform_interest: str,
    modality_id: str,
    validation_score: float,
    difficulty_b: float,
    discrimination_a: float,
    generator_model: str,
    validator_model: str,
    seed_id: str,
    employment_context: str = "",
    distractor_rationales: Optional[dict] = None,
    passage_text: Optional[str] = None,
    cacheable: bool = True,
    runtime: ToolRuntime[LearnerContext] = None,
) -> str:
    """Save a validated generated item to the content cache.

    Called by the content pipeline AFTER cross-provider validation passes.
    Items saved here can be reused for other learners with matching criteria.

    Args:
        item_id: Unique identifier for this generated item
        skill_id: Skill this item targets
        chain_step: Step in the skill chain
        item_role: "target" or "mastered"
        question_text: The generated question
        choices: Answer choices
        correct_answer: Letter of correct answer
        correct_rationale: Explanation of correct answer
        theme_applied: Theme category used
        freeform_interest: Specific interest woven in
        modality_id: Learning modality
        validation_score: Score from cross-provider validator (0.0-1.0)
        difficulty_b: IRT difficulty parameter
        discrimination_a: IRT discrimination parameter
        generator_model: Model that generated this item
        validator_model: Model that validated this item
        seed_id: Source seed this was generated from
        employment_context: Workplace context applied
        distractor_rationales: Explanation for each wrong answer
        passage_text: Reading passage if applicable
        cacheable: Whether this item can be reused for other learners
    """
    row = {
        "item_id": item_id,
        "skill_id": skill_id,
        "chain_step": chain_step,
        "item_role": item_role,
        "question_text": question_text,
        "choices": choices,
        "correct_answer": correct_answer,
        "correct_rationale": correct_rationale,
        "theme_applied": theme_applied,
        "freeform_interest": freeform_interest,
        "modality_id": modality_id,
        "validation_score": validation_score,
        "difficulty_b": difficulty_b,
        "discrimination_a": discrimination_a,
        "generator_model": generator_model,
        "validator_model": validator_model,
        "seed_id": seed_id,
        "employment_context": employment_context,
        "distractor_rationales": distractor_rationales or {},
        "passage_text": passage_text,
        "cacheable": cacheable,
        "status": "validated",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    result = await asyncio.to_thread(db.write_generated_item, row)
    if result:
        return f"Saved validated item {item_id} (score={validation_score:.2f})"
    return f"FAILED to save item {item_id}"


@tool
async def fetch_skill_chain(
    skill_id: str,
    runtime: ToolRuntime[LearnerContext] = None,
) -> str:
    """Get the step sequence for a skill chain.

    Returns the chain definition including all steps, their descriptions,
    prerequisites, and target behaviors.

    Args:
        skill_id: The skill chain to fetch (e.g. fractions_decimals)
    """
    chain = await asyncio.to_thread(db.fetch_chain, skill_id)
    if not chain:
        return f"No chain found for skill_id={skill_id}"
    return json.dumps(chain, indent=2, default=str)


@tool
async def fetch_all_chains_for_subject(
    subject: str,
    runtime: ToolRuntime[LearnerContext] = None,
) -> str:
    """Fetch all skill chains for a given subject area.

    Used by the skill graph builder and lesson sequencer to understand
    the full curriculum structure.

    Args:
        subject: The subject id (e.g., 'math', 'hardware')
    """
    chains = await asyncio.to_thread(db.fetch_all_chains, subject)
    if not chains:
        return f"No chains found for subject={subject}"

    parts = [f"=== {subject.upper()} CHAINS ({len(chains)}) ==="]
    for c in chains:
        parts.append(
            f"  [{c.get('chain_id', '?')}] {c.get('skill_id', '?')}: "
            f"{c.get('description', 'no description')}"
        )
    return "\n".join(parts)


@tool
async def fetch_learning_style_guidance(
    style_id: str,
    runtime: ToolRuntime[LearnerContext] = None,
) -> str:
    """Get content adaptation guidance for a specific learning style.

    Returns tips on how to present content for visual, auditory,
    kinesthetic, or read-write learners.

    Args:
        style_id: Learning style identifier
    """
    tips = await asyncio.to_thread(db.fetch_learning_style_tips, style_id)
    if not tips:
        return f"No style guidance found for style_id={style_id}"
    return json.dumps(tips, indent=2, default=str)


# ──────────────────────────────────────────────────────────────
# Learner Profile Tools (Supabase learner_profiles table)
# ──────────────────────────────────────────────────────────────

@tool
async def get_learner_profile(
    runtime: ToolRuntime[LearnerContext],
) -> str:
    """Get the current learner's complete profile.

    Returns all profile data: skill levels, interests, preferences,
    employment goals, modality weights, scaffold settings, etc.
    """
    learner_id = runtime.context.learner_id

    result = await asyncio.to_thread(
        lambda: db.client.table("learner_profiles")
        .select("*")
        .eq("learner_id", learner_id)
        .maybe_single()
        .execute()
    )

    if result.data:
        return json.dumps(result.data, indent=2, default=str)
    return f"No profile found for learner {learner_id}. Run intake/onboarding first."


@tool
async def update_learner_profile(
    updates: dict,
    runtime: ToolRuntime[LearnerContext],
) -> str:
    """Update specific fields on the learner's profile.

    Merges the provided updates with the existing profile.
    Only the ProfileUpdaterAgent or assessment team should call this.

    Args:
        updates: Dict of field names to new values. Only include fields to change.
                 Examples: {"interests": ["music", "gaming"]},
                          {"modality_preference": "visual"},
                          {"scaffold_level": 3}
    """
    learner_id = runtime.context.learner_id

    # Add updated_at timestamp
    updates["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    result = await asyncio.to_thread(
        lambda: db.client.table("learner_profiles")
        .update(updates)
        .eq("learner_id", learner_id)
        .execute()
    )

    if result.data:
        return f"Profile updated for {learner_id}: {list(updates.keys())}"
    return f"FAILED to update profile for {learner_id}. Profile may not exist."


@tool
async def create_learner_profile(
    profile_data: dict,
    runtime: ToolRuntime[LearnerContext],
) -> str:
    """Create a new learner profile during onboarding.

    Called once during initial assessment/intake. After this, use
    update_learner_profile for modifications.

    Args:
        profile_data: Complete initial profile data
    """
    learner_id = runtime.context.learner_id
    profile_data["learner_id"] = learner_id
    profile_data["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    profile_data["updated_at"] = profile_data["created_at"]

    result = await asyncio.to_thread(
        lambda: db.client.table("learner_profiles")
        .upsert(profile_data, on_conflict="learner_id")
        .execute()
    )

    if result.data:
        return f"Profile created for {learner_id}"
    return f"FAILED to create profile for {learner_id}"


# ──────────────────────────────────────────────────────────────
# Mastery Tracking Tools (Supabase learner_mastery table)
# ──────────────────────────────────────────────────────────────

@tool
async def get_learner_mastery(
    skill_id: Optional[str] = None,
    runtime: ToolRuntime[LearnerContext] = None,
) -> str:
    """Get mastery data for the current learner.

    Returns per-skill mastery state: prompt level, consecutive correct/error
    counts, mastered status, next review date, etc.

    Args:
        skill_id: Specific skill to check (None = all skills for this learner)
    """
    learner_id = runtime.context.learner_id

    q = (
        db.client.table("learner_mastery")
        .select("*")
        .eq("learner_id", learner_id)
    )
    if skill_id:
        q = q.eq("skill_id", skill_id)

    result = await asyncio.to_thread(lambda: q.execute())
    data = result.data or []

    if not data:
        scope = f"skill={skill_id}" if skill_id else "any skills"
        return f"No mastery data for learner {learner_id} on {scope}."

    return json.dumps(data, indent=2, default=str)


from datetime import datetime, timedelta, timezone

@tool
async def record_mastery_attempt(
    skill_id: str,
    chain_step: int,
    correct: bool,
    prompt_level: int,
    runtime: ToolRuntime[LearnerContext],
) -> str:
    """Record a learning attempt and update mastery tracking."""
    learner_id = runtime.context.learner_id
    now = datetime.now(timezone.utc)
    now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Fetch current mastery record
    existing = await asyncio.to_thread(
        lambda: db.client.table("learner_mastery")
        .select("*")
        .eq("learner_id", learner_id)
        .eq("skill_id", skill_id)
        .eq("chain_step", chain_step)
        .maybe_single()
        .execute()
    )

    if existing.data:
        row = existing.data
        total_attempts = row.get("total_attempts", 0) + 1
        total_correct = row.get("total_correct", 0) + (1 if correct else 0)

        if correct:
            consecutive_correct = row.get("consecutive_correct", 0) + 1
            consecutive_errors = 0
        else:
            consecutive_correct = 0
            consecutive_errors = row.get("consecutive_errors", 0) + 1

        # Check mastery: 5 consecutive correct at the INDEPENDENT level
        mastered = consecutive_correct >= 5 and prompt_level == PROMPT_LEVEL_INDEPENDENT
        
        # Determine dates
        mastered_at = row.get("mastered_at")
        review_interval = row.get("review_interval_days", 1)
        next_review_at = row.get("next_review_at")
        
        if mastered and not row.get("mastered"):
            # First time mastering!
            mastered_at = now_str
            review_interval = 1
            next_review_at = (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        elif mastered and correct:
            # Maintained mastery, push the review date back further (Spaced Retrieval)
            review_interval = min(review_interval * 2, 30) # Cap at 30 days
            next_review_at = (now + timedelta(days=review_interval)).strftime("%Y-%m-%dT%H:%M:%SZ")

        update = {
            "prompt_level": prompt_level,
            "consecutive_correct": consecutive_correct,
            "consecutive_errors": consecutive_errors,
            "total_attempts": total_attempts,
            "total_correct": total_correct,
            "mastered": mastered,
            "mastered_at": mastered_at,
            "review_interval_days": review_interval,
            "next_review_at": next_review_at,
            "last_attempt_at": now_str,
            "updated_at": now_str,
        }

        await asyncio.to_thread(
            lambda: db.client.table("learner_mastery")
            .update(update)
            .eq("id", row["id"])
            .execute()
        )

        status = "MASTERED!" if mastered and not row.get("mastered") else (
            f"streak={consecutive_correct}" if correct else f"errors={consecutive_errors}"
        )
        return f"Recorded: {skill_id}/{chain_step} {'✓' if correct else '✗'} (level={prompt_level}, {status})"

    else:
        # First attempt on this skill/step
        new_row = {
            "learner_id": learner_id,
            "skill_id": skill_id,
            "chain_step": chain_step,
            "prompt_level": prompt_level,
            "consecutive_correct": 1 if correct else 0,
            "consecutive_errors": 0 if correct else 1,
            "total_attempts": 1,
            "total_correct": 1 if correct else 0,
            "mastered": False,
            "last_attempt_at": now_str,
            "review_interval_days": 1,
            "created_at": now_str,
            "updated_at": now_str,
        }

        await asyncio.to_thread(lambda: db.client.table("learner_mastery").insert(new_row).execute())
        return f"First attempt: {skill_id}/{chain_step} {'✓' if correct else '✗'} (level={prompt_level})"


@tool
async def get_skills_due_for_review(
    runtime: ToolRuntime[LearnerContext],
) -> str:
    """Get mastered skills that are due for spaced retrieval maintenance.
    Returns skills where next_review_at is <= current time.
    """
    learner_id = runtime.context.learner_id
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # DB-level filtering! Massively faster and highly scalable.
    result = await asyncio.to_thread(
        lambda: db.client.table("learner_mastery")
        .select("skill_id, chain_step, next_review_at, review_interval_days")
        .eq("learner_id", learner_id)
        .eq("mastered", True)
        .lte("next_review_at", now_str)
        .execute()
    )

    data = result.data or []
    if not data:
        return "No skills currently due for review."
    
    return json.dumps(data, indent=2, default=str)

@tool
async def get_mastered_skills(
    runtime: ToolRuntime[LearnerContext],
) -> str:
    """Get all mastered skills for the current learner.

    Used by the skill graph to determine which prerequisites are met
    and which new skills can be unlocked.
    """
    learner_id = runtime.context.learner_id

    result = await asyncio.to_thread(
        lambda: db.client.table("learner_mastery")
        .select("skill_id, chain_step, mastered_at")
        .eq("learner_id", learner_id)
        .eq("mastered", True)
        .execute()
    )

    data = result.data or []
    if not data:
        return "No mastered skills yet."

    return json.dumps(data, default=str)



# ──────────────────────────────────────────────────────────────
# Competency Tracking Tools (Supabase learner_competencies table)
# ──────────────────────────────────────────────────────────────

@tool
async def get_competency_profile(
    runtime: ToolRuntime[LearnerContext],
) -> str:
    """Get the current learner's employment competency profile.

    Returns scores for all 12 workplace competencies:
    communication, collaboration, problem_solving, learning_agility,
    self_time_management, work_ethic, results_orientation, tech_fluency,
    interpersonal, initiative, integrity_accountability, adaptability
    """
    learner_id = runtime.context.learner_id

    result = await asyncio.to_thread(
        lambda: db.client.table("learner_competencies")
        .select("*")
        .eq("learner_id", learner_id)
        .execute()
    )

    data = result.data or []
    if not data:
        return "No competency data. The structural layer will begin tracking automatically."
    return json.dumps(data, indent=2, default=str)


@tool
async def update_competency_score(
    competency: str,
    signal: str,
    strength: float,
    runtime: ToolRuntime[LearnerContext],
) -> str:
    """Record a competency demonstration observation.

    Called by the EmploymentSkillsStructuralMiddleware after detecting
    behavioral signals. The learner never sees this happening.

    Uses rolling average with recency bias for the strength score.

    Args:
        competency: One of the 12 employment competencies
        signal: What was observed (e.g. "unprompted_planning", "self_correction")
        strength: Confidence in the observation (0.0-1.0)
    """
    learner_id = runtime.context.learner_id
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Fetch existing competency record
    existing = await asyncio.to_thread(
        lambda: db.client.table("learner_competencies")
        .select("*")
        .eq("learner_id", learner_id)
        .eq("competency", competency)
        .maybe_single()
        .execute()
    )

    if existing.data:
        row = existing.data
        old_strength = row.get("strength", 0.0)
        count = row.get("demonstrated_count", 0)
        # Rolling average with recency bias (cap lookback at 10)
        new_strength = (old_strength * min(count, 10) + strength) / (min(count, 10) + 1)

        notes = row.get("notes", [])
        if isinstance(notes, str):
            try:
                notes = json.loads(notes)
            except (json.JSONDecodeError, TypeError):
                notes = []
        notes.append(f"{now}: {signal}")
        if len(notes) > 20:
            notes = notes[-20:]

        update = {
            "strength": round(new_strength, 4),
            "demonstrated_count": count + 1,
            "last_demonstrated": now,
            "notes": json.dumps(notes),
            "updated_at": now,
        }

        await asyncio.to_thread(
            lambda: db.client.table("learner_competencies")
            .update(update)
            .eq("id", row["id"])
            .execute()
        )

        return (
            f"Updated {competency}: {old_strength:.2f}→{new_strength:.2f} "
            f"(signal={signal}, count={count + 1})"
        )

    else:
        new_row = {
            "learner_id": learner_id,
            "competency": competency,
            "strength": round(strength, 4),
            "demonstrated_count": 1,
            "prompted_count": 0,
            "last_demonstrated": now,
            "notes": json.dumps([f"{now}: {signal}"]),
            "created_at": now,
            "updated_at": now,
        }

        await asyncio.to_thread(
            lambda: db.client.table("learner_competencies")
            .insert(new_row)
            .execute()
        )

        return f"First observation for {competency}: {signal} (strength={strength:.2f})"


# ──────────────────────────────────────────────────────────────
# Stealth Assessment Tools
# ──────────────────────────────────────────────────────────────

@tool
async def log_stealth_observation(
    observation_type: str,
    data: dict,
    runtime: ToolRuntime[LearnerContext],
) -> str:
    """Log a behavioral observation without the learner knowing.

    Stealth assessment captures signals like response patterns, error types,
    help-seeking behavior, and engagement indicators. These feed into
    profile adaptations but NEVER affect mastery determination.

    Args:
        observation_type: Category of observation
            - "response_latency": Time to respond (for UX adaptation, NOT mastery)
            - "error_pattern": Type of error made
            - "help_seeking": Whether/how learner asked for help
            - "engagement": Response length, question-asking, elaboration
            - "competency_signal": Employment competency demonstration
            - "misconception": Detected misconception pattern
        data: Observation payload (varies by type)
    """
    learner_id = runtime.context.learner_id
    session_id = runtime.context.session_id

    row = {
        "learner_id": learner_id,
        "session_id": session_id,
        "observation_type": observation_type,
        "data": json.dumps(data) if isinstance(data, dict) else data,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    await asyncio.to_thread(
        lambda: db.client.table("stealth_observations").insert(row).execute()
    )

    return f"Logged stealth: {observation_type}"


# ──────────────────────────────────────────────────────────────
# Work Profile Tools (Employment Services)
# ──────────────────────────────────────────────────────────────

@tool
async def get_work_profile(
    runtime: ToolRuntime[LearnerContext],
) -> str:
    """Get the learner's employment work profile.

    Contains their actual work history, education, certifications,
    career goals, and constraints — all from real data gathered
    during intake (resume upload/paste or conversational probing).
    """
    learner_id = runtime.context.learner_id

    result = await asyncio.to_thread(
        lambda: db.client.table("work_profiles")
        .select("*")
        .eq("learner_id", learner_id)
        .maybe_single()
        .execute()
    )

    if result.data:
        return json.dumps(result.data, indent=2, default=str)
    return "No work profile found. Run employment intake first."


@tool
async def save_work_profile(
    profile_data: dict,
    runtime: ToolRuntime[LearnerContext],
) -> str:
    """Save or update the learner's work profile.

    Called by the employment intake flow after data collection is complete.

    Args:
        profile_data: Complete work profile data from intake
    """
    learner_id = runtime.context.learner_id
    profile_data["learner_id"] = learner_id
    profile_data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    result = await asyncio.to_thread(
        lambda: db.client.table("work_profiles")
        .upsert(profile_data, on_conflict="learner_id")
        .execute()
    )

    if result.data:
        return f"Work profile saved for {learner_id}"
    return f"FAILED to save work profile for {learner_id}"


# ──────────────────────────────────────────────────────────────
# Convenience: Tool collections for each team
# ──────────────────────────────────────────────────────────────

CURRICULUM_TOOLS = [
    fetch_seed_content,
    fetch_seeds_for_session,
    check_content_cache,
    save_validated_content,
    fetch_skill_chain,
    fetch_all_chains_for_subject,
    fetch_learning_style_guidance,
]

LEARNER_TOOLS = [
    get_learner_profile,
    update_learner_profile,
    create_learner_profile,
]

MASTERY_TOOLS = [
    get_learner_mastery,
    record_mastery_attempt,
    get_mastered_skills,
    get_skills_due_for_review,
]

COMPETENCY_TOOLS = [
    get_competency_profile,
    update_competency_score,
]

STEALTH_TOOLS = [
    log_stealth_observation,
]

EMPLOYMENT_TOOLS = [
    get_work_profile,
    save_work_profile,
]

# What each team needs:
ASSESSMENT_TEAM_TOOLS = CURRICULUM_TOOLS + LEARNER_TOOLS + MASTERY_TOOLS + STEALTH_TOOLS
CONTENT_TEAM_TOOLS = CURRICULUM_TOOLS + LEARNER_TOOLS
COACHING_TEAM_TOOLS = CURRICULUM_TOOLS + LEARNER_TOOLS + MASTERY_TOOLS + COMPETENCY_TOOLS + STEALTH_TOOLS
EMPLOYMENT_TEAM_TOOLS = EMPLOYMENT_TOOLS + LEARNER_TOOLS + COMPETENCY_TOOLS
GAMIFICATION_TEAM_TOOLS = LEARNER_TOOLS + MASTERY_TOOLS + COMPETENCY_TOOLS
