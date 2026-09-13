import os
import sys
import unittest
import asyncio
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from adapters.ocean_scheduler import OceanScheduler, ocean_scheduler
from adapters.ocean_gfw import detect_dark_vessel
from adapters.ocean_ingest import OceanIngestionEngine
from database.firestore import db_client
from schemas.event import NormalizedEvent, PipelineResult


class TestOceanSchedulerAndAPI(unittest.TestCase):

    def setUp(self) -> None:
        self.client = TestClient(app)
        db_client.clear()
        # Reset scheduler state
        ocean_scheduler.stop()
        ocean_scheduler._running = False
        ocean_scheduler._last_run_at = None
        ocean_scheduler._last_success_at = None
        ocean_scheduler._last_fetched_count = 0
        ocean_scheduler._last_processed_count = 0
        ocean_scheduler._last_duplicate_count = 0
        ocean_scheduler._last_failed_count = 0
        ocean_scheduler._last_error = None

    def tearDown(self) -> None:
        ocean_scheduler.stop()
        db_client.clear()

    def test_01_scheduler_start_and_no_duplicate_workers(self) -> None:
        scheduler = OceanScheduler()
        self.assertFalse(scheduler.is_running)
        
        # Test start behavior
        scheduler.start()
        self.assertTrue(scheduler.is_running)
        task1 = scheduler._task

        # Call start again, should not create a second task
        scheduler.start()
        self.assertTrue(scheduler.is_running)
        self.assertIs(scheduler._task, task1)
        
        scheduler.stop()
        self.assertFalse(scheduler.is_running)

    def test_02_poll_interval_configurable(self) -> None:
        with patch.dict(os.environ, {"OCEAN_POLL_INTERVAL_SECONDS": "45"}):
            scheduler = OceanScheduler()
            self.assertEqual(scheduler._poll_interval, 45)

        scheduler_default = OceanScheduler()
        self.assertEqual(scheduler_default._poll_interval, 300)

    def test_03_successful_ingestion_updates_status(self) -> None:
        mock_result = {
            "fetched_count": 5,
            "duplicate_count": 2,
            "newly_processed_count": 3,
            "failed_count": 0,
            "processed_results": []
        }
        with patch("adapters.ocean_scheduler.ingest_ocean_events", return_value=mock_result):
            asyncio.run(ocean_scheduler.poll_once())
            
            status = ocean_scheduler.get_status()
            self.assertIsNotNone(status["last_run_at"])
            self.assertIsNotNone(status["last_success_at"])
            self.assertEqual(status["last_fetched_count"], 5)
            self.assertEqual(status["last_duplicate_count"], 2)
            self.assertEqual(status["last_processed_count"], 3)
            self.assertEqual(status["last_failed_count"], 0)
            self.assertIsNone(status["last_error"])

    def test_04_failed_ingestion_updates_error_status(self) -> None:
        with patch("adapters.ocean_scheduler.ingest_ocean_events", side_effect=Exception("GFW Connection Timeout")):
            with self.assertRaises(Exception):
                asyncio.run(ocean_scheduler.poll_once())
            
            status = ocean_scheduler.get_status()
            self.assertIsNotNone(status["last_run_at"])
            self.assertIsNone(status["last_success_at"])
            self.assertIn("GFW Connection Timeout", status["last_error"])

    def test_05_status_endpoint_returns_correct_information(self) -> None:
        res = self.client.get("/ingest/ocean/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("running", data)
        self.assertIn("mode", data)
        self.assertIn("poll_interval_seconds", data)
        self.assertIn("last_run_at", data)
        self.assertIn("last_success_at", data)
        self.assertIn("last_fetched_count", data)
        self.assertIn("last_processed_count", data)
        self.assertIn("last_duplicate_count", data)
        self.assertIn("last_failed_count", data)
        self.assertIn("last_error", data)

    def test_06_events_api_and_provenance_preservation(self) -> None:
        engine = OceanIngestionEngine(store=db_client)

        live_evt = detect_dark_vessel(
            data_mode="live",
            source="global_fishing_watch",
            gfw_event_id="evt_test_live_prov",
            dataset="public-global-gaps-events:latest",
            is_gap_event=True,
            gap_hours=14.0,
        )
        sim_evt = detect_dark_vessel(
            data_mode="simulated",
            source="ecosentinel_demo",
            custom_id="evt_test_sim_prov",
            is_gap_event=True,
            gap_hours=5.0,
        )

        with patch("adapters.ocean_ingest.fetch_ocean_events", return_value=[live_evt, sim_evt]):
            ingest_res = engine.ingest_events(mode="auto", limit=2)
            self.assertEqual(ingest_res["newly_processed_count"], 2)

            res = self.client.get("/events")
            self.assertEqual(res.status_code, 200)
            events = res.json()
            self.assertGreaterEqual(len(events), 2)

            live_entry = next((e for e in events if e.get("event", {}).get("metadata", {}).get("gfw_event_id") == "evt_test_live_prov"), None)
            self.assertIsNotNone(live_entry)
            evt_live = live_entry["event"]
            self.assertEqual(evt_live["metadata"]["source"], "global_fishing_watch")
            self.assertEqual(evt_live["metadata"]["data_mode"], "live")
            self.assertEqual(evt_live["sensor_id"], "GFW_AIS")

            sim_entry = next((e for e in events if e.get("event", {}).get("id") == "evt_test_sim_prov"), None)
            self.assertIsNotNone(sim_entry)
            evt_sim = sim_entry["event"]
            self.assertEqual(evt_sim["metadata"]["source"], "ecosentinel_demo")
            self.assertEqual(evt_sim["metadata"]["data_mode"], "simulated")
            self.assertEqual(evt_sim["sensor_id"], "ECOSENTINEL_SIMULATOR")

    def test_07_event_approval_and_rejection_flow(self) -> None:
        engine = OceanIngestionEngine(store=db_client)

        live_evt = detect_dark_vessel(
            data_mode="live",
            source="global_fishing_watch",
            gfw_event_id="evt_test_approval",
            dataset="public-global-gaps-events:latest",
            is_gap_event=True,
            gap_hours=20.0,
            flag="CHN",
        )
        with patch("adapters.ocean_ingest.fetch_ocean_events", return_value=[live_evt]):
            ingest_res = engine.ingest_events(mode="live", limit=1)
            processed = ingest_res["processed_results"][0]
            evt_id = processed.event.id

            res = self.client.get(f"/events/{evt_id}")
            self.assertEqual(res.status_code, 200)

            res_appr = self.client.post(f"/events/{evt_id}/approve")
            self.assertEqual(res_appr.status_code, 200)
            self.assertEqual(res_appr.json()["human_gate"]["status"], "APPROVED")

        live_evt2 = detect_dark_vessel(
            data_mode="live",
            source="global_fishing_watch",
            gfw_event_id="evt_test_rejection",
            dataset="public-global-gaps-events:latest",
            is_gap_event=True,
            gap_hours=22.0,
        )
        with patch("adapters.ocean_ingest.fetch_ocean_events", return_value=[live_evt2]):
            ingest_res2 = engine.ingest_events(mode="live", limit=1)
            evt_id2 = ingest_res2["processed_results"][0].event.id

            res_rej = self.client.post(f"/events/{evt_id2}/reject")
            self.assertEqual(res_rej.status_code, 200)
            self.assertEqual(res_rej.json()["human_gate"]["status"], "REJECTED")

    def test_08_demo_endpoints(self) -> None:
        # Test POST /demo/fake-poaching
        res_poach = self.client.post("/demo/fake-poaching")
        self.assertEqual(res_poach.status_code, 200)
        data_poach = res_poach.json()
        self.assertEqual(data_poach["event"]["domain"], "land")
        self.assertEqual(data_poach["event"]["event_type"], "gunshot")
        self.assertEqual(data_poach["classification"]["category"], "wildlife_poaching")

        # Test POST /demo/live-ocean
        with patch("adapters.ocean_ingest.fetch_ocean_events", return_value=[]):
            res_ocean = self.client.post("/demo/live-ocean?mode=simulated&limit=2")
            self.assertEqual(res_ocean.status_code, 200)
            data_ocean = res_ocean.json()
            self.assertIn("fetched_count", data_ocean)


if __name__ == "__main__":
    unittest.main()
