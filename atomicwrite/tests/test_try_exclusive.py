# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `flock.try_exclusive`: a held lock is an answer, never a wait (mtools:W1383).

⚑ THE CONTROLS ARE THE TWO WAYS A NON-BLOCKING LOCK GOES WRONG: it waits behind a holder (this test
would then never return), and it releases a lock it did not take (the real holder would be freed
under it). Both are read through a second descriptor on the same path.
"""

from __future__ import annotations

import fcntl
from typing import TYPE_CHECKING

from mikemol.atomicwrite import flock

if TYPE_CHECKING:
    from pathlib import Path


def _refused(path: Path) -> bool:
    # Whether a fresh descriptor on `path` is refused a non-blocking exclusive lock.
    with path.open("ab") as probe:
        try:
            fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(probe.fileno(), fcntl.LOCK_UN)
    return False


def test_a_free_lock_is_taken_held_inside_the_body_and_released_after(tmp_path: Path) -> None:
    """True inside, another descriptor refused inside, free again after."""
    target = tmp_path / "x.lock"
    with flock.try_exclusive(target) as took:
        assert took
        assert _refused(target)
    assert not _refused(target)


def test_a_held_lock_yields_false_without_waiting(tmp_path: Path) -> None:
    """With another holder the call returns False at once; reaching the assert proves no wait."""
    target = tmp_path / "x.lock"
    with flock.exclusive(target), flock.try_exclusive(target) as took:
        assert not took


def test_a_refused_attempt_does_not_release_the_holders_lock(tmp_path: Path) -> None:
    """The holder keeps the lock after a refused try_exclusive body ends."""
    target = tmp_path / "x.lock"
    with flock.exclusive(target):
        with flock.try_exclusive(target) as took:
            assert not took
        assert _refused(target)


def test_the_file_is_created_when_absent(tmp_path: Path) -> None:
    """A path that does not exist is created, so a caller needs no setup."""
    target = tmp_path / "new.lock"
    with flock.try_exclusive(target):
        assert target.exists()
