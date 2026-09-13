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

    # Formulate Targeted Acoustic Countermeasure (Bio-Acoustic Defense)
    countermeasure = None
    if "poaching" in refined or event.event_type == "gunshot":
        countermeasure = {
            "type": "DIRECTIONAL_ACOUSTIC_DETERRENT",
            "name": "Directional High-Intensity Sonic Warning Pulse",
            "target_node": event.sensor_id or "ACOUSTIC_NODE_12",
            "frequency_hz": "3,200 Hz High-Decibel Warning Strobe",
            "intensity_db": "125 dB Directional Pulse",
            "broadcast_message": "Automated Warning: You are inside a protected wildlife reserve. Acoustic triangulation locked. Ranger intercept unit alerted.",
            "autonomous_status": "ARMED (Pending Human Gate Clearance)" if requires_approval else "AUTONOMOUSLY DEPLOYED",
        }
        reasons.append("Targeted acoustic countermeasure armed: 125 dB directional sonic deterrent queued for localized sector")
    elif "logging" in refined or event.event_type == "chainsaw":
        countermeasure = {
            "type": "ACOUSTIC_INTERDICTION_SIREN",
            "name": "Bio-Acoustic Interdiction Audio Beacon",
            "target_node": event.sensor_id or "ACOUSTIC_NODE_S07",
            "frequency_hz": "1,800 - 2,500 Hz Sweeping Siren",
            "intensity_db": "115 dB Area Broadcast",
            "broadcast_message": "Warning: Unauthorized forestry activity detected by Bio-Acoustic Sensor Mesh. Vacate sector immediately.",
            "autonomous_status": "ARMED (Pending Human Gate Clearance)" if requires_approval else "AUTONOMOUSLY DEPLOYED",
        }
        reasons.append("Targeted acoustic countermeasure armed: 115 dB interdiction siren targeted at logging coordinates")
    elif "invasive" in refined or "invasive" in event.event_type:
        countermeasure = {
            "type": "BIOACOUSTIC_DISPERSAL_PLAYBACK",
            "name": "Targeted Predator Bio-Acoustic Dispersal Call",
            "target_node": event.sensor_id or "BIO_SENSOR_03",
            "frequency_hz": "18.5 kHz Ultrasound / Predator Vocalization",
            "intensity_db": "95 dB Targeted Scatter",
            "broadcast_message": "Autonomous bio-acoustic playback active: synthesizing territorial predator distress call to scatter invasive species.",
            "autonomous_status": "AUTONOMOUSLY DEPLOYED",
        }
        reasons.append("Autonomous bio-acoustic countermeasure deployed: predator playback activated to disperse invasive species")
    elif domain == "ocean":
        countermeasure = {
            "type": "UNDERWATER_ACOUSTIC_HAILING",
            "name": "Marine Sanctuary Acoustic Transponder Hail",
            "target_node": event.sensor_id or "HYDROPHONE_BUOY_04",
            "frequency_hz": "37.5 kHz Hydrophone Ping / VHF Hail",
            "intensity_db": "160 dB Underwater Pulse",
            "broadcast_message": "Notice to Mariners: Vessel transiting restricted Marine Protected Area. AIS reactivation mandatory.",
            "autonomous_status": "AUTONOMOUSLY DEPLOYED",
        }
        reasons.append("Targeted marine acoustic hail transmitted via hydrophone transducer network")

    if requires_approval:
        reasons.append("Action is held in pending status awaiting human operator clearance")
    else:
        reasons.append("Action executed automatically under routine monitoring protocol")

    return ActionResult(
        action=action,
        message=message,
        requires_approval=requires_approval,
        dispatched=dispatched,
        countermeasure=countermeasure,
        reasons=reasons,
    )
