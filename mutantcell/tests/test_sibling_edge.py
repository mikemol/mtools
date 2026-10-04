# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The dist-to-dist edges: mutantcell resolves mikemol-mutation and mikemol-importdag."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.atomicwrite.durable import write_atomic
from mikemol.importdag import dagderive
from mikemol.mutation import mutate

from mikemol.mutantcell import sites

if TYPE_CHECKING:
    from pathlib import Path


def test_the_mutation_sibling_resolves_beside_this_distribution() -> None:
    """The mutator's enumerators import and read a source."""
    arms = mutate.branch_sites("def f(v):\n    if v:\n        return 1\n")
    assert [qualname for qualname, _n, _arm in arms] == ["f"]


def test_the_importdag_sibling_resolves_beside_this_distribution() -> None:
    """The flat-import reader imports and reads a source."""
    assert dagderive.flat_imports("import beta\n", {"beta", "gamma"}) == {"beta"}


def test_the_transitive_atomicwrite_resolves_through_importdag(tmp_path: Path) -> None:
    """The sibling of the sibling is declared nowhere here, yet it writes a file."""
    target = tmp_path / "out.txt"
    write_atomic(target, "payload")
    assert target.read_text(encoding="utf-8") == "payload"


def test_this_distribution_still_resolves_beside_its_siblings() -> None:
    """The namespace package merges: importing the siblings does not shadow mikemol.mutantcell."""
    assert sites.__name__ == "mikemol.mutantcell.sites"
