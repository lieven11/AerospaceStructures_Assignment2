# Standalone Aerospace Structures Calculation

This project is a standalone Python migration of `Calculation.xlsx`. The source workbook is not read at runtime. Baseline geometry, material data, element volumes, and grouping are stored in `inputs/`; current HyperMesh stresses are read from `../Results_Querey/`.

The numerical operations intentionally reproduce the workbook as implemented. No engineering equations, constants, signs, mappings, safety factors, or workbook-specific choices were corrected or reinterpreted.

## Run

Python 3.10 or newer is sufficient; there are no third-party runtime dependencies.

```bash
python3 run.py
```

The terminal prints a pass/fail summary for the 19.8505 kg mass limit, minimum
thicknesses, and all reserve factors. It also lists the first five RF values that
are not greater than 1. Each of the ten panel thicknesses must be at least 1.2 mm;
T-stringer `DIM4` and omega-stringer `DIM2` must be at least 1.0 mm. These
minimums cannot be overridden, and invalid geometry is rejected before any
output is changed. In `Results_final.xlsx`,
RF cells greater than 1 are green and RF cells less than or equal to 1 are red.

Generated files:

- `outputs/calculation_results.json`: complete intermediate and final results
- `outputs/calculation_methodology.json`: equations and data-flow notes used by the calculation
- `outputs/Results_final.csv`: semicolon-delimited official submission-template layout
- `outputs/Results_final.xlsx`: workbook containing the same populated submission layout
- `outputs/ordered_stresses.csv`: stress values after loading the ordered input schema
- `outputs/strength_results.csv`: von Mises, axial, and strength reserve-factor calculations
- `outputs/panel_volume_averages.csv`: panel volumes and volume-weighted stresses
- `outputs/stringer_volume_averages.csv`: stringer volumes and volume-weighted axial stresses
- `outputs/panel_buckling_results.csv`: panel buckling intermediate terms and final RFs
- `outputs/section_properties.csv`: T/omega areas, inertias, radii, slenderness, and critical stresses
- `outputs/column_buckling_results.csv`: combined stresses, critical stresses, and RFs
- `outputs/mass_breakdown.csv`: geometry area → volume → density → mass calculation

## Inputs

- `inputs/geometry.json`: ten individually editable panel thicknesses plus T-stringer, omega-stringer, and column geometry
- `inputs/materials.json`: E, E B-basis, strengths, density, Poisson ratio, and ultimate load factor
- `inputs/layout.json`: panel/stringer element groups and section assignments
- `../Results_Querey/Stresses.csv`: panel XX/XY/YY for elements 1-30, with load case 1 followed by load case 2
- `../Results_Querey/Axial.csv`: stringer axial stress for elements 37-63, with load case 1 followed by load case 2
- `inputs/element_volumes.csv`: copied finite-element volumes

The reader consumes exactly the first complete two-load-case block from each Results Query file. Any duplicate blocks appended by HyperMesh are ignored.

Set the ten panel thicknesses, in panel-ID order, in `inputs/geometry.json`:

```json
"panel_thicknesses_mm": [3.9, 3.9, 3.9, 3.9, 3.9, 3.9, 3.9, 3.9, 3.9, 3.9]
```

The list must contain exactly ten numeric values and every value must be at least
`1.2`. Panel `i` affects its own panel-buckling calculation and mass. It also
affects the combined section and column-buckling calculation of stringers `i-1`
and `i` where those adjacent stringers exist.

Units follow the assignment convention: mm, tonne, s, N, mJ, MPa, and tonne/mm³. Exported mass is in kg.

## Calculation modules

- `stress_processing.py`: workbook stress-component reordering and absolute shear handling
- `strength.py`: von Mises/axial strength reserve factors
- `averaging.py`: element-volume-weighted panel and stringer stresses
- `mass.py`: geometry-derived skin/stringer areas, volumes, and mass (`Mass_computed` logic)
- `panel_buckling.py`: biaxial-plus-shear panel buckling
- `sections.py`: stringer-specific T/omega combined cross-sections using half of each adjacent panel, including unequal panel thicknesses
- `column_buckling.py`: combined skin-stringer stress and final column reserve factors
- `results.py`: official submission-template population and `Results_final` layout
- `excel_export.py`: dependency-free CSV/JSON/XLSX export

## Verify

```bash
python3 -m unittest discover -s tests -v
```

The regression test compares every populated cell in the generated `Results_final` matrix against the validated baseline, with the final mass intentionally changed to the geometry-derived `Mass_computed` value. The fixture is self-contained and does not read `Calculation.xlsx`.
