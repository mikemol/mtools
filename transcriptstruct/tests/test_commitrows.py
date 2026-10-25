# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Rows another extractor wrote are read whole or refused, deduplicated, and never inflate (W1986).

⚑ THE FIXTURES ARE THE AGREED ROW: the same place found by two families is one row naming both, a
guess every source flagged is uncertain and uncounted, a firm source outvotes an uncertain one, and
a line that is not a well-typed row refuses the whole file naming its number.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, cast

from mikemol.transcriptstruct import commitledger, commitrows
from mikemol.transcriptstruct.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_CARDS: list[dict[str, object]] = [{"symbol": "W1", "status": "ready"}]
_REFUSED = 1
_USAGE = 2


def _line(number: int, family: str, *, repo: str = "mtools", **extra: object) -> str:
    row: dict[str, object] = {
        "line": number,
        "uuid": "u1",
        "session": "sess",
        "repo": repo,
        "family": family,
        "text": "",
        "names": ["W1"],
        "at": "T",
    }
    row.update(extra)
    return json.dumps(row)


def test_one_place_found_twice_is_one_row_naming_both_families() -> None:
    """The first row is kept and the families are listed in the order seen."""
    rows, why = commitrows.read([_line(3, "canonical"), _line(3, "amr")], "mtools")
    assert not why
    assert [(r.commitment.line, r.families) for r in rows] == [(3, ("canonical", "amr"))]


def test_uncertain_only_when_every_source_said_so() -> None:
    """A firm source and an uncertain one agreeing is a firm commitment."""
    unsure = [_line(3, "a", uncertain=True), _line(3, "b", uncertain=True)]
    mixed = [_line(3, "a", uncertain=True), _line(3, "b")]
    assert [r.uncertain for r in commitrows.read(unsure, "mtools")[0]] == [True]
    assert [r.uncertain for r in commitrows.read(mixed, "mtools")[0]] == [False]


def test_other_repositories_rows_are_left_out_and_text_is_carried_as_given() -> None:
    """Rows are per repository, and an empty text stays empty."""
    rows, _ = commitrows.read([_line(1, "a", repo="other"), _line(2, "a")], "mtools")
    assert [r.commitment.line for r in rows] == [2]
    assert not rows[0].commitment.text


def test_a_bad_line_refuses_the_whole_file_and_names_it() -> None:
    """Not JSON, not an object, a bool line and a non-string name each refuse."""
    good = _line(1, "a")
    bad = [
        "not json",
        "[1]",
        _line(2, "a", line=True),
        _line(2, "a", names=[1]),
        _line(2, "a", uncertain="yes"),
    ]
    for line in bad:
        assert commitrows.read([good, line], "mtools") == ([], "line 2 is not a commitment row")


def test_an_uncertain_row_is_resolved_but_never_counted() -> None:
    """The ledger row keeps the flag and the sources, and the metric leaves it out."""
    lines = [_line(1, "a", names=[], uncertain=True), _line(2, "a", names=[])]
    resolved = commitrows.resolve(commitrows.read(lines, "mtools")[0], _CARDS)
    assert commitledger.counted(resolved) == {"none": 1}
    assert commitledger.uncertain_count(resolved) == 1
    record = commitledger.record(resolved[0])
    assert (record["uncertain"], record["families"]) == (True, ["a"])
    assert "uncertain" not in commitledger.record(resolved[1])


def test_the_resolve_mode_writes_the_document_then_a_tally(tmp_path: Path) -> None:
    """The mode's output, and its two refusals: no --queue and a bad row."""
    rows_file = tmp_path / "rows.jsonl"
    rows_file.write_text(_line(1, "a") + "\n" + _line(2, "a", names=[], uncertain=True) + "\n")
    queue = tmp_path / "queue.json"
    body: dict[str, object] = {"waypoints": _CARDS}
    queue.write_text(json.dumps(body), encoding="utf-8")
    out = io.StringIO()
    args = [str(rows_file), "--resolve", "--queue", str(queue), "--repo", "mtools"]
    assert main(args, out) == 0
    document, tally = out.getvalue().splitlines()
    parsed = cast("dict[str, object]", json.loads(document))
    listed = cast("list[dict[str, object]]", parsed["rows"])
    assert [r["layer"] for r in listed] == ["card", "none"]
    assert tally == "# 0 counted: {}, 1 uncertain"
    assert main([str(rows_file), "--resolve", "--repo", "mtools"], io.StringIO()) == _USAGE
    rows_file.write_text("nope\n")
    assert main(args, io.StringIO()) == _REFUSED
