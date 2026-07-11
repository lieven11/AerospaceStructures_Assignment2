from __future__ import annotations

from typing import Any

from .geometry import omega_stringer_area_mm2, panel_areas_mm2, t_stringer_area_mm2
from .models import MassBreakdown, MassComponent


def calculate_geometry_mass(
    geometry: dict[str, Any],
    density_tonne_per_mm3: float,
) -> MassBreakdown:
    """Reproduce Volume!Mass_computed from editable geometry, not FE volumes."""
    skin = geometry["skin"]
    t_section = geometry["t_stringer"]
    omega_section = geometry["omega_stringer"]

    panel_length = skin["panel_length_mm"]
    skin_areas = panel_areas_mm2(geometry)
    t_area = t_stringer_area_mm2(geometry)
    omega_area = omega_stringer_area_mm2(geometry)

    definitions = [
        (f"skin_panel_{panel_id}", 1, area)
        for panel_id, area in enumerate(skin_areas, start=1)
    ]
    definitions.extend(
        [
            ("t_stringer", t_section["count"], t_area),
            ("omega_stringer", omega_section["count"], omega_area),
        ]
    )
    components: list[MassComponent] = []
    for name, count, area in definitions:
        volume_each = area * panel_length
        total_volume = count * volume_each
        components.append(
            MassComponent(
                component=name,
                count=count,
                cross_section_area_mm2=area,
                length_mm=panel_length,
                volume_each_mm3=volume_each,
                total_volume_mm3=total_volume,
                density_tonne_per_mm3=density_tonne_per_mm3,
                mass_kg=density_tonne_per_mm3 * total_volume * 1_000.0,
            )
        )
    total_volume = sum(component.total_volume_mm3 for component in components)
    return MassBreakdown(
        components=tuple(components),
        total_volume_mm3=total_volume,
        total_mass_kg=density_tonne_per_mm3 * total_volume * 1_000.0,
    )
