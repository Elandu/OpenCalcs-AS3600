# Scope and reference policy

## Current calculation scope

The initial calculation, `structural.as3600.section_analysis`, covers generic reinforced concrete section mechanics: gross section properties and nominal ultimate bending analysis using user-supplied material model coefficients and reinforcement. The implementation uses `concreteproperties` and `sectionproperties`.

This release does not apply AS 3600 normative formulas and makes no AS 3600 compliance claim. A null standard descriptor and `standard_compliance_evaluated: false` communicate that no code check was performed. Results are conditional on the supplied geometry, reinforcement, and material model.

## Planned code checks

The selected target is the latest published normative edition: **AS 3600:2018 with
Amendment 1:2018 and Amendment 2:2021**. As checked on 1 October 2026, the
[Standards Australia catalogue](https://store.standards.org.au/product/as-3600-2018)
marks the base edition Pending Revision and lists both amendments as Current.
[Amendment 2](https://store.standards.org.au/product/as-3600-2018-amd-2-2021)
was published on 21 May 2021. The 2022 supplement and its 2024 amendment relate to
commentary, which must be distinguished from normative amendments.

This is the target for future code checks, not a supported-standard claim for the current
mechanics calculation. Future checks must be narrow, individually named additions backed
by reviewed references for this edition and its amendments. Record the clause or table
identifier, engineering interpretation, applicability limits and independent verification
evidence before implementing each check.

The upstream
[concreteproperties 0.8.0 design-code adapter](https://concrete-properties.readthedocs.io/en/v0.8.0/user_guide/design_codes/as3600.html)
documents AS 3600:2018 support. Its documentation does not establish complete coverage of
the amended standard. This package currently uses the generic section solver and does not
enable that design-code adapter or infer compliance from its availability.

## Reference handling

Reference identifiers and original engineering interpretations may be documented where needed. Do not include copyrighted standard text, scans, or OCR. Preserve source and review provenance for each future code check and make its applicability and limitations visible in calculation metadata and results.
