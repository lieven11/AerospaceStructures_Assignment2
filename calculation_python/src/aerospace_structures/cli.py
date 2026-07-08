from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO

from .calculation import run_calculation
from .io import load_json
from .reporting import print_requirement_summary, thickness_violations


def confirm_thickness_violations(
    geometry: dict[str, object],
    *,
    input_stream: TextIO = sys.stdin,
    output_stream: TextIO = sys.stdout,
) -> bool:
    _ = input_stream
    try:
        violations = thickness_violations(geometry)
    except (KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: Invalid panel thickness configuration: {exc}", file=output_stream)
        return False
    if not violations:
        return True

    print("ERROR: One or more thicknesses are below the assignment minimum:", file=output_stream)
    for violation in violations:
        print(f"  - {violation}", file=output_stream)
    print("Calculation blocked; thickness minimums cannot be overridden.", file=output_stream)
    return False


def run_cli(project_root: Path) -> int:
    project_root = project_root.resolve()
    geometry = load_json(project_root / "inputs" / "geometry.json")
    if not confirm_thickness_violations(geometry):
        print("Calculation cancelled; no outputs were changed.")
        return 1

    result = run_calculation(project_root)
    print_requirement_summary(result, geometry)
    print(f"\nResults written to: {project_root / 'outputs'}")
    print("RF cells in Results_final.xlsx are green when > 1 and red when <= 1.")
    return 0
