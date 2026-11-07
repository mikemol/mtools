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


def test_a_path_frozen_twice_with_the_same_pinned_blob_is_one_file() -> None:
    """Two entries carrying the pinned bytes are one file (an earlier other blob is N6)."""
    frozen = _stack(("src/series.py", _A), ("src/series.py", _A), ("tests/test_series.py", _B))
    assert admission.refusal(_ROW, ["W1660"], frozen) is None


def test_no_row_admits_another_repository_or_a_changed_stack() -> None:
    """`admitting` answers None, not an exception, for a wrong repository or a refused stack."""
    assert admission.admitting([_ROW], "luthen", ["W1660"], _EXACT) is None
    assert admission.admitting([_ROW], "nemik", ["W1660"], _stack(("src/series.py", _A))) is None


def test_the_first_matching_row_of_several_is_found() -> None:
    """Rows are tried in order and the one that matches this stack wins."""
    other = admission.Row(repo="nemik", card="W7", blobs={"x.py": _C})
    assert admission.admitting([other, _ROW], "nemik", ["W1660"], _EXACT) is _ROW


def test_a_row_that_pins_no_path_admits_nothing() -> None:
    """An empty row would otherwise match any stack of its card with only queue files."""
    empty = admission.Row(repo="nemik", card="W1660")
    reason = admission.refusal(empty, ["W1660"], [])
    assert reason == "the row pins no path, so it admits nothing"
    assert admission.admitting([empty], "nemik", ["W1660"], []) is None


def test_the_table_ships_empty_so_nothing_is_admitted_until_a_row_is_added() -> None:
    """A row is a reviewed literal: with none added, the exact change above is not admitted."""
    assert admission.ROWS == ()
    assert admission.admitting(admission.ROWS, "nemik", ["W1660"], _EXACT) is None


_RECORD = "bde02714-1533-475a-b934-d2ce58024a15:104181"
_BIRTH = admission.Row(
    repo="nemik",
    card="W1978",
    blobs={"codon-edges-baseline.json": _A},
    kind=admission.BIRTH,
    ratchet="codon-edges-baseline.json",
    old=0,
    new=7,
    record=_RECORD,
)
_ENTRY = (
    '{"rebaselines": [{"ratchet": "codon-edges-baseline.json", "old": 0, "new": 7, '
    '"reason": "birth", "warrant": "' + _RECORD + '"}]}'
)


def test_a_repair_row_has_no_accident_checks() -> None:
    """The control: only a birth row is asked the accident questions."""
    assert admission.accident(_ROW, {"codon-edges-baseline.json"}, None) is None


def test_a_birth_row_passes_when_the_file_is_new_and_the_entry_cites_the_record() -> None:
    """The control for a birth: new file, matching entry, pinned record."""
    assert admission.accident(_BIRTH, {"src/a.py"}, _ENTRY) is None


def test_a_birth_row_is_refused_for_an_existing_file_a_missing_entry_or_another_record() -> None:
    """Each accident check is reached through the row: file, entry, record."""
    assert admission.accident(_BIRTH, {"codon-edges-baseline.json"}, _ENTRY) is not None
    assert admission.accident(_BIRTH, {"src/a.py"}, None) is not None
    other = _ENTRY.replace("104181", "104182")
    assert admission.accident(_BIRTH, {"src/a.py"}, other) is not None


def _birth_row(*, record: str, ratchet: str) -> admission.Row:
    return admission.Row(
        repo="nemik",
        card="W1978",
        blobs={"baseline.json": _A},
        review="r",
        kind=admission.BIRTH,
        ratchet=ratchet,
        record=record,
    )


def test_a_row_must_cite_a_review_and_a_birth_row_its_record_and_its_ratchet() -> None:
    """N4 and N5: an empty review, an empty record and a ratchet not among the blobs each refuse."""
    unreviewed = admission.Row(repo="nemik", card="W1660", blobs={"a.py": _A})
    assert "no cold review" in str(admission.refusal(unreviewed, ["W1660"], _stack(("a.py", _A))))
    held = _stack(("baseline.json", _A))
    no_record = _birth_row(record="", ratchet="baseline.json")
    assert "no operator record" in str(admission.refusal(no_record, ["W1978"], held))
    stray = _birth_row(record="u:1", ratchet="other.json")
    assert "not among its pinned paths" in str(admission.refusal(stray, ["W1978"], held))
    assert (
        admission.refusal(_birth_row(record="u:1", ratchet="baseline.json"), ["W1978"], held)
        is None
    )


def test_an_earlier_entry_with_unpinned_bytes_and_a_non_regular_mode_are_refused() -> None:
    """N6: the pin covers every entry's bytes for the path, and the file mode."""
    row = admission.Row(repo="nemik", card="W1660", blobs={"a.py": _A}, review="r")
    earlier = _stack(("a.py", _B), ("a.py", _A))
    assert "does not pin" in str(admission.refusal(row, ["W1660"], earlier))
    link = [Frozen("a.py", "120000", _A)]
    assert "not a regular file" in str(admission.refusal(row, ["W1660"], link))
    assert admission.refusal(row, ["W1660"], _stack(("a.py", _A))) is None


def test_a_row_kind_outside_the_closed_set_is_refused_not_read_as_a_repair() -> None:
    """A misspelt kind such as 'Birth' must not skip the birth checks by reading as a repair."""
    odd = admission.Row(repo="nemik", card="W1", blobs={"a.py": _A}, review="r", kind="Birth")
    reason = admission.refusal(odd, ["W1"], _stack(("a.py", _A)))
    assert "unknown row kind" in str(reason)
