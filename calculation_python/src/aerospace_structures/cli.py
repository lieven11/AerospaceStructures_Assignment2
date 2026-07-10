from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import TextIO

from .calculation import run_calculation
from .io import load_json
from .reporting import print_requirement_summary, thickness_violations


def _format_metric_change(metric_row: dict[str, str], unit: str = "") -> str:
    delta = metric_row["delta_vs_previous"]
    direction = metric_row["comparison_vs_previous"]
    if not delta:
        return "no previous value"
    unit_suffix = f" {unit}" if unit else ""
    return f"{float(delta):+.6g}{unit_suffix} ({direction})"


def print_history_summary(
    history: dict[str, object],
    *,
    stream: TextIO = sys.stdout,
) -> None:
    comparison_path = Path(str(history["comparison_path"]))
    previous_run_id = history.get("previous_run_id")
    print("\nRUN COMPARISON", file=stream)
    if previous_run_id is None:
        print("No previous successful run; saved this run as the comparison baseline.", file=stream)
    else:
        with comparison_path.open(newline="", encoding="utf-8") as handle:
            rows = {
                row["metric"]: row
                for row in csv.DictReader(handle)
                if row["is_latest"] == "yes"
            }
        print(f"Compared against previous run: {previous_run_id}", file=stream)
        print(f"Mass change: {_format_metric_change(rows['mass_kg'], 'kg')}", file=stream)
        print(
            "Minimum RF changes: "
            f"strength {_format_metric_change(rows['minimum_strength_rf'])}, "
            f"panel {_format_metric_change(rows['minimum_panel_buckling_rf'])}, "
            f"column {_format_metric_change(rows['minimum_column_buckling_rf'])}",
            file=stream,
        )
        print(
            f"RF fail-count change: {_format_metric_change(rows['rf_fail_count'])}",
            file=stream,
        )
        print(f"Changed tracked metrics: {history.get('changed_metrics', 0)}", file=stream)
    print(f"Single comparison file: {comparison_path}", file=stream)
    print(f"Runs kept in comparison file: {history.get('retained_run_count', 1)}", file=stream)


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
    if not confirm_thickness_violations(geometry, output_stream=sys.stdout):
        print("Calculation cancelled; no outputs were changed.")
        return 1

    result = run_calculation(project_root, record_history=True)
    print_requirement_summary(result, geometry)
    history = result.get("history")
    if isinstance(history, dict):
        print_history_summary(history)
    print(f"\nResults written to: {project_root / 'outputs'}")
    print("RF cells in Results_final.xlsx are green when > 1 and red when <= 1.")
    return 0
