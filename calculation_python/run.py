from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aerospace_structures.calculation import run_calculation  # noqa: E402


if __name__ == "__main__":
    result = run_calculation(PROJECT_ROOT)
    print(f"Mass: {result['mass_kg']:.12f} kg")
    print(f"Results written to: {PROJECT_ROOT / 'outputs'}")

