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
    print("\n" + "=" * 60)
    print(f"  {title.upper()}")
    print("=" * 60)


def print_kv(key: str, val: str, indent: int = 2) -> None:
    prefix = " " * indent
    print(f"{prefix}{key:<24}: {val}")


def main() -> None:
    print_divider("EcoSentinel Ocean Demo")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    # 1. Check GFW Token & Mode
    gfw_token = os.environ.get("GFW_API_TOKEN")
    if gfw_token:
        print_kv("Data source", "Global Fishing Watch")
        print_kv("Mode", "LIVE")
    else:
        print_kv("Data source", "EcoSentinel demo")
        print_kv("Mode", "SIMULATED")
        print("  (Note: Set GFW_API_TOKEN to enable live Global Fishing Watch API calls)")

    # 2. Fetch Ocean Events
    events = fetch_ocean_events(limit=3, mode="auto")
    demo_event = events[0]
    meta = demo_event.metadata or {}

    print_divider("Observed Vessel Event Summary")
    print_kv("Data source", meta.get("source", "unknown"))
    print_kv("Mode", meta.get("data_mode", "unknown").upper())
    print_kv("Vessel ID", meta.get("vessel_id", "unknown"))
    print_kv("Vessel Class", meta.get("vessel_type", "unknown"))
    print_kv("Flag State", meta.get("flag", "unknown"))
    print_kv("Event", "AIS GAP (potential_dark_vessel)")
    print_kv("AIS gap", f"{meta.get('ais_gap_hours', 0.0)} hours")
    print_kv("Loitering", "YES" if meta.get("loitering") else "NO")
    print_kv("Encounter", "YES" if meta.get("encounter") else "NO")
    print_kv("Apparent Fishing", "YES" if meta.get("apparent_fishing") else "NO")
    print_kv("Protected area", "YES" if meta.get("protected_area") else "NO")
    print_kv("MPA Name", str(meta.get("protected_area_name", "N/A")))
    print_kv("Boundary Context", str(meta.get("boundary_source", "N/A")))
    print_kv("Suspicion score", f"{demo_event.confidence:.2f} (Prototype score, not confirmed IUU)")

    print("\nReasons:")
    for reason in meta.get("reasons", []):
        print(f"  - {reason}")

    print_divider("Creating Normalized Event (Person 3 Contract)")
    print_kv("id", demo_event.id)
    print_kv("domain", demo_event.domain)
    print_kv("event_type", demo_event.event_type)
    print_kv("confidence", str(demo_event.confidence))
    print_kv("sensor_id", demo_event.sensor_id)
    print_kv("location", f"lat={demo_event.location.lat}, lon={demo_event.location.lon}")

    # 3. Process through Person 3 Shared Reasoning Pipeline
    print_divider("Sending to Person 3 Reasoning Pipeline...")
    reasoning_result = process_event(demo_event)

    print_kv("Classification", reasoning_result.classification.refined_type)
    print_kv("Threat Category", reasoning_result.classification.category)
    print_kv("Verification Level", f"{reasoning_result.verification.level.upper()} (score: {reasoning_result.verification.score:.2f})")
    print_kv("Risk Score", f"{reasoning_result.risk.score} / 100")
    print_kv("Risk Level", reasoning_result.risk.level)
    print_kv("Human Gate", reasoning_result.human_gate.status)
    print_kv("Human Approval?", "REQUIRED" if reasoning_result.human_gate.requires_human else "NOT REQUIRED")
    print_kv("Recommended Action", reasoning_result.action.action)
    print_kv("Operational Message", reasoning_result.action.message)

    # 4. Optional Live HTTP POST check
    api_url = os.environ.get("ECOSENTINEL_API_URL", "http://localhost:8000/events")
    try:
        http_res = post_to_person3(demo_event, backend_url=api_url, timeout_sec=1.5)
        print(f"\nLive HTTP POST {api_url} -> 200 OK (Status: {http_res.get('human_gate', {}).get('status')})")
    except Exception:
        print(f"\nLive HTTP endpoint ({api_url}) not reachable (Standalone pipeline verified).")

    print_divider("Demo Completed Successfully")


if __name__ == "__main__":
    main()
