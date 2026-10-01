# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

from importlib.metadata import entry_points

from fastapi.testclient import TestClient
from opencalcs.api import create_app
from opencalcs.auth import AllowAllAuthenticator
from opencalcs.registry import CalculationRegistry

from opencalcs_as3600.plugin import CALCULATION_ID, get_plugin


def test_installed_entry_point_and_descriptor() -> None:
    entry = next(item for item in entry_points(group="opencalcs.plugins") if item.name == "as3600")
    plugin = entry.load()()
    assert plugin.id == "structural.as3600"
    assert plugin.version == "0.1.1"
    descriptor = plugin.descriptor()
    assert descriptor["calculations"][0]["id"] == CALCULATION_ID
    assert descriptor["calculations"][0]["standard"] is None
    assert get_plugin().calculations[0].standard is None


def test_descriptors_do_not_expose_mutable_validation_schemas() -> None:
    calculation = get_plugin().calculations[0]
    descriptor = calculation.descriptor()
    properties = descriptor["input_schema"]["properties"]["section"]["properties"]
    properties["width_mm"]["maximum"] = 0
    own_properties = calculation.input_schema["properties"]["section"]["properties"]
    assert own_properties["width_mm"]["maximum"] == 10_000
    assert get_plugin().calculations[0].input_schema == calculation.input_schema


def test_real_host_discovery_run_and_provenance(section_inputs: dict) -> None:
    registry = CalculationRegistry()
    assert "structural.as3600" in {item.id for item in registry.plugins}
    assert CALCULATION_ID in {item["id"] for item in registry.list_calculations()}
    result = registry.run(CALCULATION_ID, section_inputs)
    assert result["solver"]["version"] == "0.8.0"
    assert result["_provenance"]["engine"]["id"] == "structural.as3600"
    assert result["_provenance"]["engine"]["version"] == "0.1.1"
    assert result["standard_compliance_evaluated"] is False


def test_host_api_descriptor_and_run(section_inputs: dict) -> None:
    with TestClient(create_app(authenticator=AllowAllAuthenticator())) as client:
        definition = client.get(f"/api/v1/calculations/{CALCULATION_ID}")
        assert definition.status_code == 200
        assert definition.json()["plugin"]["id"] == "structural.as3600"
        assert definition.json()["standard"] is None
        response = client.post(
            f"/api/v1/calculations/{CALCULATION_ID}/run", json={"inputs": section_inputs}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["ultimate"]["moment_x_knm"] > 300
        assert result["_provenance"]["engine"]["id"] == "structural.as3600"


def test_host_api_invalid_model_rejected(section_inputs: dict) -> None:
    section_inputs["section"]["bars"][0]["x_mm"] = 0
    with TestClient(create_app(authenticator=AllowAllAuthenticator())) as client:
        response = client.post(
            f"/api/v1/calculations/{CALCULATION_ID}/run", json={"inputs": section_inputs}
        )
        assert response.status_code == 422
