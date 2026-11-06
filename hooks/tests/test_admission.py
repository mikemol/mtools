# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a pinned row admits exactly the change it names and nothing else (W2310).

⚑ THE CONTROL IS THE EXACT MATCH: it is admitted, and every refused case below differs from it by
ONE thing (a waypoint, a path, a missing path, a byte), so each refusal is that difference's.
"""

from __future__ import annotations

from mikemol.hooks import admission
from mikemol.hooks.stacksnap import Frozen

_MODE = "100644"
_A = "a" * 40
_B = "b" * 40
_C = "c" * 40
_QUEUE = ".claude/paths-forward.json"
_ROW = admission.Row(
    repo="nemik",
    card="W1660",
    blobs={"src/series.py": _A, "tests/test_series.py": _B},
    review="cold review of 2026-11-06",
)


def _stack(*pairs: tuple[str, str]) -> list[Frozen]:
    """Freeze `(path, blob)` pairs as a submit would.

    Returns:
        the frozen files, in order.

    """
    return [Frozen(path, _MODE, blob) for path, blob in pairs]


_EXACT = _stack(("src/series.py", _A), ("tests/test_series.py", _B))


def test_the_exact_change_is_admitted_and_names_its_row() -> None:
    """The control: the pinned paths at the pinned blobs under the row's card admit."""
    assert admission.refusal(_ROW, ["W1660"], _EXACT) is None
    found = admission.admitting([_ROW], "nemik", ["W1660"], _EXACT)
    assert found is _ROW
    assert found.ident() == "nemik/W1660"


def test_queue_files_ride_free_and_a_repeated_waypoint_is_one_card() -> None:
    """A queue file at any blob, and several entries of the same card, change nothing."""
    frozen = [*_EXACT, *_stack((_QUEUE, _C))]
    assert admission.refusal(_ROW, ["W1660", "W1660", "W1660"], frozen) is None


def test_another_card_or_no_card_is_refused() -> None:
    """Every entry must be the row's card: one other waypoint, or none, refuses."""
    assert "not only W1660" in str(admission.refusal(_ROW, ["W1660", "W9"], _EXACT))
    assert "not only W1660" in str(admission.refusal(_ROW, ["W9"], _EXACT))
    assert "not only W1660" in str(admission.refusal(_ROW, [], _EXACT))


def test_a_path_the_row_does_not_pin_is_refused_by_name() -> None:
    """The row pins a change, not a directory: an extra file is not admitted."""
    frozen = [*_EXACT, *_stack(("tests/test_other.py", _C))]
    reason = admission.refusal(_ROW, ["W1660"], frozen)
    assert reason == "the stack carries a path the row does not pin: tests/test_other.py"


def test_a_pinned_path_the_stack_does_not_carry_is_refused_by_name() -> None:
    """Half the change is not the change."""
    reason = admission.refusal(_ROW, ["W1660"], _stack(("src/series.py", _A)))
    assert reason == "the row pins a path the stack does not carry: tests/test_series.py"


def test_a_changed_byte_is_refused_naming_the_path_and_the_blob_it_holds() -> None:
    """The same paths at a different blob are a different change."""
    frozen = _stack(("src/series.py", _C), ("tests/test_series.py", _B))
    reason = admission.refusal(_ROW, ["W1660"], frozen)
    assert reason == f"src/series.py is not the pinned blob (the stack holds {_C})"


def test_a_deletion_is_not_the_pinned_blob() -> None:
    """A frozen deletion has an empty blob and says so."""
    frozen = _stack(("src/series.py", ""), ("tests/test_series.py", _B))
    assert "the stack holds a deletion" in str(admission.refusal(_ROW, ["W1660"], frozen))


def test_a_path_frozen_twice_is_judged_by_its_last_blob() -> None:
    """A later entry's file replaces an earlier one's, as the landing does."""
    frozen = _stack(("src/series.py", _C), ("src/series.py", _A), ("tests/test_series.py", _B))
    assert admission.refusal(_ROW, ["W1660"], frozen) is None


def test_no_row_admits_another_repository_or_a_changed_stack() -> None:
    """`admitting` answers None, not an exception, for a wrong repository or a refused stack."""
    assert admission.admitting([_ROW], "luthen", ["W1660"], _EXACT) is None
    assert admission.admitting([_ROW], "nemik", ["W1660"], _stack(("src/series.py", _A))) is None


def test_the_first_matching_row_of_several_is_found() -> None:
    """Rows are tried in order and the one that matches this stack wins."""
    other = admission.Row(repo="nemik", card="W7", blobs={"x.py": _C})
    assert admission.admitting([other, _ROW], "nemik", ["W1660"], _EXACT) is _ROW


def test_the_table_ships_empty_so_nothing_is_admitted_until_a_row_is_added() -> None:
    """A row is a reviewed literal: with none added, the exact change above is not admitted."""
    assert admission.ROWS == ()
    assert admission.admitting(admission.ROWS, "nemik", ["W1660"], _EXACT) is None
