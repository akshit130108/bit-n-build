"""
EcoSentinel - Person 2 Ocean / AIS Adapter Interface
Connects Global Fishing Watch (GFW) AIS detections to the EcoSentinel shared reasoning backend.
"""

import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from adapters.ocean_gfw import (
    detect_dark_vessel,
    fetch_ocean_events,
    get_demo_ocean_event,
    post_to_person3,
    evaluate_mpa_context,
)

__all__ = [
    "detect_dark_vessel",
    "fetch_ocean_events",
    "get_demo_ocean_event",
    "post_to_person3",
    "evaluate_mpa_context",
]
