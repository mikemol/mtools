# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A ratchet may rise only with a written, warranted re-baseline in the same change (W2024).

⚑ THE CONTROLS: a rise with no entry is refused and named, a rise with an entry of exactly that
old and new is admitted, an entry for another rise does not cover it, a fall and an unread or new
ratchet need nothing, an entry that is not a rise or has no reason or a malformed warrant is
refused, and the same comparison runs over declared and name-classified ratchets alike.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.ratchet import cli, rebaseline

if TYPE_CHECKING:
    from pathlib import Path

_WARRANT = "bde02714-1533-475a-b934-d2ce58024a15:104181"
_REASON = "upstream-dictated name, operator chose (a)"
_PATH = "stubs/ratchet-preview.txt"


def _entry(**given: object) -> dict[str, object]:
    base: dict[str, object] = {
        "ratchet": _PATH,
        "old": 0,
        "new": 1,
        "reason": _REASON,
        "warrant": _WARRANT,
    }
    return {**base, **given}


def _write(repo: Path, entries: list[dict[str, object]]) -> None:
    body: dict[str, object] = {"rebaselines": entries}
    (repo / rebaseline.NAME).write_text(json.dumps(body), encoding="utf-8")


def _tree(root: Path, lines: int) -> Path:
    root.mkdir(parents=True)
    target = root / "stubs"
    target.mkdir()
    (target / "ratchet-preview.txt").write_text("k\n" * lines, encoding="utf-8")
    return root


def test_a_rise_with_no_entry_is_refused_and_names_the_entry_it_needs() -> None:
    """The line says the path, the old and the new value, and what to add."""
    [line] = rebaseline.refusals({_PATH: 0}, {_PATH: 1}, [])
    assert line.startswith(f"{_PATH}: rose 0 to 1 with no rebaselines entry")


def test_a_rise_with_an_entry_of_exactly_that_old_and_new_is_admitted() -> None:
    """The declared move: (ratchet, old, new) all match."""
    entry = rebaseline.Rebaseline(_PATH, 0, 1, _REASON, _WARRANT)
    assert rebaseline.refusals({_PATH: 0}, {_PATH: 1}, [entry]) == []


def test_an_entry_for_another_rise_does_not_cover_this_one() -> None:
    """Old 0 to 2 does not cover 0 to 1, and another ratchet's entry covers nothing here."""
    wrong_new = rebaseline.Rebaseline(_PATH, 0, 2, _REASON, _WARRANT)
    other = rebaseline.Rebaseline("other.txt", 0, 1, _REASON, _WARRANT)
    assert rebaseline.refusals({_PATH: 0}, {_PATH: 1}, [wrong_new, other])


def test_a_fall_an_unread_value_and_a_birth_at_zero_need_no_entry() -> None:
    """Paydown is what a ratchet is for; UNREAD is not a number; nothing born is nothing owed."""
    assert rebaseline.refusals({_PATH: 3}, {_PATH: 1}, []) == []
    assert rebaseline.refusals({_PATH: None}, {_PATH: 1}, []) == []
    assert rebaseline.refusals({_PATH: 1}, {_PATH: None}, []) == []
    assert rebaseline.refusals({}, {_PATH: 0}, []) == []


def test_a_ratchet_born_at_a_nonzero_value_needs_an_entry_from_zero() -> None:
    """W2024's birth judgement: a new baseline already holding 4 is 4 of expansion.

    The control is the same birth with an entry of old 0 and new 4, which is admitted, and an entry
    for a different new value, which is not.
    """
    [line] = rebaseline.refusals({}, {_PATH: 4}, [])
    assert line.startswith(f"{_PATH}: was born at 4 with no rebaselines entry")
    assert '"old": 0, "new": 4' in line
    declared = rebaseline.Rebaseline(_PATH, 0, 4, _REASON, _WARRANT)
    assert rebaseline.refusals({}, {_PATH: 4}, [declared]) == []
    wrong = rebaseline.Rebaseline(_PATH, 0, 3, _REASON, _WARRANT)
    assert rebaseline.refusals({}, {_PATH: 4}, [wrong])


def test_an_entry_the_tree_before_declared_may_not_vanish_or_change() -> None:
    """Entries only grow: removing one, or editing its reason, is named; adding one is not."""
    old = rebaseline.Rebaseline(_PATH, 0, 1, _REASON, _WARRANT)
    added = rebaseline.Rebaseline("other.txt", 0, 2, _REASON, _WARRANT)
    assert rebaseline.lost([old], [old, added]) == []
    assert rebaseline.lost([old], [added]) == [
        f"{_PATH}: the entry 0 to 1 was removed or changed; entries only grow"
    ]
    edited = rebaseline.Rebaseline(_PATH, 0, 1, "a different reason", _WARRANT)
    assert rebaseline.lost([old], [edited])
    assert rebaseline.lost([], [old]) == []


@pytest.mark.parametrize(
    "bad",
    [
        _entry(old=1, new=1),
        _entry(old=2, new=1),
        _entry(reason=" "),
        _entry(warrant="not-a-warrant"),
        _entry(ratchet=""),
        _entry(old="0"),
    ],
)
def test_an_entry_that_is_not_a_warranted_rise_is_refused(
    tmp_path: Path, bad: dict[str, object]
) -> None:
    """Not a rise, no reason, a warrant that is not uuid:line, no ratchet, a non-integer."""
    _write(tmp_path, [bad])
    with pytest.raises(rebaseline.RebaselineError):
        rebaseline.read(tmp_path)


def test_no_file_is_no_entries_and_a_file_without_the_list_is_refused(tmp_path: Path) -> None:
    """Absent is none; a file that is not the shape is a refusal, never read as empty."""
    assert rebaseline.read(tmp_path) == []
    (tmp_path / rebaseline.NAME).write_text("{}", encoding="utf-8")
    with pytest.raises(rebaseline.RebaselineError):
        rebaseline.read(tmp_path)


def test_check_compares_two_trees_and_admits_a_declared_rise(tmp_path: Path) -> None:
    """The name-classified ratchet-preview.txt gains a line; the entry in the new tree covers it."""
    before, after = _tree(tmp_path / "before", 0), _tree(tmp_path / "after", 1)
    assert rebaseline.check(after, before)
    _write(after, [_entry()])
    assert rebaseline.check(after, before) == []


def test_check_refuses_a_declaration_deleted_after_it_was_made(tmp_path: Path) -> None:
    """The ratchet value did not move, but the entry that excused it is gone: still refused."""
    before, after = _tree(tmp_path / "before", 1), _tree(tmp_path / "after", 1)
    _write(before, [_entry()])
    assert rebaseline.check(after, before) == [
        f"{_PATH}: the entry 0 to 1 was removed or changed; entries only grow"
    ]
    _write(after, [_entry()])
    assert rebaseline.check(after, before) == []


def test_the_command_exits_one_on_an_unexplained_rise_and_zero_when_declared(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`mikemol-ratchet rebaselines --repo AFTER --before BEFORE` prints each rise it refuses."""
    before, after = _tree(tmp_path / "before", 0), _tree(tmp_path / "after", 1)
    argv = ["rebaselines", "--repo", str(after), "--before", str(before)]
    assert cli.main(argv) == 1
    assert "rose 0 to 1" in capsys.readouterr().out
    _write(after, [_entry()])
    assert cli.main(argv) == 0


def test_the_command_refuses_an_untrustworthy_file_without_a_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A malformed rebaselines file is exit 1 and a line on stderr."""
    before, after = _tree(tmp_path / "before", 0), _tree(tmp_path / "after", 1)
    (after / rebaseline.NAME).write_text("{nope", encoding="utf-8")
    argv = ["rebaselines", "--repo", str(after), "--before", str(before)]
    assert cli.main(argv) == 1
    assert "cannot be read as JSON" in capsys.readouterr().err
