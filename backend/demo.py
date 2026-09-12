"""
EcoSentinel Reasoning Pipeline - Terminal Demo
Demonstrates the agentic reasoning lifecycle:
1. Historical recurrence detection in Terrestrial Logging scenario
2. Dynamic risk escalation driven by spatial-temporal memory
3. Human supervision gating (WAITING_FOR_APPROVAL -> APPROVED -> DISPATCHED)
4. Domain-agnostic transfer to Marine Vessel Intrusion scenario
"""

import json
import sys
from datetime import datetime, timezone

from adapters.fake_events import (
    generate_historical_events,
    generate_land_event,
    generate_ocean_event,
)
from database.firestore import db_client
from orchestrator.pipeline import approve_incident, process_event


def print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title.upper()}")
    print("=" * 70)


def print_substep(step: str, title: str) -> None:
    print(f"\n[{step}] {title}")
    print("-" * 50)


def print_kv(key: str, val: str, indent: int = 4) -> None:
    prefix = " " * indent
    print(f"{prefix}{key:<24}: {val}")


def print_json_preview(label: str, obj: dict, indent: int = 4) -> None:
    prefix = " " * indent
    print(f"{prefix}{label}:")
    lines = json.dumps(obj, indent=2).splitlines()
    for line in lines:
        print(f"{prefix}  {line}")


def main() -> None:
    print_header("EcoSentinel - Agentic Ecological Reasoning Pipeline")
    print(f"Active Storage Backend: {db_client.backend_type.upper()}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    # Clear store for fresh demo run
    db_client.clear()

    # =========================================================================
    # PART 1: TERRESTRIAL LOGGING & MEMORY RECURRENCE DEMO
    # =========================================================================
    print_header("Part 1: Land Logging Scenario (Memory Recurrence & Human Gate)")

    print_substep("Step 1", "Seeding 3 Historical Chainsaw Incidents in Sector-7")
    seed_events = generate_historical_events(
        domain="land",
        event_type="chainsaw",
        center_lat=12.9716,
        center_lon=77.5946,
        count=3,
        time_span_hours=8,
    )
    for i, s_ev in enumerate(seed_events, start=1):
        p_res = process_event(s_ev)
        print_kv(
            f"Historical Incident #{i}",
            f"ID={s_ev.id} | Sensor={s_ev.sensor_id} | Time={s_ev.timestamp[11:19]}Z | Lat={s_ev.location.lat:.4f}, Lon={s_ev.location.lon:.4f}",
        )

    print_substep("Step 2", "Ingesting 4th Chainsaw Detection (Normalized Event)")
    current_land_event = generate_land_event(
        custom_id="evt_chainsaw_hotspot",
        confidence=0.92,
        sensor_id="S07_ACOUSTIC_NODE",
        lat=12.9718,
        lon=77.5948,
        nearby_confirmations=2,
        protected_area=True,
    )
    print_kv("Event ID", current_land_event.id)
    print_kv("Domain", current_land_event.domain)
    print_kv("Raw Sensor Type", current_land_event.event_type)
    print_kv("Raw Confidence", f"{current_land_event.confidence:.2f}")
    print_kv("Coordinates", f"Lat={current_land_event.location.lat}, Lon={current_land_event.location.lon}")
    print_kv("Metadata", str(current_land_event.metadata))

    print_substep("Step 3", "Executing 9-Stage Reasoning Pipeline")
    result = process_event(current_land_event)

    # 1. Classification
    print("\n  >>> [AGENT 1: CLASSIFIER]")
    print_kv("Refined Threat", result.classification.refined_type)
    print_kv("Threat Category", result.classification.category)
    print_kv("Urgency", result.classification.urgency)
    print_kv("Reasoning", "; ".join(result.classification.reasons))

    # 2. Verification
    print("\n  >>> [AGENT 2: VERIFIER]")
    print_kv("Verification Level", result.verification.level.upper())
    print_kv("Trust Score", f"{result.verification.score:.2f}")
    print_kv("Evidence", "; ".join(result.verification.reasons))

    # 3. Localization
    print("\n  >>> [AGENT 3: LOCALIZER]")
    print_kv("Target Sector", result.localization.sector_name)
    print_kv("Precision Radius", f"+/-{result.localization.radius_meters:.0f} meters")
    print_kv("Spatial Evidence", "; ".join(result.localization.reasons))

    # 4. Memory Retrieval
    print("\n  >>> [AGENT 4: SPATIAL-TEMPORAL MEMORY]")
    print_kv("Historical Incidents", str(result.memory.historical_events))
    print_kv("Recurrence Detected", str(result.memory.recurrence_detected))
    for r in result.memory.reasons:
        print_kv("Memory Note", r)

    # 5. Risk Assessment
    print("\n  >>> [AGENT 5: MULTI-FACTOR RISK]")
    print_kv("Calculated Risk Score", f"{result.risk.score} / 100")
    print_kv("Risk Level", result.risk.level)
    print_kv("Factor Breakdown", str(result.risk.factors))
    print_kv("Risk Justifications", "; ".join(result.risk.reasons))

    # 6. Human Gate
    print("\n  >>> [AGENT 6: HUMAN SUPERVISION GATE]")
    print_kv("Requires Human Review", str(result.human_gate.requires_human))
    print_kv("Gate Status", result.human_gate.status)
    print_kv("Gate Policy", "; ".join(result.human_gate.reasons))

    # 7. Action Agent
    print("\n  >>> [AGENT 7: ACTION AGENT]")
    print_kv("Recommended Action", result.action.action)
    print_kv("Action Message", result.action.message)
    print_kv("Requires Approval", str(result.action.requires_approval))
    print_kv("Dispatched Immediately", str(result.action.dispatched))
    print_kv("Action Context", "; ".join(result.action.reasons))

    # Step 4: Human Approval
    print_substep("Step 4", "Simulating Human Ranger Supervisor Approval")
    print("  Triggering: POST /events/evt_chainsaw_hotspot/approve")
    approved_incident = approve_incident(
        event_id="evt_chainsaw_hotspot",
        reviewer="chief_ranger_patel",
        notes="Ground patrol unit Charlie mobilized with GPS coordinates. Intercept authorized.",
    )
    print_kv("Updated Gate Status", approved_incident.human_gate.status)
    print_kv("Action Dispatched?", str(approved_incident.action.dispatched))
    print_kv("Supervisor Note", approved_incident.human_gate.reasons[-1])
    print_kv("Dispatch Record", approved_incident.action.reasons[-1])

    # =========================================================================
    # PART 2: OCEAN DOMAIN TRANSFER DEMO
    # =========================================================================
    print_header("Part 2: Ocean Domain Transfer (Suspicious Vessel Detection)")
    print("Demonstrating that the EXACT same pipeline processes marine threats:")

    ocean_event = generate_ocean_event(
        custom_id="evt_vessel_marine_sanctuary",
        confidence=0.88,
        sensor_id="GALAPAGOS_AIS_STATION_3",
        lat=-0.5000,
        lon=-90.5000,
        nearby_confirmations=1,
        protected_area=True,
    )
    print_kv("Raw Domain", ocean_event.domain)
    print_kv("Raw Event Type", ocean_event.event_type)
    print_kv("Raw Coordinates", f"Lat={ocean_event.location.lat}, Lon={ocean_event.location.lon}")

    ocean_result = process_event(ocean_event)

    print("\n  >>> [REASONING RESULTS FOR OCEAN EVENT]")
    print_kv("Refined Classification", ocean_result.classification.refined_type)
    print_kv("Verification Level", f"{ocean_result.verification.level} (Score {ocean_result.verification.score})")
    print_kv("Historical Incidents", str(ocean_result.memory.historical_events))
    print_kv("Assessed Risk Score", f"{ocean_result.risk.score} / 100 ({ocean_result.risk.level})")
    print_kv("Human Gate Status", ocean_result.human_gate.status)
    print_kv("Recommended Action", ocean_result.action.action)
    print_kv("Action Message", ocean_result.action.message)

    print_header("Demo Completed Successfully")
    print("All agents responded with transparent evidence and structured reasoning.")


if __name__ == "__main__":
    main()
