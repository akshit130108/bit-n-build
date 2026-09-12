from typing import Tuple
from schemas.event import ClassificationResult, NormalizedEvent


def classify_event(event: NormalizedEvent) -> ClassificationResult:
    """
    Classification Agent: Refines raw multimodal sensor detections into
    high-level ecological threat classifications.
    Domain-agnostic reasoning across land, ocean, and mixed biomes.
    """
    domain = event.domain.lower()
    raw_type = event.event_type.lower()
    reasons = []

    # Map domain + raw signature to refined ecological incident
    if domain == "land":
        if "chainsaw" in raw_type or "logging" in raw_type or "saw" in raw_type:
            refined_type = "possible_logging"
            category = "illegal_logging"
            urgency = "high"
            reasons.append(f"Acoustic signature '{raw_type}' on land indicates mechanized timber felling")
        elif "gunshot" in raw_type or "shot" in raw_type or "rifle" in raw_type:
            refined_type = "possible_poaching"
            category = "wildlife_poaching"
            urgency = "critical"
            reasons.append(f"Ballistic impulse '{raw_type}' indicates illicit hunting in terrestrial zone")
        elif "vehicle" in raw_type or "engine" in raw_type:
            refined_type = "unauthorized_vehicle_entry"
            category = "trespass"
            urgency = "medium"
            reasons.append(f"Terrestrial motor acoustic '{raw_type}' in restricted sanctuary boundary")
        elif "fire" in raw_type or "smoke" in raw_type:
            refined_type = "possible_wildfire"
            category = "wildfire_threat"
            urgency = "critical"
            reasons.append(f"Thermal/optical detection '{raw_type}' indicates brush fire or arson")
        else:
            refined_type = f"unclassified_{raw_type}"
            category = "general_terrestrial"
            urgency = "low"
            reasons.append(f"General terrestrial detection for '{raw_type}'")

    elif domain == "ocean":
        if "vessel" in raw_type or "ship" in raw_type or "boat" in raw_type:
            refined_type = "possible_illegal_fishing"
            category = "marine_violation"
            urgency = "high"
            reasons.append(f"Vessel signature '{raw_type}' detected inside marine protected corridor")
        elif "sonar" in raw_type or "explosion" in raw_type or "blast" in raw_type:
            refined_type = "possible_blast_fishing"
            category = "destructive_marine_practice"
            urgency = "critical"
            reasons.append(f"Acoustic blast signature '{raw_type}' indicative of dynamite fishing")
        else:
            refined_type = f"unclassified_{raw_type}"
            category = "marine_activity"
            urgency = "medium"
            reasons.append(f"Oceanic detection for '{raw_type}'")

    else:
        # Cross-domain fallback
        refined_type = f"unclassified_{raw_type}"
        category = "general_ecological"
        urgency = "low"
        reasons.append(f"Detection '{raw_type}' in domain '{domain}'")

    # Check if metadata gives extra context
    if event.metadata.get("ais_disabled"):
        reasons.append("Vessel is operating dark (AIS transponder disabled)")
    if event.metadata.get("protected_area"):
        reasons.append("Event coordinates intersect designated protected ecological zone")

    return ClassificationResult(
        refined_type=refined_type,
        category=category,
        urgency=urgency,
        reasons=reasons,
    )
