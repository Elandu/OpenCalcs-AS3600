# OpenCalcs AS3600 Plugin

`opencalcs-as3600` is a Python plugin package maintained in this repository. OpenCalcs
discovers it through `opencalcs.plugins`; OpenCalcs-UI owns the browser interface.
It uses the MIT-licensed upstream libraries
[concreteproperties](https://github.com/robbievanleeuwen/concrete-properties) and
[sectionproperties](https://github.com/robbievanleeuwen/section-properties).

The initial calculation returns uncracked composite section properties and nominal bending
capacity for a rectangular reinforced concrete section. Geometry, reinforcement and material
coefficients are supplied explicitly. **AS 3600 design checks are not implemented in this
release**: the standard descriptor is null and `standard_compliance_evaluated` is false.

## Install into OpenCalcs

Install the host and this plugin in the same Python environment. From an OpenCalcs checkout:

```powershell
python -m pip install .
python -m pip install "git+https://github.com/Elandu/OpenCalcs-AS3600.git@v0.1.0"
```

For local development:

```powershell
python -m pip install -e "Y:\OSRS\OpenCalcs-AS3600[dev]"
```

Restart the OpenCalcs API after installing. No changes to its discovery code are needed.
The package does not install OpenCalcs implicitly and is not published on PyPI.
Installation into a deployed backend is a separate deployment action.

## Calculation and API

Plugin: `structural.as3600`.
Calculation: `structural.as3600.section_analysis`.

- Descriptor: `GET /api/v1/calculations/structural.as3600.section_analysis`.
- Run: `POST /api/v1/calculations/structural.as3600.section_analysis/run`.
- Request body: `{"inputs": <section model>}`.
- Example model: [examples/rectangular_section.json](examples/rectangular_section.json).

With the repository as the current directory, this runs the model through the installed host:

```python
import json
from pathlib import Path
from opencalcs.registry import CalculationRegistry

inputs = json.loads(Path("examples/rectangular_section.json").read_text())
result = CalculationRegistry().run("structural.as3600.section_analysis", inputs)
print(json.dumps(result, indent=2, allow_nan=False))
```

Coordinates are measured from the rectangle's bottom-left corner. Geometry uses mm, material
stress and elastic modulus use MPa, densities use kg/m³, axial load uses kN, and returned moments
use kN·m. Axial compression is positive. `bending_angle_deg` specifies the neutral-axis angle
counterclockwise from +x; zero compresses the top face and 180 compresses the bottom face.
At an arbitrary angle, both moment components are returned. Moments are about the elastic centroid.

The example's independent nominal capacity is **300.87890625 kN·m**. Output also includes
composite area, centroid, EA, EI, mass per metre, neutral-axis depth, force residual, maximum
steel strain, library versions and limitations. Models with duplicate, overlapping or outside
bars, nonfinite numbers, insufficient fracture strain or unsolvable axial loads are rejected.

## Development and validation

Use Python 3.11–3.13. On Windows, keep the virtual environment on a local drive when using a
mapped network checkout.

```powershell
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m pytest
python -m build
```

Tests require the OpenCalcs host; CI installs the pinned host revision documented in
[validation](docs/validation.md), then checks the built wheel through the host registry and API.
See [scope and reference policy](docs/scope.md) for the standard-check roadmap.

## License

AGPL-3.0-only. Upstream dependencies retain their own licenses. Licensed standards documents
and extracted standard text are not distributed in this repository.
