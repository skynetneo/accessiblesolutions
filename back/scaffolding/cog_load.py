"""
praxis/scaffolding/cog_load.py

Dynamic Cognitive Load Governor.
Determines if an academic skill is currently taxing the learner's 
cognitive load too much to safely inject employment competency training.
If load is safe, it performs a probabilistically weighted selection of
which competency to inject, mapped to specific instructional directives.
"""

import logging
import random
from typing import TypedDict, Optional, Dict
from pydantic import BaseModel
from employment_skills.skills import CompetencyProfile, EmploymentCompetency

logger = logging.getLogger(__name__)


# ============================================================
# 1. State & Constants
# ============================================================

class GraphState(TypedDict):
    """The state payload passed between LangGraph nodes."""
    learner_id: str
    academic_skill_id: str
    
    # Telemetry representing the learner's current struggle with the academic skill
    # e.g., 0.0 = perfect mastery, 1.0 = failing consistently
    academic_error_rate: float 
    
    # The learner's current competency map
    competency_profile: CompetencyProfile
    
    # Output of this node: Which competency to inject (if any)
    selected_competency: Optional[EmploymentCompetency]
    
    # Output of this node: The specific directive string to pass to the LLM
    injection_directive: Optional[str]


# Specific instructions telling the LLM HOW to weave the competency into the math/reading problem
COMPETENCY_DIRECTIVES: Dict[EmploymentCompetency, str] = {
    EmploymentCompetency.COMMUNICATION: "Frame this problem such that the learner must explain their reasoning clearly to a coworker or manager.",
    EmploymentCompetency.COLLABORATION: "Present this as a team task where the learner must integrate input or data from others to find the solution.",
    EmploymentCompetency.PROBLEM_SOLVING: "Present this as an unexpected obstacle in a workflow that needs to be debugged and resolved.",
    EmploymentCompetency.LEARNING_AGILITY: "Introduce a new rule or constraint midway through the problem to test adaptation.",
    EmploymentCompetency.SELF_TIME_MANAGEMENT: "Add a time constraint or prioritization element to this task (e.g., 'You have 3 tasks, solve this one first').",
    EmploymentCompetency.WORK_ETHIC: "Emphasize quality standards, accuracy, and double-checking work in the prompt framing.",
    EmploymentCompetency.RESULTS_ORIENTATION: "Focus the scenario on measurable outcomes and reaching a specific target metric for a client.",
    EmploymentCompetency.TECH_FLUENCY: "Embed the problem within a digital tool context (e.g., pulling data from a CRM dashboard or a spreadsheet).",
    EmploymentCompetency.INTERPERSONAL: "Frame the problem around helping a frustrated customer or navigating a sensitive client request.",
    EmploymentCompetency.INITIATIVE: "Leave part of the problem slightly ambiguous so the learner must proactively identify the missing step.",
    EmploymentCompetency.INTEGRITY_ACCOUNTABILITY: "Present a scenario where a mistake was made (perhaps by a colleague), and the learner must identify and correct it transparently.",
    EmploymentCompetency.ADAPTABILITY: "Change the initial parameters of the problem slightly and ask the learner to adjust their approach to match the new reality."
}


# ============================================================
# 2. The Dynamic Injection Governor Node
# ============================================================

def evaluate_injection_governor(state: GraphState) -> GraphState:
    """
    LangGraph Node: Determines if a competency should be injected, 
    and if so, executes a weighted probabilistic selection.
    """
    error_rate = state.get("academic_error_rate", 0.0)
    profile = state.get("competency_profile")
    skill_id = state.get("academic_skill_id")
    
    # RULE 1: The Cognitive Load Constraint
    # If the learner is failing > 30% of recent academic probes, abort injection.
    # The system must prioritize primary academic acquisition.
    COGNITIVE_OVERLOAD_THRESHOLD = 0.30
    
    if error_rate >= COGNITIVE_OVERLOAD_THRESHOLD:
        logger.debug("[GOVERNOR] Cognitive load too high (Error rate: %.2f). Bypassing injection.", error_rate)
        return {**state, "selected_competency": None, "injection_directive": None}

    # RULE 2 & 3: Weight Calculation & Decay
    # Fetch the dynamically calculated weights from the Pydantic model
    weights_map: Dict[EmploymentCompetency, float] = profile.calculate_injection_weights(skill_id)
    
    # Separate the keys and values for the random selection function
    competencies = list(weights_map.keys())
    probabilities = list(weights_map.values())
    
    # Normalize the probabilities (optional, but good for debugging/logging)
    total_weight = sum(probabilities)
    if total_weight == 0:
        logger.debug("[GOVERNOR] Zero total weight. Bypassing injection.")
        return {**state, "selected_competency": None, "injection_directive": None}
        
    normalized_probs = [w / total_weight for w in probabilities]
    
    # Execute the probabilistic selection
    # random.choices returns a list, so we grab the first element
    selected: EmploymentCompetency = random.choices(
        population=competencies,
        weights=normalized_probs,
        k=1
    )[0]
    
    logger.debug("[GOVERNOR] Load optimal. Selected %s (Probability mass: %.4f)", selected.value, weights_map[selected])
    
    # Map the selected competency to the precise LLM directive
    directive = COMPETENCY_DIRECTIVES.get(
        selected, 
        f"Apply {selected.value} framing to this problem." # Fallback
    )
    
    # Update state to route to the LLM generation node
    return {
        **state,
        "selected_competency": selected,
        "injection_directive": directive 
    }
