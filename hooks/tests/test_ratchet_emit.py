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
_FLAGGED = (
    "alpha a.json baseline value=1 floor=0 guessed=1\n"
    "alpha b.json baseline value=2 floor=0 sum=5 guessed=0\n"
)


def _no_binary(_name: str) -> None:
    return None


def test_a_census_line_with_a_value_is_read_and_unread_and_comment_lines_are_not() -> None:
    """UNREAD is not 0: a gauge of 0 for a broken baseline would read as debt paid down."""
    found = ratchet_emit.parse_census(_CENSUS)
    assert found == [
        ("alpha", ".claude/debt-ledger.json", "debt", 0, None, None),
        ("alpha", "baselines/ruff-baseline.json", "baseline", _ENTRIES, _SUM, None),
    ]


def test_the_guessed_flag_is_read_when_the_line_says_it_and_is_none_when_it_does_not() -> None:
    """W1958: guessed=1 is the name classifier's, guessed=0 is declared, no flag is unknown."""
    assert ratchet_emit.parse_census(_FLAGGED) == [
        ("alpha", "a.json", "baseline", 1, None, True),
        ("alpha", "b.json", "baseline", 2, 5, False),
    ]


def test_a_row_carries_the_ratchets_own_repo_its_path_and_its_kind() -> None:
    """The repo label is the ratchet's repository, not the repository whose gate ran."""
    census = [("luthen-observability", "exit_baseline.txt", "baseline", _VALUE, None, None)]
    [row] = ratchet_emit.rows_of(census, _NOW)
    assert row["name"] == "mikemol.ratchet.value"
    assert row["value"] == _VALUE
    assert row["time_ns"] == _NOW
    assert row["fields"] == {
        "repo": "luthen-observability",
        "ratchet": "exit_baseline.txt",
        "kind": "baseline",
    }


def test_guessed_is_a_label_only_where_the_census_said_so() -> None:
    """W1958: nemik treats a guessed row as advisory; an unknown flag is not sent as false."""
    census = [
        ("r", "a.json", "baseline", 1, None, True),
        ("r", "b.json", "baseline", 1, None, False),
        ("r", "c.json", "baseline", 1, None, None),
    ]
    rows = ratchet_emit.rows_of(census, _NOW)
    labels = [cast("dict[str, str]", row["fields"]).get("guessed") for row in rows]
    assert labels == ["true", "false", None]


def test_a_stage_is_a_label_only_when_one_is_given() -> None:
    """W2171: the gate's rows keep their labels; a landed run adds `stage=landed` to both series."""
    census = [("nemik", "ruff-baseline.json", "baseline", _ENTRIES, _SUM, None)]
    gate = ratchet_emit.rows_of(census, _NOW)
    landed = ratchet_emit.rows_of(census, _NOW, "landed")
    assert all("stage" not in cast("dict[str, str]", r["fields"]) for r in gate)
    assert [cast("dict[str, str]", r["fields"])["stage"] for r in landed] == ["landed", "landed"]
    assert [r["value"] for r in landed] == [r["value"] for r in gate]


def test_a_file_rule_count_baseline_also_sends_its_sum_and_no_other_does() -> None:
    """W1922: a count falling inside a key leaves the entry count flat; the sum shows it."""
    census = [
        ("nemik", "ruff-baseline.json", "baseline", _ENTRIES, _SUM, None),
        ("nemik", "codon-baseline.json", "baseline", _VALUE, None, None),
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
    census = [("r", f"p{n}", "baseline", n, None, None) for n in range(_MANY)]
    children = ratchet_emit.plan("/bin/otlp", ratchet_emit.rows_of(census, _NOW))
    assert [len(text.splitlines()) for _argv, text in children] == [_FULL, _REST]
    assert children[0][0][:2] == ["/bin/otlp", "metrics"]


def test_no_binary_or_store_sends_nothing_and_a_failed_spawn_is_false(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Best effort: the exit status never depends on the send."""
    rows = ratchet_emit.rows_of([("r", "p", "baseline", 1, None, None)], _NOW)
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


def test_the_tool_is_found_by_env_then_path_and_never_in_a_sibling_checkout(
    tmp_path: Path,
) -> None:
    """W1927: RATCHET_BIN, then PATH; with neither, None even when a checkout path would exist."""
    named = tmp_path / "named" / "mikemol-ratchet"
    named.parent.mkdir()
    named.write_text("", encoding="utf-8")
    on_path = tmp_path / "bin" / "mikemol-ratchet"
    on_path.parent.mkdir()
    on_path.write_text("", encoding="utf-8")
    on_path.chmod(0o755)
    env = {"RATCHET_BIN": str(named), "PATH": str(on_path.parent)}
    assert ratchet_emit.reader_path(env) == str(named)
    assert ratchet_emit.reader_path({"PATH": str(on_path.parent)}) == str(on_path)
    assert ratchet_emit.reader_path({"HOME": str(tmp_path), "PATH": ""}) is None
    assert ratchet_emit.reader_path({"RATCHET_BIN": str(tmp_path / "gone"), "PATH": ""}) is None


def test_main_reads_the_census_and_ships_the_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The census of DIR is read and sent under NAME, never under the directory's basename."""
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

    assert ratchet_emit.main(["mtools", "/snapshot/tree"], spawn, run) == 0
    assert asked == [[str(tool), "census", "--repo", "/snapshot/tree"]]
    first = cast("dict[str, object]", json.loads(sent[0].splitlines()[0]))
    assert first["value"] == 0
    assert cast("dict[str, str]", first["fields"])["repo"] == "mtools"
    assert "3 ratchet(s), sent=3" in capsys.readouterr().out
    assert ratchet_emit.main(["only-one-argument"]) == ratchet_emit.EXIT_USAGE
    sent.clear()
    assert ratchet_emit.main(["mtools", "/snapshot/tree", "landed"], spawn, run) == 0
    landed = cast("dict[str, object]", json.loads(sent[0].splitlines()[0]))
    assert cast("dict[str, str]", landed["fields"])["stage"] == "landed"
    assert ratchet_emit.main(["mtools", "/snapshot/tree", "someday"]) == ratchet_emit.EXIT_USAGE
    assert ratchet_emit.main(["mtools", "/snapshot/tree", "landed", "x"]) == ratchet_emit.EXIT_USAGE


def test_zero_ratchets_never_read_as_sent_and_fail_for_a_directory_that_declares_some(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2018: `0 ratchet(s), sent=True` read as success; now sent is a count and 0 exits 1 there."""
    tool = tmp_path / "mikemol-ratchet"
    tool.write_text("", encoding="utf-8")
    monkeypatch.setenv("RATCHET_BIN", str(tool))
    monkeypatch.setenv("MIKEMOL_OTLP_BIN", "/bin/otlp")
    monkeypatch.setenv("MIKEMOL_ENDPOINTS", "x")
    repo = tmp_path / "repo"
    repo.mkdir()

    def run(_argv: Sequence[str]) -> tuple[int, str]:
        return 0, ""

    def spawn(_argv: Sequence[str], _text: str) -> None:
        return None

    assert ratchet_emit.main(["r", str(repo)], spawn, run) == 0
    assert "0 ratchet(s), sent=0" in capsys.readouterr().out
    (repo / "ratchets.json").write_text("{}", encoding="utf-8")
    assert ratchet_emit.main(["r", str(repo)], spawn, run) == 1
    assert "sent=0" in capsys.readouterr().out
