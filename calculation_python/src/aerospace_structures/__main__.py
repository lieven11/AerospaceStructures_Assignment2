from __future__ import annotations

import argparse
from pathlib import Path

from .cli import run_cli


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the standalone Assignment 2 structural calculations.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Folder containing inputs/ and outputs/ (defaults to this project).",
    )
    args = parser.parse_args()
    raise SystemExit(run_cli(args.project_root))


if __name__ == "__main__":
    main()
