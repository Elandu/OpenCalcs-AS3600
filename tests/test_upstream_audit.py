# SPDX-License-Identifier: AGPL-3.0-only
"""Diagnostics document known dependency blockers; they do not excuse design failures."""

import json

import pytest
from concreteproperties.design_codes.as3600 import AS3600

from opencalcs_as3600.upstream_audit import main, run_upstream_audit


def test_pinned_dependency_integration_blockers_are_reproduced() -> None:
    report = run_upstream_audit()
    cases = {case["id"]: case for case in report["cases"]}
    assert report["enabled_by_plugin"] is False
    assert report["aggregate"] == {"status": "blocked", "case_count": 4, "blocked": 4}
    squash = cases["upstream-squash-fc80"]
    assert squash["expected"] == 9_778_800
    assert squash["actual"] == pytest.approx(12_630_000, abs=1)
    assert squash["relative_error_percent"] == pytest.approx(29.1569519)
    assert squash["evidence"]["service_strength_getter"] is None
    assert cases["upstream-squash-steel-strain"]["expected"] == 500
    assert cases["upstream-squash-steel-strain"]["actual"] == pytest.approx(600, abs=1e-6)
    assert cases["upstream-fc120"]["expected"] == 44_400
    assert "100 MPa" in cases["upstream-fc120"]["actual"]
    assert cases["upstream-compression-context"]["actual"] == 0.6
    assert cases["upstream-compression-context"]["expected"] == 0.65
    json.dumps(report, allow_nan=False)


def test_steel_diagnostic_observes_the_actual_upstream_squash_path(monkeypatch) -> None:
    original = AS3600.squash_tensile_load

    def corrected_steel_strain(self):
        squash, tensile = original(self)
        for geometry in self.concrete_section.reinf_geometries_lumped:
            profile = geometry.material.stress_strain_profile
            squash -= geometry.calculate_area() * (
                profile.get_stress(strain=0.025) - profile.get_stress(strain=0.0025)
            )
        return squash, tensile

    monkeypatch.setattr(AS3600, "squash_tensile_load", corrected_steel_strain)
    report = run_upstream_audit()
    case = next(case for case in report["cases"] if case["id"] == "upstream-squash-steel-strain")
    assert case["actual"] == pytest.approx(500, abs=1e-6)
    assert case["status"] == "matched"
    assert report["aggregate"]["blocked"] == 3


def test_audit_cli_keeps_blockers_as_a_nonzero_exit(tmp_path) -> None:
    output = tmp_path / "audit.json"
    assert main(["--output", str(output)]) == 1
    assert json.loads(output.read_text(encoding="utf-8"))["aggregate"]["status"] == "blocked"
