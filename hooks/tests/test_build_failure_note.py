# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The failure hook appends its report to an open gate card through the queue's own CLI (W830)."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from mikemol.hooks import build_failure

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

INVOCATION = "11111111-2222-3333-4444-555555555555"
FAILED_OUTPUT = (
    f"INFO: Streaming build results to: http://bb:8080/invocation/{INVOCATION}\nFAILED\n"
)
_FAILED = {"tool_name": "Bash", "error": FAILED_OUTPUT}
_PLAIN = {"tool_name": "Bash", "error": "Exit code 1"}
_STATE_FLAG_AT = 1
_STATE_PATH_AT = 2
_TEXT_AT = 4
_OVERLONG = 3


class _Calls:
    """A runner that records every argv it is given and answers like the log reader does."""

    def __init__(self) -> None:
        """Start with no calls."""
        self.argvs: list[list[str]] = []

    def __call__(self, argv: Sequence[str]) -> str | None:
        """Record `argv` and answer with a failures view, or with nothing for the CLI.

        Returns:
            the failures text for the log reader, None for anything else.

        """
        self.argvs.append(list(argv))
        return "FAILED //a:b\n" if "--failures" in argv else None

    def notes(self) -> list[list[str]]:
        """Pick the argvs that were gate-note calls.

        Returns:
            those argvs, in order.

        """
        return [argv for argv in self.argvs if "--gate-note" in argv]


def _repo(tmp_path: Path, *, queue: bool, cli: bool) -> dict[str, str]:
    """Make a project with an optional queue file and an optional reader, named by the env.

    Returns:
        the environment naming the project, the log reader and (if made) the queue reader.

    """
    env = {"CLAUDE_PROJECT_DIR": str(tmp_path)}
    log = tmp_path / "mikemol-buildlog"
    log.write_text("#!/bin/sh\n", encoding="utf-8")
    env[build_failure.BUILDLOG_ENV] = str(log)
    if queue:
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "paths-forward.json").write_text("{}", encoding="utf-8")
    if cli:
        reader = tmp_path / "mikemol-paths-forward"
        reader.write_text("#!/bin/sh\n", encoding="utf-8")
        env[build_failure.PATHSFORWARD_ENV] = str(reader)
    return env


def _run(
    env: dict[str, str], calls: _Calls, record: dict[str, str] | None = None
) -> tuple[int, str]:
    """Run the hook once over `record` (a failed build by default).

    Returns:
        the exit code and what it wrote to stderr.

    """
    err = io.StringIO()
    code = build_failure.run(record or _FAILED, env, calls, err)
    return code, err.getvalue()


def test_a_failed_build_is_noted_on_the_gate_card(tmp_path: Path) -> None:
    """With a queue and a reader, the CLI is called once with the state path and the report."""
    calls = _Calls()
    code, _ = _run(_repo(tmp_path, queue=True, cli=True), calls)
    notes = calls.notes()
    assert code == build_failure.EXIT_FEEDBACK
    assert len(notes) == 1
    assert notes[0][_STATE_FLAG_AT] == "--state"
    assert notes[0][_STATE_PATH_AT] == str(tmp_path / ".claude" / "paths-forward.json")
    assert "FAILED //a:b" in notes[0][_TEXT_AT]


def test_no_queue_means_no_note(tmp_path: Path) -> None:
    """A repo with no paths-forward.json is not written to, and the report still reaches stderr."""
    calls = _Calls()
    code, err = _run(_repo(tmp_path, queue=False, cli=True), calls)
    assert code == build_failure.EXIT_FEEDBACK
    assert not calls.notes()
    assert "FAILED //a:b" in err


def test_no_reader_means_no_note(tmp_path: Path) -> None:
    """A queue with no installed reader is a silent skip, not an error."""
    calls = _Calls()
    code, _ = _run(_repo(tmp_path, queue=True, cli=False), calls)
    assert code == build_failure.EXIT_FEEDBACK
    assert not calls.notes()


def test_a_failure_that_ran_no_build_is_not_noted(tmp_path: Path) -> None:
    """Only a failed build's report is kept: a plain failed command writes nothing."""
    calls = _Calls()
    code, _ = _run(_repo(tmp_path, queue=True, cli=True), calls, _PLAIN)
    assert code == 0
    assert not calls.notes()


def test_the_note_is_bounded(tmp_path: Path) -> None:
    """The evidence rides in every payload naming the card, so a long report is cut."""
    calls = _Calls()
    env = _repo(tmp_path, queue=True, cli=True)
    build_failure.note_gate_card("x" * (build_failure.NOTE_CHARS * _OVERLONG), tmp_path, env, calls)
    assert len(calls.notes()[0][_TEXT_AT]) == build_failure.NOTE_CHARS
