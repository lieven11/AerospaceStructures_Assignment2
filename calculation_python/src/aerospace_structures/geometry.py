from __future__ import annotations

import math
from typing import Any


def panel_thicknesses_mm(geometry: dict[str, Any]) -> list[float]:
    skin = geometry["skin"]
    values = skin.get("panel_thicknesses_mm")
    if not isinstance(values, list):
        raise ValueError("skin.panel_thicknesses_mm must be a list")

    expected_count = int(skin["panel_count"])
    if len(values) != expected_count:
        raise ValueError(
            f"skin.panel_thicknesses_mm contains {len(values)} values; "
            f"expected {expected_count}"
        )
    try:
        thicknesses = [float(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise ValueError("Every panel thickness must be numeric") from exc
    if any(not math.isfinite(value) or value <= 0.0 for value in thicknesses):
        raise ValueError("Every panel thickness must be finite and greater than zero")
    return thicknesses


def panel_areas_mm2(geometry: dict[str, Any]) -> list[float]:
    skin = geometry["skin"]
    return [
        thickness * skin["panel_width_mm"]
        for thickness in panel_thicknesses_mm(geometry)
    ]


def t_stringer_area_mm2(geometry: dict[str, Any]) -> float:
    section = geometry["t_stringer"]
    return (
        section["DIM1_mm"] * section["DIM3_mm"]
        + (section["DIM2_mm"] - section["DIM3_mm"]) * section["DIM4_mm"]
    )


def omega_stringer_area_mm2(geometry: dict[str, Any]) -> float:
    section = geometry["omega_stringer"]
    return (
        2.0 * section["DIM4_mm"] * section["DIM2_mm"]
        + 2.0 * section["DIM1_mm"] * section["DIM2_mm"]
        + (section["DIM3_mm"] - 2.0 * section["DIM2_mm"]) * section["DIM2_mm"]
    )


def t_stringer_centroid_z_mm(geometry: dict[str, Any]) -> float:
    section = geometry["t_stringer"]
    dim1 = section["DIM1_mm"]
    dim2 = section["DIM2_mm"]
    dim3 = section["DIM3_mm"]
    dim4 = section["DIM4_mm"]
    first_moment = (
        (dim3 / 2.0) * dim3 * dim1
        + (dim3 + (dim2 - dim3) / 2.0) * dim4 * (dim2 - dim3)
    )
    return first_moment / t_stringer_area_mm2(geometry)


def omega_stringer_centroid_z_mm(geometry: dict[str, Any]) -> float:
    section = geometry["omega_stringer"]
    dim1 = section["DIM1_mm"]
    t = section["DIM2_mm"]
    dim3 = section["DIM3_mm"]
    dim4 = section["DIM4_mm"]
    first_moment = (
        2.0 * (dim4 * t) * (t / 2.0)
        + 2.0 * ((dim1 / 2.0) * t * dim1)
        + ((dim1 - t) + t / 2.0) * (dim3 - 2.0 * t) * t
    )
    return first_moment / omega_stringer_area_mm2(geometry)


def panel_volumes_mm3(geometry: dict[str, Any]) -> list[float]:
    panel_length = geometry["skin"]["panel_length_mm"]
    return [area * panel_length for area in panel_areas_mm2(geometry)]


def stringer_volumes_mm3(
    geometry: dict[str, Any],
    t_section_stringer_ids: set[int],
    stringer_count: int,
) -> list[float]:
    panel_length = geometry["skin"]["panel_length_mm"]
    t_volume = t_stringer_area_mm2(geometry) * panel_length
    omega_volume = omega_stringer_area_mm2(geometry) * panel_length
    return [
        t_volume if stringer_id in t_section_stringer_ids else omega_volume
        for stringer_id in range(1, stringer_count + 1)
    ]


def panel_offsets_mm(geometry: dict[str, Any]) -> list[float]:
    return [thickness / 2.0 for thickness in panel_thicknesses_mm(geometry)]


def stringer_offsets_mm(
    geometry: dict[str, Any],
    t_section_stringer_ids: set[int],
    stringer_count: int,
) -> list[float]:
    t_centroid = t_stringer_centroid_z_mm(geometry)
    omega_centroid = omega_stringer_centroid_z_mm(geometry)
    return [
        t_centroid if stringer_id in t_section_stringer_ids else omega_centroid
        for stringer_id in range(1, stringer_count + 1)
    ]
