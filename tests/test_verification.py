# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

import json

from engcalcs_as3600 import analysis, verification


def test_independent_report_contains_hand_auditable_nominal_case() -> None:
    report = verification.run_verification()

    assert report["aggregate"]["case_count"] >= 15
    assert report["aggregate"]["status"] == "passed"
    baseline = next(case for case in report["cases"] if case["id"] == "nominal-300x500")
    values = {check["metric"]: check["expected"] for check in baseline["checks"]}
    assert values["ultimate.neutral_axis_depth_mm"] == 122.0703125
    assert values["ultimate.moment_x_knm"] == 300.87890625
    assert "C=alpha*fc*b*gamma*dn" in baseline["reference"]
    assert baseline["inputs"]["section"]["width_mm"] == 300.0
    assert any("d-r=" in check for check in baseline["assumption_checks"])
    assert all(case["status"] == "passed" for case in report["cases"])
    asymmetric = next(case for case in report["cases"] if case["id"] == "wide-420")
    asymmetric_expected = asymmetric["expected"]
    assert asymmetric_expected["gross_properties.ei_xy_n_mm2"] != 0
    assert asymmetric_expected["ultimate.moment_y_knm"] != 0
    json.dumps(report, allow_nan=False)


def test_elastic_branch_has_checked_below_yield_assumption() -> None:
    report = verification.run_verification()
    case = next(case for case in report["cases"] if case["id"] == "elastic-steel-1600kn")

    assert case["status"] == "passed"
    assert any(
        "steel strain" in check and "elastic" in check for check in case["assumption_checks"]
    )
    assert "positive root" in case["reference"]


def test_unexpected_solver_error_counts_as_failed_case(monkeypatch) -> None:
    class BrokenCalculation:
        def run(self, inputs):
            raise RuntimeError("injected solver failure")

    class BrokenPlugin:
        calculations = (BrokenCalculation(),)

    monkeypatch.setattr(verification, "get_plugin", lambda: BrokenPlugin())
    report = verification.run_verification()

    assert report["aggregate"]["status"] == "failed"
    assert report["aggregate"]["failed"] == report["aggregate"]["case_count"]
    assert report["cases"][0]["error"] == {
        "type": "RuntimeError",
        "message": "injected solver failure",
    }


def test_cli_writes_requested_json_and_returns_failure_status(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        verification,
        "run_verification",
        lambda: {"aggregate": {"status": "failed"}, "cases": []},
    )
    destination = tmp_path / "reports" / "check.json"

    status = verification.main(["--output", str(destination)])

    assert status == 1
    assert json.loads(destination.read_text(encoding="utf-8")) == {
        "aggregate": {"status": "failed"},
        "cases": [],
    }


def test_reference_bar_polygon_count_is_explicit_and_independent() -> None:
    assert verification.REFERENCE_BAR_VERTICES == 32
    assert analysis.BAR_VERTICES == verification.REFERENCE_BAR_VERTICES


def test_tight_steel_strain_tolerance_rejects_injected_numerical_mismatch() -> None:
    assert verification.ABS_TOLERANCES["ultimate.neutral_axis_depth_mm"] == 1e-3
    assert verification.ABS_TOLERANCES["ultimate.axial_force_kn"] == 1e-2
    assert verification.ABS_TOLERANCES["ultimate.moment_x_knm"] == 1e-6
    check = verification._numeric_check(
        metric="ultimate.maximum_steel_strain",
        expected=0.008,
        actual=0.0081,
        units="dimensionless",
        expected_values={},
    )

    assert check["absolute_tolerance"] == 1e-8
    assert check["relative_tolerance"] == 1e-5
    assert check["passed"] is False
