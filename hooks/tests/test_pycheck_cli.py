# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `pycheck_cli`: the gate's verdict by hand, and not-checked never reads as clean."""

from __future__ import annotations

import io
import sys
from typing import TYPE_CHECKING

from mikemol.hooks import (
    project_root,
    pycheck,
    pycheck_clear,
    pycheck_cli,
    pycheck_format,
)
from mikemol.hooks.pycheck_clear import Steps
from mikemol.hooks.pycheck_install import Gate

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


def test_ratchet_with_no_baselines_judges_nothing_and_cannot_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--ratchet ROOT` on a root with no committed baselines is not checked, never clean."""
    cannot_run = 7  # the exit table's CANNOT_RUN, an instrument fault
    assert pycheck_cli.main(["--ratchet", str(tmp_path)]) == cannot_run
    assert "none judged" in capsys.readouterr().err


_CLEARED = 11
_FORMATTED = 12
_LEDGERED = 13


def test_each_rewrite_flag_runs_its_own_rewriter_on_the_resolved_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2203: each rewrite flag reaches its own rewriter, and that rewriter's exit code stands.

    ⚑ The usage tests stop at the argument count, so a dispatch that swapped `--format`,
    `--clear` and `--clear-ledger`, or dropped the target, passed them all.
    """
    calls: list[tuple[str, Path]] = []

    def clear_here(target: Path) -> int:
        calls.append(("clear", target))
        return _CLEARED

    def format_file(target: Path, out: object, err: object) -> int:
        del out, err
        calls.append(("format", target))
        return _FORMATTED

    def clear_ledger(root: Path, names: object, clear: object, out: object, err: object) -> int:
        del names, clear, out, err
        calls.append(("ledger", root))
        return _LEDGERED

    monkeypatch.setattr(pycheck_cli, "_clear_here", clear_here)
    monkeypatch.setattr("mikemol.hooks.pycheck_format.format_file", format_file)
    monkeypatch.setattr("mikemol.hooks.pycheck_clear.clear_ledger", clear_ledger)
    target = tmp_path / "x.py"
    assert pycheck_cli.main(["--clear", str(target)]) == _CLEARED
    assert pycheck_cli.main(["--format", str(target)]) == _FORMATTED
    assert pycheck_cli.main(["--clear-ledger", str(tmp_path)]) == _LEDGERED
    assert calls == [("clear", target), ("format", target), ("ledger", tmp_path)]


def test_check_by_hand_hands_the_real_gate_project_lookup_and_streams_to_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2203: `--check-file` is the gate's `analyze`, the real `project_for`, the real streams."""
    seen: list[tuple[Path, bool, bool, bool, bool]] = []

    def check(path: Path, analyze: object, project_of: object, out: object, err: object) -> int:
        wired = (
            analyze is pycheck.analyze,
            project_of is project_root.project_for,
            out is sys.stdout,
            err is sys.stderr,
        )
        seen.append((path, *wired))
        return _CLEARED

    monkeypatch.setattr(pycheck_cli, "check", check)
    target = tmp_path / "x.py"
    assert pycheck_cli.main(["--check-file", str(target)]) == _CLEARED
    assert seen == [(target, True, True, True, True)]


def test_clear_by_hand_composes_the_real_formatter_fixer_and_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2203: `--clear` hands pycheck_clear the formatter, the safe fixer and the real check."""
    steps_seen: list[Steps] = []
    checked: list[Path] = []

    def clear(path: Path, steps: object, out: object, err: object) -> int:
        del path, out, err
        assert isinstance(steps, Steps)
        steps_seen.append(steps)
        return _CLEARED

    def check(path: Path, analyze: object, project_of: object, out: object, err: object) -> int:
        del analyze, project_of, out, err
        checked.append(path)
        return _LEDGERED

    monkeypatch.setattr("mikemol.hooks.pycheck_clear.clear", clear)
    monkeypatch.setattr(pycheck_cli, "check", check)
    target = tmp_path / "x.py"
    assert pycheck_cli.main(["--clear", str(target)]) == _CLEARED
    (steps,) = steps_seen
    assert steps.format_text is pycheck_format.format_text
    assert steps.fix_text is pycheck_clear.fix_text
    assert steps.check(target) == _LEDGERED
    assert checked == [target]


def test_install_by_hand_resolves_the_draft_and_keeps_the_destination_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2203: the draft is resolved, the destination made absolute, the gate is the real pair."""
    seen: list[tuple[Path, Path, bool, bool]] = []

    def install(src: Path, dest: Path, gate: object, out: object, err: object) -> int:
        del out, err
        assert isinstance(gate, Gate)
        real = (gate.analyze is pycheck.analyze, gate.format_text is pycheck_format.format_text)
        seen.append((src, dest, *real))
        return _CLEARED

    monkeypatch.setattr("mikemol.hooks.pycheck_install.install", install)
    monkeypatch.chdir(tmp_path)
    draft = tmp_path / "draft.py"
    assert pycheck_cli.main([pycheck_cli.INSTALL_FLAG, "draft.py", "out/x.py"]) == _CLEARED
    assert seen == [(draft.resolve(), tmp_path / "out" / "x.py", True, True)]


def test_the_ledger_names_are_the_ledger_keys_sorted_and_no_ledger_clears_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2203: `--clear-ledger` visits the ledger's files sorted; no ledger is not-checked."""
    visited: list[Path] = []

    def clear_here(target: Path) -> int:
        visited.append(target)
        return 0

    monkeypatch.setattr(pycheck_cli, "_clear_here", clear_here)
    assert pycheck_cli.main(["--clear-ledger", str(tmp_path)]) == pycheck_cli.EXIT_NOT_CHECKED
    assert not visited
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "debt-ledger.json").write_text('{"b.py": 2, "a.py": 1}', "utf-8")
    assert pycheck_cli.main(["--clear-ledger", str(tmp_path)]) == 0
    assert visited == [tmp_path / "a.py", tmp_path / "b.py"]
