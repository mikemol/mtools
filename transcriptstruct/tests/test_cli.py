# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for stage 6: the CLI refuses what it does not know and prints its denominators.

Every fixture is SYNTHETIC and written into pytest's tmp_path. Real transcript excerpts are held
by substrate's operator and do not enter this tree.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.transcriptstruct.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_USAGE_ERROR = 2


def _user(content: str) -> str:
    """Build a synthetic user line.

    Returns:
        the JSONL line.

    """
    message: dict[str, object] = {"role": "user", "content": content}
    envelope: dict[str, object] = {"type": "user", "message": message}
    return json.dumps(envelope)


def _transcript(tmp_path: Path) -> Path:
    """Write a three-line synthetic transcript: human prose, a reminder, a torn line.

    Returns:
        its path.

    """
    lines = [
        _user("please drain the tier"),
        _user("<system-reminder>drain</system-reminder>"),
        "{torn",
    ]
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _object(line: str) -> dict[str, object]:
    """Parse one printed JSON line as an object.

    Returns:
        the object.

    """
    return cast("dict[str, object]", json.loads(line))


def _run(*argv: str) -> list[str]:
    """Run the CLI and capture what it prints.

    Returns:
        the output lines.

    """
    out = io.StringIO()
    assert main(list(argv), out=out) == 0
    return out.getvalue().splitlines()


def test_an_unknown_flag_is_refused_not_ignored(tmp_path: Path) -> None:
    """A flag the CLI does not know exits 2; it is not silently dropped from the query.

    ⚑ substrate's `_arg` ignored unknown flags, so a mistyped `--timestamps` ran the default
    query and its answer read as the answer to the question actually asked.
    """
    with pytest.raises(SystemExit) as refused:
        main([str(_transcript(tmp_path)), "--timestamps"], out=io.StringIO())
    assert refused.value.code == _USAGE_ERROR


def test_the_bare_invocation_is_the_stats_read(tmp_path: Path) -> None:
    """With no mode, the CLI prints one JSON line of population counts, never a dump."""
    (line,) = _run(str(_transcript(tmp_path)))
    counts = _object(line)
    assert (counts["total"], counts["malformed"]) == (3, 1)


def test_human_search_prints_hits_and_the_denominator_line(tmp_path: Path) -> None:
    """`--human` finds the operator's words, not the reminder, and ends with its n-of-m line."""
    *hits, footer = _run(str(_transcript(tmp_path)), "--human", "drain")
    assert [_object(hit)["line"] for hit in hits] == [1]
    assert footer == "# 1 hit(s) in 2 searched of 3 record(s), 1 malformed"


def test_extract_prints_null_for_a_missing_line(tmp_path: Path) -> None:
    """`--extract` prints every requested line, with null blocks where no record exists."""
    printed = [_object(line) for line in _run(str(_transcript(tmp_path)), "--extract", "1", "9")]
    assert [(entry["line"], entry["blocks"] is None) for entry in printed] == [
        (1, False),
        (9, True),
    ]
