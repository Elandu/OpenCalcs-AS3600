# SPDX-License-Identifier: AGPL-3.0-only
"""Reproduce design-adapter integration blockers; this adapter is not enabled.

This is a bounded dependency diagnostic, not a full AS 3600 verification suite.
Reference values were independently calculated after reviewing the licensed
2018 reference incorporating Amendment 1 and Amendment 2:2021.
"""

from __future__ import annotations

import argparse
import json
from importlib.metadata import version
from pathlib import Path
from typing import Any

from concreteproperties.concrete_section import ConcreteSection
from concreteproperties.design_codes.as3600 import AS3600
from concreteproperties.pre import add_bar
from sectionproperties.pre.library.primitive_sections import rectangular_section


def run_upstream_audit() -> dict[str, Any]:
    """Return observed gaps with independently derived reference values."""
    code = AS3600()
    concrete = code.create_concrete_material(80)
    steel = code.create_steel_material()
    geometry = rectangular_section(d=500, b=300, material=concrete)
    for x in (60, 150, 240):
        geometry = add_bar(geometry, area=500, material=steel, x=x, y=50, n=32)
    code.assign_concrete_section(ConcreteSection(geometry))

    # Concrete alpha1 uses characteristic strength; steel is evaluated at eps=.0025.
    concrete_area = 300 * 500 - 3 * 500
    squash_expected = concrete_area * 80 * max(0.72, min(0.85, 1 - 0.003 * 80))
    squash_expected += 3 * 500 * min(500, 200_000 * 0.0025)
    squash_actual = float(code.squash_load)
    service_strength = concrete.stress_strain_profile.get_compressive_strength()

    # This compares an accepted material model with the clause's strain cap.
    # It does not establish that arbitrary 600 MPa steel is standard-approved.
    custom_steel = code.create_steel_material(yield_strength=600)
    custom_code = AS3600()
    custom_geometry = rectangular_section(d=500, b=300, material=concrete)
    for x in (60, 150, 240):
        custom_geometry = add_bar(custom_geometry, area=500, material=custom_steel, x=x, y=50, n=32)
    custom_code.assign_concrete_section(ConcreteSection(custom_geometry))
    steel_expected = min(600, 200_000 * 0.0025)
    # Both fixtures have identical concrete and geometry, so their concrete forces
    # cancel. The 500 MPa baseline has yielded at both candidate strains. Infer the
    # custom steel stress from real upstream squash loads, not a manually chosen strain.
    modeled_steel_area = sum(
        geometry.calculate_area()
        for geometry in custom_code.concrete_section.reinf_geometries_lumped
    )
    steel_actual = 500 + (float(custom_code.squash_load) - squash_actual) / modeled_steel_area

    cases: list[dict[str, Any]] = [
        {
            "id": "upstream-squash-fc80",
            "reference": "AS 3600:2018 clause 10.6.2.2; independent force sum",
            "inputs": {
                "width_mm": 300,
                "depth_mm": 500,
                "steel_area_mm2": 1500,
                "fc_mpa": 80,
                "fy_mpa": 500,
                "es_mpa": 200_000,
            },
            "expected": squash_expected,
            "actual": squash_actual,
            "units": "N",
            "relative_error_percent": 100 * (squash_actual - squash_expected) / squash_expected,
            "status": "blocked" if abs(squash_actual - squash_expected) > 1 else "matched",
            "evidence": {
                "service_strength_getter": service_strength,
                "effective_upstream_alpha1": 1 if service_strength is None else None,
            },
            "finding": (
                "Generated service profile returns no compressive strength from its getter. "
                "The squash calculation then falls back to alpha1=1."
            ),
        },
        {
            "id": "upstream-squash-steel-strain",
            "reference": "AS 3600:2018 clause 10.6.2.2(b); steel strain cap",
            "inputs": {
                "width_mm": 300,
                "depth_mm": 500,
                "steel_area_mm2": 1500,
                "fc_mpa": 80,
                "fy_mpa": 600,
                "es_mpa": 200_000,
                "reference_compression_strain": 0.0025,
            },
            "expected": steel_expected,
            "actual": steel_actual,
            "units": "MPa",
            "relative_error_percent": 100 * (steel_actual - steel_expected) / steel_expected,
            "status": "blocked" if abs(steel_actual - steel_expected) > 1e-6 else "matched",
            "evidence": {
                "baseline_squash_load_n": squash_actual,
                "custom_squash_load_n": float(custom_code.squash_load),
                "modeled_steel_area_mm2": modeled_steel_area,
                "steel_stress_isolation": "500 + (custom squash - baseline squash) / modeled As",
            },
            "finding": (
                "Squash code uses strain 0.025 rather than 0.0025. Default 500 MPa steel "
                "masks this because both strain states have already yielded. The accepted "
                "custom model exposes it; its normative admissibility needs a separate check."
            ),
        },
    ]

    try:
        material120 = code.create_concrete_material(120)
    except ValueError as exc:
        high_strength_actual: float | str = str(exc)
        high_strength_status = "blocked"
    else:
        high_strength_actual = float(material120.stress_strain_profile.get_elastic_modulus())
        high_strength_status = "matched" if high_strength_actual == 44_400 else "blocked"
    cases.append(
        {
            "id": "upstream-fc120",
            "reference": "Amendment 2:2021 clause 3.1.1.1 / Table 3.1.2 (PDF pages 3-4)",
            "inputs": {"fc_mpa": 120},
            "expected": 44_400,
            "actual": high_strength_actual,
            "units": "MPa (elastic modulus)",
            "relative_error_percent": None,
            "status": high_strength_status,
            "finding": "Material factory is limited to 100 MPa; amended 120 MPa grade is missing.",
        }
    )

    # A qualifying short column at/above its balanced load needs .65 here.
    # Other member/action regimes use .60; a constant default cannot select between them.
    phi_actual = code.capacity_reduction_factor(
        n_u=100, n_ub=100, n_uot=-750_000, k_uo=0.2, phi_0=0.6
    )
    cases.append(
        {
            "id": "upstream-compression-context",
            "reference": "Amendment 2:2021 Table 2.2.2(d) (PDF page 2)",
            "inputs": {"short_column": True, "q_over_g": 0.3, "nu_over_nub": 1},
            "expected": 0.65,
            "actual": phi_actual,
            "units": "dimensionless",
            "relative_error_percent": 100 * (phi_actual - 0.65) / 0.65,
            "status": "blocked" if phi_actual != 0.65 else "matched",
            "finding": (
                "Default phi0=.6 is conservative for this qualifying short-column case, "
                "but does not implement the amended contextual selection. A caller must "
                "supply a reviewed phi0; the upstream API does not take Q/G or member class."
            ),
        }
    )
    blocked = sum(case["status"] == "blocked" for case in cases)
    return {
        "report_version": 1,
        "dependency": {"name": "concreteproperties", "version": version("concreteproperties")},
        "adapter": "concreteproperties.design_codes.as3600.AS3600",
        "enabled_by_plugin": False,
        "scope": "Four bounded future-integration diagnostics; not a full standard audit.",
        "aggregate": {
            "status": "blocked" if blocked else "matched",
            "case_count": len(cases),
            "blocked": blocked,
        },
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = run_upstream_audit()
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 1 if report["aggregate"]["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
