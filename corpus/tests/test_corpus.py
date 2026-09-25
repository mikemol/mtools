# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.corpus.corpus`: substrate's `corpus_selftest` arms, plus the root arm.

Every tree is SYNTHETIC, built in tmp_path, so no arm depends on any real checkout.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.corpus import corpus

if TYPE_CHECKING:
    from collections.abc import Callable

# Paths that merely CONTAIN a skip word and must survive component matching.
_KEEP = ("rebuild", "buildtools", "prebuild/inner")

# Paths that are genuinely generated output or vendored code.
_DROP = (
    "build",
    "dist/wheel",
    "a/__pycache__/b",
    "bazel-bin",
    "bazel-substrate",
    ".venv/lib",
    "x/site-packages/y",
)


def _tree(root: Path) -> Path:
    """Build a small synthetic repo: real sources, a generated tree, a skipped tree.

    Returns:
        the tree's root.

    """
    for rel in (
        "src/pkg/mod.py",
        "src/pkg/other.py",
        "tests/test_x.py",
        "build/lib/copy.py",
        "bazel-bin/gen.py",
        "agda/tool.py",
        ".hidden/h.py",
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    return root


def test_the_root_has_no_default_anywhere() -> None:
    """No walker defaults its root, and the module holds no `ROOT` to default to.

    ⚑⚑ substrate's `ROOT = Path(__file__).absolute().parent.parent` is its repo root in place and
    the venv's lib directory once installed, so its 173 importers would have censused
    site-packages with no error. Here, a walker called without a root refuses at the call.
    """
    assert not hasattr(corpus, "ROOT")
    for walker in (corpus.roots, corpus.py_files):
        with pytest.raises(TypeError, match="root"):
            cast("Callable[[], object]", walker)()
    with pytest.raises(TypeError, match="root"):
        cast("Callable[[str], object]", corpus.resolve_root)("src")


def test_an_unresolvable_root_raises_naming_the_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A path neither the current directory nor the root has raises, naming what was asked.

    ⚑ Silently returning the default corpus is the bug: a peer nearly published substrate's
    census as their own repo's.
    """
    monkeypatch.chdir(tmp_path)
    with pytest.raises(corpus.PopulationError, match="no-such-directory-anywhere"):
        corpus.resolve_root("no-such-directory-anywhere", root=tmp_path)


def test_exclusion_matches_whole_components_never_substrings() -> None:
    """`rebuild/` and `buildtools/` stay in; `build/`, caches, venvs and bazel links are out."""
    assert [keep for keep in _KEEP if corpus.excluded(Path(keep))] == []
    assert [drop for drop in _DROP if not corpus.excluded(Path(drop))] == []


def test_root_discovery_uses_the_walk_vocabulary_and_the_caller_skip(tmp_path: Path) -> None:
    """Generated, hidden and caller-skipped top-level trees are not discovered as roots.

    ⚑ A generated tree that is a TOP-LEVEL entry becomes its own root, so the component check
    below it never sees its name. And `agda` is substrate's policy, passed as `skip`.
    """
    root = _tree(tmp_path)
    assert corpus.roots(root=root, skip=("agda",)) == ("src", "tests")
    assert "agda" in corpus.roots(root=root)


def test_the_walk_of_a_real_tree_is_not_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Walking a tree with sources returns at least one file: the positive control.

    ⚑ Every exclusion returns FEWER files, and an over-eager one returns zero, which reads as a
    clean tree. The empty list passes sortedness vacuously, so this arm keeps the next two honest.
    """
    monkeypatch.chdir(tmp_path)
    assert corpus.py_files(root=_tree(tmp_path), skip=("agda",))


def test_the_population_is_returned_sorted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`py_files` hands its population back in sorted order, so a caller can cite it."""
    monkeypatch.chdir(tmp_path)
    got = corpus.py_files(root=_tree(tmp_path), skip=("agda",))
    assert got == sorted(got)


def test_the_walk_finds_real_sources_and_omits_generated_copies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A named source file is in the population; generated and skipped copies are not.

    ⚑ A named member is what separates a walk from a list: non-emptiness says the walk returned
    something, membership says it returned the right something.
    """
    monkeypatch.chdir(tmp_path)
    got = {
        Path(p).relative_to(tmp_path).as_posix()
        for p in corpus.py_files(root=_tree(tmp_path), skip=("agda",))
    }
    assert got == {"src/pkg/mod.py", "src/pkg/other.py", "tests/test_x.py"}
