from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .models import RawStress


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _number(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    return float(value)


def load_raw_stresses(path: Path) -> dict[int, RawStress]:
    stresses: dict[int, RawStress] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            element_id = int(float(row["ID"]))
            stresses[element_id] = RawStress(
                element_id=element_id,
                panel_xx_case1=_number(row["Panel, XX, Case 1"]),
                panel_xx_case2=_number(row["Panel, XX, Case 2"]),
                panel_xy_case1=_number(row["Panel, XY, Case 1"]),
                panel_xy_case2=_number(row["Panel, XY, Case 2"]),
                panel_yy_case1=_number(row["Panel, YY, Case 1"]),
                panel_yy_case2=_number(row["Panel, YY, Case 2"]),
                stringer_axial_case1=_number(row["Stringer, 1D, Case 1"]),
                stringer_axial_case2=_number(row["Stringer, 1D, Case 2"]),
            )
    return stresses


def load_element_volumes(path: Path) -> dict[int, float]:
    volumes: dict[int, float] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            volumes[int(float(row["element_id"]))] = float(row["volume_mm3"])
    return volumes

