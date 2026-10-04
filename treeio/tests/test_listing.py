# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `listing`: the two matchers, their disagreement, and the refusal that names it."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygit2
import pytest

from mikemol.treeio.listing import (
    LISTDIR_ORDER,
    AmbiguousPattern,
    AmbiguousPatternError,
    ambiguous_across_sources,
    listdir,
    suffixed,
)
from mikemol.treeio.sources import Rev, WorkingTree

if TYPE_CHECKING:
    from pathlib import Path

_FILES = {
    "d/top.agda": b"x",
    "d/sub/mid.agda": b"x",
    "d/sub/deep/low.agda": b"x",
    "d/sub/other.txt": b"x",
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


def _corpus(root: Path) -> tuple[WorkingTree, Rev]:
    """Commit the corpus and also lay it out on disk, so both sources hold the same files.

    Returns:
        The working tree and the HEAD revision over the same directory.

    """
    repo = pygit2.init_repository(str(root), initial_head="main")
    who = pygit2.Signature("t", "t@t")
    repo.create_commit("HEAD", who, who, "t", _tree(repo, _FILES), [])
    for rel, data in _FILES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    return WorkingTree(root), Rev("HEAD", root)


def _disk_files(tree: WorkingTree, pattern: str) -> list[str]:
    """List only the regular files a working-tree listing returned.

    Returns:
        The matching paths that are files, since git holds blobs only.

    """
    return [p for p in listdir(pattern, tree, strict=False) if (tree.root / p).is_file()]


def test_a_glued_double_star_is_ambiguous_and_named() -> None:
    """A double star fused into a segment is a plain star to glob and nothing to fnmatch."""
    reason = ambiguous_across_sources("d/x**/y")
    assert reason is not None
    assert reason.startswith("`x**` — `**` is only a segment wildcard when it is a WHOLE segment")


def test_a_double_star_followed_by_more_is_ambiguous_and_names_the_successor() -> None:
    """The lossy form refuses and names the depth-agnostic spelling that means one thing."""
    reason = ambiguous_across_sources("d/**/*.agda")
    assert reason is not None
    assert "Use the depth-agnostic `d/**` (+ `--suffix`)" in reason
    assert "/**" in reason


def test_a_star_across_segments_is_ambiguous_and_names_the_successor() -> None:
    """A bare star crosses a slash under fnmatch only, so a multi-segment pattern is refused."""
    reason = ambiguous_across_sources("d/*.agda")
    assert reason is not None
    assert "selects one depth on disk and every depth at a revision" in reason
    assert "Use `d/**` (+ `--suffix`)" in reason
    assert "`d/*.agda`" in reason


def test_patterns_both_matchers_agree_on_are_not_refused() -> None:
    """An exact path, a trailing double star, and a single-segment star all pass."""
    assert ambiguous_across_sources("d/top.agda") is None
    assert ambiguous_across_sources("d/**") is None
    assert ambiguous_across_sources("**") is None
    assert ambiguous_across_sources("*.md") is None
    assert ambiguous_across_sources("") is None


def test_the_refusal_is_a_value_error_with_a_compatible_alias() -> None:
    """The renamed error is a ValueError and the old paperkit spelling is the same class."""
    assert issubclass(AmbiguousPatternError, ValueError)
    assert AmbiguousPattern is AmbiguousPatternError


def test_listdir_refuses_an_ambiguous_pattern_at_both_sources_naming_it(tmp_path: Path) -> None:
    """The refusal fires on the working tree too, where the pattern happens to be exact."""
    tree, head = _corpus(tmp_path)
    for source in (tree, head):
        with pytest.raises(AmbiguousPatternError) as caught:
            listdir("d/**/*.agda", source)
        message = str(caught.value)
        assert message.startswith(
            "pattern 'd/**/*.agda' means different things at a WorkingTree and at a Rev: "
        )
        assert "Use the depth-agnostic `d/**`" in message


def test_listdir_accepts_the_agreeing_form_and_returns_sorted_paths(tmp_path: Path) -> None:
    """The depth-agnostic form is not refused, and a revision lists only blobs, sorted."""
    _, head = _corpus(tmp_path)
    assert listdir("d/**", head) == [
        "d/sub/deep/low.agda",
        "d/sub/mid.agda",
        "d/sub/other.txt",
        "d/top.agda",
    ]


def test_a_working_tree_listing_includes_directories_and_is_sorted(tmp_path: Path) -> None:
    """The working-tree branch wraps glob, which also returns the directories it walked."""
    tree, _ = _corpus(tmp_path)
    got = listdir("d/**", tree)
    assert got == sorted(got)
    assert "d/sub" in got
    assert "d/sub/deep/low.agda" in got


def test_every_accepted_pattern_selects_the_same_files_at_both_sources(tmp_path: Path) -> None:
    """The invariant is a relation between the branches, not a pinned listing."""
    tree, head = _corpus(tmp_path)
    for pattern in ("d/**", "d/sub/**", "**", "d/sub/other.txt", "d/top.agda"):
        assert ambiguous_across_sources(pattern) is None
        assert _disk_files(tree, pattern) == listdir(pattern, head)


def test_the_comparison_reports_a_real_divergence_for_a_refused_pattern(tmp_path: Path) -> None:
    """The positive control: where the branches disagree, the same comparison goes red."""
    tree, head = _corpus(tmp_path)
    disk = set(_disk_files(tree, "d/*.agda"))
    rev = set(listdir("d/*.agda", head, strict=False))
    assert sorted(disk ^ rev) == ["d/sub/deep/low.agda", "d/sub/mid.agda"]


def test_the_lossy_form_at_a_revision_drops_exactly_the_depth_zero_members(tmp_path: Path) -> None:
    """The six-module drop in miniature: a double star followed by a suffix misses depth 0."""
    tree, head = _corpus(tmp_path)
    lossy = set(listdir("d/**/*.agda", head, strict=False))
    full = set(suffixed(listdir("d/**", head), ".agda"))
    assert sorted(full - lossy) == ["d/top.agda"]
    assert "d/top.agda" in listdir("d/**/*.agda", tree, strict=False)


def test_a_broken_revision_raises_instead_of_listing_nothing(tmp_path: Path) -> None:
    """An empty list from a bad revision would read as no matches, so it raises."""
    _corpus(tmp_path)
    with pytest.raises(ValueError, match="bad revision"):
        listdir("d/**", Rev("nosuchrev-zzz-9999", tmp_path))


def test_the_default_source_is_the_working_tree_at_the_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no source the listing happens where the process is standing."""
    _corpus(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert "d/top.agda" in listdir("d/**")


def test_listdir_order_is_named() -> None:
    """The order is a constant a caller can cite instead of an incident of a sort call."""
    assert LISTDIR_ORDER == "path-lexicographic, repo-relative, forward-slashed"


def test_suffixed_filters_by_ending_and_an_empty_suffix_keeps_everything() -> None:
    """A suffix keeps matching endings; an empty one is a no-op, and a miss reports none."""
    paths = ["a.agda", "b.txt", "c/d.agda"]
    assert suffixed(paths, ".agda") == ["a.agda", "c/d.agda"]
    assert suffixed(paths, "") == paths
    assert suffixed(iter(paths), "") == paths
    assert suffixed(paths, ".nosuchext") == []
