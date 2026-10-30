# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""An undeclared linked-worktree submit is refused naming the main repo, and leaves a mark (W2103).

⚑ THE GIT DIR SHAPES ARE THE MEASURED ONES: a main checkout's is `<repo>/.git`, a linked
worktree's `<repo>/.git/worktrees/<name>` (github-8f's toy run, where the second queue appeared).
"""

from pathlib import Path

from mikemol.hooks import worktree_submit

_STAMP = "2026-10-30T18:30:00Z"


def _dirs(tmp_path: Path) -> tuple[Path, Path]:
    main = tmp_path / "repo" / ".git"
    return main, main / "worktrees" / "toy-W2"


def test_a_worktrees_git_dir_names_its_main_and_any_other_shape_names_none(tmp_path: Path) -> None:
    """`<main>/.git/worktrees/<name>` has a main; a main checkout's `.git` and a bare dir do not."""
    main, worktree = _dirs(tmp_path)
    assert worktree_submit.main_git_dir(worktree) == main
    assert worktree_submit.main_git_dir(main) is None
    assert worktree_submit.main_git_dir(tmp_path / "bare.git") is None


def test_an_undeclared_worktree_submit_is_refused_naming_the_main_repo_and_the_card(
    tmp_path: Path,
) -> None:
    """The witness: the refusal names the main repository's directory and W2103."""
    main, worktree = _dirs(tmp_path)
    text = worktree_submit.refusal("toy-W2", worktree)
    assert text is not None
    assert text.startswith("NOT COMMITTED: toy-W2 is a linked worktree of")
    assert str(main.parent) in text
    assert "W2103" in text
    assert worktree_submit.refusal("repo", main) is None


def test_a_mode_is_admitted_only_from_the_closed_declared_list(tmp_path: Path) -> None:
    """Today the list is empty, so a named mode does not lift the refusal."""
    worktree = _dirs(tmp_path)[1]
    assert worktree_submit.DECLARED_MODES == ()
    assert worktree_submit.refusal("toy-W2", worktree, "per-branch") is not None


def test_every_worktree_submit_leaves_a_line_in_the_main_repositorys_log(tmp_path: Path) -> None:
    """The mark goes to `<main>/.git/mtools`, which `git worktree remove` does not delete."""
    main, worktree = _dirs(tmp_path)
    made = worktree_submit.record(_STAMP, "toy-W2", worktree, worktree_submit.REFUSED)
    assert made is not None
    path, line = made
    assert path == main / "mtools" / worktree_submit.LOG_NAME
    assert line == f"{_STAMP} refused toy-W2 {worktree}\n"
    worktree_submit.append(path, line)
    worktree_submit.append(path, line)
    assert path.read_text(encoding="utf-8") == line * 2
    assert worktree_submit.record(_STAMP, "repo", main, "declared") is None
