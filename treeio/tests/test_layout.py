# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `layout`: where the journal and the untracked-copy store live under a root."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.treeio.layout import Layout, layout

if TYPE_CHECKING:
    import pytest


def test_the_journal_and_the_store_live_under_the_roots_scratch_directory(tmp_path: Path) -> None:
    """Both places are fixed relative to the root, so a root names the whole layout."""
    here = Layout(tmp_path)
    assert here.journal == tmp_path / "scratch" / "edit_snapshot.journal.tsv"
    assert here.snapdir == tmp_path / "scratch" / ".edit-snapshots"


def test_rel_relativises_an_absolute_path_and_leaves_a_relative_one_alone(tmp_path: Path) -> None:
    """A path under the root is spelled relative to it; one already relative is untouched."""
    here = Layout(tmp_path)
    assert here.rel(tmp_path / "a" / "b.agda") == "a/b.agda"
    assert here.rel("a/b.agda") == "a/b.agda"
    assert here.rel(Path("a") / "b.agda") == "a/b.agda"
    assert here.rel("/etc/hosts").startswith("..")


def test_layout_makes_the_root_absolute(tmp_path: Path) -> None:
    """A named root is made absolute, so a relative root cannot drift with the cwd."""
    assert layout(tmp_path).root == tmp_path
    assert layout("relative-root").root.is_absolute()


def test_layout_defaults_to_the_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a root the layout is wherever the process is standing."""
    monkeypatch.chdir(tmp_path)
    assert layout().root == tmp_path.resolve()


def test_a_layout_is_a_value() -> None:
    """Two layouts over one root are equal and hashable, so one can key a cache."""
    assert Layout(Path("/r")) == Layout(Path("/r"))
    assert len({Layout(Path("/r")), Layout(Path("/r")), Layout(Path("/s"))}) == len(("r", "s"))
