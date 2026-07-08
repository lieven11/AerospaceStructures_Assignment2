from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .models import RawStress


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_first_results_query_block(
    path: Path,
    element_ids: range,
    value_columns: tuple[str, ...],
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
    required_columns = ("Elements", "Loadcase", *value_columns)
    missing_columns = [name for name in required_columns if name not in header]
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
            result = tuple(float(row[column_indexes[name]]) for name in value_columns)
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


def load_query_stresses(stresses_path: Path, axial_path: Path) -> dict[int, RawStress]:
    panel_ids = range(1, 31)
    stringer_ids = range(37, 64)
    panel = _load_first_results_query_block(
        stresses_path,
        panel_ids,
        ("XX", "XY", "YY"),
    )
    axial = _load_first_results_query_block(axial_path, stringer_ids, ("1D Stress:CBAR Axial",))

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


def load_element_volumes(path: Path) -> dict[int, float]:
    volumes: dict[int, float] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            volumes[int(float(row["element_id"]))] = float(row["volume_mm3"])
    return volumes
