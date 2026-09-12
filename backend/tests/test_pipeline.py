import os
import sys
import unittest
from datetime import datetime, timezone
from pydantic import ValidationError

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adapters.fake_events import (
    generate_historical_events,
    generate_land_event,
    generate_ocean_event,
    generate_poaching_event,
)
from agents.action import determine_action
from agents.classifier import classify_event
from agents.human_gate import evaluate_human_supervision
from agents.localizer import localize_event
from agents.memory import retrieve_incident_memory
from agents.risk import assess_risk
from agents.verifier import verify_event
from database.firestore import db_client
from fastapi.testclient import TestClient
from main import app
from orchestrator.pipeline import approve_incident, process_event, reject_incident
from schemas.event import Location, NormalizedEvent


class TestEcoSentinelReasoningSystem(unittest.TestCase):

    def setUp(self) -> None:
        # Clear database before each test
        db_client.clear()

    # --- 1. Schema Validation Tests ---

    def test_schema_valid_event(self) -> None:
        event = NormalizedEvent(
            id="evt_test_001",
            domain="land",
            event_type="chainsaw",
            confidence=0.91,
            sensor_id="S07",
            location=Location(lat=12.9716, lon=77.5946),
            metadata={"test": True},
        )
        self.assertEqual(event.id, "evt_test_001")
        self.assertEqual(event.confidence, 0.91)
        self.assertEqual(event.location.lat, 12.9716)

    def test_schema_invalid_confidence_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            NormalizedEvent(
                id="evt_bad_conf",
                domain="land",
                event_type="chainsaw",
                confidence=1.45,  # Invalid: > 1.0
                sensor_id="S07",
                location=Location(lat=12.9716, lon=77.5946),
            )

        with self.assertRaises(ValidationError):
            NormalizedEvent(
                id="evt_bad_conf_neg",
                domain="land",
                event_type="chainsaw",
                confidence=-0.1,  # Invalid: < 0.0
                sensor_id="S07",
                location=Location(lat=12.9716, lon=77.5946),
            )

    def test_schema_invalid_coordinates_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            NormalizedEvent(
                id="evt_bad_lat",
                domain="land",
                event_type="chainsaw",
                confidence=0.8,
                sensor_id="S07",
                location=Location(lat=95.0, lon=77.5946),  # Invalid: > 90
            )

    # --- 2. Classification Agent Tests ---

    def test_land_classification(self) -> None:
        event = generate_land_event(event_type="chainsaw")
        res = classify_event(event)
        self.assertEqual(res.refined_type, "possible_logging")
        self.assertEqual(res.category, "illegal_logging")
        self.assertTrue(any("chainsaw" in r.lower() for r in res.reasons))

    def test_poaching_classification(self) -> None:
        event = generate_poaching_event()
        res = classify_event(event)
        self.assertEqual(res.refined_type, "possible_poaching")
        self.assertEqual(res.category, "wildlife_poaching")
        self.assertEqual(res.urgency, "critical")

    def test_ocean_classification(self) -> None:
        event = generate_ocean_event()
        res = classify_event(event)
        self.assertEqual(res.refined_type, "possible_illegal_fishing")
        self.assertEqual(res.category, "marine_violation")
        self.assertTrue(any("vessel" in r.lower() for r in res.reasons))

    # --- 3. Verification Agent Tests ---

    def test_verification_high_confidence_with_corroboration(self) -> None:
        event = generate_land_event(confidence=0.92, nearby_confirmations=2)
        res = verify_event(event)
        self.assertEqual(res.level, "high")
        self.assertGreaterEqual(res.score, 0.92)
        self.assertTrue(any("2 nearby sensors" in r for r in res.reasons))

    def test_verification_low_confidence(self) -> None:
        event = generate_land_event(confidence=0.45, nearby_confirmations=0)
        res = verify_event(event)
        self.assertEqual(res.level, "low")
        self.assertLess(res.score, 0.65)
        self.assertTrue(any("requires sensor corroboration" in r for r in res.reasons))

    # --- 4. Localization Agent Tests ---

    def test_localization_single_sensor(self) -> None:
        event = generate_land_event(lat=12.9716, lon=77.5946)
        res = localize_event(event)
        self.assertEqual(res.lat, 12.9716)
        self.assertEqual(res.lon, 77.5946)
        self.assertGreater(res.radius_meters, 0)

    def test_localization_multi_sensor_centroid(self) -> None:
        event = generate_land_event(
            lat=10.0,
            lon=20.0,
            extra_metadata={
                "multi_sensor_locations": [
                    {"lat": 10.0, "lon": 20.0},
                    {"lat": 10.2, "lon": 20.2},
                ]
            },
        )
        res = localize_event(event)
        self.assertAlmostEqual(res.lat, 10.1, places=3)
        self.assertAlmostEqual(res.lon, 20.1, places=3)
        self.assertTrue(any("centroid" in r.lower() for r in res.reasons))

    # --- 5. Memory & Recurrence Risk Escalation (Critical Demonstration) ---

    def test_memory_storage_and_retrieval(self) -> None:
        # Seed 2 events in same sector
        e1 = generate_land_event(custom_id="seed_01", lat=12.9716, lon=77.5946)
        process_event(e1)

        e2 = generate_land_event(custom_id="seed_02", lat=12.9720, lon=77.5949)
        process_event(e2)

        # Ingest 3rd event
        e3 = generate_land_event(custom_id="query_03", lat=12.9718, lon=77.5947)
        res = process_event(e3)

        self.assertEqual(res.memory.historical_events, 2)
        self.assertTrue(res.memory.recurrence_detected)
        self.assertEqual(len(res.memory.recent_incidents), 2)

    def test_recurrence_increases_risk_scenario_a_vs_b(self) -> None:
        """
        Scenario A: Single isolated chainsaw event.
        Scenario B: Same event after 3 previous incidents in the same cluster.
        Demonstrates that memory retrieval directly increases the risk score.
        """
        # Scenario A (Isolated)
        db_client.clear()
        event_a = generate_land_event(
            custom_id="evt_isolated",
            lat=12.9716,
            lon=77.5946,
            confidence=0.88,
            nearby_confirmations=1,
            protected_area=True,
            is_night=False,
        )
        res_a = process_event(event_a)
        score_a = res_a.risk.score
        hist_a = res_a.memory.historical_events
        self.assertEqual(hist_a, 0)
        self.assertFalse(res_a.memory.recurrence_detected)

        # Scenario B (Recurrent with 3 seeded prior incidents)
        db_client.clear()
        historical_events = generate_historical_events(
            domain="land",
            event_type="chainsaw",
            center_lat=12.9716,
            center_lon=77.5946,
            count=3,
        )
        for h_ev in historical_events:
            process_event(h_ev)

        event_b = generate_land_event(
            custom_id="evt_recurrent",
            lat=12.9716,
            lon=77.5946,
            confidence=0.88,
            nearby_confirmations=1,
            protected_area=True,
            is_night=False,
        )
        res_b = process_event(event_b)
        score_b = res_b.risk.score
        hist_b = res_b.memory.historical_events

        self.assertEqual(hist_b, 3)
        self.assertTrue(res_b.memory.recurrence_detected)
        # Recurrence must produce a meaningfully higher risk score!
        self.assertGreater(
            score_b,
            score_a,
            f"Expected score_b ({score_b}) to be higher than score_a ({score_a}) due to memory recurrence",
        )
        self.assertGreaterEqual(score_b - score_a, 15, "Recurrence should increase score by at least 15 points")
        self.assertEqual(res_b.risk.level, "HIGH")

    # --- 6. Human Supervision Gate & Action Dispatch Flow ---

    def test_human_gate_and_approval_flow(self) -> None:
        db_client.clear()
        # Seed to ensure HIGH risk
        hist_events = generate_historical_events(count=3)
        for ev in hist_events:
            process_event(ev)

        high_risk_event = generate_land_event(
            custom_id="evt_gate_test",
            confidence=0.95,
            nearby_confirmations=2,
            protected_area=True,
        )
        pipeline_res = process_event(high_risk_event)

        # Initially waiting for human approval
        self.assertTrue(pipeline_res.human_gate.requires_human)
        self.assertEqual(pipeline_res.human_gate.status, "WAITING_FOR_APPROVAL")
        self.assertEqual(pipeline_res.action.action, "ALERT_RANGER")
        self.assertFalse(pipeline_res.action.dispatched)

        # Call approve_incident
        approved_res = approve_incident(
            event_id="evt_gate_test",
            reviewer="chief_ranger_dan",
            notes="Ground team team Charlie dispatched to Sector 7",
        )
        self.assertIsNotNone(approved_res)
        self.assertFalse(approved_res.human_gate.requires_human)
        self.assertEqual(approved_res.human_gate.status, "APPROVED")
        self.assertTrue(approved_res.action.dispatched)
        self.assertTrue(any("chief_ranger_dan" in r for r in approved_res.action.reasons))

    def test_rejection_flow(self) -> None:
        db_client.clear()
        event = generate_land_event(custom_id="evt_reject_test", confidence=0.95)
        process_event(event)

        rejected_res = reject_incident(
            event_id="evt_reject_test",
            reviewer="operator_sarah",
            notes="Controlled forestry management activity authorized by permit",
        )
        self.assertIsNotNone(rejected_res)
        self.assertEqual(rejected_res.human_gate.status, "REJECTED")
        self.assertEqual(rejected_res.action.action, "CANCELLED")
        self.assertFalse(rejected_res.action.dispatched)

    # --- 7. Domain Pipelines (Land, Ocean, Poaching) ---

    def test_land_pipeline(self) -> None:
        event = generate_land_event()
        res = process_event(event)
        self.assertEqual(res.event.domain, "land")
        self.assertEqual(res.classification.refined_type, "possible_logging")
        self.assertIsNotNone(res.risk.score)

    def test_ocean_pipeline(self) -> None:
        event = generate_ocean_event()
        res = process_event(event)
        self.assertEqual(res.event.domain, "ocean")
        self.assertEqual(res.classification.refined_type, "possible_illegal_fishing")
        self.assertIn(res.action.action, ("TRACK_VESSEL", "REQUEST_MORE_EVIDENCE"))

    def test_poaching_pipeline(self) -> None:
        event = generate_poaching_event()
        res = process_event(event)
        self.assertEqual(res.event.domain, "land")
        self.assertEqual(res.classification.refined_type, "possible_poaching")
        self.assertEqual(res.action.action, "ALERT_RANGER")

    # --- 8. FastAPI Endpoints Integration ---

    def test_fastapi_endpoints(self) -> None:
        client = TestClient(app)

        # GET /
        resp = client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["system"], "EcoSentinel Reasoning Engine")

        # GET /health
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "healthy")

        # POST /demo/fake-land
        resp = client.get("/demo/fake-land") if False else client.post("/demo/fake-land")
        self.assertEqual(resp.status_code, 200)
        land_data = resp.json()
        self.assertEqual(land_data["event"]["domain"], "land")

        # POST /demo/fake-ocean
        resp = client.post("/demo/fake-ocean")
        self.assertEqual(resp.status_code, 200)
        ocean_data = resp.json()
        self.assertEqual(ocean_data["event"]["domain"], "ocean")

        # POST /demo/seed-recurrence
        resp = client.post("/demo/seed-recurrence")
        self.assertEqual(resp.status_code, 200)
        rec_data = resp.json()
        self.assertEqual(rec_data["historical_seeded_count"], 3)
        new_inc = rec_data["new_trigger_incident"]
        self.assertEqual(new_inc["memory"]["historical_events"], 3)
        self.assertTrue(new_inc["memory"]["recurrence_detected"])
        self.assertEqual(new_inc["risk"]["level"], "HIGH")

        # POST /events ingestion
        raw_event = {
            "id": "evt_api_test_01",
            "domain": "land",
            "event_type": "chainsaw",
            "confidence": 0.89,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sensor_id": "S_API_01",
            "location": {"lat": 12.9716, "lon": 77.5946},
            "metadata": {"protected_area": True},
        }
        resp = client.post("/events", json=raw_event)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["event"]["id"], "evt_api_test_01")

        # GET /events
        resp = client.get("/events")
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.json()), 0)

        # GET /events/{event_id}
        resp = client.get("/events/evt_api_test_01")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["event"]["id"], "evt_api_test_01")

        # POST /events/{event_id}/approve
        resp = client.post(
            "/events/evt_api_test_01/approve",
            json={"reviewer": "officer_judy", "notes": "Dispatched ground unit"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["human_gate"]["status"], "APPROVED")
        self.assertTrue(resp.json()["action"]["dispatched"])


if __name__ == "__main__":
    unittest.main()
