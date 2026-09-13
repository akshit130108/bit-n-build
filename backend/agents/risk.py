from typing import Any, Dict, List
from schemas.event import (
    ClassificationResult,
    MemoryResult,
    NormalizedEvent,
    RiskAssessmentResult,
    VerificationResult,
)


def assess_risk(
    event: NormalizedEvent,
    classification: ClassificationResult,
    verification: VerificationResult,
    memory: MemoryResult,
) -> RiskAssessmentResult:
    """
    Risk Agent: Evaluates multimodal threat factors to produce an interpretable
    prototype risk score (0-100) and actionable alert level.
    Incorporates sensor verification and historical spatial-temporal memory.
    """
    metadata = event.metadata or {}
    reasons: List[str] = []
    factors: Dict[str, Any] = {}

    # 1. Base Threat Factor (max 30 pts)
    refined = classification.refined_type
    if "poaching" in refined or "blast" in refined:
        base_threat = 30
        reasons.append("Severe wildlife/habitat destruction threat type")
    elif "logging" in refined or "illegal_fishing" in refined or "fishing" in refined:
        base_threat = 25
        if "illegal_fishing" in refined or "fishing" in refined:
            reasons.append("High-impact marine resource extraction threat type")
        else:
            reasons.append("High-impact resource extraction threat type")
    elif "wildfire" in refined:
        base_threat = 30
        reasons.append("Catastrophic wildfire hazard")
    elif "dark_vessel" in refined or "gap" in refined:
        base_threat = 20
        reasons.append("Suspicious dark vessel AIS gap activity")
    elif "vehicle" in refined:
        base_threat = 20
        reasons.append("Unauthorized vehicular perimeter breach")
    elif "loitering" in refined:
        base_threat = 15
        reasons.append("Suspicious vessel loitering pattern")
    elif "encounter" in refined:
        base_threat = 15
        reasons.append("Suspicious vessel encounter / transshipment pattern")
    else:
        base_threat = 10
        reasons.append(f"Observation activity signature ({refined})")
    factors["base_threat"] = base_threat

    # 2. Verification & Sensor Evidence Factor (max 25 pts)
    # Scales directly with verification score
    evidence_score = int(round(verification.score * 25))
    factors["evidence_score"] = evidence_score
    if verification.level == "high":
        reasons.append(f"High verification confidence ({verification.score:.2f})")
    elif verification.level == "medium":
        reasons.append(f"Moderate verification score ({verification.score:.2f})")
    else:
        reasons.append(f"Low verification score ({verification.score:.2f}) reduces initial risk certainty")

    # 3. Ecological Sensitivity & Protected Reserve (max 20 pts)
    eco_score = 0
    if metadata.get("protected_area", False):
        eco_score += 12
        reasons.append("Location is inside a designated Protected Ecological Reserve")

    sensitivity = metadata.get("ecological_sensitivity", "").lower()
    if sensitivity == "critical":
        eco_score += 8
        reasons.append("Area has critical ecological sensitivity designation")
    elif sensitivity == "high":
        eco_score += 5
        reasons.append("Area has elevated ecological sensitivity designation")
    factors["ecological_sensitivity"] = eco_score

    # 4. Nocturnal / Clandestine Timing (max 10 pts)
    # Strictly require explicit nighttime evidence from source event metadata
    timing_score = 0
    is_night = bool(metadata.get("is_night", False))

    if is_night:
        timing_score = 8
        reasons.append("Nighttime activity indicates intentional clandestine evasion")
    factors["nighttime_factor"] = timing_score

    # 5. Historical Memory & Recurrence Factor (max 25 pts) - AGENTIC RECURRENCE SPIKE
    recurrence_score = 0
    hist_count = memory.historical_events
    if hist_count >= 3:
        recurrence_score = 24
        reasons.append(f"Repeated activity in the same sector ({hist_count} previous incidents)")
    elif hist_count == 2:
        recurrence_score = 16
        reasons.append(f"Emerging recurrence cluster ({hist_count} previous incidents)")
    elif hist_count == 1:
        recurrence_score = 9
        reasons.append("Prior incident detected in vicinity within 48h")
    else:
        reasons.append("Isolated event: No recent historical incidents in sector")
    factors["historical_recurrence"] = recurrence_score

    # Calculate Total Score (clamped to 0-100)
    raw_total = base_threat + evidence_score + eco_score + timing_score + recurrence_score
    total_score = max(0, min(100, raw_total))

    # Categorize Risk Level
    if total_score >= 80:
        level = "HIGH" if total_score < 95 else "CRITICAL"
    elif total_score >= 50:
        level = "MEDIUM"
    else:
        level = "LOW"

    factors["model_version"] = "v1.0-hackathon-prototype"

    return RiskAssessmentResult(
        score=total_score,
        level=level,
        reasons=reasons,
        factors=factors,
    )
