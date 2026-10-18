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
_ID_LENGTH = 12


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
    assert f"rule={refusal_record.rule_id("REFUSED: bad 'v'")}" in argv
    assert line == "bad <value>"


def test_one_rule_keeps_one_id_whatever_values_it_quotes_and_another_rule_differs() -> None:
    """The id groups refusals by rule: quoted values do not change it, different words do."""
    first = refusal_record.rule_id("REFUSED: W9 is not a card; got 'a'")
    again = refusal_record.rule_id("REFUSED: W9 is not a card; got 'other'")
    other = refusal_record.rule_id("REFUSED: title is too long")
    assert first == again
    assert first != other
    assert len(first) == _ID_LENGTH


def test_with_only_the_endpoints_file_set_the_child_starts_without_a_url(tmp_path: Path) -> None:
    """Luthen's route: MIKEMOL_ENDPOINTS alone configures it, and no address is passed on argv."""
    seen: list[list[str]] = []

    def start(argv: object, line: str) -> None:
        del line
        seen.append(list(argv) if isinstance(argv, list) else [])

    env = {refusal_record.ENDPOINTS_ENV: "/host/endpoints.json", refusal_record.BIN_ENV: "/o/bin"}
    assert refusal_record.emit("REFUSED: x", [], _state(tmp_path), env, start)
    assert "--url" not in seen[0]


def test_the_hosts_file_under_home_configures_it_when_the_variable_is_unset(tmp_path: Path) -> None:
    """W1529: a session with no MIKEMOL_ENDPOINTS still ships when the host's file is under HOME."""
    seen: list[list[str]] = []

    def start(argv: object, line: str) -> None:
        del line
        seen.append(list(argv) if isinstance(argv, list) else [])

    home = tmp_path / "home"
    (home / refusal_record.HOME_FILE).parent.mkdir(parents=True)
    (home / refusal_record.HOME_FILE).write_text("{}", encoding="utf-8")
    env = {"HOME": str(home), refusal_record.BIN_ENV: "/o/bin"}
    assert refusal_record.emit("REFUSED: x", [], _state(tmp_path), env, start)
    assert "--url" not in seen[0]


def test_a_home_without_the_hosts_file_and_no_variable_ships_nothing(tmp_path: Path) -> None:
    """W1529: the negative control: HOME alone, with no file under it, is a silent no-op."""
    started: list[str] = []

    def start(argv: object, line: str) -> None:
        del argv
        started.append(line)

    env = {"HOME": str(tmp_path), refusal_record.BIN_ENV: "/o/bin"}
    assert not refusal_record.emit("REFUSED: x", [], _state(tmp_path), env, start)
    assert not started


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


def test_an_accepted_call_ships_the_same_shape_with_verdict_accepted_and_no_rule(
    tmp_path: Path,
) -> None:
    """The record pairs with a refusal: same fields, INFO, empty rule, the caller from the env."""
    seen: list[tuple[list[str], str]] = []

    def start(argv: object, line: str) -> None:
        seen.append((list(argv) if isinstance(argv, list) else [], line))

    env = {
        refusal_record.URL_ENV: "http://sink/logs",
        refusal_record.BIN_ENV: "/opt/mikemol-otlp",
        refusal_record.CALLER_ENV: "mtools-tick",
    }
    assert refusal_record.emit_accepted(
        "tick_open", ["--tick-open", "h"], _state(tmp_path), env, start
    )
    argv, line = seen[0]
    assert argv[argv.index("--severity") + 1] == "INFO"
    assert "verdict=ACCEPTED" in argv
    assert "rule=" in argv
    assert "flags=--tick-open" in argv
    assert "caller=mtools-tick" in argv
    assert line == "accepted --tick-open"


def test_the_caller_falls_back_to_the_parent_command_and_repo_never_a_pid() -> None:
    """With no MIKEMOL_CALLER: `<parent comm>@<repo>`, and the explicit value wins when set."""
    explicit = refusal_record.caller_of({refusal_record.CALLER_ENV: "me"}, "repo")
    assert explicit == "me"
    fallback = refusal_record.caller_of({}, "repo")
    assert fallback.endswith("@repo") or not fallback
    assert not any(part.isdigit() for part in fallback.split("@"))


def test_a_successful_invocation_ships_one_accepted_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The writer's own success path emits ACCEPTED; a failure of the child changes nothing."""
    lines: list[str] = []

    def spawned(argv: object, line: str) -> None:
        del argv
        lines.append(line)

    monkeypatch.setenv(refusal_record.URL_ENV, "http://sink/logs")
    monkeypatch.setenv(refusal_record.BIN_ENV, "/opt/mikemol-otlp")
    monkeypatch.setattr(refusal_record, "spawn", spawned)
    assert cli.main(["--state", str(_state(tmp_path)), "--hash"]) == 0
    assert lines == ["accepted --hash"]
