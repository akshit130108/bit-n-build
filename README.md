# EcoSentinel — Autonomous Ecological Defense Network

EcoSentinel is an autonomous, domain-agnostic agentic ecological defense and reasoning platform designed to monitor, detect, verify, evaluate, and respond to environmental threats across **Land** (acoustic chainsaw/gunshot logging detections) and **Ocean** (Global Fishing Watch AIS dark vessel & illegal fishing detections).

> **IMPORTANT DISCLAIMER:** EcoSentinel uses periodic polling of Global Fishing Watch data. It is not a zero-latency real-time vessel tracking system.

---

## 🏛️ System Architecture

EcoSentinel executes an 8-stage agentic reasoning trajectory for every detected event:

```
[ Sensor Signal / Telemetry Feed ]
               │
               ▼
   1. Detection & Normalization (NormalizedEvent schema)
               │
               ▼
   2. Threat Classification (Refined threat type & category)
               │
               ▼
   3. Sensor Verification (Cross-sensor trust score & level)
               │
               ▼
   4. Geographic Localization (Sector resolution & sanctuary check)
               │
               ▼
   5. Spatial-Temporal Memory (Recurrence cluster analysis)
               │
               ▼
   6. Risk Assessment (Multi-factor risk score 0-100)
               │
               ▼
   7. Human Supervision Gate (WAITING_FOR_APPROVAL vs AUTO_APPROVED)
               │
               ▼
   8. Action Dispatch (Ranger alert / vessel tracking dispatch)
```

---

## 🔑 Environment Variables & Security

Create a `backend/.env` file in the `backend/` directory:

```ini
# Global Fishing Watch (GFW) API v3 Token
GFW_API_TOKEN=your_gfw_api_token_here

# Background Ocean Polling Interval in Seconds (Default: 300)
OCEAN_POLL_INTERVAL_SECONDS=300

# Background Ocean Polling Mode ('auto', 'live', or 'simulated')
OCEAN_POLL_MODE=auto

# Optional: Firebase / Firestore Service Account Key Path (Default: in-memory store)
# FIREBASE_KEY_PATH=firebase-key.json
```

> **Security Guarantee:** Secrets and API keys are stored strictly in `backend/.env` (git-ignored) and are never exposed via API endpoints, logs, frontend bundles, or error tracebacks.

---

## 💻 Developer Quickstart

### 1. Run Backend Server (FastAPI)

```bash
cd backend
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Backend API will be live at: `http://localhost:8000`  
Swagger API Docs: `http://localhost:8000/docs`

### 2. Run Frontend Dashboard (React + Leaflet + Vite)

```bash
cd frontend
npm install
npm run dev
```
Dashboard will be live at: `http://localhost:5173`

---

## 🧪 Testing & Verification

### Run Complete Unit Test Suite (69 Tests)

```bash
cd backend
python -m unittest discover tests -v
```

### Run End-to-End Live GFW Smoke Test

```bash
python scratch/smoke_test.py
```

---

## 🛰️ Demonstration Scenarios

### Scenario A — Real Live Data Ingestion
1. Ensure `GFW_API_TOKEN` is configured in `backend/.env`.
2. Trigger automated polling or call `POST /ingest/ocean?mode=live&limit=5` (or click **"🔄 Ingest GFW Now"** in dashboard).
3. The dashboard displays `📡 LIVE GFW API DATA` with genuine vessel MMSI/ID, flag state, AIS gap evidence, and 30-day UTC window timestamps.

### Scenario B — High-Risk Governance & Human Gate (Dark Vessel)
1. Click **"⚓ Simulate Dark Vessel"** on the dashboard header (or post to `POST /demo/fake-ocean`).
2. The simulated dark vessel exhibits extended AIS gaps in a marine sanctuary (Galapagos Marine Reserve), triggering a **HIGH Risk score (80/100+)**.
3. The Human Supervision Gate locks the incident in `WAITING_FOR_APPROVAL`.
4. Click **"✓ APPROVE & DISPATCH"** or **"✕ REJECT"** to execute governance clearance.

### Scenario C — Ballistic Gunshot Wildlife Poaching
1. Click **"💥 Simulate Gunshot"** on the dashboard header (or post to `POST /demo/fake-poaching`).
2. Acoustic sensor nodes detect high-frequency ballistic impulses matching high-caliber rifle fire in a rhino sanctuary.
3. Risk surges to `92/100 (CRITICAL)`, automatically recommending armed anti-poaching patrol deployment with human authorization.

### Scenario D — Spatial-Temporal Recurrence Spike
1. Click **"🚨 Seed Recurrence Spike"** on the dashboard header (or post to `POST /demo/seed-recurrence`).
2. Seeds 3 historical logging incidents in Sector-7; the 4th detection identifies spatial clustering.
3. Risk score surges to `CRITICAL` via Memory Agent recurrence scoring, escalating to `WAITING_FOR_APPROVAL`.

---

## 📋 API Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health status check |
| `POST` | `/events` | Primary entrypoint: processes a `NormalizedEvent` through the 8-stage pipeline |
| `GET` | `/events` | List all processed incidents (supports domain & risk filters) |
| `GET` | `/events/{id}` | Retrieve detailed incident dossier by ID |
| `POST` | `/events/{id}/approve` | Human operator approval & action dispatch |
| `POST` | `/events/{id}/reject` | Human operator rejection & action cancellation |
| `POST` | `/events/{id}/request-more-evidence` | Request auxiliary sensor evidence before action |
| `POST` | `/ingest/ocean` | Manually trigger ocean GFW ingestion (`live`, `simulated`, or `auto`) |
| `GET` | `/ingest/ocean/status` | Query background poller health & telemetry metrics |
| `POST` | `/demo/fake-land` | Simulate acoustic logging chainsaw detection |
| `POST` | `/demo/fake-ocean` | Simulate high-risk dark vessel incident in sanctuary |
| `POST` | `/demo/fake-poaching` | Simulate ballistic gunshot wildlife poaching event |
| `POST` | `/demo/live-ocean` | Trigger immediate on-demand ocean ingestion cycle |
| `POST` | `/demo/seed-recurrence` | Demonstrate spatial-temporal recurrence risk surge |

---

## 🚀 Deployment

For production deployment instructions on Render or Vercel, please see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## ⚠️ Known Limitations

* **Periodic Polling**: GFW API data is retrieved via background polling cycles (default 300s) to observe API rate limits.
* **Storage Provider**: Default configuration uses an in-memory store for fast local development; set `FIREBASE_KEY_PATH` to enable Firestore cloud persistence.
