from __future__ import annotations

import math
from typing import Any

from .models import SectionProperties


def _crippling_coefficient(x: float) -> float:
    if x < 0.4:
        return math.nan
    if x <= 1.095:
        return 1.4 - 0.628 * x
    if x <= 1.633:
        return 0.78 / x
    return 0.69 / x**0.75


def _critical_stress(
    slenderness: float,
    transition_slenderness: float,
    cutoff: float,
    elastic_modulus_b_basis_mpa: float,
) -> float:
    if slenderness < transition_slenderness:
        return cutoff - (1.0 / elastic_modulus_b_basis_mpa) * (cutoff / (2.0 * math.pi)) ** 2 * slenderness**2
    return math.pi**2 * elastic_modulus_b_basis_mpa / slenderness**2


def calculate_t_section(
    geometry: dict[str, Any],
    yield_strength_mpa: float,
    elastic_modulus_b_basis_mpa: float,
) -> SectionProperties:
    skin = geometry["skin"]
    section = geometry["t_stringer"]
    column = geometry["column"]
    w_eff = column["effective_width_mm"]
    t_skin = skin["thickness_mm"]
    dim1 = section["DIM1_mm"]
    dim2 = section["DIM2_mm"]
    dim3 = section["DIM3_mm"]
    dim4 = section["DIM4_mm"]

    z_numerator = (
        -(t_skin / 2.0) * w_eff * t_skin
        + (dim3 / 2.0) * dim3 * dim1
        + (dim3 + (dim2 - dim3) / 2.0) * dim4 * (dim2 - dim3)
    )
    area = w_eff * t_skin + dim1 * dim3 + (dim2 - dim3) * dim4
    z_ec = z_numerator / area
    inertia_skin = w_eff * t_skin**3 / 12.0 + w_eff * t_skin * (z_ec + t_skin / 2.0) ** 2
    inertia_flange = dim1 * dim3**3 / 12.0 + dim1 * dim3 * (dim3 / 2.0 - z_ec) ** 2
    inertia_web = dim4 * (dim2 - dim3) ** 3 / 12.0 + dim4 * (dim2 - dim3) * ((dim2 + dim3) / 2.0 - z_ec) ** 2
    inertia = inertia_skin + inertia_flange + inertia_web
    radius = math.sqrt(inertia / area)
    slenderness = column["effective_length_factor"] * column["length_mm"] / radius

    b11 = dim1 / 2.0 - (dim4 / 2.0) * (0.25 * (dim4 / dim3))
    b12 = dim2 - (dim3 / 2.0) * (2.0 - 0.5 * (dim4 / dim3))
    k = 0.41
    x1 = (b11 / dim3) * math.sqrt(yield_strength_mpa / (k * elastic_modulus_b_basis_mpa))
    x2 = (b12 / dim4) * math.sqrt(yield_strength_mpa / (k * elastic_modulus_b_basis_mpa))
    sigma_crip1 = _crippling_coefficient(x1) * yield_strength_mpa
    sigma_crip2 = _crippling_coefficient(x2) * yield_strength_mpa
    sigma_average = (
        sigma_crip2 * b12 * dim4 + 2.0 * yield_strength_mpa * b11 * dim3
    ) / (2.0 * b11 * dim3 + b12 * dim4)
    cutoff = min(yield_strength_mpa, sigma_average)
    transition = math.sqrt(2.0 * math.pi**2 * elastic_modulus_b_basis_mpa / cutoff)
    euler = math.pi**2 * elastic_modulus_b_basis_mpa / slenderness**2
    return SectionProperties(
        name="T-section",
        area_mm2=area,
        second_moment_mm4=inertia,
        radius_of_gyration_mm=radius,
        slenderness=slenderness,
        crippling_cutoff_mpa=cutoff,
        transition_slenderness=transition,
        euler_johnson_critical_mpa=_critical_stress(
            slenderness, transition, cutoff, elastic_modulus_b_basis_mpa
        ),
        euler_critical_mpa=euler,
    )


def calculate_omega_section(
    geometry: dict[str, Any],
    yield_strength_mpa: float,
    elastic_modulus_b_basis_mpa: float,
) -> SectionProperties:
    skin = geometry["skin"]
    section = geometry["omega_stringer"]
    column = geometry["column"]
    w_eff = column["effective_width_mm"]
    t_skin = skin["thickness_mm"]
    dim1 = section["DIM1_mm"]
    t = section["DIM2_mm"]
    dim3 = section["DIM3_mm"]
    dim4 = section["DIM4_mm"]

    z_numerator = (
        -t_skin / 2.0 * w_eff * t_skin
        + 2.0 * (dim4 * t) * (t / 2.0)
        + 2.0 * ((dim1 / 2.0) * t * dim1)
        + ((dim1 - t) + t / 2.0) * (dim3 - 2.0 * t) * t
    )
    area = w_eff * t_skin + t * (2.0 * dim4 + 2.0 * dim1 + (dim3 - 2.0 * t))
    z_ec = z_numerator / area
    inertia_skin = w_eff * t_skin**3 / 12.0 + w_eff * t_skin * (t_skin / 2.0 + z_ec) ** 2
    inertia_flange = dim4 * t**3 / 12.0 + dim4 * t * (t / 2.0 - z_ec) ** 2
    inertia_web = t * dim1**3 / 12.0 + dim1 * t * (dim1 / 2.0 - z_ec) ** 2
    inertia_bottom = (
        (dim3 - 2.0 * t) * t**3 / 12.0
        + (dim3 - 2.0 * t) * t * (dim1 - t / 2.0 - z_ec) ** 2
    )
    inertia = inertia_skin + 2.0 * inertia_flange + 2.0 * inertia_web + inertia_bottom
    radius = math.sqrt(inertia / area)
    slenderness = column["effective_length_factor"] * column["length_mm"] / radius

    b1 = dim1 - t
    b2 = dim3 - t
    b_flange = dim4 + t - t / 2.0
    k_two_connected = 3.6
    k_flange = 0.41
    x1 = (b1 / t) * math.sqrt(yield_strength_mpa / (k_two_connected * elastic_modulus_b_basis_mpa))
    x2 = (b2 / t) * math.sqrt(yield_strength_mpa / (k_two_connected * elastic_modulus_b_basis_mpa))
    x3 = (b_flange / t) * math.sqrt(yield_strength_mpa / (k_flange * elastic_modulus_b_basis_mpa))
    sigma_crip1 = _crippling_coefficient(x1) * yield_strength_mpa
    _ = x2, x3, _crippling_coefficient(x3)
    sigma_crip2 = yield_strength_mpa
    cutoff = min(
        (sigma_crip1 * b1 * t + sigma_crip2 * b2 * t) / (b1 * t + b2 * t),
        yield_strength_mpa,
    )
    transition = math.sqrt(2.0 * math.pi**2 * elastic_modulus_b_basis_mpa / cutoff)
    euler = math.pi**2 * elastic_modulus_b_basis_mpa / slenderness**2
    return SectionProperties(
        name="Omega-section",
        area_mm2=area,
        second_moment_mm4=inertia,
        radius_of_gyration_mm=radius,
        slenderness=slenderness,
        crippling_cutoff_mpa=cutoff,
        transition_slenderness=transition,
        euler_johnson_critical_mpa=_critical_stress(
            slenderness, transition, cutoff, elastic_modulus_b_basis_mpa
        ),
        euler_critical_mpa=euler,
    )

