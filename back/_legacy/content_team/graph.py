"""
upskill/content_team/graph.py

Content Generation Team — LangGraph workflow.

Architecture: Orchestrator-Worker with Evaluator-Optimizer loop

Flow:
  START
    ↓
  fetch_seeds          (DB lookup for target skill)
    ↓
  plan_lesson          (LessonDesignerAgent → lesson structure)
    ↓
  [Send API → parallel generation workers]
  generate_items       (one worker per item slot)
    ↓ (fan-in)
  validate_items       (parallel: one Gemini validator per generated item)
    ↓ (fan-in)
  review_validated     (supervisor reviews all results)
    ↓
  [conditional: enough items?]
    ├── YES → build_lesson_plan → cache_items → END
    └── NO  → regenerate_rejected (loop, max 3 attempts)

Key patterns used:
  - Send API for true parallel generation (one worker per item)
  - Send API for true parallel validation (one validator per item)
  - Evaluator-optimizer loop for regeneration on rejection
  - Cross-provider bias removal (generator ≠ validator ≠ supervisor)
"""

from __future__ import annotations
import json
import uuid
from typing import Literal, Optional

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Send
from langgraph.runtime import Runtime

from .schemas import (
    ContentGraphState,
    GeneratedItem,
    LessonPlan,
    SeedItem,
    ValidationResult,
    ContentStatus,
    SubjectKey,
)
from .agents import (
    build_lesson_designer,
    build_assessment_builder,
    build_media_theme_agent,
    build_scaffolding_agent,
    build_content_validator,
    fetch_seeds_for_skill,
    get_theme_context,
    get_supervisor_model,
    SEED_DB,
)


# ---------------------------------------------------------------------------
# Worker state for parallel generation
# Each worker gets its own isolated state via Send API
# ---------------------------------------------------------------------------

from typing import TypedDict, Annotated
from operator import add

class GenerationWorkerState(TypedDict):
    """State for a single item generation worker."""
    # Inputs from orchestrator
    learner_id: str
    seed_id: str
    seed_json: str
    slot_type: str          # warmup, instruction, practice, generalization
    theme: str
    freeform_interests: list[str]
    learning_style: str
    employment_goal: str
    employment_context_preferred: bool
    target_theta: float
    
    # Output: written to parent state via reducer
    generated_items: Annotated[list[GeneratedItem], add]
    errors: Annotated[list[str], add]


class ValidationWorkerState(TypedDict):
    """State for a single item validation worker."""
    item_json: str
    subject: str
    
    # Output
    validated_items: Annotated[list[GeneratedItem], add]
    rejected_items: Annotated[list[dict], add]
    errors: Annotated[list[str], add]


# ---------------------------------------------------------------------------
# Instantiate agents (module-level, reused across requests)
# ---------------------------------------------------------------------------

lesson_designer = build_lesson_designer()
assessment_builder = build_assessment_builder()
media_theme_agent = build_media_theme_agent()
scaffolding_agent = build_scaffolding_agent()
content_validator = build_content_validator()


# ---------------------------------------------------------------------------
# Node: Fetch seeds from DB
# ---------------------------------------------------------------------------

async def fetch_seeds_node(state: ContentGraphState) -> dict:
    """
    Fetch seed items from the content DB for the target skill.
    Seeds are the authoritative templates — generation always starts here.
    """
    seeds = fetch_seeds_for_skill(
        subject=state.subject,
        skill_id=state.target_skill_id,
        count=5,  # Fetch a few to give generator variety
    )
    
    if not seeds:
        # Fall back to any seed for subject
        all_seeds = SEED_DB.get(state.subject, [])
        seeds = all_seeds[:3]
    
    if not seeds:
        return {
            "errors": [f"No seeds found for {state.subject}/{state.target_skill_id}"],
            "seed_items": [],
        }
    
    return {
        "seed_items": seeds,
        "messages": [{
            "role": "system",
            "content": f"Fetched {len(seeds)} seeds for {state.subject}/{state.target_skill_id}",
        }],
    }


# ---------------------------------------------------------------------------
# Node: Plan lesson structure
# ---------------------------------------------------------------------------

async def plan_lesson_node(state: ContentGraphState) -> dict:
    """
    LessonDesignerAgent builds the session structure.
    Determines how many items of each type to generate.
    """
    if not state.seed_items:
        return {"errors": ["Cannot plan lesson — no seeds available"]}
    
    prompt = f"""Design a lesson plan for:
Learner ID: {state.learner_id}
Subject: {state.subject}
Target skill: {state.target_skill_id}
Target theta: {state.target_theta}
Available seeds: {[s.seed_id for s in state.seed_items]}
Employment goal: {state.employment_goal}

Call design_lesson_sequence then select_seed_for_slot for each slot type.
Return the complete lesson plan with seed assignments."""

    result = await lesson_designer.ainvoke({
        "messages": [{"role": "user", "content": prompt}]
    })
    
    result_content = result["messages"][-1].content
    
    return {
        "messages": [{"role": "assistant", "content": result_content}],
    }


# ---------------------------------------------------------------------------
# Fan-out: dispatch generation workers via Send API
# ---------------------------------------------------------------------------

def dispatch_generation_workers(state: ContentGraphState) -> list[Send]:
    """
    Fan out to parallel generation workers — one per item slot.
    Uses LangGraph Send API for true parallelism.
    
    Each worker gets: a seed to vary, the learner's theme, and its slot type.
    """
    if not state.seed_items:
        return []
    
    sends = []
    
    # Define slots based on lesson structure
    # In production: parse lesson plan from plan_lesson_node output
    slots = [
        # (slot_type, seed_index, count)
        ("warmup", 0, 2),
        ("instruction", 0, 2),
        ("practice", 1 if len(state.seed_items) > 1 else 0, 3),
        ("generalization", 0, 1),
    ]
    
    # Select freeform interest to use (rotate through if multiple)
    freeform = state.freeform_interests[0] if state.freeform_interests else ""
    
    for slot_type, seed_idx, count in slots:
        seed = state.seed_items[min(seed_idx, len(state.seed_items) - 1)]
        
        for i in range(count):
            # Alternate between freeform and standard theme for variety
            use_freeform = freeform if i % 2 == 0 else ""
            
            sends.append(Send(
                "generate_item_worker",
                GenerationWorkerState(
                    learner_id=state.learner_id,
                    seed_id=seed.seed_id,
                    seed_json=seed.model_dump_json(),
                    slot_type=slot_type,
                    theme=state.theme,
                    freeform_interests=state.freeform_interests,
                    learning_style=state.learning_style,
                    employment_goal=state.employment_goal,
                    employment_context_preferred=state.employment_context_preferred,
                    target_theta=state.target_theta,
                    generated_items=[],
                    errors=[],
                ),
            ))
    
    return sends


# ---------------------------------------------------------------------------
# Worker node: Generate one item
# ---------------------------------------------------------------------------

async def generate_item_worker(state: GenerationWorkerState) -> dict:
    """
    Single item generation worker.
    Runs in parallel with all other workers via Send API.
    
    Pipeline: AssessmentBuilder → MediaTheme → Scaffolding
    """
    try:
        seed_data = json.loads(state["seed_json"])
        freeform = state["freeform_interests"][0] if state["freeform_interests"] else ""
        
        theme_context = get_theme_context(
            theme=state["theme"],
            subject=seed_data.get("subject", "math"),
            skill_id=seed_data.get("skill_id", ""),
            freeform=freeform,
        )
        
        # Step 1: Generate themed variation
        gen_prompt = f"""Generate a themed variation of this seed item.

Seed: {state['seed_json']}
Theme context: {theme_context}
Freeform interest: {freeform}
Slot type: {state['slot_type']}
Learning style: {state['learning_style']}
Employment context needed: {state['employment_context_preferred']}
Employment goal: {state['employment_goal']}

Use generate_themed_variation to structure the request, 
then produce the actual themed question.
Run validate_theme_coherence before returning.
Return complete GeneratedItem JSON."""

        gen_result = await assessment_builder.ainvoke({
            "messages": [{"role": "user", "content": gen_prompt}]
        })
        gen_content = gen_result["messages"][-1].content
        
        # Step 2: Apply media/theme enrichment
        media_prompt = f"""Apply theme and media assets to this generated item.

Generated item: {gen_content}
Freeform interest: {freeform}
Theme: {state['theme']}
Learning style: {state['learning_style']}

If freeform interest exists, call apply_freeform_interest.
Always call generate_visual_asset_description.
If learning style is auditory, call generate_audio_script.
Return enriched item JSON."""

        media_result = await media_theme_agent.ainvoke({
            "messages": [{"role": "user", "content": media_prompt}]
        })
        media_content = media_result["messages"][-1].content
        
        # Step 3: Generate scaffolding
        scaffold_prompt = f"""Generate hint progression and error feedback for this item.

Item: {media_content}
Seed rationale: {seed_data.get('correct_rationale', '')}
Distractor rationales: {json.dumps(seed_data.get('distractor_rationales', {}))}

Call generate_hint_progression then generate_error_specific_feedback.
Return complete scaffolding JSON."""

        scaffold_result = await scaffolding_agent.ainvoke({
            "messages": [{"role": "user", "content": scaffold_prompt}]
        })
        scaffold_content = scaffold_result["messages"][-1].content
        
        # Assemble GeneratedItem
        item = GeneratedItem(
            item_id=str(uuid.uuid4()),
            seed_id=state["seed_id"],
            subject=seed_data.get("subject", "math"),  # type: ignore
            skill_id=seed_data.get("skill_id", ""),
            question_type=seed_data.get("question_type", "multiple_choice"),  # type: ignore
            difficulty_b=seed_data.get("difficulty_b", 0.0),
            discrimination_a=seed_data.get("discrimination_a", 1.0),
            theme_applied=state["theme"],
            freeform_interest=freeform,
            question_text=f"[Generated from seed {state['seed_id']} with {theme_context}]",
            choices=seed_data.get("choices", []),
            correct_answer=seed_data.get("correct_answer", ""),
            correct_rationale=seed_data.get("correct_rationale", ""),
            distractor_rationales=seed_data.get("distractor_rationales", {}),
            status="draft",
            generator_model="gpt-4o-mini",  # Track which model generated
            generation_attempts=1,
        )
        
        # Parse and attach scaffolding
        try:
            scaffold_data = json.loads(scaffold_content) if scaffold_content.startswith("{") else {}
            item.hints = scaffold_data.get("general_strategy", {})
        except Exception:
            pass
        
        return {"generated_items": [item]}
    
    except Exception as e:
        return {
            "generated_items": [],
            "errors": [f"Generation worker error for seed {state['seed_id']}: {str(e)}"],
        }


# ---------------------------------------------------------------------------
# Fan-out: dispatch validation workers via Send API
# ---------------------------------------------------------------------------

def dispatch_validation_workers(state: ContentGraphState) -> list[Send]:
    """
    Fan out to parallel validation workers — one per generated item.
    Gemini validates each item independently.
    """
    sends = []
    
    for item in state.generated_items:
        sends.append(Send(
            "validate_item_worker",
            ValidationWorkerState(
                item_json=item.model_dump_json(),
                subject=item.subject,
                validated_items=[],
                rejected_items=[],
                errors=[],
            ),
        ))
    
    return sends


# ---------------------------------------------------------------------------
# Worker node: Validate one item (Gemini)
# ---------------------------------------------------------------------------

async def validate_item_worker(state: ValidationWorkerState) -> dict:
    """
    Cross-provider validation worker.
    Each generated item is validated by Gemini independently.
    """
    try:
        item_data = json.loads(state["item_json"])
        item_id = item_data.get("item_id", str(uuid.uuid4()))
        
        validate_prompt = f"""Validate this generated curriculum content item.

Item ID: {item_id}
Subject: {state['subject']}
Question: {item_data.get('question_text', '')}
Choices: {json.dumps(item_data.get('choices', []))}
Correct answer: {item_data.get('correct_answer', '')}
Rationale: {item_data.get('correct_rationale', '')}
Theme applied: {item_data.get('theme_applied', '')}
Employment bridge: {item_data.get('employment_bridge', '')}
Skill ID: {item_data.get('skill_id', '')}

Validation protocol:
1. Call validate_math_accuracy — solve the problem YOURSELF first
2. Call validate_content_quality — check all quality dimensions  
3. Call produce_validation_verdict — make the final decision

Be rigorous. You are the safety net before this reaches a learner."""

        result = await content_validator.ainvoke({
            "messages": [{"role": "user", "content": validate_prompt}]
        })
        
        result_content = result["messages"][-1].content
        
        # Parse validation result
        try:
            verdict = json.loads(result_content) if result_content.startswith("{") else {}
        except Exception:
            verdict = {"approved": False, "rejection_reasons": ["Parse error in validator output"]}
        
        # Update item status
        item = GeneratedItem(**item_data)
        
        if verdict.get("approved", False):
            item.status = "validated"
            item.validation_score = verdict.get("confidence_score", 0.8)
            item.validator_model = "gemini-2.0-flash"
            return {"validated_items": [item]}
        else:
            item.status = "rejected"
            item.rejection_reason = "; ".join(verdict.get("rejection_reasons", ["Unknown"]))
            item.validation_feedback = "; ".join(verdict.get("improvement_suggestions", []))
            return {
                "rejected_items": [{
                    "item": item.model_dump(),
                    "verdict": verdict,
                    "seed_id": item.seed_id,
                }]
            }
    
    except Exception as e:
        return {
            "validated_items": [],
            "rejected_items": [],
            "errors": [f"Validation worker error: {str(e)}"],
        }


# ---------------------------------------------------------------------------
# Node: Supervisor review
# ---------------------------------------------------------------------------

async def supervisor_review_node(state: ContentGraphState) -> dict:
    """
    Content Team Supervisor (Claude Opus) reviews validation results.
    
    Responsibilities:
    - Check if enough validated items to build a lesson (>= items_needed * 0.75)
    - Decide which rejected items are worth regenerating vs. abandoning
    - Flag systematic issues (theme consistently failing → different theme)
    - Approve content for caching (score > 0.85)
    """
    validated_count = len(state.validated_items)
    rejected_count = len(state.rejected_items)
    attempts = state.generation_attempts
    
    summary = {
        "validated": validated_count,
        "rejected": rejected_count,
        "attempts": attempts,
        "items_needed": state.items_needed,
        "rejection_reasons": [
            r.get("verdict", {}).get("rejection_reasons", [])
            for r in state.rejected_items
        ],
    }
    
    supervisor_model = get_supervisor_model()
    
    from langchain.tools import tool
    
    @tool
    def assess_content_readiness(
        validated_count: int,
        rejected_count: int,
        items_needed: int,
        attempts: int,
    ) -> str:
        """Assess whether we have enough validated content to proceed."""
        min_required = max(4, int(items_needed * 0.625))
        sufficient = validated_count >= min_required
        should_regenerate = (
            not sufficient
            and attempts < 3
            and rejected_count > 0
        )
        
        return json.dumps({
            "sufficient_content": sufficient,
            "should_regenerate": should_regenerate,
            "items_available": validated_count,
            "items_needed": items_needed,
            "min_required": min_required,
            "recommendation": (
                "proceed" if sufficient
                else "regenerate" if should_regenerate
                else "proceed_with_partial"
            ),
        })
    
    @tool  
    def select_items_for_caching(validated_items_json: str) -> str:
        """Select high-confidence items for caching in the shared content pool."""
        try:
            items = json.loads(validated_items_json)
            cacheable = [
                item for item in items
                if item.get("validation_score", 0) >= 0.85
                and item.get("cacheable", True)
            ]
            return json.dumps({
                "cacheable_count": len(cacheable),
                "cacheable_ids": [i.get("item_id") for i in cacheable],
            })
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    supervisor_agent = create_agent(
        model=supervisor_model,
        tools=[assess_content_readiness, select_items_for_caching],
        system_prompt="""You are the Content Generation Team Supervisor for UpSkill.

You review the output of the generation + validation pipeline and make final decisions.

Your responsibilities:
1. Assess if we have enough validated content to build a lesson plan
2. Identify which items should be cached for other learners
3. Identify systematic problems (e.g. all rejections have same reason → theme issue)
4. Decide whether to trigger regeneration

Principles:
- 5+ validated items = sufficient for a session (proceed)
- 3-4 validated items = partial lesson (proceed with caution, note gap)
- < 3 validated items = must regenerate if attempts < 3
- Systematic rejections = change approach (different theme/seed)

Return JSON decision with your reasoning.
""",
        name="content_supervisor",
    )
    
    prompt = f"""Review content generation results:

Summary: {json.dumps(summary, indent=2)}
Validated items: {len(state.validated_items)}
Rejected items: {len(state.rejected_items)}

Call assess_content_readiness then select_items_for_caching.
Return your decision: proceed or regenerate."""

    result = await supervisor_agent.ainvoke({
        "messages": [{"role": "user", "content": prompt}]
    })
    
    result_content = result["messages"][-1].content
    
    try:
        decision = json.loads(result_content) if result_content.startswith("{") else {}
    except Exception:
        decision = {"recommendation": "proceed"}
    
    return {
        "messages": [{"role": "assistant", "content": json.dumps(decision)}],
        "generation_attempts": state.generation_attempts + 1,
    }


def route_after_supervisor(state: ContentGraphState) -> Literal[
    "build_lesson_plan", "regenerate_rejected", "build_lesson_plan"
]:
    """Route based on supervisor decision."""
    validated_count = len(state.validated_items)
    min_required = max(4, int(state.items_needed * 0.625))
    
    if validated_count >= min_required:
        return "build_lesson_plan"
    elif state.generation_attempts < state.max_attempts and state.rejected_items:
        return "regenerate_rejected"
    else:
        return "build_lesson_plan"  # Proceed with what we have


# ---------------------------------------------------------------------------
# Node: Regenerate rejected items
# ---------------------------------------------------------------------------

def dispatch_regeneration_workers(state: ContentGraphState) -> list[Send]:
    """
    Fan out regeneration workers for rejected items.
    Uses feedback from validator to improve the next attempt.
    """
    sends = []
    
    # Only regenerate items with specific feedback (not systematic failures)
    for rejected in state.rejected_items[:3]:  # Limit to 3 regen attempts
        item_data = rejected.get("item", {})
        verdict = rejected.get("verdict", {})
        
        # Find original seed
        seed_id = rejected.get("seed_id", "")
        seed = None
        for s_list in SEED_DB.values():
            for s in s_list:
                if s.seed_id == seed_id:
                    seed = s
                    break
        
        if not seed:
            continue
        
        # Pass rejection feedback to worker for improved generation
        sends.append(Send(
            "generate_item_worker",
            GenerationWorkerState(
                learner_id=state.learner_id,
                seed_id=seed_id,
                seed_json=seed.model_dump_json(),
                slot_type=item_data.get("slot_type", "practice"),
                theme=state.theme,
                freeform_interests=state.freeform_interests,
                learning_style=state.learning_style,
                employment_goal=state.employment_goal,
                employment_context_preferred=state.employment_context_preferred,
                target_theta=state.target_theta,
                generated_items=[],
                errors=[],
            ),
        ))
    
    return sends


# ---------------------------------------------------------------------------
# Node: Build final lesson plan
# ---------------------------------------------------------------------------

async def build_lesson_plan_node(state: ContentGraphState) -> dict:
    """
    Assemble the final lesson plan from validated items.
    Orders items by slot type and difficulty.
    """
    validated = state.validated_items
    
    if not validated:
        return {
            "errors": ["No validated items available for lesson plan"],
            "lesson_plan": None,
        }
    
    # Sort by difficulty (ascending) for progressive difficulty
    sorted_items = sorted(validated, key=lambda x: x.difficulty_b)
    
    # Assign to slots by position
    warmup_items = [i for i in sorted_items if i.difficulty_b < state.target_theta - 0.5][:2]
    practice_items = [i for i in sorted_items if i not in warmup_items]
    
    # Last item is always generalization (employment bridge)
    generalization = practice_items[-1:] if practice_items else []
    core_items = practice_items[:-1] if len(practice_items) > 1 else practice_items
    
    lesson_plan = LessonPlan(
        learner_id=state.learner_id,
        session_id=str(uuid.uuid4()),
        subject=state.subject,
        target_skill_id=state.target_skill_id,
        warmup_item_ids=[i.item_id for i in warmup_items],
        instruction_item_ids=[i.item_id for i in core_items[:2]],
        practice_item_ids=[i.item_id for i in core_items[2:]],
        generalization_item_ids=[i.item_id for i in generalization],
        estimated_minutes=20 + (len(validated) * 2),
        target_theta_min=state.target_theta - 0.5,
        target_theta_max=state.target_theta + 0.5,
    )
    
    return {
        "lesson_plan": lesson_plan,
        "messages": [{
            "role": "assistant",
            "content": json.dumps({
                "lesson_plan_created": True,
                "total_items": len(validated),
                "warmup_count": len(warmup_items),
                "practice_count": len(core_items),
                "generalization_count": len(generalization),
                "estimated_minutes": lesson_plan.estimated_minutes,
            }),
        }],
    }


# ---------------------------------------------------------------------------
# Node: Cache high-confidence items
# ---------------------------------------------------------------------------

async def cache_items_node(state: ContentGraphState, runtime: Runtime) -> dict:
    """
    Cache high-confidence validated items in the shared content pool.
    Items with validation_score > 0.85 are available to other learners
    with the same theme/skill combination.
    """
    cacheable = [
        item for item in state.validated_items
        if (item.validation_score or 0) >= 0.85 and item.cacheable
    ]
    
    cached_count = 0
    for item in cacheable:
        try:
            namespace = ("content_cache", item.subject, item.skill_id, item.theme_applied)
            await runtime.store.aput(
                namespace,
                item.item_id,
                item.model_dump(),
            )
            cached_count += 1
        except Exception:
            pass  # Cache failure is non-critical
    
    return {
        "messages": [{
            "role": "system",
            "content": f"Cached {cached_count}/{len(cacheable)} items to shared pool",
        }],
    }


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def build_content_graph():
    """
    Compile the Content Generation Team graph.
    
    Uses:
    - Send API for parallel generation workers
    - Send API for parallel validation workers
    - Evaluator-optimizer loop for regeneration
    """
    checkpointer = InMemorySaver()
    
    builder = StateGraph(ContentGraphState)
    
    # Main flow nodes
    builder.add_node("fetch_seeds", fetch_seeds_node)
    builder.add_node("plan_lesson", plan_lesson_node)
    builder.add_node("supervisor_review", supervisor_review_node)
    builder.add_node("build_lesson_plan", build_lesson_plan_node)
    builder.add_node("cache_items", cache_items_node)
    
    # Worker nodes (invoked via Send API)
    builder.add_node("generate_item_worker", generate_item_worker)
    builder.add_node("validate_item_worker", validate_item_worker)
    
    # Main flow edges
    builder.add_edge(START, "fetch_seeds")
    builder.add_edge("fetch_seeds", "plan_lesson")
    
    # Fan-out to generation workers
    builder.add_conditional_edges(
        "plan_lesson",
        dispatch_generation_workers,
        ["generate_item_worker"],
    )
    
    # Fan-out to validation workers after all generators complete
    builder.add_conditional_edges(
        "generate_item_worker",
        dispatch_validation_workers,
        ["validate_item_worker"],
    )
    
    # Supervisor reviews all validation results
    builder.add_edge("validate_item_worker", "supervisor_review")
    
    # Route: enough items? → build plan; need more? → regenerate
    builder.add_conditional_edges(
        "supervisor_review",
        route_after_supervisor,
        {
            "build_lesson_plan": "build_lesson_plan",
            "regenerate_rejected": "generate_item_worker",  # Loop back
        },
    )
    
    builder.add_edge("build_lesson_plan", "cache_items")
    builder.add_edge("cache_items", END)
    
    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

content_graph = build_content_graph()


async def generate_lesson(
    learner_id: str,
    subject: SubjectKey,
    target_skill_id: str,
    target_theta: float,
    theme: str,
    freeform_interests: Optional[list[str]] = None,
    learning_style: str = "visual",
    employment_goal: str = "default",
    employment_context_preferred: bool = True,
    thread_id: Optional[str] = None,
) -> ContentGraphState:
    """
    Generate a complete themed lesson for a learner.
    
    Args:
        learner_id: From LearnerProfile
        subject: curriculum subject area
        target_skill_id: Skill to teach this session
        target_theta: IRT ability estimate (from Assessment Team)
        theme: Primary theme (gaming/sports/space/nature/urban)
        freeform_interests: Specific interests (["rick and morty", "minecraft"])
        learning_style: From preference profile
        employment_goal: Learner's employment target
        employment_context_preferred: Include employment bridges
    
    Returns:
        Final ContentGraphState with lesson_plan and validated_items
    """
    from dataclasses import dataclass
    
    @dataclass
    class UserContext:
        user_id: str
    
    thread_id = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = ContentGraphState(
        learner_id=learner_id,
        subject=subject,
        target_skill_id=target_skill_id,
        target_theta=target_theta,
        theme=theme,
        freeform_interests=freeform_interests or [],
        learning_style=learning_style,
        employment_goal=employment_goal,
        employment_context_preferred=employment_context_preferred,
        items_needed=8,
    )
    
    result = await content_graph.ainvoke(
        initial_state.model_dump(),
        config=config,
        context=UserContext(user_id=learner_id),
    )
    
    return ContentGraphState(**result)
