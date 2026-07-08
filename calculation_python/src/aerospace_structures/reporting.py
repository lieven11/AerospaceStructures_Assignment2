from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from typing import Any, TextIO

from .geometry import panel_thicknesses_mm

MASS_LIMIT_KG = 19.8505
MIN_SKIN_THICKNESS_MM = 1.2
MIN_STRINGER_THICKNESS_MM = 1.0


@dataclass(frozen=True)
class ReserveFactor:
    label: str
    value: float


def thickness_violations(geometry: dict[str, Any]) -> list[str]:
    checks = [
        (f"Panel {panel_id} thickness", value, MIN_SKIN_THICKNESS_MM)
        for panel_id, value in enumerate(panel_thicknesses_mm(geometry), start=1)
    ]
    checks.extend(
        [
        ("T-stringer DIM4", geometry["t_stringer"]["DIM4_mm"], MIN_STRINGER_THICKNESS_MM),
        ("Omega-stringer DIM2", geometry["omega_stringer"]["DIM2_mm"], MIN_STRINGER_THICKNESS_MM),
        ]
    )
    return [
        f"{label}: {value:g} mm (minimum {minimum:g} mm)"
        for label, value, minimum in checks
        if value < minimum
    ]


def collect_reserve_factors(result: dict[str, Any]) -> list[ReserveFactor]:
    factors: list[ReserveFactor] = []
    for item in result["strength"]:
        for case in (1, 2):
            factors.append(
                ReserveFactor(
                    f"Strength, element {item['element_id']}, case {case}",
                    float(item[f"rf_case{case}"]),
                )
            )
    for item in result["panel_buckling"]:
        for case in (1, 2):
            factors.append(
                ReserveFactor(
                    f"Panel buckling, panel {item['panel_id']}, case {case}",
                    float(item[f"rf_case{case}"]),
                )
            )
    for item in result["column_buckling"]:
        for case in (1, 2):
            factors.append(
                ReserveFactor(
                    f"Column buckling, stringer {item['stringer_id']}, case {case}",
                    float(item[f"rf_case{case}"]),
                )
            )
    return factors


def reserve_factor_passes(value: object) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number > 1.0


def print_requirement_summary(
    result: dict[str, Any],
    geometry: dict[str, Any],
    *,
    stream: TextIO = sys.stdout,
    use_color: bool | None = None,
) -> None:
    if use_color is None:
        use_color = bool(getattr(stream, "isatty", lambda: False)())

    def status(passed: bool) -> str:
        text = "PASS" if passed else "FAIL"
        if not use_color:
            return f"[{text}]"
        color = "\033[32m" if passed else "\033[31m"
        return f"{color}[{text}]\033[0m"

    mass = float(result["mass_kg"])
    mass_passed = mass <= MASS_LIMIT_KG
    relation = "<=" if mass_passed else ">"
    print("\nDESIGN REQUIREMENT SUMMARY", file=stream)
    print(
        f"{status(mass_passed)} Weight: {mass:.6f} kg {relation} {MASS_LIMIT_KG:.4f} kg limit",
        file=stream,
    )

    skin_thicknesses = panel_thicknesses_mm(geometry)
    panel_thicknesses_passed = min(skin_thicknesses) >= MIN_SKIN_THICKNESS_MM
    print(
        f"{status(panel_thicknesses_passed)} Panel thicknesses: "
        f"minimum {min(skin_thicknesses):g} mm across {len(skin_thicknesses)} panels "
        f"(required minimum {MIN_SKIN_THICKNESS_MM:g} mm)",
        file=stream,
    )
    thickness_checks = (
        ("T-stringer DIM4", geometry["t_stringer"]["DIM4_mm"], MIN_STRINGER_THICKNESS_MM),
        ("Omega-stringer DIM2", geometry["omega_stringer"]["DIM2_mm"], MIN_STRINGER_THICKNESS_MM),
    )
    thicknesses_passed = panel_thicknesses_passed
    for label, value, minimum in thickness_checks:
        thicknesses_passed = thicknesses_passed and value >= minimum
        print(
            f"{status(value >= minimum)} {label}: {value:g} mm (minimum {minimum:g} mm)",
            file=stream,
        )

    factors = collect_reserve_factors(result)
    failed = [factor for factor in factors if not reserve_factor_passes(factor.value)]
    print(
        f"{status(not failed)} Reserve factors: {len(factors) - len(failed)}/{len(factors)} are > 1",
        file=stream,
    )
    if failed:
        print(f"First {min(5, len(failed))} RF values not > 1:", file=stream)
        for factor in failed[:5]:
            value = f"{factor.value:.6g}"
            if use_color:
                value = f"\033[31m{value}\033[0m"
            print(f"  - {factor.label}: {value}", file=stream)
    else:
        print("First 5 RF values not > 1: none", file=stream)
    overall_passed = mass_passed and thicknesses_passed and not failed
    print(f"{status(overall_passed)} Overall design", file=stream)
