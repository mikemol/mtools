# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `pycheck_advise`: the closure advisory after an edit, and nothing else."""

from __future__ import annotations

import io
import sys
from typing import TYPE_CHECKING

from mikemol.hooks import entry, hook_argv, pycheck_advise, pycheck_closure

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

LEDGER = '{"lib/b.py": 12}'
PLAN = '{"rows": [{"file": "app/a.py", "waits_on": ["lib/b.py"]}]}'


def _plans(argv: Sequence[str]) -> str | None:
    """Stand in for the planner: every plan names lib/b.py as app/a.py's unclean import.

    Returns:
        the fixed plan, whatever the argv.

    """
    del argv
    return PLAN


def _project(root: Path) -> Path:
    """Make a project with a ledger, a planner and an app/a.py.

    Returns:
        the path of app/a.py.

    """
    (root / ".claude").mkdir()
    (root / "app").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    (root / pycheck_closure.LEDGER).write_text(LEDGER, encoding="utf-8")
    planner = root / ".venv" / "bin" / pycheck_closure.PLANNER
    planner.parent.mkdir(parents=True)
    planner.write_text("#!/bin/sh\n", encoding="utf-8")
    target = root / "app" / "a.py"
    target.write_text("x = 1\n", encoding="utf-8")
    return target


def _payload(tool: str, path: Path) -> dict[str, object]:
    """Build a PostToolUse payload for an edit of `path`.

    Returns:
        the payload.

    """
    return {"tool_name": tool, "tool_input": {"file_path": str(path)}}


def test_an_edited_python_file_with_unclean_imports_gets_the_advisory(tmp_path: Path) -> None:
    """The context goes out as PostToolUse additionalContext and the exit code is zero."""
    target = _project(tmp_path)
    out = io.StringIO()
    assert pycheck_advise.run(_payload("Edit", target), {}, _plans, out) == 0
    decision = out.getvalue()
    assert '"hookEventName": "PostToolUse"' in decision
    assert "lib/b.py (12)" in decision


def test_anything_but_a_python_edit_says_nothing(tmp_path: Path) -> None:
    """A read, a non-Python file and a missing file are silent."""
    target = _project(tmp_path)
    notes = tmp_path / "notes.md"
    notes.write_text("x\n", encoding="utf-8")
    for record in (
        _payload("Read", target),
        _payload("Edit", notes),
        _payload("Edit", tmp_path / "app" / "gone.py"),
        {"tool_name": "Edit"},
    ):
        out = io.StringIO()
        assert pycheck_advise.run(record, {}, _plans, out) == 0
        assert not out.getvalue()


def test_a_file_in_no_project_says_nothing(tmp_path: Path) -> None:
    """With no governing project upward there is no ledger to read."""
    loose = tmp_path / "loose.py"
    loose.write_text("x = 1\n", encoding="utf-8")
    out = io.StringIO()
    assert pycheck_advise.run(_payload("Write", loose), {}, _plans, out) == 0
    assert not out.getvalue()


def test_main_says_nothing_for_an_unreadable_payload(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A context hook has nothing to refuse, so junk on stdin is silence and exit zero."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert pycheck_advise.main() == 0
    assert not capsys.readouterr().out


def test_the_console_entry_refuses_an_argument_before_reading_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The argv contract: a hook takes no arguments, and the refusal names the program."""
    monkeypatch.setattr(sys, "argv", ["mikemol-hook-pycheck-advise", "--help"])
    assert entry.pycheck_advise_main() == hook_argv.EXIT_REFUSED
    assert "mikemol-hook-pycheck-advise" in capsys.readouterr().err
