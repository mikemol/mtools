# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the guard launcher: the command's status passes through, a trip interrupts (W921).

⚑ THE UNGUARDED RUN IS THE POSITIVE CONTROL: a launcher that changed the command's exit status would
break every commit it wraps. The tripping arm uses a real shell, a real `sleep` beneath it and a
real signal, with the reading replaced by a constant so no store is needed.
"""

from __future__ import annotations

import shutil
import signal
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.fence import guard_cli, triprecord
from mikemol.fence.policy import Spec
from mikemol.fence.watcher import Row

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    import pytest

    from mikemol.fence.guard import Sample

_SH = shutil.which("sh") or "sh"
_EXIT_THREE = 3
_OVER = 9.0
_WAIT_S = 10.0
_TERMINATED = 128 + int(signal.SIGTERM)


def _over(_name: str, _query: str, _environ: Mapping[str, str]) -> Callable[[], Sample]:
    """Stand in for `reading.reader`: a reading that is always over any limit.

    Returns:
        the zero-argument reading.

    """
    return lambda: _OVER


def _quiet(_args: threading.ExceptHookArgs) -> None:
    """Swallow a guard thread's traceback, which a test raises on purpose."""


def test_the_commands_exit_status_passes_through_unguarded() -> None:
    """The positive control: no spec, exit 0 stays 0 and exit 3 stays 3."""
    assert guard_cli.run([_SH, "-c", "exit 0"], [], {}) == 0
    assert guard_cli.run([_SH, "-c", f"exit {_EXIT_THREE}"], [], {}) == _EXIT_THREE


def test_a_command_killed_by_a_signal_is_a_shell_style_status() -> None:
    """A child ended by SIGTERM reads as 128 plus the signal, as a shell reports it."""
    assert guard_cli.exit_status(-int(signal.SIGTERM)) == _TERMINATED
    assert guard_cli.run([_SH, "-c", "kill -TERM $$"], [], {}) == _TERMINATED


def test_the_policy_path_is_the_flag_then_the_environment_then_the_host_default() -> None:
    """Explicitly named paths are flagged as such; the default is not."""
    env = {guard_cli.ENV: "/b.toml"}
    assert guard_cli.policy_path("/a.toml", env) == (Path("/a.toml"), True)
    assert guard_cli.policy_path(None, env) == (Path("/b.toml"), True)
    path, explicit = guard_cli.policy_path(None, {})
    assert (path.name, explicit) == ("guards.toml", False)


def test_parse_wants_a_separator_and_a_command() -> None:
    """`--policy FILE -- CMD` and `-- CMD` are good; anything else is a usage error."""
    assert guard_cli.parse(["--", "x", "y"]) == (None, ["x", "y"])
    assert guard_cli.parse(["--policy", "p.toml", "--", "x"]) == ("p.toml", ["x"])
    bad_forms = [[], ["x"], ["--"], ["--policy", "p.toml", "x"], ["a", "--", "x"]]
    assert [guard_cli.parse(bad) for bad in bad_forms] == [None] * len(bad_forms)


def test_main_reports_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    """No command: exit 2 and the usage line."""
    assert guard_cli.main([]) == guard_cli.EXIT_USAGE
    assert "usage: guard_cli" in capsys.readouterr().err


def test_a_broken_policy_is_loud_and_the_command_still_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A typo must not turn into an outage, and must not read as a guarded run."""
    policy_file = tmp_path / "guards.toml"
    policy_file.write_text('[[guard]]\nname = "x"\n', encoding="utf-8")
    command = [_SH, "-c", f"exit {_EXIT_THREE}"]
    code = guard_cli.main(["--policy", str(policy_file), "--", *command])
    err = capsys.readouterr().err
    assert code == _EXIT_THREE
    assert "UNGUARDED" in err
    assert "missing key 'above'" in err


def test_a_named_policy_that_does_not_exist_is_said_and_the_command_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A misconfiguration is said once; the default location being empty is not."""
    missing = tmp_path / "absent.toml"
    assert guard_cli.main(["--policy", str(missing), "--", _SH, "-c", "exit 0"]) == 0
    assert "does not exist; running unguarded" in capsys.readouterr().err


def test_a_trip_interrupts_the_named_descendant_and_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A shell with a `sleep` child, a constant over-limit reading: the sleep is interrupted."""
    monkeypatch.setattr(guard_cli, "reader", _over)
    row = Row("t", above=1.0, hold=2, interval_s=0.01, signal=int(signal.SIGTERM), target="sleep")
    marker = tmp_path / "child.pid"
    script = f"sleep 30 & echo $! > {marker}; wait"
    started = time.monotonic()
    code = guard_cli.run([_SH, "-c", script], [Spec(row, "ep", "q")], {})
    assert time.monotonic() - started < _WAIT_S
    assert code == 0
    assert "guard t: TRIPPED" in capsys.readouterr().err


def test_a_freeze_row_reports_each_freeze_and_resume_and_not_a_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2358: a reading that never clears freezes the tree, hits the cap and resumes it, saying so.

    ⚑ THE SIGNAL LINE IS NOT PRINTED FOR A FREEZE: it would read "signalled nothing" for a row that
    stopped and resumed real processes.
    """
    monkeypatch.setattr(guard_cli, "reader", _over)
    row = Row(
        "t",
        above=1.0,
        hold=1,
        interval_s=0.01,
        signal=int(signal.SIGTERM),
        target="sleep",
        action="freeze",
        resume_hold=2,
        max_frozen=3,
        on_cap="resume",
    )
    marker = tmp_path / "child.pid"
    script = f"sleep 1 & echo $! > {marker}; wait"
    code = guard_cli.run([_SH, "-c", script], [Spec(row, "ep", "q")], {})
    err = capsys.readouterr().err
    assert code == 0
    assert "guard t: freeze [" in err
    assert "guard t: cap:resume [" in err
    assert "TRIPPED" not in err


def test_a_trip_is_recorded_as_one_line_and_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2359: a signalling guard's trip leaves a `trip` line in the record and a counter."""
    monkeypatch.setattr(guard_cli, "reader", _over)
    row = Row("t", above=1.0, hold=2, interval_s=0.01, signal=int(signal.SIGTERM), target="sleep")
    record = tmp_path / "state" / "events.jsonl"
    script = "sleep 30 & wait"
    environ = {triprecord.ENV: str(record)}
    assert guard_cli.run([_SH, "-c", script], [Spec(row, "ep", "q")], environ) == 0
    assert triprecord.counts(record) == {("t", "trip"): 1}
    counter = triprecord.counter_path(record).read_text(encoding="utf-8")
    assert 'guard="t",event="trip"} 1' in counter


def test_a_freeze_is_recorded_with_its_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2359: a freeze row records the freeze and the cap's resume, and no `trip` of its own."""
    monkeypatch.setattr(guard_cli, "reader", _over)
    row = Row(
        "t",
        above=1.0,
        hold=1,
        interval_s=0.01,
        signal=int(signal.SIGTERM),
        target="sleep",
        action="freeze",
        resume_hold=2,
        max_frozen=3,
        on_cap="resume",
    )
    record = tmp_path / "events.jsonl"
    environ = {triprecord.ENV: str(record)}
    assert guard_cli.run([_SH, "-c", "sleep 1 & wait"], [Spec(row, "ep", "q")], environ) == 0
    kinds = {event for _, event in triprecord.counts(record)}
    assert {"freeze", "cap:resume"} <= kinds
    assert "trip" not in kinds


def test_a_record_that_cannot_be_written_is_said_and_the_status_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2359: a record path under a regular file fails; the command's own status still passes."""
    monkeypatch.setattr(guard_cli, "reader", _over)
    row = Row("t", above=1.0, hold=2, interval_s=0.01, signal=int(signal.SIGTERM), target="sleep")
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    environ = {triprecord.ENV: str(blocker / "events.jsonl")}
    script = f"sleep 30 & wait; exit {_EXIT_THREE}"
    code = guard_cli.run([_SH, "-c", script], [Spec(row, "ep", "q")], environ)
    assert code == _EXIT_THREE
    assert "the trip record" in capsys.readouterr().err


def test_a_freeze_that_happened_before_the_thread_raised_is_still_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """b65 (F): the events gathered before a reading raised are in the record beside the error."""
    calls: list[int] = []
    patience = 5

    def raising(_name: str, _query: str, _environ: Mapping[str, str]) -> Callable[[], Sample]:
        def read() -> Sample:
            calls.append(1)
            if len(calls) > patience:
                message = "boom"
                raise RuntimeError(message)
            return _OVER

        return read

    monkeypatch.setattr(guard_cli, "reader", raising)
    monkeypatch.setattr(threading, "excepthook", _quiet)
    row = Row(
        "t",
        above=1.0,
        hold=1,
        interval_s=0.01,
        signal=int(signal.SIGTERM),
        target="sleep",
        action="freeze",
        resume_hold=2,
        max_frozen=100,
        on_cap="resume",
    )
    record = tmp_path / "events.jsonl"
    environ = {triprecord.ENV: str(record)}
    assert guard_cli.run([_SH, "-c", "sleep 1 & wait"], [Spec(row, "ep", "q")], environ) == 0
    kinds = {event for _, event in triprecord.counts(record)}
    assert {"freeze", "error"} <= kinds


def test_a_guard_thread_that_raises_is_said_and_recorded_not_read_as_quiet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2371: a reading that raises kills the guard thread; the failure is named and recorded."""

    def broken(_name: str, _query: str, _environ: Mapping[str, str]) -> Callable[[], Sample]:
        def read() -> Sample:
            message = "boom"
            raise RuntimeError(message)

        return read

    monkeypatch.setattr(guard_cli, "reader", broken)
    monkeypatch.setattr(threading, "excepthook", _quiet)
    row = Row("t", above=1.0, hold=2, interval_s=0.01, signal=int(signal.SIGTERM), target="sleep")
    record = tmp_path / "events.jsonl"
    environ = {triprecord.ENV: str(record)}
    code = guard_cli.run([_SH, "-c", f"exit {_EXIT_THREE}"], [Spec(row, "ep", "q")], environ)
    assert code == _EXIT_THREE
    assert "guard t: FAILED RuntimeError: boom" in capsys.readouterr().err
    assert triprecord.counts(record) == {("t", "error"): 1}
