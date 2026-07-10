from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

from .geometry import panel_thicknesses_mm
from .models import ColumnBucklingResult, PanelBucklingResult, StrengthResult


PANEL_OFFSET_MM = 1.0
STRINGER_OFFSET_MM = 3.0


def _load_submission_template(path: Path) -> list[list[object | None]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle, delimiter=";"))
    width = max(len(row) for row in rows)
    return [row + [""] * (width - len(row)) for row in rows]


def _minimum_numeric(values: list[float | str]) -> float:
    numeric = [float(value) for value in values if math.isfinite(float(value))]
    if not numeric:
        raise ValueError("Cannot calculate a minimum reserve factor without numeric values")
    return min(numeric)


def build_results_final_matrix(
    strength: dict[int, StrengthResult],
    panel_buckling: list[PanelBucklingResult],
    column_buckling: list[ColumnBucklingResult],
    mass_kg: float,
    geometry: dict[str, Any],
    layout: dict[str, Any],
    submission_template: Path,
) -> list[list[object | None]]:
    """Populate the official submission layout with all calculated results."""
    matrix = _load_submission_template(submission_template)

    # Cross-section dimensions and provisional FE offsets.
    for row_index, thickness in zip(range(20, 30), panel_thicknesses_mm(geometry)):
        matrix[row_index][1] = thickness
        matrix[row_index][2] = PANEL_OFFSET_MM

    t_stringer_ids = set(layout["t_section_stringer_ids"])
    for stringer_id, row_index in enumerate(range(31, 40), start=1):
        section_key = "t_stringer" if stringer_id in t_stringer_ids else "omega_stringer"
        section = geometry[section_key]
        matrix[row_index][1] = section["DIM4_mm"] if section_key == "t_stringer" else section["DIM2_mm"]
        matrix[row_index][2] = section["DIM2_mm"] if section_key == "t_stringer" else section["DIM1_mm"]
        matrix[row_index][3] = STRINGER_OFFSET_MM

    # Strength analysis.
    strength_ids = list(range(1, 31)) + list(range(37, 64))
    for row_index, element_id in enumerate(strength_ids, start=45):
        matrix[row_index][1] = strength[element_id].rf_case1
        matrix[row_index][4] = strength[element_id].rf_case2

    # Panel buckling analysis.
    for row_index, panel in enumerate(panel_buckling, start=107):
        matrix[row_index][1:7] = [
            panel.xx_case1,
            panel.yy_case1,
            panel.xy_case1,
            panel.k_tau,
            panel.k_biax_case1,
            panel.rf_case1,
        ]
        matrix[row_index][9:15] = [
            panel.xx_case2,
            panel.yy_case2,
            panel.xy_case2,
            panel.k_tau,
            panel.k_biax_case2,
            panel.rf_case2,
        ]

    # Column buckling and combined section properties.
    for row_index, column in enumerate(column_buckling, start=122):
        matrix[row_index][1:4] = [
            column.combined_axial_case1,
            column.section.crippling_cutoff_mpa,
            column.rf_case1,
        ]
        matrix[row_index][6:9] = [
            column.combined_axial_case2,
            column.section.crippling_cutoff_mpa,
            column.rf_case2,
        ]

    for row_index, column in enumerate(column_buckling, start=135):
        section = column.section
        matrix[row_index][1:5] = [
            section.second_moment_mm4,
            section.radius_of_gyration_mm,
            section.slenderness,
            section.transition_slenderness,
        ]

    strength_min = _minimum_numeric(
        [item.rf_case1 for item in strength.values()] + [item.rf_case2 for item in strength.values()]
    )
    panel_min = min(
        [item.rf_case1 for item in panel_buckling] + [item.rf_case2 for item in panel_buckling]
    )
    column_min = min(
        [item.rf_case1 for item in column_buckling] + [item.rf_case2 for item in column_buckling]
    )
    matrix[146][1] = strength_min
    matrix[147][1] = panel_min
    matrix[148][1] = column_min
    matrix[149][1] = min(strength_min, panel_min, column_min)
    matrix[152][1] = mass_kg
    return matrix
