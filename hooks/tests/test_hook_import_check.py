# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the hook import check: an edit that breaks the hooks is named at once (W1584)."""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING

from mikemol.hooks import beat

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

_ERROR = "ImportError: cannot import name 'writeguard'"
_BAD = (1, f"Traceback (most recent call last):\n  File x\n{_ERROR}\n")
_NOT_FOUND = 127
_EXIT_THREE = 3


def _project(tmp_path: Path, *, built: bool = True) -> Path:
    # A project with a git dir and, when built, a stand-in for the built hooks venv's interpreter.
    (tmp_path / ".git").mkdir(parents=True)
    if built:
        python = tmp_path / "bazel-bin" / "hooks" / ".venv" / "bin" / "python3"
        python.parent.mkdir(parents=True)
        python.write_text("", encoding="utf-8")
    return tmp_path


def _edit(tool: str, path: Path) -> dict[str, object]:
    return {"tool_name": tool, "tool_input": {"file_path": str(path)}}


def _probe(monkeypatch: pytest.MonkeyPatch, answer: tuple[int, str]) -> list[Sequence[str]]:
    # Replace the seam with a recorder that answers `answer`; returns the argvs it was asked.
    asked: list[Sequence[str]] = []

    def fake(argv: Sequence[str]) -> tuple[int, str]:
        asked.append(argv)
        return answer

    monkeypatch.setattr(beat, "IMPORT_PROBE", fake)
    return asked


def test_an_edit_or_write_under_hooks_src_or_bin_names_the_file_relative_to_the_project(
    tmp_path: Path,
) -> None:
    """Edit, Write and MultiEdit of a hook source or launcher count; the path is made relative."""
    src = tmp_path / "hooks" / "src" / "mikemol" / "hooks" / "x.py"
    launcher = tmp_path / "hooks" / "bin" / "mikemol-hook-x"
    assert beat.edited_hook(_edit("Edit", src), tmp_path) == "hooks/src/mikemol/hooks/x.py"
    assert beat.edited_hook(_edit("Write", launcher), tmp_path) == "hooks/bin/mikemol-hook-x"
    assert beat.edited_hook(_edit("MultiEdit", src), tmp_path) is not None


def test_any_other_tool_or_file_is_not_a_hook_edit(tmp_path: Path) -> None:
    """A read, a doc, a test, a file outside the project and a payload with no path pass."""
    src = tmp_path / "hooks" / "src" / "mikemol" / "hooks" / "x.py"
    assert beat.edited_hook(_edit("Read", src), tmp_path) is None
    assert beat.edited_hook(_edit("Edit", tmp_path / "docs" / "a.md"), tmp_path) is None
    assert beat.edited_hook(_edit("Edit", tmp_path / "hooks" / "tests" / "t.py"), tmp_path) is None
    assert beat.edited_hook(_edit("Edit", tmp_path.parent / "elsewhere.py"), tmp_path) is None
    assert beat.edited_hook({"tool_name": "Edit"}, tmp_path) is None


def test_a_failing_import_is_named_by_its_last_stderr_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The error line is the answer; the probe imports the entry module with -B and -c."""
    asked = _probe(monkeypatch, _BAD)
    assert beat.import_failure(_project(tmp_path)) == _ERROR
    argv = asked[0]
    assert list(argv[1:]) == ["-B", "-c", f"import {beat.ENTRY_MODULE}"]
    assert argv[0].endswith("hooks/.venv/bin/python3")


def test_a_working_import_or_no_built_venv_is_not_a_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Exit 0 (stderr noise and all) says nothing; with no venv the launcher already says so."""
    _probe(monkeypatch, (0, "Could not find platform dependent libraries\n"))
    assert beat.import_failure(_project(tmp_path / "built")) is None
    asked = _probe(monkeypatch, _BAD)
    assert beat.import_failure(_project(tmp_path / "bare", built=False)) is None
    assert not asked


def test_a_failure_with_no_stderr_still_says_the_exit_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A crash that wrote nothing is not read as success."""
    _probe(monkeypatch, (_EXIT_THREE, ""))
    assert beat.import_failure(_project(tmp_path)) == f"exit {_EXIT_THREE}"


def test_the_message_names_the_file_the_error_and_how_to_restore_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The next call tells the session which file broke the hooks and the one-line recovery."""
    _probe(monkeypatch, _BAD)
    project = _project(tmp_path)
    said = beat.hook_break(_edit("Edit", project / "hooks" / "src" / "x.py"), project)
    assert said is not None
    assert "hooks/src/x.py" in said
    assert "cannot import name 'writeguard'" in said
    assert "git checkout HEAD -- hooks/src/x.py" in said
    assert "fails OPEN" in said


def test_an_edit_elsewhere_never_starts_the_probe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The import costs a process, so it runs only after an edit under hooks/."""
    asked = _probe(monkeypatch, _BAD)
    project = _project(tmp_path)
    assert beat.hook_break(_edit("Edit", project / "docs" / "a.md"), project) is None
    assert not asked


def test_the_hook_prints_the_break_as_context_on_the_call_after_the_edit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """End to end through run(): the JSON context carries the message, and the exit stays 0."""
    _probe(monkeypatch, _BAD)
    project = _project(tmp_path)
    payload = _edit("Edit", project / "hooks" / "src" / "x.py")
    out = io.StringIO()
    env = {beat.PROJECT_ENV: str(project)}
    assert beat.run(io.StringIO(json.dumps(payload)), env, out=out) == 0
    assert "does not import (hooks/src/x.py)" in out.getvalue()


def test_the_real_probe_reports_a_command_exit_and_a_program_that_is_missing() -> None:
    """The seam's real implementation: success, failure and a program that cannot start."""
    assert beat.run_probe(["true"]) == (0, "")
    assert beat.run_probe(["false"]) == (1, "")
    code, text = beat.run_probe(["/nonexistent/program"])
    assert code == _NOT_FOUND
    assert text
