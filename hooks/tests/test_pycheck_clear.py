# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-pycheck --clear PATH`: format, safe fixes, format, then the verdict.

W1085 (gabion:W1051). ⚑ THE CLEAN FILE IS THE POSITIVE CONTROL: a file the steps leave unchanged is
not rewritten and still gets the verdict, so a rewrite is the steps' doing and not every call's.
The formatter, the fixer and the check are injected; no ruff runs here.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from mikemol.hooks import pycheck_clear, pycheck_cli

if TYPE_CHECKING:
    from pathlib import Path
    from typing import TextIO

    import pytest

_DIRTY = "import b\nimport a\n"
_CLEAN = "import a\nimport b\n"
_REFUSED = 1
_NOT_RUN = 3


class _World:
    """Stand-in steps that record their calls and answer as told."""

    def __init__(self, *, fixes: bool = True, verdict: int = 0, works: bool = True) -> None:
        self.fixes = fixes
        self.verdict = verdict
        self.works = works
        self.checked: list[Path] = []

    def steps(self) -> pycheck_clear.Steps:
        return pycheck_clear.Steps(self._format, self._fix, self._check)

    def _format(self, _path: Path, text: str, _err: TextIO) -> str | None:
        return text if self.works else None

    def _fix(self, _path: Path, text: str, _err: TextIO) -> str | None:
        return _CLEAN if self.fixes and text == _DIRTY else text

    def _check(self, path: Path) -> int:
        self.checked.append(path)
        return self.verdict


def _draft(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "mod.py"
    path.write_text(text, encoding="utf-8")
    return path


def _run(path: Path, world: _World) -> tuple[int, str]:
    out = io.StringIO()
    code = pycheck_clear.clear(path, world.steps(), out, io.StringIO())
    return code, out.getvalue()


def test_a_dirty_file_is_rewritten_and_then_judged(tmp_path: Path) -> None:
    """The safe fix rewrites the file; the check then runs on it and its status is returned."""
    path = _draft(tmp_path, _DIRTY)
    world = _World(verdict=_REFUSED)
    code, out = _run(path, world)
    assert path.read_text(encoding="utf-8") == _CLEAN
    assert "cleared" in out
    assert world.checked == [path]
    assert code == _REFUSED


def test_a_clean_file_is_not_rewritten_but_is_still_judged(tmp_path: Path) -> None:
    """The positive control: nothing to clear, no write, the verdict still comes back."""
    path = _draft(tmp_path, _CLEAN)
    world = _World()
    code, out = _run(path, world)
    assert path.read_text(encoding="utf-8") == _CLEAN
    assert "nothing to clear" in out
    assert (code, world.checked) == (0, [path])


def test_a_step_that_cannot_run_leaves_the_file_and_skips_the_verdict(tmp_path: Path) -> None:
    """No formatter: exit 3, the file untouched, and no verdict claimed over an uncleared file."""
    path = _draft(tmp_path, _DIRTY)
    world = _World(works=False)
    code, _out = _run(path, world)
    assert code == _NOT_RUN
    assert path.read_text(encoding="utf-8") == _DIRTY
    assert not world.checked


def test_an_unreadable_file_is_not_cleared(tmp_path: Path) -> None:
    """A missing path is exit 3, nothing checked."""
    world = _World()
    code, _out = _run(tmp_path / "absent.py", world)
    assert code == _NOT_RUN
    assert not world.checked


def test_the_safe_rules_do_not_include_the_import_deleting_fix() -> None:
    """F401 deletes an import a module re-exports on purpose, so it is never in the safe list."""
    assert "F401" not in pycheck_clear.SAFE_RULES.split(",")


def test_the_flag_takes_exactly_one_path(capsys: pytest.CaptureFixture[str]) -> None:
    """--clear with no path, or two, is the usage message."""
    assert pycheck_cli.main(["--clear"]) == pycheck_cli.EXIT_USAGE
    assert pycheck_cli.main(["--clear", "a", "b"]) == pycheck_cli.EXIT_USAGE
    assert "--clear PATH" in capsys.readouterr().err
