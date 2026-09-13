import os
import sys
import json
from datetime import datetime, timezone, timedelta

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from adapters.ocean_gfw import fetch_ocean_events, detect_dark_vessel
from adapters.ocean_ingest import ingest_ocean_events, OceanIngestionEngine
from adapters.ocean_scheduler import ocean_scheduler
from database.firestore import db_client, InMemoryStore
from main import app
from fastapi.testclient import TestClient

def run_acceptance_verification():
    print("==================================================")
    print("     ECOSENTINEL FINAL ACCEPTANCE VERIFICATION    ")
    print("==================================================")
    
    token = os.environ.get("GFW_API_TOKEN")
    print(f"\n[1] Security & Secret Check:")
    print(f"  - GFW_API_TOKEN present in environment: {bool(token)}")
    if token:
        # Guarantee token value is NEVER printed
        print(f"  - Token value is masked and safely loaded from backend/.env")

    client = TestClient(app)

    # 2. Backend Endpoint Check
    print("\n[2] Backend API Endpoint Verification:")
    res_root = client.get("/")
    assert res_root.status_code == 200, f"Root returned {res_root.status_code}"
    print("  - GET / status: 200 OK")

    res_status = client.get("/ingest/ocean/status")
    assert res_status.status_code == 200, f"Status returned {res_status.status_code}"
    status_data = res_status.json()
    print("  - GET /ingest/ocean/status: 200 OK")
    print(f"    • Scheduler running: {status_data.get('running')}")
    print(f"    • Poll interval: {status_data.get('poll_interval_seconds')}s")
    print(f"    • Mode: '{status_data.get('mode')}'")
    # Verify no secret fields in status
    for k in status_data.keys():
        assert "token" not in k.lower() and "key" not in k.lower() and "auth" not in k.lower(), f"Secret key leaked in status: {k}"

    # 3. Real GFW Live Data Fetch Test
    print("\n[3] Real GFW Live Data Fetch Test (mode='live'):")
    live_events = fetch_ocean_events(mode="live", limit=3)
    print(f"  - Retrieved live GFW events count: {len(live_events)}")
    
    now_utc = datetime.now(timezone.utc)
    date_window_start = now_utc - timedelta(days=30)
    newest_verified_ts = None

    if live_events:
        evt = live_events[0]
        meta = evt.metadata
        print(f"  - Event ID: {evt.id}")
        print(f"  - Provenance source: '{meta.get('source')}' (expected: 'global_fishing_watch')")
        print(f"  - Provenance data_mode: '{meta.get('data_mode')}' (expected: 'live')")
        print(f"  - Sensor ID: '{evt.sensor_id}' (expected: 'GFW_AIS')")
        print(f"  - GFW Event ID preserved: '{meta.get('gfw_event_id')}'")

        dt = datetime.fromisoformat(evt.timestamp.replace("Z", "+00:00"))
        newest_verified_ts = evt.timestamp
        is_valid_ts = date_window_start <= dt <= now_utc
        print(f"  - Timestamp: {evt.timestamp} (Inside 30-day UTC window: {is_valid_ts})")

        assert meta.get('source') == "global_fishing_watch", "Invalid live source"
        assert meta.get('data_mode') == "live", "Invalid live data_mode"
        assert evt.sensor_id == "GFW_AIS", "Invalid live sensor_id"
        assert is_valid_ts, f"Timestamp {evt.timestamp} outside 30-day window"

    # 4. Full Ingestion & Deduplication Test
    print("\n[4] Ingestion Engine & Deduplication Test:")
    db_client.clear()
    engine = OceanIngestionEngine(store=db_client)

    # First Ingestion Run
    run1 = engine.ingest_events(mode="live", limit=3)
    print("  - First Ingestion Run:")
    print(f"    • fetched_count: {run1['fetched_count']}")
    print(f"    • newly_processed_count: {run1['newly_processed_count']}")
    print(f"    • duplicate_count: {run1['duplicate_count']}")
    print(f"    • failed_count: {run1['failed_count']}")

    assert run1['newly_processed_count'] > 0, "Expected newly_processed_count > 0 on first run"

    # Second Ingestion Run (Same events -> Deduplication expected)
    run2 = engine.ingest_events(mode="live", limit=3)
    print("  - Second Ingestion Run (Deduplication Check):")
    print(f"    • fetched_count: {run2['fetched_count']}")
    print(f"    • newly_processed_count: {run2['newly_processed_count']}")
    print(f"    • duplicate_count: {run2['duplicate_count']}")
    print(f"    • failed_count: {run2['failed_count']}")

    assert run2['newly_processed_count'] == 0, "Expected newly_processed_count == 0 on second run"
    assert run2['duplicate_count'] == run1['fetched_count'], "Expected duplicate_count == fetched_count on second run"
    print("  [OK] Deduplication verified successfully!")

    # 5. Person 3 Pipeline Output Verification
    print("\n[5] Person 3 Pipeline Output Verification:")
    incidents = db_client.list_incidents(limit=10)
    assert len(incidents) > 0, "No incidents stored in db_client"
    sample = incidents[0]
    
    stages = ["classification", "verification", "localization", "memory", "risk", "human_gate", "action"]
    for s in stages:
        assert s in sample, f"Missing stage '{s}' in PipelineResult"
        print(f"  - Stage '{s}': Present [OK]")

    print(f"  - Refined Threat: {sample['classification']['refined_type']}")
    print(f"  - Risk Score: {sample['risk']['score']}/100 ({sample['risk']['level']})")
    print(f"  - Human Gate Status: {sample['human_gate']['status']}")

    # 6. Human Gate Governance Verification
    print("\n[6] Human Gate Governance Acceptance Test:")
    
    # Create legitimate High-Risk simulated event yielding risk score >= 80 (HIGH risk)
    from adapters.fake_events import generate_poaching_event
    high_risk_evt = generate_poaching_event(
        confidence=0.95,
        lat=-0.4850,
        lon=-90.4920,
        protected_area=True,
        custom_id="demo_poaching_high_risk_test",
    )
    res_high = client.post("/events", json=high_risk_evt.model_dump(mode="json"))
    assert res_high.status_code == 201
    high_data = res_high.json()
    high_id = high_data["event"]["id"]
    
    print(f"  - High-Risk Event [{high_id}]:")
    print(f"    • Risk score: {high_data['risk']['score']}/100 ({high_data['risk']['level']})")
    print(f"    • Human Gate Status: {high_data['human_gate']['status']}")
    print(f"    • Action Dispatched: {high_data['action']['dispatched']}")
    
    assert high_data['human_gate']['status'] == "WAITING_FOR_APPROVAL", "High-risk event must require human approval"
    assert not high_data['action']['dispatched'], "High-risk action must not be dispatched automatically"

    # Test Approval
    res_appr = client.post(f"/events/{high_id}/approve", json={"reviewer": "ranger_sup", "notes": "Approved test"})
    assert res_appr.status_code == 200
    appr_data = res_appr.json()
    print(f"  - After Approval:")
    print(f"    • Human Gate Status: {appr_data['human_gate']['status']}")
    print(f"    • Action Dispatched: {appr_data['action']['dispatched']}")
    assert appr_data['human_gate']['status'] == "APPROVED"
    assert appr_data['action']['dispatched']

    # Test Rejection on another high-risk event
    high_risk_evt2 = generate_poaching_event(
        confidence=0.96,
        lat=-0.4850,
        lon=-90.4920,
        protected_area=True,
        custom_id="demo_poaching_reject_test",
    )
    res_high2 = client.post("/events", json=high_risk_evt2.model_dump(mode="json"))
    high_id2 = res_high2.json()["event"]["id"]

    res_rej = client.post(f"/events/{high_id2}/reject", json={"reviewer": "ranger_sup", "notes": "Rejected test"})
    assert res_rej.status_code == 200
    rej_data = res_rej.json()
    print(f"  - After Rejection:")
    print(f"    • Human Gate Status: {rej_data['human_gate']['status']}")
    print(f"    • Action Dispatched: {rej_data['action']['dispatched']}")
    assert rej_data['human_gate']['status'] == "REJECTED"
    assert not rej_data['action']['dispatched']

    # Test Low-Risk Event
    low_risk_evt = detect_dark_vessel(
        data_mode="simulated",
        is_gap_event=False,
        gap_hours=None,
        apparent_fishing=False,
        loitering=False,
        encounter=False,
        lat=10.0,
        lon=10.0,
        vessel_id="demo_vsl_low_risk",
    )
    res_low = client.post("/events", json=low_risk_evt.model_dump(mode="json"))
    low_data = res_low.json()
    print(f"  - Low-Risk Event:")
    print(f"    • Risk score: {low_data['risk']['score']}/100 ({low_data['risk']['level']})")
    print(f"    • Human Gate Status: {low_data['human_gate']['status']}")
    print(f"    • Action: {low_data['action']['action']}")
    assert low_data['human_gate']['status'] == "AUTO_APPROVED"
    assert low_data['action']['action'] == "CONTINUE_MONITORING"
    print("  [OK] Human Gate Governance verified successfully!")

    # 7. Persistence Check
    print("\n[7] Persistence Check:")
    res_events = client.get("/events")
    assert res_events.status_code == 200
    all_events = res_events.json()
    print(f"  - Total persisted incidents accessible via GET /events: {len(all_events)}")
    res_single = client.get(f"/events/{high_id}")
    assert res_single.status_code == 200
    assert res_single.json()["human_gate"]["status"] == "APPROVED"
    print("  [OK] Incident retrieval & state persistence verified successfully!")

    print("\n==================================================")
    print("   ALL ACCEPTANCE VERIFICATION CHECKS PASSED      ")
    print("==================================================")
    return newest_verified_ts

if __name__ == "__main__":
    ts = run_acceptance_verification()
    print(f"NEWEST_VERIFIED_TIMESTAMP={ts}")
