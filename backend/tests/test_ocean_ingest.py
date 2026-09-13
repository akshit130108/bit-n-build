import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adapters.ocean_gfw import detect_dark_vessel
from adapters.ocean_ingest import OceanIngestionEngine, ingest_ocean_events
from database.firestore import InMemoryStore
from schemas.event import NormalizedEvent, PipelineResult


class TestOceanIngestionLayer(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_store = InMemoryStore()
        self.engine = OceanIngestionEngine(store=self.mock_store)

    def test_01_one_new_gfw_event_processed(self) -> None:
        live_evt = detect_dark_vessel(
            data_mode="live",
            source="global_fishing_watch",
            gfw_event_id="evt_test_001",
            dataset="public-global-gaps-events:latest",
            is_gap_event=True,
            gap_hours=15.0,
        )

        with patch("adapters.ocean_ingest.fetch_ocean_events", return_value=[live_evt]):
            res = self.engine.ingest_events(mode="live", limit=1)
            self.assertEqual(res["fetched_count"], 1)
            self.assertEqual(res["duplicate_count"], 0)
            self.assertEqual(res["newly_processed_count"], 1)
            self.assertEqual(res["failed_count"], 0)
            self.assertEqual(len(res["processed_results"]), 1)
            self.assertIsInstance(res["processed_results"][0], PipelineResult)

    def test_02_duplicate_gfw_event_skipped(self) -> None:
        live_evt = detect_dark_vessel(
            data_mode="live",
            source="global_fishing_watch",
            gfw_event_id="evt_test_dup",
            dataset="public-global-gaps-events:latest",
            is_gap_event=True,
            gap_hours=15.0,
        )

        with patch("adapters.ocean_ingest.fetch_ocean_events", return_value=[live_evt]):
            # First run: process
            res1 = self.engine.ingest_events(mode="live", limit=1)
            self.assertEqual(res1["newly_processed_count"], 1)

            # Second run: duplicate skipped
            res2 = self.engine.ingest_events(mode="live", limit=1)
            self.assertEqual(res2["fetched_count"], 1)
            self.assertEqual(res2["duplicate_count"], 1)
            self.assertEqual(res2["newly_processed_count"], 0)

    def test_03_two_different_gfw_events_both_processed(self) -> None:
        evt1 = detect_dark_vessel(
            data_mode="live",
            source="global_fishing_watch",
            gfw_event_id="evt_diff_1",
            dataset="public-global-loitering-events:latest",
            loitering=True,
        )
        evt2 = detect_dark_vessel(
            data_mode="live",
            source="global_fishing_watch",
            gfw_event_id="evt_diff_2",
            dataset="public-global-encounters-events:latest",
            encounter=True,
        )

        with patch("adapters.ocean_ingest.fetch_ocean_events", return_value=[evt1, evt2]):
            res = self.engine.ingest_events(mode="live", limit=2)
            self.assertEqual(res["fetched_count"], 2)
            self.assertEqual(res["duplicate_count"], 0)
            self.assertEqual(res["newly_processed_count"], 2)

    def test_04_missing_gfw_event_id_handled_safely(self) -> None:
        evt_no_gfw_id = detect_dark_vessel(
            data_mode="live",
            source="global_fishing_watch",
            gfw_event_id=None,
            custom_id="custom_evt_999",
            is_gap_event=True,
        )

        with patch("adapters.ocean_ingest.fetch_ocean_events", return_value=[evt_no_gfw_id]):
            res = self.engine.ingest_events(mode="live", limit=1)
            self.assertEqual(res["fetched_count"], 1)
            self.assertEqual(res["newly_processed_count"], 1)

            # Second ingestion should deduplicate based on custom_id/event.id
            res_dup = self.engine.ingest_events(mode="live", limit=1)
            self.assertEqual(res_dup["duplicate_count"], 1)

    def test_05_simulated_events_remain_simulated(self) -> None:
        sim_evt = detect_dark_vessel(
            data_mode="simulated",
            source="ecosentinel_demo",
            custom_id="sim_test_001",
        )

        with patch("adapters.ocean_ingest.fetch_ocean_events", return_value=[sim_evt]):
            res = self.engine.ingest_events(mode="simulated", limit=1)
            proc_evt = res["processed_results"][0].event
            self.assertEqual(proc_evt.metadata["source"], "ecosentinel_demo")
            self.assertEqual(proc_evt.metadata["data_mode"], "simulated")
            self.assertEqual(proc_evt.sensor_id, "ECOSENTINEL_SIMULATOR")

    def test_06_live_provenance_remains_live(self) -> None:
        live_evt = detect_dark_vessel(
            data_mode="live",
            source="global_fishing_watch",
            gfw_event_id="gfw_prov_100",
        )

        with patch("adapters.ocean_ingest.fetch_ocean_events", return_value=[live_evt]):
            res = self.engine.ingest_events(mode="live", limit=1)
            proc_evt = res["processed_results"][0].event
            self.assertEqual(proc_evt.metadata["source"], "global_fishing_watch")
            self.assertEqual(proc_evt.metadata["data_mode"], "live")
            self.assertEqual(proc_evt.sensor_id, "GFW_AIS")

    def test_07_person3_receives_exact_normalized_event(self) -> None:
        live_evt = detect_dark_vessel(
            data_mode="live",
            source="global_fishing_watch",
            gfw_event_id="exact_p3_evt",
            lat=-0.4850,
            lon=-90.4920,
        )

        with patch("adapters.ocean_ingest.fetch_ocean_events", return_value=[live_evt]):
            res = self.engine.ingest_events(mode="live", limit=1)
            pipeline_res = res["processed_results"][0]
            self.assertEqual(pipeline_res.event.id, live_evt.id)
            self.assertEqual(pipeline_res.event.domain, "ocean")
            self.assertEqual(pipeline_res.event.location.lat, -0.4850)
            self.assertEqual(pipeline_res.event.location.lon, -90.4920)

    def test_08_one_failed_event_does_not_mark_batch_successful(self) -> None:
        evt1 = detect_dark_vessel(custom_id="fail_evt_1", data_mode="live")

        def mock_process(event: NormalizedEvent) -> PipelineResult:
            raise ValueError("Processing pipeline internal explosion")

        with patch("adapters.ocean_ingest.fetch_ocean_events", return_value=[evt1]):
            with patch("adapters.ocean_ingest.process_event", side_effect=mock_process):
                res = self.engine.ingest_events(mode="live", limit=1)
                self.assertEqual(res["fetched_count"], 1)
                self.assertEqual(res["newly_processed_count"], 0)
                self.assertEqual(res["failed_count"], 1)
                self.assertEqual(len(res["errors"]), 1)
                self.assertIn("Processing pipeline internal explosion", res["errors"][0])

    def test_09_empty_gfw_response(self) -> None:
        with patch("adapters.ocean_ingest.fetch_ocean_events", return_value=[]):
            res = self.engine.ingest_events(mode="live", limit=5)
            self.assertEqual(res["fetched_count"], 0)
            self.assertEqual(res["duplicate_count"], 0)
            self.assertEqual(res["newly_processed_count"], 0)
            self.assertEqual(res["failed_count"], 0)
            self.assertEqual(len(res["processed_results"]), 0)

    def test_10_gfw_api_failure_in_live_mode(self) -> None:
        with patch("adapters.ocean_ingest.fetch_ocean_events", side_effect=RuntimeError("500 Internal Server Error")):
            with self.assertRaises(RuntimeError) as cm:
                self.engine.ingest_events(mode="live", limit=5)
            self.assertIn("500", str(cm.exception))

    def test_11_gfw_api_failure_in_auto_mode(self) -> None:
        # In auto mode, fetch_ocean_events falls back to simulated events
        sim_evt = detect_dark_vessel(data_mode="simulated", custom_id="fallback_sim_01")
        with patch("adapters.ocean_ingest.fetch_ocean_events", return_value=[sim_evt]):
            res = self.engine.ingest_events(mode="auto", limit=5)
            self.assertGreater(res["fetched_count"], 0)
            self.assertEqual(res["processed_results"][0].event.metadata["data_mode"], "simulated")


if __name__ == "__main__":
    unittest.main()
