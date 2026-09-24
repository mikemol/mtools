# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.witness.witness_row`: substrate's `witness_row_selftest` arms, ported.

Two arms deliberately break the type contract (a size on a verdict, a write to a frozen row). They
reach it through a precise Protocol cast and a non-literal attribute name, not a line suppression.
"""

from __future__ import annotations

import dataclasses
from typing import Protocol, cast

import pytest

from mikemol.witness import witness_row


class _VerdictWithSize(Protocol):
    """The constructor as a caller that WANTS a size would call it: the call this arm refuses."""

    def __call__(self, *, key: str, state: str, why: str, size: int) -> object:
        """Build a verdict with a size."""
        ...


def test_a_verdict_refuses_a_size() -> None:
    """The verdict record does not accept a size.

    ⚑ The retirement, pinned: the size/rows reconciliation caught a live `mods[:12]` truncation,
    and it is retired because one walk makes the defect inexpressible. A `size` field here would
    be the second derivation returning under a new name.
    """
    build = cast("_VerdictWithSize", witness_row.Verdict)
    with pytest.raises(TypeError, match="size"):
        build(key="k", state=witness_row.OPEN, why="w", size=3)


def test_only_the_exact_closed_state_resolves() -> None:
    """An unrecognised state reads as open; closed is closed; opened is open.

    ⚑ Every not-ok predicate points the same way: a state nobody recognises must never resolve to
    closed, because a typo would then close an item silently.
    """
    assert witness_row.Verdict(key="k", state="dunno", why="w").is_open
    assert not witness_row.closed("k", "w").is_open
    assert witness_row.opened("k", "w").is_open


def test_the_state_spelling_is_case_sensitive() -> None:
    """`OPEN` is uppercase and `closed` is not, and neither is normalised.

    ⚑ The letter's one contract detail: a `CLOSED` spelled in capitals is not the closed state, so
    it reads as open rather than being quietly folded into the resolved one.
    """
    assert (witness_row.OPEN, witness_row.CLOSED) == ("OPEN", "closed")
    assert witness_row.Verdict(key="k", state="CLOSED", why="w").is_open


def test_a_part_carries_its_route() -> None:
    """The route survives onto the row.

    ⚑ The route is what the graph reads: a witness's per-provider routes were once discarded at
    the boundary, surviving only inside a formatted string.
    """
    assert witness_row.part("k", "n", route="sub-item K-child").route == "sub-item K-child"


def test_rows_are_immutable() -> None:
    """A row cannot be mutated after it is emitted.

    ⚑ A yielded row may already have been consumed, so a later mutation would change a value
    someone already acted on — the deposit-and-read-back shape this contract replaces.
    """
    row = witness_row.part("k", "n")
    attribute = "name"
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(row, attribute, "other")


def test_the_detail_is_per_row() -> None:
    """Two rows do not share one detail mapping.

    ⚑ The mutable-default trap: a shared dict would let one witness's detail appear on another's
    row, which reads as a measurement rather than as a bug.
    """
    first, second = witness_row.part("a", "1"), witness_row.part("b", "2")
    first.detail["x"] = "1"
    assert not second.detail


def test_a_part_and_a_verdict_carry_distinct_kinds() -> None:
    """A reader can tell a part from a verdict by its kind."""
    assert witness_row.part("k", "n").kind != witness_row.opened("k", "w").kind
