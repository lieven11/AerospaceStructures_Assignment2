from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .averaging import average_panels, average_stringers
from .column_buckling import calculate_column_buckling
from .excel_export import write_csv, write_json, write_xlsx
from .io import load_element_volumes, load_json, load_raw_stresses
from .mass import calculate_geometry_mass
from .panel_buckling import calculate_panel_buckling
from .results import build_results_final_matrix
from .sections import calculate_omega_section, calculate_t_section
from .strength import calculate_strength
from .stress_processing import normalize_stresses
from .trace_outputs import write_intermediate_outputs


def run_calculation(project_root: Path) -> dict[str, Any]:
    inputs = project_root / "inputs"
    outputs = project_root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    geometry = load_json(inputs / "geometry.json")
    materials = load_json(inputs / "materials.json")
    layout = load_json(inputs / "layout.json")
    raw = load_raw_stresses(inputs / "analysis_stresses.csv")
    volumes = load_element_volumes(inputs / "element_volumes.csv")

    normalized = normalize_stresses(raw)
    strength = calculate_strength(
        normalized,
        materials["ultimate_strength_mpa"],
        materials["ultimate_load_factor"],
    )
    panels = average_panels(normalized, volumes, layout["panel_element_groups"])
    stringers = average_stringers(normalized, volumes, layout["stringer_element_groups"])
    panel_buckling = calculate_panel_buckling(
        panels,
        materials["elastic_modulus_b_basis_mpa"],
        materials["poisson_ratio"],
        geometry["skin"]["panel_length_mm"],
        geometry["skin"]["panel_width_mm"],
        geometry["skin"]["thickness_mm"],
        materials["ultimate_load_factor"],
    )
    t_section = calculate_t_section(
        geometry,
        materials["yield_strength_mpa"],
        materials["elastic_modulus_b_basis_mpa"],
    )
    omega_section = calculate_omega_section(
        geometry,
        materials["yield_strength_mpa"],
        materials["elastic_modulus_b_basis_mpa"],
    )
    column_buckling = calculate_column_buckling(
        panels,
        stringers,
        t_section,
        omega_section,
        set(layout["t_section_stringer_ids"]),
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
    )
    payload = {
        "mass_kg": mass.total_mass_kg,
        "mass_breakdown": asdict(mass),
        "ordered_stresses": [asdict(normalized[i]) for i in sorted(normalized)],
        "strength": [asdict(strength[i]) for i in sorted(strength)],
        "panel_averages": [asdict(value) for value in panels],
        "stringer_averages": [asdict(value) for value in stringers],
        "panel_buckling": [asdict(value) for value in panel_buckling],
        "sections": {"t_section": asdict(t_section), "omega_section": asdict(omega_section)},
        "column_buckling": [asdict(value) for value in column_buckling],
        "results_final": matrix,
    }
    write_json(outputs / "calculation_results.json", payload)
    write_json(
        outputs / "calculation_methodology.json",
        {
            "stress_input": {
                "schema": "Ordered Import layout: ID, panel XX/XY/YY for cases 1/2, stringer axial for cases 1/2",
                "processing": "Values are consumed directly; blank fields become zero only for non-applicable element types.",
            },
            "strength": {
                "panel_von_mises": "sqrt(xx^2 + yy^2 - xx*yy + 3*xy^2)",
                "reserve_factor": "ultimate_strength / (ultimate_load_factor * applicable_stress)",
            },
            "volume_averaging": {
                "equation": "sum(element_volume * element_stress) / sum(element_volume)",
                "volume_source": "inputs/element_volumes.csv",
            },
            "mass": {
                "skin_area_mm2": "skin_thickness * panel_width",
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
                "critical_stress": "pi^2*E_b/slenderness^2",
                "reserve_factor": "critical_stress / abs(ultimate_load_factor * combined_stress)",
            },
        },
    )
    write_csv(outputs / "Results_final.csv", matrix)
    write_xlsx(outputs / "Results_final.xlsx", matrix)
    write_intermediate_outputs(
        outputs,
        normalized,
        strength,
        panels,
        stringers,
        panel_buckling,
        t_section,
        omega_section,
        column_buckling,
        mass,
        materials["ultimate_load_factor"],
    )
    return payload
