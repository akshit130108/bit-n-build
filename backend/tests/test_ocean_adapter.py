import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx

from adapters.ocean_gfw import (
    calculate_dark_vessel_confidence,
    detect_dark_vessel,
    evaluate_mpa_context,
    fetch_ocean_events,
    get_demo_ocean_event,
    get_simulated_ocean_events,
    post_to_person3,
)
from orchestrator.pipeline import process_event
from schemas.event import NormalizedEvent


class TestOceanGFWAdapter(unittest.TestCase):

    # --- 1. Simulated Event Generation ---
    def test_simulated_event_generation(self) -> None:
        event = detect_dark_vessel(
            gap_hours=18.5,
            lat=-0.4850,
            lon=-90.4920,
            vessel_id="demo_vsl_001",
            vessel_type="FISHING",
            flag="CHN",
            distance_from_shore_nm=72.0,
            apparent_fishing=True,
            loitering=True,
            data_mode="simulated",
        )
        self.assertIsInstance(event, NormalizedEvent)
        self.assertEqual(event.domain, "ocean")
        self.assertEqual(event.event_type, "potential_dark_vessel")
        self.assertGreaterEqual(event.confidence, 0.0)
        self.assertLessEqual(event.confidence, 1.0)
        self.assertAlmostEqual(event.location.lat, -0.4850)
        self.assertAlmostEqual(event.location.lon, -90.4920)

        # Required metadata fields
        meta = event.metadata
        self.assertEqual(meta["source"], "ecosentinel_demo")
        self.assertEqual(meta["data_mode"], "simulated")
        self.assertEqual(meta["vessel_id"], "demo_vsl_001")
        self.assertEqual(meta["ais_gap_hours"], 18.5)
        self.assertTrue(meta["loitering"])
        self.assertFalse(meta["encounter"])
        self.assertTrue(meta["apparent_fishing"])
        self.assertIn("reasons", meta)
        self.assertIn("supporting_evidence", meta)

    # --- 2. Live Event With Valid AIS Gap ---
    def test_live_event_with_valid_ais_gap(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "gfw_gap_001",
                    "start": "2026-09-01T12:00:00Z",
                    "dataset": "public-global-gaps-events:latest",
                    "type": "gap",
                    "position": {"lat": -0.45, "lon": -90.55},
                    "gap": {"durationHours": 24.5, "distanceFromShoreKm": 100.0},
                    "vessel": {"id": "vsl_123", "type": "FISHING", "flag": "PER"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(token="test_token", mode="live")
            self.assertEqual(len(events), 1)
            ev = events[0]
            self.assertEqual(ev.event_type, "potential_dark_vessel")
            self.assertEqual(ev.metadata["ais_gap_hours"], 24.5)
            self.assertEqual(ev.metadata["source"], "global_fishing_watch")
            self.assertEqual(ev.metadata["data_mode"], "live")

    # --- 3. Live Event With Missing AIS Gap (No Fake 12.0 Hours) ---
    def test_live_event_with_missing_ais_gap(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "gfw_loiter_002",
                    "start": "2026-09-02T14:00:00Z",
                    "dataset": "public-global-loitering-events:latest",
                    "type": "loitering",
                    "position": {"lat": 1.2, "lon": 103.8},
                    "vessel": {"id": "vsl_456", "type": "CARRIER", "flag": "PAN"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(token="test_token", mode="live")
            self.assertEqual(len(events), 1)
            ev = events[0]
            # Must NOT have fabricated 12.0 gap_hours
            self.assertNotIn("ais_gap_hours", ev.metadata)
            self.assertTrue(ev.metadata["loitering"])
            self.assertFalse(ev.metadata["apparent_fishing"])

    # --- 4. Live Event With Nested Vessel Info ---
    def test_live_event_with_nested_vessel_info(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "gfw_enc_003",
                    "start": "2026-09-03T08:00:00Z",
                    "dataset": "public-global-encounters-events:latest",
                    "position": {"lat": 5.0, "lon": 80.0},
                    "vessel": {"ssvid": "mmsi_999888777", "vesselType": "REEFER", "flag": "LBR"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(token="test_token", mode="live")
            self.assertEqual(len(events), 1)
            ev = events[0]
            self.assertEqual(ev.metadata["vessel_id"], "mmsi_999888777")
            self.assertEqual(ev.metadata["vessel_type"], "REEFER")
            self.assertEqual(ev.metadata["flag"], "LBR")
            self.assertTrue(ev.metadata["encounter"])

    # --- 5. Live Event With Fishing Evidence ---
    def test_live_event_with_fishing_evidence(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "gfw_fish_004",
                    "start": "2026-09-04T10:00:00Z",
                    "dataset": "public-global-fishing-events:latest",
                    "type": "fishing",
                    "position": {"lat": -0.5, "lon": -90.5},
                    "vessel": {"id": "vsl_trawler", "type": "FISHING", "flag": "CHN"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(token="test_token", mode="live")
            self.assertEqual(len(events), 1)
            ev = events[0]
            self.assertTrue(ev.metadata["apparent_fishing"])

    # --- 6. Live Event Without Fishing Evidence ---
    def test_live_event_without_fishing_evidence(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "gfw_cargo_005",
                    "start": "2026-09-05T12:00:00Z",
                    "dataset": "public-global-loitering-events:latest",
                    "type": "loitering",
                    "position": {"lat": 20.0, "lon": 60.0},
                    "vessel": {"id": "vsl_cargo", "type": "CONTAINER", "flag": "SGP"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(token="test_token", mode="live")
            self.assertEqual(len(events), 1)
            ev = events[0]
            self.assertFalse(ev.metadata["apparent_fishing"])

    # --- 7. Live Event With Loitering ---
    def test_live_event_with_loitering(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "gfw_loiter_006",
                    "start": "2026-09-06T15:00:00Z",
                    "dataset": "public-global-loitering-events:latest",
                    "position": {"lat": 0.0, "lon": 0.0},
                    "vessel": {"id": "vsl_loiter"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(token="test_token", mode="live")
            self.assertEqual(len(events), 1)
            self.assertTrue(events[0].metadata["loitering"])

    # --- 8. Live Event With Encounter ---
    def test_live_event_with_encounter(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "gfw_enc_007",
                    "start": "2026-09-07T18:00:00Z",
                    "dataset": "public-global-encounters-events:latest",
                    "position": {"lat": 10.0, "lon": 10.0},
                    "vessel": {"id": "vsl_enc"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(token="test_token", mode="live")
            self.assertEqual(len(events), 1)
            self.assertTrue(events[0].metadata["encounter"])

    # --- 9. Current/Recent Timestamp Parsing ---
    def test_recent_timestamp_parsing(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"entries": []}

        with patch("httpx.post", return_value=mock_resp) as mock_post:
            fetch_ocean_events(token="test_token", mode="live")
            call_kwargs = mock_post.call_args[1]
            body = call_kwargs["json"]
            self.assertIn("startDate", body)
            self.assertIn("endDate", body)
            # Verify startDate represents a recent window (e.g. 2026)
            self.assertTrue(body["startDate"].startswith("202"))

    # --- 10. MPA Inside/Boundary/Outside Behavior ---
    def test_mpa_status_differentiation(self) -> None:
        # Inside Galapagos Reserve
        inside = evaluate_mpa_context(-0.4850, -90.4920)
        self.assertTrue(inside["protected_area"])
        self.assertEqual(inside["mpa_status"], "INSIDE_RESERVE")
        self.assertEqual(inside["boundary_source"], "local_demo_geojson")

        # Near boundary buffer (within 20km)
        near = evaluate_mpa_context(-1.600, -90.750)
        self.assertTrue(near["protected_area"])
        self.assertEqual(near["mpa_status"], "NEAR_BOUNDARY_BUFFER")

        # Outside reserve
        outside = evaluate_mpa_context(45.0, 45.0)
        self.assertFalse(outside["protected_area"])
        self.assertEqual(outside["mpa_status"], "OUTSIDE_RESERVE")

    # --- 11. API Error in mode="live" ---
    def test_api_error_in_mode_live(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        with patch("httpx.post", return_value=mock_resp):
            with self.assertRaises(RuntimeError) as cm:
                fetch_ocean_events(token="test_token", mode="live")
            self.assertIn("500", str(cm.exception))

    # --- 12. API Error in mode="auto" ---
    def test_api_error_in_mode_auto(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(token="test_token", mode="auto")
            self.assertGreater(len(events), 0)
            self.assertEqual(events[0].metadata["data_mode"], "simulated")

    # --- 13. No Token in Live Mode ---
    def test_no_token_in_live_mode(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as cm:
                fetch_ocean_events(mode="live")
            self.assertIn("GFW_API_TOKEN", str(cm.exception))

    # --- 14. No Token in Auto Mode ---
    def test_no_token_in_auto_mode(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            events = fetch_ocean_events(mode="auto")
            self.assertGreater(len(events), 0)
            self.assertEqual(events[0].metadata["data_mode"], "simulated")

    # --- 15. Person 3 Integration ---
    def test_person3_integration(self) -> None:
        demo_event = get_demo_ocean_event()
        result = process_event(demo_event)
        self.assertEqual(result.event.domain, "ocean")
        self.assertIn(result.action.action, ("TRACK_VESSEL", "REQUEST_MORE_EVIDENCE", "CONTINUE_MONITORING"))

    # --- 16 Task Specific Required Tests ---

    def test_task_01_recent_default_date_window_generated(self) -> None:
        mock_payload = {"entries": []}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp) as mock_post:
            fetch_ocean_events(token="test_token", mode="live", start_date=None, end_date=None)
            body = mock_post.call_args[1]["json"]
            self.assertIn("startDate", body)
            self.assertIn("endDate", body)
            self.assertTrue(body["startDate"].endswith("Z"))
            self.assertTrue(body["endDate"].endswith("Z"))

    def test_task_02_explicit_start_end_date_override(self) -> None:
        mock_payload = {"entries": []}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp) as mock_post:
            fetch_ocean_events(
                token="test_token",
                mode="live",
                start_date="2026-08-01T00:00:00Z",
                end_date="2026-08-15T00:00:00Z",
            )
            body = mock_post.call_args[1]["json"]
            self.assertEqual(body["startDate"], "2026-08-01T00:00:00Z")
            self.assertEqual(body["endDate"], "2026-08-15T00:00:00Z")

    def test_task_03_stale_2014_event_rejected(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "stale_2014_evt",
                    "start": "2014-09-23T03:39:27.000Z",
                    "dataset": "public-global-gaps-events:latest",
                    "position": {"lat": 10.0, "lon": 10.0},
                    "vessel": {"id": "old_vessel"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(
                token="test_token",
                mode="live",
                start_date="2026-09-01T00:00:00Z",
                end_date="2026-09-13T00:00:00Z",
            )
            self.assertEqual(len(events), 0)

    def test_task_07_exact_production_failure_regression_test(self) -> None:
        """Regression test for the 2014 historical timestamp leak."""
        mock_stale = {
            "entries": [
                {
                    "id": "prod_fail_2014",
                    "start": "2014-09-23T03:39:27.000Z",
                    "dataset": "public-global-gaps-events:latest",
                    "position": {"lat": -0.485, "lon": -90.492},
                    "vessel": {"id": "vsl_2014"},
                }
            ]
        }
        mock_resp_stale = MagicMock()
        mock_resp_stale.status_code = 200
        mock_resp_stale.json.return_value = mock_stale

        with patch("httpx.post", return_value=mock_resp_stale):
            stale_events = fetch_ocean_events(
                token="test_token",
                mode="live",
                start_date="2026-08-13T00:00:00Z",
                end_date="2026-09-13T00:00:00Z",
            )
            self.assertEqual(len(stale_events), 0, "Historical 2014 event MUST be filtered out")

        # Inverse test: valid recent event in window
        mock_valid = {
            "entries": [
                {
                    "id": "prod_valid_2026",
                    "start": "2026-09-10T08:00:00Z",
                    "dataset": "public-global-loitering-events:latest",
                    "position": {"lat": -0.485, "lon": -90.492},
                    "vessel": {"id": "vsl_2026"},
                }
            ]
        }
        mock_resp_valid = MagicMock()
        mock_resp_valid.status_code = 200
        mock_resp_valid.json.return_value = mock_valid

        with patch("httpx.post", return_value=mock_resp_valid):
            valid_events = fetch_ocean_events(
                token="test_token",
                mode="live",
                start_date="2026-08-13T00:00:00Z",
                end_date="2026-09-13T00:00:00Z",
            )
            self.assertEqual(len(valid_events), 1, "Valid 2026 event MUST be accepted")
            self.assertEqual(valid_events[0].timestamp, "2026-09-10T08:00:00Z")

    def test_task_04_valid_recent_timestamp_accepted(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "recent_2026_evt",
                    "start": "2026-09-05T12:00:00Z",
                    "dataset": "public-global-loitering-events:latest",
                    "position": {"lat": 10.0, "lon": 10.0},
                    "vessel": {"id": "new_vessel"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(
                token="test_token",
                mode="live",
                start_date="2026-09-01T00:00:00Z",
                end_date="2026-09-13T00:00:00Z",
            )
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].timestamp, "2026-09-05T12:00:00Z")

    def test_task_05_missing_gap_duration_remains_none(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "no_gap_dur_evt",
                    "start": "2026-09-05T12:00:00Z",
                    "dataset": "public-global-loitering-events:latest",
                    "position": {"lat": 10.0, "lon": 10.0},
                    "vessel": {"id": "vessel_x"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(token="test_token", mode="live")
            self.assertEqual(len(events), 1)
            self.assertNotIn("ais_gap_hours", events[0].metadata)

    def test_task_06_loitering_dataset_produces_loitering_evidence(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "loitering_evt",
                    "start": "2026-09-05T12:00:00Z",
                    "dataset": "public-global-loitering-events:latest",
                    "position": {"lat": 10.0, "lon": 10.0},
                    "vessel": {"id": "vessel_loiter"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(token="test_token", mode="live")
            self.assertTrue(events[0].metadata["loitering"])
            self.assertFalse(events[0].metadata["apparent_fishing"])

    def test_task_07_encounter_dataset_produces_encounter_evidence(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "encounter_evt",
                    "start": "2026-09-05T12:00:00Z",
                    "dataset": "public-global-encounters-events:latest",
                    "position": {"lat": 10.0, "lon": 10.0},
                    "vessel": {"id": "vessel_encounter"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(token="test_token", mode="live")
            self.assertTrue(events[0].metadata["encounter"])
            self.assertFalse(events[0].metadata["apparent_fishing"])

    def test_task_08_fishing_dataset_produces_fishing_evidence(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "fishing_evt",
                    "start": "2026-09-05T12:00:00Z",
                    "dataset": "public-global-fishing-events:latest",
                    "position": {"lat": 10.0, "lon": 10.0},
                    "vessel": {"id": "vessel_fishing"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(token="test_token", mode="live")
            self.assertTrue(events[0].metadata["apparent_fishing"])

    def test_task_09_ais_gap_dataset_produces_ais_gap_evidence(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "gap_evt",
                    "start": "2026-09-05T12:00:00Z",
                    "dataset": "public-global-gaps-events:latest",
                    "position": {"lat": 10.0, "lon": 10.0},
                    "vessel": {"id": "vessel_gap"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(token="test_token", mode="live")
            self.assertTrue(events[0].metadata["ais_disabled"])
            self.assertEqual(events[0].event_type, "potential_dark_vessel")

    def test_task_10_event_type_changes_according_to_evidence(self) -> None:
        loiter_event = detect_dark_vessel(loitering=True, apparent_fishing=False, is_gap_event=False)
        self.assertEqual(loiter_event.event_type, "suspicious_loitering_vessel")

        encounter_event = detect_dark_vessel(encounter=True, apparent_fishing=False, is_gap_event=False)
        self.assertEqual(encounter_event.event_type, "suspicious_encounter_vessel")

        fishing_event = detect_dark_vessel(apparent_fishing=True, is_gap_event=False)
        self.assertEqual(fishing_event.event_type, "possible_illegal_fishing")

        general_vessel = detect_dark_vessel(is_gap_event=False)
        self.assertEqual(general_vessel.event_type, "suspicious_vessel")

    def test_task_11_low_confidence_loitering_does_not_become_high_urgency_illegal_fishing(self) -> None:
        event = detect_dark_vessel(
            lat=45.0,
            lon=45.0,  # Outside protected area
            loitering=True,
            apparent_fishing=False,
            is_gap_event=False,
            gap_hours=None,
        )
        result = process_event(event)
        self.assertEqual(result.classification.refined_type, "suspicious_loitering_vessel")
        self.assertEqual(result.classification.category, "marine_loitering")
        self.assertEqual(result.classification.urgency, "low")
        self.assertEqual(result.risk.level, "LOW")
        self.assertEqual(result.human_gate.status, "AUTO_APPROVED")
        self.assertEqual(result.action.action, "CONTINUE_MONITORING")

    def test_task_12_risk_reasons_never_mention_nighttime_without_evidence(self) -> None:
        event = detect_dark_vessel(is_gap_event=False, timestamp="2026-09-05T22:00:00Z")
        # Ensure is_night is NOT set in metadata
        event.metadata.pop("is_night", None)
        result = process_event(event)
        night_reasons = [r for r in result.risk.reasons if "Nighttime" in r or "night" in r.lower()]
        self.assertEqual(len(night_reasons), 0)

    def test_task_13_risk_reasons_never_mention_recurrence_without_memory(self) -> None:
        event = detect_dark_vessel(is_gap_event=False)
        result = process_event(event)
        self.assertIn("Isolated event: No recent historical incidents in sector", result.risk.reasons)

    def test_task_14_protected_area_reasoning_only_when_mpa_confirms(self) -> None:
        event = detect_dark_vessel(lat=45.0, lon=45.0)  # Clearly outside MPA
        result = process_event(event)
        mpa_reasons = [r for r in result.risk.reasons if "Protected Ecological Reserve" in r]
        self.assertEqual(len(mpa_reasons), 0)

    def test_task_15_live_events_contain_correct_provenance(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "live_prov_evt",
                    "start": "2026-09-05T12:00:00Z",
                    "dataset": "public-global-loitering-events:latest",
                    "position": {"lat": 10.0, "lon": 10.0},
                    "vessel": {"id": "vessel_live"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp):
            events = fetch_ocean_events(token="test_token", mode="live")
            self.assertEqual(events[0].metadata["source"], "global_fishing_watch")
            self.assertEqual(events[0].metadata["data_mode"], "live")
            self.assertEqual(events[0].sensor_id, "GFW_AIS")

    def test_task_16_simulated_events_contain_correct_provenance(self) -> None:
        events = get_simulated_ocean_events(limit=1)
        self.assertEqual(events[0].metadata["source"], "ecosentinel_demo")
        self.assertEqual(events[0].metadata["data_mode"], "simulated")
        self.assertEqual(events[0].sensor_id, "ECOSENTINEL_SIMULATOR")


if __name__ == "__main__":
    unittest.main()

