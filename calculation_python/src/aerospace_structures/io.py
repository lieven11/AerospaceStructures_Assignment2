from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from .models import RawStress


ColumnSelector = str | tuple[str, ...]


ANALYSIS_STRESS_HEADER = [
    "ID",
    "Panel, XX, Case 1",
    "Panel, XX, Case 2",
    "Panel, XY, Case 1",
    "Panel, XY, Case 2",
    "Panel, YY, Case 1",
    "Panel, YY, Case 2",
    "Stringer, 1D, Case 1",
    "Stringer, 1D, Case 2",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _column_aliases(column: ColumnSelector) -> tuple[str, ...]:
    if isinstance(column, str):
        return (column,)
    return column


def _load_first_results_query_block(
    path: Path,
    element_ids: Sequence[int],
    value_columns: tuple[ColumnSelector, ...],
) -> dict[tuple[int, int], tuple[float, ...]]:
    """Read the first complete two-load-case block from a Results Query CSV.

    HyperMesh sometimes appends the same result block more than once. The export
    layout is fixed: case 1 is followed vertically by case 2. Reading exactly the
    first expected block prevents later duplicates from replacing the first values.
    """
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))

    header_index = next(
        (index for index, row in enumerate(rows) if row and row[0].strip() == "Elements"),
        None,
    )
    if header_index is None:
        raise ValueError(f"No Results Query data header found in {path}")

    header = [cell.strip() for cell in rows[header_index]]
    required_columns = ("Elements", "Loadcase")
    missing_columns = [name for name in required_columns if name not in header]
    value_column_indexes: list[int] = []
    for column in value_columns:
        aliases = _column_aliases(column)
        header_name = next((alias for alias in aliases if alias in header), None)
        if header_name is None:
            missing_columns.append(" or ".join(aliases))
            continue
        value_column_indexes.append(header.index(header_name))

    if missing_columns:
        raise ValueError(f"Missing columns in {path}: {', '.join(missing_columns)}")

    column_indexes = {name: header.index(name) for name in required_columns}
    expected_order = [
        (element_id, loadcase)
        for loadcase in (1, 2)
        for element_id in element_ids
    ]
    data_rows: list[tuple[int, list[str]]] = []
    for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not row or not row[0].strip():
            continue
        try:
            int(float(row[0]))
        except ValueError:
            continue
        data_rows.append((row_number, row))
        if len(data_rows) == len(expected_order):
            break

    if len(data_rows) != len(expected_order):
        raise ValueError(
            f"{path} contains {len(data_rows)} rows in its first result block; "
            f"expected {len(expected_order)}"
        )

    values: dict[tuple[int, int], tuple[float, ...]] = {}
    for (expected_element, expected_case), (row_number, row) in zip(expected_order, data_rows):
        try:
            element_id = int(float(row[column_indexes["Elements"]]))
            loadcase = int(float(row[column_indexes["Loadcase"]]))
            result = tuple(float(row[index]) for index in value_column_indexes)
        except (IndexError, ValueError) as exc:
            raise ValueError(f"Invalid result data in {path} at row {row_number}") from exc

        if (element_id, loadcase) != (expected_element, expected_case):
            raise ValueError(
                f"Unexpected row order in {path} at row {row_number}: found element "
                f"{element_id}, load case {loadcase}; expected element {expected_element}, "
                f"load case {expected_case}"
            )
        values[(element_id, loadcase)] = result

    return values


def load_query_stresses(
    stresses_path: Path,
    axial_path: Path,
    panel_element_ids: Sequence[int],
    stringer_element_ids: Sequence[int],
) -> dict[int, RawStress]:
    panel_ids = tuple(int(element_id) for element_id in panel_element_ids)
    stringer_ids = tuple(int(element_id) for element_id in stringer_element_ids)
    panel = _load_first_results_query_block(
        stresses_path,
        panel_ids,
        ("XX", "XY", "YY"),
    )
    axial = _load_first_results_query_block(
        axial_path,
        stringer_ids,
        (("1D Stress:CBAR Axial", "Element Stresses (1D):CBAR/CBEAM Axial Stress"),),
    )

    stresses: dict[int, RawStress] = {}
    for element_id in panel_ids:
        xx1, xy1, yy1 = panel[(element_id, 1)]
        xx2, xy2, yy2 = panel[(element_id, 2)]
        stresses[element_id] = RawStress(
            element_id=element_id,
            panel_xx_case1=xx1,
            panel_xx_case2=xx2,
            panel_xy_case1=xy1,
            panel_xy_case2=xy2,
            panel_yy_case1=yy1,
            panel_yy_case2=yy2,
            stringer_axial_case1=None,
            stringer_axial_case2=None,
        )

    for element_id in stringer_ids:
        stresses[element_id] = RawStress(
            element_id=element_id,
            panel_xx_case1=None,
            panel_xx_case2=None,
            panel_xy_case1=None,
            panel_xy_case2=None,
            panel_yy_case1=None,
            panel_yy_case2=None,
            stringer_axial_case1=axial[(element_id, 1)][0],
            stringer_axial_case2=axial[(element_id, 2)][0],
        )
    return stresses


def _optional_float(value: float | None) -> float | str:
    if value is None:
        return ""
    return value


def write_analysis_stresses(
    path: Path,
    stresses: dict[int, RawStress],
    row_ids: Iterable[int],
) -> None:
    """Write the legacy clean stress copy table regenerated from Results Query data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(ANALYSIS_STRESS_HEADER)
        for element_id in row_ids:
            stress = stresses.get(element_id)
            if stress is None:
                writer.writerow([element_id, "", "", "", "", "", "", "", ""])
                continue
            writer.writerow(
                [
                    element_id,
                    _optional_float(stress.panel_xx_case1),
                    _optional_float(stress.panel_xx_case2),
                    _optional_float(stress.panel_xy_case1),
                    _optional_float(stress.panel_xy_case2),
                    _optional_float(stress.panel_yy_case1),
                    _optional_float(stress.panel_yy_case2),
                    _optional_float(stress.stringer_axial_case1),
                    _optional_float(stress.stringer_axial_case2),
                ]
            )
