# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A path the landing deleted leaves no untracked copy in the main tree (luthen W2334)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import isolated, scratch
from mikemol.hooks.commit_kata import run_git_in

if TYPE_CHECKING:
    import pytest

_KEEP = "keep.txt"
_GONE = "gone.txt"
_BYTES = "bytes the old HEAD held\n"


def _git(root: Path, *args: str) -> str:
    """Run the real git and fail loudly.

    Returns:
        git's stdout.

    """
    code, out = scratch.git_out(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t.invalid", *args]
    )
    assert code == 0, out
    return out


def _landed_deletion(root: Path) -> str:
    """Commit two files, then a commit that deletes one; leave the deleted file's bytes behind.

    Returns:
        the sha of the commit before the deletion, the landing's `start`.

    """
    _git(root, "init", "--quiet", "-b", "main")
    (root / _KEEP).write_text("kept\n", encoding="utf-8")
    (root / _GONE).write_text(_BYTES, encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    start = _git(root, "rev-parse", "HEAD").strip()
    _git(root, "rm", "--quiet", _GONE)
    _git(root, "commit", "--quiet", "-m", "delete")
    (root / _GONE).write_text(_BYTES, encoding="utf-8")
    return start


def _says_the_gone_path_is_a_link(path: Path) -> bool:
    return path.name == _GONE


def test_a_deleted_path_whose_leftover_holds_the_old_bytes_is_removed(tmp_path: Path) -> None:
    """Absent at HEAD and equal to what `start` held: nobody edited it, so it goes and is named."""
    start = _landed_deletion(tmp_path)
    said = isolated.refresh_tree(tmp_path, [_GONE], start, run_git_in)
    assert said is not None
    assert _GONE in said
    assert not (tmp_path / _GONE).exists()


def test_a_deleted_path_whose_leftover_was_edited_is_left_and_named(tmp_path: Path) -> None:
    """Absent at HEAD and different from `start`'s bytes: someone's edit, kept and reported."""
    start = _landed_deletion(tmp_path)
    (tmp_path / _GONE).write_text("someone else's work\n", encoding="utf-8")
    said = isolated.refresh_tree(tmp_path, [_GONE], start, run_git_in)
    assert said is not None
    assert f"left for {_GONE}" in said
    assert (tmp_path / _GONE).read_text(encoding="utf-8") == "someone else's work\n"


def test_a_leftover_that_only_a_filter_makes_equal_is_not_removed(tmp_path: Path) -> None:
    """github-14's cold BLOCK of 42b23583: under `text eol=crlf` a CRLF copy is not the old bytes.

    ⚑ WITHOUT `--no-filters` the clean filter folds the carriage returns away and the hash matches
    the deleted LF blob, so the leftover would be unlinked though its bytes are not the landing's.
    """
    start = _landed_deletion(tmp_path)
    (tmp_path / ".gitattributes").write_text("*.txt text eol=crlf\n", encoding="utf-8")
    crlf = _BYTES.replace("\n", "\r\n").encode("utf-8")
    (tmp_path / _GONE).write_bytes(crlf)
    said = isolated.refresh_tree(tmp_path, [_GONE], start, run_git_in)
    assert said is not None
    assert f"left for {_GONE}" in said
    assert (tmp_path / _GONE).read_bytes() == crlf


def test_a_leftover_that_is_a_link_is_never_removed_even_with_the_old_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """github-14's cold BLOCK of 42b23583: `is_file()` follows a link, so a link was unlinked.

    ⚑ NO LINK IS CREATED HERE (the no-symlinks ruling): the path holds the old bytes as a plain file
    and `Path.is_symlink` is made to answer yes for it, which is the only fact the judgement reads.
    The file must survive and be named, never followed.
    """
    start = _landed_deletion(tmp_path)
    monkeypatch.setattr(Path, "is_symlink", _says_the_gone_path_is_a_link)
    said = isolated.refresh_tree(tmp_path, [_GONE], start, run_git_in)
    assert said is not None
    assert f"left for {_GONE}" in said
    assert (tmp_path / _GONE).read_text(encoding="utf-8") == _BYTES


def test_a_path_at_head_and_a_path_gone_from_both_say_nothing(tmp_path: Path) -> None:
    """The ordinary judgement stays: a file equal to HEAD, and one absent everywhere."""
    start = _landed_deletion(tmp_path)
    (tmp_path / _GONE).unlink()
    assert isolated.refresh_tree(tmp_path, [_KEEP, _GONE], start, run_git_in) is None
