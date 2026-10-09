# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 Elandu and contributors

"""EngCalcs reinforced concrete section mechanics plugin."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("engcalcs-as3600")
except PackageNotFoundError:
    __version__ = "0.1.1"

__all__ = ["__version__"]
