from __future__ import annotations

from collections.abc import Iterable

from .models import AveragedPanelStress, AveragedStringerStress, NormalizedStress


def _weighted_average(
    element_ids: Iterable[int],
    values: dict[int, float],
    total_geometry_volume: float,
) -> float:
    ids = tuple(element_ids)
    geometry_subvolume = total_geometry_volume / len(ids)
    return sum(geometry_subvolume * values[element_id] for element_id in ids) / total_geometry_volume


def average_panels(
    stresses: dict[int, NormalizedStress],
    groups: list[list[int]],
    panel_volumes_mm3: list[float],
) -> list[AveragedPanelStress]:
    results: list[AveragedPanelStress] = []
    for panel_id, group in enumerate(groups, start=1):
        ids = tuple(group)
        total_volume = panel_volumes_mm3[panel_id - 1]
        results.append(
            AveragedPanelStress(
                panel_id=panel_id,
                element_ids=ids,
                volume_mm3=total_volume,
                xx_case1=_weighted_average(ids, {i: stresses[i].xx_case1 for i in ids}, total_volume),
                xx_case2=_weighted_average(ids, {i: stresses[i].xx_case2 for i in ids}, total_volume),
                xy_case1=_weighted_average(ids, {i: stresses[i].xy_case1 for i in ids}, total_volume),
                xy_case2=_weighted_average(ids, {i: stresses[i].xy_case2 for i in ids}, total_volume),
                yy_case1=_weighted_average(ids, {i: stresses[i].yy_case1 for i in ids}, total_volume),
                yy_case2=_weighted_average(ids, {i: stresses[i].yy_case2 for i in ids}, total_volume),
            )
        )
    return results


def average_stringers(
    stresses: dict[int, NormalizedStress],
    groups: list[list[int]],
    stringer_volumes_mm3: list[float],
) -> list[AveragedStringerStress]:
    results: list[AveragedStringerStress] = []
    for stringer_id, group in enumerate(groups, start=1):
        ids = tuple(group)
        total_volume = stringer_volumes_mm3[stringer_id - 1]
        results.append(
            AveragedStringerStress(
                stringer_id=stringer_id,
                element_ids=ids,
                volume_mm3=total_volume,
                axial_case1=_weighted_average(ids, {i: stresses[i].axial_case1 for i in ids}, total_volume),
                axial_case2=_weighted_average(ids, {i: stresses[i].axial_case2 for i in ids}, total_volume),
            )
        )
    return results
