# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The dist-to-dist edge: mdstruct resolves mikemol-pathwalk beside its own package (W562)."""

from __future__ import annotations

from mikemol.pathwalk import walk

from mikemol import mdstruct


def test_the_sibling_walk_is_importable_beside_this_distribution() -> None:
    """The sibling's walk module imports and exposes the directory-operand expansion."""
    assert walk.expand.__module__ == "mikemol.pathwalk.walk"


def test_this_distribution_still_resolves_beside_its_sibling() -> None:
    """The namespace package merges: importing the sibling does not shadow mikemol.mdstruct."""
    assert mdstruct.__name__ == "mikemol.mdstruct"
