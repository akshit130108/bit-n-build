from schemas.event import NormalizedEvent, VerificationResult


def verify_event(event: NormalizedEvent) -> VerificationResult:
    """
    Verification Agent: Evaluates signal integrity, model confidence,
    and multi-sensor corroboration to determine trustworthiness.
    """
    raw_conf = event.confidence
    metadata = event.metadata or {}
    reasons = []

    nearby_confirms = metadata.get("nearby_confirmations", 0)
    snr = metadata.get("snr_db")
    cross_modal = metadata.get("cross_modal_match", False)

    # Base verification score initialized from model confidence
    score = raw_conf

    # Evaluate raw confidence level
    if raw_conf >= 0.85:
        reasons.append(f"High-confidence detection ({int(raw_conf * 100)}%)")
    elif raw_conf >= 0.65:
        reasons.append(f"Moderate-confidence detection ({int(raw_conf * 100)}%)")
    else:
        reasons.append(f"Low-confidence raw detection ({int(raw_conf * 100)}%) requires sensor corroboration")

    # Corroborating evidence evaluation
    if nearby_confirms > 0:
        boost = min(0.15, nearby_confirms * 0.05)
        score = min(0.99, score + boost)
        sensor_word = "sensor" if nearby_confirms == 1 else "sensors"
        reasons.append(f"Confirmed by {nearby_confirms} nearby {sensor_word}")
    else:
        if raw_conf >= 0.85:
            reasons.append("Single-sensor report without secondary node confirmation")

    if snr is not None and snr >= 15.0:
        score = min(0.99, score + 0.03)
        reasons.append(f"Clear acoustic/signal profile (SNR {snr:.1f} dB)")

    if cross_modal:
        score = min(0.99, score + 0.05)
        reasons.append("Cross-modal confirmation between acoustic and vision sensors")

    # Determine final qualitative level
    score = round(score, 2)
    if score >= 0.85:
        level = "high"
    elif score >= 0.65:
        level = "medium"
    else:
        level = "low"

    return VerificationResult(
        level=level,
        score=score,
        reasons=reasons,
    )
