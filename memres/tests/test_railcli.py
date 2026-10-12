# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-rail`: its options, its refusals, the textfile write and the real effects it wires.

W1034. ⚑ A LIVE RUN NEEDS THE FENCE, AND THE REFUSAL IS CHECKED BESIDE THE RUN THAT DOES NOT: the
dry run with no fence on the path must succeed, or "refuse when the fence is absent" would pass for
a CLI that refuses everything.
"""

import time
from pathlib import Path

import pytest

from mikemol.memres import railcli, railloop
from mikemol.memres.rail import Rail
from mikemol.memres.railcli import Options
from mikemol.memres.railloop import Plan, Seams

_EXECUTABLE = 0o755
_BASE = ["--cell-mb", "2048", "--ceiling", "24"]
_RAIL = Rail(2048.0, 0.0, 10.0, 24)
_FENCE_EXIT = 3
_ROUNDS = 7
_TIMEOUT_S = 0.2


def _fence_on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    """Put a `mikemol-membudget` running `body` alone on the PATH."""
    script = tmp_path / "mikemol-membudget"
    script.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    script.chmod(_EXECUTABLE)
    monkeypatch.setenv("PATH", str(tmp_path))


def _quiet(_text: str) -> None:
    """Take published metrics and drop them."""


def test_the_minimum_flags_give_the_defaults() -> None:
    """A cell size and a ceiling are enough: floor 1, no reserve, ten seconds ahead, stdout."""
    options = railcli.parse(_BASE)
    assert options == Options(Plan(_RAIL), None, dry_run=False)
    assert options.plan.interval_s == pytest.approx(railloop.DEFAULT_INTERVAL_S)
    assert options.plan.rounds is None


def test_every_flag_is_read_into_the_plan(tmp_path: Path) -> None:
    """Each option lands in its own field."""
    target = tmp_path / "rail.prom"
    argv = [*_BASE, "--floor", "2", "--reserve-mb", "4096", "--horizon-s", "30"]
    argv += ["--swap-weight", "0.5", "--interval-s", "1.5", "--rounds", str(_ROUNDS)]
    argv += ["--textfile", str(target), "--dry-run"]
    options = railcli.parse(argv)
    assert options.plan.limits == Rail(2048.0, 4096.0, 30.0, 24, 2)
    assert options.plan.swap_weight == pytest.approx(0.5)
    assert options.plan.interval_s == pytest.approx(1.5)
    assert options.plan.rounds == _ROUNDS
    assert options.textfile == target
    assert options.dry_run


def test_a_missing_required_flag_is_an_argparse_usage_error() -> None:
    """No ceiling is exit 2 from argparse, not a default."""
    with pytest.raises(SystemExit) as stopped:
        railcli.parse(["--cell-mb", "2048"])
    assert stopped.value.code == railcli.EXIT_USAGE


def test_a_rail_that_cannot_exist_is_refused_with_its_reason(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A ceiling of 0 sits below the floor of 1."""
    assert railcli.main(["--cell-mb", "2048", "--ceiling", "0", "--dry-run"]) == railcli.EXIT_USAGE
    assert "below floor" in capsys.readouterr().err


def test_a_live_run_with_no_fence_on_the_path_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The refusal names `--dry-run` as the way to run without the fence."""
    monkeypatch.setenv("PATH", str(tmp_path))
    assert railcli.main(_BASE) == railcli.EXIT_USAGE
    assert "--dry-run" in capsys.readouterr().err


def test_a_dry_run_needs_no_fence_and_publishes_to_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control for the refusal above: with --dry-run and the real meminfo, one round runs."""
    monkeypatch.setenv("PATH", str(tmp_path))
    assert railcli.main([*_BASE, "--dry-run", "--rounds", "1"]) == 0
    assert "mikemol_rail_allowance_cells" in capsys.readouterr().out


def test_interrupting_the_loop_ends_it_cleanly() -> None:
    """Ctrl-C during the sleep is exit 0, not a traceback."""

    def interrupted(_seconds: float) -> None:
        raise KeyboardInterrupt

    seams = Seams(lambda: "", lambda: 0.0, interrupted, _quiet)
    assert railcli.main([*_BASE, "--dry-run"], seams) == 0


def test_the_textfile_replaces_the_old_one_and_leaves_nothing_behind(tmp_path: Path) -> None:
    """The write is a rename over the target, so no temporary file remains and old text is gone."""
    target = tmp_path / "rail.prom"
    target.write_text("old", encoding="utf-8")
    railcli.write_textfile(target, "new")
    assert target.read_text(encoding="utf-8") == "new"
    assert [p.name for p in tmp_path.iterdir()] == ["rail.prom"]


def test_the_fence_runner_returns_the_programs_exit_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Whatever the fence exits with is what the loop sees."""
    _fence_on_path(tmp_path, monkeypatch, f"exit {_FENCE_EXIT}")
    assert railcli.run_fence([railcli.FENCE, "init"]) == _FENCE_EXIT


def test_the_fence_runner_says_127_when_the_program_is_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No program on the path is a status, not an exception."""
    monkeypatch.setenv("PATH", str(tmp_path))
    assert railcli.run_fence([railcli.FENCE, "init"]) == railcli.EXIT_NOT_FOUND


def test_a_fence_that_runs_too_long_is_stopped_with_124(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A wedged resize cannot hold the sampler."""
    _fence_on_path(tmp_path, monkeypatch, "while :; do :; done")
    monkeypatch.setattr(railcli, "_RUN_TIMEOUT_S", _TIMEOUT_S)
    assert railcli.run_fence([railcli.FENCE, "init"]) == railcli.EXIT_TIMED_OUT


def test_the_real_seams_read_a_file_publish_to_a_file_and_run_the_fence(tmp_path: Path) -> None:
    """Meminfo from the given path, the textfile when named, the fence runner unless dry."""
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemAvailable: 1 kB\n", encoding="utf-8")
    target = tmp_path / "rail.prom"
    live = railcli.default_seams(Options(Plan(_RAIL), target, dry_run=False), meminfo)
    assert live.read() == "MemAvailable: 1 kB\n"
    live.write("published")
    assert target.read_text(encoding="utf-8") == "published"
    assert live.runner is railcli.run_fence
    assert live.clock is time.monotonic
    assert live.sleep is time.sleep


def test_an_unreadable_meminfo_reads_as_nothing_and_a_dry_run_has_no_runner(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The loop skips an empty round; a dry run publishes to stdout and never resizes."""
    dry = railcli.default_seams(Options(Plan(_RAIL), None, dry_run=True), tmp_path / "absent")
    assert not dry.read()
    assert dry.runner is None
    dry.write("to stdout")
    assert capsys.readouterr().out == "to stdout"
