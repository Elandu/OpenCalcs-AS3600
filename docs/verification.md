# Repeatable section verification

The format follows the useful parts of the
[AutoCalcs verification page](https://autocalcs.com/as4100-design-calculator/verification):
named reference cases, expected/calculated values, differences and an explanation
of the comparison method. This package additionally records full inputs, units,
per-quantity tolerances, branch assumptions, runtime versions and individual outcomes.

## What the results establish

The numerical suite covers nominal section mechanics with explicitly supplied
material models. It does **not** establish AS 3600 design compliance.

- 21 original analytical cases cover area, displaced concrete, steel area, EA,
  elastic centroid, mass, EIxx/EIyy/EIxy, force equilibrium, neutral-axis depth,
  both moment components, resultant moment and maximum steel strain.
- Cases exercise yielded and unyielded tensile reinforcement, compression and
  tension axial forces, reversed bending, geometric scaling, asymmetric steel
  placement, and varied geometry/material coefficients.
- One rotation case checks a transformation relation between solver runs. It is
  explicitly labeled **metamorphic**, rather than an independent capacity reference.
- Three invalid-input cases check overlap, bar-edge clearance and infeasible load
  rejection. The broader test suite includes additional validation conditions.
- Separate upstream diagnostics retain four unresolved design-adapter blockers.
  They are not included in the mechanics pass count.

These are original analytical fixtures. No expectation is imported from the solver,
AutoCalcs, another design engine or a solver-generated snapshot. They are not
published textbook design examples. Future normative calculations must add reviewed
worked examples with source edition, problem/page, applicability and rounding notes.

## Independent reference mechanics

For a single tensile reinforcement row clear of the rectangular compression block:

1. Define `k = alpha * fc * b * gamma` and `d` from the compression face to the bars.
2. Yielded steel gives `T = As * fy` and `dn = (T + N) / k`.
3. Unyielded steel gives `T = As * Es * epscu * (d / dn - 1)`; solve the positive
   root of `k*dn^2 + (As*Es*epscu - N)*dn - As*Es*epscu*d = 0` independently.
4. Check the branch against yield strain, the fracture limit, bar fit/spacing and
   the compression block's clearance to every bar's near-face edge.
5. Sum concrete compression and steel tension moments about the independently
   derived elastic centroid. Positive N is compression.

Gross reference properties use transformed-area centroids and the parallel-axis
theorem. For the pinned model, concrete holes are equal-area regular 32-gons while
lumped steel's local inertia is treated by upstream as an equal-area circle. The
reference independently subtracts the concrete polygon contribution and adds the
steel circle contribution, rather than assuming their local inertias are identical.
The vertex count is a fixed fixture contract, tested against the adapter.

The baseline hand result is `dn=122.0703125 mm` and
`Mx=300.87890625 kN*m`. The calculation does not use AS 3600 default block factors.

## Tolerances and failure handling

The report declares absolute/relative tolerances for every metric. The larger
of the absolute allowance and `relative tolerance * abs(reference)` determines a
numeric pass. Zero references use absolute error; their relative difference is
not used to claim agreement. Stiffness cross-product residuals use a tolerance
scaled to the larger reference principal-axis EI, because subtracting large
moments of area introduces cancellation error.

Limits reflect the pinned numerical model, including the neutral-axis root's
0.001 mm absolute tolerance and geometric integration rounding. They are numerical
acceptance tolerances, not engineering design tolerances. Gross area permits
0.0001 mm2 of numerical residue; strain permits 1e-8 absolute error. Relevant
relative checks use 1e-5. Axial force permits 0.01 kN absolute error, and the adapter
also imposes its independently reported force-scale equilibrium limit.

Reference assumption failures, unexpected solver exceptions and exceeded
tolerances count as failed cases. Failed cases are never silently skipped. Tests
inject a wrong steel strain and a runtime exception to verify that the suite
reports failures. The mechanics CLI returns 1 if any case fails.

## Commands

Use the same Python environment that contains the plugin and pinned dependencies:

```powershell
python -m opencalcs_as3600.verification --output artifacts/mechanics.json
python -m opencalcs_as3600.upstream_audit --output artifacts/upstream-audit.json
python -m opencalcs_as3600.reporting --mechanics artifacts/mechanics.json --upstream artifacts/upstream-audit.json --output artifacts/verification.html
python -m pytest
```

The upstream audit intentionally returns **1** while its known blockers remain;
see [the amendment review](amendment-review.md). A successful report rendering
means an HTML file was generated, not that its listed checks all passed. Open
the page locally, filter by case name and expand results to inspect the comparisons.
The JSON records retain full numeric precision; HTML values are rounded for reading.

## CI and distribution evidence

CI builds and installs the wheel, then runs tests through the real pinned
OpenCalcs registry/API with the source-path override disabled. It also generates
mechanics and upstream JSON plus the HTML page for Python 3.12 and 3.13, uploading
them as workflow artifacts. Known upstream findings remain marked **blocked**.
Tests that reproduce a known dependency defect prove the diagnostic is accurate;
their passing status does not mean that dependency's design result is correct.

Release assets provide the distribution, checksums and recorded reports. Reports
are tied to the release/workflow commit and record package/dependency versions.
Authenticated production execution, the concrete browser workbench and engineering
approval remain outside this package verification.

## Recorded local review, 1 October 2026

The v0.1.1 wheel was installed into the Windows Python 3.12 validation environment
with the pinned OpenCalcs host. Imports resolved from `site-packages`. With the
source-path override disabled, **46 tests passed**, including registry/API integration,
failure injection and the four upstream diagnostics. One existing Starlette/HTTPX
test-client deprecation warning remained. Ruff lint/format checks, distribution
builds, bytecode compilation and dependency compatibility also passed.

The installed-wheel mechanics run passed **25/25 cases and 341 comparisons**.
The largest relative difference against a nonzero independent analytical reference
was **0.006688991%** (axial force in `two-bar-negative-axial`), within its explicit
absolute force tolerance. All four upstream design integration findings remained
**blocked**; the audit returned 1 as designed. The steel-strain diagnostic infers
steel stress from two actual upstream squash-load runs with identical concrete,
and a test confirms it responds when that upstream strain defect is corrected.

The generated HTML contained 25 case sections and 371 table rows. Browser visual
and interaction verification remained **unverified**: navigation was rejected
because the in-app browser could not verify saved permissions. The numerical
adapter `analysis.py` was unchanged by this amendment/verification release.
