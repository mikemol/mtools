# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for stage 10: the rulings query returns the operator's words, newest first (W1387).

⚑ THE CONTROLS ARE THE ORDER AND THE EMPTY ANSWERS: the latest ruling comes first (a later word
supersedes an earlier one), a pattern that matches nothing and a ledger that does not exist are
both an empty list rather than an error, and the match is case-insensitive over the whole needle.
Every fixture is SYNTHETIC.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.transcriptstruct.rulingq import rulings

if TYPE_CHECKING:
    from pathlib import Path


_BOTH = 2


def _entity(uuid: str, said: str, needle: str, line: int = 1) -> str:
    entity: dict[str, object] = {
        "@id": f"file:///t.jsonl#{uuid}",
        "prov:generatedAtTime": {"@value": said, "@type": "xsd:dateTime"},
        "mtools:line": line,
        "mtools:session": "s",
        "mtools:needle": needle,
    }
    return json.dumps(entity)


def _ledger(tmp_path: Path) -> Path:
    path = tmp_path / "rulings.jsonl"
    path.write_text(
        "\n".join(
            [
                _entity("old", "2026-10-01T10:00:00.000Z", "Freeze gabion for now"),
                _entity(
                    "new", "2026-10-16T10:00:00.000Z", "Unfreeze gabion after the priority repos"
                ),
                _entity("other", "2026-10-10T10:00:00.000Z", "Atomize W1386 into steps"),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_a_line_separator_inside_a_needle_does_not_split_its_ledger_line(tmp_path: Path) -> None:
    """A raw line separator in the operator's words is one ruling, not a crash on half (W1864).

    The control is the line after it, which still reads.
    """
    needle = f"split{chr(0x2028)}here and{chr(0x85)}there"
    entity: dict[str, object] = {
        "@id": "file:///t.jsonl#odd",
        "prov:generatedAtTime": {"@value": "2026-10-01T10:00:00.000Z", "@type": "xsd:dateTime"},
        "mtools:line": 1,
        "mtools:session": "s",
        "mtools:needle": needle,
    }
    path = tmp_path / "rulings.jsonl"
    path.write_text(
        json.dumps(entity, ensure_ascii=False)
        + "\n"
        + _entity("next", "2026-10-02T10:00:00.000Z", "after it")
        + "\n",
        encoding="utf-8",
    )
    assert [r.iri.rsplit("#", 1)[1] for r in rulings(path, "here")] == ["odd"]
    assert [r.iri.rsplit("#", 1)[1] for r in rulings(path, "after")] == ["next"]


def test_matching_rulings_come_newest_first_with_their_citation(tmp_path: Path) -> None:
    """The later word leads; each carries the IRI a warrant cites and its line."""
    got = rulings(_ledger(tmp_path), "gabion")
    assert [r.iri.rsplit("#", 1)[1] for r in got] == ["new", "old"]
    assert got[0].said_at == "2026-10-16T10:00:00.000Z"
    assert got[0].line == 1


def test_the_match_is_case_insensitive_over_the_needle_and_a_card_symbol_works(
    tmp_path: Path,
) -> None:
    """`FREEZE` finds the lowercase text; a card symbol is just a pattern."""
    ledger = _ledger(tmp_path)
    assert len(rulings(ledger, "FREEZE")) == _BOTH
    assert [r.needle for r in rulings(ledger, "W1386")] == ["Atomize W1386 into steps"]


def test_a_limit_keeps_the_newest_and_nothing_matching_is_empty_not_an_error(
    tmp_path: Path,
) -> None:
    """The limit cuts the oldest; an unmatched pattern and an absent ledger are empty lists."""
    ledger = _ledger(tmp_path)
    assert [r.iri.rsplit("#", 1)[1] for r in rulings(ledger, "gabion", limit=1)] == ["new"]
    assert rulings(ledger, "no such topic") == []
    assert rulings(tmp_path / "absent.jsonl", "gabion") == []
