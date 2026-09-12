import os
import sys
import unittest
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

    # --- 1. Normalized Output Schema ---
    def test_normalized_output_schema(self) -> None:
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
        self.assertIn("source", meta)
        self.assertIn("data_mode", meta)
        self.assertIn("vessel_id", meta)
        self.assertIn("vessel_type", meta)
        self.assertIn("ais_gap_hours", meta)
        self.assertIn("loitering", meta)
        self.assertIn("encounter", meta)
        self.assertIn("apparent_fishing", meta)
        self.assertIn("protected_area", meta)
        self.assertIn("reasons", meta)
        self.assertIn("supporting_evidence", meta)

    # --- 2. AIS Gap Scoring Baseline ---
    def test_ais_gap_scoring_baseline(self) -> None:
        score, reasons, evidence = calculate_dark_vessel_confidence(
            gap_hours=6.0,
            vessel_type="CARGO",
            apparent_fishing=False,
            loitering=False,
            encounter=False,
            protected_area=False,
            distance_from_shore_nm=10.0,
        )
        self.assertEqual(score, 0.50)
        self.assertTrue(any("AIS gap detected" in r for r in reasons))
        self.assertIn("AIS gap", evidence)

    # --- 3. Long AIS Gap Increases Score ---
    def test_long_ais_gap_increases_score(self) -> None:
        score_short, _, _ = calculate_dark_vessel_confidence(
            gap_hours=5.0,
            vessel_type="CARGO",
            apparent_fishing=False,
            loitering=False,
            encounter=False,
            protected_area=False,
            distance_from_shore_nm=10.0,
        )
        score_long, reasons_long, _ = calculate_dark_vessel_confidence(
            gap_hours=26.0,
            vessel_type="CARGO",
            apparent_fishing=False,
            loitering=False,
            encounter=False,
            protected_area=False,
            distance_from_shore_nm=10.0,
        )
        self.assertGreater(score_long, score_short)
        self.assertTrue(any("exceeds 24 hours" in r for r in reasons_long))

    # --- 4. Fishing Vessel Increases Score ---
    def test_fishing_vessel_increases_score(self) -> None:
        score_cargo, _, _ = calculate_dark_vessel_confidence(
            gap_hours=10.0,
            vessel_type="CARGO",
            apparent_fishing=False,
            loitering=False,
            encounter=False,
            protected_area=False,
            distance_from_shore_nm=10.0,
        )
        score_fishing, reasons_fishing, evidence_fishing = calculate_dark_vessel_confidence(
            gap_hours=10.0,
            vessel_type="FISHING",
            apparent_fishing=False,
            loitering=False,
            encounter=False,
            protected_area=False,
            distance_from_shore_nm=10.0,
        )
        self.assertGreater(score_fishing, score_cargo)
        self.assertTrue(any("Commercial fishing" in r for r in reasons_fishing))
        self.assertIn("Fishing vessel classification", evidence_fishing)

    # --- 5. Loitering Adds Evidence ---
    def test_loitering_adds_evidence(self) -> None:
        score_no_loiter, _, evidence_no = calculate_dark_vessel_confidence(
            gap_hours=10.0,
            vessel_type="CARGO",
            apparent_fishing=False,
            loitering=False,
            encounter=False,
            protected_area=False,
            distance_from_shore_nm=10.0,
        )
        score_loiter, reasons_loiter, evidence_loiter = calculate_dark_vessel_confidence(
            gap_hours=10.0,
            vessel_type="CARGO",
            apparent_fishing=False,
            loitering=True,
            encounter=False,
            protected_area=False,
            distance_from_shore_nm=10.0,
        )
        self.assertGreater(score_loiter, score_no_loiter)
        self.assertIn("Loitering", evidence_loiter)
        self.assertNotIn("Loitering", evidence_no)

    # --- 6. Encounter Adds Evidence ---
    def test_encounter_adds_evidence(self) -> None:
        score_no_enc, _, evidence_no = calculate_dark_vessel_confidence(
            gap_hours=10.0,
            vessel_type="CARGO",
            apparent_fishing=False,
            loitering=False,
            encounter=False,
            protected_area=False,
            distance_from_shore_nm=10.0,
        )
        score_enc, reasons_enc, evidence_enc = calculate_dark_vessel_confidence(
            gap_hours=10.0,
            vessel_type="CARGO",
            apparent_fishing=False,
            loitering=False,
            encounter=True,
            protected_area=False,
            distance_from_shore_nm=10.0,
        )
        self.assertGreater(score_enc, score_no_enc)
        self.assertIn("Encounter", evidence_enc)
        self.assertNotIn("Encounter", evidence_no)

    # --- 7. Protected Area Adds Evidence ---
    def test_protected_area_adds_evidence(self) -> None:
        score_outside, _, _ = calculate_dark_vessel_confidence(
            gap_hours=10.0,
            vessel_type="CARGO",
            apparent_fishing=False,
            loitering=False,
            encounter=False,
            protected_area=False,
            distance_from_shore_nm=10.0,
        )
        score_inside, reasons_inside, evidence_inside = calculate_dark_vessel_confidence(
            gap_hours=10.0,
            vessel_type="CARGO",
            apparent_fishing=False,
            loitering=False,
            encounter=False,
            protected_area=True,
            distance_from_shore_nm=10.0,
        )
        self.assertGreater(score_inside, score_outside)
        self.assertIn("Activity near/inside protected area", evidence_inside)

    # --- 8. Repeated Gaps Add Evidence ---
    def test_repeated_gaps_add_evidence(self) -> None:
        score_single, _, _ = calculate_dark_vessel_confidence(
            gap_hours=10.0,
            vessel_type="CARGO",
            apparent_fishing=False,
            loitering=False,
            encounter=False,
            protected_area=False,
            distance_from_shore_nm=10.0,
            repeated_gaps=False,
        )
        score_repeat, reasons_repeat, evidence_repeat = calculate_dark_vessel_confidence(
            gap_hours=10.0,
            vessel_type="CARGO",
            apparent_fishing=False,
            loitering=False,
            encounter=False,
            protected_area=False,
            distance_from_shore_nm=10.0,
            repeated_gaps=True,
        )
        self.assertGreater(score_repeat, score_single)
        self.assertIn("Repeated AIS gaps", evidence_repeat)

    # --- 9. Missing API Token Handling ---
    def test_missing_api_token(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            # In auto mode: returns simulated events without error
            events_auto = fetch_ocean_events(mode="auto")
            self.assertGreater(len(events_auto), 0)
            self.assertEqual(events_auto[0].metadata["data_mode"], "simulated")
            self.assertEqual(events_auto[0].metadata["source"], "ecosentinel_demo")

            # In live mode: raises ValueError indicating token requirement
            with self.assertRaises(ValueError) as cm:
                fetch_ocean_events(mode="live")
            self.assertIn("GFW_API_TOKEN", str(cm.exception))

    # --- 10. GFW API Timeout Handling ---
    def test_gfw_api_timeout(self) -> None:
        with patch("httpx.post", side_effect=httpx.TimeoutException("Connection timed out")):
            # Auto mode gracefully falls back to simulated
            events = fetch_ocean_events(token="dummy_token_123", mode="auto")
            self.assertGreater(len(events), 0)
            self.assertEqual(events[0].metadata["data_mode"], "simulated")

            # Live mode raises cleanly
            with self.assertRaises(RuntimeError) as cm:
                fetch_ocean_events(token="dummy_token_123", mode="live")
            self.assertIn("failed", str(cm.exception).lower())

    # --- 11. GFW API HTTP Error Handling ---
    def test_gfw_api_http_error(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = '{"error": "invalid token"}'

        with patch("httpx.post", return_value=mock_resp):
            # Auto mode gracefully falls back to simulated
            events = fetch_ocean_events(token="invalid_token", mode="auto")
            self.assertGreater(len(events), 0)
            self.assertEqual(events[0].metadata["data_mode"], "simulated")

            # Live mode raises informative error
            with self.assertRaises(RuntimeError) as cm:
                fetch_ocean_events(token="invalid_token", mode="live")
            self.assertIn("401", str(cm.exception))

    # --- 12. Real-Looking Mocked GFW Response Normalization & Request Shape ---
    def test_mocked_gfw_response_normalization(self) -> None:
        mock_payload = {
            "entries": [
                {
                    "id": "gfw_raw_gap_98765",
                    "start": "2026-08-15T04:30:00Z",
                    "position": {"lat": -0.45, "lon": -90.55},
                    "gap": {"durationHours": 22.4, "distanceFromShoreKm": 120.0},
                    "vessel": {
                        "id": "vsl_real_trawler_44",
                        "type": "FISHING",
                        "flag": "PER",
                    },
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.post", return_value=mock_resp) as mock_post:
            events = fetch_ocean_events(
                start_date="2026-08-01T00:00:00Z",
                end_date="2026-08-15T23:59:59Z",
                token="valid_test_token",
                mode="live",
                region={"type": "Polygon", "coordinates": [[[-92.5, -1.5], [-89.0, -1.5], [-89.0, 1.5], [-92.5, 1.5], [-92.5, -1.5]]]},
            )
            self.assertEqual(len(events), 1)
            ev = events[0]
            self.assertEqual(ev.domain, "ocean")
            self.assertEqual(ev.event_type, "potential_dark_vessel")
            self.assertEqual(ev.sensor_id, "GFW_AIS")
            self.assertEqual(ev.metadata["source"], "global_fishing_watch")
            self.assertEqual(ev.metadata["data_mode"], "live")
            self.assertEqual(ev.metadata["vessel_id"], "vsl_real_trawler_44")
            self.assertEqual(ev.metadata["gfw_event_id"], "gfw_raw_gap_98765")
            self.assertAlmostEqual(ev.metadata["ais_gap_hours"], 22.4)

            # Verify request shape (all 10 requirements)
            mock_post.assert_called_once()
            call_args, call_kwargs = mock_post.call_args
            # 1 & 2: POST to /v3/events
            self.assertEqual(call_args[0], "https://gateway.api.globalfishingwatch.org/v3/events")
            # 3 & 4: Query parameters contain offset=0 and positive limit
            params = call_kwargs["params"]
            self.assertEqual(params["offset"], 0)
            self.assertGreaterEqual(params["limit"], 1)
            # 9: Authorization header present
            self.assertEqual(call_kwargs["headers"]["Authorization"], "Bearer valid_test_token")
            self.assertEqual(call_kwargs["headers"]["Content-Type"], "application/json")

            # 5, 6, 7, 8: JSON body fields
            json_body = call_kwargs["json"]
            self.assertEqual(len(json_body["datasets"]), 4)
            self.assertIn("public-global-gaps-events:latest", json_body["datasets"])
            self.assertIn("public-global-loitering-events:latest", json_body["datasets"])
            self.assertIn("public-global-encounters-events:latest", json_body["datasets"])
            self.assertIn("public-global-fishing-events:latest", json_body["datasets"])
            self.assertEqual(json_body["startDate"], "2026-08-01T00:00:00Z")
            self.assertEqual(json_body["endDate"], "2026-08-15T23:59:59Z")
            self.assertEqual(json_body["region"]["type"], "Polygon")

    # --- 13. Simulated Events Explicitly Marked Simulated ---
    def test_simulated_events_marked_explicitly(self) -> None:
        sim_events = get_simulated_ocean_events(limit=3)
        for ev in sim_events:
            self.assertEqual(ev.metadata["data_mode"], "simulated")
            self.assertEqual(ev.metadata["source"], "ecosentinel_demo")
            self.assertEqual(ev.sensor_id, "ECOSENTINEL_SIMULATOR")
            self.assertIn("Simulated demonstration event", ev.metadata.get("note", ""))
            self.assertNotEqual(ev.metadata["source"], "global_fishing_watch")

    # --- 14. Person 3 POST Integration & Pipeline ---
    def test_person3_pipeline_and_post(self) -> None:
        from fastapi.testclient import TestClient
        from main import app

        demo_event = get_demo_ocean_event()
        # Direct pipeline processing
        result = process_event(demo_event)
        self.assertEqual(result.event.domain, "ocean")
        self.assertEqual(result.classification.refined_type, "possible_illegal_fishing")
        self.assertIn(result.action.action, ("TRACK_VESSEL", "REQUEST_MORE_EVIDENCE"))

        # FastAPI POST /events contract test
        client = TestClient(app)
        resp = client.post("/events", json=demo_event.model_dump(mode="json"))
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["event"]["domain"], "ocean")
        self.assertEqual(data["event"]["event_type"], "potential_dark_vessel")
        self.assertEqual(data["classification"]["refined_type"], "possible_illegal_fishing")

    def test_post_to_person3_connection_error(self) -> None:
        event = get_demo_ocean_event()
        with patch("httpx.post", side_effect=httpx.ConnectError("Connection refused")):
            with self.assertRaises(ConnectionError):
                post_to_person3(event, backend_url="http://127.0.0.1:59999/events")

    def test_post_to_person3_timeout_error(self) -> None:
        event = get_demo_ocean_event()
        with patch("httpx.post", side_effect=httpx.TimeoutException("Request timed out")):
            with self.assertRaises(TimeoutError):
                post_to_person3(event, backend_url="http://127.0.0.1:59999/events")


if __name__ == "__main__":
    unittest.main()
