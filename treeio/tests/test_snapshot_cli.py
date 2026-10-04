# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `snapshot_cli`: which snapshot holds a path, in what order, and how to restore."""

from __future__ import annotations

import contextvars
import os
import sys
from typing import TYPE_CHECKING

from mikemol.treeio.gitrun import git
from mikemol.treeio.snapshot import snapshot
from mikemol.treeio.snapshot_cli import holding_rows, main

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    import pytest

_USAGE_EXIT = 2
_MANY = 8


def _fresh[T](fn: Callable[[], T]) -> T:
    """Run `fn` as its own invocation, so the snapshot record never leaks between tests.

    Returns:
        Whatever `fn` returns.

    """
    return contextvars.copy_context().run(fn)


def _repo(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `root` a repository with one commit, and stand the process in it."""
    for name in [n for n in os.environ if n.startswith("GIT_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(root.parent))
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")
    git(root, "init", "-q")
    (root / "a.txt").write_text("one", encoding="utf-8")
    git(root, "add", "a.txt")
    git(root, "commit", "-qm", "c")
    monkeypatch.chdir(root)


def _journal(path: Path, rows: list[str]) -> Path:
    """Write a journal file holding the given rows after its header.

    Returns:
        The journal path.

    """
    path.write_text("# sha\tlabel\tn_paths\tpaths\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_holding_rows_are_newest_first_and_skip_comments_blanks_and_short_rows(
    tmp_path: Path,
) -> None:
    """The journal is newest-last, so rows are reversed once, and malformed lines are skipped."""
    journal = _journal(
        tmp_path / "j.tsv",
        [
            "aaa\told\t1\tp/x.agda",
            "",
            "short\trow",
            "bbb\tmid\t2\tp/y.agda,q/other.agda",
            "ccc\tnew\t1\tp/x.agda",
        ],
    )
    assert holding_rows(journal, "x.agda") == [
        ("ccc", "new", ["p/x.agda"]),
        ("aaa", "old", ["p/x.agda"]),
    ]
    assert holding_rows(journal, "p/") == [
        ("ccc", "new", ["p/x.agda"]),
        ("bbb", "mid", ["p/y.agda"]),
        ("aaa", "old", ["p/x.agda"]),
    ]
    assert holding_rows(journal, "nothing") == []


def test_holding_rows_of_a_missing_journal_is_empty(tmp_path: Path) -> None:
    """No journal means no snapshot holds anything."""
    assert holding_rows(tmp_path / "absent.tsv", "x") == []


def test_list_says_when_nothing_is_recorded_and_otherwise_dumps_the_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The raw journal is shown verbatim, or a sentence when there is none."""
    _repo(tmp_path, monkeypatch)
    assert main(["--list"]) == 0
    assert capsys.readouterr().out == "no snapshots recorded\n"
    sha = _fresh(lambda: snapshot("t", ["a.txt"], tmp_path))
    capsys.readouterr()
    assert main(["--list"]) == 0
    assert capsys.readouterr().out == (
        "# sha\tlabel\tn_paths\tpaths\n"
        "# restore:  git checkout <sha> -- <path>...\n"
        "# list:     git show --stat <sha>\n"
        f"{sha}\tt\t1\ta.txt\n"
    )


def test_holding_leads_with_the_newest_and_the_restore_hint_names_that_same_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The orientation is pinned: the hint names the listing's first row, not the journal's."""
    _repo(tmp_path, monkeypatch)
    (tmp_path / "scratch").mkdir()
    _journal(
        tmp_path / "scratch" / "edit_snapshot.journal.tsv",
        ["a" * 40 + "\told\t1\tp/x.agda", "b" * 40 + "\tnew\t1\tp/x.agda"],
    )
    assert main(["--holding", "x.agda"]) == 0
    assert capsys.readouterr().out == (
        f"{'b' * 12}  new\n"
        "      p/x.agda\n"
        f"{'a' * 12}  old\n"
        "      p/x.agda\n"
        "2 snapshot(s) hold a path matching 'x.agda' (newest first)\n"
        f"   restore:  mikemol-edit-snapshot --from-snapshot={'b' * 12} <path> --apply\n"
    )


def test_holding_names_five_paths_and_counts_the_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A snapshot with many matching paths shows five and summarizes the remainder."""
    _repo(tmp_path, monkeypatch)
    (tmp_path / "scratch").mkdir()
    paths = ",".join(f"d/f{n}.agda" for n in range(_MANY))
    _journal(
        tmp_path / "scratch" / "edit_snapshot.journal.tsv", [f"{'c' * 40}\tbig\t{_MANY}\t{paths}"]
    )
    assert main(["--holding", ".agda"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[1:6] == [f"      d/f{n}.agda" for n in range(5)]
    assert lines[6] == "      … 3 more matching path(s)"


def test_holding_with_no_match_says_so_and_offers_no_restore_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Nothing matched, so there is nothing to restore and no hint to print."""
    _repo(tmp_path, monkeypatch)
    assert main(["--holding", "nothing"]) == 0
    assert capsys.readouterr().out == (
        "0 snapshot(s) hold a path matching 'nothing' (newest first)\n"
    )


def test_holding_without_a_fragment_prints_its_usage_and_exits_two(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The fragment is required, and the refusal says how to give one."""
    assert main(["--holding"]) == _USAGE_EXIT
    assert capsys.readouterr().out == "usage: mikemol-edit-snapshot --holding <path-fragment>\n"


def test_from_snapshot_without_apply_reports_what_it_would_restore_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A dry run lists each path, counts the halves, warns about the untracked copy, and is dry."""
    _repo(tmp_path, monkeypatch)
    (tmp_path / "a.txt").write_text("two", encoding="utf-8")
    (tmp_path / "tool.py").write_text("good", encoding="utf-8")
    sha = _fresh(lambda: snapshot("t", ["tool.py"], tmp_path))
    (tmp_path / "a.txt").write_text("DAMAGED", encoding="utf-8")
    capsys.readouterr()
    assert main([f"--from-snapshot={sha}"]) == 0
    assert capsys.readouterr().out == (
        "would restore  tracked            a.txt\n"
        "would restore  untracked-latest   tool.py\n"
        "2 path(s): 1 tracked, 1 untracked\n"
        "   ⚑ untracked entries are the MOST RECENT pre-write copy "
        "(the store is keyed by path, not by sha)\n"
        "\nDry run — pass --apply to execute.\n"
    )
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "DAMAGED"


def test_from_snapshot_with_apply_restores_the_named_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With apply the rows say RESTORED, only the named path comes back, and no dry-run note."""
    _repo(tmp_path, monkeypatch)
    (tmp_path / "a.txt").write_text("two", encoding="utf-8")
    sha = _fresh(lambda: snapshot("t", [], tmp_path))
    (tmp_path / "a.txt").write_text("DAMAGED", encoding="utf-8")
    capsys.readouterr()
    assert main([f"--from-snapshot={sha}", "a.txt", "--apply"]) == 0
    assert capsys.readouterr().out == (
        "RESTORED       tracked            a.txt\n1 path(s): 1 tracked, 0 untracked\n"
    )
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "two"


def test_no_mode_or_an_empty_snapshot_names_prints_the_description_and_the_usage(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Without a mode the tool describes itself and shows all three forms."""
    assert main([]) == 0
    first = capsys.readouterr().out
    assert first.startswith("A recoverable-by-construction snapshot for any tool")
    assert "mikemol-edit-snapshot --from-snapshot=<sha> [paths] [--apply]" in first
    assert main(["--from-snapshot="]) == 0
    assert capsys.readouterr().out == first


def test_main_reads_the_process_arguments_when_none_are_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no argv argument the command line is the process's own."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["mikemol-edit-snapshot", "--list"])
    assert main() == 0
    assert capsys.readouterr().out == "no snapshots recorded\n"
