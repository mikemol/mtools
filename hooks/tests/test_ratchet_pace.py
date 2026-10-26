# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Which ratchets a repository still owes, read from nemik's pace file, never recomputed (W1920).

⚑ THE CONTROLS: an ok row, another repo's row and a row that cannot be paid (the requirement exceeds
the entries its file holds) are NOT owed; a ratchet whose entries cannot be counted still is, and a
torn line is counted as unread and never read as ok.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.hooks import ratchet_pace

if TYPE_CHECKING:
    from pathlib import Path

_HEAD = '{"as_of": "2026-10-26T12:34:36Z", "window": "10"}'
_ROWS = 3
_TWO = 2


def _line(repo: str, ratchet: str, state: str, observed: int, required: int) -> str:
    row = {
        "repo": repo,
        "ratchet": ratchet,
        "state": state,
        "observed": str(observed),
        "required": str(required),
    }
    return json.dumps(row)


def test_the_head_is_skipped_and_a_torn_line_is_counted_not_read_as_ok() -> None:
    """Three rows are read; the head and a half-written line are not rows, the latter is counted."""
    text = "\n".join(
        [
            _HEAD,
            _line("mtools", "a.txt", "behind", 0, 1),
            "{not json",
            _line("mtools", "b.txt", "ok", 0, 0),
            _line("nemik", "c.json", "behind", 0, 2),
        ]
    )
    rows, unread = ratchet_pace.read_rows(text)
    assert [r.ratchet for r in rows] == ["a.txt", "b.txt", "c.json"]
    assert len(rows) == _ROWS
    assert unread == 1


def test_owed_keeps_behind_rows_of_this_repo_and_drops_the_unpayable(tmp_path: Path) -> None:
    """Behind and payable is owed; ok, another repo's, and required above the entries are not."""
    (tmp_path / "pay.txt").write_text("# header\n\nx 1\ny 2\n", encoding="utf-8")
    (tmp_path / "one.txt").write_text("only\n", encoding="utf-8")
    rows = [
        ratchet_pace.Row("mtools", "pay.txt", "behind", 0, 1),
        ratchet_pace.Row("mtools", "one.txt", "behind", 0, 6),
        ratchet_pace.Row("mtools", "ok.txt", "ok", 0, 0),
        ratchet_pace.Row("nemik", "pay.txt", "behind", 0, 1),
        ratchet_pace.Row("mtools", ".claude/debtplan.json", "behind", 0, 1),
    ]
    got = ratchet_pace.owed(rows, "mtools", tmp_path)
    kept = [(o.ratchet, o.entries) for o in got]
    assert kept == [("pay.txt", _TWO), (".claude/debtplan.json", None)]


def test_entries_skip_comments_and_blanks_and_are_unknown_for_a_missing_or_json_file(
    tmp_path: Path,
) -> None:
    """A comment and a blank line are no entry; a missing file and a JSON document are unknown."""
    (tmp_path / "f.tsv").write_text("# k\tv\n\na\t1\nb\t2\n", encoding="utf-8")
    assert ratchet_pace.entries_in(tmp_path, "f.tsv") == _TWO
    assert ratchet_pace.entries_in(tmp_path, "missing.txt") is None
    assert ratchet_pace.entries_in(tmp_path, "doc.json") is None
