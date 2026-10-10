# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The scaffold's one witness: the package imports and says what it is."""

from __future__ import annotations

import mikemol.htmlstruct as package


def test_the_package_imports_and_carries_its_docstring() -> None:
    """The scaffold compiles, imports and documents itself."""
    assert package.__doc__ is not None
