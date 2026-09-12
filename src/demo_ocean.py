"""
EcoSentinel - Top-level demo for Person 2 Ocean / AIS Adapter.
Run from repository root: python src/demo_ocean.py
"""

import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from demo_ocean import main

if __name__ == "__main__":
    main()
