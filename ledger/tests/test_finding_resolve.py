# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.ledger.finding_resolve`: substrate's suite, ported case for case.

⚑ AMBIGUITY IS ASSERTED IN BOTH DIRECTIONS: a case checking only that a unique prefix resolves
would hold against a resolver that picks the first hit — the defect the refusal exists to prevent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.ledger import finding_resolve

if TYPE_CHECKING:
    from collections.abc import Callable


def _thunk(code: int, note: str) -> Callable[[], tuple[int, str]]:
    """Build a stand-in witness, so a fixture roster needs no real command.

    Returns:
        the witness.

    """

    def run() -> tuple[int, str]:
        return code, note

    return run


# ⚑ THE FIXTURE MIRRORS A LIVE ROSTER'S AWKWARD SHAPE: a bare stem that is also a prefix, plus a
#   sibling family that makes a short stem ambiguous.
_ROSTER: dict[str, Callable[[], tuple[int, str]]] = {
    "aa-F1": _thunk(0, "one"),
    "aa-F10": _thunk(0, "ten"),
    "aa-F11": _thunk(0, "eleven"),
    "bb-F2-descriptive-tail": _thunk(1, "two"),
    "cc-F3": _thunk(2, "three"),
}


def test_an_exact_key_wins_though_it_prefixes_longer_keys() -> None:
    """`aa-F1` resolves to itself and runs, though it also prefixes aa-F10 and aa-F11."""
    answer = finding_resolve.resolve("aa-F1", _ROSTER)
    key, hit = answer
    assert key == "aa-F1"
    assert not finding_resolve.unresolved(answer)
    assert hit is not None
    assert hit()[1] == "one"


def test_a_unique_prefix_resolves_to_its_full_key() -> None:
    """A unique prefix resolves to the full key and carries that key's witness."""
    key, hit = finding_resolve.resolve("bb-F2", _ROSTER)
    assert key == "bb-F2-descriptive-tail"
    assert hit is not None
    assert hit()[1] == "two"


def test_an_ambiguous_prefix_refuses_naming_every_candidate() -> None:
    """An ambiguous prefix REFUSES rather than picking, names its candidates, and says why."""
    text, hit = finding_resolve.resolve("aa-F", _ROSTER)
    assert hit is None
    assert "AMBIGUOUS" in text
    assert all(key in text for key in ("aa-F1", "aa-F10", "aa-F11"))
    assert "reads like a right one" in text


def test_an_unknown_key_is_its_own_outcome() -> None:
    """An unknown key does not resolve, and is named as a possible roster/record disagreement."""
    answer = finding_resolve.resolve("zz-nothing-like-this", _ROSTER)
    text, _ = answer
    assert finding_resolve.unresolved(answer)
    assert "no witness registered" in text
    assert "roster/record" in text
