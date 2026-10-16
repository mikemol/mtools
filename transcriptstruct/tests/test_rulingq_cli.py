# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--rulings REGEX` on the command line: newest first, whole, with a count (W1387).

⚑ THE CONTROL IS THE EMPTY ANSWER: a pattern that matches nothing prints only the `#` line saying
zero, exit 0, so "no ruling touches this" is a finding the caller can read. Every fixture is
SYNTHETIC.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, cast

from mikemol.transcriptstruct.cli import main

if TYPE_CHECKING:
    from pathlib import Path


_LINE = 7


def _entity(uuid: str, said: str, needle: str) -> str:
    entity: dict[str, object] = {
        "@id": f"file:///t.jsonl#{uuid}",
        "prov:generatedAtTime": {"@value": said, "@type": "xsd:dateTime"},
        "mtools:line": _LINE,
        "mtools:session": "s",
        "mtools:needle": needle,
    }
    return json.dumps(entity)


def _ledger(tmp_path: Path) -> Path:
    path = tmp_path / "rulings.jsonl"
    path.write_text(
        _entity("a", "2026-10-01T10:00:00.000Z", "freeze it")
        + "\n"
        + _entity("b", "2026-10-16T10:00:00.000Z", "unfreeze it")
        + "\n",
        encoding="utf-8",
    )
    return path


def test_the_cli_prints_matching_rulings_newest_first_then_the_count(tmp_path: Path) -> None:
    """Two JSON lines, the later first, each with its citation, then the `#` count."""
    out = io.StringIO()
    assert main([str(_ledger(tmp_path)), "--rulings", "freeze"], out) == 0
    lines = out.getvalue().splitlines()
    first = cast("dict[str, object]", json.loads(lines[0]))
    assert first["needle"] == "unfreeze it"
    assert str(first["iri"]).endswith("#b")
    assert first["line"] == _LINE
    assert lines[-1] == "# 2 ruling(s) match"


def test_limit_keeps_the_newest_and_a_pattern_that_matches_nothing_prints_only_the_count(
    tmp_path: Path,
) -> None:
    """`--limit 1` keeps the later ruling; an unmatched pattern is exit 0 with a zero count."""
    ledger = str(_ledger(tmp_path))
    limited = io.StringIO()
    assert main([ledger, "--rulings", "freeze", "--limit", "1"], limited) == 0
    assert limited.getvalue().splitlines()[-1] == "# 1 ruling(s) match"
    empty = io.StringIO()
    assert main([ledger, "--rulings", "no such topic"], empty) == 0
    assert empty.getvalue() == "# 0 ruling(s) match\n"
