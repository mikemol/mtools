# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The fleet ratchet census is shipped as one gauge per ratchet per gate run (W1909, W1922)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.hooks import ratchet_emit

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

_NOW = 1_000
_VALUE = 29
_MANY = 150
_FULL = ratchet_emit.CHUNK
_REST = _MANY - ratchet_emit.CHUNK
_ENTRIES = 24
_SUM = 61
_CENSUS = (
    "alpha .claude/debt-ledger.json debt value=0 floor=0\n"
    "alpha baselines/ruff-baseline.json baseline value=24 floor=0 sum=61\n"
    "beta broken-baseline.json baseline value=UNREAD floor=0\n"
    "# 3 ratchet file(s), 1 unread\n"
)


def _no_binary(_name: str) -> None:
    return None


def test_a_census_line_with_a_value_is_read_and_unread_and_comment_lines_are_not() -> None:
    """UNREAD is not 0: a gauge of 0 for a broken baseline would read as debt paid down."""
    found = ratchet_emit.parse_census(_CENSUS)
    assert found == [
        ("alpha", ".claude/debt-ledger.json", "debt", 0, None),
        ("alpha", "baselines/ruff-baseline.json", "baseline", _ENTRIES, _SUM),
    ]


def test_a_row_carries_the_ratchets_own_repo_its_path_and_its_kind() -> None:
    """The repo label is the ratchet's repository, not the repository whose gate ran."""
    census = [("luthen-observability", "exit_baseline.txt", "baseline", _VALUE, None)]
    [row] = ratchet_emit.rows_of(census, _NOW)
    assert row["name"] == "mikemol.ratchet.value"
    assert row["value"] == _VALUE
    assert row["time_ns"] == _NOW
    assert row["fields"] == {
        "repo": "luthen-observability",
        "ratchet": "exit_baseline.txt",
        "kind": "baseline",
    }


def test_a_file_rule_count_baseline_also_sends_its_sum_and_no_other_does() -> None:
    """W1922: a count falling inside a key leaves the entry count flat; the sum shows it."""
    census = [
        ("nemik", "ruff-baseline.json", "baseline", _ENTRIES, _SUM),
        ("nemik", "codon-baseline.json", "baseline", _VALUE, None),
    ]
    rows = ratchet_emit.rows_of(census, _NOW)
    assert [(r["name"], r["value"]) for r in rows] == [
        ("mikemol.ratchet.value", _ENTRIES),
        ("mikemol.ratchet.sum", _SUM),
        ("mikemol.ratchet.value", _VALUE),
    ]
    assert rows[0]["fields"] == rows[1]["fields"]


def test_rows_go_in_chunks_to_one_metrics_child_each() -> None:
    """Each chunk is a `metrics` argv with its JSON lines; more than CHUNK rows make two."""
    census = [("r", f"p{n}", "baseline", n, None) for n in range(_MANY)]
    children = ratchet_emit.plan("/bin/otlp", ratchet_emit.rows_of(census, _NOW))
    assert [len(text.splitlines()) for _argv, text in children] == [_FULL, _REST]
    assert children[0][0][:2] == ["/bin/otlp", "metrics"]


def test_no_binary_or_store_sends_nothing_and_a_failed_spawn_is_false(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Best effort: the exit status never depends on the send."""
    rows = ratchet_emit.rows_of([("r", "p", "baseline", 1, None)], _NOW)
    sent: list[Sequence[str]] = []

    def spawn(argv: Sequence[str], _text: str) -> None:
        sent.append(argv)

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("shutil.which", _no_binary)
    assert ratchet_emit.emit(rows, {}, spawn) is False
    assert not sent
    env = {"MIKEMOL_OTLP_BIN": "/bin/otlp", "MIKEMOL_ENDPOINTS": "x"}
    assert ratchet_emit.emit(rows, env, spawn) is True
    assert sent

    def failing(_argv: Sequence[str], _text: str) -> None:
        raise OSError

    assert ratchet_emit.emit(rows, env, failing) is False


def test_main_reads_the_census_and_ships_the_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The tool named by RATCHET_BIN is asked for `census ROOT`; its values are sent."""
    tool = tmp_path / "mikemol-ratchet"
    tool.write_text("", encoding="utf-8")
    monkeypatch.setenv("RATCHET_BIN", str(tool))
    monkeypatch.setenv("MIKEMOL_OTLP_BIN", "/bin/otlp")
    monkeypatch.setenv("MIKEMOL_ENDPOINTS", "x")
    asked: list[Sequence[str]] = []
    sent: list[str] = []

    def run(argv: Sequence[str]) -> tuple[int, str]:
        asked.append(argv)
        return 0, _CENSUS

    def spawn(_argv: Sequence[str], text: str) -> None:
        sent.append(text)

    assert ratchet_emit.main(["/root"], spawn, run) == 0
    assert asked == [[str(tool), "census", "/root"]]
    first = cast("dict[str, object]", json.loads(sent[0].splitlines()[0]))
    assert first["value"] == 0
    assert "3 ratchet(s), sent=True" in capsys.readouterr().out
    assert ratchet_emit.main([]) == ratchet_emit.EXIT_USAGE
