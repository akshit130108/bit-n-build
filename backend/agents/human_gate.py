from schemas.event import HumanGateResult, NormalizedEvent, RiskAssessmentResult


def evaluate_human_supervision(
    event: NormalizedEvent,
    risk: RiskAssessmentResult,
) -> HumanGateResult:
    """
    Human Supervision Gate: Safety & governance checkpoint.
    Enforces that high-consequence conservation responses (ranger deployments,
    vessel interception dispatches) require explicit human review.
    """
    reasons = []

    if risk.level in ("HIGH", "CRITICAL"):
        requires_human = True
        status = "WAITING_FOR_APPROVAL"
        reasons.append(
            f"{risk.level} risk incident ({risk.score}/100) mandates human operator approval before dispatching field rangers"
        )
        reasons.append("Safety policy: Autonomous physical deployment is restricted to human authorization")

    elif risk.level == "MEDIUM":
        requires_human = False
        status = "REQUEST_MORE_EVIDENCE"
        reasons.append(
            f"Moderate risk ({risk.score}/100) qualifies for automated sensor cross-examination and camera verification"
        )
        reasons.append("Human intervention optional: Operator review queue notified")

    else:
        # LOW risk
        requires_human = False
        status = "AUTO_APPROVED"
        reasons.append(f"Low risk level ({risk.score}/100): Routine monitoring continues without human gating")

    return HumanGateResult(
        requires_human=requires_human,
        status=status,
        reasons=reasons,
    )
