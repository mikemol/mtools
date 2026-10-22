# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Following a file is the batch pass repeated on a change, never on elapsed time (W1817).

⚑ THE QUIET FILE IS THE NEGATIVE CONTROL: with nothing appended the loop must sample and not pass,
so a loop that passes on every pause (a timer in disguise) fails the first arm below.

⚑ EVERY PAUSE IS BOUNDED BY A COUNT, NOT A CLOCK: a broken loop that never passes again would wait
forever, so `_Run.pause` raises once it has been asked more times than any arm needs. A mutant of
the loop then fails fast instead of hanging.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from mikemol.hooks import vlogfollow

_PASSES_WANTED = 2
_QUIET_PAUSES = 5
_MOST_PAUSES = 50


class _Run:
    """A recorded run: the passes made and the pauses taken, with an action on the pauses."""

    def __init__(self, on_pause: Callable[["_Run"], None] | None = None) -> None:
        self.passes = 0
        self.pauses = 0
        self.on_pause = on_pause

    def step(self) -> bool:
        self.passes += 1
        return False

    def pause(self) -> None:
        self.pauses += 1
        if self.pauses > _MOST_PAUSES:
            pytest.fail("the loop kept pausing and never passed again")
        if self.on_pause is not None:
            self.on_pause(self)


def test_a_quiet_file_is_sampled_and_never_passed_again(tmp_path: Path) -> None:
    """One pass at the start, then only pauses while the file does not change."""
    path = tmp_path / "app.log"
    path.write_text("one\n", encoding="utf-8")
    run = _Run()
    got = vlogfollow.follow(run.step, path, run.pause, lambda: run.pauses >= _QUIET_PAUSES)
    assert got == 1
    assert run.pauses == _QUIET_PAUSES


def test_an_append_makes_the_next_pass_and_only_then(tmp_path: Path) -> None:
    """The file grows during a pause; the loop passes again after that pause, not before."""
    path = tmp_path / "app.log"
    path.write_text("one\n", encoding="utf-8")

    def append_on_fifth(run: _Run) -> None:
        if run.pauses == _QUIET_PAUSES:
            with path.open("a", encoding="utf-8") as handle:
                handle.write("two\n")

    run = _Run(append_on_fifth)
    got = vlogfollow.follow(run.step, path, run.pause, lambda: run.passes >= _PASSES_WANTED)
    assert got == _PASSES_WANTED
    assert run.pauses == _QUIET_PAUSES


def test_a_rotation_to_a_file_of_the_same_size_is_a_change(tmp_path: Path) -> None:
    """A new inode is a change even when the size is the same: rotation restarts the read."""
    path = tmp_path / "app.log"
    path.write_text("aaa\n", encoding="utf-8")

    def rotate(_run: _Run) -> None:
        fresh = tmp_path / "fresh.log"
        fresh.write_text("bbb\n", encoding="utf-8")
        fresh.replace(path)

    run = _Run(rotate)
    got = vlogfollow.follow(run.step, path, run.pause, lambda: run.passes >= _PASSES_WANTED)
    assert got == _PASSES_WANTED


def test_a_missing_file_waits_and_passes_when_it_returns(tmp_path: Path) -> None:
    """Between a rotation's rename and its recreation there is no file; that is a signature too."""
    path = tmp_path / "app.log"

    def appear_on_fifth(run: _Run) -> None:
        if run.pauses == _QUIET_PAUSES:
            path.write_text("late\n", encoding="utf-8")

    run = _Run(appear_on_fifth)
    got = vlogfollow.follow(run.step, path, run.pause, lambda: run.passes >= _PASSES_WANTED)
    assert got == _PASSES_WANTED
    assert run.pauses == _QUIET_PAUSES


def test_a_held_pass_pauses_and_passes_again_without_the_file_changing(tmp_path: Path) -> None:
    """The spool at its ceiling leaves lines in a file that may never change: pass again."""
    path = tmp_path / "app.log"
    path.write_text("one\n", encoding="utf-8")
    run = _Run()

    def held_once() -> bool:
        run.passes += 1
        return run.passes < _PASSES_WANTED

    got = vlogfollow.follow(held_once, path, run.pause, lambda: run.passes >= _PASSES_WANTED)
    assert got == _PASSES_WANTED
    assert run.pauses == 1


def test_the_signature_is_none_for_a_missing_file_and_inode_and_size_otherwise(
    tmp_path: Path,
) -> None:
    """The positive control for the reader the loop rests on."""
    path = tmp_path / "app.log"
    assert vlogfollow.signature(path) is None
    path.write_text("abc\n", encoding="utf-8")
    seen = vlogfollow.signature(path)
    assert seen is not None
    assert seen[1] == len("abc\n")
    assert vlogfollow.never() is False
