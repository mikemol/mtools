# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `vfs_cli`: each mode's output, and exit codes that keep the three answers apart."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pygit2

from mikemol.treeio.vfs_cli import main

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_BROKEN = 2
_AMBIGUOUS = 3
_FILES = {
    "has.txt": b"hello",
    "empty.txt": b"",
    "d/top.agda": b"x",
    "d/sub/mid.agda": b"x",
    "d/sub/deep/low.agda": b"x",
}


def _tree(repo: pygit2.Repository, files: dict[str, bytes]) -> pygit2.Oid:
    """Build the tree object for a mapping of slash-separated paths to bytes.

    Returns:
        The id of the written tree.

    """
    builder = repo.TreeBuilder()
    nested: dict[str, dict[str, bytes]] = {}
    for rel, data in files.items():
        head, sep, rest = rel.partition("/")
        if sep:
            nested.setdefault(head, {})[rest] = data
        else:
            builder.insert(head, repo.create_blob(data), pygit2.enums.FileMode.BLOB)
    for name, sub in nested.items():
        builder.insert(name, _tree(repo, sub), pygit2.enums.FileMode.TREE)
    return builder.write()


def _corpus(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Commit the corpus, lay it out on disk, and stand the process in it."""
    repo = pygit2.init_repository(str(root), initial_head="main")
    who = pygit2.Signature("t", "t@t")
    repo.create_commit("HEAD", who, who, "t", _tree(repo, _FILES), [])
    for rel, data in _FILES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    monkeypatch.chdir(root)


def test_states_prints_the_roster_with_the_defect_marked(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each presence is listed with its gloss, and only BROKEN carries the defect marker."""
    assert main(["--states"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [ln.split()[0] for ln in lines] == ["PRESENT", "ABSENT", "BROKEN"]
    assert "(defect)" not in lines[0]
    assert "(defect)" not in lines[1]
    assert "(defect) bad rev, not a repo" in lines[_BROKEN]
    assert lines[0].startswith("  PRESENT  a blob exists")


def test_read_reports_present_with_exit_zero_and_the_byte_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A present path prints its presence, source and size, and exits zero."""
    _corpus(tmp_path, monkeypatch)
    assert main(["--read", "has.txt"]) == 0
    assert capsys.readouterr().out == "PRESENT  has.txt  (working tree)\n  5 bytes\n"


def test_read_reports_absent_with_exit_one_and_the_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing path exits one, which is a legitimate answer and not an error."""
    _corpus(tmp_path, monkeypatch)
    assert main(["--read", "gone.txt"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("ABSENT   gone.txt  (working tree)\n")
    assert "No such file or directory" in out


def test_read_reports_broken_with_exit_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A directory is BROKEN, and the exit code says the read did not happen."""
    _corpus(tmp_path, monkeypatch)
    assert main(["--read", "d"]) == _BROKEN
    out = capsys.readouterr().out
    assert out.startswith("BROKEN   d  (working tree)\n")
    assert "Is a directory" in out


def test_read_at_a_revision_and_a_bad_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The revision flag reads from history, and a bad revision is BROKEN rather than ABSENT."""
    _corpus(tmp_path, monkeypatch)
    assert main(["--read", "has.txt", "--at", "HEAD"]) == 0
    assert capsys.readouterr().out == "PRESENT  has.txt  (rev HEAD)\n  5 bytes\n"
    assert main(["--read", "has.txt", "--at", "nosuchrev-zzz-9999"]) == _BROKEN
    assert "bad revision 'nosuchrev-zzz-9999'" in capsys.readouterr().out


def test_list_prints_paths_and_honours_the_suffix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A depth-agnostic glob plus a suffix lists every depth, one path per line."""
    _corpus(tmp_path, monkeypatch)
    assert main(["--list", "d/**", "--suffix", ".agda", "--at", "HEAD"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "d/sub/deep/low.agda",
        "d/sub/mid.agda",
        "d/top.agda",
    ]


def test_an_ambiguous_pattern_is_a_verdict_with_exit_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The refusal names the pattern to use instead on stderr and exits three, not a traceback."""
    _corpus(tmp_path, monkeypatch)
    assert main(["--list", "d/**/*.agda"]) == _AMBIGUOUS
    captured = capsys.readouterr()
    assert not captured.out
    assert captured.err.startswith("AMBIGUOUS  pattern 'd/**/*.agda' means different things")
    assert "depth-agnostic `d/**`" in captured.err


def test_census_prints_the_cells_and_exits_two_on_a_broken_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The census names the empty file, counts the cells, and exits two when one member broke."""
    _corpus(tmp_path, monkeypatch)
    assert main(["--census", "*.txt"]) == 0
    assert capsys.readouterr().out == (
        "census *.txt  (working tree)\n"
        "  PRESENT nonempty  1\n"
        "  PRESENT empty     1\n"
        "      empty.txt\n"
        "  ABSENT            0\n"
        "  BROKEN            0\n"
        "  total             2\n"
    )
    (tmp_path / "dir.txt").mkdir()
    assert main(["--census", "*.txt", "--suffix", ".txt"]) == _BROKEN
    out = capsys.readouterr().out
    assert out.startswith("census *.txt  suffix=.txt  (working tree)\n")
    assert "  BROKEN            1\n      dir.txt  " in out
    assert out.endswith("  total             3\n")


def test_compare_prints_the_header_and_each_sources_misses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The comparison names what each matcher dropped relative to the depth-agnostic control."""
    _corpus(tmp_path, monkeypatch)
    assert main(["--compare", "d/*.agda", "--suffix", ".agda"]) == 0
    assert capsys.readouterr().out == (
        "compare d/*.agda   control d/**   rev HEAD\n"
        "  wt        1   control     3   missed 2   extra 0\n"
        "        MISSED  d/sub/deep/low.agda\n"
        "        MISSED  d/sub/mid.agda\n"
        "  head      3   control     3   missed 0   extra 0\n"
    )


def test_compare_names_extra_paths_and_takes_the_revision_from_at(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A pattern selecting more than its control prints EXTRA lines, under the chosen revision."""
    _corpus(tmp_path, monkeypatch)
    (tmp_path / "d" / "stray.agda").write_bytes(b"x")
    assert main(["--compare", "d/**", "--suffix", ".agda", "--at", "HEAD"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("compare d/**   control d/**   rev HEAD\n")
    assert "EXTRA" not in out
    assert main(["--compare", "*.agda", "--suffix", ".agda"]) == 0
    extra = [ln for ln in capsys.readouterr().out.splitlines() if "EXTRA  " in ln]
    assert extra == [
        "        EXTRA   d/sub/deep/low.agda",
        "        EXTRA   d/sub/mid.agda",
        "        EXTRA   d/top.agda",
    ]


def test_no_mode_prints_the_usage_and_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without a mode the help is shown, naming the program."""
    _corpus(tmp_path, monkeypatch)
    assert main([]) == 0
    assert capsys.readouterr().out.startswith("usage: mikemol-vfs")


def test_main_reads_the_process_arguments_when_none_are_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no argv argument the command line is the process's own."""
    _corpus(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "argv", ["mikemol-vfs", "--read", "has.txt"])
    assert main() == 0
    assert capsys.readouterr().out.startswith("PRESENT  has.txt")
