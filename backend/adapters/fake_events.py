import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from schemas.event import Location, NormalizedEvent


def generate_land_event(
    event_type: str = "chainsaw",
    confidence: float = 0.91,
    sensor_id: str = "S07",
    lat: float = 12.9716,
    lon: float = 77.5946,
    nearby_confirmations: int = 2,
    protected_area: bool = True,
    is_night: bool = False,
    custom_id: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> NormalizedEvent:
    """Generate a simulated land event (e.g. chainsaw or logging acoustic detection)."""
    meta: Dict[str, Any] = {
        "nearby_confirmations": nearby_confirmations,
        "protected_area": protected_area,
        "is_night": is_night,
        "ecological_sensitivity": "critical" if protected_area else "moderate",
        "audio_frequency_hz": 2450,
        "snr_db": 18.5,
    }
    if extra_metadata:
        meta.update(extra_metadata)

    return NormalizedEvent(
        id=custom_id or f"evt_land_{uuid.uuid4().hex[:8]}",
        domain="land",
        event_type=event_type,
        confidence=confidence,
        timestamp=datetime.now(timezone.utc).isoformat(),
        sensor_id=sensor_id,
        location=Location(lat=lat, lon=lon),
        metadata=meta,
    )


def generate_ocean_event(
    event_type: str = "suspicious_vessel",
    confidence: float = 0.88,
    sensor_id: str = "AIS_BUOY_04",
    lat: float = -0.5000,
    lon: float = -90.5000,
    nearby_confirmations: int = 1,
    protected_area: bool = True,
    custom_id: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> NormalizedEvent:
    """Generate a simulated ocean event (e.g. dark vessel / illegal fishing in marine sanctuary)."""
    meta: Dict[str, Any] = {
        "nearby_confirmations": nearby_confirmations,
        "protected_area": protected_area,
        "is_night": True,
        "ecological_sensitivity": "critical" if protected_area else "moderate",
        "ais_disabled": True,
        "speed_knots": 3.4,
        "radar_signature": "trawler",
    }
    if extra_metadata:
        meta.update(extra_metadata)

    return NormalizedEvent(
        id=custom_id or f"evt_ocean_{uuid.uuid4().hex[:8]}",
        domain="ocean",
        event_type=event_type,
        confidence=confidence,
        timestamp=datetime.now(timezone.utc).isoformat(),
        sensor_id=sensor_id,
        location=Location(lat=lat, lon=lon),
        metadata=meta,
    )


def generate_poaching_event(
    confidence: float = 0.94,
    sensor_id: str = "ACOUSTIC_NODE_12",
    lat: float = 12.9725,
    lon: float = 77.5955,
    nearby_confirmations: int = 1,
    protected_area: bool = True,
    custom_id: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> NormalizedEvent:
    """Generate a simulated poaching event (e.g. gunshot acoustic detection in national park)."""
    meta: Dict[str, Any] = {
        "nearby_confirmations": nearby_confirmations,
        "protected_area": protected_area,
        "is_night": True,
        "ecological_sensitivity": "critical",
        "estimated_caliber": "high_power_rifle",
        "snr_db": 22.1,
    }
    if extra_metadata:
        meta.update(extra_metadata)

    return NormalizedEvent(
        id=custom_id or f"evt_poach_{uuid.uuid4().hex[:8]}",
        domain="land",
        event_type="gunshot",
        confidence=confidence,
        timestamp=datetime.now(timezone.utc).isoformat(),
        sensor_id=sensor_id,
        location=Location(lat=lat, lon=lon),
        metadata=meta,
    )


def generate_historical_events(
    domain: str = "land",
    event_type: str = "chainsaw",
    center_lat: float = 12.9716,
    center_lon: float = 77.5946,
    count: int = 3,
    time_span_hours: int = 12,
) -> List[NormalizedEvent]:
    """
    Generate multiple historical events clustered around a central location
    to test spatial-temporal memory retrieval and recurrence risk escalation.
    """
    now = datetime.now(timezone.utc)
    historical_events: List[NormalizedEvent] = []

    for i in range(count):
        # Calculate stepped timestamp in the past
        hours_ago = (time_span_hours / max(count, 1)) * (count - i)
        ts = (now - timedelta(hours=hours_ago)).isoformat()
        
        # Small realistic coordinate jitter (~50-200 meters)
        jitter_lat = center_lat + random.uniform(-0.0015, 0.0015)
        jitter_lon = center_lon + random.uniform(-0.0015, 0.0015)

        event = NormalizedEvent(
            id=f"hist_{domain[:4]}_{i+1}_{uuid.uuid4().hex[:6]}",
            domain=domain,
            event_type=event_type,
            confidence=round(random.uniform(0.82, 0.95), 2),
            timestamp=ts,
            sensor_id=f"S0{i+1}",
            location=Location(lat=round(jitter_lat, 5), lon=round(jitter_lon, 5)),
            metadata={
                "nearby_confirmations": 1,
                "protected_area": True,
                "historical_seed": True,
                "cluster_sector": "Sector-7",
            },
        )
        historical_events.append(event)

    return historical_events
