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
from datetime import datetime, timedelta, timezone
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


# Optional auto-load GFW_API_TOKEN from backend/.env into os.environ if present
if "GFW_API_TOKEN" not in os.environ:
    _env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(_env_path):
        try:
            with open(_env_path, "r", encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line.startswith("GFW_API_TOKEN="):
                        os.environ["GFW_API_TOKEN"] = _line.split("=", 1)[1].strip('\'"')
                        break
        except Exception:
            pass


def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    """Parse ISO 8601 string to UTC datetime object."""
    if not dt_str:
        return None
    try:
        s = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


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
    gap_hours: Optional[float] = None,
    vessel_type: str = "UNKNOWN",
    apparent_fishing: bool = False,
    loitering: bool = False,
    encounter: bool = False,
    protected_area: bool = False,
    distance_from_shore_nm: Optional[float] = None,
    repeated_gaps: bool = False,
    is_gap_event: bool = False,
) -> Tuple[float, List[str], List[str]]:
    """
    Calculate a transparent prototype suspicion score (0.0 - 1.0) and reasoning
    for potential dark vessel behavior.
    """
    reasons: List[str] = []
    supporting_evidence: List[str] = []

    # Base score depending on whether an explicit AIS gap duration exists or general marine event
    if gap_hours is not None:
        score = 0.50
        reasons.append(f"AIS gap detected ({gap_hours:.1f} hours duration)")
        supporting_evidence.append("AIS gap")
        if gap_hours >= 24.0:
            score += 0.10
            reasons.append("Prolonged AIS gap exceeds 24 hours")
            supporting_evidence.append("Extended gap duration (>24h)")
        elif gap_hours >= 12.0:
            score += 0.05
            reasons.append("Extended AIS gap exceeds 12 hours")
    elif is_gap_event:
        score = 0.35
        reasons.append("AIS gap event recorded (duration unquantified)")
        supporting_evidence.append("AIS gap")
    elif loitering or encounter:
        score = 0.30
        reasons.append("Suspicious vessel loitering or encounter pattern recorded")
    elif apparent_fishing:
        score = 0.35
        reasons.append("Fishing activity track recorded")
    else:
        score = 0.25
        reasons.append("Marine observation track recorded")

    # Vessel type evidence
    if "fishing" in vessel_type.lower():
        score += 0.10
        reasons.append("Commercial fishing vessel class")
        supporting_evidence.append("Fishing vessel classification")

    # Apparent fishing activity
    if apparent_fishing and "fishing" not in vessel_type.lower():
        score += 0.10
        reasons.append("Apparent fishing activity detected during surrounding track")
        supporting_evidence.append("Apparent fishing activity")
    elif apparent_fishing and "fishing" in vessel_type.lower():
        supporting_evidence.append("Apparent fishing activity")

    # Loitering / Encounter contextual corroboration
    if loitering or encounter:
        score += 0.05
        if loitering and encounter:
            reasons.append("Preceding loitering and transshipment encounter detected")
            supporting_evidence.append("Loitering")
            supporting_evidence.append("Encounter")
        elif loitering:
            reasons.append("Loitering behavior detected")
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
    elif distance_from_shore_nm is not None and distance_from_shore_nm >= 50.0:
        score += 0.03
        reasons.append(f"Offshore evasion: {distance_from_shore_nm:.0f} nm from coastal monitoring authority")

    final_confidence = round(max(0.0, min(1.0, score)), 2)
    return final_confidence, reasons, supporting_evidence


def detect_dark_vessel(
    gap_hours: Optional[float] = None,
    lat: float = -0.4850,
    lon: float = -90.4920,
    vessel_id: str = "demo_vsl_galapagos_trawler",
    vessel_type: str = "FISHING",
    flag: str = "CHN",
    distance_from_shore_nm: Optional[float] = 72.0,
    apparent_fishing: bool = False,
    loitering: bool = False,
    encounter: bool = False,
    repeated_gaps: bool = False,
    custom_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    data_mode: str = "simulated",
    source: Optional[str] = None,
    gfw_event_id: Optional[str] = None,
    dataset: Optional[str] = None,
    event_type: Optional[str] = None,
    is_gap_event: bool = False,
    requested_start_date: Optional[str] = None,
    requested_end_date: Optional[str] = None,
) -> NormalizedEvent:
    """
    Detects potential dark vessel / marine threat behavior from AIS gap and spatial-temporal evidence,
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
        is_gap_event=is_gap_event,
    )

    actual_data_mode = "live" if data_mode == "live" else "simulated"
    actual_source = source or ("global_fishing_watch" if actual_data_mode == "live" else "ecosentinel_demo")

    if actual_data_mode == "simulated":
        prefix = "demo_ocean_evt"
    else:
        prefix = "gfw_evt"

    event_id = custom_id or f"{prefix}_{uuid.uuid4().hex[:10]}"
    event_timestamp = timestamp or datetime.now(timezone.utc).isoformat()

    # Deterministic priority rule for event_type mapping based on actual evidence
    # Priority: AIS gap -> loitering -> encounter -> fishing -> suspicious_vessel
    if event_type:
        normalized_event_type = event_type
    elif is_gap_event or (gap_hours is not None and gap_hours > 0):
        normalized_event_type = "potential_dark_vessel"
    elif loitering:
        normalized_event_type = "suspicious_loitering_vessel"
    elif encounter:
        normalized_event_type = "suspicious_encounter_vessel"
    elif apparent_fishing:
        normalized_event_type = "possible_illegal_fishing"
    else:
        normalized_event_type = "suspicious_vessel"

    metadata: Dict[str, Any] = {
        "source": actual_source,
        "data_mode": actual_data_mode,
        "vessel_id": vessel_id,
        "vessel_type": vessel_type.upper(),
        "flag": flag.upper(),
        "protected_area": is_mpa,
        "protected_area_name": mpa_info["protected_area_name"],
        "distance_to_boundary_km": mpa_info["distance_to_boundary_km"],
        "boundary_source": mpa_info["boundary_source"],
        "loitering": loitering,
        "encounter": encounter,
        "apparent_fishing": apparent_fishing,
        "nearby_confirmations": 1 if (loitering or encounter) else 0,
        "ais_disabled": is_gap_event or (gap_hours is not None and gap_hours > 0),
        "supporting_evidence": supporting_evidence,
        "reasons": reasons,
    }

    if gap_hours is not None:
        metadata["ais_gap_hours"] = round(gap_hours, 1)

    if distance_from_shore_nm is not None:
        metadata["distance_from_shore_nm"] = round(distance_from_shore_nm, 1)

    if dataset:
        metadata["dataset"] = dataset

    if gfw_event_id:
        metadata["gfw_event_id"] = gfw_event_id

    if requested_start_date:
        metadata["requested_start_date"] = requested_start_date
    if requested_end_date:
        metadata["requested_end_date"] = requested_end_date

    if actual_data_mode == "simulated":
        metadata["note"] = (
            "Simulated demonstration event modeled on typical EEZ boundary fishing behavior. "
            "Set GFW_API_TOKEN to fetch live observations."
        )

    return NormalizedEvent(
        id=event_id,
        domain="ocean",
        event_type=normalized_event_type,
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
            is_gap_event=True,
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
            is_gap_event=True,
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
            is_gap_event=True,
        ),
    ]
    return sim_events[:limit]


ALL_EVENTS_DATASETS = [
    DATASET_GAPS,
    DATASET_LOITERING,
    DATASET_ENCOUNTERS,
    DATASET_FISHING,
]


def fetch_ocean_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    token: Optional[str] = None,
    limit: int = 10,
    mode: str = "auto",  # 'auto', 'live', or 'simulated'
    region: Optional[Any] = None,
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

    # Set default recent date window (past 30 days) for live queries if start_date/end_date are not passed
    req_start_dt = parse_iso_datetime(start_date) if start_date else None
    req_end_dt = parse_iso_datetime(end_date) if end_date else None

    now = datetime.now(timezone.utc)
    if req_end_dt is None:
        req_end_dt = now
        end_date = req_end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    if req_start_dt is None:
        req_start_dt = req_end_dt - timedelta(days=30)
        start_date = req_start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Attempt live query to GFW v3 Events API (HTTP POST with JSON payload)
    try:
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        json_body: Dict[str, Any] = {
            "datasets": ALL_EVENTS_DATASETS,
            "startDate": start_date,
            "endDate": end_date,
        }
        if region is not None:
            json_body["region"] = region

        query_params: Dict[str, Any] = {
            "limit": max(1, min(limit, 20)),
            "offset": 0,
            "sort": "-start",
        }

        response = httpx.post(
            f"{GFW_API_BASE}/events",
            headers=headers,
            params=query_params,
            json=json_body,
            timeout=18.0,
        )

        if response.status_code in (200, 201):
            data = response.json()
            if isinstance(data, dict):
                entries = data.get("entries") or data.get("data") or []
            elif isinstance(data, list):
                entries = data
            else:
                entries = []

            live_events: List[NormalizedEvent] = []

            for entry in entries:
                if not isinstance(entry, dict):
                    continue

                gfw_id = str(entry.get("id") or entry.get("eventId") or uuid.uuid4().hex[:8])

                start_ts = (
                    entry.get("start")
                    or entry.get("startTimestamp")
                    or entry.get("start_time")
                    or entry.get("timestamp")
                )

                if not start_ts:
                    continue

                # Validate timestamp against requested date window
                entry_dt = parse_iso_datetime(start_ts)
                if entry_dt is None or entry_dt < req_start_dt or entry_dt > req_end_dt:
                    # Stale or out-of-window event - filter out!
                    continue

                # Position parsing
                pos = entry.get("position") or entry.get("boundingCentroid") or entry.get("centroid") or {}
                lat_val = pos.get("lat") if isinstance(pos, dict) else None
                lon_val = pos.get("lon") if isinstance(pos, dict) else None

                if lat_val is None:
                    lat_val = entry.get("lat")
                if lon_val is None:
                    lon_val = entry.get("lon")

                if lat_val is None or lon_val is None:
                    continue

                try:
                    lat = float(lat_val)
                    lon = float(lon_val)
                except (ValueError, TypeError):
                    continue

                # Vessel parsing - no fake defaults
                vessel_info = entry.get("vessel") or entry.get("vesselInfo") or {}
                if isinstance(vessel_info, dict):
                    vessel_id = str(
                        vessel_info.get("id")
                        or vessel_info.get("ssvid")
                        or vessel_info.get("mmsi")
                        or entry.get("vesselId")
                        or entry.get("ssvid")
                        or f"gfw_vsl_{gfw_id}"
                    )
                    vessel_type = str(
                        vessel_info.get("type") or vessel_info.get("vesselType") or entry.get("vesselType") or "UNKNOWN"
                    )
                    flag = str(vessel_info.get("flag") or entry.get("flag") or "UNKNOWN")
                else:
                    vessel_id = f"gfw_vsl_{gfw_id}"
                    vessel_type = "UNKNOWN"
                    flag = "UNKNOWN"

                # Dataset and Event Type provenance
                dataset_name = str(entry.get("dataset") or entry.get("datasetId") or "").lower()
                raw_event_type = str(entry.get("type") or "").lower()

                # AIS Gap parsing (Do NOT default gap_hours!)
                gap_info = entry.get("gap") if isinstance(entry.get("gap"), dict) else {}
                gap_hours_raw = (
                    gap_info.get("durationHours")
                    or gap_info.get("gapHours")
                    or entry.get("durationHours")
                    or entry.get("gapHours")
                )
                if gap_hours_raw is not None:
                    try:
                        gap_hours = float(gap_hours_raw)
                    except (ValueError, TypeError):
                        gap_hours = None
                else:
                    gap_hours = None

                # Distance from shore parsing
                dist_shore_raw = (
                    gap_info.get("distanceFromShoreKm")
                    or (entry.get("loitering", {}).get("distanceFromShoreKm") if isinstance(entry.get("loitering"), dict) else None)
                    or entry.get("distanceFromShoreKm")
                )
                if dist_shore_raw is not None:
                    try:
                        dist_shore = float(dist_shore_raw) * 0.539957  # km to nm
                    except (ValueError, TypeError):
                        dist_shore = None
                else:
                    dist_shore = None

                # Evidence flags strictly from dataset / entry fields
                is_gap_event = ("gap" in dataset_name or "gap" in raw_event_type or isinstance(entry.get("gap"), dict))
                is_loitering_event = ("loitering" in dataset_name or "loitering" in raw_event_type or isinstance(entry.get("loitering"), dict) or bool(entry.get("loitering")))
                is_encounter_event = ("encounter" in dataset_name or "encounter" in raw_event_type or isinstance(entry.get("encounter"), dict) or bool(entry.get("encounter")))
                is_fishing_event = ("fishing" in dataset_name or "fishing" in raw_event_type or bool(entry.get("apparentFishing")) or isinstance(entry.get("fishing"), dict))

                event = detect_dark_vessel(
                    gap_hours=gap_hours,
                    lat=lat,
                    lon=lon,
                    vessel_id=vessel_id,
                    vessel_type=vessel_type,
                    flag=flag,
                    distance_from_shore_nm=dist_shore,
                    apparent_fishing=is_fishing_event,
                    loitering=is_loitering_event,
                    encounter=is_encounter_event,
                    custom_id=f"gfw_evt_{gfw_id}",
                    timestamp=start_ts,
                    data_mode="live",
                    source="global_fishing_watch",
                    gfw_event_id=gfw_id,
                    dataset=entry.get("dataset"),
                    is_gap_event=is_gap_event,
                    requested_start_date=start_date,
                    requested_end_date=end_date,
                )
                live_events.append(event)

            if live_events:
                return live_events[:limit]

            # Empty results after date-window validation
            if mode == "live":
                return []
            return get_simulated_ocean_events(limit=limit)

        else:
            if mode == "live":
                raise RuntimeError(
                    f"Global Fishing Watch API returned HTTP {response.status_code}: {response.text[:200]}"
                )
            return get_simulated_ocean_events(limit=limit)

    except Exception as exc:
        if mode == "live":
            raise RuntimeError(f"Global Fishing Watch API request failed: {str(exc)}") from exc
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


def ingest_ocean_events(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """
    Automated ingestion wrapper forwarding to ocean_ingest.ingest_ocean_events.
    """
    from adapters.ocean_ingest import ingest_ocean_events as _ingest
    return _ingest(*args, **kwargs)

