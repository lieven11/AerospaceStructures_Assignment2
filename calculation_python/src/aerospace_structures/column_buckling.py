from __future__ import annotations

from .models import (
    AveragedPanelStress,
    AveragedStringerStress,
    ColumnBucklingResult,
    SectionProperties,
)


def _combined_stress(
    left_stress: float,
    left_volume: float,
    right_stress: float,
    right_volume: float,
    stringer_stress: float,
    stringer_volume: float,
) -> float:
    denominator = left_volume / 2.0 + right_volume / 2.0 + stringer_volume
    return (
        left_stress * left_volume / 2.0
        + right_stress * right_volume / 2.0
        + stringer_stress * stringer_volume
    ) / denominator


def calculate_column_buckling(
    panels: list[AveragedPanelStress],
    stringers: list[AveragedStringerStress],
    t_section: SectionProperties,
    omega_section: SectionProperties,
    t_section_ids: set[int],
    ultimate_load_factor: float,
) -> list[ColumnBucklingResult]:
    results: list[ColumnBucklingResult] = []
    for stringer in stringers:
        left = panels[stringer.stringer_id - 1]
        right = panels[stringer.stringer_id]
        section = t_section if stringer.stringer_id in t_section_ids else omega_section
        combined_case1 = _combined_stress(
            left.xx_case1,
            left.volume_mm3,
            right.xx_case1,
            right.volume_mm3,
            stringer.axial_case1,
            stringer.volume_mm3,
        )
        combined_case2 = _combined_stress(
            left.xx_case2,
            left.volume_mm3,
            right.xx_case2,
            right.volume_mm3,
            stringer.axial_case2,
            stringer.volume_mm3,
        )
        # The workbook's final column RF uses the linear Euler value from f_RF,
        # while the Euler-Johnson value is retained as a separate section result.
        critical = section.euler_critical_mpa
        results.append(
            ColumnBucklingResult(
                stringer_id=stringer.stringer_id,
                combined_axial_case1=combined_case1,
                critical_stress_mpa=critical,
                rf_case1=critical / abs(ultimate_load_factor * combined_case1),
                combined_axial_case2=combined_case2,
                rf_case2=critical / abs(ultimate_load_factor * combined_case2),
                section=section,
            )
        )
    return results

