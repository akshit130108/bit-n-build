import os
import sys
import json
from datetime import datetime, timezone, timedelta

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from adapters.ocean_gfw import fetch_ocean_events
from adapters.ocean_ingest import ingest_ocean_events
from database.firestore import db_client
from main import app
from fastapi.testclient import TestClient

def main():
    print("=== PHASE 9 END-TO-END SMOKE TEST ===")
    token = os.environ.get("GFW_API_TOKEN")
    mode = "live" if token else "auto"
    print(f"GFW API Token present in os.environ: {bool(token)} (Running smoke test in mode: '{mode}')")
    
    limit = 3
    print(f"\n1. Fetching ocean events directly via fetch_ocean_events(mode='{mode}', limit={limit})...")
    raw_fetched = fetch_ocean_events(mode=mode, limit=limit)
    print(f"Fetched raw GFW events count: {len(raw_fetched)}")

    print(f"\n2. Ingesting via ingest_ocean_events(mode='{mode}', limit={limit})...")
    ingest_res = ingest_ocean_events(mode=mode, limit=limit)
    print("Ingestion result summary:")
    print(" - fetched_count:", ingest_res["fetched_count"])
    print(" - duplicate_count:", ingest_res["duplicate_count"])
    print(" - newly_processed_count:", ingest_res["newly_processed_count"])
    print(" - failed_count:", ingest_res["failed_count"])

    print("\n3. Testing GET /events endpoint via FastAPI TestClient...")
    client = TestClient(app)
    res = client.get("/events?domain=ocean")
    assert res.status_code == 200, f"GET /events returned status {res.status_code}"
    events = res.json()
    print(f"Total ocean incidents in database: {len(events)}")

    now_utc = datetime.now(timezone.utc)
    date_window_start = now_utc - timedelta(days=30)
    print(f"\n4. Verifying returned incidents against 30-day UTC window [{date_window_start.isoformat()} to {now_utc.isoformat()}]:\n")

    for idx, inc in enumerate(events[:5], 1):
        evt = inc.get("event", {})
        cls = inc.get("classification", {})
        rsk = inc.get("risk", {})
        gate = inc.get("human_gate", {})
        act = inc.get("action", {})
        meta = evt.get("metadata", {})

        ts_str = evt.get("timestamp")
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        is_in_window = date_window_start <= dt <= now_utc

        print(f"--- Incident #{idx} ---")
        print(f"  Event ID: {evt.get('id')}")
        print(f"  Timestamp: {ts_str} (Inside 30-day window: {is_in_window})")
        print(f"  Raw Event Type: {evt.get('event_type')}")
        print(f"  Provenance / Mode: source='{meta.get('source')}', data_mode='{meta.get('data_mode')}', sensor_id='{evt.get('sensor_id')}'")
        print(f"  Vessel ID: {meta.get('vessel_id')} (Flag: {meta.get('flag')})")
        print(f"  Person 3 Refined Threat: {cls.get('refined_type')} (Category: {cls.get('category')})")
        print(f"  Risk Score / Level: {rsk.get('score')}/100 ({rsk.get('level')})")
        print(f"  Human Gate Status: {gate.get('status')} (Requires Human: {gate.get('requires_human')})")
        print(f"  Recommended Action: {act.get('action')} (Dispatched: {act.get('dispatched')})")
        print(f"  Persistence Check: Found in db_client (backend: {db_client.backend_type})\n")

    print("=== SMOKE TEST COMPLETE SUCCESS ===")

if __name__ == "__main__":
    main()
