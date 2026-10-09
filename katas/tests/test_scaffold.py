# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `scaffold`: bazel files from templates, never overwritten, and the hook swap."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.katas import scaffold

if TYPE_CHECKING:
    from pathlib import Path

_VERSION = "9.9.9"
_THREE = 3


def _templates(tmp_path: Path) -> Path:
    """Write the three templates a scaffold and a hook install read.

    Returns:
        the templates directory.

    """
    directory = tmp_path / "templates"
    directory.mkdir()
    (directory / "bazelrc").write_text("# rc for @REPO@\n", encoding="utf-8")
    (directory / "MODULE.bazel").write_text('module(name = "@REPO@")\n', encoding="utf-8")
    (directory / "pre-commit").write_text("exec bazel test //:precommit # @REPO@\n", "utf-8")
    return directory


def _repo(tmp_path: Path) -> Path:
    """Make an empty repo directory named `proj`.

    Returns:
        its path.

    """
    root = tmp_path / "proj"
    root.mkdir()
    return root


def test_the_three_files_are_written_with_the_repo_name_filled_in(tmp_path: Path) -> None:
    """The placeholder becomes the directory's name; the version file holds the version."""
    root = _repo(tmp_path)
    wrote, left = scaffold.scaffold(root, _templates(tmp_path), _VERSION)
    assert len(wrote) == _THREE
    assert not left
    assert (root / ".bazelrc").read_text(encoding="utf-8") == "# rc for proj\n"
    assert (root / "MODULE.bazel").read_text(encoding="utf-8") == 'module(name = "proj")\n'
    assert (root / ".bazelversion").read_text(encoding="utf-8") == f"{_VERSION}\n"


def test_an_existing_file_is_left_alone_and_named(tmp_path: Path) -> None:
    """Nothing is overwritten: the existing file keeps its bytes and is reported."""
    root = _repo(tmp_path)
    (root / ".bazelrc").write_text("mine\n", encoding="utf-8")
    wrote, left = scaffold.scaffold(root, _templates(tmp_path), _VERSION)
    assert left == [".bazelrc"]
    assert ".bazelrc" not in wrote
    assert (root / ".bazelrc").read_text(encoding="utf-8") == "mine\n"


def test_a_second_scaffold_writes_nothing(tmp_path: Path) -> None:
    """Idempotent: everything now exists."""
    root = _repo(tmp_path)
    templates = _templates(tmp_path)
    scaffold.scaffold(root, templates, _VERSION)
    wrote, left = scaffold.scaffold(root, templates, _VERSION)
    assert not wrote
    assert len(left) == _THREE


def test_the_hook_is_not_swapped_without_a_build_file(tmp_path: Path) -> None:
    """There is no //:precommit to run yet, so the reason says to write it first."""
    root = _repo(tmp_path)
    reason = scaffold.install_hook(root, _templates(tmp_path), target_passed=True)
    assert "no BUILD.bazel" in reason
    assert not (root / ".githooks" / "pre-commit").exists()


def test_the_hook_is_not_swapped_until_the_target_passed(tmp_path: Path) -> None:
    """The caller's word that //:precommit passed is required."""
    root = _repo(tmp_path)
    (root / "BUILD.bazel").write_text("", encoding="utf-8")
    reason = scaffold.install_hook(root, _templates(tmp_path), target_passed=False)
    assert "NOT swapped" in reason
    assert not (root / ".githooks" / "pre-commit").exists()


def test_the_hook_is_swapped_once_the_target_passed(tmp_path: Path) -> None:
    """The bazel template is written to `.githooks/pre-commit` with the repo name filled in."""
    root = _repo(tmp_path)
    (root / "BUILD.bazel").write_text("", encoding="utf-8")
    assert not scaffold.install_hook(root, _templates(tmp_path), target_passed=True)
    text = (root / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    assert text == "exec bazel test //:precommit # proj\n"
