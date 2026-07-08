from __future__ import annotations

from .models import NormalizedStress, RawStress


def _zero(value: float | None) -> float:
    return 0.0 if value is None else value


def normalize_stresses(raw: dict[int, RawStress]) -> dict[int, NormalizedStress]:
    """Load stresses already arranged in the workbook's ordered Import schema.

    Incoming files contain XX, XY, YY, and axial values in final calculation
    order. No component min/max reordering is performed here.
    """
    normalized: dict[int, NormalizedStress] = {}
    for element_id, item in raw.items():
        normalized[element_id] = NormalizedStress(
            element_id=element_id,
            xx_case1=_zero(item.panel_xx_case1),
            xx_case2=_zero(item.panel_xx_case2),
            xy_case1=_zero(item.panel_xy_case1),
            xy_case2=_zero(item.panel_xy_case2),
            yy_case1=_zero(item.panel_yy_case1),
            yy_case2=_zero(item.panel_yy_case2),
            axial_case1=_zero(item.stringer_axial_case1),
            axial_case2=_zero(item.stringer_axial_case2),
        )
    return normalized
