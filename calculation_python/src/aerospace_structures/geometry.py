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
