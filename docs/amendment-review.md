# Amendment and dependency review

Reviewed 1 October 2026 against the `v0.1.0` mechanics implementation and pinned
`concreteproperties` 0.8.0 / `sectionproperties` 3.10.2. This review accompanies the
repeatable [numerical verification](verification.md).

## Finding

The current plugin calculates **nominal section mechanics**. It does not implement
AS 3600 design checks. No normative amendment is automatically applied by accepting
a caller-supplied material coefficient. `standard=None` and
`standard_compliance_evaluated=false` correctly describe that boundary.

**Do not enable the upstream AS3600 design adapter unchanged.** Four bounded
diagnostics below show missing amendment coverage and two squash-load defects.
The generic solver used by this plugin does not call those design-adapter methods.
The defects therefore do not invalidate the independently verified nominal
mechanics cases, but prevent treating the upstream design adapter as verified.

## References and review method

- AS 3600:2018, local consolidated copy incorporating Amendment 1:2018. Its
  amendment control sheet lists the November 2018 corrections. A1 was reviewed
  as incorporated text; no standalone A1 replacement-text comparison was available.
- AS 3600:2018 Amendment 2:2021, 22 pages, published 21 May 2021. All 22 pages were
  inspected, including tables, formula layout, notes and the replacement figures.
- The amendment initially rendered blank in MuPDF, PDFium and Poppler. Its
  document content layer was isolated **in memory** for local rendering, excluding
  the unrelated overlay layers. The original file was not changed or re-exported.
  Extracted text was checked against those rendered pages before interpretation.
- Local source review of `analysis.py`, `schemas.py`, `plugin.py` and the pinned
  dependency's `design_codes/as3600.py` and `stress_strain_profile.py`.

This is an amendment impact/coverage audit for the existing plugin, with a bounded
review of a possible future dependency. It is not an independent engineering
approval or a clause-by-clause verification of the whole standard. Licensed
documents, rendered pages, extracted text and reference-owner details are not
distributed. The interpretations below are original summaries.

## Reproduced upstream integration blockers

Run `python -m opencalcs_as3600.upstream_audit --output upstream-audit.json`.
It intentionally returns exit status **1** while a listed blocker remains.
The report records expected/actual values and keeps these failures separate from
the passing mechanics benchmarks.

| ID | Reference | Evidence and impact | Required action before enabling design checks |
| --- | --- | --- | --- |
| upstream-squash-fc80 | 10.6.2.2 | For a 300 x 500 mm section, 1500 mm2 of 500 MPa steel and 80 MPa concrete, independent squash load is **9,778,800 N**; upstream returns approximately **12,630,000 N**, **29.157% high**. The generated service profile inherits a getter returning `None`; `squash_tensile_load()` consequently chooses alpha1=1. | Derive the squash factor from characteristic ultimate concrete strength; verify intermediate strengths and both factor limits. An unconditional factor of 1 is unsafe for this design path. |
| upstream-squash-steel-strain | 10.6.2.2(b) | Upstream evaluates steel at **0.025** strain, versus the reviewed **0.0025** cap. Default 500 MPa steel masks the error because it has yielded in both states. A 600 MPa/200 GPa material accepted by the factory gives 600 versus 500 MPa, exposing the difference. | Correct the strain; also review admissible reinforcement strengths/classes. This custom material comparison does not assert that arbitrary 600 MPa steel is approved by the standard. |
| upstream-fc120 | A2 3.1.1.1 and Table 3.1.2 | The amended reference includes a 120 MPa grade and an elastic modulus of 44,400 MPa. The upstream factory rejects strengths above 100 MPa. | Extend and verify the intended design domain, or explicitly declare a narrower domain. The plugin's generic acceptance of caller-supplied 120 MPa material is not a normative material check. |
| upstream-compression-context | A2 Table 2.2.2(d) | A qualifying short column with Q/G=0.30 and Nu>=Nub uses 0.65 in the reviewed table; upstream's default phi0=0.60 yields 0.60. This particular difference is conservative. The API cannot derive the selection because it lacks member/action context. | Add reviewed context-based selection or require an explicit, validated factor. Do not replace the constant globally: other regimes still use 0.60. |

These four diagnostics are a small set of integration gates, not a complete audit
of upstream capacity reduction, interaction diagrams, service stresses or design
domains. Shape-dependent block reductions, steel classification inferred from
fracture strain, and axial/biaxial applicability need further review before use.

## Amendment 1 coverage

The consolidated document's control sheet identifies the following affected
references. All are accounted for here; this table maps the incorporated provisions
to the implemented scope, without reconstructing the standalone amendment's edits.

| A1 references | Relevance to this plugin | Coverage / next verification |
| --- | --- | --- |
| 8.1.3 | Directly related to a rectangular compression block. Reviewed incorporated formula/notes include strength-dependent factors, ultimate strain and shape reductions. | Caller supplies alpha, gamma and strain in `_build_section()`. Generic equilibrium is tested; standard factor derivation and applicability are **not implemented**. Oblique compression of a rectangle must receive a separate shape-applicability review before normative use. |
| 8.1.5 | Compression reinforcement provisions. | Lumped steel mechanics are analysed; reinforcement restraint is **not checked**. |
| 3.1.7.2; 9.4.4.1 | Shrinkage and long-term deflection. | **Not implemented**; gross uncracked EI does not establish serviceability. |
| 4.10.3.7 | Cover/durability detailing. | Geometric bar clearance is a solver requirement; normative cover is **not checked**. |
| 5.6.3; 5.6.4; Table 5.7.2 | Fire design. | **Not implemented**. |
| 8.2.3.4; 8.2.4.2.1; 8.2.7; 8.2.8.3 | Shear/torsion interaction and longitudinal reinforcement. | **Not implemented**; several are subsequently affected by A2. |
| 14.5.2.2; 14.6.7 | Earthquake reinforcement. | **Not implemented**; nominal bending does not establish ductility/detailing. |
| 17.4.1; 17.4.2 | Construction joints and embedded items. | **Not implemented**. |
| Table 2.4; 18.3; 18.4 | Fatigue. | **Not implemented**; follow the A2 corrections where applicable. |
| 19.3.1 | Fixings. | **Not implemented**. |
| 20.4.3; 21.3.2 | Plain concrete/footings. | **Not implemented**; the plugin requires reinforcement and returns no footing design check. |

## Amendment 2 impact matrix

Page numbers refer to the amendment PDF, not the base standard. "Not implemented"
means the plugin neither evaluates nor reports a pass for that requirement. Gross
geometry outputs and equilibrium checks are related mechanics, not substitutes
for the missing design checks. Rows group related edits while retaining their
clause/table/equation/figure identifiers.

| A2 references / PDF page | Original interpretation of the change | Code location and coverage / verification needed |
| --- | --- | --- |
| Contents; global symbols; 1.1.2; 1.7 / 1-2 | Correct appendix references, distinguish cylinder strength and clarify symbols for column dimensions, fibres, prestress and wall height. | `schemas.py` uses descriptive names. No cylinder/cube classification, wall-height or prestress model. Future material/geometry checks need explicit semantics. |
| 2.1.2 / 2 | Clarify the earthquake design statement. | No global earthquake analysis or ductility factor selection. **Not implemented**. |
| Table 2.2.2 / 2 | Compression capacity factor depends on column/action regime; prestress-at-transfer note added. | No phi applied by `run_analysis()`. Upstream context gap reproduced above. Test short/slender regimes, Q/G boundary, balanced load and transfer cases before implementation. |
| Table 2.2.5 note / 2 | Clarify serviceability-factor wording. | No standard serviceability factor selection. **Not implemented**. |
| 2.5.2.2; 2.5.2.3; Table 2.5.2.3(B) / 2-3 | Revise prestress combinations and fatigue terminology. | Input axial load is already specified; no combinations, tendons or fatigue checks. **Not implemented**. |
| 3.1.1.1; Table 3.1.1.1 / 3-4 | Expand material strength domain and distinguish cylinder/cube/grout strengths and conversion. | `_build_section()` accepts an explicit generic strength. No normative classification or conversion. Upstream 120 MPa coverage gap reproduced. |
| Table 3.1.2 / 4 | Extend strength-dependent material table, including the high-strength grade. | Caller supplies E; no standard table lookup. Upstream 20-100 MPa E values match the reviewed row, but the 120 MPa endpoint is missing. Verify grade endpoints and permitted interpolation separately. |
| Table 3.2.1 / 4 | Correct stainless reinforcement strength entry. | Caller supplies fy; no product type/grade field. Upstream steel factory accepts a strength rather than selecting by product standard. **Normative material selection not implemented**. |
| 3.3.4.2 / 4 | Remove a tendon relaxation paragraph. | No prestressing. **Not implemented**. |
| 4.10.2; 4.10.3.2 / 4 | Cover text and heading clarified. | Bar fit/overlap validation is geometric only. **Durability/cover not implemented**. |
| 5.3.1; 5.6.3; Tables 5.6.3/5.6.4 / 4-5 | Clarify fire column guidance, reinforcement ratios, gross-area basis and column dimensions. | Area output is available, but no fire model or fire-domain ratio check. **Not implemented**. |
| 5.7.2; Table 5.7.2; 5.7.4.1 / 5 | Correct wall-thickness terminology for fire checks. | No wall fire calculation. **Not implemented**. |
| 6.2.7.1 / 5 | Correct crack-opening terminology. | No nonlinear frame/fibre model. **Not implemented**. |
| 8.1.4 / 5 | Concentrated-force/prestress dispersion and splitting/bursting design clarified. | No bearing-zone or strut-and-tie model. **Not implemented**. |
| 8.1.5 / 6 | Correct restraint cross-references. | Lumped steel response does not check transverse restraint. **Not implemented**. |
| 8.2.1.2 / 6 | Correct torsion/shear references and remove superseded text. | No torsion trigger or shear model. **Not implemented**. |
| 8.2.1.3 / 6 | Prestress vertical-component sign and factors depend on whether it increases or reduces shear. | No prestress or shear input. **Not implemented**; test both signs and transfer conditions in a future adapter. |
| 8.2.1.5; Eq 8.2.1.5 / 6 | Duct width uses the sum across the web. | No ducts or effective web width. **Not implemented**. |
| 8.2.1.6; 8.2.1.7 / 6-7 | Revise transverse reinforcement triggers, depth dependence and minimum reinforcement wording. | No transverse reinforcement. **Not implemented**; boundary cases must cover depth transitions and shear/torsion triggers. |
| 8.2.3.1; 8.2.3.2 / 7 | Revise shear/torsion design inequalities, shear depth and support-face crushing requirement. | No shear/torsion demand or resistance. **Not implemented**. |
| 8.2.3.3; 8.2.3.4 / 7-8 | Consolidate crushing provisions and revise combined shear/torsion limits by section type. | No web-crushing check. **Not implemented**; no inference from successful nominal flexure. |
| 8.2.4.1 / 8 | Clarify strength cap and eligibility for simplified shear method. | No general/simplified shear selection. **Not implemented**. |
| 8.2.4.2.1 / 8-9 | Revise compression-strut-angle relationship and equation numbering. | Neutral-axis angle in this plugin is unrelated to the shear strut angle. **Not implemented**. |
| 8.2.4.2.2; Eqs (1)/(2) / 9 | Revise longitudinal-strain equations, bounds, moment floor and prestress terms. | No mid-depth shear strain model. **Not implemented**; test tensile/compressive branches and action signs. |
| 8.2.4.2.3; Eqs (1)/(2)/(3) / 9-10 | Revise combined shear/torsion strain and minimum moment conditions. | No corresponding analysis. **Not implemented**. |
| 8.2.4.3 / 10 | Revise simplified concrete shear contribution and domain. | No simplified shear model. **Not implemented**. |
| 8.2.5; 8.2.5.4; 8.2.5.5; 8.2.5.6 / 10-11 | Delete a superseded clause and revise torsional reinforcement and shear-flow definitions. | No closed fitments, shear flow or transverse contribution. **Not implemented**. |
| 8.2.7 / 11 | Additional longitudinal tension from shear/torsion revised and bounded. | No additional longitudinal demand. **Not implemented**. |
| 8.2.8.1; 8.2.8.2; Eq (2); Fig 8.2.8 / 11-12 | Revise total longitudinal tension, anchorage/extension alternative and force-envelope figure. | No force-envelope/anchorage check. **Not implemented**. Future conversion must account for this clause's tension-positive axial convention; plugin axial compression is positive. |
| 8.3.1.4; 8.3.2.2; 8.3.3 / 13 | Revise fitment anchorage, shear spacing and torsion perimeter symbol. | No fitment/detailing model. **Not implemented**. |
| Eq 8.4.3 / 13 | Add a longitudinal shear-stress cap. | No interface/longitudinal shear. **Not implemented**. |
| 8.6.1; 8.6.2.2 / 13 | Clarify crack-control domains, steel-stress limits and bar-size treatment. | Gross uncracked E/EI is reported, with no cracked service stress or crack-control design. **Not implemented**. |
| 8.6.2.3; Table 8.6.3 / 14 | Revise crack spacing expression/cap, equivalent diameter for mixed bars and prestressed stress table. | Bar area is available; no nominal diameter, bonded tendons or crack-spacing check. **Not implemented**. |
| 9.5.1; 9.5.2.1; 9.5.3.2 / 14-15 | Revise slab crack-control spacing, stress and shrinkage/temperature rules. | No slab serviceability/design model. **Not implemented**. |
| 10.7.3.1; 10.7.4.3 / 15 | Earthquake detailing references and column-dimension symbols clarified. | No restraint/ductility/member classification. **Not implemented**. |
| Eqs 10.8(1)/(2) / 15 | Revise effective strength where a column passes through a floor system. | No column-floor-joint model. **Not implemented**. |
| 11.1; 11.2.1 / 15 | Clarify wall shear design and earthquake analysis for compression classification. | Section force state alone is insufficient; no wall/member seismic model. **Not implemented**. |
| 11.5.2 / 16 | Revise simplified-wall eligibility with seismic soil conditions. | No geotechnical/seismic eligibility fields. **Not implemented**. |
| 11.6; 11.6.1; 11.6.3 / 16 | Revise wall-height definitions, critical shear location and concrete contribution. | No wall shear model. **Not implemented**. |
| 11.7.4; 11.7.5 / 16-17 | Revise wall reinforcement restraint, high-strength confinement and dowels by ductility/action regime. | No wall restraint, end region, dowel or anchorage checks. **Not implemented**. |
| 12.5; 12.5.1-.5; 12.6 / 17-18 | Extend concentrated-force/bearing-zone provisions and clarify bearing limitations. | No local bearing/confinement/anchorage model. **Not implemented**. |
| 13.1.2.2; 13.1.2.3; Table 13.1.2.3; 13.1.2.7 / 18-19 | Correct development-length symbols/references and headed-bar references. | No development/anchorage data. **Not implemented**. |
| 13.3.2.4; 13.3.3 / 19 | Clarify tendon breaking-strength terminology. | No tendons. **Not implemented**. |
| 14.2.10; 14.5.4; 14.5.5; Eq 14.6.6 / 19 | Revise squat-wall classification, column fitments/confinement and seismic wall shear amplification. | No earthquake design/detailing. **Not implemented**. |
| 14.6.7 / 20 | Revise wall laps/end anchorage and reinforcement ductility restriction. | No wall detailing or product ductility classification. **Not implemented**. |
| 16.1; 16.3.3.4; 16.4.2; 16.4.4.2.1; 16.4.7.2.1 / 20 | Revise fibre test factors, shear contribution and serviceability strength basis. | One concrete block and lumped bars only; no fibre model. **Not implemented**. |
| 17.6.2.5; 17.7.2 / 21 | Construction/backpropping clarification and heading correction. | No construction sequencing. **Not implemented**. |
| Eq 18.3(1); Eq 18.4(2); 18.4 note; 18.8; Fig 18.8 / 21 | Correct fatigue inequality/strength symbols and revise reinforcement fatigue figure. | No stress-cycle/fatigue analysis. **Not implemented**. |
| Eq 20.4.3(2); 21.3.1; 21.3.2 / 22 | Revise plain-concrete punching expression and footing minimum reinforcement/fibre references. | No footing or punching calculation. **Not implemented**. |

## Review disposition

- Preserve the explicit nominal-mechanics scope. No claim of amended-standard
  design compliance is justified by the present code or its mechanics test results.
- Keep the design adapter disabled until the reproduced defects and amendment
  coverage are resolved with independent reference cases.
- Implement future standard checks as separately named calculations, with reviewed
  clause provenance, domain limits, required context and rejection conditions.
- First useful standard-specific verification should cover material selection,
  principal-axis rectangular flexure and contextual phi. Follow with restraint,
  anchorage and minimum reinforcement; a flexural capacity alone is insufficient
  for a complete beam design result.
- Benchmark future checks against licensed worked examples with recorded edition,
  problem/page, assumptions and published rounding. The current independent
  analytical fixtures are original mechanics examples, not textbook design cases.
