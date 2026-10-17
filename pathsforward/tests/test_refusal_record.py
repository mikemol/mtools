# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for shipping a REFUSED line as an OTLP record (mtools:W1248).

⚑ THE CONTROLS ARE THE THREE WAYS IT COULD HURT: it ships a value the caller typed (a quoted path
or token), it waits on a slow endpoint, and it changes the refusal the caller reads when shipping
fails. So the record carries shapes only, the child is started and not awaited, and an unstartable
child or an absent URL or binary leaves the exit code and the printed line exactly as they were.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.pathsforward import cli, refusal_record

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_REFUSED = cli.EXIT_REFUSED


def _state(tmp_path: Path) -> Path:
    path = tmp_path / "myrepo" / ".claude" / "paths-forward.json"
    path.parent.mkdir(parents=True)
    doc: dict[str, object] = {"counter": 1, "waypoints": []}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_the_rule_text_drops_the_prefix_and_replaces_every_quoted_value() -> None:
    """A path or token inside quotes never reaches the record; the rule's own words do."""
    said = "REFUSED: W9 is not a card; got 'secret-token' and \"/home/x/y\""
    assert refusal_record.rule_of(said) == "W9 is not a card; got <value> and <value>"


def test_an_unquoted_absolute_path_is_replaced_too() -> None:
    """The first real record carried the whole --state path unquoted; now it is `<path>`."""
    said = "REFUSED: /home/u/repo/.claude/paths-forward.json: [Errno 2] No such file"
    assert refusal_record.rule_of(said) == "<path>: [Errno 2] No such file"


def test_flags_are_names_without_their_values() -> None:
    """The argv shape is the flag names: `--update W1 --next=do it` ships `--update --next`."""
    shape = refusal_record.flags_of(["--update", "W1", "--next=do it", "--status", "ready"])
    assert shape == "--update --next --status"


def test_nothing_starts_without_a_url(tmp_path: Path) -> None:
    """The control: a host with no logs URL set is a silent no-op, whatever binary exists."""
    started: list[str] = []

    def start(argv: object, line: str) -> None:
        del argv
        started.append(line)

    no_url = {refusal_record.BIN_ENV: "/bin/true"}
    assert not refusal_record.emit("REFUSED: x", [], _state(tmp_path), no_url, start)
    assert not started


def test_a_configured_host_starts_the_child_with_shapes_the_repo_and_the_caller(
    tmp_path: Path,
) -> None:
    """The child gets the url, the service, the repo as namespace and the rule on stdin."""
    seen: list[tuple[list[str], str]] = []

    def start(argv: object, line: str) -> None:
        seen.append((list(argv) if isinstance(argv, list) else [], line))

    env = {
        refusal_record.URL_ENV: "http://sink/logs",
        refusal_record.BIN_ENV: "/opt/mikemol-otlp",
        refusal_record.CALLER_ENV: "mtools-tick",
    }
    assert refusal_record.emit("REFUSED: bad 'v'", ["--update", "W1"], _state(tmp_path), env, start)
    argv, line = seen[0]
    assert argv[:2] == ["/opt/mikemol-otlp", "log"]
    assert argv[argv.index("--namespace") + 1] == "myrepo"
    assert argv[argv.index("--url") + 1] == "http://sink/logs"
    assert "flags=--update" in argv
    assert "caller=mtools-tick" in argv
    assert line == "bad <value>"


def test_a_child_that_cannot_start_leaves_the_refusal_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: spawn raising OSError still gives exit 2 and the same printed line."""

    def broken(argv: object, line: str) -> None:
        del argv, line
        raise OSError

    monkeypatch.setenv(refusal_record.URL_ENV, "http://sink/logs")
    monkeypatch.setenv(refusal_record.BIN_ENV, "/opt/mikemol-otlp")
    monkeypatch.setattr(refusal_record, "spawn", broken)
    code = cli.main(["--state", str(_state(tmp_path)), "--update", "W9", "--status", "ready"])
    assert code == _REFUSED
    assert "REFUSED:" in capsys.readouterr().err
