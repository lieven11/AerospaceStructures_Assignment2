from __future__ import annotations

import csv
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .excel_export import write_csv
from .geometry import panel_thicknesses_mm
from .reporting import MASS_LIMIT_KG, collect_reserve_factors, reserve_factor_passes


MAX_HISTORY_RECORDS = 10
COMPARISON_FILE_NAME = "run_comparison.csv"
NO_CHANGE_ABS_TOL = 1e-9


def _as_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _format_number(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return ""
    return f"{value:.12g}"


def _delta(current: float, previous: float | None) -> float | None:
    if previous is None:
        return None
    value = current - previous
    return 0.0 if math.isclose(value, 0.0, rel_tol=0.0, abs_tol=NO_CHANGE_ABS_TOL) else value


def _minimum(values: list[float]) -> float | None:
    return min(values) if values else None


def _minimum_or_nan(values: list[float]) -> float:
    value = _minimum(values)
    return value if value is not None else math.nan


def _metric_values(result: dict[str, Any], geometry: dict[str, Any]) -> dict[str, float]:
    factors = collect_reserve_factors(result)
    failed = [factor for factor in factors if not reserve_factor_passes(factor.value)]

    strength_values = [
        float(item[f"rf_case{case}"])
        for item in result["strength"]
        for case in (1, 2)
        if _as_float(item[f"rf_case{case}"]) is not None
    ]
    panel_values = [
        float(item[f"rf_case{case}"])
        for item in result["panel_buckling"]
        for case in (1, 2)
        if _as_float(item[f"rf_case{case}"]) is not None
    ]
    column_values = [
        float(item[f"rf_case{case}"])
        for item in result["column_buckling"]
        for case in (1, 2)
        if _as_float(item[f"rf_case{case}"]) is not None
    ]
    all_rf_values = strength_values + panel_values + column_values

    metrics: dict[str, float] = {
        "mass_kg": float(result["mass_kg"]),
        "minimum_strength_rf": _minimum_or_nan(strength_values),
        "minimum_panel_buckling_rf": _minimum_or_nan(panel_values),
        "minimum_column_buckling_rf": _minimum_or_nan(column_values),
        "minimum_overall_rf": _minimum_or_nan(all_rf_values),
        "rf_fail_count": float(len(failed)),
    }
    for panel_id, thickness in enumerate(panel_thicknesses_mm(geometry), start=1):
        metrics[f"panel_{panel_id}_thickness_mm"] = float(thickness)
    metrics["t_stringer_DIM4_mm"] = float(geometry["t_stringer"]["DIM4_mm"])
    metrics["omega_stringer_DIM2_mm"] = float(geometry["omega_stringer"]["DIM2_mm"])
    return metrics


def _direction(metric: str, previous: float | None, current: float | None) -> str:
    if previous is None or current is None:
        return "new"
    delta = current - previous
    if math.isclose(delta, 0.0, rel_tol=0.0, abs_tol=NO_CHANGE_ABS_TOL):
        return "no_change"
    if metric == "mass_kg":
        if previous <= MASS_LIMIT_KG < current:
            return "worse"
        if current <= MASS_LIMIT_KG < previous:
            return "better"
        return "better" if delta < 0 else "worse"
    if metric.startswith("minimum_") and metric.endswith("_rf"):
        return "better" if delta > 0 else "worse"
    if metric == "rf_fail_count":
        return "better" if delta < 0 else "worse"
    return "changed"


def _read_existing_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _records_from_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        run_id = row.get("run_id", "")
        metric = row.get("metric", "")
        value = _as_float(row.get("value"))
        if not run_id or not metric or value is None:
            continue
        record = records_by_id.setdefault(
            run_id,
            {
                "run_id": run_id,
                "timestamp_utc": row.get("timestamp_utc", ""),
                "metrics": {},
            },
        )
        record["metrics"][metric] = value
    return sorted(records_by_id.values(), key=lambda item: str(item["timestamp_utc"]))


def _new_run_id(existing_ids: set[str]) -> str:
    while True:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        if run_id not in existing_ids:
            return run_id


def _previous_values(
    records: list[dict[str, Any]],
    metric: str,
    *,
    before_run_id: str,
) -> list[tuple[str, float]]:
    values: list[tuple[str, float]] = []
    for record in records:
        if record["run_id"] == before_run_id:
            break
        value = record["metrics"].get(metric)
        if isinstance(value, (int, float)) and math.isfinite(value):
            values.append((record["run_id"], float(value)))
    return values


def _row_for_metric(
    record: dict[str, Any],
    records: list[dict[str, Any]],
    metric: str,
    latest_run_id: str,
) -> list[object]:
    current = record["metrics"][metric]
    previous = _previous_values(records, metric, before_run_id=record["run_id"])
    previous_value = previous[-1][1] if previous else None
    previous_run_id = previous[-1][0] if previous else ""
    previous_numbers = [value for _, value in previous]
    best_previous = None
    worst_previous = None
    if previous_numbers and metric.startswith("minimum_"):
        best_previous = max(previous_numbers)
        worst_previous = min(previous_numbers)
    elif previous_numbers and metric in {"mass_kg", "rf_fail_count"}:
        best_previous = min(previous_numbers)
        worst_previous = max(previous_numbers)
    average_previous = (
        sum(previous_numbers) / len(previous_numbers) if previous_numbers else None
    )

    delta_previous = _delta(current, previous_value)
    delta_best = _delta(current, best_previous)
    delta_worst = _delta(current, worst_previous)
    delta_average = _delta(current, average_previous)
    return [
        "yes" if record["run_id"] == latest_run_id else "no",
        record["run_id"],
        record["timestamp_utc"],
        metric,
        _format_number(current),
        previous_run_id,
        _format_number(previous_value),
        _format_number(delta_previous),
        _format_number(best_previous),
        _format_number(delta_best),
        _format_number(worst_previous),
        _format_number(delta_worst),
        _format_number(average_previous),
        _format_number(delta_average),
        _direction(metric, previous_value, current),
    ]


def _comparison_rows(records: list[dict[str, Any]]) -> list[list[object]]:
    rows: list[list[object]] = [
        [
            "is_latest",
            "run_id",
            "timestamp_utc",
            "metric",
            "value",
            "previous_run_id",
            "previous_value",
            "delta_vs_previous",
            "best_previous_value",
            "delta_vs_best_previous",
            "worst_previous_value",
            "delta_vs_worst_previous",
            "average_previous_value",
            "delta_vs_average_previous",
            "comparison_vs_previous",
        ]
    ]
    if not records:
        return rows
    latest_run_id = records[-1]["run_id"]
    metric_order = list(records[-1]["metrics"])
    for record in reversed(records):
        for metric in metric_order:
            if metric in record["metrics"]:
                rows.append(_row_for_metric(record, records, metric, latest_run_id))
    return rows


def record_run_comparison(
    project_root: Path,
    result: dict[str, Any],
    geometry: dict[str, Any],
) -> dict[str, Any]:
    """Update the single rolling comparison CSV for a successful run."""
    comparison_path = project_root / "outputs" / COMPARISON_FILE_NAME
    existing_records = _records_from_rows(_read_existing_rows(comparison_path))
    run_id = _new_run_id({str(record["run_id"]) for record in existing_records})
    previous_run_id = existing_records[-1]["run_id"] if existing_records else None
    current_record = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "metrics": _metric_values(result, geometry),
    }
    records = (existing_records + [current_record])[-MAX_HISTORY_RECORDS:]
    write_csv(comparison_path, _comparison_rows(records))

    latest_rows = [
        row
        for row in _comparison_rows(records)[1:]
        if row[0] == "yes"
    ]
    changed_metrics = sum(1 for row in latest_rows if row[-1] not in {"new", "no_change"})
    return {
        "run_id": run_id,
        "previous_run_id": previous_run_id,
        "comparison_path": str(comparison_path),
        "changed_metrics": changed_metrics,
        "retained_run_count": len(records),
        "metrics": current_record["metrics"],
    }
