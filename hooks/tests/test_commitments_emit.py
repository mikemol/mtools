# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The commitments ledger is shipped as the contract's two gauges, zeros included (W1933)."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from mikemol.hooks import commitments_emit

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

_NOW = 5
_ROWS = 4
_LEDGER = (
    '{"as_of": "2026-10-25T09:00:00Z", "rows": ['
    '{"repo": "mtools", "layer": "none"}, {"repo": "mtools", "layer": "memory"},'
    '{"repo": "mtools", "layer": "gate"}, {"repo": "nemik", "layer": "card"}]}\n'
    "# 2 counted: {}\n"
)


def _values(rows: list[dict[str, object]]) -> dict[str, int]:
    found: dict[str, int] = {}
    for row in rows:
        fields = cast("dict[str, str]", row["fields"])
        key = f"{row['name']}|{fields['repo']}|{fields.get('layer', '')}"
        found[key] = int(str(row["value"]))
    return found


def test_the_document_is_read_and_comment_lines_and_junk_give_nothing_else() -> None:
    """The rows of the first JSON line; a comment, nothing or a broken line gives none."""
    assert len(commitments_emit.ledger_rows(_LEDGER)) == _ROWS
    assert commitments_emit.ledger_rows("# only a comment\n") == []
    assert commitments_emit.ledger_rows("{broken\n") == []
    assert commitments_emit.ledger_rows('{"rows": 3}\n') == []


def test_every_repository_gets_said_and_all_three_counted_layers_with_zeros() -> None:
    """The open gauge for none, memory and instructions; the said gauge counts every row."""
    got = _values(commitments_emit.rows_of(commitments_emit.ledger_rows(_LEDGER), _NOW))
    assert got == {
        "mikemol.commitments.said|mtools|": 3,
        "mikemol.commitments.open|mtools|none": 1,
        "mikemol.commitments.open|mtools|memory": 1,
        "mikemol.commitments.open|mtools|instructions": 0,
        "mikemol.commitments.said|nemik|": 1,
        "mikemol.commitments.open|nemik|none": 0,
        "mikemol.commitments.open|nemik|memory": 0,
        "mikemol.commitments.open|nemik|instructions": 0,
    }


def test_main_ships_under_the_commitments_namespace_and_an_unreadable_ledger_sends_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The namespace reaches the child; best effort, so the exit is 0 either way."""
    monkeypatch.setenv("MIKEMOL_OTLP_BIN", "/bin/otlp")
    monkeypatch.setenv("MIKEMOL_ENDPOINTS", "x")
    ledger = tmp_path / "ledger.txt"
    ledger.write_text(_LEDGER, encoding="utf-8")
    argvs: list[Sequence[str]] = []

    def spawn(argv: Sequence[str], _text: str) -> None:
        argvs.append(argv)

    assert commitments_emit.main([str(ledger)], spawn) == 0
    assert list(argvs[0][-2:]) == ["--namespace", "commitments"]
    assert "8 row(s), sent=True" in capsys.readouterr().out
    argvs.clear()
    assert commitments_emit.main([str(tmp_path / "gone")], spawn) == 0
    assert not argvs
    assert commitments_emit.main([]) == commitments_emit.EXIT_USAGE
