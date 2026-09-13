import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class Location(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")


class NormalizedEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}", description="Unique event identifier")
    domain: str = Field(..., description="Sensor/ecological domain, e.g. land, ocean")
    event_type: str = Field(..., description="Raw detected type, e.g. chainsaw, gunshot, suspicious_vessel")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 formatted timestamp"
    )
    sensor_id: str = Field(..., min_length=1, description="Sensor identifier, e.g. S07")
    location: Location
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary domain-specific metadata")

    @field_validator("domain", "event_type")
    @classmethod
    def normalize_strings(cls, value: str) -> str:
        return value.strip().lower()


class ClassificationResult(BaseModel):
    refined_type: str
    category: str
    urgency: str
    reasons: List[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    level: str  # "high", "medium", "low"
    score: float = Field(..., ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)


class LocalizationResult(BaseModel):
    lat: float
    lon: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    radius_meters: float
    sector_name: str
    reasons: List[str] = Field(default_factory=list)


class MemoryResult(BaseModel):
    historical_events: int
    recurrence_detected: bool
    recent_incidents: List[Dict[str, Any]] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)


class RiskAssessmentResult(BaseModel):
    score: int = Field(..., ge=0, le=100)
    level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    reasons: List[str] = Field(default_factory=list)
    factors: Dict[str, Any] = Field(default_factory=dict)


class HumanGateResult(BaseModel):
    requires_human: bool
    status: str  # "WAITING_FOR_APPROVAL", "AUTO_APPROVED", "REQUEST_MORE_EVIDENCE", "APPROVED", "REJECTED"
    reasons: List[str] = Field(default_factory=list)


class ActionResult(BaseModel):
    action: str  # "ALERT_RANGER", "TRACK_VESSEL", "REQUEST_MORE_EVIDENCE", "CONTINUE_MONITORING"
    message: str
    requires_approval: bool
    dispatched: bool = False
    countermeasure: Optional[Dict[str, Any]] = None
    reasons: List[str] = Field(default_factory=list)


class PipelineResult(BaseModel):
    event: NormalizedEvent
    classification: ClassificationResult
    verification: VerificationResult
    localization: LocalizationResult
    memory: MemoryResult
    risk: RiskAssessmentResult
    human_gate: HumanGateResult
    action: ActionResult
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ApprovalRequest(BaseModel):
    reviewer: str = Field(default="ranger_supervisor", description="Name/ID of the human operator")
    notes: Optional[str] = Field(default=None, description="Operational notes or reason for decision")
