from __future__ import annotations

from collections.abc import Iterable

from .models import AveragedPanelStress, AveragedStringerStress, NormalizedStress


def _weighted_average(
    element_ids: Iterable[int],
    values: dict[int, float],
    volumes: dict[int, float],
) -> float:
    ids = tuple(element_ids)
    total_volume = sum(volumes[element_id] for element_id in ids)
    return sum(volumes[element_id] * values[element_id] for element_id in ids) / total_volume


def average_panels(
    stresses: dict[int, NormalizedStress],
    volumes: dict[int, float],
    groups: list[list[int]],
    panel_volumes_mm3: list[float] | None = None,
) -> list[AveragedPanelStress]:
    results: list[AveragedPanelStress] = []
    for panel_id, group in enumerate(groups, start=1):
        ids = tuple(group)
        total_volume = sum(volumes[element_id] for element_id in ids)
        results.append(
            AveragedPanelStress(
                panel_id=panel_id,
                element_ids=ids,
                volume_mm3=(
                    panel_volumes_mm3[panel_id - 1]
                    if panel_volumes_mm3 is not None
                    else total_volume
                ),
                xx_case1=_weighted_average(ids, {i: stresses[i].xx_case1 for i in ids}, volumes),
                xx_case2=_weighted_average(ids, {i: stresses[i].xx_case2 for i in ids}, volumes),
                xy_case1=_weighted_average(ids, {i: stresses[i].xy_case1 for i in ids}, volumes),
                xy_case2=_weighted_average(ids, {i: stresses[i].xy_case2 for i in ids}, volumes),
                yy_case1=_weighted_average(ids, {i: stresses[i].yy_case1 for i in ids}, volumes),
                yy_case2=_weighted_average(ids, {i: stresses[i].yy_case2 for i in ids}, volumes),
            )
        )
    return results


def average_stringers(
    stresses: dict[int, NormalizedStress],
    volumes: dict[int, float],
    groups: list[list[int]],
) -> list[AveragedStringerStress]:
    results: list[AveragedStringerStress] = []
    for stringer_id, group in enumerate(groups, start=1):
        ids = tuple(group)
        total_volume = sum(volumes[element_id] for element_id in ids)
        results.append(
            AveragedStringerStress(
                stringer_id=stringer_id,
                element_ids=ids,
                volume_mm3=total_volume,
                axial_case1=_weighted_average(ids, {i: stresses[i].axial_case1 for i in ids}, volumes),
                axial_case2=_weighted_average(ids, {i: stresses[i].axial_case2 for i in ids}, volumes),
            )
        )
    return results
