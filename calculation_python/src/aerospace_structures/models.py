from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawStress:
    element_id: int
    panel_xx_case1: float | None
    panel_xx_case2: float | None
    panel_xy_case1: float | None
    panel_xy_case2: float | None
    panel_yy_case1: float | None
    panel_yy_case2: float | None
    stringer_axial_case1: float | None
    stringer_axial_case2: float | None


@dataclass(frozen=True)
class NormalizedStress:
    element_id: int
    xx_case1: float
    xx_case2: float
    xy_case1: float
    xy_case2: float
    yy_case1: float
    yy_case2: float
    axial_case1: float
    axial_case2: float


@dataclass(frozen=True)
class AveragedPanelStress:
    panel_id: int
    element_ids: tuple[int, ...]
    volume_mm3: float
    xx_case1: float
    xx_case2: float
    xy_case1: float
    xy_case2: float
    yy_case1: float
    yy_case2: float


@dataclass(frozen=True)
class AveragedStringerStress:
    stringer_id: int
    element_ids: tuple[int, ...]
    volume_mm3: float
    axial_case1: float
    axial_case2: float


@dataclass(frozen=True)
class StrengthResult:
    element_id: int
    von_mises_case1_mpa: float
    von_mises_case2_mpa: float
    axial_abs_case1_mpa: float
    axial_abs_case2_mpa: float
    rf_case1: float | str
    rf_case2: float | str


@dataclass(frozen=True)
class PanelBucklingResult:
    panel_id: int
    xx_case1: float
    yy_case1: float
    xy_case1: float
    k_tau: float
    k_biax_case1: float
    sigma_e_mpa: float
    sigma_cr_biax_case1_mpa: float
    main_compression_case1_mpa: float
    compression_ratio_case1: float
    biaxial_interaction_case1: float
    shear_interaction_case1: float
    rf_case1: float
    xx_case2: float
    yy_case2: float
    xy_case2: float
    k_biax_case2: float
    sigma_cr_biax_case2_mpa: float
    main_compression_case2_mpa: float
    compression_ratio_case2: float
    biaxial_interaction_case2: float
    shear_interaction_case2: float
    rf_case2: float


@dataclass(frozen=True)
class SectionProperties:
    name: str
    area_mm2: float
    second_moment_mm4: float
    radius_of_gyration_mm: float
    slenderness: float
    crippling_cutoff_mpa: float
    transition_slenderness: float
    euler_johnson_critical_mpa: float
    euler_critical_mpa: float


@dataclass(frozen=True)
class ColumnBucklingResult:
    stringer_id: int
    combined_axial_case1: float
    critical_stress_mpa: float
    rf_case1: float
    combined_axial_case2: float
    rf_case2: float
    section: SectionProperties


@dataclass(frozen=True)
class MassComponent:
    component: str
    count: int
    cross_section_area_mm2: float
    length_mm: float
    volume_each_mm3: float
    total_volume_mm3: float
    density_tonne_per_mm3: float
    mass_kg: float


@dataclass(frozen=True)
class MassBreakdown:
    components: tuple[MassComponent, ...]
    total_volume_mm3: float
    total_mass_kg: float
