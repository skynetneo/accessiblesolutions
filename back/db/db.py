"""Local SQLite data layer for AccessFyndr.

Source of truth is `agent/data/agencies.db` with schema:
  agencies(id, name, fees, notes, espanol)
  services(id, agency_id, service_type)
  locations(id, agency_id, address, latitude, longitude)
  contacts(id, agency_id, contact_info)

Override the path with AGENCIES_DB.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# ──────────────────────────────────────────────────────────────
# Connection management
# ──────────────────────────────────────────────────────────────

_DB_LOCK = threading.Lock()
_DB_CONN: sqlite3.Connection | None = None


def _resolve_db_path() -> Path:
    raw = os.environ.get("AGENCIES_DB")
    if raw:
        return Path(raw).expanduser()
    return Path(__file__).parent / "data" / "agencies.db"


def get_conn() -> sqlite3.Connection:
    """Process-shared sqlite3 connection. Rows come back as dict-likes."""
    global _DB_CONN
    if _DB_CONN is None:
        with _DB_LOCK:
            if _DB_CONN is None:
                path = _resolve_db_path()
                path.parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(str(path), check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON")
                _DB_CONN = conn
    return _DB_CONN


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


# ──────────────────────────────────────────────────────────────
# Geocoding (unchanged — Nominatim, no DB dependency)
# ──────────────────────────────────────────────────────────────

def _parse_json_column(value: Any) -> Any:
    if not value:
        return []
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return [value]
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        return [value]


def _haversine(lat1, lon1, lat2, lon2):
    R = 3959.87433  # miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _nominatim_fetch(url: str) -> Any:
    req = Request(url, headers={"User-Agent": "accessfyndr/1.0"})
    with urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _geocode_address(address: str) -> tuple[float, float] | None:
    if not address:
        return None
    try:
        url = "https://nominatim.openstreetmap.org/search?" + urlencode(
            {"q": address, "format": "json", "limit": 1}
        )
        payload = _nominatim_fetch(url)
        if not payload:
            return None
        return float(payload[0]["lat"]), float(payload[0]["lon"])
    except Exception:
        return None


def geocode_with_details(address: str) -> Dict[str, Any] | None:
    if not address:
        return None
    try:
        url = "https://nominatim.openstreetmap.org/search?" + urlencode(
            {"q": address, "format": "json", "limit": 1, "addressdetails": 1}
        )
        payload = _nominatim_fetch(url)
        if not payload:
            return None
        item = payload[0]
        return {
            "latitude": float(item["lat"]),
            "longitude": float(item["lon"]),
            "display_name": item.get("display_name"),
            "details": item.get("address") or {},
        }
    except Exception:
        return None


def reverse_geocode_with_details(lat: float, lng: float) -> Dict[str, Any] | None:
    try:
        url = "https://nominatim.openstreetmap.org/reverse?" + urlencode(
            {"lat": lat, "lon": lng, "format": "json", "zoom": 10, "addressdetails": 1}
        )
        payload = _nominatim_fetch(url)
        if not payload or not isinstance(payload, dict):
            return None
        return {
            "display_name": payload.get("display_name"),
            "details": payload.get("address") or {},
        }
    except Exception:
        return None


def _is_lane_county(county: Optional[str], state: Optional[str], state_code: Optional[str]) -> Optional[bool]:
    if not county or not isinstance(county, str):
        return None
    if "lane" not in county.strip().lower():
        return False

    normalized_state = None
    if isinstance(state_code, str) and state_code:
        code = state_code.strip().upper()
        if code.startswith("US-"):
            code = code[3:]
        normalized_state = code
    if isinstance(state, str) and state and normalized_state is None:
        normalized_state = state.strip().upper()

    if normalized_state in ("OREGON", "OR"):
        return True
    if normalized_state is None:
        return None
    return False


def resolve_location(
    location: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
) -> Dict[str, Any]:
    resolved_lat = lat
    resolved_lng = lng
    details: Dict[str, Any] = {}
    display_name = None

    if (resolved_lat is None or resolved_lng is None) and location:
        geo = geocode_with_details(location)
        if geo:
            resolved_lat = geo.get("latitude")
            resolved_lng = geo.get("longitude")
            details = geo.get("details") or {}
            display_name = geo.get("display_name")

    if (not details) and resolved_lat is not None and resolved_lng is not None:
        rev = reverse_geocode_with_details(resolved_lat, resolved_lng)
        if rev:
            details = rev.get("details") or {}
            display_name = rev.get("display_name") or display_name

    county = details.get("county") or details.get("state_district")
    state = details.get("state") or details.get("region")
    state_code = details.get("state_code") or details.get("ISO3166-2-lvl4")

    return {
        "latitude": resolved_lat,
        "longitude": resolved_lng,
        "county": county,
        "state": state,
        "state_code": state_code,
        "display_name": display_name,
        "is_lane_county": _is_lane_county(county, state, state_code),
    }


# ──────────────────────────────────────────────────────────────
# Internal: fetch + assemble agency rows
# ──────────────────────────────────────────────────────────────

def _fetch_agencies_by_id(ids: Iterable[Any]) -> List[Dict[str, Any]]:
    id_list = [i for i in ids if i is not None]
    if not id_list:
        return []
    placeholders = ",".join("?" for _ in id_list)
    conn = get_conn()
    rows = conn.execute(
        f"SELECT id, name, notes, fees, espanol FROM agencies WHERE id IN ({placeholders})",
        id_list,
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _attach_relations(agencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not agencies:
        return agencies
    ids = [a["id"] for a in agencies]
    placeholders = ",".join("?" for _ in ids)
    conn = get_conn()

    loc_rows = conn.execute(
        f"SELECT agency_id, address, latitude, longitude FROM locations WHERE agency_id IN ({placeholders})",
        ids,
    ).fetchall()
    svc_rows = conn.execute(
        f"SELECT agency_id, service_type FROM services WHERE agency_id IN ({placeholders})",
        ids,
    ).fetchall()

    loc_by_agency: Dict[Any, List[sqlite3.Row]] = {}
    for r in loc_rows:
        loc_by_agency.setdefault(r["agency_id"], []).append(r)
    svc_by_agency: Dict[Any, List[str]] = {}
    for r in svc_rows:
        svc_by_agency.setdefault(r["agency_id"], []).append(r["service_type"])

    enriched: List[Dict[str, Any]] = []
    for a in agencies:
        locs = loc_by_agency.get(a["id"], [])
        loc = locs[0] if locs else None
        enriched.append(
            {
                **a,
                "_address": loc["address"] if loc else None,
                "_latitude": loc["latitude"] if loc else None,
                "_longitude": loc["longitude"] if loc else None,
                "_services": [s for s in svc_by_agency.get(a["id"], []) if s],
            }
        )
    return enriched


def _to_result(
    a: Dict[str, Any],
    user_lat: Optional[float],
    user_lng: Optional[float],
) -> Optional[Dict[str, Any]]:
    rid = a.get("id")
    name = a.get("name")
    if rid is None or name is None:
        return None

    r_lat = a.get("_latitude")
    r_lng = a.get("_longitude")

    distance: Optional[float] = None
    if user_lat is not None and user_lng is not None and r_lat is not None and r_lng is not None:
        try:
            distance = _haversine(user_lat, user_lng, float(r_lat), float(r_lng))
        except (ValueError, TypeError):
            distance = None

    return {
        "id": str(rid),
        "name": name,
        "description": a.get("notes"),
        "address": a.get("_address"),
        "latitude": r_lat,
        "longitude": r_lng,
        "fees": a.get("fees"),
        "espanol": _parse_json_column(a.get("espanol")),
        "services": a.get("_services") or [],
        "distance_miles": round(distance, 1) if distance is not None else None,
    }


# ──────────────────────────────────────────────────────────────
# Public API: search / filter / upsert
# ──────────────────────────────────────────────────────────────

def search_resources(
    query: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_miles: float = 15,
) -> List[Dict[str, Any]]:
    """Free-text search on agency name/notes + service types."""
    conn = get_conn()
    like = f"%{query}%"
    name_match = conn.execute(
        "SELECT id FROM agencies WHERE name LIKE ? OR notes LIKE ?",
        (like, like),
    ).fetchall()
    svc_match = conn.execute(
        "SELECT agency_id FROM services WHERE service_type LIKE ?",
        (like,),
    ).fetchall()

    ids = {r["id"] for r in name_match if r["id"] is not None}
    ids.update(r["agency_id"] for r in svc_match if r["agency_id"] is not None)
    if not ids:
        return []

    enriched = _attach_relations(_fetch_agencies_by_id(ids))
    results: List[Dict[str, Any]] = []
    for a in enriched:
        item = _to_result(a, lat, lng)
        if item is None:
            continue
        if (
            lat is not None
            and lng is not None
            and item["distance_miles"] is not None
            and item["distance_miles"] > radius_miles
        ):
            continue
        results.append(item)

    if lat is not None and lng is not None:
        results.sort(key=lambda x: x["distance_miles"] if x["distance_miles"] is not None else 999)
    return results[:10]


def filter_resources(
    service_type: Optional[str] = None,
    agency_name: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_miles: float = 15,
) -> List[Dict[str, Any]]:
    """Pure filter for the sidebar UI. Skips Lane County checks."""
    conn = get_conn()
    ids: set[Any] = set()
    used_filter = False

    if agency_name:
        used_filter = True
        rows = conn.execute(
            "SELECT id FROM agencies WHERE name LIKE ?",
            (f"%{agency_name}%",),
        ).fetchall()
        ids.update(r["id"] for r in rows if r["id"] is not None)

    if service_type:
        used_filter = True
        rows = conn.execute(
            "SELECT agency_id FROM services WHERE service_type LIKE ?",
            (f"%{service_type}%",),
        ).fetchall()
        ids.update(r["agency_id"] for r in rows if r["agency_id"] is not None)

    if used_filter:
        if not ids:
            return []
        agencies = _fetch_agencies_by_id(ids)
    else:
        rows = conn.execute(
            "SELECT id, name, notes, fees, espanol FROM agencies LIMIT 200"
        ).fetchall()
        agencies = [_row_to_dict(r) for r in rows]

    enriched = _attach_relations(agencies)
    results: List[Dict[str, Any]] = []
    for a in enriched:
        item = _to_result(a, lat, lng)
        if item is None:
            continue
        if (
            lat is not None
            and lng is not None
            and item["distance_miles"] is not None
            and item["distance_miles"] > radius_miles
        ):
            continue
        results.append(item)

    if lat is not None and lng is not None:
        results.sort(key=lambda x: x["distance_miles"] if x["distance_miles"] is not None else 999)
    return results[:25]


def upsert_agencies(agencies: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Insert agencies + locations + services into the local DB.

    Used when the agent web-searches resources outside Lane County and wants
    to persist them so the map can render.
    """
    conn = get_conn()
    saved: List[Dict[str, Any]] = []

    for agency in agencies:
        name = agency.get("name") or agency.get("agency_name")
        if not name:
            continue

        description = agency.get("description") or agency.get("notes")
        address = agency.get("address")
        lat = agency.get("latitude")
        lng = agency.get("longitude")

        if (lat is None or lng is None) and address:
            geo = _geocode_address(address)
            if geo:
                lat, lng = geo

        with conn:
            existing = conn.execute(
                "SELECT id FROM agencies WHERE name = ? LIMIT 1", (name,)
            ).fetchone()
            if existing:
                agency_id = existing["id"]
            else:
                cur = conn.execute(
                    "INSERT INTO agencies (name, notes, fees, espanol) VALUES (?, ?, ?, ?)",
                    (
                        name,
                        description,
                        agency.get("fees"),
                        json.dumps(agency.get("espanol")) if agency.get("espanol") is not None else None,
                    ),
                )
                agency_id = cur.lastrowid

            if address or lat is not None or lng is not None:
                conn.execute(
                    "INSERT INTO locations (agency_id, address, latitude, longitude) VALUES (?, ?, ?, ?)",
                    (agency_id, address, lat, lng),
                )

            services = agency.get("services") or []
            if isinstance(services, str):
                services = [services]
            for svc in services:
                if not svc:
                    continue
                conn.execute(
                    "INSERT INTO services (agency_id, service_type) VALUES (?, ?)",
                    (agency_id, svc),
                )

        saved.append(
            {
                "id": str(agency_id),
                "name": name,
                "description": description,
                "address": address,
                "latitude": lat,
                "longitude": lng,
                "fees": agency.get("fees"),
                "espanol": agency.get("espanol"),
                "services": agency.get("services") or [],
            }
        )

    return saved


# Backwards-compatible aliases — kept so any external code that imported them
# from db.py keeps working. New code should use the functions above directly.
def get_supabase() -> Any:  # pragma: no cover - removed
    raise RuntimeError(
        "Supabase client is no longer used. Data lives in agent/data/agencies.db. "
        "Use get_conn(), search_resources(), filter_resources(), or upsert_agencies()."
    )


__all__ = [
    "get_conn",
    "search_resources",
    "filter_resources",
    "upsert_agencies",
    "resolve_location",
    "geocode_with_details",
    "reverse_geocode_with_details",
]
