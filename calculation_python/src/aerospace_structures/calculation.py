from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .averaging import average_panels, average_stringers
from .column_buckling import calculate_column_buckling
from .excel_export import write_csv, write_json, write_xlsx
from .geometry import panel_thicknesses_mm, panel_volumes_mm3, stringer_volumes_mm3
from .history import record_run_comparison
from .io import load_json, load_query_stresses, write_analysis_stresses
from .mass import calculate_geometry_mass
from .panel_buckling import calculate_panel_buckling
from .results import build_results_final_matrix
from .reporting import thickness_violations
from .sections import calculate_omega_section, calculate_t_section
from .strength import calculate_strength
from .stress_processing import normalize_stresses
from .trace_outputs import write_intermediate_outputs


def _flatten_element_groups(groups: list[list[int]]) -> list[int]:
    return [int(element_id) for group in groups for element_id in group]


def _analysis_stress_row_ids(layout: dict[str, Any], stress_element_ids: list[int]) -> list[int]:
    row_ids = set(stress_element_ids)
    row_ids.update(int(element_id) for element_id in layout.get("excluded_spar_element_ids", []))
    row_ids.update(int(element_id) for element_id in layout.get("analysis_stress_extra_ids", []))
    return sorted(row_ids)


def run_calculation(project_root: Path, *, record_history: bool = False) -> dict[str, Any]:
    inputs = project_root / "inputs"
    outputs = project_root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    geometry = load_json(inputs / "geometry.json")
    violations = thickness_violations(geometry)
    if violations:
        raise ValueError(
            "Geometry violates mandatory thickness minimums: "
            + "; ".join(violations)
        )
    materials = load_json(inputs / "materials.json")
    layout = load_json(inputs / "layout.json")
    panel_element_ids = _flatten_element_groups(layout["panel_element_groups"])
    stringer_element_ids = _flatten_element_groups(layout["stringer_element_groups"])
    results_query = project_root.parent / "Results_Querey"
    raw = load_query_stresses(
        results_query / "Stresses.csv",
        results_query / "Axial.csv",
        panel_element_ids,
        stringer_element_ids,
    )
    write_analysis_stresses(
        inputs / "analysis_stresses.csv",
        raw,
        _analysis_stress_row_ids(layout, panel_element_ids + stringer_element_ids),
    )
    skin_thicknesses = panel_thicknesses_mm(geometry)
    panel_volumes = panel_volumes_mm3(geometry)
    t_section_ids = set(layout["t_section_stringer_ids"])
    stringer_volumes = stringer_volumes_mm3(
        geometry,
        t_section_ids,
        len(layout["stringer_element_groups"]),
    )

    normalized = normalize_stresses(raw)
    strength = calculate_strength(
        normalized,
        materials["ultimate_strength_mpa"],
        materials["ultimate_load_factor"],
    )
    panels = average_panels(
        normalized,
        layout["panel_element_groups"],
        panel_volumes,
    )
    stringers = average_stringers(
        normalized,
        layout["stringer_element_groups"],
        stringer_volumes,
    )
    panel_buckling = calculate_panel_buckling(
        panels,
        materials["elastic_modulus_b_basis_mpa"],
        materials["poisson_ratio"],
        geometry["skin"]["panel_length_mm"],
        geometry["skin"]["panel_width_mm"],
        skin_thicknesses,
        materials["ultimate_load_factor"],
    )
    sections_by_stringer = {}
    for stringer_id in range(1, len(skin_thicknesses)):
        section_calculator = (
            calculate_t_section
            if stringer_id in t_section_ids
            else calculate_omega_section
        )
        sections_by_stringer[stringer_id] = section_calculator(
            geometry,
            materials["yield_strength_mpa"],
            materials["elastic_modulus_b_basis_mpa"],
            skin_thicknesses[stringer_id - 1],
            skin_thicknesses[stringer_id],
        )
    column_buckling = calculate_column_buckling(
        panels,
        stringers,
        sections_by_stringer,
        materials["ultimate_load_factor"],
    )
    mass = calculate_geometry_mass(
        geometry,
        materials["density_tonne_per_mm3"],
    )

    matrix = build_results_final_matrix(
        strength,
        panel_buckling,
        column_buckling,
        mass.total_mass_kg,
        geometry,
        layout,
        project_root.parent / "AS_Project_Part2_SubmissionTemplate_3766785.csv",
    )
    payload = {
        "mass_kg": mass.total_mass_kg,
        "mass_breakdown": asdict(mass),
        "ordered_stresses": [asdict(normalized[i]) for i in sorted(normalized)],
        "strength": [asdict(strength[i]) for i in sorted(strength)],
        "panel_averages": [asdict(value) for value in panels],
        "stringer_averages": [asdict(value) for value in stringers],
        "panel_buckling": [asdict(value) for value in panel_buckling],
        "sections": {
            str(stringer_id): asdict(section)
            for stringer_id, section in sections_by_stringer.items()
        },
        "column_buckling": [asdict(value) for value in column_buckling],
        "results_final": matrix,
    }
    write_json(outputs / "calculation_results.json", payload)
    write_json(
        outputs / "calculation_methodology.json",
        {
            "stress_input": {
                "schema": "Results_Querey/Stresses.csv elements 1-30 and Axial.csv elements 37-63; load case 1 is followed vertically by load case 2",
                "processing": "Only the first fixed-size result block in each file is read, so appended duplicate blocks are ignored.",
            },
            "strength": {
                "panel_von_mises": "sqrt(xx^2 + yy^2 - xx*yy + 3*xy^2)",
                "reserve_factor": "ultimate_strength / (ultimate_load_factor * applicable_stress)",
            },
            "volume_averaging": {
                "equation": "sum(geometry_subvolume * element_stress) / sum(geometry_subvolume)",
                "volume_source": "inputs/geometry.json",
                "panel_volume": "panel_thickness * panel_width * panel_length",
                "panel_group_subvolume": "panel_volume / number of elements in the panel group",
                "stringer_volume": "stringer_cross_section_area * panel_length",
                "stringer_group_subvolume": "stringer_volume / number of elements in the stringer group",
                "note": "FE extracted element volumes are not used.",
            },
            "mass": {
                "skin_area_mm2": "panel_thickness * panel_width, evaluated separately for panels 1-10",
                "t_stringer_area_mm2": "DIM1*DIM3 + (DIM2-DIM3)*DIM4",
                "omega_stringer_area_mm2": "2*DIM4*DIM2 + 2*DIM1*DIM2 + (DIM3-2*DIM2)*DIM2",
                "component_volume_mm3": "area * panel_length * count",
                "total_mass_kg": "density_tonne_per_mm3 * total_volume_mm3 * 1000",
                "note": "Geometry-derived Mass_computed logic; FE extracted volumes are not used for mass.",
            },
            "panel_buckling": {
                "sigma_e": "E_b*pi^2/(12*(1-nu^2))*(t/b)^2",
                "k_tau": "5.34 + 4/alpha^2",
                "combined_rf": "1 / (biaxial_interaction + shear_interaction^2)",
            },
            "column_buckling": {
                "combined_stress": "volume-weighted adjacent half-panels plus stringer",
                "combined_section": "half effective width from each adjacent panel, retaining each panel's own thickness in centroid and inertia calculations",
                "critical_stress": "pi^2*E_b/slenderness^2",
                "reserve_factor": "critical_stress / abs(ultimate_load_factor * combined_stress)",
            },
        },
    )
    write_csv(outputs / "Results_final.csv", matrix, delimiter=";")
    write_xlsx(outputs / "Results_final.xlsx", matrix)
    write_intermediate_outputs(
        outputs,
        normalized,
        strength,
        panels,
        stringers,
        panel_buckling,
        sections_by_stringer,
        column_buckling,
        mass,
        materials["ultimate_load_factor"],
    )
    if record_history:
        payload["history"] = record_run_comparison(project_root, payload, geometry)
    return payload
