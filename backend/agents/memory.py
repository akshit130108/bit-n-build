from typing import List
from database.firestore import db_client
from schemas.event import ClassificationResult, LocalizationResult, MemoryResult, NormalizedEvent


def retrieve_incident_memory(
    event: NormalizedEvent,
    classification: ClassificationResult,
    localization: LocalizationResult,
    search_radius_km: float = 15.0,
    time_window_hours: float = 48.0,
) -> MemoryResult:
    """
    Memory Agent: Queries historical incidents stored in Firestore/in-memory
    to discover spatial-temporal patterns, repeated violations, and hot-spots.
    """
    # Query database for recent incidents within proximity
    matched_incidents = db_client.query_nearby_incidents(
        lat=localization.lat,
        lon=localization.lon,
        max_distance_km=search_radius_km,
        hours_window=time_window_hours,
        domain=event.domain,
        event_type=event.event_type,
        exclude_id=event.id,
    )

    hist_count = len(matched_incidents)
    recurrence_detected = hist_count > 0
    reasons: List[str] = []

    if recurrence_detected:
        reasons.append(
            f"Detected {hist_count} previous incident(s) of '{event.event_type}' within {search_radius_km}km over the past {int(time_window_hours)}h"
        )
        if hist_count >= 3:
            reasons.append(
                f"Sustained pattern in {localization.sector_name}: Multiple recurring violations indicate organized activity"
            )
        else:
            reasons.append(
                f"Repeated disturbance noted near coordinates ({localization.lat:.4f}, {localization.lon:.4f})"
            )
    else:
        reasons.append(f"No prior incidents recorded in {localization.sector_name} within the last {int(time_window_hours)}h (isolated detection)")

    # Format simplified recent incident records for the frontend
    recent_summaries = []
    for inc in matched_incidents[:5]:
        ev = inc.get("event", {})
        recent_summaries.append({
            "id": ev.get("id"),
            "event_type": ev.get("event_type"),
            "timestamp": ev.get("timestamp"),
            "distance_km": inc.get("distance_km", 0.0),
            "risk_score": inc.get("risk", {}).get("score"),
        })

    return MemoryResult(
        historical_events=hist_count,
        recurrence_detected=recurrence_detected,
        recent_incidents=recent_summaries,
        reasons=reasons,
    )
