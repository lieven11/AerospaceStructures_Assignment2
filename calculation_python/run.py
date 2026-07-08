from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aerospace_structures.cli import run_cli  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(run_cli(PROJECT_ROOT))
