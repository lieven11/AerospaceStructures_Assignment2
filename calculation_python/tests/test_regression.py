from __future__ import annotations

import csv
import json
import math
import shutil
from contextlib import redirect_stdout
from io import StringIO
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aerospace_structures.calculation import run_calculation  # noqa: E402
from aerospace_structures.cli import confirm_thickness_violations, run_cli  # noqa: E402
from aerospace_structures.history import COMPARISON_FILE_NAME, MAX_HISTORY_RECORDS  # noqa: E402
from aerospace_structures.io import load_query_stresses  # noqa: E402
from aerospace_structures.mass import calculate_geometry_mass  # noqa: E402
from aerospace_structures.models import AveragedPanelStress  # noqa: E402
from aerospace_structures.panel_buckling import calculate_panel_buckling  # noqa: E402
from aerospace_structures.reporting import reserve_factor_passes  # noqa: E402
from aerospace_structures.sections import calculate_t_section  # noqa: E402


class WorkbookMigrationRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_calculation(PROJECT_ROOT)

    def test_results_final_has_expected_shape(self) -> None:
        actual = self.result["results_final"]
        self.assertEqual(len(actual), 155)
        self.assertTrue(all(len(row) == 16 for row in actual))

    def test_results_final_uses_submission_template_layout(self) -> None:
        actual = self.result["results_final"]
        self.assertEqual(actual[18][0], "Cross-section dimensions and element offsets")
        self.assertEqual(actual[42][0], "Strength Analysis")
        self.assertEqual(actual[104][0], "Stability Analysis - Panel Buckling")
        self.assertEqual(actual[119][0], "Stability Analysis - Column Buckling")

    def test_geometry_dimensions_and_placeholder_offsets_are_exported(self) -> None:
        actual = self.result["results_final"]
        self.assertEqual(actual[20][1:3], [3.9, 1.0])
        self.assertEqual(actual[31][1:4], [2.1, 42.0, 3.0])  # T stringer 1
        self.assertEqual(actual[33][1:4], [2.4, 28.0, 3.0])  # Omega stringer 3

    def test_mass_uses_geometry_derived_workbook_mass_computed(self) -> None:
        self.assertTrue(math.isclose(self.result["mass_kg"], 16.397640000000003, rel_tol=1e-14))

    def test_input_uses_first_results_query_block(self) -> None:
        stresses = self.result["ordered_stresses"]
        self.assertEqual(len(stresses), 57)
        self.assertEqual([item["element_id"] for item in stresses[:2]], [1, 2])
        self.assertEqual([item["element_id"] for item in stresses[-2:]], [62, 63])

    def test_repeated_results_query_blocks_are_ignored(self) -> None:
        panel_rows = ["Elements,FileID,Loadcase,Step,Layer,XX,XY,YY,"]
        axial_rows = ["Elements,FileID,Loadcase,Step,1D Stress:CBAR Axial,"]
        for loadcase in (1, 2):
            for element_id in range(1, 31):
                base = loadcase * 1000 + element_id
                panel_rows.append(
                    f"{element_id},2,{loadcase},0,average,{base + 0.1},{base + 0.2},{base + 0.3},"
                )
            for element_id in range(37, 64):
                axial_rows.append(f"{element_id},2,{loadcase},0,{-loadcase * 1000 - element_id},")

        first_panel_block = "\n".join(panel_rows)
        first_axial_block = "\n".join(axial_rows)
        conflicting_panel_block = first_panel_block.replace("1001.1", "9999", 1)
        conflicting_axial_block = first_axial_block.replace("-1037", "9999", 1)

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            stresses_path = temporary_path / "Stresses.csv"
            axial_path = temporary_path / "Axial.csv"
            stresses_path.write_text(
                f"{first_panel_block}\n{conflicting_panel_block}",
                encoding="utf-8",
            )
            axial_path.write_text(
                f"{first_axial_block}\n{conflicting_axial_block}",
                encoding="utf-8",
            )
            stresses = load_query_stresses(stresses_path, axial_path)

        self.assertEqual(stresses[1].panel_xx_case1, 1001.1)
        self.assertEqual(stresses[37].stringer_axial_case1, -1037.0)

    def test_xlsx_contains_only_results_final(self) -> None:
        path = PROJECT_ROOT / "outputs" / "Results_final.xlsx"
        with zipfile.ZipFile(path) as archive:
            root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        sheets = root.findall("x:sheets/x:sheet", namespace)
        self.assertEqual([sheet.attrib["name"] for sheet in sheets], ["Results_final"])

    def test_xlsx_colors_passing_and_failing_reserve_factors(self) -> None:
        path = PROJECT_ROOT / "outputs" / "Results_final.xlsx"
        with zipfile.ZipFile(path) as archive:
            root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        cells = {cell.attrib["r"]: cell for cell in root.findall(".//x:c", namespace)}
        self.assertEqual(cells["B46"].attrib["s"], "2")  # RF > 1: green
        self.assertEqual(cells["O108"].attrib["s"], "3")  # RF <= 1: red

    def test_thickness_guard_cannot_be_overridden(self) -> None:
        geometry = {
            "skin": {
                "panel_count": 10,
                "panel_thicknesses_mm": [1.1] + [3.9] * 9,
            },
            "t_stringer": {"DIM4_mm": 1.0},
            "omega_stringer": {"DIM2_mm": 1.0},
        }
        output = StringIO()
        self.assertFalse(
            confirm_thickness_violations(
                geometry,
                input_stream=StringIO("Y\n"),
                output_stream=output,
            )
        )
        self.assertIn("Panel 1 thickness: 1.1 mm", output.getvalue())
        self.assertIn("cannot be overridden", output.getvalue())

    def test_panel_thickness_list_requires_exactly_ten_values(self) -> None:
        geometry = {
            "skin": {
                "panel_count": 10,
                "panel_thicknesses_mm": [3.9] * 9,
            },
            "t_stringer": {"DIM4_mm": 2.1},
            "omega_stringer": {"DIM2_mm": 2.4},
        }
        output = StringIO()
        self.assertFalse(confirm_thickness_violations(geometry, output_stream=output))
        self.assertIn("contains 9 values; expected 10", output.getvalue())

    def test_individual_panel_thickness_propagates_to_mass_and_section(self) -> None:
        geometry = {
            "skin": {
                "panel_thicknesses_mm": [4.9] + [3.9] * 9,
                "panel_length_mm": 600.0,
                "panel_width_mm": 200.0,
                "panel_count": 10,
            },
            "t_stringer": {
                "count": 4,
                "DIM1_mm": 65.0,
                "DIM2_mm": 42.0,
                "DIM3_mm": 3.0,
                "DIM4_mm": 2.1,
            },
            "omega_stringer": {
                "count": 5,
                "DIM1_mm": 28.0,
                "DIM2_mm": 2.4,
                "DIM3_mm": 20.0,
                "DIM4_mm": 15.0,
            },
            "column": {
                "effective_width_mm": 200.0,
                "length_mm": 600.0,
                "effective_length_factor": 1.0,
            },
        }
        mass = calculate_geometry_mass(geometry, 2.7e-9)
        self.assertTrue(math.isclose(mass.total_mass_kg, 16.72164, rel_tol=1e-14))
        self.assertEqual(mass.components[0].component, "skin_panel_1")
        self.assertTrue(
            math.isclose(mass.components[0].cross_section_area_mm2, 980.0, rel_tol=1e-14)
        )

        baseline = calculate_t_section(geometry, 491.79, 65643.64, 3.9, 3.9)
        modified = calculate_t_section(geometry, 491.79, 65643.64, 4.9, 3.9)
        self.assertNotEqual(modified.second_moment_mm4, baseline.second_moment_mm4)
        self.assertNotEqual(modified.radius_of_gyration_mm, baseline.radius_of_gyration_mm)

    def test_panel_buckling_uses_each_panels_own_thickness(self) -> None:
        panels = [
            AveragedPanelStress(
                panel_id=panel_id,
                element_ids=(panel_id,),
                volume_mm3=1.0,
                xx_case1=-80.0,
                xx_case2=-30.0,
                xy_case1=20.0,
                xy_case2=10.0,
                yy_case1=10.0,
                yy_case2=5.0,
            )
            for panel_id in (1, 2)
        ]
        results = calculate_panel_buckling(
            panels,
            65643.64,
            0.34,
            600.0,
            200.0,
            [3.9, 4.9],
            1.5,
        )
        self.assertGreater(results[1].sigma_e_mpa, results[0].sigma_e_mpa)
        self.assertGreater(results[1].rf_case1, results[0].rf_case1)

    def test_non_numeric_reserve_factor_fails(self) -> None:
        self.assertTrue(reserve_factor_passes(1.0001))
        self.assertFalse(reserve_factor_passes(1.0))
        self.assertFalse(reserve_factor_passes("NaN"))


class RunHistoryTest(unittest.TestCase):
    def _copy_project(self, temporary_path: Path) -> Path:
        project_copy = temporary_path / "calculation_python"
        shutil.copytree(
            PROJECT_ROOT,
            project_copy,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                ".pytest_cache",
                "run_history",
                COMPARISON_FILE_NAME,
            ),
        )
        shutil.copytree(PROJECT_ROOT.parent / "Results_Querey", temporary_path / "Results_Querey")
        shutil.copy2(
            PROJECT_ROOT.parent / "AS_Project_Part2_SubmissionTemplate_3766785.csv",
            temporary_path / "AS_Project_Part2_SubmissionTemplate_3766785.csv",
        )
        return project_copy

    def _comparison_rows(self, project_root: Path) -> list[dict[str, str]]:
        with (project_root / "outputs" / COMPARISON_FILE_NAME).open(
            newline="",
            encoding="utf-8",
        ) as handle:
            return list(csv.DictReader(handle))

    def test_successful_cli_style_run_updates_one_comparison_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = self._copy_project(Path(temporary_directory))
            result = run_calculation(project_root, record_history=True)
            comparison_path = project_root / "outputs" / COMPARISON_FILE_NAME
            rows = self._comparison_rows(project_root)

            self.assertTrue(comparison_path.exists())
            self.assertFalse((project_root / "run_history").exists())
            self.assertTrue(all(row["is_latest"] == "yes" for row in rows))
            self.assertIn("mass_kg", {row["metric"] for row in rows})
            self.assertIn("minimum_overall_rf", {row["metric"] for row in rows})
            self.assertEqual(result["history"]["previous_run_id"], None)

    def test_second_comparison_run_compares_against_first_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = self._copy_project(Path(temporary_directory))
            first = run_calculation(project_root, record_history=True)
            geometry_path = project_root / "inputs" / "geometry.json"
            geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
            geometry["skin"]["panel_thicknesses_mm"][0] += 0.1
            geometry_path.write_text(json.dumps(geometry, indent=2) + "\n", encoding="utf-8")
            second = run_calculation(project_root, record_history=True)

            latest_rows = {
                row["metric"]: row
                for row in self._comparison_rows(project_root)
                if row["is_latest"] == "yes"
            }

            self.assertEqual(second["history"]["previous_run_id"], first["history"]["run_id"])
            self.assertEqual(latest_rows["mass_kg"]["previous_run_id"], first["history"]["run_id"])
            self.assertNotEqual(latest_rows["mass_kg"]["delta_vs_previous"], "")
            self.assertEqual(latest_rows["mass_kg"]["comparison_vs_previous"], "worse")
            self.assertEqual(latest_rows["panel_1_thickness_mm"]["comparison_vs_previous"], "changed")
            self.assertGreater(second["history"]["changed_metrics"], 0)

    def test_official_output_paths_stay_unchanged_when_history_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = self._copy_project(Path(temporary_directory))
            run_calculation(project_root, record_history=True)

            self.assertTrue((project_root / "outputs" / "Results_final.csv").exists())
            self.assertTrue((project_root / "outputs" / "Results_final.xlsx").exists())

    def test_comparison_file_retention_keeps_last_ten_successful_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = self._copy_project(Path(temporary_directory))
            geometry_path = project_root / "inputs" / "geometry.json"
            first_run_id = None
            for index in range(MAX_HISTORY_RECORDS + 2):
                geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
                geometry["skin"]["panel_thicknesses_mm"][0] = 3.9 + index * 0.01
                geometry_path.write_text(json.dumps(geometry, indent=2) + "\n", encoding="utf-8")
                result = run_calculation(project_root, record_history=True)
                if first_run_id is None:
                    first_run_id = result["history"]["run_id"]
            run_ids = {
                row["run_id"]
                for row in self._comparison_rows(project_root)
            }

            self.assertEqual(len(run_ids), MAX_HISTORY_RECORDS)
            self.assertNotIn(first_run_id, run_ids)

    def test_failed_thickness_validation_creates_no_comparison_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = self._copy_project(Path(temporary_directory))
            geometry_path = project_root / "inputs" / "geometry.json"
            geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
            geometry["skin"]["panel_thicknesses_mm"][0] = 1.1
            geometry_path.write_text(json.dumps(geometry, indent=2) + "\n", encoding="utf-8")

            output = StringIO()
            with redirect_stdout(output):
                exit_code = run_cli(project_root)

            self.assertEqual(exit_code, 1)
            self.assertFalse((project_root / "run_history").exists())
            self.assertFalse((project_root / "outputs" / COMPARISON_FILE_NAME).exists())


if __name__ == "__main__":
    unittest.main()
