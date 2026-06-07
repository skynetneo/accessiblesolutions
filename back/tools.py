from langchain.tools import tool, ToolRuntime
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from typing import Optional, List, Dict, Any
from pydantic.json_schema import SkipJsonSchema
from db.db import search_resources, upsert_agencies, resolve_location, filter_resources

@tool
def find_agencies(
    query: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    location: Optional[str] = None,
    runtime: SkipJsonSchema[Optional[ToolRuntime]] = None,
) -> Any:
    """
    Search for local agencies, shelters, food banks, and legal services.
    
    Args:
        query: The type of help needed (e.g., "food", "housing", "legal", "eviction").
        latitude: (Optional) User's latitude.
        longitude: (Optional) User's longitude.
        location: (Optional) User-provided city/zip/address to resolve.
    """
    lat = _to_float(latitude)
    lng = _to_float(longitude)

    if location is None and lat is None and lng is None:
        summary = "A city, zip code, or address is needed before searching the database."
        if runtime and runtime.tool_call_id:
            return Command(
                update={
                    "found_agencies": [],
                    "selected_agency_id": None,
                    "messages": [ToolMessage(summary, tool_call_id=runtime.tool_call_id)],
                }
            )
        return []
    location_info = None
    if location or lat is not None or lng is not None:
        location_info = resolve_location(location=location, lat=lat, lng=lng)
        lat = location_info.get("latitude")
        lng = location_info.get("longitude")

        is_lane_county = location_info.get("is_lane_county")
        if is_lane_county is False:
            summary = (
                "Location appears to be outside Lane County, OR. "
                "Use web search for nearby agencies, then call save_agencies."
            )
            if runtime and runtime.tool_call_id:
                return Command(
                    update={
                        "found_agencies": [],
                        "selected_agency_id": None,
                        "messages": [ToolMessage(summary, tool_call_id=runtime.tool_call_id)],
                    }
                )
            return []
        if is_lane_county is None:
            summary = (
                "Couldn't verify whether the location is in Lane County, OR. "
                "Ask for a clearer city/zip before searching the database."
            )
            if runtime and runtime.tool_call_id:
                return Command(
                    update={
                        "found_agencies": [],
                        "selected_agency_id": None,
                        "messages": [ToolMessage(summary, tool_call_id=runtime.tool_call_id)],
                    }
                )
            return []

    results = search_resources(query, lat, lng)

    if runtime and runtime.tool_call_id:
        summary = f"Found {len(results)} resources for '{query}'."
        return Command(
            update={
                "found_agencies": results,
                "selected_agency_id": results[0]["id"] if results else None,
                "messages": [ToolMessage(summary, tool_call_id=runtime.tool_call_id)],
            }
        )

    return results


@tool
def save_agencies(
    agencies: List[Dict[str, Any]],
    runtime: SkipJsonSchema[Optional[ToolRuntime]] = None,
) -> Any:
    """
    Save new agencies to Supabase and update state so the UI shows cards/pins.
    """
    saved = upsert_agencies(agencies)

    if runtime and runtime.tool_call_id:
        summary = f"Saved {len(saved)} new resources."
        return Command(
            update={
                "found_agencies": saved,
                "selected_agency_id": saved[0]["id"] if saved else None,
                "messages": [ToolMessage(summary, tool_call_id=runtime.tool_call_id)],
            }
        )

    return saved

def _to_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

@tool
def navigate_to_page(page_name: str):
    """
    Navigate the user to a specific page in the application.
    
    Args:
        page_name: The destination. Valid options: 
                   'accessfyndr' (for AccessFyndr resource map), 
                   'about' (Mission info),
                   'home' (Home page),
                   'programs' (Programs page), 
                   'getinvolved' (Donation page), 
                   'career' (AccessCareer resume builder),
                   'contact' (Contact Us page).
    """
    # The frontend will listen for this string and trigger a router.push()
    return f"NAVIGATE_TO: {page_name}"

@tool
def update_career_state(
    resume_markdown: Optional[str] = None,
    cover_letter_markdown: Optional[str] = None,
    job_listings: Optional[List[Dict[str, Any]]] = None,
    career_view: Optional[str] = None,
    runtime: SkipJsonSchema[Optional[ToolRuntime]] = None,
) -> Any:
    """
    Update AccessCareer state fields in one call.
    """
    update: Dict[str, Any] = {}
    if resume_markdown is not None:
        update["resume_markdown"] = resume_markdown
    if cover_letter_markdown is not None:
        update["cover_letter_markdown"] = cover_letter_markdown
    if job_listings is not None:
        update["job_listings"] = job_listings
    if career_view is not None:
        update["career_view"] = career_view

    if runtime and runtime.tool_call_id:
        summary = "Updated career state."
        return Command(
            update={
                **update,
                "messages": [ToolMessage(summary, tool_call_id=runtime.tool_call_id)],
            }
        )
    return update

# ──────────────────────────────────────────────────────────────
# Deterministic assistance helpers — zero LLM cost.
# ──────────────────────────────────────────────────────────────

# Stress-phrase → (search_query, programs[]) mapping. The LLM picks a key by
# matching the user's situation; the explanation text below is canned.
ASSISTANCE_INTENTS: Dict[str, Dict[str, Any]] = {
    "food_insecurity": {
        "search_query": "food",
        "programs": ["SNAP", "WIC", "food_pantry", "211"],
        "summary": (
            "If you're struggling to afford groceries, the fastest path is SNAP "
            "(food stamps) and a local food pantry while you wait for SNAP to start."
        ),
    },
    "lost_job": {
        "search_query": "food",
        "programs": ["SNAP", "unemployment_insurance", "TANF", "food_pantry", "211"],
        "summary": (
            "Losing a job often qualifies you for SNAP and Unemployment Insurance "
            "right away. Apply for both today; food pantries can cover the gap."
        ),
    },
    "eviction_risk": {
        "search_query": "housing",
        "programs": ["LIHEAP", "rental_assistance", "211", "legal_aid"],
        "summary": (
            "If eviction is on the table, contact 211 and a local legal-aid clinic "
            "the same day. Many counties have emergency rental-assistance funds."
        ),
    },
    "domestic_violence": {
        "search_query": "domestic violence",
        "programs": ["dv_shelter", "211", "national_dv_hotline"],
        "summary": (
            "Help is available 24/7. The National DV Hotline is 1-800-799-7233 "
            "(text START to 88788). Local shelters can place you tonight."
        ),
    },
    "utilities": {
        "search_query": "utilities",
        "programs": ["LIHEAP", "211"],
        "summary": (
            "LIHEAP helps cover heating/cooling bills. 211 can connect you with "
            "local utility-assistance funds for past-due balances."
        ),
    },
    "medical": {
        "search_query": "medical",
        "programs": ["Medicaid", "free_clinic", "211"],
        "summary": (
            "Medicaid covers medical care for low-income households; eligibility "
            "is broader than most people assume. Free clinics handle urgent needs."
        ),
    },
}

PROGRAM_EXPLANATIONS: Dict[str, str] = {
    "SNAP": (
        "SNAP (Supplemental Nutrition Assistance Program — formerly food stamps) "
        "loads a monthly benefit onto an EBT card you can use at most grocery "
        "stores. Apply through your state DHS/ORS office; if you're in Oregon, "
        "https://benefits.oregon.gov takes about 20 minutes and benefits can "
        "start within 7 days for emergency cases."
    ),
    "WIC": (
        "WIC supports pregnant people, new parents, and kids under 5 with "
        "food vouchers and nutrition support. Income limits are generous — "
        "many working families qualify."
    ),
    "TANF": (
        "TANF is short-term cash assistance for families with kids. It's smaller "
        "than SNAP but pairs well with it."
    ),
    "LIHEAP": (
        "LIHEAP helps low-income households pay heating and cooling bills. "
        "Apply through the local Community Action Agency."
    ),
    "Medicaid": (
        "Medicaid (Oregon Health Plan, in OR) covers medical, dental, and "
        "behavioral health for low-income households. Apply at the same place "
        "you apply for SNAP."
    ),
    "unemployment_insurance": (
        "Unemployment Insurance pays a weekly benefit while you search for "
        "work. File the same week you lose hours — backdating is limited."
    ),
    "rental_assistance": (
        "Many counties have emergency rental-assistance funds for tenants at "
        "imminent risk of eviction. Funds run out fast — call 211 today."
    ),
    "food_pantry": (
        "Local food pantries are the fastest source of free groceries — most "
        "have no income test and you can visit the same day."
    ),
    "free_clinic": (
        "Free and sliding-scale clinics handle primary care for people without "
        "insurance. 211 can route you to the closest one."
    ),
    "legal_aid": (
        "Legal-aid clinics offer free representation for evictions, family law, "
        "and benefits appeals."
    ),
    "dv_shelter": (
        "DV shelters provide confidential same-day housing for survivors. "
        "Locations are not posted publicly — the hotline routes you."
    ),
    "211": (
        "Dialing 2-1-1 connects you to a trained operator who can match you to "
        "every program and resource in your area."
    ),
    "national_dv_hotline": (
        "National DV Hotline: 1-800-799-7233 or text START to 88788. Available 24/7."
    ),
}


@tool
def recommend_assistance(
    situation: str,
    runtime: SkipJsonSchema[Optional[ToolRuntime]] = None,
) -> Any:
    """
    Map a user's stressful situation to relevant aid programs and a brief
    explanation for each. Use this for prompts like "I lost my job and can't
    afford groceries", "I'm about to be evicted", "no power", etc.

    Args:
        situation: One of:
            food_insecurity, lost_job, eviction_risk, domestic_violence,
            utilities, medical.
    """
    intent = ASSISTANCE_INTENTS.get(situation)
    if intent is None:
        msg = (
            f"Unknown situation '{situation}'. Valid keys: "
            f"{', '.join(ASSISTANCE_INTENTS.keys())}."
        )
        if runtime and runtime.tool_call_id:
            return Command(
                update={"messages": [ToolMessage(msg, tool_call_id=runtime.tool_call_id)]}
            )
        return {"error": msg}

    programs = [
        {"key": p, "explanation": PROGRAM_EXPLANATIONS.get(p, p)}
        for p in intent["programs"]
    ]
    payload = {
        "situation": situation,
        "summary": intent["summary"],
        "search_query": intent["search_query"],
        "programs": programs,
    }

    if runtime and runtime.tool_call_id:
        # Encode payload into the tool message so the LLM can render it.
        rendered = (
            f"{payload['summary']}\n\n"
            + "\n".join(f"• {p['key']}: {p['explanation']}" for p in programs)
            + f"\n\n(Now call find_agencies with query='{payload['search_query']}'.)"
        )
        return Command(
            update={"messages": [ToolMessage(rendered, tool_call_id=runtime.tool_call_id)]}
        )

    return payload


@tool
def filter_agencies(
    service_type: Optional[str] = None,
    agency_name: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    max_distance_miles: float = 15,
    runtime: SkipJsonSchema[Optional[ToolRuntime]] = None,
) -> Any:
    """
    Pure-DB filter for the resource map. Cheaper than find_agencies because it
    skips geocoding/web-search fallbacks and Lane County checks.

    Args:
        service_type: e.g. 'food', 'housing', 'legal'.
        agency_name: substring of an agency name to match.
        latitude/longitude: user coords. If provided, results are filtered
            within max_distance_miles and sorted by distance.
        max_distance_miles: radius cap when coordinates are present.
    """
    lat = _to_float(latitude)
    lng = _to_float(longitude)

    results = filter_resources(
        service_type=service_type,
        agency_name=agency_name,
        lat=lat,
        lng=lng,
        radius_miles=max_distance_miles,
    )

    if runtime and runtime.tool_call_id:
        summary = f"Filtered to {len(results)} resources."
        return Command(
            update={
                "found_agencies": results,
                "selected_agency_id": results[0]["id"] if results else None,
                "messages": [ToolMessage(summary, tool_call_id=runtime.tool_call_id)],
            }
        )
    return results


@tool
def switch_career_view(
    view: str,
    runtime: SkipJsonSchema[Optional[ToolRuntime]] = None,
):
    """
    Switch the Career Dashboard view.
    Args:
        view: One of 'resume', 'cover_letter', 'jobs'.
    """
    if runtime and runtime.tool_call_id:
        return Command(
            update={
                "career_view": view,
                "messages": [
                    ToolMessage(
                        f"Switched career view to {view}.",
                        tool_call_id=runtime.tool_call_id,
                    )
                ],
            }
        )
    return f"SWITCHED_VIEW_TO: {view}"
