# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Extra mypy flags override a project's config for the mypy run only (W1537)."""

from pathlib import Path

from mikemol.hooks import checkers, pycheck

_SOURCE = '"""Doc."""\n'
_FLAGS = ("--strict", "--disallow-any-expr")
_ARGV = ["py", "-m", "mypy", "--config-file", "c", "--pretty", "--shadow-file", "a", "b", "a"]
_SUBJECT = 4


def _dist(tmp_path: Path) -> tuple[Path, Path]:
    """Build a project whose interpreter logs every argv it is given.

    Returns:
        the project directory and the log the interpreter appends to.

    """
    dist = tmp_path / "dist"
    (dist / "src").mkdir(parents=True)
    (dist / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    log = tmp_path / "log"
    py = dist / ".venv" / "bin" / "python3"
    py.parent.mkdir(parents=True)
    py.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{log}"\nexit 0\n', encoding="utf-8")
    py.chmod(0o755)
    return dist, log


def test_flags_go_after_mypys_own_options_and_before_its_subject() -> None:
    """The subject stays last, so a flag is never read as a file to check."""
    got = checkers.with_flags(list(_ARGV), _FLAGS)
    at = got.index("--pretty")
    assert got[at + 1 : at + 1 + len(_FLAGS)] == list(_FLAGS)
    assert got[-_SUBJECT:] == _ARGV[-_SUBJECT:]


def test_no_flags_leave_the_argv_as_it_was() -> None:
    """The edit gate passes none, and its argv must not change."""
    assert checkers.with_flags(list(_ARGV), ()) == _ARGV


def test_analyze_gives_the_flags_to_mypy_and_to_no_other_checker(tmp_path: Path) -> None:
    """Ruff and ruff-format never see a mypy flag; the mypy run does."""
    dist, log = _dist(tmp_path)
    target = dist / "src" / "mod.py"
    assert pycheck.analyze(_SOURCE, str(target), mypy_flags=_FLAGS) == (True, "")
    lines = log.read_text(encoding="utf-8").splitlines()
    mypy = [line for line in lines if "-m mypy" in line]
    others = [line for line in lines if "-m mypy" not in line]
    assert len(mypy) == 1
    assert all(flag in mypy[0] for flag in _FLAGS)
    assert others
    assert not any(flag in line for line in others for flag in _FLAGS)
