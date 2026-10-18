# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The line --tick-open prints to start the idle watchdog: on PATH, in the checkout, or none."""

import json
from pathlib import Path

import pytest

from mikemol.pathsforward import cli, watchdogcmd

_STATE = Path("/r/.claude/paths-forward.json")
_WRITER = "/w/mikemol-paths-forward"


def _none(_name: str) -> str | None:
    return None


def _checkout_bin(home: Path) -> Path:
    path = home / "github" / "mtools" / "hooks" / ".venv" / "bin"
    path.mkdir(parents=True)
    return path


def test_a_watchdog_on_path_is_used_and_names_the_state_and_the_writer(tmp_path: Path) -> None:
    """The writer that printed the command is the one the watchdog asks."""
    got = watchdogcmd.command(_STATE, _WRITER, tmp_path, lambda _n: "/usr/bin/mikemol-watchdog")
    assert got == f"/usr/bin/mikemol-watchdog --state {_STATE} --writer {_WRITER}"


def test_the_installed_script_in_the_checkout_comes_next(tmp_path: Path) -> None:
    """No PATH entry, but the mtools checkout has the console script."""
    script = _checkout_bin(tmp_path) / "mikemol-watchdog"
    script.write_text("", encoding="utf-8")
    got = watchdogcmd.command(_STATE, _WRITER, tmp_path, _none)
    assert got == f"{script} --state {_STATE} --writer {_WRITER}"


def test_the_checkouts_interpreter_runs_the_module_before_a_venv_is_rebuilt(tmp_path: Path) -> None:
    """The form that works while the console script does not exist yet."""
    python = _checkout_bin(tmp_path) / "python"
    python.write_text("", encoding="utf-8")
    got = watchdogcmd.command(_STATE, _WRITER, tmp_path, _none)
    assert got == f"{python} -m mikemol.hooks.watchdog --state {_STATE} --writer {_WRITER}"


def test_no_watchdog_anywhere_prints_no_command(tmp_path: Path) -> None:
    """A command that cannot run is worse than none."""
    assert watchdogcmd.command(_STATE, _WRITER, tmp_path, _none) is None


def test_the_tick_line_names_the_running_writer_resolved(tmp_path: Path) -> None:
    """The watchdog asks the copy of the writer that printed the line."""
    line = watchdogcmd.tick_line(_STATE, "relative/writer", tmp_path, lambda _n: "/bin/wd")
    assert line.startswith("watchdog: start it in the background: /bin/wd --state ")
    assert str(Path("relative/writer").resolve()) in line


def test_the_tick_line_says_so_when_no_watchdog_is_found(tmp_path: Path) -> None:
    """A missing watchdog shows up in the opening output instead of hiding."""
    line = watchdogcmd.tick_line(_STATE, "w", tmp_path, _none)
    assert line.startswith("watchdog: none found")


def test_tick_open_prints_the_watchdog_line_before_its_closing_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The line a session copies into a background task is part of the opening output."""
    state = tmp_path / "myrepo" / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    root = str(state.parent.parent)
    doc: dict[str, object] = {"counter": 0, "waypoints": [], "project_root": root}
    state.write_text(json.dumps(doc), encoding="utf-8")
    assert cli.main(["--state", str(state), "--tick-open", "tester"]) == 0
    said = capsys.readouterr().out.splitlines()
    assert any(line.startswith("watchdog: ") for line in said)
    assert said[-1].startswith("tick open as tester")
