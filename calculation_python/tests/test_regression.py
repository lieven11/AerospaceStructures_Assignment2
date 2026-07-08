from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aerospace_structures.calculation import run_calculation  # noqa: E402


class WorkbookMigrationRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_calculation(PROJECT_ROOT)
        cls.expected = json.loads(
            (PROJECT_ROOT / "expected" / "results_final_baseline.json").read_text(encoding="utf-8")
        )["values"]

    def test_results_final_matches_cached_workbook_values(self) -> None:
        actual = self.result["results_final"]
        self.assertEqual(len(actual), len(self.expected))
        for row_index, (actual_row, expected_row) in enumerate(zip(actual, self.expected), start=1):
            for column_index, (actual_value, expected_value) in enumerate(
                zip(actual_row, expected_row), start=1
            ):
                if expected_value is None:
                    self.assertIsNone(
                        actual_value,
                        msg=f"Unexpected value at row {row_index}, column {column_index}",
                    )
                elif isinstance(expected_value, (int, float)):
                    self.assertIsInstance(actual_value, (int, float))
                    self.assertTrue(
                        math.isclose(float(actual_value), float(expected_value), rel_tol=2e-12, abs_tol=2e-12),
                        msg=(
                            f"Mismatch at row {row_index}, column {column_index}: "
                            f"{actual_value!r} != {expected_value!r}"
                        ),
                    )
                else:
                    self.assertEqual(actual_value, expected_value)

    def test_mass_uses_geometry_derived_workbook_mass_computed(self) -> None:
        self.assertTrue(math.isclose(self.result["mass_kg"], 16.397640000000003, rel_tol=1e-14))

    def test_input_uses_ordered_import_schema(self) -> None:
        first = self.result["ordered_stresses"][0]
        self.assertEqual(first["xx_case1"], -66.018310546875)
        self.assertEqual(first["xy_case1"], 35.701557159424)
        self.assertEqual(first["yy_case1"], 22.834733963013)

    def test_xlsx_contains_only_results_final(self) -> None:
        path = PROJECT_ROOT / "outputs" / "Results_final.xlsx"
        with zipfile.ZipFile(path) as archive:
            root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        sheets = root.findall("x:sheets/x:sheet", namespace)
        self.assertEqual([sheet.attrib["name"] for sheet in sheets], ["Results_final"])


if __name__ == "__main__":
    unittest.main()
