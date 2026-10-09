# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `write_atomic`: the path is replaced, permissions survive, no temp stays."""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

import pytest

from mikemol.atomicwrite import durable

_PRESERVED_MODE = 0o640
_UMASK = 0o027
_EXPECTED_NEW_MODE = 0o640  # 0o666 with _UMASK applied


def _mode(path: Path) -> int:
    """Return the permission bits of `path`.

    Returns:
        The mode with the file-type bits stripped.

    """
    return stat.S_IMODE(path.stat().st_mode)


def test_text_is_written_to_a_new_path(tmp_path: Path) -> None:
    """Text data lands as its content."""
    target = tmp_path / "out.txt"
    durable.write_atomic(target, "hello")
    assert target.read_text(encoding="utf-8") == "hello"


def test_bytes_are_written_to_a_new_path(tmp_path: Path) -> None:
    """Bytes data lands byte for byte, including bytes that are not text."""
    target = tmp_path / "out.bin"
    durable.write_atomic(target, b"\x00\xff\x10")
    assert target.read_bytes() == b"\x00\xff\x10"


def test_an_existing_file_is_overwritten(tmp_path: Path) -> None:
    """A second write replaces the first, with no remnant of the longer old content."""
    target = tmp_path / "out.txt"
    target.write_text("a much longer old content", encoding="utf-8")
    durable.write_atomic(target, "new")
    assert target.read_text(encoding="utf-8") == "new"


def test_a_hardlinked_twin_keeps_its_old_bytes(tmp_path: Path) -> None:
    """The rename breaks the alias: the path gets the new bytes, the twin keeps the old."""
    target = tmp_path / "target.txt"
    twin = tmp_path / "twin.txt"
    target.write_text("old", encoding="utf-8")
    os.link(target, twin)
    durable.write_atomic(target, "new")
    assert target.read_text(encoding="utf-8") == "new"
    assert twin.read_text(encoding="utf-8") == "old"
    assert target.stat().st_ino != twin.stat().st_ino


def test_an_existing_files_mode_is_preserved(tmp_path: Path) -> None:
    """The temp is born at 0600; the write must not narrow the target's permissions."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")
    target.chmod(_PRESERVED_MODE)
    durable.write_atomic(target, "new")
    assert _mode(target) == _PRESERVED_MODE


def test_a_new_file_gets_the_umask_default_and_the_umask_is_left_as_found(tmp_path: Path) -> None:
    """A file that did not exist is created at 0666 minus the process umask."""
    target = tmp_path / "out.txt"
    previous = os.umask(_UMASK)
    try:
        durable.write_atomic(target, "new")
        after = os.umask(_UMASK)
    finally:
        os.umask(previous)
    assert after == _UMASK
    assert _mode(target) == _EXPECTED_NEW_MODE


@pytest.mark.parametrize("data", ["new", b"new"])
def test_the_temp_is_flushed_to_disk_before_it_replaces_the_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data: str | bytes
) -> None:
    """The fsync happens once, on the temp, while the target still holds its old content."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")
    seen: list[str] = []
    real = os.fsync

    def recording(fd: int) -> None:
        seen.append(target.read_text(encoding="utf-8"))
        real(fd)

    monkeypatch.setattr(os, "fsync", recording)
    durable.write_atomic(target, data)
    assert seen == ["old"]
    assert target.read_text(encoding="utf-8") == "new"


def test_a_failed_write_leaves_no_temp_and_reraises(tmp_path: Path) -> None:
    """A rename that cannot happen (the target is a directory) removes the temp and raises."""
    target = tmp_path / "occupied"
    target.mkdir()
    with pytest.raises(OSError, match="directory"):
        durable.write_atomic(target, "new")
    assert [p.name for p in tmp_path.iterdir()] == ["occupied"]


def test_the_temp_is_a_sibling_in_the_targets_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The temp is made beside the target, since rename cannot cross filesystems."""
    seen: list[str] = []
    real = tempfile.mkstemp

    def spy(**kwargs: str) -> tuple[int, str]:
        fd, name = real(dir=kwargs["dir"], prefix=kwargs["prefix"], suffix=kwargs["suffix"])
        seen.append(name)
        return fd, name

    monkeypatch.setattr(tempfile, "mkstemp", spy)
    sub = tmp_path / "sub"
    sub.mkdir()
    durable.write_atomic(sub / "out.txt", "x")
    assert len(seen) == 1
    assert Path(seen[0]).parent == sub
