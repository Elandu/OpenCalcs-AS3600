# SPDX-License-Identifier: AGPL-3.0-only
"""Independent, analytical benchmarks for the nominal section mechanics adapter.

These cases check a bounded rectangular-section model. They do not evaluate AS 3600
compliance and deliberately do not use concreteproperties/sectionproperties for references.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import platform
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from opencalcs_as3600.plugin import get_plugin

REFERENCE_BAR_VERTICES = 32
REL_TOL = 1e-5
ABS_TOLERANCES = {
    "gross_properties.total_area_mm2": 1e-4,
    "gross_properties.concrete_area_mm2": 1e-4,
    "gross_properties.steel_area_mm2": 1e-4,
    "gross_properties.axial_rigidity_n": 1e-2,
    "gross_properties.elastic_centroid_x_mm": 1e-6,
    "gross_properties.elastic_centroid_y_mm": 1e-6,
    "gross_properties.mass_per_length_kg_m": 1e-6,
    "gross_properties.ei_xx_n_mm2": 1e4,
    "gross_properties.ei_yy_n_mm2": 1e4,
    "gross_properties.ei_xy_n_mm2": 1e4,
    "ultimate.axial_force_kn": 1e-2,
    "ultimate.neutral_axis_depth_mm": 1e-3,
    "ultimate.moment_x_knm": 1e-6,
    "ultimate.moment_y_knm": 1e-6,
    "ultimate.resultant_moment_knm": 1e-6,
    "ultimate.maximum_steel_strain": 1e-8,
}
REL_TOLERANCES = {key: REL_TOL for key in ABS_TOLERANCES}
for _key in (
    "gross_properties.total_area_mm2",
    "gross_properties.concrete_area_mm2",
    "gross_properties.steel_area_mm2",
    "gross_properties.axial_rigidity_n",
    "gross_properties.elastic_centroid_x_mm",
    "gross_properties.elastic_centroid_y_mm",
    "gross_properties.mass_per_length_kg_m",
):
    REL_TOLERANCES[_key] = 1e-8
for _key in (
    "gross_properties.ei_xx_n_mm2",
    "gross_properties.ei_yy_n_mm2",
    "gross_properties.ei_xy_n_mm2",
):
    REL_TOLERANCES[_key] = 1e-6


def _base_inputs() -> dict[str, Any]:
    return {
        "section": {
            "width_mm": 300.0,
            "depth_mm": 500.0,
            "bars": [
                {"id": "B1", "area_mm2": 500.0, "x_mm": 70.0, "y_mm": 50.0},
                {"id": "B2", "area_mm2": 500.0, "x_mm": 150.0, "y_mm": 50.0},
                {"id": "B3", "area_mm2": 500.0, "x_mm": 230.0, "y_mm": 50.0},
            ],
        },
        "concrete": {
            "elastic_modulus_mpa": 30_000.0,
            "compressive_strength_mpa": 32.0,
            "density_kg_m3": 2_400.0,
            "stress_block_alpha": 0.8,
            "stress_block_gamma": 0.8,
            "ultimate_compressive_strain": 0.003,
        },
        "steel": {
            "elastic_modulus_mpa": 200_000.0,
            "yield_strength_mpa": 500.0,
            "density_kg_m3": 7_850.0,
            "fracture_strain": 0.05,
        },
        "axial_force_kn": 0.0,
        "bending_angle_deg": 0.0,
    }


def _case_set() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    def add(case_id: str, title: str, inputs: dict[str, Any], method: str = "yielded") -> None:
        cases.append(
            {
                "id": case_id,
                "title": title,
                "inputs": inputs,
                "method": method,
                "kind": "analytical",
            }
        )

    add("nominal-300x500", "Nominal rectangular baseline", _base_inputs())
    item = _base_inputs()
    item["section"].update(width_mm=250.0, depth_mm=450.0)
    item["section"]["bars"] = [{"id": "B1", "area_mm2": 1_200.0, "x_mm": 125.0, "y_mm": 40.0}]
    item["concrete"].update(
        compressive_strength_mpa=25.0, stress_block_alpha=0.72, stress_block_gamma=0.78
    )
    add("narrow-low-strength", "Narrow section with lower concrete strength", item)
    item = _base_inputs()
    item["section"].update(width_mm=400.0, depth_mm=550.0)
    item["section"]["bars"] = [{"id": "B1", "area_mm2": 2_000.0, "x_mm": 200.0, "y_mm": 55.0}]
    item["concrete"].update(
        compressive_strength_mpa=40.0, stress_block_alpha=0.85, stress_block_gamma=0.82
    )
    add("wide-high-strength", "Wide section with independently supplied block factors", item)
    item = _base_inputs()
    item["steel"].update(yield_strength_mpa=400.0, elastic_modulus_mpa=200_000.0)
    add("steel-fy400", "Lower steel yield strength", item)
    item = _base_inputs()
    item["steel"].update(yield_strength_mpa=600.0, elastic_modulus_mpa=195_000.0)
    add("steel-fy600-e195", "Higher steel strength and altered modulus", item)
    item = _base_inputs()
    item["section"]["depth_mm"] = 600.0
    item["section"]["bars"] = [{"id": "B1", "area_mm2": 1_500.0, "x_mm": 150.0, "y_mm": 60.0}]
    add("deep-600", "Deeper section with a single tensile bar", item)
    item = _base_inputs()
    item["section"]["width_mm"] = 420.0
    item["section"]["bars"] = [
        {"id": "B1", "area_mm2": 500.0, "x_mm": 130.0, "y_mm": 50.0},
        {"id": "B2", "area_mm2": 1_000.0, "x_mm": 235.0, "y_mm": 50.0},
    ]
    add("wide-420", "Wider section with explicit material coefficients", item)
    for axial in (100.0, 300.0):
        item = _base_inputs()
        item["axial_force_kn"] = axial
        add(f"compression-{int(axial)}kn", f"Positive axial compression {axial:g} kN", item)
    for axial in (-100.0, -300.0):
        item = _base_inputs()
        item["axial_force_kn"] = axial
        add(f"tension-{abs(int(axial))}kn", f"Negative axial force {axial:g} kN", item)
    item = _base_inputs()
    item["bending_angle_deg"] = 180.0
    for bar in item["section"]["bars"]:
        bar["y_mm"] = 450.0
    add("mirrored-bottom-bending", "Mirrored reinforcement and reversed bending", item)
    item = _base_inputs()
    item["section"]["width_mm"] *= 2
    item["section"]["depth_mm"] *= 2
    for bar in item["section"]["bars"]:
        bar["x_mm"] *= 2
        bar["y_mm"] *= 2
        bar["area_mm2"] *= 4
    add("geometric-scale-2", "Twofold dimension scale with area scaled by four", item)
    item = _base_inputs()
    item["concrete"].update(stress_block_alpha=0.65, stress_block_gamma=0.70)
    add("alpha-gamma-065-070", "Explicit alpha and gamma coefficients", item)
    # These loads place the tensile steel on the elastic branch; the reference is quadratic.
    item = _base_inputs()
    item["section"]["bars"] = [{"id": "B1", "area_mm2": 200.0, "x_mm": 150.0, "y_mm": 50.0}]
    item["axial_force_kn"] = 1_600.0
    add("elastic-steel-1600kn", "Tensile steel remains below yield", item, "elastic")
    item = _base_inputs()
    item["section"]["bars"] = [{"id": "B1", "area_mm2": 300.0, "x_mm": 150.0, "y_mm": 50.0}]
    item["steel"].update(yield_strength_mpa=600.0, elastic_modulus_mpa=195_000.0)
    item["axial_force_kn"] = 1_500.0
    add(
        "elastic-steel-altered-material",
        "Elastic steel with a separate material model",
        item,
        "elastic",
    )
    item = _base_inputs()
    item["section"]["bars"] = [{"id": "B1", "area_mm2": 900.0, "x_mm": 150.0, "y_mm": 60.0}]
    item["concrete"].update(
        compressive_strength_mpa=35.0, stress_block_alpha=0.75, stress_block_gamma=0.76
    )
    item["axial_force_kn"] = 75.0
    add("moderate-axial-custom-block", "Custom compression block with moderate axial force", item)
    item = _base_inputs()
    item["section"]["bars"] = [{"id": "B1", "area_mm2": 2_400.0, "x_mm": 150.0, "y_mm": 45.0}]
    item["steel"].update(yield_strength_mpa=450.0, elastic_modulus_mpa=210_000.0)
    add("large-steel-area", "Larger tensile reinforcement and altered steel modulus", item)
    item = _base_inputs()
    item["section"].update(width_mm=350.0, depth_mm=650.0)
    item["section"]["bars"] = [{"id": "B1", "area_mm2": 1_800.0, "x_mm": 175.0, "y_mm": 75.0}]
    item["concrete"].update(
        compressive_strength_mpa=50.0, stress_block_alpha=0.9, stress_block_gamma=0.75
    )
    add("high-fc-deep", "Deep higher strength section", item)
    item = _base_inputs()
    item["section"]["bars"] = [
        {"id": "B1", "area_mm2": 600.0, "x_mm": 100.0, "y_mm": 50.0},
        {"id": "B2", "area_mm2": 600.0, "x_mm": 200.0, "y_mm": 50.0},
    ]
    item["axial_force_kn"] = -50.0
    add("two-bar-negative-axial", "Separated bars with tensile axial force", item)
    item = _base_inputs()
    item["section"].update(width_mm=275.0, depth_mm=425.0)
    item["section"]["bars"] = [{"id": "B1", "area_mm2": 1_000.0, "x_mm": 137.5, "y_mm": 35.0}]
    item["concrete"].update(
        compressive_strength_mpa=28.0, stress_block_alpha=0.78, stress_block_gamma=0.84
    )
    item["axial_force_kn"] = 50.0
    add("small-section-compression", "Smaller section under axial compression", item)

    # This case checks rotational invariance as a metamorphic relation, not an independent
    # numerical capacity reference. Both shapes are related by a 90-degree coordinate turn.
    original = _base_inputs()
    original["section"]["bars"] = [
        {"id": "B1", "area_mm2": 500.0, "x_mm": 150.0, "y_mm": 50.0},
        {"id": "B2", "area_mm2": 500.0, "x_mm": 150.0, "y_mm": 100.0},
    ]
    original["bending_angle_deg"] = 90.0
    rotated = copy.deepcopy(original)
    rotated["section"].update(width_mm=500.0, depth_mm=300.0)
    rotated["bending_angle_deg"] = 0.0
    for bar in rotated["section"]["bars"]:
        bar["x_mm"], bar["y_mm"] = bar["y_mm"], 300.0 - bar["x_mm"]
    cases.append(
        {
            "id": "rotation-invariance",
            "title": "Quarter-turn geometry and bending direction invariance",
            "inputs": {"original": original, "rotated": rotated},
            "kind": "metamorphic",
        }
    )

    bad_overlap = _base_inputs()
    bad_overlap["section"]["bars"][1]["x_mm"] = 80.0
    cases.append(
        {
            "id": "reject-overlap",
            "title": "Reject overlapping reinforcement",
            "inputs": bad_overlap,
            "kind": "rejection",
            "expected_error": "overlap",
        }
    )
    bad_edge = _base_inputs()
    bad_edge["section"]["bars"][0]["x_mm"] = 5.0
    cases.append(
        {
            "id": "reject-outside-bar",
            "title": "Reject bar outside section bounds",
            "inputs": bad_edge,
            "kind": "rejection",
            "expected_error": "strictly inside",
        }
    )
    bad_axial = _base_inputs()
    bad_axial["axial_force_kn"] = 10_000.0
    cases.append(
        {
            "id": "reject-impossible-axial",
            "title": "Reject axial force outside equilibrium range",
            "inputs": bad_axial,
            "kind": "rejection",
            "expected_error": "equilibrium",
        }
    )
    return cases


def _polygon_inertia(area: float) -> float:
    """Centroidal inertia of the equal-area regular polygon used by the adapter."""
    angle = 2 * math.pi / REFERENCE_BAR_VERTICES
    return area * area * (2 + math.cos(angle)) / (6 * REFERENCE_BAR_VERTICES * math.sin(angle))


def _polygon_radius(area: float) -> float:
    """Circumradius of an equal-area regular reference polygon."""
    return math.sqrt(
        2 * area / (REFERENCE_BAR_VERTICES * math.sin(2 * math.pi / REFERENCE_BAR_VERTICES))
    )


def _assumptions(inputs: dict[str, Any], method: str) -> list[str]:
    section, concrete, steel = inputs["section"], inputs["concrete"], inputs["steel"]
    width, depth = section["width_mm"], section["depth_mm"]
    angle = inputs.get("bending_angle_deg", 0.0)
    if angle not in (0, 180, -180):
        raise ValueError("Independent benchmarks currently support bending angles 0 and ±180 only.")
    is_bottom = abs(angle) == 180

    def coord(bar: dict[str, Any]) -> float:
        return bar["y_mm"] if is_bottom else depth - bar["y_mm"]

    radii = [_polygon_radius(bar["area_mm2"]) for bar in section["bars"]]
    checks: list[str] = []
    for i, (bar, radius) in enumerate(zip(section["bars"], radii, strict=True)):
        if not (radius < bar["x_mm"] < width - radius and radius < bar["y_mm"] < depth - radius):
            raise ValueError(f"Bar {bar['id']} fails strict section-edge clearance.")
        if steel["fracture_strain"] <= steel["yield_strength_mpa"] / steel["elastic_modulus_mpa"]:
            raise ValueError("Steel fracture strain does not exceed yield strain.")
        checks.append(
            f"bar {bar['id']} fits inside section and fracture strain exceeds yield strain"
        )
        for j in range(i):
            spacing = math.hypot(
                bar["x_mm"] - section["bars"][j]["x_mm"], bar["y_mm"] - section["bars"][j]["y_mm"]
            )
            if spacing <= radius + radii[j]:
                raise ValueError(
                    f"Bars {bar['id']} and {section['bars'][j]['id']} fail spacing clearance."
                )
    if len(section["bars"]) == 1:
        checks.append("inter-bar spacing is not applicable (one bar)")
    else:
        checks.append("all bar pairs have positive clear spacing using the adapter polygon radii")
    if len({round(coord(bar), 10) for bar in section["bars"]}) != 1:
        raise ValueError("Reference requires bars at one common tensile depth.")
    d = coord(section["bars"][0])
    k = (
        concrete["stress_block_alpha"]
        * concrete["compressive_strength_mpa"]
        * width
        * concrete["stress_block_gamma"]
    )
    axial = inputs.get("axial_force_kn", 0.0) * 1000
    As = sum(bar["area_mm2"] for bar in section["bars"])
    eps_cu = concrete["ultimate_compressive_strain"]
    if method == "yielded":
        tension = As * steel["yield_strength_mpa"]
        dn = (tension + axial) / k
        steel_strain = eps_cu * (d / dn - 1)
        if steel_strain < steel["yield_strength_mpa"] / steel["elastic_modulus_mpa"]:
            raise ValueError(
                "Yielded-steel branch assumption fails: calculated tensile strain is below yield."
            )
    elif method == "elastic":
        a = As * steel["elastic_modulus_mpa"] * eps_cu
        # k*dn² + (a-N)*dn - a*d = 0, solved for the positive root.
        dn = (-(a - axial) + math.sqrt((a - axial) ** 2 + 4 * k * a * d)) / (2 * k)
        steel_strain = eps_cu * (d / dn - 1)
        if (
            steel_strain < 0
            or steel_strain * steel["elastic_modulus_mpa"] >= steel["yield_strength_mpa"]
        ):
            raise ValueError(
                "Elastic-steel branch assumption fails: calculated tensile stress "
                "is not below yield."
            )
    else:
        raise ValueError(f"Unknown independent reference method {method!r}.")
    block_depth = concrete["stress_block_gamma"] * dn
    clear_cover = min(
        coord(bar) - radius for bar, radius in zip(section["bars"], radii, strict=True)
    )
    if dn <= 0 or block_depth >= clear_cover:
        raise ValueError("Rectangular compression block is not clear of the tensile bar polygon.")
    if steel_strain >= steel["fracture_strain"]:
        raise ValueError("Independent strain state reaches steel fracture strain.")
    checks.extend(
        [
            f"compression-block depth gamma*dn={block_depth:.9g} mm is less than "
            f"bar-near-edge depth d-r={clear_cover:.9g} mm",
            f"steel strain {steel_strain:.9g} is "
            f"{'yielded' if method == 'yielded' else 'elastic'} and below fracture strain",
        ]
    )
    return checks


def _reference(inputs: dict[str, Any], method: str) -> tuple[dict[str, float], list[str], str]:
    assumptions = _assumptions(inputs, method)
    section, concrete, steel = inputs["section"], inputs["concrete"], inputs["steel"]
    width, depth = section["width_mm"], section["depth_mm"]
    bars = section["bars"]
    As = sum(bar["area_mm2"] for bar in bars)
    ec, es = concrete["elastic_modulus_mpa"], steel["elastic_modulus_mpa"]
    concrete_area = width * depth - As
    ea = ec * concrete_area + es * As
    cx = (
        ec * width * depth * width / 2 + sum((es - ec) * b["area_mm2"] * b["x_mm"] for b in bars)
    ) / ea
    cy = (
        ec * width * depth * depth / 2 + sum((es - ec) * b["area_mm2"] * b["y_mm"] for b in bars)
    ) / ea
    ei_xx = ec * (width * depth**3 / 12 + width * depth * (depth / 2 - cy) ** 2)
    ei_yy = ec * (depth * width**3 / 12 + width * depth * (width / 2 - cx) ** 2)
    for bar in bars:
        dy, dx = bar["y_mm"] - cy, bar["x_mm"] - cx
        transfer = bar["area_mm2"] * dy**2
        concrete_local_i = _polygon_inertia(bar["area_mm2"])
        steel_local_i = bar["area_mm2"] ** 2 / (4 * math.pi)
        ei_xx += (es - ec) * transfer - ec * concrete_local_i + es * steel_local_i
        transfer_x = bar["area_mm2"] * dx**2
        ei_yy += (es - ec) * transfer_x - ec * concrete_local_i + es * steel_local_i
    ei_xy = ec * width * depth * (width / 2 - cx) * (depth / 2 - cy) + sum(
        (es - ec) * bar["area_mm2"] * (bar["x_mm"] - cx) * (bar["y_mm"] - cy) for bar in bars
    )
    mass = (concrete_area * concrete["density_kg_m3"] + As * steel["density_kg_m3"]) / 1e6

    angle = inputs.get("bending_angle_deg", 0.0)
    bottom_compression = abs(angle) == 180
    d = bars[0]["y_mm"] if bottom_compression else depth - bars[0]["y_mm"]
    k = (
        concrete["stress_block_alpha"]
        * concrete["compressive_strength_mpa"]
        * width
        * concrete["stress_block_gamma"]
    )
    axial = inputs.get("axial_force_kn", 0.0) * 1000
    eps_cu = concrete["ultimate_compressive_strain"]
    if method == "yielded":
        tension = As * steel["yield_strength_mpa"]
        neutral_axis = (tension + axial) / k
    else:
        a = As * es * eps_cu
        neutral_axis = (-(a - axial) + math.sqrt((a - axial) ** 2 + 4 * k * a * d)) / (2 * k)
        tension = As * es * eps_cu * (d / neutral_axis - 1)
    compression = k * neutral_axis
    y_comp = (
        concrete["stress_block_gamma"] * neutral_axis / 2
        if bottom_compression
        else depth - concrete["stress_block_gamma"] * neutral_axis / 2
    )
    y_steel = bars[0]["y_mm"]
    moment_x = (compression * (y_comp - cy) + tension * (cy - y_steel)) / 1e6
    moment_y = (
        compression * (width / 2 - cx)
        - sum(tension * bar["area_mm2"] / As * (bar["x_mm"] - cx) for bar in bars)
    ) / 1e6
    gross = {
        "total_area_mm2": width * depth,
        "concrete_area_mm2": concrete_area,
        "steel_area_mm2": As,
        "axial_rigidity_n": ea,
        "elastic_centroid_x_mm": cx,
        "elastic_centroid_y_mm": cy,
        "mass_per_length_kg_m": mass,
        "ei_xx_n_mm2": ei_xx,
        "ei_yy_n_mm2": ei_yy,
        "ei_xy_n_mm2": ei_xy,
    }
    expected = {
        **{f"gross_properties.{key}": value for key, value in gross.items()},
        "ultimate.axial_force_kn": axial / 1000,
        "ultimate.neutral_axis_depth_mm": neutral_axis,
        "ultimate.moment_x_knm": moment_x,
        "ultimate.moment_y_knm": moment_y,
        "ultimate.resultant_moment_knm": math.hypot(moment_x, moment_y),
        "ultimate.maximum_steel_strain": abs(eps_cu * (1 - d / neutral_axis)),
    }
    formula = (
        "Independent equilibrium: C=alpha*fc*b*gamma*dn; yielded T=As*fy, or elastic "
        "T=As*Es*eps_cu*(d/dn-1) using the positive root of "
        "k*dn^2+(As*Es*eps_cu-N)*dn-As*Es*eps_cu*d=0. Moment is the force couple "
        "about the independently calculated elastic centroid. Gross properties use "
        "transformed-area centroid and inertia. Concrete bar holes use the exact regular-polygon "
        "inertia at 32 vertices; steel bars use the solver's equal-area circular lump inertia."
    )
    return expected, assumptions, formula


def _get_path(data: dict[str, Any], path: str) -> float:
    value: Any = data
    for part in path.split("."):
        value = value[part]
    return float(value)


def _installed_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def _numeric_check(
    metric: str,
    expected: float,
    actual: float,
    units: str,
    expected_values: dict[str, float],
) -> dict[str, Any]:
    absolute_tolerance = ABS_TOLERANCES[metric]
    if metric == "gross_properties.ei_xy_n_mm2":
        absolute_tolerance = 1e-12 * max(
            expected_values["gross_properties.ei_xx_n_mm2"],
            expected_values["gross_properties.ei_yy_n_mm2"],
        )
    relative_tolerance = REL_TOLERANCES[metric]
    error = abs(actual - expected)
    tolerance = max(absolute_tolerance, relative_tolerance * abs(expected))
    return {
        "metric": metric,
        "units": units,
        "expected": expected,
        "actual": actual,
        "absolute_error": error,
        "relative_error": error / abs(expected) if expected else (0.0 if error == 0 else None),
        "absolute_tolerance": absolute_tolerance,
        "relative_tolerance": relative_tolerance,
        "passed": error <= tolerance,
    }


def run_verification() -> dict[str, Any]:
    """Run the self-contained benchmark set and return a strict-JSON-safe report."""
    calculation = get_plugin().calculations[0]
    reports: list[dict[str, Any]] = []
    units = {
        "gross_properties.total_area_mm2": "mm^2",
        "gross_properties.concrete_area_mm2": "mm^2",
        "gross_properties.steel_area_mm2": "mm^2",
        "gross_properties.axial_rigidity_n": "N",
        "gross_properties.elastic_centroid_x_mm": "mm",
        "gross_properties.elastic_centroid_y_mm": "mm",
        "gross_properties.mass_per_length_kg_m": "kg/m",
        "gross_properties.ei_xx_n_mm2": "N*mm^2",
        "gross_properties.ei_yy_n_mm2": "N*mm^2",
        "gross_properties.ei_xy_n_mm2": "N*mm^2",
        "ultimate.axial_force_kn": "kN",
        "ultimate.neutral_axis_depth_mm": "mm",
        "ultimate.moment_x_knm": "kN*m",
        "ultimate.moment_y_knm": "kN*m",
        "ultimate.resultant_moment_knm": "kN*m",
        "ultimate.maximum_steel_strain": "dimensionless",
    }
    for spec in _case_set():
        inputs = copy.deepcopy(spec["inputs"])
        item: dict[str, Any] = {
            "id": spec["id"],
            "title": spec["title"],
            "inputs": inputs,
            "verification_type": spec["kind"],
            "scope": "nominal_section_mechanics; no AS 3600 compliance evaluated",
            "warnings": [
                "Analytical idealization is limited to rectangular sections with a common "
                "tensile bar depth."
            ],
        }
        try:
            if spec["kind"] == "rejection":
                try:
                    calculation.run(inputs)
                except (ValueError, TypeError) as exc:
                    passed = spec["expected_error"].casefold() in str(exc).casefold()
                    item["reference"] = (
                        "Input contract requires this invalid geometry/load to be rejected."
                    )
                    item["expected"] = {"rejection_message_contains": spec["expected_error"]}
                    item["actual"] = {"exception_type": type(exc).__name__, "message": str(exc)}
                    item["checks"] = [
                        {
                            "metric": "input_rejected",
                            "units": "boolean",
                            "expected": True,
                            "actual": passed,
                            "absolute_error": None,
                            "relative_error": None,
                            "absolute_tolerance": 0,
                            "relative_tolerance": 0,
                            "passed": passed,
                        }
                    ]
                    item["status"] = "passed" if passed else "failed"
                else:
                    item.update(
                        reference=(
                            "Input contract requires this invalid geometry/load to be rejected."
                        ),
                        expected={"rejection_message_contains": spec["expected_error"]},
                        actual={"exception_type": None, "message": None},
                        checks=[
                            {
                                "metric": "input_rejected",
                                "units": "boolean",
                                "expected": True,
                                "actual": False,
                                "absolute_error": None,
                                "relative_error": None,
                                "absolute_tolerance": 0,
                                "relative_tolerance": 0,
                                "passed": False,
                            }
                        ],
                        status="failed",
                    )
                if item["status"] == "failed":
                    item["warnings"].append("Expected input rejection did not occur as specified.")
                reports.append(item)
                continue
            if spec["kind"] == "metamorphic":
                first = calculation.run(inputs["original"])
                second = calculation.run(inputs["rotated"])
                fields = ("neutral_axis_depth_mm", "resultant_moment_knm")
                checks = []
                for field in fields:
                    first_value = float(first["ultimate"][field])
                    second_value = float(second["ultimate"][field])
                    error = abs(first_value - second_value)
                    base_metric = (
                        "ultimate.neutral_axis_depth_mm"
                        if field == "neutral_axis_depth_mm"
                        else "ultimate.resultant_moment_knm"
                    )
                    abs_tolerance = ABS_TOLERANCES[base_metric]
                    rel_tolerance = REL_TOLERANCES[base_metric]
                    checks.append(
                        {
                            "metric": f"rotation_delta.{field}",
                            "units": "mm" if field == "neutral_axis_depth_mm" else "kN*m",
                            "expected": 0.0,
                            "actual": error,
                            "absolute_error": error,
                            "relative_error": None
                            if first_value == 0
                            else error / abs(first_value),
                            "absolute_tolerance": abs_tolerance,
                            "relative_tolerance": rel_tolerance,
                            "passed": error <= max(abs_tolerance, rel_tolerance * abs(first_value)),
                        }
                    )
                item.update(
                    reference=(
                        "Metamorphic check: rotating the section, bars, and bending direction "
                        "together preserves neutral-axis depth and resultant capacity."
                    ),
                    assumption_checks=[
                        "Both configurations are the same geometry under a rigid "
                        "90-degree coordinate rotation."
                    ],
                    expected={check["metric"]: check["expected"] for check in checks},
                    actual={"original": first["ultimate"], "rotated": second["ultimate"]},
                    checks=checks,
                    status="passed" if all(check["passed"] for check in checks) else "failed",
                )
                item["warnings"] = [
                    "This is a metamorphic solver-invariance check, not an independent "
                    "capacity oracle."
                ]
                reports.append(item)
                continue
            expected, assumptions, explanation = _reference(inputs, spec["method"])
            item["reference"] = explanation
            item["reference_method"] = spec["method"]
            item["assumption_checks"] = assumptions
            actual_result = calculation.run(inputs)
            item["actual"] = {
                "gross_properties": actual_result["gross_properties"],
                "ultimate": actual_result["ultimate"],
            }
            item["expected"] = expected
            checks = []
            for metric, target in expected.items():
                observed = _get_path(actual_result, metric)
                checks.append(_numeric_check(metric, target, observed, units[metric], expected))
            item["checks"] = checks
            item["status"] = "passed" if all(check["passed"] for check in checks) else "failed"
            if item["status"] == "failed":
                item["warnings"].append(
                    "One or more actual values exceeded the declared tolerance."
                )
        except Exception as exc:  # benchmark failures are report data, never silently skipped
            item.update(
                status="failed", checks=[], error={"type": type(exc).__name__, "message": str(exc)}
            )
            item["warnings"].append(
                "Reference precondition or solver execution failed; this case counts as a failure."
            )
        reports.append(item)
    failed = sum(report["status"] != "passed" for report in reports)
    result = {
        "report_version": 1,
        "scope": (
            "Independent numerical verification of nominal section mechanics; "
            "not an AS 3600 compliance assessment."
        ),
        "versions": {
            "python": platform.python_version(),
            "opencalcs_as3600": _installed_version("opencalcs-as3600"),
            "concreteproperties": _installed_version("concreteproperties"),
            "sectionproperties": _installed_version("sectionproperties"),
        },
        "tolerances": {
            "absolute_by_metric": ABS_TOLERANCES,
            "relative_by_metric": REL_TOLERANCES,
            "ei_xy_absolute": "1e-12 times the larger reference EI principal-axis magnitude",
            "numerical_basis": [
                "Area absolute tolerance is 1e-4 mm^2 to cover the approximately 5e-5 mm^2 "
                "polygon-mesh residue observed in the pinned solver.",
                "Axial-force absolute tolerance is 0.01 kN to cover the pinned solver root "
                "residual while remaining below its independent adapter equilibrium bound.",
            ],
        },
        "aggregate": {
            "status": "passed" if failed == 0 else "failed",
            "case_count": len(reports),
            "passed": len(reports) - failed,
            "failed": failed,
        },
        "cases": reports,
    }
    # Reject accidental NaN/Infinity before the report escapes the API.
    json.dumps(result, allow_nan=False)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, help="Write the JSON report to this path; default prints to stdout."
    )
    args = parser.parse_args(argv)
    report = run_verification()
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)
    return 0 if report["aggregate"]["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
