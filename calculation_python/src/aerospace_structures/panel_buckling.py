from __future__ import annotations

import math

from .models import AveragedPanelStress, PanelBucklingResult


def _compression_pair(xx: float, yy: float) -> tuple[float, float, float]:
    main = max(-min(xx, 0.0), -min(yy, 0.0))
    secondary_signed = yy if -min(xx, 0.0) >= -min(yy, 0.0) else xx
    ratio = -secondary_signed / main if secondary_signed > 0.0 else abs(secondary_signed) / main
    return main, secondary_signed, ratio


def _biaxial_factor(alpha: float, ratio: float, modes: range) -> float:
    candidates = [
        ((mode**2 + alpha**2) ** 2) / (alpha**2 * (mode**2 + ratio * alpha**2))
        for mode in modes
    ]
    return min(value for value in candidates if value > 0.0)


def calculate_panel_buckling(
    panels: list[AveragedPanelStress],
    elastic_modulus_b_basis_mpa: float,
    poisson_ratio: float,
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    ultimate_load_factor: float,
) -> list[PanelBucklingResult]:
    alpha = length_mm / width_mm
    sigma_e = (
        elastic_modulus_b_basis_mpa
        * math.pi**2
        / (12.0 * (1.0 - poisson_ratio**2))
        * (thickness_mm / width_mm) ** 2
    )
    k_tau = 5.34 + 4.0 / alpha**2
    tau_critical = sigma_e * k_tau

    results: list[PanelBucklingResult] = []
    for panel in panels:
        main1, _, ratio1 = _compression_pair(panel.xx_case1, panel.yy_case1)
        main2, _, ratio2 = _compression_pair(panel.xx_case2, panel.yy_case2)
        k_biax1 = _biaxial_factor(alpha, ratio1, range(1, 7))
        k_biax2 = _biaxial_factor(alpha, ratio2, range(1, 7))
        sigma_critical1 = k_biax1 * sigma_e
        sigma_critical2 = k_biax2 * sigma_e
        rf_biax1 = ultimate_load_factor * main1 / sigma_critical1
        rf_biax2 = ultimate_load_factor * main2 / sigma_critical2
        rf_shear1 = abs(ultimate_load_factor * panel.xy_case1 / tau_critical)
        rf_shear2 = abs(ultimate_load_factor * panel.xy_case2 / tau_critical)
        results.append(
            PanelBucklingResult(
                panel_id=panel.panel_id,
                xx_case1=panel.xx_case1,
                yy_case1=panel.yy_case1,
                xy_case1=panel.xy_case1,
                k_tau=k_tau,
                k_biax_case1=k_biax1,
                sigma_e_mpa=sigma_e,
                sigma_cr_biax_case1_mpa=sigma_critical1,
                main_compression_case1_mpa=main1,
                compression_ratio_case1=ratio1,
                biaxial_interaction_case1=rf_biax1,
                shear_interaction_case1=rf_shear1,
                rf_case1=1.0 / (rf_biax1 + rf_shear1**2),
                xx_case2=panel.xx_case2,
                yy_case2=panel.yy_case2,
                xy_case2=panel.xy_case2,
                k_biax_case2=k_biax2,
                sigma_cr_biax_case2_mpa=sigma_critical2,
                main_compression_case2_mpa=main2,
                compression_ratio_case2=ratio2,
                biaxial_interaction_case2=rf_biax2,
                shear_interaction_case2=rf_shear2,
                rf_case2=1.0 / (rf_biax2 + rf_shear2**2),
            )
        )
    return results
