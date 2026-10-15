# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `flock.exclusive`: the lock is real, is released on exit and on an error."""

from __future__ import annotations

import fcntl
from typing import TYPE_CHECKING

import pytest

from mikemol.atomicwrite import flock

if TYPE_CHECKING:
    from pathlib import Path


def _held_elsewhere(path: Path) -> bool:
    """Say whether another descriptor on `path` is refused a non-blocking exclusive lock.

    Returns:
        True when the lock is held, False when this probe could take (and then drop) it.

    """
    with path.open("ab") as probe:
        try:
            fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(probe.fileno(), fcntl.LOCK_UN)
    return False


def _fail_inside(path: Path) -> None:
    """Hold the lock and raise, as a body that fails would.

    Raises:
        RuntimeError: always, with the lock held.

    """
    with flock.exclusive(path):
        raise RuntimeError


def test_the_lock_is_held_inside_the_body_and_released_after(tmp_path: Path) -> None:
    """A second descriptor is refused inside the body and succeeds once the body ends."""
    target = tmp_path / "x.lock"
    assert not _held_elsewhere(target)
    with flock.exclusive(target):
        assert _held_elsewhere(target)
    assert not _held_elsewhere(target)


def test_the_lock_is_released_when_the_body_raises(tmp_path: Path) -> None:
    """The control for the release path: an error in the body still frees the lock."""
    target = tmp_path / "x.lock"
    with pytest.raises(RuntimeError):
        _fail_inside(target)
    assert not _held_elsewhere(target)


def test_the_file_is_created_when_absent(tmp_path: Path) -> None:
    """A path that does not exist is created, so a caller needs no setup."""
    target = tmp_path / "new.lock"
    assert not target.exists()
    with flock.exclusive(target):
        assert target.exists()
