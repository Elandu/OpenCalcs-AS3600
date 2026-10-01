# Validation of the initial section adapter

This record covers nominal section mechanics. It is not an AS 3600 design verification.
Fixture inputs are in `examples/rectangular_section.json`; the coefficients were explicitly
selected for an analytical comparison and are not standard-derived defaults.

## Independent rectangular-section benchmark

For a 300 mm wide, 500 mm deep rectangle with three 500 mm² bars at y = 50 mm:

- Steel tension when yielded: `T = 1500 × 500 = 750000 N`.
- Compression block: `C = 0.8 × 32 × 300 × 0.8 × dn`.
- Zero axial force requires `C = T`, giving `dn = 122.0703125 mm`.
- Nominal moment: `T × (450 - 0.8 × dn / 2) / 1000000 = 300.87890625 kN·m`.
- Gross area: `150000 mm²`; displaced concrete: `148500 mm²`.
- Composite axial rigidity: `148500 × 30000 + 1500 × 200000 = 4.755e9 N`.
- Mass per metre: `148500 × 2400 / 1e6 + 1500 × 7850 / 1e6 = 368.175 kg/m`.

Capacity assertions use relative tolerance `1e-5`. The upstream neutral-axis solver uses
`xtol = 0.001 mm` and `rtol = 1e-6`. The adapter independently rejects axial residuals larger
than the greater of 1 N and `1e-5` of the sum of full concrete-block and steel force magnitudes.
The result includes the residual in kN. Equal-area bar polygons introduce small floating-point
differences in geometric properties.

## Additional checks

The suite covers compression and tension sign conventions, moments about the elastic centroid,
reversed bending, section rotation, geometric scaling, strict JSON output, invalid dimensions,
nonfinite inputs, overlapping/outside reinforcement, missing coefficients, steel fracture,
and axial loads outside the solver's equilibrium range. Reinforcement strain is checked at each
bar centroid because the upstream ultimate model treats bars as lumped areas.

Integration checks load the installed Python entry point, use the real OpenCalcs registry,
exercise its HTTP API, and check attached plugin provenance. CI installs the built wheel before
running tests and disables the source-path override so these checks exercise the distribution.
OpenCalcs is pinned to commit `fe875fa53678afbd0cce29937d1d7b30a1fb747d`.

Supported CI interpreters are Python 3.12 and 3.13. Engineering approval, authenticated
production execution and an OpenCalcs-UI concrete workbench are outside this package bootstrap.

## Bootstrap evidence, 1 October 2026

The final wheel was installed into a fresh local Windows Python 3.12 environment alongside
the pinned host. Imports resolved from `site-packages`, and all **36 tests passed** with the
source-path override disabled. One host dependency warning noted the deprecation of the
HTTPX-backed Starlette test client; there were no failed checks. Ruff lint and formatting,
bytecode compilation, dependency compatibility, and wheel/sdist builds also passed.

The initial CI matrix exposed that `concreteproperties` 0.8.0 requires Python >=3.12.
The package now advertises that minimum and tests Python 3.12 and 3.13. The initial Python
3.11 dependency-install failure was resolved by correcting the declared support range.
