# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit material-model fixture; the values are not AS 3600 defaults."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def section_inputs() -> dict:
    example = Path(__file__).resolve().parents[1] / "examples" / "rectangular_section.json"
    return json.loads(example.read_text(encoding="utf-8"))
