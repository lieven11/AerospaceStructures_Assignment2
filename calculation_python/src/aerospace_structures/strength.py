from __future__ import annotations

import math

from .models import NormalizedStress, StrengthResult


def _reserve_factor(ultimate: float, factor: float, panel_vm: float, axial: float) -> float | str:
    if panel_vm != 0.0:
        return ultimate / (factor * panel_vm)
    if axial != 0.0:
        return ultimate / (factor * axial)
    return "NaN"


def calculate_strength(
    stresses: dict[int, NormalizedStress],
    ultimate_strength_mpa: float,
    ultimate_load_factor: float,
) -> dict[int, StrengthResult]:
    results: dict[int, StrengthResult] = {}
    for element_id, item in stresses.items():
        vm_case1 = math.sqrt(
            item.xx_case1**2
            + item.yy_case1**2
            - item.xx_case1 * item.yy_case1
            + 3.0 * item.xy_case1**2
        )
        vm_case2 = math.sqrt(
            item.xx_case2**2
            + item.yy_case2**2
            - item.xx_case2 * item.yy_case2
            + 3.0 * item.xy_case2**2
        )
        results[element_id] = StrengthResult(
            element_id=element_id,
            von_mises_case1_mpa=vm_case1,
            von_mises_case2_mpa=vm_case2,
            axial_abs_case1_mpa=abs(item.axial_case1),
            axial_abs_case2_mpa=abs(item.axial_case2),
            rf_case1=_reserve_factor(
                ultimate_strength_mpa,
                ultimate_load_factor,
                vm_case1,
                abs(item.axial_case1),
            ),
            rf_case2=_reserve_factor(
                ultimate_strength_mpa,
                ultimate_load_factor,
                vm_case2,
                abs(item.axial_case2),
            ),
        )
    return results
