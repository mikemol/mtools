# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `pycheck_cli`: the gate's verdict by hand, and not-checked never reads as clean."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from mikemol.hooks import pycheck_cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from mikemol.hooks.verdict import Verdict

REPORT = "line 3: ruff E501 line-too-long\nline 9: mypy attr-defined"


def _refuses(content: str, path: str) -> Verdict:
    """Judge every file as refused with the full report.

    Returns:
        a refusal carrying REPORT, whatever the file.

    """
    del content, path
    return (False, REPORT)


def _admits(content: str, path: str) -> Verdict:
    """Judge every file as admitted.

    Returns:
        an admission, whatever the file.

    """
    del content, path
    return (True, "")


def _cannot(content: str, path: str) -> Verdict:
    """Render no verdict, as when no checker could run.

    Returns:
        no verdict with a reason, whatever the file.

    """
    del content, path
    return (None, "ruff is absent")


def _governed(path: Path) -> Path | None:
    """Place every file in a project.

    Returns:
        the file's parent, whatever the file.

    """
    return path.parent


def _ungoverned(path: Path) -> Path | None:
    """Place no file in a project.

    Returns:
        None, whatever the file.

    """
    del path
    return None


def _file(tmp_path: Path) -> Path:
    """Write a small Python file.

    Returns:
        its path.

    """
    target = tmp_path / "mod.py"
    target.write_text("x = 1\n", encoding="utf-8")
    return target


def test_a_refused_file_prints_the_whole_report_and_exits_one(tmp_path: Path) -> None:
    """The unclipped report goes to stdout and the exit code is the refusal's."""
    out, err = io.StringIO(), io.StringIO()
    code = pycheck_cli.check(_file(tmp_path), _refuses, _governed, out, err)
    assert code == pycheck_cli.EXIT_REFUSED
    assert REPORT in out.getvalue()
    assert not err.getvalue()


def test_an_admitted_file_says_so_and_exits_zero(tmp_path: Path) -> None:
    """Admission is stated, with the per-file bound, and exits zero."""
    out, err = io.StringIO(), io.StringIO()
    code = pycheck_cli.check(_file(tmp_path), _admits, _governed, out, err)
    assert code == pycheck_cli.EXIT_ADMITTED
    assert "admitted" in out.getvalue()
    assert "this file alone" in out.getvalue()
    assert not err.getvalue()


def test_no_verdict_is_not_checked_and_never_clean(tmp_path: Path) -> None:
    """A checker that could not run exits three and names the reason on stderr."""
    out, err = io.StringIO(), io.StringIO()
    code = pycheck_cli.check(_file(tmp_path), _cannot, _governed, out, err)
    assert code == pycheck_cli.EXIT_NOT_CHECKED
    assert "ruff is absent" in err.getvalue()
    assert not out.getvalue()


def test_a_file_in_no_project_is_not_checked_even_though_analyze_would_admit_it(
    tmp_path: Path,
) -> None:
    """The hook's admit-what-is-not-mine answer must not read as clean to a person asking."""
    out, err = io.StringIO(), io.StringIO()
    code = pycheck_cli.check(_file(tmp_path), _admits, _ungoverned, out, err)
    assert code == pycheck_cli.EXIT_NOT_CHECKED
    assert "no governing project" in err.getvalue()
    assert not out.getvalue()


def test_a_missing_file_is_not_checked(tmp_path: Path) -> None:
    """An unreadable path exits three and says it was not checked."""
    out, err = io.StringIO(), io.StringIO()
    code = pycheck_cli.check(tmp_path / "absent.py", _admits, _governed, out, err)
    assert code == pycheck_cli.EXIT_NOT_CHECKED
    assert "not checked" in err.getvalue()


def test_main_accepts_exactly_the_flag_and_a_path(capsys: pytest.CaptureFixture[str]) -> None:
    """Anything but one flag and its argument is a usage error, exit two, naming both modes."""
    for argv in ([], ["--check-file"], ["PATH"], ["--check-file", "a", "b"], ["--other", "a"]):
        assert pycheck_cli.main(argv) == pycheck_cli.EXIT_USAGE
    usage = capsys.readouterr().err
    assert "--check-file PATH" in usage
    assert "--census ROOT" in usage
