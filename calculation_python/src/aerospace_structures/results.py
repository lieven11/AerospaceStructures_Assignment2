from __future__ import annotations

from .models import ColumnBucklingResult, PanelBucklingResult, StrengthResult


def build_results_final_matrix(
    strength: dict[int, StrengthResult],
    panel_buckling: list[PanelBucklingResult],
    column_buckling: list[ColumnBucklingResult],
    mass_kg: float,
) -> list[list[object | None]]:
    matrix: list[list[object | None]] = [[None for _ in range(17)] for _ in range(61)]

    matrix[0][1] = "Case 1"
    matrix[0][2] = "Case 2"
    matrix[1][1] = "RF_Strength"
    strength_ids = list(range(1, 31)) + list(range(37, 64))
    for row_index, element_id in enumerate(strength_ids, start=2):
        matrix[row_index][1] = strength[element_id].rf_case1
        matrix[row_index][2] = strength[element_id].rf_case2

    matrix[0][4] = "Stability Analysis - Panel Buckling"
    matrix[1][4] = "case1"
    matrix[1][11] = "case2"
    for row_index, panel in enumerate(panel_buckling, start=2):
        matrix[row_index][4:10] = [
            panel.xx_case1,
            panel.yy_case1,
            panel.xy_case1,
            panel.k_tau,
            panel.k_biax_case1,
            panel.rf_case1,
        ]
        matrix[row_index][11:17] = [
            panel.xx_case2,
            panel.yy_case2,
            panel.xy_case2,
            panel.k_tau,
            panel.k_biax_case2,
            panel.rf_case2,
        ]

    matrix[14][4] = "Stability Analysis - Column Buckling"
    for row_index, column in enumerate(column_buckling, start=15):
        matrix[row_index][4:8] = [
            column.stringer_id,
            column.combined_axial_case1,
            column.critical_stress_mpa,
            column.rf_case1,
        ]
        matrix[row_index][10:14] = [
            column.stringer_id,
            column.combined_axial_case2,
            column.critical_stress_mpa,
            column.rf_case2,
        ]

    for row_index, column in enumerate(column_buckling, start=26):
        section = column.section
        matrix[row_index][4:9] = [
            column.stringer_id,
            section.second_moment_mm4,
            section.radius_of_gyration_mm,
            section.slenderness,
            section.transition_slenderness,
        ]

    matrix[37][4:7] = ["Mass", mass_kg, "kg"]
    return matrix

