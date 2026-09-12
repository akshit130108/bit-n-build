"""
EcoSentinel - Person 2 Ocean / AIS Adapter Interface
Connects Global Fishing Watch (GFW) AIS detections to the EcoSentinel shared reasoning backend.

CANONICAL ADAPTER NOTE:
This module is a lightweight forwarder to `backend/adapters/ocean_gfw.py`, which is the
single canonical source of truth for Person 2's ocean adapter.
Any service or integration code should rely directly on `backend/adapters/ocean_gfw.py`.
"""

import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from adapters.ocean_gfw import (
    detect_dark_vessel,
    evaluate_mpa_context,
    fetch_ocean_events,
    get_demo_ocean_event,
    get_simulated_ocean_events,
    post_to_person3,
)

__all__ = [
    "detect_dark_vessel",
    "fetch_ocean_events",
    "get_demo_ocean_event",
    "get_simulated_ocean_events",
    "post_to_person3",
    "evaluate_mpa_context",
]
