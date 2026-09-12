import os
import sys
import unittest

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adapters.ocean_gfw import (
    calculate_dark_vessel_confidence,
    detect_dark_vessel,
    evaluate_mpa_context,
    fetch_ocean_events,
    get_demo_ocean_event,
)
from orchestrator.pipeline import process_event
from schemas.event import NormalizedEvent


class TestOceanGFWAdapter(unittest.TestCase):

    def test_calculate_confidence_scoring(self) -> None:
        # Base gap only
        score_base, reasons_base = calculate_dark_vessel_confidence(
            gap_hours=6.0,
            vessel_type="CARGO",
            apparent_fishing=False,
            loitering=False,
            encounter=False,
            protected_area=False,
            distance_from_shore_nm=10.0,
        )
        self.assertEqual(score_base, 0.50)
        self.assertTrue(any("AIS gap detected" in r for r in reasons_base))

        # Accumulated suspicious evidence (long gap, fishing, loitering, MPA)
        score_high, reasons_high = calculate_dark_vessel_confidence(
            gap_hours=28.0,
            vessel_type="FISHING",
            apparent_fishing=True,
            loitering=True,
            encounter=False,
            protected_area=True,
            distance_from_shore_nm=65.0,
        )
        # Expected: 0.50 + 0.10 (gap) + 0.10 (vessel) + 0.10 (fishing) + 0.05 (loitering) + 0.10 (MPA) + 0.03 (offshore) = 0.98
        self.assertGreaterEqual(score_high, 0.90)
        self.assertTrue(any("exceeds 24 hours" in r for r in reasons_high))
        self.assertTrue(any("Commercial fishing" in r for r in reasons_high))
        self.assertTrue(any("Marine Protected Area" in r for r in reasons_high))

    def test_mpa_context_evaluation(self) -> None:
        # Inside Galapagos Marine Reserve
        inside = evaluate_mpa_context(lat=-0.50, lon=-90.50)
        self.assertTrue(inside["protected_area"])
        self.assertEqual(inside["protected_area_name"], "Galapagos Marine Reserve")
        self.assertEqual(inside["mpa_status"], "INSIDE_RESERVE")
        self.assertEqual(inside["distance_to_boundary_km"], 0.0)

        # Far outside in international waters
        outside = evaluate_mpa_context(lat=40.0, lon=-40.0)
        self.assertFalse(outside["protected_area"])
        self.assertEqual(outside["mpa_status"], "OUTSIDE_RESERVE")

    def test_detect_dark_vessel_contract(self) -> None:
        event = detect_dark_vessel(
            gap_hours=18.5,
            lat=-0.4850,
            lon=-90.4920,
            vessel_id="vsl_test_123",
            vessel_type="FISHING",
            flag="CHN",
            distance_from_shore_nm=72.0,
            apparent_fishing=True,
            loitering=True,
        )

        # Must conform strictly to Person 3 NormalizedEvent schema
        self.assertIsInstance(event, NormalizedEvent)
        self.assertEqual(event.domain, "ocean")
        self.assertEqual(event.event_type, "potential_dark_vessel")
        self.assertGreater(event.confidence, 0.0)
        self.assertLessEqual(event.confidence, 1.0)
        self.assertEqual(event.sensor_id, "GFW_AIS")
        self.assertAlmostEqual(event.location.lat, -0.4850)
        self.assertAlmostEqual(event.location.lon, -90.4920)

        # Metadata contract verification (Section 8)
        meta = event.metadata
        self.assertEqual(meta["source"], "global_fishing_watch")
        self.assertEqual(meta["vessel_id"], "vsl_test_123")
        self.assertEqual(meta["vessel_type"], "FISHING")
        self.assertEqual(meta["flag"], "CHN")
        self.assertEqual(meta["ais_gap_hours"], 18.5)
        self.assertTrue(meta["protected_area"])
        self.assertEqual(meta["protected_area_name"], "Galapagos Marine Reserve")
        self.assertTrue(meta["loitering"])
        self.assertFalse(meta["encounter"])
        self.assertTrue(meta["apparent_fishing"])
        self.assertIsInstance(meta["reasons"], list)
        self.assertGreater(len(meta["reasons"]), 0)

    def test_fetch_ocean_events(self) -> None:
        events = fetch_ocean_events(limit=3)
        self.assertGreaterEqual(len(events), 1)
        for ev in events:
            self.assertEqual(ev.domain, "ocean")
            self.assertEqual(ev.event_type, "potential_dark_vessel")

    def test_person3_pipeline_integration(self) -> None:
        """Verify that the normalized ocean event executes through Person 3 seamlessly."""
        ocean_event = get_demo_ocean_event()
        result = process_event(ocean_event)

        # Verification of Person 3 pipeline outputs
        self.assertEqual(result.event.id, ocean_event.id)
        self.assertEqual(result.classification.refined_type, "possible_illegal_fishing")
        self.assertEqual(result.classification.category, "marine_violation")
        self.assertIn(result.verification.level, ("high", "medium"))
        self.assertGreater(result.risk.score, 50)
        self.assertIn(result.action.action, ("TRACK_VESSEL", "REQUEST_MORE_EVIDENCE"))

    def test_fastapi_post_events_contract(self) -> None:
        """Verify that Person 3 FastAPI endpoint accepts the exact ocean adapter output."""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        ocean_event = get_demo_ocean_event()
        response = client.post("/events", json=ocean_event.model_dump())
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["event"]["domain"], "ocean")
        self.assertEqual(data["event"]["event_type"], "potential_dark_vessel")
        self.assertEqual(data["classification"]["refined_type"], "possible_illegal_fishing")



if __name__ == "__main__":
    unittest.main()
