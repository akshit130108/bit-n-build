from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from adapters.fake_events import (
    generate_historical_events,
    generate_land_event,
    generate_ocean_event,
)
from adapters.ocean_scheduler import ocean_scheduler
from database.firestore import db_client
from orchestrator.pipeline import (
    approve_incident,
    process_event,
    reject_incident,
    request_evidence_incident,
)
from schemas.event import ApprovalRequest, NormalizedEvent, PipelineResult


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background ocean ingestion scheduler safely without duplicates
    ocean_scheduler.start()
    yield
    # Shutdown: Stop worker cleanly
    ocean_scheduler.stop()


app = FastAPI(
    title="EcoSentinel Reasoning Pipeline API",
    description="Person 3's shared, domain-agnostic agentic ecological reasoning backend for EcoSentinel.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Person 4's React/Vite + Leaflet dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["System"])
def root() -> Dict[str, Any]:
    return {
        "system": "EcoSentinel Reasoning Engine",
        "role": "Person 3 Shared Pipeline",
        "status": "operational",
        "storage_backend": db_client.backend_type,
        "docs_url": "/docs",
        "dashboard_url": "/dashboard",
    }


@app.get("/health", tags=["System"])
def health() -> Dict[str, Any]:
    incidents = db_client.list_incidents(limit=1000)
    return {
        "status": "healthy",
        "storage_backend": db_client.backend_type,
        "total_incidents_stored": len(incidents),
    }


@app.post(
    "/events",
    response_model=PipelineResult,
    status_code=status.HTTP_201_CREATED,
    tags=["Events"],
    summary="Ingest a normalized event and execute the 9-stage agentic reasoning pipeline",
)
def ingest_event(event: NormalizedEvent) -> PipelineResult:
    try:
        result = process_event(event)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Pipeline execution error: {str(e)}")


@app.post(
    "/ingest/ocean",
    tags=["Ingestion"],
    summary="Trigger automated ingestion from GFW Ocean API to Person 3 pipeline with deduplication",
)
def trigger_ocean_ingestion(
    mode: str = Query(default="auto", description="Data mode: 'auto', 'live', or 'simulated'"),
    limit: int = Query(default=10, ge=1, le=50, description="Max events to fetch"),
) -> Dict[str, Any]:
    from adapters.ocean_ingest import ingest_ocean_events
    try:
        return ingest_ocean_events(mode=mode, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocean ingestion error: {str(e)}")


@app.get(
    "/ingest/ocean/status",
    tags=["Ingestion"],
    summary="Get status and metrics of the automated ocean background ingestion scheduler",
)
def get_ocean_ingest_status() -> Dict[str, Any]:
    return ocean_scheduler.get_status()


@app.get("/events", response_model=List[Dict[str, Any]], tags=["Events"], summary="List processed ecological incidents")
def list_events(
    limit: int = Query(default=50, ge=1, le=200),
    domain: Optional[str] = Query(default=None, description="Filter by domain (land, ocean)"),
    risk_level: Optional[str] = Query(default=None, description="Filter by risk level (LOW, MEDIUM, HIGH, CRITICAL)"),
    status: Optional[str] = Query(default=None, description="Filter by status (WAITING_FOR_APPROVAL, AUTO_APPROVED, APPROVED, REJECTED)"),
) -> List[Dict[str, Any]]:
    return db_client.list_incidents(limit=limit, domain=domain, risk_level=risk_level, status=status)


@app.get("/events/{event_id}", response_model=Dict[str, Any], tags=["Events"], summary="Get detailed incident record by ID")
def get_event(event_id: str) -> Dict[str, Any]:
    incident = db_client.get_incident(event_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident with ID '{event_id}' not found")
    return incident


@app.post(
    "/events/{event_id}/approve",
    response_model=PipelineResult,
    tags=["Human Supervision"],
    summary="Approve pending high-risk incident and dispatch recommended action",
)
def approve_event(event_id: str, request: ApprovalRequest = ApprovalRequest()) -> PipelineResult:
    result = approve_incident(event_id=event_id, reviewer=request.reviewer, notes=request.notes)
    if not result:
        raise HTTPException(status_code=404, detail=f"Incident with ID '{event_id}' not found")
    return result


@app.post(
    "/events/{event_id}/reject",
    response_model=PipelineResult,
    tags=["Human Supervision"],
    summary="Reject incident recommendation and cancel action dispatch",
)
def reject_event(event_id: str, request: ApprovalRequest = ApprovalRequest()) -> PipelineResult:
    result = reject_incident(event_id=event_id, reviewer=request.reviewer, notes=request.notes)
    if not result:
        raise HTTPException(status_code=404, detail=f"Incident with ID '{event_id}' not found")
    return result


@app.post(
    "/events/{event_id}/request-more-evidence",
    response_model=PipelineResult,
    tags=["Human Supervision"],
    summary="Request supplementary evidence (camera trap / auxiliary sensor) before decision",
)
def request_more_evidence(event_id: str, request: ApprovalRequest = ApprovalRequest()) -> PipelineResult:
    result = request_evidence_incident(event_id=event_id, reviewer=request.reviewer, notes=request.notes)
    if not result:
        raise HTTPException(status_code=404, detail=f"Incident with ID '{event_id}' not found")
    return result


@app.post("/demo/fake-land", response_model=PipelineResult, tags=["Demo"], summary="Simulate a real-time land chainsaw event")
def demo_fake_land() -> PipelineResult:
    event = generate_land_event()
    return process_event(event)


@app.post("/demo/fake-ocean", response_model=PipelineResult, tags=["Demo"], summary="Simulate a real-time ocean suspicious vessel event")
def demo_fake_ocean() -> PipelineResult:
    event = generate_ocean_event()
    return process_event(event)


@app.post(
    "/demo/seed-recurrence",
    tags=["Demo"],
    summary="Seed 3 historical chainsaw events in Sector-7, then process a 4th event demonstrating risk surge",
)
def demo_seed_recurrence(clear_first: bool = Query(default=True, description="Clear existing incidents first for a fresh demo run")) -> Dict[str, Any]:
    if clear_first:
        db_client.clear()

    # 1. Seed 3 historical events into the database
    historical_events = generate_historical_events(
        domain="land",
        event_type="chainsaw",
        center_lat=12.9716,
        center_lon=77.5946,
        count=3,
        time_span_hours=12,
    )
    seeded_ids = []
    for hist_ev in historical_events:
        res = process_event(hist_ev)
        seeded_ids.append(res.event.id)

    # 2. Trigger a 4th new event in the exact same sector
    new_event = generate_land_event(
        event_type="chainsaw",
        confidence=0.92,
        sensor_id="S07_HOTSPOT",
        lat=12.9718,
        lon=77.5948,
        nearby_confirmations=2,
        protected_area=True,
    )
    result = process_event(new_event)

    return {
        "scenario": "Historical Spatial-Temporal Recurrence Spike",
        "historical_seeded_count": len(seeded_ids),
        "seeded_incident_ids": seeded_ids,
        "new_trigger_incident": result,
        "demonstration_takeaway": (
            f"Risk score surged to {result.risk.score}/100 ({result.risk.level}) because {result.memory.historical_events} "
            f"historical incidents were retrieved in Sector-7. Human gate triggered status {result.human_gate.status}."
        ),
    }


# Mount built React dashboard at /dashboard if frontend/dist exists
import os
from fastapi.staticfiles import StaticFiles

frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/dashboard", StaticFiles(directory=frontend_dist, html=True), name="dashboard")

