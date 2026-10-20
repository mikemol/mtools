# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The footprint audit compares what a test opens with the inputs its target declares."""

from collections.abc import Sequence
from pathlib import Path

from mikemol.hooks import footprint

_COMMAND = ("python3", "-m", "pytest")


def _openat(path: str, result: str) -> str:
    return f'123 openat(AT_FDCWD, "{path}", O_RDONLY|O_CLOEXEC) = {result}'


def _runner(trace: str, ran: list[Sequence[str]]) -> footprint.Runner:
    def run(argv: Sequence[str], _cwd: Path) -> tuple[int, str]:
        ran.append(argv)
        Path(argv[argv.index("-o") + 1]).write_text(trace, encoding="utf-8")
        return 0, ""

    return run


def test_only_a_successful_open_is_a_read() -> None:
    """A probe that fails with ENOENT opens nothing, and only a descriptor result counts."""
    trace = "\n".join([_openat("/r/a.py", "3"), _openat("/r/b.py", "-1 ENOENT (No such file)")])
    assert footprint.opened(trace) == {"/r/a.py"}


def test_a_path_outside_the_root_or_not_a_file_is_not_a_repo_input(tmp_path: Path) -> None:
    """Only a regular file inside the repo root is named, relative to it."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x", encoding="utf-8")
    seen = {str(tmp_path / "src" / "a.py"), str(tmp_path / "src"), "/etc/hostname"}
    assert footprint.within(seen, tmp_path) == {"src/a.py"}


def test_an_undeclared_read_is_missing_and_an_unread_declaration_is_unused() -> None:
    """Both directions are findings, the omitted file first."""
    got = footprint.findings(["a.py", "c.py"], ["a.py", "b.py"])
    assert got == ["MISSING b.py", "UNUSED c.py"]


def test_a_declaration_matching_the_trace_has_no_finding() -> None:
    """The audit is clean only when the two sets are equal."""
    assert footprint.findings(["a.py"], ["a.py"]) == []


def test_the_command_runs_under_strace_following_children_and_tracing_opens() -> None:
    """The argv names strace, `-f`, the openat trace and the output file before the command."""
    argv = footprint.trace_argv(Path("/t/out"), _COMMAND)
    assert argv == ["strace", "-f", "-e", "trace=openat", "-o", "/t/out", *_COMMAND]


def test_a_host_without_strace_is_degraded_and_runs_nothing(tmp_path: Path) -> None:
    """No trace is not a clean trace: the finding is DEGRADED and no process starts."""
    ran: list[Sequence[str]] = []
    got = footprint.audit(
        _COMMAND, tmp_path, ["a.py"], run=_runner("", ran), which=lambda _name: None
    )
    assert got == [footprint.DEGRADED]
    assert ran == []


def test_an_audit_traces_the_command_and_compares_the_repo_files_it_opened(
    tmp_path: Path,
) -> None:
    """A planted trace of one declared and one undeclared file gives the one MISSING line."""
    for name in ("a.py", "b.py"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    trace = "\n".join(_openat(str(tmp_path / n), "3") for n in ("a.py", "b.py"))
    ran: list[Sequence[str]] = []
    got = footprint.audit(
        _COMMAND, tmp_path, ["a.py"], run=_runner(trace, ran), which=lambda _name: "/usr/bin/strace"
    )
    assert got == ["MISSING b.py"]
    assert len(ran) == 1
