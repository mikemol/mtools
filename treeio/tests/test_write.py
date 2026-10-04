# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `write`: atomic UTF-8 writes to the working tree, and the refusals around them."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

from mikemol.treeio import write as write_module
from mikemol.treeio.read import read
from mikemol.treeio.sources import Rev, WorkingTree
from mikemol.treeio.write import declare, write

if TYPE_CHECKING:
    from pathlib import Path

_AGDA_ISH = "rc = F2.\U0001d7d9 ∷ F2.\U0001d7d8 ∷ []\n"


def _leftovers(root: Path) -> list[str]:
    """List any temp file the atomic write left behind.

    Returns:
        The names containing the temp marker.

    """
    return [p.name for p in root.iterdir() if ".vfs-tmp" in p.name]


def test_text_is_written_as_utf8_on_the_wire_and_round_trips(tmp_path: Path) -> None:
    """The bytes on disk are UTF-8 whatever the locale, and the count is of bytes."""
    tree = WorkingTree(tmp_path)
    count = write("uni.agda", _AGDA_ISH, tree)
    assert count == len(_AGDA_ISH.encode("utf-8"))
    assert (tmp_path / "uni.agda").read_bytes() == _AGDA_ISH.encode("utf-8")
    assert read("uni.agda", tree).text() == _AGDA_ISH


def test_bytes_and_bytearrays_are_written_as_given(tmp_path: Path) -> None:
    """Raw bytes pass through untouched, including bytes that are not UTF-8."""
    tree = WorkingTree(tmp_path)
    assert write("b.bin", b"\xff\xfe", tree) == len(b"\xff\xfe")
    assert write("c.bin", bytearray(b"abc"), tree) == len(b"abc")
    assert (tmp_path / "b.bin").read_bytes() == b"\xff\xfe"
    assert (tmp_path / "c.bin").read_bytes() == b"abc"


def test_a_write_over_an_existing_file_replaces_its_content(tmp_path: Path) -> None:
    """The new content wins whole: no truncation window, no leftover tail of the old file."""
    (tmp_path / "f.txt").write_text("a long original body", encoding="utf-8")
    write("f.txt", "new", WorkingTree(tmp_path))
    assert (tmp_path / "f.txt").read_text(encoding="utf-8") == "new"


def test_a_successful_write_leaves_no_temp_file(tmp_path: Path) -> None:
    """The sibling temp is renamed away, so nothing carrying the temp marker survives."""
    write("f.txt", "x", WorkingTree(tmp_path))
    assert _leftovers(tmp_path) == []


def test_a_failed_write_removes_its_temp_and_raises_the_original_error(tmp_path: Path) -> None:
    """A rename onto a directory fails; the temp is cleaned up and the OS error propagates."""
    (tmp_path / "d").mkdir()
    with pytest.raises(IsADirectoryError):
        write("d", "x", WorkingTree(tmp_path))
    assert _leftovers(tmp_path) == []
    assert (tmp_path / "d").is_dir()


def test_mkdirs_creates_the_parents_and_its_absence_refuses(tmp_path: Path) -> None:
    """Without mkdirs a missing directory is an error; with it the parents are made."""
    tree = WorkingTree(tmp_path)
    with pytest.raises(FileNotFoundError):
        write("sub/deep/f.txt", "x", tree)
    write("sub/deep/f.txt", "x", tree, mkdirs=True)
    assert (tmp_path / "sub" / "deep" / "f.txt").read_text(encoding="utf-8") == "x"
    write("sub/deep/g.txt", "y", tree, mkdirs=True)
    assert (tmp_path / "sub" / "deep" / "g.txt").read_text(encoding="utf-8") == "y"


def test_an_absolute_path_is_written_where_it_points(tmp_path: Path) -> None:
    """An absolute path ignores the root, as a read of one does."""
    target = tmp_path / "abs.txt"
    write(target, "x", WorkingTree(tmp_path / "elsewhere"))
    assert target.read_text(encoding="utf-8") == "x"


def test_the_default_source_is_the_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no source the write lands where the process is standing."""
    monkeypatch.chdir(tmp_path)
    write("here.txt", "x")
    assert (tmp_path / "here.txt").read_text(encoding="utf-8") == "x"


def test_a_revision_is_refused_and_the_refusal_names_its_successor(tmp_path: Path) -> None:
    """History is not writable, so the refusal says so and points at committing instead."""
    with pytest.raises(ValueError, match="not writable") as caught:
        write("x.txt", "x", Rev("HEAD", tmp_path))
    message = str(caught.value)
    assert "cannot write to Rev('HEAD')" in message
    assert "there is no write(path, Rev(...))" in message
    assert "commit to the working tree" in message
    assert not (tmp_path / "x.txt").exists()


def test_anything_but_text_or_bytes_is_a_type_error(tmp_path: Path) -> None:
    """An int is refused by name instead of being coerced or failing deep inside the write."""
    with pytest.raises(TypeError) as caught:
        write("x.txt", cast("str", 5), WorkingTree(tmp_path))
    assert str(caught.value) == "write expects str or bytes, got int"
    assert not (tmp_path / "x.txt").exists()


def test_dry_run_refuses_the_write_and_leaves_the_file_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A set DRY_RUN stops the byte-level writer, and clearing it lets writes resume."""
    tree = WorkingTree(tmp_path)
    write("dry.txt", b"applied", tree)
    monkeypatch.setattr(write_module, "DRY_RUN", True)
    with pytest.raises(RuntimeError, match="DRY_RUN is set"):
        write("dry.txt", b"OVERWRITTEN", tree)
    assert read("dry.txt", tree).data == b"applied"
    monkeypatch.setattr(write_module, "DRY_RUN", False)
    write("dry.txt", b"again", tree)
    assert read("dry.txt", tree).data == b"again"


def test_declare_accepts_apply_and_refuses_any_other_intent() -> None:
    """The seam's intent is fixed by its position, so anything but apply is refused by name."""
    declare("apply")
    with pytest.raises(ValueError, match="unknown intent 'mutate'") as caught:
        declare("mutate")
    assert str(caught.value) == "vfs.write: unknown intent 'mutate' (expected 'apply')"
