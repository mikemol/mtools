# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that the driver PRINTS what the directory-operand walk left out.

The walk moved to mikemol-pathwalk (mtools:W573); its own suite proves what it skips. What stays
here is the contract of the driver: the `skipped ...` and `refused ...` lines, exactly as before,
and the exit code 2 of a refusal. Every case runs git in a DECOY repository made under tmp_path,
with every GIT_* variable removed and the global and system git config switched off.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import cli

if TYPE_CHECKING:
    from pathlib import Path

_IMPORTER = "import target_mod\n"
_MAIN = "main_importer.py"
_WT_ONLY = "wt_only_importer.py"
_THIRD_PARTY = "third_party_importer.py"
_REFUSED = 2


def _git(root: Path, *args: str) -> None:
    git = shutil.which("git")
    assert git is not None
    subprocess.run(
        [git, "-c", "user.name=decoy", "-c", "user.email=decoy@invalid", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _isolate(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a repository with one importer and one linked worktree holding its own importer.

    Returns:
        the main tree's root.

    """
    _isolate(monkeypatch)
    root = tmp_path / "repo"
    root.mkdir()
    (root / _MAIN).write_text(_IMPORTER, encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    tree = root / ".claude" / "worktrees" / "wt"
    _git(root, "worktree", "add", "-q", "--detach", str(tree))
    (tree / _WT_ONLY).write_text(_IMPORTER, encoding="utf-8")
    return root


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    code = cli.main(["importers", "target_mod", *argv])
    return code, capsys.readouterr().out


def test_a_directory_operand_skips_a_registered_worktree_and_says_so(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Default: the importer outside the worktree is found, the one inside is not, skip printed."""
    code, out = _run(capsys, str(repo))
    assert code == 0
    assert f"{repo / _MAIN}:1" in out
    assert _WT_ONLY not in out
    assert "skipped 1 registered worktrees" in out
    assert "skipped 0 virtualenvs" in out
    assert "refused 0 symlinks (not followed)" in out


def test_include_worktrees_reads_the_worktree_and_reports_zero_skipped(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With --include-worktrees both importers are found and the skip line says zero."""
    code, out = _run(capsys, "--include-worktrees", str(repo))
    assert code == 0
    assert f"{repo / '.claude' / 'worktrees' / 'wt' / _WT_ONLY}:1" in out
    assert "skipped 0 registered worktrees" in out


def test_require_hits_on_a_directory_counts_the_worktree_files_searched(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty directory search exits 1; --include-worktrees widens the searched count.

    The skip lines are not rows, so they never turn an empty result into a hit.
    """
    code = cli.main(["importers", "--require-hits", "nobody", str(repo)])
    out = capsys.readouterr().out
    assert code == 1
    assert "skipped 1 registered worktrees" in out
    assert "importers: searched 1 file(s), found none" in out
    wide = ["importers", "--require-hits", "--include-worktrees", "nobody", str(repo)]
    code = cli.main(wide)
    out = capsys.readouterr().out
    assert code == 1
    assert "skipped 0 registered worktrees" in out
    assert "importers: searched 3 file(s), found none" in out


def test_require_hits_on_a_directory_with_a_worktree_hit_exits_zero(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A hit found only through --include-worktrees is a hit: exit 0, no found-none line."""
    (repo / _MAIN).write_text("x = 1\n", encoding="utf-8")
    code = cli.main(["importers", "--require-hits", "target_mod", str(repo)])
    assert code == 1
    assert "found none" in capsys.readouterr().out
    code = cli.main(["importers", "--require-hits", "--include-worktrees", "target_mod", str(repo)])
    out = capsys.readouterr().out
    assert code == 0
    assert _WT_ONLY in out
    assert "found none" not in out


def test_a_venv_is_pruned_and_printed(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A directory holding pyvenv.cfg is not walked, and the driver prints the count."""
    venv = repo / ".venv"
    venv.mkdir()
    (venv / _THIRD_PARTY).write_text(_IMPORTER, encoding="utf-8")
    (venv / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
    code, out = _run(capsys, str(repo))
    assert code == 0
    assert _THIRD_PARTY not in out
    assert "skipped 1 virtualenvs" in out


def test_a_symlink_is_counted_and_printed(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A linked file is not read, and the driver prints the refused count."""
    (repo / "linked_file.py").symlink_to(repo / _MAIN)
    code, out = _run(capsys, str(repo))
    assert code == 0
    assert "refused 1 symlinks (not followed)" in out
    assert "linked_file.py" not in out


def test_a_refused_walk_exits_two_and_names_why(
    repo: Path, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A symlink given AS the directory operand refuses (exit 2) with the walk's message."""
    (tmp_path / "front").symlink_to(repo, target_is_directory=True)
    code, out = _run(capsys, str(tmp_path / "front"))
    assert code == _REFUSED
    assert "is a symlink to a directory" in out
    assert "skipped" not in out


def test_file_operands_print_no_skip_line(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Explicit files are read as given, with no skip line."""
    code, out = _run(capsys, str(repo / _MAIN))
    assert code == 0
    assert f"{repo / _MAIN}:1" in out
    assert "skipped" not in out


_GEN = "generated_importer.py"


def _generated(repo: Path, *names: str) -> None:
    """Give each named directory under the repo one importer file."""
    for name in names:
        (repo / name).mkdir()
        (repo / name / _GEN).write_text(_IMPORTER, encoding="utf-8")


def test_exclude_prunes_a_named_directory_and_counts_it(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W658: `--exclude build` drops build/ by its name, keeps builder/, and prints the count."""
    _generated(repo, "build", "builder")
    code, out = _run(capsys, "--exclude", "build", str(repo))
    assert code == 0
    assert str(repo / "build" / _GEN) not in out
    assert str(repo / "builder" / _GEN) in out
    assert "skipped 1 excluded directories" in out


def test_without_exclude_nothing_is_pruned_and_the_count_is_zero(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W658: no default list: build/ is read unless the caller names it, and the count says zero."""
    _generated(repo, "build")
    code, out = _run(capsys, str(repo))
    assert code == 0
    assert str(repo / "build" / _GEN) in out
    assert "skipped 0 excluded directories" in out


def test_exclude_is_repeatable_takes_a_glob_and_binds_both_spellings(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W658: a spaced entry and an `=` entry both bind, and `bazel-*` prunes by glob."""
    _generated(repo, "build", "bazel-bin", "src")
    code, out = _run(capsys, "--exclude", "build", "--exclude=bazel-*", str(repo))
    assert code == 0
    assert str(repo / "build" / _GEN) not in out
    assert str(repo / "bazel-bin" / _GEN) not in out
    assert str(repo / "src" / _GEN) in out
    assert "skipped 2 excluded directories" in out


@pytest.mark.parametrize("entry", ["", "a/b"])
def test_a_bad_exclude_entry_is_refused_by_name(
    entry: str, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W658: an empty or path-shaped entry is exit 2 and the refusal quotes the entry."""
    code, out = _run(capsys, "--exclude", entry, str(repo))
    assert code == _REFUSED
    assert f"exclude {entry!r}" in out


def test_exclude_with_a_file_operand_prints_no_count_line(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W658: file operands are read as given; no directory was expanded, so no count line."""
    code, out = _run(capsys, "--exclude", "build", str(repo / _MAIN))
    assert code == 0
    assert "excluded directories" not in out
