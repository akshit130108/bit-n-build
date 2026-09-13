from datetime import datetime, timezone
from typing import Optional

from agents.action import determine_action
from agents.classifier import classify_event
from agents.human_gate import evaluate_human_supervision
from agents.localizer import localize_event
from agents.memory import retrieve_incident_memory
from agents.risk import assess_risk
from agents.verifier import verify_event
from database.firestore import db_client
from schemas.event import NormalizedEvent, PipelineResult


def process_event(event: NormalizedEvent) -> PipelineResult:
    """
    EcoSentinel Core Reasoning Orchestrator:
    Coordinates the 9-stage domain-agnostic ecological reasoning pipeline.
    """
    # 1. Classification Refinement
    classification = classify_event(event)

    # 2. Verification
    verification = verify_event(event)

    # 3. Localization
    localization = localize_event(event)

    # 4. Spatial-Temporal Memory Retrieval
    memory = retrieve_incident_memory(event, classification, localization)

    # 5. Multi-factor Risk Assessment
    risk = assess_risk(event, classification, verification, memory)

    # 6. Human Supervision Gate
    human_gate = evaluate_human_supervision(event, risk)

    # 7. Action Recommendation
    action = determine_action(event, classification, verification, risk, human_gate)

    # 8. Assemble Pipeline Result
    now_iso = datetime.now(timezone.utc).isoformat()
    pipeline_result = PipelineResult(
        event=event,
        classification=classification,
        verification=verification,
        localization=localization,
        memory=memory,
        risk=risk,
        human_gate=human_gate,
        action=action,
        created_at=now_iso,
        updated_at=now_iso,
    )

    # 9. Store Processed Incident into Memory / Firestore
    db_client.save_incident(pipeline_result.model_dump())

    return pipeline_result


def approve_incident(
    event_id: str,
    reviewer: str = "ranger_supervisor",
    notes: Optional[str] = None,
) -> Optional[PipelineResult]:
    """Approve a pending high-risk incident and dispatch the recommended action."""
    incident_dict = db_client.get_incident(event_id)
    if not incident_dict:
        return None

    # Update Human Gate status
    incident_dict["human_gate"]["status"] = "APPROVED"
    incident_dict["human_gate"]["requires_human"] = False
    incident_dict["human_gate"]["reasons"].append(
        f"Approved by {reviewer}: {notes or 'Authorized operational response dispatch'}"
    )

    # Dispatch Action
    incident_dict["action"]["dispatched"] = True
    if incident_dict["action"].get("countermeasure"):
        incident_dict["action"]["countermeasure"]["autonomous_status"] = "DEPLOYED & TRANSMITTING"
    incident_dict["action"]["reasons"].append(
        f"Operational action confirmed and dispatched by {reviewer}"
    )
    incident_dict["updated_at"] = datetime.now(timezone.utc).isoformat()

    db_client.update_incident(event_id, incident_dict)
    return PipelineResult.model_validate(incident_dict)


def reject_incident(
    event_id: str,
    reviewer: str = "ranger_supervisor",
    notes: Optional[str] = None,
) -> Optional[PipelineResult]:
    """Reject a pending incident, preventing action dispatch and recording operator reason."""
    incident_dict = db_client.get_incident(event_id)
    if not incident_dict:
        return None

    incident_dict["human_gate"]["status"] = "REJECTED"
    incident_dict["human_gate"]["requires_human"] = False
    incident_dict["human_gate"]["reasons"].append(
        f"Dismissed by {reviewer}: {notes or 'False positive or non-actionable detection'}"
    )

    incident_dict["action"]["dispatched"] = False
    incident_dict["action"]["action"] = "CANCELLED"
    if incident_dict["action"].get("countermeasure"):
        incident_dict["action"]["countermeasure"]["autonomous_status"] = "DISARMED / CANCELLED"
    incident_dict["action"]["message"] = f"Action cancelled following human review: {notes or 'Dismissed'}"
    incident_dict["updated_at"] = datetime.now(timezone.utc).isoformat()

    db_client.update_incident(event_id, incident_dict)
    return PipelineResult.model_validate(incident_dict)


def request_evidence_incident(
    event_id: str,
    reviewer: str = "ranger_supervisor",
    notes: Optional[str] = None,
) -> Optional[PipelineResult]:
    """Flag incident as requesting additional secondary sensor/drone evidence."""
    incident_dict = db_client.get_incident(event_id)
    if not incident_dict:
        return None

    incident_dict["human_gate"]["status"] = "REQUEST_MORE_EVIDENCE"
    incident_dict["human_gate"]["reasons"].append(
        f"Additional evidence requested by {reviewer}: {notes or 'Awaiting sensor/camera trap confirmation'}"
    )

    incident_dict["action"]["action"] = "REQUEST_MORE_EVIDENCE"
    incident_dict["action"]["message"] = f"Awaiting supplementary evidence before dispatch: {notes or 'Inspection initiated'}"
    incident_dict["updated_at"] = datetime.now(timezone.utc).isoformat()

    db_client.update_incident(event_id, incident_dict)
    return PipelineResult.model_validate(incident_dict)
