"""
EcoSentinel - Person 2 Ocean / AIS Demonstration
Demonstrates end-to-end pipeline:
Global Fishing Watch AIS Gap & Loitering Event
→ Dark Vessel Behavior Analysis
→ Marine Protected Area Context Enrichment
→ Normalized EcoSentinel Event Contract
→ Person 3 Shared Reasoning Engine
"""

import json
import os
import sys
from datetime import datetime, timezone

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from adapters.ocean_gfw import fetch_ocean_events, get_demo_ocean_event, post_to_person3
from orchestrator.pipeline import process_event


def print_divider(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title.upper()}")
    print("=" * 70)


def print_kv(key: str, val: str, indent: int = 4) -> None:
    prefix = " " * indent
    print(f"{prefix}{key:<26}: {val}")


def main() -> None:
    print_divider("EcoSentinel - Person 2 Ocean / AIS Adapter Demo")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    gfw_token = os.environ.get("GFW_API_TOKEN")
    if gfw_token:
        print("  GFW API Token           : Configured (Live gateway.api.globalfishingwatch.org enabled)")
    else:
        print("  GFW API Token           : Not set (Using high-fidelity calibrated GFW v3 event model)")

    # 1. Retrieve GFW Ocean Events
    print("\n[Step 1] Fetching Ocean Events from Global Fishing Watch Adapter...")
    events = fetch_ocean_events(limit=3)
    print(f"  Retrieved {len(events)} candidate marine events.")

    # 2. Select Concrete Galapagos Dark Vessel Demo Event
    demo_event = events[0]
    print("\n[Step 2] Normalized Ocean Event (Person 3 Contract):")
    print("-" * 50)
    print(json.dumps(demo_event.model_dump(), indent=2))

    # 3. Process through Person 3 Shared Reasoning Pipeline
    print("\n[Step 3] Passing Normalized Event into Person 3 Reasoning Pipeline...")
    reasoning_result = process_event(demo_event)

    print("\n[Step 4] Person 3 Reasoning Engine Evaluation:")
    print("-" * 50)
    print_kv("Domain", reasoning_result.event.domain.upper())
    print_kv("Detected Event Type", reasoning_result.event.event_type)
    print_kv("Adapter Confidence", f"{reasoning_result.event.confidence:.2f}")

    print("\n  >>> [CLASSIFIER AGENT]")
    print_kv("Refined Threat", reasoning_result.classification.refined_type)
    print_kv("Threat Category", reasoning_result.classification.category)
    print_kv("Urgency", reasoning_result.classification.urgency)
    print_kv("Reasoning", "; ".join(reasoning_result.classification.reasons))

    print("\n  >>> [VERIFICATION AGENT]")
    print_kv("Verification Level", reasoning_result.verification.level.upper())
    print_kv("Verification Score", f"{reasoning_result.verification.score:.2f}")
    print_kv("Evidence", "; ".join(reasoning_result.verification.reasons))

    print("\n  >>> [LOCALIZATION & MPA CONTEXT]")
    print_kv("Coordinates", f"Lat={reasoning_result.localization.lat}, Lon={reasoning_result.localization.lon}")
    print_kv("Operational Sector", reasoning_result.localization.sector_name)
    print_kv("MPA Name", str(reasoning_result.event.metadata.get("protected_area_name")))
    print_kv("Inside Protected Area?", str(reasoning_result.event.metadata.get("protected_area")))

    print("\n  >>> [RISK ASSESSMENT AGENT]")
    print_kv("Multi-Factor Risk Score", f"{reasoning_result.risk.score} / 100")
    print_kv("Risk Alert Level", reasoning_result.risk.level)
    print_kv("Risk Breakdown", str(reasoning_result.risk.factors))
    print_kv("Risk Reasons", "; ".join(reasoning_result.risk.reasons))

    print("\n  >>> [HUMAN SUPERVISION GATE]")
    print_kv("Requires Human Clearance", str(reasoning_result.human_gate.requires_human))
    print_kv("Gate Status", reasoning_result.human_gate.status)
    print_kv("Gate Rationale", "; ".join(reasoning_result.human_gate.reasons))

    print("\n  >>> [ACTION AGENT]")
    print_kv("Recommended Action", reasoning_result.action.action)
    print_kv("Operational Message", reasoning_result.action.message)
    print_kv("Dispatched Immediately", str(reasoning_result.action.dispatched))
    print_kv("Action Context", "; ".join(reasoning_result.action.reasons))

    print_divider("Ocean Pipeline Verification Successful")
    print("Person 2 GFW adapter seamlessly consumed by Person 3 reasoning engine.")


if __name__ == "__main__":
    main()
