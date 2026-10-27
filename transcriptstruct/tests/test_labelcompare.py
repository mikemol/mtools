# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Two labellers' labels are compared per kind over the rows both carry and nobody fitted (W2052).

⚑ THE CONTROLS: an excluded id is not counted, an id only one side carries is not counted, recall
is over MY rows and precision over THEIRS, a figure is printed as `k of n`, an unknown word on one
side is kept in the confusion and not folded, and a file that cannot be read is exit 2.
"""

import json
from itertools import starmap
from pathlib import Path

import pytest

from mikemol.transcriptstruct import labelcompare

_USAGE = 2
_MINE = {"1": "commitment", "2": "commitment", "3": "announce", "4": "status", "5": "announce"}
_THEIRS = {"1": "commitment", "2": "other", "3": "announce", "4": "commitment", "5": "other"}


def _row(ident: str, word: str) -> str:
    row: dict[str, str] = {"id": ident, "label": word}
    return json.dumps(row) + "\n"


def _lines(labels: dict[str, str]) -> str:
    return "".join(starmap(_row, labels.items()))


def test_a_label_file_is_read_by_id_and_a_torn_or_foreign_line_is_skipped() -> None:
    """Ids come back as text; a line that is not an object with both keys is left out."""
    text = '{"id": 7, "label": "status"}\n{nope\n{"id": 8}\n["x"]\n'
    assert labelcompare.read_labels(text) == {"7": "status"}
    assert labelcompare.read_ids("3 5\n9\n") == {"3", "5", "9"}


def test_the_confusion_counts_only_ids_both_carry_and_not_the_excluded() -> None:
    """Id 5 is excluded, id 6 is only mine, id 7 only theirs: none of them is a cell."""
    mine = {**_MINE, "6": "done"}
    theirs = {**_THEIRS, "7": "status"}
    pairs = labelcompare.confusion(mine, theirs, {"5"})
    assert pairs == {
        ("commitment", "commitment"): 1,
        ("commitment", "other"): 1,
        ("announce", "announce"): 1,
        ("status", "commitment"): 1,
    }


def test_recall_is_over_my_rows_and_precision_over_theirs_as_counts() -> None:
    """Commitment: I gave it to 2, they to 2, both to 1; each figure is `k of n`."""
    pairs = labelcompare.confusion(_MINE, _THEIRS, {"5"})
    assert labelcompare.kind_line(pairs, "commitment") == (
        "commitment: mine 2, theirs 2, both 1; recall 1 of 2, precision 1 of 2"
    )
    assert labelcompare.kind_line(pairs, "announce") == (
        "announce: mine 1, theirs 1, both 1; recall 1 of 1, precision 1 of 1"
    )


def test_recall_and_precision_are_not_interchangeable() -> None:
    """I gave commitment to 3 rows, they to 1, both to 1: recall 1 of 3, precision 1 of 1."""
    pairs = {("commitment", "commitment"): 1, ("commitment", "other"): 2}
    assert labelcompare.kind_line(pairs, "commitment") == (
        "commitment: mine 3, theirs 1, both 1; recall 1 of 3, precision 1 of 1"
    )


def test_a_kind_nobody_used_scores_zero_of_zero_not_a_division() -> None:
    """No rows of the kind: `0 of 0`, never a ratio that raises or reads as 100 percent."""
    pairs = labelcompare.confusion(_MINE, _THEIRS, set())
    assert labelcompare.kind_line(pairs, "mention").endswith("recall 0 of 0, precision 0 of 0")


def test_a_word_only_one_side_uses_stays_in_the_confusion() -> None:
    """Their `other` has no counterpart in my words: it is a cell, not folded into status."""
    lines = labelcompare.render(labelcompare.confusion(_MINE, _THEIRS, set()), ("commitment",))
    assert any("theirs=other" in line for line in lines)
    assert lines[0] == "rows compared: 5"


def test_the_command_reads_two_files_and_an_exclude_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 0, the excluded id left out, the default kinds scored."""
    mine, theirs, skip = tmp_path / "m.jsonl", tmp_path / "t.jsonl", tmp_path / "ids.txt"
    mine.write_text(_lines(_MINE), encoding="utf-8")
    theirs.write_text(_lines(_THEIRS), encoding="utf-8")
    skip.write_text("5\n", encoding="utf-8")
    argv = [str(mine), str(theirs), "--exclude", str(skip)]
    assert labelcompare.main(argv) == 0
    said = capsys.readouterr().out
    assert "rows compared: 4" in said
    assert "commitment: mine 2, theirs 2, both 1" in said
    assert "announce: mine 1, theirs 1, both 1" in said


def test_an_unreadable_file_is_exit_two_with_a_line_on_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing label file is a usage failure and prints nothing on stdout."""
    assert labelcompare.main([str(tmp_path / "gone"), str(tmp_path / "gone2")]) == _USAGE
    captured = capsys.readouterr()
    assert not captured.out
    assert "labelcompare:" in captured.err
