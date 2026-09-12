from schemas.event import (
    ActionResult,
    ClassificationResult,
    HumanGateResult,
    NormalizedEvent,
    RiskAssessmentResult,
    VerificationResult,
)


def determine_action(
    event: NormalizedEvent,
    classification: ClassificationResult,
    verification: VerificationResult,
    risk: RiskAssessmentResult,
    human_gate: HumanGateResult,
) -> ActionResult:
    """
    Action Agent: Recommends non-lethal ecological conservation responses
    based on domain, threat classification, verification, risk, and human approval status.
    """
    domain = event.domain.lower()
    refined = classification.refined_type
    reasons = []

    # High / Critical risk actions
    if risk.level in ("HIGH", "CRITICAL"):
        if domain == "land":
            if "poaching" in refined:
                action = "ALERT_RANGER"
                message = "High-priority anti-poaching patrol dispatch recommended for immediate sector intercept."
                reasons.append("Critical gunshot acoustic signature necessitates rapid terrestrial ranger alert")
            else:
                action = "ALERT_RANGER"
                message = "Ranger patrol alert recommended for suspected illegal logging operations."
                reasons.append("Recurrent timber extraction activity detected; ground patrol dispatch prepared")
        elif domain == "ocean":
            action = "TRACK_VESSEL"
            message = "Automated satellite AIS tracking and marine sanctuary patrol vessel alert initiated."
            reasons.append("Unidentified vessel in restricted marine zone; persistent radar and AIS tracking queued")
        else:
            action = "ALERT_RANGER"
            message = "Ecological conservation alert recommended for critical habitat threat."
            reasons.append("Cross-domain critical threat response")

    # Medium risk actions
    elif risk.level == "MEDIUM":
        if domain == "ocean":
            action = "REQUEST_MORE_EVIDENCE"
            message = "Requesting synthetic aperture radar (SAR) satellite pass and coastal AIS corroboration."
            reasons.append("Medium risk marine signature requires secondary sensor confirmation")
        else:
            action = "REQUEST_MORE_EVIDENCE"
            message = "Requesting automated camera trap snapshot and auxiliary acoustic verification."
            reasons.append("Moderate risk terrestrial signature: requesting camera and acoustic cross-validation")

    # Low risk actions
    else:
        action = "CONTINUE_MONITORING"
        message = "Low ecological threat level. Continue standard passive sensor surveillance."
        reasons.append("Detection within normal baseline parameters; no intervention required")

    requires_approval = human_gate.requires_human
    # Consequential actions requiring approval cannot be dispatched autonomously
    dispatched = False if requires_approval else True

    if requires_approval:
        reasons.append("Action is held in pending status awaiting human operator clearance")
    else:
        reasons.append("Action executed automatically under routine monitoring protocol")

    return ActionResult(
        action=action,
        message=message,
        requires_approval=requires_approval,
        dispatched=dispatched,
        reasons=reasons,
    )
