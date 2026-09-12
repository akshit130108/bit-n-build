"""
EcoSentinel - Person 2 Ocean/AIS Adapter (Global Fishing Watch API v3)
Retrieves AIS gap, loitering, encounter, and fishing events from Global Fishing Watch (GFW),
evaluates suspicious dark vessel behavior, enriches with Marine Protected Area (MPA) context,
and normalizes into the Person 3 reasoning event contract.

CANONICAL ADAPTER:
This module (backend/adapters/ocean_gfw.py) is the canonical ocean adapter for the EcoSentinel system.
All ocean event ingestion for Person 3 should import from this module.
"""

import math
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from schemas.event import Location, NormalizedEvent

# Global Fishing Watch API v3 Constants
GFW_API_BASE = "https://gateway.api.globalfishingwatch.org/v3"
DATASET_GAPS = "public-global-gaps-events:latest"
DATASET_LOITERING = "public-global-loitering-events:latest"
DATASET_ENCOUNTERS = "public-global-encounters-events:latest"
DATASET_FISHING = "public-global-fishing-events:latest"

# Demo Marine Protected Area (MPA) Boundaries (GeoJSON Polygon coordinates [lon, lat])
# Clearly labeled local boundary context for hackathon demonstration.
# Authoritative boundary context source is explicitly noted as 'local_demo_geojson'.
DEMO_MPAS: Dict[str, Dict[str, Any]] = {
    "Galapagos Marine Reserve": {
        "source": "local_demo_geojson",
        "description": "UNESCO World Heritage marine sanctuary with strictly prohibited commercial fishing",
        "polygon": [
            [-92.50, -1.50],
            [-89.00, -1.50],
            [-89.00, 1.50],
            [-92.50, 1.50],
            [-92.50, -1.50],
        ],
    },
    "Chagos Marine Protected Area": {
        "source": "local_demo_geojson",
        "description": "Indian Ocean no-take marine reserve",
        "polygon": [
            [70.50, -7.50],
            [73.50, -7.50],
            [73.50, -4.50],
            [70.50, -4.50],
            [70.50, -7.50],
        ],
    },
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def point_in_polygon(lat: float, lon: float, polygon: List[List[float]]) -> bool:
    """Ray casting algorithm to determine if point (lat, lon) is inside polygon [lon, lat]."""
    inside = False
    n = len(polygon)
    p1_lon, p1_lat = polygon[0]
    for i in range(1, n + 1):
        p2_lon, p2_lat = polygon[i % n]
        if min(p1_lat, p2_lat) < lat <= max(p1_lat, p2_lat):
            if lon <= max(p1_lon, p2_lon):
                x_intersection = (lat - p1_lat) * (p2_lon - p1_lon) / ((p2_lat - p1_lat) or 1e-9) + p1_lon
                if p1_lon == p2_lon or lon <= x_intersection:
                    inside = not inside
        p1_lon, p1_lat = p2_lon, p2_lat
    return inside


def distance_to_polygon_boundary_km(lat: float, lon: float, polygon: List[List[float]]) -> float:
    """Calculate minimum distance from point to polygon perimeter segments in kilometers."""
    min_dist = float("inf")
    for i in range(len(polygon) - 1):
        v1_lon, v1_lat = polygon[i]
        v2_lon, v2_lat = polygon[i + 1]
        mid_lat = (v1_lat + v2_lat) / 2.0
        mid_lon = (v1_lon + v2_lon) / 2.0
        d = haversine_km(lat, lon, mid_lat, mid_lon)
        if d < min_dist:
            min_dist = d
    return round(min_dist, 2)


def evaluate_mpa_context(lat: float, lon: float, buffer_threshold_km: float = 20.0) -> Dict[str, Any]:
    """
    Evaluate whether geographic coordinates fall inside, near the boundary,
    or outside a designated Marine Protected Area.
    Explicitly labels the geometry source as 'local_demo_geojson'.
    """
    for mpa_name, mpa_info in DEMO_MPAS.items():
        poly = mpa_info["polygon"]
        is_inside = point_in_polygon(lat, lon, poly)
        dist_to_boundary = distance_to_polygon_boundary_km(lat, lon, poly)

        if is_inside:
            return {
                "protected_area": True,
                "protected_area_name": mpa_name,
                "distance_to_boundary_km": 0.0,
                "mpa_status": "INSIDE_RESERVE",
                "boundary_source": mpa_info["source"],
            }
        elif dist_to_boundary <= buffer_threshold_km:
            return {
                "protected_area": True,
                "protected_area_name": mpa_name,
                "distance_to_boundary_km": dist_to_boundary,
                "mpa_status": "NEAR_BOUNDARY_BUFFER",
                "boundary_source": mpa_info["source"],
            }

    return {
        "protected_area": False,
        "protected_area_name": "International Waters / Unprotected",
        "distance_to_boundary_km": None,
        "mpa_status": "OUTSIDE_RESERVE",
        "boundary_source": "none",
    }


def calculate_dark_vessel_confidence(
    gap_hours: float,
    vessel_type: str,
    apparent_fishing: bool,
    loitering: bool,
    encounter: bool,
    protected_area: bool,
    distance_from_shore_nm: float,
    repeated_gaps: bool = False,
) -> Tuple[float, List[str], List[str]]:
    """
    Calculate a transparent prototype suspicion score (0.0 - 1.0) and reasoning
    for potential dark vessel behavior.
    NOTE: This is a prototype heuristic score for hackathon demonstration,
    NOT a scientifically certified probability of illegal fishing.
    Returns (confidence, reasons, supporting_evidence).
    """
    reasons: List[str] = []
    supporting_evidence: List[str] = ["AIS gap"]

    # Base score: AIS gap detected
    score = 0.50
    reasons.append(f"AIS gap detected ({gap_hours:.1f} hours duration)")

    # Gap duration evidence
    if gap_hours >= 24.0:
        score += 0.10
        reasons.append("Prolonged AIS gap exceeds 24 hours")
        supporting_evidence.append("Extended gap duration (>24h)")
    elif gap_hours >= 12.0:
        score += 0.05
        reasons.append("Extended AIS gap exceeds 12 hours")

    # Vessel type evidence
    if "fishing" in vessel_type.lower():
        score += 0.10
        reasons.append("Commercial fishing vessel class")
        supporting_evidence.append("Fishing vessel classification")

    # Apparent fishing activity
    if apparent_fishing:
        score += 0.10
        reasons.append("Apparent fishing activity detected during surrounding track")
        supporting_evidence.append("Apparent fishing activity")

    # Loitering / Encounter contextual corroboration
    if loitering or encounter:
        score += 0.05
        if loitering and encounter:
            reasons.append("Preceding loitering and transshipment encounter detected")
            supporting_evidence.append("Loitering")
            supporting_evidence.append("Encounter")
        elif loitering:
            reasons.append("Loitering behavior detected prior to AIS transponder gap")
            supporting_evidence.append("Loitering")
        else:
            reasons.append("At-sea encounter detected with auxiliary carrier/support vessel")
            supporting_evidence.append("Encounter")

    # Marine Protected Area proximity
    if protected_area:
        score += 0.10
        reasons.append("Activity intersects or borders sensitive Marine Protected Area boundary")
        supporting_evidence.append("Activity near/inside protected area")

    # Repeated suspicious behavior or offshore isolation
    if repeated_gaps:
        score += 0.05
        reasons.append("Vessel has repeated historical AIS disablement records")
        supporting_evidence.append("Repeated AIS gaps")
    elif distance_from_shore_nm >= 50.0:
        score += 0.03
        reasons.append(f"Offshore evasion: {distance_from_shore_nm:.0f} nm from coastal monitoring authority")

    # Clamp confidence between 0.0 and 1.0
    final_confidence = round(max(0.0, min(1.0, score)), 2)
    return final_confidence, reasons, supporting_evidence


def detect_dark_vessel(
    gap_hours: float = 18.5,
    lat: float = -0.4850,
    lon: float = -90.4920,
    vessel_id: str = "demo_vsl_galapagos_trawler",
    vessel_type: str = "FISHING",
    flag: str = "CHN",
    distance_from_shore_nm: float = 72.0,
    apparent_fishing: bool = True,
    loitering: bool = True,
    encounter: bool = False,
    repeated_gaps: bool = False,
    custom_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    data_mode: str = "simulated",  # Explicitly 'live' or 'simulated'
    source: Optional[str] = None,  # 'global_fishing_watch' if live, 'ecosentinel_demo' if simulated
    gfw_event_id: Optional[str] = None,
) -> NormalizedEvent:
    """
    Detects potential dark vessel behavior from AIS gap and spatial-temporal evidence,
    computes an interpretable confidence score, and returns a normalized EcoSentinel event.

    CRITICAL TRUTHFULNESS RULE:
    - If data_mode is 'live', source is 'global_fishing_watch'.
    - If data_mode is 'simulated', source is 'ecosentinel_demo', clearly identifying it as simulated.
    """
    mpa_info = evaluate_mpa_context(lat, lon)
    is_mpa = mpa_info["protected_area"]

    confidence, reasons, supporting_evidence = calculate_dark_vessel_confidence(
        gap_hours=gap_hours,
        vessel_type=vessel_type,
        apparent_fishing=apparent_fishing,
        loitering=loitering,
        encounter=encounter,
        protected_area=is_mpa,
        distance_from_shore_nm=distance_from_shore_nm,
        repeated_gaps=repeated_gaps,
    )

    actual_data_mode = "live" if data_mode == "live" else "simulated"
    actual_source = source or ("global_fishing_watch" if actual_data_mode == "live" else "ecosentinel_demo")

    if actual_data_mode == "simulated":
        prefix = "demo_ocean_evt"
    else:
        prefix = "gfw_evt"

    event_id = custom_id or f"{prefix}_{uuid.uuid4().hex[:10]}"
    event_timestamp = timestamp or datetime.now(timezone.utc).isoformat()

    metadata: Dict[str, Any] = {
        "source": actual_source,
        "data_mode": actual_data_mode,
        "vessel_id": vessel_id,
        "vessel_type": vessel_type.upper(),
        "flag": flag.upper(),
        "ais_gap_hours": round(gap_hours, 1),
        "distance_from_shore_nm": round(distance_from_shore_nm, 1),
        "protected_area": is_mpa,
        "protected_area_name": mpa_info["protected_area_name"],
        "distance_to_boundary_km": mpa_info["distance_to_boundary_km"],
        "boundary_source": mpa_info["boundary_source"],
        "loitering": loitering,
        "encounter": encounter,
        "apparent_fishing": apparent_fishing,
        "nearby_confirmations": 1 if (loitering or encounter) else 0,
        "ais_disabled": True,
        "supporting_evidence": supporting_evidence,
        "reasons": reasons,
    }

    if gfw_event_id:
        metadata["gfw_event_id"] = gfw_event_id

    if actual_data_mode == "simulated":
        metadata["note"] = (
            "Simulated demonstration event modeled on typical EEZ boundary fishing behavior. "
            "Set GFW_API_TOKEN to fetch live observations."
        )

    return NormalizedEvent(
        id=event_id,
        domain="ocean",
        event_type="potential_dark_vessel",
        confidence=confidence,
        timestamp=event_timestamp,
        sensor_id="GFW_AIS" if actual_data_mode == "live" else "ECOSENTINEL_SIMULATOR",
        location=Location(lat=lat, lon=lon),
        metadata=metadata,
    )


def get_simulated_ocean_events(limit: int = 3) -> List[NormalizedEvent]:
    """
    Returns clearly labeled simulated demo events.
    Never misrepresents simulated data as live Global Fishing Watch data.
    """
    sim_events = [
        detect_dark_vessel(
            gap_hours=18.5,
            lat=-0.4850,
            lon=-90.4920,
            vessel_id="demo_vsl_galapagos_trawler_01",
            vessel_type="FISHING",
            flag="CHN",
            distance_from_shore_nm=72.0,
            apparent_fishing=True,
            loitering=True,
            encounter=False,
            repeated_gaps=True,
            custom_id="demo_ocean_evt_galapagos_001",
            data_mode="simulated",
            source="ecosentinel_demo",
        ),
        detect_dark_vessel(
            gap_hours=31.2,
            lat=-0.5210,
            lon=-90.5110,
            vessel_id="demo_vsl_galapagos_carrier_02",
            vessel_type="CARRIER_REEFER",
            flag="PAN",
            distance_from_shore_nm=85.0,
            apparent_fishing=False,
            loitering=True,
            encounter=True,
            repeated_gaps=False,
            custom_id="demo_ocean_evt_galapagos_002",
            data_mode="simulated",
            source="ecosentinel_demo",
        ),
        detect_dark_vessel(
            gap_hours=14.0,
            lat=-5.2100,
            lon=71.8500,
            vessel_id="demo_vsl_chagos_longliner_03",
            vessel_type="FISHING",
            flag="TWN",
            distance_from_shore_nm=110.0,
            apparent_fishing=True,
            loitering=False,
            encounter=False,
            repeated_gaps=False,
            custom_id="demo_ocean_evt_chagos_003",
            data_mode="simulated",
            source="ecosentinel_demo",
        ),
    ]
    return sim_events[:limit]


def fetch_ocean_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    token: Optional[str] = None,
    limit: int = 10,
    mode: str = "auto",  # 'auto', 'live', or 'simulated'
) -> List[NormalizedEvent]:
    """
    Retrieves AIS gap and suspicious vessel events.

    Modes:
    - 'live': Strictly calls Global Fishing Watch API v3. Raises on error or missing token.
    - 'simulated': Directly returns clearly labeled simulated demo events.
    - 'auto': Attempts live API call if GFW_API_TOKEN is present; if absent or on error,
              safely falls back to clearly labeled simulated events (source='ecosentinel_demo').
    """
    if mode == "simulated":
        return get_simulated_ocean_events(limit=limit)

    api_token = token or os.environ.get("GFW_API_TOKEN")

    if not api_token:
        if mode == "live":
            raise ValueError("GFW_API_TOKEN environment variable not set. Live mode requires an API token.")
        return get_simulated_ocean_events(limit=limit)

    # Attempt live query to GFW v3 Events API
    try:
        headers = {"Authorization": f"Bearer {api_token}"}
        params: Dict[str, Any] = {
            "datasets": DATASET_GAPS,
            "limit": min(limit, 20),
        }
        if start_date:
            params["start-date"] = start_date
        if end_date:
            params["end-date"] = end_date

        response = httpx.get(
            f"{GFW_API_BASE}/events",
            headers=headers,
            params=params,
            timeout=8.0,
        )

        if response.status_code == 200:
            data = response.json()
            entries = data.get("entries", [])
            live_events: List[NormalizedEvent] = []

            for entry in entries:
                pos = entry.get("position", {})
                lat = float(pos.get("lat", 0.0))
                lon = float(pos.get("lon", 0.0))
                gap_info = entry.get("gap", {})
                gap_hours = float(gap_info.get("durationHours", 12.0))
                dist_shore = float(gap_info.get("distanceFromShoreKm", 50.0)) * 0.539957  # km to nm

                vessel_info = entry.get("vessel", {})
                vessel_id = vessel_info.get("id", f"gfw_vsl_{uuid.uuid4().hex[:6]}")
                vessel_type = vessel_info.get("type", "FISHING")
                flag = vessel_info.get("flag", "UNKNOWN")
                gfw_id = entry.get("id", uuid.uuid4().hex[:8])

                event = detect_dark_vessel(
                    gap_hours=gap_hours,
                    lat=lat,
                    lon=lon,
                    vessel_id=vessel_id,
                    vessel_type=vessel_type,
                    flag=flag,
                    distance_from_shore_nm=dist_shore,
                    apparent_fishing=True,
                    loitering=False,
                    encounter=False,
                    custom_id=f"gfw_evt_{gfw_id}",
                    timestamp=entry.get("start"),
                    data_mode="live",
                    source="global_fishing_watch",
                    gfw_event_id=gfw_id,
                )
                live_events.append(event)

            if live_events:
                return live_events

            # Empty results from live API
            if mode == "live":
                return []
            return get_simulated_ocean_events(limit=limit)

        else:
            if mode == "live":
                raise RuntimeError(
                    f"Global Fishing Watch API returned HTTP {response.status_code}: {response.text[:200]}"
                )
            # In auto mode, fall back to clearly labeled simulated data
            return get_simulated_ocean_events(limit=limit)

    except Exception as exc:
        if mode == "live":
            raise RuntimeError(f"Global Fishing Watch API request failed: {str(exc)}") from exc
        # In auto mode, fall back to clearly labeled simulated data
        return get_simulated_ocean_events(limit=limit)


def get_demo_ocean_event() -> NormalizedEvent:
    """
    Convenience helper returning the primary Galapagos demonstration event.
    If GFW_API_TOKEN is present, attempts to fetch live; otherwise returns simulated demo event.
    """
    events = fetch_ocean_events(limit=1, mode="auto")
    return events[0]


def post_to_person3(
    event: NormalizedEvent,
    backend_url: Optional[str] = None,
    timeout_sec: float = 5.0,
) -> Dict[str, Any]:
    """
    Dispatches a normalized ocean event to Person 3's shared reasoning pipeline.
    Reads backend URL from ECOSENTINEL_API_URL or defaults to http://localhost:8000/events.
    Handles connection errors, timeouts, and HTTP status codes cleanly.
    """
    target_url = backend_url or os.environ.get("ECOSENTINEL_API_URL", "http://localhost:8000/events")
    payload = event.model_dump(mode="json")

    try:
        response = httpx.post(target_url, json=payload, timeout=timeout_sec)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError as ce:
        raise ConnectionError(
            f"Unable to connect to Person 3 backend at {target_url}. Is FastAPI running?"
        ) from ce
    except httpx.TimeoutException as te:
        raise TimeoutError(
            f"Request to Person 3 backend at {target_url} timed out after {timeout_sec}s"
        ) from te
    except httpx.HTTPStatusError as hse:
        raise RuntimeError(
            f"Person 3 backend returned HTTP {hse.response.status_code}: {hse.response.text}"
        ) from hse
