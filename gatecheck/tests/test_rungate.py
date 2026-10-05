# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `rungate`: the budgeted bazel command line, printed and then run (or not)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mikemol.gatecheck import rungate

if TYPE_CHECKING:
    from collections.abc import Sequence

_TARGET = "@paperkit_boundaries//:gate"
_CHILD_EXIT = 3
_GATE_EXIT = 7
_FAILED_BUDGET_EXIT = 2


def _done(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout, "")


class _Calls:
    """Records every command a seam is asked to run, and answers with a fixed result."""

    def __init__(self, result: subprocess.CompletedProcess[str]) -> None:
        self.result = result
        self.seen: list[tuple[list[str], Path]] = []

    def __call__(self, cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        self.seen.append((list(cmd), cwd))
        return self.result


def test_parse_reads_the_target_and_both_flags() -> None:
    """The record holds exactly what the command line said; the flags default to off."""
    assert rungate.parse([_TARGET]) == rungate.GateArgs(_TARGET, keep_going=False, dry_run=False)
    both = rungate.parse([_TARGET, "--keep-going", "--dry-run"])
    assert both == rungate.GateArgs(_TARGET, keep_going=True, dry_run=True)


def test_parse_requires_a_target() -> None:
    """No target is a usage error, not an empty gate."""
    with pytest.raises(SystemExit):
        rungate.parse([])


def test_the_command_line_carries_the_budget_and_the_mutant_config() -> None:
    """The line is the pre-commit hook's: mise, bazel test, the config, the memory bound."""
    args = rungate.GateArgs(_TARGET, keep_going=False, dry_run=False)
    assert rungate.argv_for(args, "4096") == [
        "mise",
        "exec",
        "--",
        "bazel",
        "test",
        _TARGET,
        "--config=mutant",
        "--local_resources=memory=4096",
        "--notest_keep_going",
    ]


def test_keep_going_flips_the_last_flag() -> None:
    """`--keep-going` is the only difference in the line."""
    args = rungate.GateArgs("//:hook", keep_going=True, dry_run=False)
    line = rungate.argv_for(args, "1")
    assert line[-1] == "--keep_going"
    assert "//:hook" in line


def test_capture_output_collects_stdout_as_text(tmp_path: Path) -> None:
    """The real capture seam runs the command in `cwd` and returns its text and status."""
    code = "import pathlib; print(pathlib.Path.cwd().name)"
    proc = rungate.capture_output([sys.executable, "-c", code], tmp_path)
    assert proc.returncode == 0
    assert proc.stdout == tmp_path.name + "\n"


def test_capture_output_reads_a_failing_status_instead_of_raising(tmp_path: Path) -> None:
    """A non-zero exit comes back as the status with its text; nothing raises."""
    code = f"print('said'); raise SystemExit({_CHILD_EXIT})"
    proc = rungate.capture_output([sys.executable, "-c", code], tmp_path)
    assert proc.returncode == _CHILD_EXIT
    assert proc.stdout == "said\n"


def test_run_passthrough_leaves_the_childs_output_uncaptured(tmp_path: Path) -> None:
    """The gate's output goes to the terminal, so the completed process holds none of it."""
    proc = rungate.run_passthrough([sys.executable, "-c", "print('to the terminal')"], tmp_path)
    assert not proc.stdout


def test_run_passthrough_returns_the_commands_exit_code(tmp_path: Path) -> None:
    """The real run seam reports the child's status as the verdict, without raising."""
    code = f"raise SystemExit({_CHILD_EXIT})"
    proc = rungate.run_passthrough([sys.executable, "-c", code], tmp_path)
    assert proc.returncode == _CHILD_EXIT


def test_budget_runs_the_owner_under_the_root_and_strips_its_answer(tmp_path: Path) -> None:
    """The owner is `tools/sweep_budget.py` under the root, run by this interpreter."""
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "sweep_budget.py").write_text("print('  8192  ')\n", encoding="utf-8")
    assert rungate.budget(tmp_path) == "8192"


def test_budget_names_the_command_it_ran(tmp_path: Path) -> None:
    """The seam sees the interpreter, the owner's path, and the root as cwd."""
    calls = _Calls(_done(0, "512\n"))
    assert rungate.budget(tmp_path, calls) == "512"
    assert calls.seen == [([sys.executable, str(tmp_path / "tools" / "sweep_budget.py")], tmp_path)]


def test_a_failing_owner_raises_rather_than_passing_an_empty_budget(tmp_path: Path) -> None:
    """A budget query that fails must not become a gate run with no bound."""
    with pytest.raises(subprocess.CalledProcessError):
        rungate.budget(tmp_path, _Calls(_done(_FAILED_BUDGET_EXIT)))


def test_a_dry_run_prints_the_line_and_runs_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--dry-run` shows budget and command, exits 0, and never calls the run seam."""
    ran = _Calls(_done(_GATE_EXIT))
    code = rungate.main(
        [_TARGET, "--dry-run"], root=tmp_path, capture=_Calls(_done(0, "2048\n")), run=ran
    )
    assert code == 0
    assert not ran.seen
    out = capsys.readouterr().out
    assert "  budget: 2048 MB (tools/sweep_budget.py)\n" in out
    assert f"  mise exec -- bazel test {_TARGET} --config=mutant" in out
    assert "--local_resources=memory=2048 --notest_keep_going\n\n" in out


def test_a_real_run_passes_the_gates_exit_code_through(tmp_path: Path) -> None:
    """The gate runs once, in the root, with the budgeted line, and its code is returned."""
    ran = _Calls(_done(_GATE_EXIT))
    code = rungate.main(
        [_TARGET, "--keep-going"], root=tmp_path, capture=_Calls(_done(0, "64\n")), run=ran
    )
    assert code == _GATE_EXIT
    assert len(ran.seen) == 1
    cmd, cwd = ran.seen[0]
    assert cwd == tmp_path
    assert cmd[-2:] == ["--local_resources=memory=64", "--keep_going"]


def test_main_defaults_to_argv_and_the_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no argument the process argv is parsed and the cwd is the repo root."""
    monkeypatch.setattr(sys, "argv", ["rungate", "//:hook", "--dry-run"])
    monkeypatch.chdir(tmp_path)
    seen = _Calls(_done(0, "1\n"))
    assert rungate.main(capture=seen) == 0
    assert seen.seen[0][1] == Path.cwd()
