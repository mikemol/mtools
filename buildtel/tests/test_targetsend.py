# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The per-target rows go to the log store through the shared emitter, one call per invocation."""

import json
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from mikemol.buildtel import proc, targetsend

_A = "11111111-1111-1111-1111-111111111111"
_B = "22222222-2222-2222-2222-222222222222"
_TWO = 2
_THREE = 3


def _row(invocation: str, label: str) -> targetsend.Row:
    return {"invocation": invocation, "label": label, "millis": 1000, "complete": True}


def _no_binary(_name: str) -> None:
    return None


class _Recorder:
    def __init__(self, status: int = 0) -> None:
        self.calls: list[tuple[list[str], str]] = []
        self.status = status

    def __call__(self, argv: Sequence[str], body: str) -> int:
        self.calls.append((list(argv), body))
        return self.status


def _rows_file(tmp_path: Path, rows: Sequence[targetsend.Row]) -> Path:
    path = tmp_path / "rows.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def test_rows_are_grouped_by_invocation_in_order_and_a_row_without_one_is_left_out() -> None:
    """One emitter call per bazel invocation, the first-seen invocation first."""
    orphan: targetsend.Row = {"label": "//a:orphan"}
    rows = [_row(_B, "//a:x"), _row(_A, "//a:y"), _row(_B, "//a:z"), orphan]
    groups = targetsend.by_invocation(rows)
    assert list(groups) == [_B, _A]
    assert [r["label"] for r in groups[_B]] == ["//a:x", "//a:z"]


def test_the_call_names_the_service_the_repo_and_the_invocation() -> None:
    """The fields a panel filters on: the invocation id and the kind."""
    argv = targetsend.argv_for("otlp", "mtools", _A)
    assert argv[:_TWO] == ["otlp", "log"]
    assert argv[argv.index("--service") + 1] == targetsend.SERVICE
    assert argv[argv.index("--namespace") + 1] == "mtools"
    assert f"invocation={_A}" in argv
    assert "kind=target-time" in argv


def test_send_gives_each_invocation_its_rows_as_json_lines_on_stdin() -> None:
    """The body is the group's rows, one JSON line each, and the count is the accepted calls."""
    record = _Recorder()
    rows = [_row(_A, "//a:x"), _row(_B, "//a:y"), _row(_A, "//a:z")]
    assert targetsend.send(rows, "mtools", "otlp", record) == _TWO
    body = record.calls[0][1]
    assert len(body.splitlines()) == _TWO
    assert "//a:x" in body
    assert "//a:z" in body
    assert "//a:y" not in body


def test_a_refused_call_is_not_counted_as_sent() -> None:
    """A non-zero status from the emitter means that invocation was not accepted."""
    assert targetsend.send([_row(_A, "//a:x")], "mtools", "otlp", _Recorder(status=1)) == 0


def test_the_command_reports_sent_and_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every invocation accepted: exit 0 and the count on stdout."""
    monkeypatch.setenv(targetsend.BIN_ENV, "otlp")
    path = _rows_file(tmp_path, [_row(_A, "//a:x"), _row(_B, "//a:y")])
    assert targetsend.main([str(path), "mtools"], _Recorder()) == 0
    assert "2 of 2 invocation(s) sent" in capsys.readouterr().out


def test_an_unaccepted_invocation_is_exit_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rows were already printed by targettimes, so a failed send loses nothing."""
    monkeypatch.setenv(targetsend.BIN_ENV, "otlp")
    path = _rows_file(tmp_path, [_row(_A, "//a:x")])
    assert targetsend.main([str(path), "mtools"], _Recorder(status=1)) == targetsend.EXIT_NOT_SENT


def test_no_emitter_anywhere_is_said_and_sends_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no named binary, none on PATH and no checkout, nothing is sent and it is said."""
    monkeypatch.delenv(targetsend.BIN_ENV, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "nobody"))
    monkeypatch.setattr(shutil, "which", _no_binary)
    path = _rows_file(tmp_path, [_row(_A, "//a:x")])
    record = _Recorder()
    assert targetsend.main([str(path), "mtools"], record) == targetsend.EXIT_NOT_SENT
    assert record.calls == []
    assert "no mikemol-otlp found" in capsys.readouterr().err


def test_a_link_and_a_wrong_argument_count_are_usage_errors(tmp_path: Path) -> None:
    """A rows file that is a link is refused as data, as every reader here refuses one."""
    real = _rows_file(tmp_path, [_row(_A, "//a:x")])
    link = tmp_path / "link.jsonl"
    link.symlink_to(real)
    assert targetsend.main([str(link), "mtools"], _Recorder()) == targetsend.EXIT_USAGE
    assert targetsend.main([str(real)], _Recorder()) == targetsend.EXIT_USAGE


def test_feed_puts_the_body_on_a_real_childs_stdin_and_returns_its_status() -> None:
    """The one real child: exit 0 only when stdin held exactly the body."""
    check = "import sys; sys.exit(0 if sys.stdin.read() == 'x' else 3)"
    assert proc.feed([sys.executable, "-c", check], "x") == 0
    assert proc.feed([sys.executable, "-c", check], "y") == _THREE
