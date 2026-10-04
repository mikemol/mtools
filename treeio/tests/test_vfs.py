# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `vfs`: the old one-module surface re-exports the split modules' own objects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.treeio import census, listing, presence, read, result, sources, vfs, write

if TYPE_CHECKING:
    from pathlib import Path

_EXPORTED = [
    "AmbiguousPattern",
    "AmbiguousPatternError",
    "LISTDIR_ORDER",
    "Presence",
    "Result",
    "Rev",
    "WorkingTree",
    "ambiguous_across_sources",
    "census",
    "compare",
    "listdir",
    "read",
    "read_text",
    "suffixed",
    "write",
]


def test_every_exported_name_is_the_split_modules_own_object() -> None:
    """A repointed caller gets the very objects, not copies, so isinstance checks agree."""
    assert vfs.Presence is presence.Presence
    assert vfs.Result is result.Result
    assert vfs.Rev is sources.Rev
    assert vfs.WorkingTree is sources.WorkingTree
    assert vfs.read is read.read
    assert vfs.read_text is read.read_text
    assert vfs.write is write.write
    assert vfs.listdir is listing.listdir
    assert vfs.suffixed is listing.suffixed
    assert vfs.ambiguous_across_sources is listing.ambiguous_across_sources
    assert vfs.AmbiguousPattern is listing.AmbiguousPatternError
    assert vfs.AmbiguousPatternError is listing.AmbiguousPatternError
    assert vfs.LISTDIR_ORDER is listing.LISTDIR_ORDER
    assert vfs.census is census.census
    assert vfs.compare is census.compare


def test_all_lists_exactly_the_exported_names_and_omits_dry_run() -> None:
    """The public surface is the list, and DRY_RUN is absent so it cannot be assigned here."""
    assert sorted(vfs.__all__) == sorted(_EXPORTED)
    assert not hasattr(vfs, "DRY_RUN")


def test_the_old_call_shape_works_end_to_end(tmp_path: Path) -> None:
    """Write through the facade and read it back with the three-valued verdict."""
    tree = vfs.WorkingTree(tmp_path)
    vfs.write("a.txt", "café", tree)
    found = vfs.read("a.txt", tree)
    assert found.presence is vfs.Presence.PRESENT
    assert found.text() == "café"
    assert vfs.read("gone.txt", tree).presence is vfs.Presence.ABSENT
