# SPDX-License-Identifier: AGPL-3.0-only
"""OpenCalcs installed-plugin contract for reinforced concrete sections."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from opencalcs_as3600 import __version__
from opencalcs_as3600.schemas import INPUT_SCHEMA, OUTPUT_SCHEMA

CALCULATION_ID = "structural.as3600.section_analysis"


@dataclass(frozen=True)
class SectionAnalysis:
    id: str = CALCULATION_ID
    name: str = "Reinforced concrete section analysis"
    description: str = (
        "Calculate uncracked properties and nominal bending capacity of a rectangular "
        "reinforced concrete section using explicitly supplied material models."
    )
    discipline: str = "structural"
    category: str = "section-analysis"
    jurisdiction: str = "general"
    version: str = "1"
    input_schema: dict[str, Any] = field(default_factory=lambda: deepcopy(INPUT_SCHEMA))
    output_schema: dict[str, Any] = field(default_factory=lambda: deepcopy(OUTPUT_SCHEMA))
    standard: None = None

    def run(self, inputs: Mapping[str, Any]) -> dict[str, Any]:
        # Keep solver imports out of host discovery and descriptor requests.
        from opencalcs_as3600.analysis import run_analysis

        return run_analysis(inputs)

    def descriptor(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "discipline": self.discipline,
            "category": self.category,
            "jurisdiction": self.jurisdiction,
            "version": self.version,
            "standard": None,
            "input_schema": deepcopy(self.input_schema),
            "output_schema": deepcopy(self.output_schema),
        }


@dataclass(frozen=True)
class AS3600Plugin:
    id: str = "structural.as3600"
    name: str = "OpenCalcs Concrete Sections"
    version: str = __version__
    revision: str | None = None
    license: str = "AGPL-3.0-only"
    source: str = "https://github.com/Elandu/OpenCalcs-AS3600"
    calculations: tuple[SectionAnalysis, ...] = field(default_factory=lambda: (SectionAnalysis(),))

    def descriptor(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "revision": self.revision,
            "license": self.license,
            "source": self.source,
            "calculations": [calculation.descriptor() for calculation in self.calculations],
        }


def get_plugin() -> AS3600Plugin:
    """Return the installed plugin without starting a service or importing the solver."""
    return AS3600Plugin()
