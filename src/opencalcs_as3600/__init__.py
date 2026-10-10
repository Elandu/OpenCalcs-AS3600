# SPDX-License-Identifier: LicenseRef-EngCalcs-Proprietary
# Copyright (c) 2026 Elandu and contributors

"""OpenCalcs reinforced concrete section mechanics plugin."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("opencalcs-as3600")
except PackageNotFoundError:
    __version__ = "0.1.1"

__all__ = ["__version__"]
