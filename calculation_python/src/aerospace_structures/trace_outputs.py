from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from .models import (
    AveragedPanelStress,
    AveragedStringerStress,
    ColumnBucklingResult,
    MassBreakdown,
    NormalizedStress,
    PanelBucklingResult,
    SectionProperties,
    StrengthResult,
)


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_intermediate_outputs(
    output_dir: Path,
    stresses: dict[int, NormalizedStress],
    strength: dict[int, StrengthResult],
    panels: list[AveragedPanelStress],
    stringers: list[AveragedStringerStress],
    panel_buckling: list[PanelBucklingResult],
    t_section: SectionProperties,
    omega_section: SectionProperties,
    columns: list[ColumnBucklingResult],
    mass: MassBreakdown,
    ultimate_load_factor: float,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "ordered_stresses.csv", [asdict(stresses[i]) for i in sorted(stresses)])
    _write_rows(output_dir / "strength_results.csv", [asdict(strength[i]) for i in sorted(strength)])
    _write_rows(output_dir / "panel_volume_averages.csv", [asdict(row) for row in panels])
    _write_rows(output_dir / "stringer_volume_averages.csv", [asdict(row) for row in stringers])
    _write_rows(output_dir / "panel_buckling_results.csv", [asdict(row) for row in panel_buckling])
    _write_rows(
        output_dir / "section_properties.csv",
        [asdict(t_section), asdict(omega_section)],
    )
    _write_rows(
        output_dir / "column_buckling_results.csv",
        [
            {
                "stringer_id": row.stringer_id,
                "section": row.section.name,
                "combined_axial_case1_mpa": row.combined_axial_case1,
                "critical_stress_mpa": row.critical_stress_mpa,
                "ultimate_load_factor_times_abs_stress_case1_mpa": abs(
                    ultimate_load_factor * row.combined_axial_case1
                ),
                "rf_case1": row.rf_case1,
                "combined_axial_case2_mpa": row.combined_axial_case2,
                "ultimate_load_factor_times_abs_stress_case2_mpa": abs(
                    ultimate_load_factor * row.combined_axial_case2
                ),
                "rf_case2": row.rf_case2,
            }
            for row in columns
        ],
    )
    mass_rows = [asdict(component) for component in mass.components]
    mass_rows.append(
        {
            "component": "TOTAL",
            "count": sum(component.count for component in mass.components),
            "cross_section_area_mm2": "",
            "length_mm": "",
            "volume_each_mm3": "",
            "total_volume_mm3": mass.total_volume_mm3,
            "density_tonne_per_mm3": mass.components[0].density_tonne_per_mm3,
            "mass_kg": mass.total_mass_kg,
        }
    )
    _write_rows(output_dir / "mass_breakdown.csv", mass_rows)
