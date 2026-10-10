# SPDX-License-Identifier: LicenseRef-EngCalcs-Proprietary
"""JSON contracts for the section mechanics calculation."""

from typing import Any


def _object(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties) if required is None else required,
        "properties": properties,
    }


def _positive(maximum: float) -> dict[str, Any]:
    return {"type": "number", "exclusiveMinimum": 0, "maximum": maximum}


INPUT_SCHEMA = _object(
    {
        "section": _object(
            {
                "width_mm": _positive(10_000),
                "depth_mm": _positive(10_000),
                "bars": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": _object(
                        {
                            "id": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 40,
                                "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,39}$",
                            },
                            "area_mm2": _positive(100_000),
                            "x_mm": {"type": "number", "minimum": 0, "maximum": 10_000},
                            "y_mm": {"type": "number", "minimum": 0, "maximum": 10_000},
                        }
                    ),
                },
            }
        ),
        "concrete": _object(
            {
                "elastic_modulus_mpa": _positive(1_000_000),
                "compressive_strength_mpa": _positive(500),
                "density_kg_m3": _positive(30_000),
                "stress_block_alpha": _positive(1),
                "stress_block_gamma": _positive(1),
                "ultimate_compressive_strain": _positive(0.1),
            }
        ),
        "steel": _object(
            {
                "elastic_modulus_mpa": _positive(1_000_000),
                "yield_strength_mpa": _positive(5_000),
                "density_kg_m3": _positive(30_000),
                "fracture_strain": _positive(1),
            }
        ),
        "axial_force_kn": {"type": "number", "minimum": -1_000_000, "maximum": 1_000_000},
        "bending_angle_deg": {"type": "number", "minimum": -180, "maximum": 180},
    },
    required=["section", "concrete", "steel"],
)
INPUT_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
INPUT_SCHEMA["properties"]["axial_force_kn"].update(
    default=0, description="Positive compression; negative tension."
)
INPUT_SCHEMA["properties"]["bending_angle_deg"].update(
    default=0,
    description=(
        "Neutral axis angle counterclockwise from +x. Zero compresses the top (+y) face; "
        "180 compresses the bottom face."
    ),
)

NUMBER = {"type": "number"}
OUTPUT_SCHEMA = _object(
    {
        "analysis_scope": {"const": "nominal_section_mechanics"},
        "standard_compliance_evaluated": {"const": False},
        "solver": _object({"name": {"const": "concreteproperties"}, "version": {"type": "string"}}),
        "dependencies": _object({"sectionproperties": {"type": "string"}}),
        "gross_properties": _object(
            {
                "total_area_mm2": NUMBER,
                "concrete_area_mm2": NUMBER,
                "steel_area_mm2": NUMBER,
                "axial_rigidity_n": NUMBER,
                "elastic_centroid_x_mm": NUMBER,
                "elastic_centroid_y_mm": NUMBER,
                "mass_per_length_kg_m": NUMBER,
                "ei_xx_n_mm2": NUMBER,
                "ei_yy_n_mm2": NUMBER,
                "ei_xy_n_mm2": NUMBER,
            }
        ),
        "ultimate": _object(
            {
                "bending_angle_deg": NUMBER,
                "axial_force_kn": NUMBER,
                "axial_equilibrium_error_kn": NUMBER,
                "neutral_axis_depth_mm": NUMBER,
                "moment_x_knm": NUMBER,
                "moment_y_knm": NUMBER,
                "resultant_moment_knm": NUMBER,
                "maximum_steel_strain": NUMBER,
            }
        ),
        "warnings": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "minItems": 1, "items": {"type": "string"}},
    }
)
OUTPUT_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
