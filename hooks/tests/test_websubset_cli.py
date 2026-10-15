# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-websubset` (mtools:W1257): the two modes and their exit statuses.

⚑ THE CONTROLS ARE THE RUNS THAT MUST NOT READ AS CLEAN: a list that cannot be read and a listed
file that is absent exit 2, never 0, and a module with a finding exits 1 beside a clean one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import websubset_cli, websubset_list

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_CLEAN = "def add(a: int, b: int) -> int:\n    return a + b\n"
_DIRTY = "def f(a):\n    return eval(a)\n"
_OK = 0
_SHAPES: tuple[list[str], ...] = ([], ["--census"], ["--bogus", "x"])


def _root(tmp_path: Path, listed: str) -> Path:
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / websubset_list.LIST_NAME).write_text(listed, encoding="utf-8")
    (tmp_path / "clean.py").write_text(_CLEAN, encoding="utf-8")
    (tmp_path / "dirty.py").write_text(_DIRTY, encoding="utf-8")
    return tmp_path


def test_check_file_reports_every_finding_with_its_line_and_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The dirty file has an eval and two missing annotations; the clean file exits 0 silently."""
    root = _root(tmp_path, "")
    dirty = websubset_cli.main(["--check-file", str(root / "dirty.py")])
    assert dirty == websubset_cli.EXIT_FINDINGS
    out = capsys.readouterr().out
    assert "dirty.py:2: eval-exec" in out
    assert "dirty.py:1: unannotated: `f` has no return type" in out
    assert "dirty.py:1: unannotated: parameter `a` of `f` has no type" in out
    assert websubset_cli.main(["--check-file", str(root / "clean.py")]) == _OK
    assert not capsys.readouterr().out


def test_check_file_on_an_unreadable_path_is_a_usage_error_not_a_clean_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An absent file exits 2 and says so on standard error."""
    status = websubset_cli.main(["--check-file", str(tmp_path / "no.py")])
    assert status == websubset_cli.EXIT_USAGE
    assert "cannot read" in capsys.readouterr().err


def test_census_checks_each_listed_module_and_counts_the_findings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A clean list exits 0; adding the dirty module exits 1 with the summary line."""
    root = _root(tmp_path, "clean.py\n")
    assert websubset_cli.main(["--census", str(root)]) == _OK
    assert capsys.readouterr().out == "census: 1 module(s), 0 finding(s)\n"
    (root / "hooks" / websubset_list.LIST_NAME).write_text("clean.py\ndirty.py\n", "utf-8")
    assert websubset_cli.main(["--census", str(root)]) == websubset_cli.EXIT_FINDINGS
    out = capsys.readouterr().out
    assert "dirty.py:2: eval-exec" in out
    assert out.endswith("census: 2 module(s), 3 finding(s)\n")


def test_an_empty_list_is_a_clean_census_and_an_unreadable_one_is_not(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Nothing listed exits 0; a missing list exits 2 and a bad entry exits 2."""
    root = _root(tmp_path, "# nothing yet\n")
    assert websubset_cli.main(["--census", str(root)]) == _OK
    assert capsys.readouterr().out == "census: 0 module(s), 0 finding(s)\n"
    (root / "hooks" / websubset_list.LIST_NAME).write_text("/abs.py\n", encoding="utf-8")
    assert websubset_cli.main(["--census", str(root)]) == websubset_cli.EXIT_USAGE
    assert "not a repo-relative" in capsys.readouterr().err
    (root / "hooks" / websubset_list.LIST_NAME).unlink()
    assert websubset_cli.main(["--census", str(root)]) == websubset_cli.EXIT_USAGE
    assert "cannot be read" in capsys.readouterr().err


def test_a_listed_file_that_is_absent_exits_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A module on the list that does not exist is a refusal, never a clean count."""
    root = _root(tmp_path, "ghost.py\n")
    assert websubset_cli.main(["--census", str(root)]) == websubset_cli.EXIT_USAGE
    assert "ghost.py is listed but cannot be read" in capsys.readouterr().err


def test_census_writes_the_jsonl_and_counts_ledgers_with_named_fields(tmp_path: Path) -> None:
    """One JSON row per refused construct, and a module-to-count object for those with findings."""
    root = _root(tmp_path, "clean.py\ndirty.py\n")
    rows, counts = tmp_path / "rows.jsonl", tmp_path / "counts.json"
    argv = ["--census", str(root), "--jsonl", str(rows), "--counts", str(counts)]
    assert websubset_cli.main(argv) == websubset_cli.EXIT_FINDINGS
    lines = rows.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(("eval-exec", "unannotated", "unannotated"))
    assert (
        '{"module": "dirty.py", "line": 2, "rule": "eval-exec", '
        '"message": "`eval` runs code built at run time"}'
    ) in lines
    assert not any("clean.py" in line for line in lines)
    assert counts.read_text(encoding="utf-8") == '{"dirty.py": 3}\n'
    assert not (tmp_path / ".rows.jsonl.tmp").exists()


def test_a_clean_census_still_writes_empty_ledgers(tmp_path: Path) -> None:
    """An empty jsonl and an empty object: the ledger says the census ran and found nothing."""
    root = _root(tmp_path, "clean.py\n")
    rows, counts = tmp_path / "rows.jsonl", tmp_path / "counts.json"
    argv = ["--census", str(root), "--jsonl", str(rows), "--counts", str(counts)]
    assert websubset_cli.main(argv) == _OK
    assert not rows.read_text(encoding="utf-8")
    assert counts.read_text(encoding="utf-8") == "{}\n"


def test_a_ledger_flag_without_census_or_repeated_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--jsonl` has no meaning beside `--check-file`, and a repeated flag is ambiguous."""
    target = str(tmp_path / "x.jsonl")
    beside = websubset_cli.main(["--check-file", "a.py", "--jsonl", target])
    assert beside == websubset_cli.EXIT_USAGE
    again = ["--census", str(tmp_path), "--jsonl", target, "--jsonl", target]
    assert websubset_cli.main(again) == websubset_cli.EXIT_USAGE
    assert capsys.readouterr().err.count("usage:") == len(("check-file", "repeated"))
    assert not (tmp_path / "x.jsonl").exists()


def test_any_other_argument_shape_prints_the_usage_and_exits_two(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No arguments, a lone flag and an unknown flag are each a usage error."""
    for argv in _SHAPES:
        assert websubset_cli.main(argv) == websubset_cli.EXIT_USAGE
    assert capsys.readouterr().err.count("usage:") == len(_SHAPES)
