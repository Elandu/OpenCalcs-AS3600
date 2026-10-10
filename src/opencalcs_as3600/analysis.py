# SPDX-License-Identifier: LicenseRef-EngCalcs-Proprietary
"""Bounded adapter to upstream section mechanics, using mm, MPa and N internally."""

from __future__ import annotations

import math
from collections.abc import Mapping
from importlib.metadata import version
from typing import Any

from concreteproperties.concrete_section import ConcreteSection
from concreteproperties.material import Concrete, SteelBar
from concreteproperties.pre import add_bar
from concreteproperties.stress_strain_profile import (
    ConcreteLinear,
    RectangularStressBlock,
    SteelElasticPlastic,
)
from concreteproperties.utils import AnalysisError
from jsonschema import Draft202012Validator, ValidationError
from sectionproperties.pre.library.primitive_sections import rectangular_section

from opencalcs_as3600.schemas import INPUT_SCHEMA, OUTPUT_SCHEMA

BAR_VERTICES = 32


def ensure_finite(value: Any, path: str = "inputs") -> None:
    """Reject NaN, infinity and numbers that cannot be represented by the solver."""
    if isinstance(value, int | float) and not isinstance(value, bool):
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError(f"{path} must contain finite numbers representable as floats.")
    elif isinstance(value, Mapping):
        for key, child in value.items():
            ensure_finite(child, f"{path}.{key}")
    elif isinstance(value, list | tuple):
        for index, child in enumerate(value):
            ensure_finite(child, f"{path}[{index}]")


def validate_inputs(inputs: Mapping[str, Any]) -> None:
    if not isinstance(inputs, Mapping):
        raise ValueError("Calculation inputs must be an object.")
    ensure_finite(inputs)
    try:
        Draft202012Validator(INPUT_SCHEMA).validate(dict(inputs))
    except ValidationError as exc:
        path = ".".join(str(part) for part in exc.absolute_path) or "<root>"
        raise ValueError(f"Invalid calculation input at {path}: {exc.message}") from exc

    section = inputs["section"]
    bars = section["bars"]
    ids = [bar["id"] for bar in bars]
    if len(ids) != len(set(ids)):
        raise ValueError("Reinforcement bar IDs must be unique.")

    radii = []
    for bar in bars:
        # Equal-area polygons have a slightly larger circumradius than a circular bar.
        radius = math.sqrt(
            2 * bar["area_mm2"] / (BAR_VERTICES * math.sin(2 * math.pi / BAR_VERTICES))
        )
        radii.append(radius)
        if not (
            radius < bar["x_mm"] < section["width_mm"] - radius
            and radius < bar["y_mm"] < section["depth_mm"] - radius
        ):
            raise ValueError(f"Bar {bar['id']} must fit strictly inside the concrete rectangle.")

    for i, first in enumerate(bars):
        for j in range(i + 1, len(bars)):
            second = bars[j]
            spacing = math.hypot(first["x_mm"] - second["x_mm"], first["y_mm"] - second["y_mm"])
            if spacing <= radii[i] + radii[j]:
                raise ValueError(f"Bars {first['id']} and {second['id']} overlap or touch.")

    steel = inputs["steel"]
    if steel["fracture_strain"] <= steel["yield_strength_mpa"] / steel["elastic_modulus_mpa"]:
        raise ValueError("Steel fracture strain must exceed its yield strain.")


def _build_section(inputs: Mapping[str, Any]) -> ConcreteSection:
    concrete = inputs["concrete"]
    steel = inputs["steel"]
    # Density kg/mm^3 gives gross.mass in kg/mm; reporting converts to kg/m.
    concrete_material = Concrete(
        name="User concrete model",
        density=concrete["density_kg_m3"] / 1e9,
        stress_strain_profile=ConcreteLinear(elastic_modulus=concrete["elastic_modulus_mpa"]),
        ultimate_stress_strain_profile=RectangularStressBlock(
            compressive_strength=concrete["compressive_strength_mpa"],
            alpha=concrete["stress_block_alpha"],
            gamma=concrete["stress_block_gamma"],
            ultimate_strain=concrete["ultimate_compressive_strain"],
        ),
        flexural_tensile_strength=0,
        colour="lightgrey",
    )
    steel_material = SteelBar(
        name="User steel model",
        density=steel["density_kg_m3"] / 1e9,
        stress_strain_profile=SteelElasticPlastic(
            yield_strength=steel["yield_strength_mpa"],
            elastic_modulus=steel["elastic_modulus_mpa"],
            fracture_strain=steel["fracture_strain"],
        ),
        colour="grey",
    )
    section = inputs["section"]
    geometry = rectangular_section(
        d=section["depth_mm"], b=section["width_mm"], material=concrete_material
    )
    for bar in section["bars"]:
        geometry = add_bar(
            geometry=geometry,
            area=bar["area_mm2"],
            material=steel_material,
            x=bar["x_mm"],
            y=bar["y_mm"],
            n=BAR_VERTICES,
        )
    # Upstream defaults to the unweighted centroid. Select the elastic centroid explicitly.
    return ConcreteSection(geometry=geometry, geometric_centroid_override=True)


def run_analysis(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Return uncracked properties and a nominal strain-compatible capacity."""
    validate_inputs(inputs)
    section = _build_section(inputs)
    angle_deg = inputs.get("bending_angle_deg", 0)
    theta = math.radians(angle_deg)
    requested_n = inputs.get("axial_force_kn", 0) * 1_000
    try:
        ultimate = section.ultimate_bending_capacity(theta=theta, n=requested_n)
    except AnalysisError as exc:
        raise ValueError(f"Section analysis failed to satisfy axial equilibrium: {exc}") from exc

    gross = section.gross_properties
    # Upstream's neutral-axis root tolerance is 0.001 mm. Check force balance separately.
    force_scale = (
        gross.concrete_area
        * inputs["concrete"]["compressive_strength_mpa"]
        * inputs["concrete"]["stress_block_alpha"]
        + gross.reinf_lumped_area * inputs["steel"]["yield_strength_mpa"]
    )
    if abs(ultimate.n - requested_n) > max(1, force_scale * 1e-5):
        raise ValueError("Section analysis failed the axial equilibrium tolerance.")

    shape = inputs["section"]
    sin_theta, cos_theta = math.sin(theta), math.cos(theta)
    extreme_v = max(
        -x * sin_theta + y * cos_theta
        for x, y in [
            (0, 0),
            (shape["width_mm"], 0),
            (0, shape["depth_mm"]),
            (shape["width_mm"], shape["depth_mm"]),
        ]
    )
    max_steel_strain = max(
        abs(
            inputs["concrete"]["ultimate_compressive_strain"]
            * (1 - (extreme_v + bar["x_mm"] * sin_theta - bar["y_mm"] * cos_theta) / ultimate.d_n)
        )
        for bar in shape["bars"]
    )
    if max_steel_strain >= inputs["steel"]["fracture_strain"]:
        raise ValueError("Section capacity reaches or exceeds the supplied steel fracture strain.")

    result = {
        "analysis_scope": "nominal_section_mechanics",
        "standard_compliance_evaluated": False,
        "solver": {"name": "concreteproperties", "version": version("concreteproperties")},
        "dependencies": {"sectionproperties": version("sectionproperties")},
        "gross_properties": {
            "total_area_mm2": float(gross.total_area),
            "concrete_area_mm2": float(gross.concrete_area),
            "steel_area_mm2": float(gross.reinf_lumped_area),
            "axial_rigidity_n": float(gross.e_a),
            "elastic_centroid_x_mm": float(gross.cx),
            "elastic_centroid_y_mm": float(gross.cy),
            "mass_per_length_kg_m": float(gross.mass * 1_000),
            "ei_xx_n_mm2": float(gross.e_ixx_c),
            "ei_yy_n_mm2": float(gross.e_iyy_c),
            "ei_xy_n_mm2": float(gross.e_ixy_c),
        },
        "ultimate": {
            "bending_angle_deg": float(angle_deg),
            "axial_force_kn": float(ultimate.n / 1_000),
            "axial_equilibrium_error_kn": float((ultimate.n - requested_n) / 1_000),
            "neutral_axis_depth_mm": float(ultimate.d_n),
            "moment_x_knm": float(ultimate.m_x / 1e6),
            "moment_y_knm": float(ultimate.m_y / 1e6),
            "resultant_moment_knm": float(ultimate.m_xy / 1e6),
            "maximum_steel_strain": float(max_steel_strain),
        },
        "warnings": ["Nominal section capacity; no AS 3600 design capacity or compliance check."],
        "limitations": [
            "Material coefficients are supplied by the caller; no AS 3600 defaults are derived.",
            "Rectangular, non-prestressed section with one concrete model and one steel model.",
            "Gross properties use uncracked linear elasticity, including concrete in tension.",
            "Ultimate analysis uses a rectangular compression block and lumped steel bars.",
            "Bars displace concrete with equal-area 32-vertex polygons and conservative bounds.",
            "Moments are about the elastic centroid; the neutral-axis angle is not a load angle.",
            "Shear, torsion, buckling, detailing, durability and serviceability are not checked.",
            "This is a section calculation; member design checks are not included.",
            "A converged nominal strain state is conditional on the supplied material models.",
        ],
    }
    ensure_finite(result, "results")
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    return result
