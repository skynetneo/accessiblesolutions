"""
DEPRECATED: Legacy employment skills middleware.
The active implementation is EmploymentStructuralMiddleware in middleware/core.py,
which uses the system_context state key pattern and includes all behavioral signal
detection from both this file and the core implementation.
This file is kept for reference only.
"""
from langchain.agents.middleware import (
    AgentMiddleware, ModelRequest, ModelResponse,
    wrap_model_call, dynamic_prompt
)
from langchain.messages import SystemMessage
from langgraph.runtime import Runtime
from typing import Any, Callable
import random

from employment_skills.skills import EmploymentCompetency

# This map was never fully defined in the legacy code.
# The active implementation in middleware/core.py uses FRAMINGS instead.
COMPETENCY_INTEGRATION_MAP: dict[str, dict[str, list[str]]] = {}


class EmploymentSkillsStructuralMiddleware(AgentMiddleware):
    """THE structural layer. Not a module. Not optional. Every interaction
    simultaneously builds academic skills AND workplace competencies.
    
    The learner never sees 'Communication Skills Lesson 3.'
    Instead, every math problem requires them to explain their reasoning.
    Every reading passage asks them to summarize as if updating their team.
    Every writing task has a workplace format (email, memo, status update).
    
    This middleware:
    1. Reads the learner's competency profile from the store
    2. Selects 1-2 competencies to reinforce (prioritizing weak ones)
    3. Injects competency-aligned task framing into the prompt
    4. Tracks demonstrations via stealth observation
    """

    def before_model(self, state, runtime: Runtime) -> dict[str, Any] | None:
        profile = self._get_competency_profile(runtime)
        if not profile:
            return None

        # Select competencies to reinforce this interaction
        selected = self._select_competencies(profile, state)
        if not selected:
            return None

        subject = state.get("current_subject", "math")
        integration_prompts = []

        for comp in selected:
            examples = COMPETENCY_INTEGRATION_MAP.get(comp, {}).get(subject, [])
            if examples:
                chosen = random.choice(examples)
                integration_prompts.append(chosen)

        if not integration_prompts:
            return None

        career = profile.get("target_career_cluster", "general workplace")

        injection = (
            f"[EMPLOYMENT SKILLS — STRUCTURAL LAYER]\n"
            f"Career context: {career}\n"
            f"Reinforce these competencies THROUGH the academic content "
            f"(never name them explicitly to the learner):\n"
        )
        for i, (comp, prompt) in enumerate(zip(selected, integration_prompts)):
            injection += f"\n{i+1}. {comp.upper()}: Frame task so learner must: {prompt}"

        injection += (
            f"\n\nIMPORTANT: These are invisible scaffolding. The learner should feel "
            f"like they're doing a math/reading/writing/science task. The workplace "
            f"competency practice is embedded in HOW the task is structured, not "
            f"called out as a separate learning objective."
        )

        # Inject as additional system context
        return {
            "messages": state["messages"] + [{
                "role": "system",
                "content": injection
            }]
        }

    def after_model(self, state, runtime: Runtime) -> dict[str, Any] | None:
        """Track competency demonstrations via stealth observation."""
        last_msg = state["messages"][-1] if state["messages"] else None
        if not last_msg or last_msg.type != "human":
            return None

        content = last_msg.content.lower() if hasattr(last_msg, 'content') else ""
        observations = []

        # Stealth detection of competency demonstrations
        if any(phrase in content for phrase in [
            "first i", "my plan is", "step 1", "i'll start by"
        ]):
            observations.append({
                "competency": "problem_solving",
                "signal": "unprompted_planning",
                "strength": 0.8,
            })

        if any(phrase in content for phrase in [
            "i think i made a mistake", "wait, let me check", "that doesn't look right"
        ]):
            observations.append({
                "competency": "integrity_accountability",
                "signal": "self_correction",
                "strength": 0.9,
            })

        if any(phrase in content for phrase in [
            "can i try", "what if", "another way", "could we also"
        ]):
            observations.append({
                "competency": "initiative",
                "signal": "self_directed_exploration",
                "strength": 0.7,
            })

        if any(phrase in content for phrase in [
            "about", "roughly", "i estimate", "probably around"
        ]):
            observations.append({
                "competency": "self_time_management",
                "signal": "estimation_behavior",
                "strength": 0.6,
            })

        if any(phrase in content for phrase in [
            "to summarize", "in short", "the main point is", "basically"
        ]):
            observations.append({
                "competency": "communication",
                "signal": "unprompted_summarization",
                "strength": 0.8,
            })

        if observations:
            return {"stealth_observations": observations}
        return None

    def _select_competencies(
        self, profile: dict, state: dict
    ) -> list[str]:
        """Select 1-2 competencies to reinforce, prioritizing weak ones.
        
        Uses a modified Thompson Sampling approach:
        - Competencies with fewer demonstrations get explored more
        - Career cluster overrides boost certain competencies
        - Recent failures increase priority
        """
        competencies = profile.get("competencies", {})
        priority = profile.get("priority_queue", [])
        overrides = profile.get("cluster_weight_overrides", {})

        if priority:
            # Take top priority + one random for variety
            selected = [priority[0]]
            others = [c for c in EmploymentCompetency if c.value != priority[0]]
            if others:
                selected.append(random.choice(others).value)
            return selected[:2]

        # Score each competency: lower strength = higher priority
        scores = {}
        for comp in EmploymentCompetency:
            level = competencies.get(comp.value, {})
            strength = level.get("strength", 0.0) if isinstance(level, dict) else 0.0
            demonstrated = level.get("demonstrated_count", 0) if isinstance(level, dict) else 0
            weight = overrides.get(comp.value, 1.0)

            # Lower strength and fewer demonstrations = higher score
            score = (1.0 - strength) * weight
            if demonstrated < 3:
                score *= 1.5  # Exploration bonus
            scores[comp.value] = score

        # Select top 2
        sorted_comps = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [c[0] for c in sorted_comps[:2]]

    def _get_competency_profile(self, runtime):
        store = runtime.store
        user_id = runtime.context.learner_id
        result = store.get(("learners", "competencies"), user_id)
        return result.value if result else None
