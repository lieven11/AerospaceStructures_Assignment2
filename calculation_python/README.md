# Standalone Aerospace Structures Calculation

This project is a standalone Python migration of `Calculation.xlsx`. The source workbook is not read at runtime. All baseline geometry, material data, element volumes, grouping, and HyperMesh/solver stress inputs are copied into `inputs/`.

The numerical operations intentionally reproduce the workbook as implemented. No engineering equations, constants, signs, mappings, safety factors, or workbook-specific choices were corrected or reinterpreted.

## Run

Python 3.10 or newer is sufficient; there are no third-party runtime dependencies.

```bash
python3 run.py
```

Generated files:

- `outputs/calculation_results.json`: complete intermediate and final results
- `outputs/calculation_methodology.json`: equations and data-flow notes used by the calculation
- `outputs/Results_final.csv`: flat copy-friendly final worksheet
- `outputs/Results_final.xlsx`: workbook containing only `Results_final`
- `outputs/ordered_stresses.csv`: stress values after loading the ordered input schema
- `outputs/strength_results.csv`: von Mises, axial, and strength reserve-factor calculations
- `outputs/panel_volume_averages.csv`: panel volumes and volume-weighted stresses
- `outputs/stringer_volume_averages.csv`: stringer volumes and volume-weighted axial stresses
- `outputs/panel_buckling_results.csv`: panel buckling intermediate terms and final RFs
- `outputs/section_properties.csv`: T/omega areas, inertias, radii, slenderness, and critical stresses
- `outputs/column_buckling_results.csv`: combined stresses, critical stresses, and RFs
- `outputs/mass_breakdown.csv`: geometry area → volume → density → mass calculation

## Inputs

- `inputs/geometry.json`: skin, T-stringer, omega-stringer, and column geometry, including all DIM values
- `inputs/materials.json`: E, E B-basis, strengths, density, Poisson ratio, and ultimate load factor
- `inputs/layout.json`: panel/stringer element groups and section assignments
- `inputs/analysis_stresses.csv`: HyperMesh/solver stress input in the ordered `Import` layout; values are used directly without component reordering
- `inputs/element_volumes.csv`: copied finite-element volumes

Units follow the assignment convention: mm, tonne, s, N, mJ, MPa, and tonne/mm³. Exported mass is in kg.

## Calculation modules

- `stress_processing.py`: workbook stress-component reordering and absolute shear handling
- `strength.py`: von Mises/axial strength reserve factors
- `averaging.py`: element-volume-weighted panel and stringer stresses
- `mass.py`: geometry-derived skin/stringer areas, volumes, and mass (`Mass_computed` logic)
- `panel_buckling.py`: biaxial-plus-shear panel buckling
- `sections.py`: T/omega cross-section, crippling, Euler-Johnson, and Euler properties
- `column_buckling.py`: combined skin-stringer stress and final column reserve factors
- `results.py`: `Results_final` worksheet layout
- `excel_export.py`: dependency-free CSV/JSON/XLSX export

## Verify

```bash
python3 -m unittest discover -s tests -v
```

The regression test compares every populated cell in the generated `Results_final` matrix against the validated baseline, with the final mass intentionally changed to the geometry-derived `Mass_computed` value. The fixture is self-contained and does not read `Calculation.xlsx`.
