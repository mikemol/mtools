# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The two runtime dependencies of cvdcore are present in the environment the tests run in."""

from __future__ import annotations

import importlib

_DEPENDENCIES = ("numpy", "colorspacious")


def test_the_runtime_dependencies_import() -> None:
    """Both dependencies import by name, so the hub and the lock agree with the pyproject."""
    for name in _DEPENDENCIES:
        assert importlib.import_module(name).__name__ == name
