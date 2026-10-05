# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a directory operand reuses the sibling walk and keeps the answer on stdout.

Asked for by el-openglo (W138, mtools:W561): a structural query over a repo root must not read the
registered worktrees under `.claude/worktrees`. The walk is mikemol-pathwalk's and has its own
suite; what is proved HERE is the driver: every read mode accepts a directory, the write modes
refuse one, the count lines go to STDERR and only for a directory operand, and a refusal from the
walk is exit 2. Every case that needs a worktree runs real git in a repository made under
tmp_path, with every GIT_* variable removed and the global and system git config switched off.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from mikemol.mdstruct import cli, operands

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.needs_pandoc

_MAIN = "main_doc.md"
_WT_ONLY = "wt_only_doc.md"
_VENV_ONLY = "venv_only_doc.md"
_BODY = "# Heading\n\nSome prose.\n"
_REFUSED = 2
_SKIP_ONE = "skipped 1 registered worktrees"
_SKIP_ZERO = "skipped 0 registered worktrees"
_READ_MODES = [
    "spans",
    "budget",
    "items",
    "tables",
    "rows",
    "classify",
    "labels",
    "roundtrip",
    "fixpoint",
    "lint",
    "verify",
    "narrowest",
]


def _git(root: Path, *args: str) -> None:
    git = shutil.which("git")
    assert git is not None
    subprocess.run(
        [git, "-c", "user.name=decoy", "-c", "user.email=decoy@invalid", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _isolate(monkeypatch: pytest.MonkeyPatch, ceiling: Path) -> None:
    for key in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(ceiling))


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a repository with one document, one venv holding one, and one linked worktree.

    Returns:
        the main tree's root.

    """
    _isolate(monkeypatch, tmp_path)
    root = tmp_path / "repo"
    root.mkdir()
    (root / _MAIN).write_text(_BODY, encoding="utf-8")
    venv = root / "env"
    venv.mkdir()
    (venv / "pyvenv.cfg").write_text("home = /nowhere\n", encoding="utf-8")
    (venv / _VENV_ONLY).write_text(_BODY, encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    tree = root / ".claude" / "worktrees" / "wt"
    _git(root, "worktree", "add", "-q", "--detach", str(tree))
    (tree / _WT_ONLY).write_text(_BODY, encoding="utf-8")
    return root


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = cli.main(["mdstruct", *argv])
    got = capsys.readouterr()
    return code, got.out, got.err


def test_a_directory_skips_a_registered_worktree_and_says_so_on_stderr(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Default: the document outside the worktree is read, the one inside is not."""
    code, out, err = _run(capsys, "spans", str(repo))
    assert code == 0
    assert _MAIN in out
    assert _WT_ONLY not in out
    assert _SKIP_ONE in err
    assert "skipped 1 virtualenvs" in err
    assert "refused 0 symlinks (not followed)" in err


def test_nothing_but_the_answer_reaches_stdout(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The three count lines are stderr only, however many files were read."""
    _, out, _ = _run(capsys, "spans", str(repo))
    assert "skipped" not in out
    assert "refused" not in out


def test_include_worktrees_reads_the_worktree_and_reports_zero_skipped(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The switch reads the worktree's documents and the skip count is zero."""
    code, out, err = _run(capsys, "spans", str(repo), "--include-worktrees")
    assert code == 0
    assert _MAIN in out
    assert _WT_ONLY in out
    assert _SKIP_ZERO in err


def test_a_virtualenv_is_pruned_even_with_the_worktree_switch(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A venv is not a worktree: its documents stay unread and it is counted."""
    _, out, err = _run(capsys, "spans", str(repo), "--include-worktrees")
    assert _VENV_ONLY not in out
    assert "skipped 2 virtualenvs" in err


def test_a_file_operand_prints_no_count_lines(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Existing single-file output is unchanged: nothing on stderr."""
    code, out, err = _run(capsys, "spans", str(repo / _MAIN))
    assert code == 0
    assert _MAIN in out
    assert not err


@pytest.mark.parametrize("mode", _READ_MODES)
def test_every_read_mode_accepts_a_directory(
    mode: str, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each read mode expands the directory instead of failing in pandoc."""
    _, _, err = _run(capsys, mode, str(repo))
    assert _SKIP_ONE in err
    assert "no such file" not in err


def test_grep_accepts_a_directory_and_keeps_its_pattern_slot(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The first operand stays the pattern; the directory after it is expanded."""
    code, out, err = _run(capsys, "grep", "prose", str(repo))
    assert code == 0
    assert "Some prose." in out
    assert _SKIP_ONE in err


def test_grep_over_a_directory_is_zero_when_any_file_matched(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file that lacks the term does not make the corpus verdict nonzero."""
    (repo / "other.md").write_text("# Other\n\nNothing here.\n", encoding="utf-8")
    code, _, _ = _run(capsys, "grep", "prose", str(repo))
    assert code == 0


def test_grep_over_a_directory_is_one_when_no_file_matched(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No match anywhere keeps grep's own nonzero code."""
    code, _, _ = _run(capsys, "grep", "absent-term-xyz", str(repo))
    assert code == 1


def test_lint_over_a_directory_returns_the_worst_code(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One failing document makes the fold nonzero while the clean one still prints."""
    (repo / "wide.md").write_text(f"# Wide\n\n{'word ' * 60}\n", encoding="utf-8")
    code, out, _ = _run(capsys, "lint", str(repo), "--width", "40")
    assert code == 1
    assert "wide.md" in out
    assert _MAIN in out


def test_a_missing_file_beside_a_directory_is_exit_two(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file operand that does not exist is named, and the fold carries the 2."""
    code, _, err = _run(capsys, "spans", str(repo), str(repo / "gone.md"))
    assert code == _REFUSED
    assert "no such file" in err


def test_an_empty_directory_reads_nothing_and_reports_zero_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A directory with no documents is a clean zero, with the count lines present."""
    _isolate(monkeypatch, tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    _git(empty, "init", "-q")
    code, out, err = _run(capsys, "spans", str(empty))
    assert code == 0
    assert not out
    assert _SKIP_ZERO in err


def test_git_unable_to_list_worktrees_refuses_with_exit_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Outside any repository the walk refuses, and the driver says so on stderr."""
    _isolate(monkeypatch, tmp_path)
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / _MAIN).write_text(_BODY, encoding="utf-8")
    code, out, err = _run(capsys, "spans", str(plain))
    assert code == _REFUSED
    assert not out
    assert err.startswith("mdstruct: refused: git worktree list failed")


@pytest.mark.parametrize("mode", ["replace-section", "append-section"])
def test_a_write_mode_refuses_a_directory(
    mode: str, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A bounded write against many files is ambiguous: exit 2 with the exact text."""
    code, out, err = _run(capsys, mode, "Heading", str(repo), "--body-file", "-")
    assert code == _REFUSED
    assert not out
    assert err == (
        f"mdstruct: {mode} writes one document; {repo} is a directory. "
        "A bounded write against many files is ambiguous. Name the file.\n"
    )


@pytest.mark.parametrize("mode", ["replace-section", "append-section"])
def test_a_write_mode_does_not_take_the_worktree_switch(
    mode: str, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The flag is owned by the directory-capable modes; a writer refuses it as unknown."""
    code, _, err = _run(capsys, mode, "Heading", str(repo), "--include-worktrees")
    assert code == _REFUSED
    assert f"mdstruct: {mode} does not take --include-worktrees" in err


def test_resolve_reports_the_counts_only_for_a_directory(repo: Path) -> None:
    """The resolution carries the files and the three lines, and no refusal."""
    got = operands.resolve([str(repo)], include_worktrees=False)
    assert got.refusal is None
    assert str(repo / _MAIN) in got.files
    assert got.notes == (
        "skipped 1 registered worktrees\nskipped 1 virtualenvs\n"
        "skipped 0 excluded directories\nrefused 0 symlinks (not followed)\n"
    )


def test_resolve_passes_a_file_through_with_no_notes(repo: Path) -> None:
    """A file operand is untouched and says nothing."""
    named = str(repo / _MAIN)
    got = operands.resolve([named], include_worktrees=False)
    assert got.files == [named]
    assert not got.notes


def test_resolve_turns_the_siblings_refusal_into_a_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory git cannot list yields the refusal text and no files."""
    _isolate(monkeypatch, tmp_path)
    plain = tmp_path / "plain"
    plain.mkdir()
    got = operands.resolve([str(plain)], include_worktrees=False)
    assert got.files == []
    assert got.refusal is not None
    assert got.refusal.startswith("mdstruct: refused: ")


def test_has_directory_tells_a_directory_from_a_file(repo: Path) -> None:
    """True for a directory operand, false for a file or a missing name."""
    assert operands.has_directory([str(repo / _MAIN), str(repo)])
    assert not operands.has_directory([str(repo / _MAIN), str(repo / "gone.md")])


_GEN = "generated_doc.md"
_EXCLUDED_ONE = "skipped 1 excluded directories"
_EXCLUDED_TWO = "skipped 2 excluded directories"
_EXCLUDED_ZERO = "skipped 0 excluded directories"


def _generated(repo: Path, *names: str) -> None:
    for name in names:
        (repo / name).mkdir()
        (repo / name / _GEN).write_text(_BODY, encoding="utf-8")


def test_exclude_prunes_a_named_directory_and_counts_it(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Red on HEAD by a missing name: `--exclude` is refused as a flag no mode takes."""
    _generated(repo, "build", "builder")
    code, out, err = _run(capsys, "spans", str(repo), "--exclude", "build")
    assert code == 0
    assert _MAIN in out
    assert str(repo / "build" / _GEN) not in out
    assert str(repo / "builder" / _GEN) in out
    assert _EXCLUDED_ONE in err


def test_without_exclude_nothing_is_pruned_and_the_count_is_zero(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No default list: a `build` directory is read, and the zero is printed."""
    _generated(repo, "build")
    _, out, err = _run(capsys, "spans", str(repo))
    assert str(repo / "build" / _GEN) in out
    assert _EXCLUDED_ZERO in err


def test_exclude_is_repeatable_takes_a_glob_and_binds_both_spellings(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two entries, one spaced and one with `=`, prune `build` and `bazel-bin` (by glob)."""
    _generated(repo, "build", "bazel-bin", "src")
    code, out, err = _run(capsys, "spans", str(repo), "--exclude", "build", "--exclude=bazel-*")
    assert code == 0
    assert str(repo / "build" / _GEN) not in out
    assert str(repo / "bazel-bin" / _GEN) not in out
    assert str(repo / "src" / _GEN) in out
    assert _EXCLUDED_TWO in err


def test_exclude_counts_apply_to_every_read_mode_and_grep(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`grep` keeps its pattern slot and honours the flag the same way."""
    _generated(repo, "build")
    code, out, err = _run(capsys, "grep", "prose", str(repo), "--exclude", "build")
    assert code == 0
    assert str(repo / "build" / _GEN) not in out
    assert _EXCLUDED_ONE in err


@pytest.mark.parametrize("entry", ["", "a/b"])
def test_a_bad_exclude_entry_is_refused_by_name(
    entry: str, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty or path-shaped entry is exit 2 and the refusal quotes the entry."""
    code, out, err = _run(capsys, "spans", str(repo), "--exclude", entry)
    assert code == _REFUSED
    assert not out
    assert err.startswith(f"mdstruct: refused: exclude {entry!r} must be a non-empty")


def test_a_write_mode_does_not_take_exclude(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The flag belongs to the directory-capable modes; a writer refuses it as unknown."""
    code, _, err = _run(capsys, "replace-section", "Heading", str(repo), "--exclude", "build")
    assert code == _REFUSED
    assert "mdstruct: replace-section does not take --exclude" in err


def test_exclude_with_a_file_operand_prints_no_count_lines(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Only a directory operand reports counts, whether or not the flag was given."""
    code, _, err = _run(capsys, "spans", str(repo / _MAIN), "--exclude", "build")
    assert code == 0
    assert not err


def test_resolve_counts_the_excluded_directories_and_drops_their_files(repo: Path) -> None:
    """`exclude=` reaches the sibling walk and its count lands on the notes."""
    _generated(repo, "build")
    got = operands.resolve([str(repo)], include_worktrees=False, exclude=["build"])
    assert str(repo / "build" / _GEN) not in got.files
    assert str(repo / _MAIN) in got.files
    assert _EXCLUDED_ONE in got.notes


def test_resolve_with_an_empty_exclude_changes_nothing(repo: Path) -> None:
    """An empty sequence is the default: same files, same notes."""
    _generated(repo, "build")
    plain = operands.resolve([str(repo)], include_worktrees=False)
    empty = operands.resolve([str(repo)], include_worktrees=False, exclude=[])
    assert empty == plain
    assert str(repo / "build" / _GEN) in empty.files
    assert _EXCLUDED_ZERO in empty.notes


def test_resolve_refuses_a_bad_exclude_entry_by_name(repo: Path) -> None:
    """A path-shaped entry yields the refusal text naming it, and no files."""
    got = operands.resolve([str(repo)], include_worktrees=False, exclude=["x/y"])
    assert got.files == []
    assert got.refusal is not None
    assert "'x/y'" in got.refusal


def test_write_refusal_is_none_for_a_file(repo: Path) -> None:
    """Only a directory is refused."""
    assert operands.write_refusal("replace-section", repo / _MAIN) is None
    assert operands.write_refusal("replace-section", repo) is not None
