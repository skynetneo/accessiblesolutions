"""
DEPRECATED: Legacy competency tool using LangGraph Store.
The active implementation is in db/tools_bridge.py (update_competency_score),
which uses Supabase for persistent storage. This file is kept for reference only.
"""
from langchain.tools import tool, ToolRuntime
from db.tools_bridge import LearnerContext

@tool
def update_competency_observation(
    competency: str,
    signal: str,
    strength: float,
    runtime: ToolRuntime[LearnerContext]
) -> str:
    """Record a competency demonstration observation.
    Called by stealth assessment, never by the learner."""
    store = runtime.store
    user_id = runtime.context.learner_id

    if store is None:
        return "Store unavailable; observation not recorded."
    
    profile = store.get(("learners", "competencies"), user_id)
    data = profile.value if profile else {"competencies": {}, "priority_queue": []}
    
    comp_data = data["competencies"].get(competency, {
        "demonstrated_count": 0,
        "prompted_count": 0,
        "strength": 0.0,
        "notes": [],
    })
    
    # Rolling average with recency bias
    old_strength = comp_data.get("strength", 0.0)
    count = comp_data.get("demonstrated_count", 0)
    comp_data["strength"] = (old_strength * min(count, 10) + strength) / (min(count, 10) + 1)
    comp_data["demonstrated_count"] = count + 1
    comp_data["notes"].append(signal)
    
    # Keep notes manageable
    if len(comp_data["notes"]) > 20:
        comp_data["notes"] = comp_data["notes"][-20:]
    
    data["competencies"][competency] = comp_data
    
    # Update priority queue: weakest competencies first
    sorted_comps = sorted(
        data["competencies"].items(),
        key=lambda x: x[1].get("strength", 0.0)
    )
    data["priority_queue"] = [c[0] for c in sorted_comps[:4]]
    
    store.put(("learners", "competencies"), user_id, data)
    return f"Recorded {competency} observation: {signal} (strength: {strength:.2f})"
