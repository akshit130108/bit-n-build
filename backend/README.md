# EcoSentinel Backend - Shared Reasoning Pipeline (Person 3)

EcoSentinel is an agentic ecological monitoring and response system. This repository contains **Person 3's shared reasoning pipeline**—a domain-agnostic reasoning backend that normalizes heterogeneous sensory events (land audio, vision, ocean AIS, satellite) and processes them through an interpretable 9-stage agentic workflow.

---

## Architecture & Reasoning Pipeline

```
Normalized Event Ingestion (Audio / Vision / AIS / Sensors)
           │
           ▼
[1] Classification Refinement (agents/classifier.py)
           │
           ▼
[2] Verification Agent (agents/verifier.py)
           │
           ▼
[3] Localization Agent (agents/localizer.py)
           │
           ▼
[4] Spatial-Temporal Memory (agents/memory.py + database/firestore.py)
           │
           ▼
[5] Multi-Factor Risk Assessment (agents/risk.py)
           │
           ▼
[6] Human Supervision Gate (agents/human_gate.py)
           │
           ▼
[7] Action Recommendation Agent (agents/action.py)
           │
           ▼
[8] Incident Persistence (Firestore / In-Memory Store)
           │
           ▼
Client Response & React Dashboard Feed
```

### Agent Roles

1. **Classification Agent** (`agents/classifier.py`): Refines raw acoustic/optical signatures into structured ecological threats (e.g. `land` + `chainsaw` $\to$ `possible_logging`; `land` + `gunshot` $\to$ `possible_poaching`; `ocean` + `suspicious_vessel` $\to$ `possible_illegal_fishing`).
2. **Verification Agent** (`agents/verifier.py`): Evaluates signal integrity, confidence score, SNR, and multi-sensor corroboration (`nearby_confirmations`).
3. **Localization Agent** (`agents/localizer.py`): Maps coordinates to operational sectors and calculates centroid/accuracy radius.
4. **Memory Agent** (`agents/memory.py`): Queries Firestore/in-memory store for previous incidents in the sector over a sliding temporal window (48h) to detect persistent hot-spots and recurrence patterns.
5. **Risk Agent** (`agents/risk.py`): Computes a transparent 0–100 risk score and categorical level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) using base threat severity, verification confidence, protected reserve status, clandestine timing, and **historical recurrence weight**.
6. **Human Supervision Gate** (`agents/human_gate.py`): Safety policy checkpoint requiring human approval before dispatching high-consequence conservation actions (e.g., ground ranger deployments).
7. **Action Agent** (`agents/action.py`): Recommends simulated non-lethal ecological conservation responses (`ALERT_RANGER`, `TRACK_VESSEL`, `REQUEST_MORE_EVIDENCE`, `CONTINUE_MONITORING`).

---

## Project Structure

```
backend/
├── main.py                     # FastAPI application & REST endpoints
├── demo.py                     # Interactive CLI demonstration
├── requirements.txt            # Python dependencies
├── README.md                   # System documentation
├── .gitignore                  # Git ignore rules
├── schemas/                    # Pydantic data schemas
│   ├── __init__.py
│   └── event.py                # NormalizedEvent & agent models
├── agents/                     # Independent reasoning agents
│   ├── __init__.py
│   ├── classifier.py
│   ├── verifier.py
│   ├── localizer.py
│   ├── memory.py
│   ├── risk.py
│   ├── human_gate.py
│   └── action.py
├── orchestrator/               # Reasoning coordinator
│   ├── __init__.py
│   └── pipeline.py
├── adapters/                   # Simulated sensor generators
│   ├── __init__.py
│   └── fake_events.py
├── database/                   # Firestore & in-memory fallback
│   ├── __init__.py
│   └── firestore.py
└── tests/                      # Automated test suite
    ├── __init__.py
    └── test_pipeline.py
```

---

## Quick Start

### 1. Installation

```bash
cd backend
pip install -r requirements.txt
```

### 2. Run Automated Tests

Execute the 18 automated unit and integration tests:

```bash
python -m unittest tests/test_pipeline.py
```

### 3. Run the CLI Demo

Witness the entire reasoning progression, memory recurrence spike, and human approval flow directly in your terminal:

```bash
python demo.py
```

### 4. Start the FastAPI Server

```bash
uvicorn main:app --reload --port 8000
```

Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

---

## Firebase Configuration

The backend supports **Google Firebase Firestore** seamlessly:

1. Place your service account key file as `firebase-key.json` in the `backend/` directory, OR set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable.
2. If credentials are not present, the system **automatically falls back to high-performance in-memory storage**.
3. All secrets are ignored in `.gitignore`.

---

## Integration Guide for Teammates

### For Person 1 (Land / Audio ML Adapter)

Send detected audio events (e.g. chainsaw, gunshot) to `POST /events`:

```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "id": "evt_audio_001",
    "domain": "land",
    "event_type": "chainsaw",
    "confidence": 0.91,
    "timestamp": "2026-09-12T10:30:00Z",
    "sensor_id": "AUDIO_S07",
    "location": {
      "lat": 12.9716,
      "lon": 77.5946
    },
    "metadata": {
      "nearby_confirmations": 2,
      "protected_area": true,
      "snr_db": 18.5
    }
  }'
```

### For Person 2 (Ocean / AIS / Other Adapters)

Send marine or external sensor detections to `POST /events`:

```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "id": "evt_ais_002",
    "domain": "ocean",
    "event_type": "suspicious_vessel",
    "confidence": 0.88,
    "timestamp": "2026-09-12T10:35:00Z",
    "sensor_id": "AIS_BUOY_04",
    "location": {
      "lat": -0.5000,
      "lon": -90.5000
    },
    "metadata": {
      "ais_disabled": true,
      "speed_knots": 3.4,
      "protected_area": true,
      "nearby_confirmations": 1
    }
  }'
```

### For Person 4 (React/Vite + Leaflet Dashboard)

- **CORS** is already configured for `http://localhost:5173`.
- **Fetch Active Incidents**: `GET /events`
- **Filter Incidents**: `GET /events?domain=land&risk_level=HIGH`
- **Get Incident Details**: `GET /events/{event_id}`
- **Approve High-Risk Alert**:
  ```bash
  POST /events/{event_id}/approve
  Body: { "reviewer": "ranger_dan", "notes": "Ground team mobilized" }
  ```
- **Reject Alert**:
  ```bash
  POST /events/{event_id}/reject
  Body: { "reviewer": "ranger_dan", "notes": "Authorized forestry operation" }
  ```
- **Trigger Quick Demo Scenarios**:
  - `POST /demo/seed-recurrence`: Demonstrates historical spatial-temporal recurrence risk surge.
  - `POST /demo/fake-land`: Ingests simulated chainsaw event.
  - `POST /demo/fake-ocean`: Ingests simulated dark vessel event.

---

## Example Pipeline Response (`PipelineResult`)

```json
{
  "event": {
    "id": "evt_land_c84e4bac",
    "domain": "land",
    "event_type": "chainsaw",
    "confidence": 0.92,
    "timestamp": "2026-09-12T10:30:00Z",
    "sensor_id": "S07_HOTSPOT",
    "location": { "lat": 12.9718, "lon": 77.5948 },
    "metadata": { "nearby_confirmations": 2, "protected_area": true }
  },
  "classification": {
    "refined_type": "possible_logging",
    "category": "illegal_logging",
    "urgency": "high",
    "reasons": ["Acoustic signature 'chainsaw' on land indicates mechanized timber felling"]
  },
  "verification": {
    "level": "high",
    "score": 0.99,
    "reasons": ["High-confidence detection (92%)", "Confirmed by 2 nearby sensors"]
  },
  "localization": {
    "lat": 12.9718,
    "lon": 77.5948,
    "confidence": 0.85,
    "radius_meters": 250.0,
    "sector_name": "Sector-29",
    "reasons": ["Direct coordinates from sensor S07_HOTSPOT"]
  },
  "memory": {
    "historical_events": 3,
    "recurrence_detected": true,
    "recent_incidents": [...],
    "reasons": [
      "Detected 3 previous incident(s) of 'chainsaw' within 15.0km over the past 48h",
      "Sustained pattern in Sector-29: Multiple recurring violations indicate organized activity"
    ]
  },
  "risk": {
    "score": 94,
    "level": "HIGH",
    "reasons": [
      "High-impact resource extraction threat type",
      "High verification confidence (0.99)",
      "Location is inside a designated Protected Ecological Reserve",
      "Repeated activity in the same sector (3 previous incidents)"
    ],
    "factors": {
      "base_threat": 25,
      "evidence_score": 25,
      "ecological_sensitivity": 20,
      "nighttime_factor": 0,
      "historical_recurrence": 24
    }
  },
  "human_gate": {
    "requires_human": true,
    "status": "WAITING_FOR_APPROVAL",
    "reasons": [
      "HIGH risk incident (94/100) mandates human operator approval before dispatching field rangers"
    ]
  },
  "action": {
    "action": "ALERT_RANGER",
    "message": "Ranger patrol alert recommended for suspected illegal logging operations.",
    "requires_approval": true,
    "dispatched": false,
    "reasons": [
      "Recurrent timber extraction activity detected; ground patrol dispatch prepared",
      "Action is held in pending status awaiting human operator clearance"
    ]
  }
}
```
