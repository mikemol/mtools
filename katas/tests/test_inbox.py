# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `inbox.archive`: handled letters move aside and are never overwritten (W876)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.katas import inbox

if TYPE_CHECKING:
    from pathlib import Path

_TWO = 2


def _letter(directory: Path, name: str, text: str = "hi\n") -> None:
    """Write a letter into `directory`."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(text, encoding="utf-8")


def test_named_letters_move_into_the_archive(tmp_path: Path) -> None:
    """Each named letter leaves the inbox and appears under `archive/`, contents intact."""
    _letter(tmp_path, "a.md", "one\n")
    _letter(tmp_path, "b.md", "two\n")
    got = inbox.archive(tmp_path, ["a.md", "b.md"])
    assert got.moved == _TWO
    assert not (tmp_path / "a.md").exists()
    assert (tmp_path / "archive" / "a.md").read_text(encoding="utf-8") == "one\n"


def test_the_archive_directory_is_created_when_absent(tmp_path: Path) -> None:
    """The first archive call makes `inbox/archive`."""
    _letter(tmp_path, "a.md")
    inbox.archive(tmp_path, ["a.md"])
    assert (tmp_path / "archive").is_dir()


def test_a_missing_letter_is_reported_not_raised(tmp_path: Path) -> None:
    """A name that is not in the inbox is named in the result, and the others still move."""
    _letter(tmp_path, "a.md")
    got = inbox.archive(tmp_path, ["a.md", "gone.md"])
    assert got.moved == 1
    assert got.missing == ["gone.md"]


def test_a_path_is_cut_to_its_file_name(tmp_path: Path) -> None:
    """A name cannot reach outside the inbox: only its last part is used."""
    _letter(tmp_path, "a.md")
    outside = tmp_path.parent / "elsewhere.md"
    outside.write_text("keep\n", encoding="utf-8")
    got = inbox.archive(tmp_path, ["../elsewhere.md", "sub/a.md"])
    assert outside.read_text(encoding="utf-8") == "keep\n"
    assert got.missing == ["elsewhere.md"]
    assert got.moved == 1


def test_an_already_archived_name_is_never_overwritten(tmp_path: Path) -> None:
    """The first archived letter survives a second one with the same name."""
    _letter(tmp_path / "archive", "a.md", "first\n")
    _letter(tmp_path, "a.md", "second\n")
    got = inbox.archive(tmp_path, ["a.md"])
    assert got.moved == 0
    assert got.clashing == ["a.md"]
    assert (tmp_path / "archive" / "a.md").read_text(encoding="utf-8") == "first\n"
    assert (tmp_path / "a.md").read_text(encoding="utf-8") == "second\n"
