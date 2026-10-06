# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `pycheck_census`: the gate's verdict counted per file, blindness never zero."""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING

from mikemol.hooks import pycheck_census, pycheck_cli

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.hooks.verdict import Verdict

RUFF_REPORT = "--- ruff ---\nE501 too long\nFound 3 errors.\n"
FORMAT_REPORT = "--- ruff-format ---\n@@ -1,2 +1,2 @@\n-a\n+b\n@@ -9,2 +9,2 @@\n-c\n+d\n"
MYPY_REPORT = "--- mypy ---\nm.py:1: error: bad  [misc]\nm.py:2: error: worse  [misc]\n"
SYNTAX_REPORT = "--- syntax ---\nm.py: error: invalid syntax  [syntax]"
RUFF_COUNT = 3
FORMAT_COUNT = 2
MYPY_COUNT = 2


def _write(root: Path, *names: str) -> None:
    """Create each named file under `root` with one line of Python."""
    for name in names:
        (root / name).write_text("x = 1\n", encoding="utf-8")


def _by_name(content: str, path: str) -> Verdict:
    """Refuse a file named dirty, leave one named blind unjudged, admit the rest.

    Returns:
        the verdict the file's name asks for.

    """
    del content
    if path.endswith("dirty.py"):
        return (False, RUFF_REPORT)
    if path.endswith("blind.py"):
        return (None, "no ruff")
    return (True, "")


def _blind(content: str, path: str) -> Verdict:
    """Judge no file.

    Returns:
        no verdict, whatever the file.

    """
    del content, path
    return (None, "no ruff")


def _admits(content: str, path: str) -> Verdict:
    """Admit every file.

    Returns:
        an admission, whatever the file.

    """
    del content, path
    return (True, "")


def _mypy_on_b(content: str, path: str) -> Verdict:
    """Refuse the file named b with a mypy report and admit the rest.

    Returns:
        the verdict the file's name asks for.

    """
    del content
    return (False, MYPY_REPORT) if path.endswith("b.py") else (True, "")


def test_each_checker_block_is_counted_by_its_own_marker() -> None:
    """Ruff's stated total, one per format hunk, one per mypy error line, one per syntax line."""
    assert pycheck_census.findings(RUFF_REPORT) == RUFF_COUNT
    assert pycheck_census.findings(FORMAT_REPORT) == FORMAT_COUNT
    assert pycheck_census.findings(MYPY_REPORT) == MYPY_COUNT
    assert pycheck_census.findings(SYNTAX_REPORT) == 1
    both = RUFF_REPORT + MYPY_REPORT
    assert pycheck_census.findings(both) == RUFF_COUNT + MYPY_COUNT


def test_a_refusal_with_no_marker_still_counts_one() -> None:
    """A refused file is never debt-free, whatever its report looks like."""
    assert pycheck_census.findings("--- suppression ---\nsomething new") == 1


def test_the_census_counts_refused_files_and_sets_unjudged_apart(tmp_path: Path) -> None:
    """Admitted files are absent, refused ones counted, a file no checker judged is not zero."""
    _write(tmp_path, "clean.py", "dirty.py", "blind.py")
    names = ["clean.py", "dirty.py", "blind.py", "gone.py"]
    debt, unchecked = pycheck_census.census(tmp_path, names, _by_name)
    assert debt == {"dirty.py": RUFF_COUNT}
    assert unchecked == ["blind.py", "gone.py"]


def test_tracked_python_is_none_outside_a_repository(tmp_path: Path) -> None:
    """Git refusing to name files is None, never an empty list that would read as no files."""
    assert pycheck_census.tracked_python(tmp_path) is None


def test_the_cli_census_writes_the_flat_ledger(tmp_path: Path) -> None:
    """With every file judged the ledger is flat JSON on stdout and the exit is zero."""
    _write(tmp_path, "a.py", "b.py")
    out, err = io.StringIO(), io.StringIO()
    code = pycheck_cli.census(tmp_path, lambda _root: ["a.py", "b.py"], _mypy_on_b, out, err)
    expected: dict[str, int] = {"b.py": MYPY_COUNT}
    assert code == pycheck_cli.EXIT_ADMITTED
    assert out.getvalue() == json.dumps(expected, indent=2) + "\n"
    assert not err.getvalue()


def test_the_cli_census_writes_no_ledger_when_any_file_is_unjudged(tmp_path: Path) -> None:
    """Blindness is not a clean ledger: exit three, nothing on stdout, the names on stderr."""
    _write(tmp_path, "a.py")
    out, err = io.StringIO(), io.StringIO()
    code = pycheck_cli.census(tmp_path, lambda _root: ["a.py"], _blind, out, err)
    assert code == pycheck_cli.EXIT_NOT_CHECKED
    assert not out.getvalue()
    assert "a.py" in err.getvalue()


def test_the_cli_census_writes_no_ledger_when_git_cannot_name_the_files(tmp_path: Path) -> None:
    """No file list is no ledger, never an empty one."""
    out, err = io.StringIO(), io.StringIO()
    code = pycheck_cli.census(tmp_path, lambda _root: None, _admits, out, err)
    assert code == pycheck_cli.EXIT_NOT_CHECKED
    assert not out.getvalue()
    assert "no ledger" in err.getvalue()


def test_a_ledger_is_written_whole_under_the_project_claude_directory(tmp_path: Path) -> None:
    """write_ledger creates `.claude/` and replaces an older ledger with the new one."""
    target = tmp_path / ".claude" / "debt-ledger.json"
    pycheck_census.write_ledger(target, {"a.py": 1})
    pycheck_census.write_ledger(target, {"b.py": MYPY_COUNT})
    expected: dict[str, int] = {"b.py": MYPY_COUNT}
    assert target.read_text(encoding="utf-8") == json.dumps(expected, indent=2) + "\n"
    assert [each.name for each in target.parent.iterdir()] == ["debt-ledger.json"]


def test_refresh_writes_the_ledger_the_closure_advisory_reads(tmp_path: Path) -> None:
    """A good measurement is written to `.claude/debt-ledger.json` and the exit is zero."""
    _write(tmp_path, "a.py", "b.py")
    err = io.StringIO()
    code = pycheck_cli.refresh(
        tmp_path,
        lambda _root: ["a.py", "b.py"],
        _mypy_on_b,
        pycheck_census.write_ledger,
        err,
    )
    assert code == pycheck_cli.EXIT_ADMITTED
    expected: dict[str, int] = {"b.py": MYPY_COUNT}
    ledger = tmp_path / ".claude" / "debt-ledger.json"
    assert ledger.read_text(encoding="utf-8") == json.dumps(expected, indent=2) + "\n"


def test_refresh_leaves_the_old_ledger_when_a_file_is_unjudged(tmp_path: Path) -> None:
    """Blindness must not replace a ledger: exit three and the previous one is byte for byte."""
    _write(tmp_path, "a.py")
    ledger = tmp_path / ".claude" / "debt-ledger.json"
    pycheck_census.write_ledger(ledger, {"old.py": 7})
    before = ledger.read_text(encoding="utf-8")
    err = io.StringIO()
    code = pycheck_cli.refresh(
        tmp_path, lambda _root: ["a.py"], _blind, pycheck_census.write_ledger, err
    )
    assert code == pycheck_cli.EXIT_NOT_CHECKED
    assert ledger.read_text(encoding="utf-8") == before


def test_refresh_says_so_when_the_ledger_cannot_be_written(tmp_path: Path) -> None:
    """A target whose parent is a file cannot be staged: exit three, the failure named."""
    _write(tmp_path, "a.py")
    (tmp_path / ".claude").write_text("in the way", encoding="utf-8")
    err = io.StringIO()
    code = pycheck_cli.refresh(
        tmp_path, lambda _root: ["a.py"], _admits, pycheck_census.write_ledger, err
    )
    assert code == pycheck_cli.EXIT_NOT_CHECKED
    assert "old ledger kept" in err.getvalue()
