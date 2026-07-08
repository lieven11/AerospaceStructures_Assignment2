from __future__ import annotations

import argparse
from pathlib import Path

from .calculation import run_calculation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the standalone Assignment 1 structural calculations.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Folder containing inputs/ and outputs/ (defaults to this project).",
    )
    args = parser.parse_args()
    result = run_calculation(args.project_root.resolve())
    print(f"Mass: {result['mass_kg']:.12f} kg")
    print(f"Results written to: {args.project_root.resolve() / 'outputs'}")


if __name__ == "__main__":
    main()

