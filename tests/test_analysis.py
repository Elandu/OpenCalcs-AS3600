# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

import copy
import json
import math

import pytest
from jsonschema import Draft202012Validator

from engcalcs_as3600.plugin import get_plugin
from engcalcs_as3600.schemas import INPUT_SCHEMA, OUTPUT_SCHEMA


def run(inputs: dict) -> dict:
    return get_plugin().calculations[0].run(inputs)


def test_schemas_are_valid() -> None:
    Draft202012Validator.check_schema(INPUT_SCHEMA)
    Draft202012Validator.check_schema(OUTPUT_SCHEMA)


def test_nominal_capacity_matches_independent_equilibrium(section_inputs: dict) -> None:
    result = run(section_inputs)
    ultimate = result["ultimate"]
    # T=As*fy; C=alpha*fc*b*gamma*dn; M=T*(d-gamma*dn/2).
    tension_n = 1_500 * 500
    neutral_axis_mm = tension_n / (0.8 * 32 * 300 * 0.8)
    moment_knm = tension_n * (450 - 0.8 * neutral_axis_mm / 2) / 1e6
    assert neutral_axis_mm == pytest.approx(122.0703125)
    assert moment_knm == pytest.approx(300.87890625)
    assert ultimate["neutral_axis_depth_mm"] == pytest.approx(neutral_axis_mm, rel=1e-5)
    assert ultimate["moment_x_knm"] == pytest.approx(moment_knm, rel=1e-5)
    assert ultimate["moment_y_knm"] == pytest.approx(0, abs=1e-6)
    assert ultimate["axial_force_kn"] == pytest.approx(0, abs=0.01)
    strain = abs(0.003 * (1 - 450 / neutral_axis_mm))
    assert ultimate["maximum_steel_strain"] == pytest.approx(strain, rel=1e-5)
    assert result["standard_compliance_evaluated"] is False
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    json.dumps(result, allow_nan=False)


def test_gross_properties_match_composite_area_and_mass(section_inputs: dict) -> None:
    gross = run(section_inputs)["gross_properties"]
    ea = 148_500 * 30_000 + 1_500 * 200_000
    cy = (150_000 * 30_000 * 250 + 1_500 * (200_000 - 30_000) * 50) / ea
    assert gross["total_area_mm2"] == pytest.approx(150_000)
    assert gross["concrete_area_mm2"] == pytest.approx(148_500)
    assert gross["steel_area_mm2"] == pytest.approx(1_500)
    assert gross["axial_rigidity_n"] == pytest.approx(4.755e9)
    assert gross["elastic_centroid_x_mm"] == pytest.approx(150)
    assert gross["elastic_centroid_y_mm"] == pytest.approx(cy)
    assert gross["mass_per_length_kg_m"] == pytest.approx(368.175)
    assert gross["ei_xx_n_mm2"] > 0
    assert gross["ei_yy_n_mm2"] > 0
    assert gross["ei_xy_n_mm2"] == pytest.approx(0, abs=1)


@pytest.mark.parametrize("axial_kn", [-100, 300])
def test_axial_force_sign_units_and_moment_reference(section_inputs: dict, axial_kn: float) -> None:
    section_inputs["axial_force_kn"] = axial_kn
    result = run(section_inputs)
    compression_n = 750_000 + axial_kn * 1_000
    neutral_axis_mm = compression_n / (0.8 * 32 * 300 * 0.8)
    yc = result["gross_properties"]["elastic_centroid_y_mm"]
    moment = compression_n * (500 - 0.8 * neutral_axis_mm / 2 - yc) + 750_000 * (yc - 50)
    assert result["ultimate"]["axial_force_kn"] == pytest.approx(axial_kn, abs=0.01)
    assert result["ultimate"]["neutral_axis_depth_mm"] == pytest.approx(neutral_axis_mm, rel=1e-5)
    assert result["ultimate"]["moment_x_knm"] == pytest.approx(moment / 1e6, rel=1e-5)


@pytest.mark.parametrize("angle", [-180, 180])
def test_mirrored_bars_and_reversed_bending(section_inputs: dict, angle: float) -> None:
    original = run(section_inputs)["ultimate"]
    section_inputs["bending_angle_deg"] = angle
    for bar in section_inputs["section"]["bars"]:
        bar["y_mm"] = 500 - bar["y_mm"]
    reversed_result = run(section_inputs)["ultimate"]
    assert reversed_result["moment_x_knm"] == pytest.approx(-original["moment_x_knm"], rel=1e-5)
    assert reversed_result["resultant_moment_knm"] == pytest.approx(
        original["resultant_moment_knm"], rel=1e-5
    )


def test_neutral_axis_angle_rotation(section_inputs: dict) -> None:
    section_inputs["bending_angle_deg"] = 90
    reference = run(section_inputs)["ultimate"]
    rotated = copy.deepcopy(section_inputs)
    rotated["bending_angle_deg"] = 0
    rotated["section"]["width_mm"] = 500
    rotated["section"]["depth_mm"] = 300
    for bar in rotated["section"]["bars"]:
        bar["x_mm"], bar["y_mm"] = bar["y_mm"], 300 - bar["x_mm"]
    result = run(rotated)["ultimate"]
    assert reference["resultant_moment_knm"] == pytest.approx(
        result["resultant_moment_knm"], rel=1e-5
    )
    assert reference["neutral_axis_depth_mm"] == pytest.approx(
        result["neutral_axis_depth_mm"], rel=1e-5
    )


def test_dimension_scaling(section_inputs: dict) -> None:
    original = run(section_inputs)
    section_inputs["section"]["width_mm"] *= 2
    section_inputs["section"]["depth_mm"] *= 2
    for bar in section_inputs["section"]["bars"]:
        bar["x_mm"] *= 2
        bar["y_mm"] *= 2
        bar["area_mm2"] *= 4
    scaled = run(section_inputs)
    assert scaled["ultimate"]["moment_x_knm"] == pytest.approx(
        original["ultimate"]["moment_x_knm"] * 8, rel=1e-5
    )
    assert scaled["gross_properties"]["axial_rigidity_n"] == pytest.approx(
        original["gross_properties"]["axial_rigidity_n"] * 4
    )
    assert scaled["gross_properties"]["ei_xx_n_mm2"] == pytest.approx(
        original["gross_properties"]["ei_xx_n_mm2"] * 16
    )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, 10**400])
def test_nonfinite_numbers_rejected(section_inputs: dict, value: float) -> None:
    section_inputs["concrete"]["stress_block_alpha"] = value
    with pytest.raises(ValueError, match="finite numbers"):
        run(section_inputs)


@pytest.mark.parametrize("value", [0, -1, True, "300", 10_001])
def test_invalid_dimensions_rejected(section_inputs: dict, value: object) -> None:
    section_inputs["section"]["width_mm"] = value
    with pytest.raises(ValueError, match="Invalid calculation input"):
        run(section_inputs)


def test_duplicate_ids_rejected(section_inputs: dict) -> None:
    section_inputs["section"]["bars"][1]["id"] = "B1"
    with pytest.raises(ValueError, match="IDs must be unique"):
        run(section_inputs)


def test_overlapping_bars_rejected(section_inputs: dict) -> None:
    section_inputs["section"]["bars"][1]["x_mm"] = 65
    with pytest.raises(ValueError, match="overlap"):
        run(section_inputs)


def test_partly_outside_bar_rejected(section_inputs: dict) -> None:
    section_inputs["section"]["bars"][0]["x_mm"] = 10
    with pytest.raises(ValueError, match="strictly inside"):
        run(section_inputs)


def test_model_size_limit(section_inputs: dict) -> None:
    section_inputs["section"]["bars"] *= 34
    with pytest.raises(ValueError, match="Invalid calculation input"):
        run(section_inputs)


def test_unknown_input_rejected(section_inputs: dict) -> None:
    section_inputs["capacity_reduction_factor"] = 0.85
    with pytest.raises(ValueError, match="Additional properties"):
        run(section_inputs)


def test_required_material_coefficients(section_inputs: dict) -> None:
    del section_inputs["concrete"]["stress_block_alpha"]
    with pytest.raises(ValueError, match="required property"):
        run(section_inputs)


def test_steel_fracture_before_yield_rejected(section_inputs: dict) -> None:
    section_inputs["steel"]["fracture_strain"] = 0.001
    with pytest.raises(ValueError, match="exceed its yield strain"):
        run(section_inputs)


def test_ultimate_fracture_exceeded_rejected(section_inputs: dict) -> None:
    section_inputs["steel"]["fracture_strain"] = 0.005
    with pytest.raises(ValueError, match="exceeds the supplied steel fracture"):
        run(section_inputs)


@pytest.mark.parametrize("axial_kn", [-10_000, 10_000])
def test_impossible_axial_force_returns_failure(section_inputs: dict, axial_kn: float) -> None:
    section_inputs["axial_force_kn"] = axial_kn
    with pytest.raises(ValueError, match="equilibrium"):
        run(section_inputs)


def test_optional_analysis_values_default_to_zero(section_inputs: dict) -> None:
    del section_inputs["bending_angle_deg"]
    del section_inputs["axial_force_kn"]
    assert run(section_inputs)["ultimate"]["moment_x_knm"] == pytest.approx(300.87890625, rel=1e-5)


def test_nonobject_input_rejected() -> None:
    with pytest.raises(ValueError, match="must be an object"):
        run([])


def test_unexpected_failure_is_not_reported_as_invalid_input(
    section_inputs: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected_failure(inputs: dict) -> dict:
        raise RuntimeError("Unexpected solver failure")

    monkeypatch.setattr("engcalcs_as3600.analysis.run_analysis", unexpected_failure)
    with pytest.raises(RuntimeError, match="Unexpected solver failure"):
        run(section_inputs)
