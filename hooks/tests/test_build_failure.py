# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `build_failure`: a failed build's cause reaches the model, and a gap is stated."""

from __future__ import annotations

import io
import sys
from typing import TYPE_CHECKING

from mikemol.hooks import build_failure, entry, hook_argv

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    import pytest

FIRST = "11111111-2222-3333-4444-555555555555"
SECOND = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
FAILED_OUTPUT = (
    f"INFO: Streaming build results to: http://bb:8080/invocation/{FIRST}\n"
    f"INFO: Streaming build results to: http://bb:8080/invocation/{SECOND}\n"
    f"INFO: Streaming build results to: http://bb:8080/invocation/{SECOND}\n"
    "FAILED\n"
)
CAUSE = "hooks/tests/test_x.py:11: resolves out of the runfiles tree\n"


def _reader(stdout_by_flag: dict[str, str | None]) -> Callable[[Sequence[str]], str | None]:
    """Build a log-reader stand-in that answers by the flag it was given.

    Returns:
        a runner; `argv[2]` is the flag, and the answer is `stdout_by_flag[flag]`.

    """

    def run(argv: Sequence[str]) -> str | None:
        return stdout_by_flag.get(argv[2])

    return run


def _tool(tmp_path: Path) -> dict[str, str]:
    """Make a reader file and name it as the env override does.

    Returns:
        the environment naming it.

    """
    binary = tmp_path / "mikemol-buildlog"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    return {build_failure.BUILDLOG_ENV: str(binary), "CLAUDE_PROJECT_DIR": str(tmp_path)}


def test_invocation_ids_are_each_listed_once_in_order() -> None:
    """The ids bazel printed, deduplicated, first appearance first; none when there are none."""
    assert build_failure.invocation_ids(FAILED_OUTPUT) == [FIRST, SECOND]
    assert build_failure.invocation_ids("no build ran here") == []


def test_the_report_reads_the_last_invocation_failures_view(tmp_path: Path) -> None:
    """The last id is the failed build; its failures text is the body, headed by the id."""
    env = _tool(tmp_path)
    report = build_failure.report_for(FAILED_OUTPUT, tmp_path, env, _reader({"--failures": CAUSE}))
    assert report is not None
    assert SECOND in report
    assert CAUSE in report
    assert FIRST not in report


def test_a_log_with_no_failure_blocks_falls_back_to_its_tail(tmp_path: Path) -> None:
    """An empty failures view is never reported as an empty section: the tail stands in."""
    env = _tool(tmp_path)
    reader = _reader({"--failures": "", "--tail": "last lines\n"})
    report = build_failure.report_for(FAILED_OUTPUT, tmp_path, env, reader)
    assert report is not None
    assert "last lines" in report


def test_an_unreadable_log_and_a_missing_reader_are_stated_with_the_command(
    tmp_path: Path,
) -> None:
    """Both gaps still name the id and the command to run, so neither reads as no cause."""
    env = _tool(tmp_path)
    unreadable = build_failure.report_for(FAILED_OUTPUT, tmp_path, env, _reader({}))
    assert unreadable is not None
    assert "could not be read" in unreadable
    assert f"mikemol-buildlog {SECOND}" in unreadable
    missing = build_failure.report_for(FAILED_OUTPUT, tmp_path, {}, _reader({}))
    assert missing is not None
    assert "not found" in missing
    assert f"mikemol-buildlog {SECOND}" in missing


def test_a_long_report_is_truncated_and_says_how_to_read_the_rest() -> None:
    """Past MAX_CHARS the head is kept and the full command is named."""
    long = "x" * (build_failure.MAX_CHARS + 50)
    clipped = build_failure.bounded(long, f"mikemol-buildlog {SECOND}")
    assert clipped.startswith("x" * build_failure.MAX_CHARS)
    assert "x" * (build_failure.MAX_CHARS + 1) not in clipped
    assert "truncated" in clipped
    assert "--all" in clipped
    assert build_failure.bounded("short", "cmd") == "short"


def test_a_failed_build_exits_two_with_the_report_on_stderr(tmp_path: Path) -> None:
    """The report travels on stderr with exit 2, the channel the harness feeds back."""
    err = io.StringIO()
    record = {"tool_name": "Bash", "error": FAILED_OUTPUT}
    code = build_failure.run(record, _tool(tmp_path), _reader({"--failures": CAUSE}), err)
    assert code == build_failure.EXIT_FEEDBACK
    assert CAUSE in err.getvalue()


def test_a_failure_that_ran_no_build_or_another_tool_says_nothing(tmp_path: Path) -> None:
    """No invocation id, or a tool that is not Bash: exit 0 and nothing written."""
    env = _tool(tmp_path)
    for record in (
        {"tool_name": "Bash", "error": "Exit code 1\nplain failure"},
        {"tool_name": "Edit", "error": FAILED_OUTPUT},
        {"tool_name": "Bash"},
    ):
        err = io.StringIO()
        assert build_failure.run(record, env, _reader({"--failures": CAUSE}), err) == 0
        assert not err.getvalue()


def _fake_reader(tmp_path: Path, cause: str) -> Path:
    """Write an executable stand-in for `mikemol-buildlog` that prints `cause` for --failures.

    Returns:
        its path.

    """
    script = tmp_path / "mikemol-buildlog"
    script.write_text(f'#!/bin/sh\nif [ "$2" = "--failures" ]; then printf "%s" "{cause}"; fi\n')
    script.chmod(0o755)
    return script


def test_the_shell_mode_prints_the_cause_of_the_build_on_stdin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The precommit pipes bazel's output in and gets the failing test's cause on stdout, exit 0."""
    reader = _fake_reader(tmp_path, "runfiles refusal")
    monkeypatch.setenv(build_failure.BUILDLOG_ENV, str(reader))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    assert build_failure.report_main([], lambda: FAILED_OUTPUT) == 0
    printed = capsys.readouterr().out
    assert "runfiles refusal" in printed
    assert SECOND in printed


def test_the_shell_mode_prints_nothing_for_output_that_ran_no_build_and_takes_no_arguments(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No invocation id is exit 1 with nothing printed; any argument is a usage error, exit 2."""
    assert build_failure.report_main([], lambda: "make: *** [all] Error 1\n") == 1
    assert not capsys.readouterr().out
    assert build_failure.report_main(["--help"]) == build_failure.EXIT_USAGE
    assert "usage: mikemol-build-failure" in capsys.readouterr().err


def test_main_says_nothing_for_an_unreadable_payload(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Junk on stdin is silence and exit zero: a context hook has nothing to refuse."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert build_failure.main() == 0
    assert not capsys.readouterr().err


def test_the_console_entry_refuses_an_argument_before_reading_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The argv contract: a hook takes no arguments, and the refusal names the program."""
    monkeypatch.setattr(sys, "argv", ["mikemol-hook-build-failure", "--help"])
    assert entry.build_failure_main() == hook_argv.EXIT_REFUSED
    assert "mikemol-hook-build-failure" in capsys.readouterr().err
