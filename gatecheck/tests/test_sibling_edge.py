# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The dist-to-dist edge: gatecheck resolves mikemol-importdag, and atomicwrite through it."""

from __future__ import annotations

from mikemol.atomicwrite import durable
from mikemol.importdag import dagnames

from mikemol.gatecheck import indexdiverge


def test_the_sibling_resolves_beside_this_distribution() -> None:
    """The sibling's dagnames imports, and its namespace package merges with this one."""
    assert dagnames.__name__ == "mikemol.importdag.dagnames"


def test_the_siblings_dependency_resolves_transitively() -> None:
    """The atomicwrite helper is not declared here: uv and Bazel both bring it through importdag."""
    assert durable.__name__ == "mikemol.atomicwrite.durable"


def test_this_distribution_still_resolves_beside_its_siblings() -> None:
    """Importing the siblings does not shadow mikemol.gatecheck."""
    assert indexdiverge.__name__ == "mikemol.gatecheck.indexdiverge"
