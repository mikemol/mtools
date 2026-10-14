# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a wrapped command's status passes through and a file is read once from an offset.

W1178. ⚑ THE PRODUCER'S STATUS IS THE POINT of the wrapper: the command exits 3 and the wrapper must
return 3 while still delivering its lines, which a pipe cannot. ⚑ THE OFFSET CASES ARE ROTATION,
TRUNCATION AND A HALF-WRITTEN LINE: each is a way a tail reads a line twice, loses it, or reads it
cut in two, and each has its own test. ⚑ NOTHING LOOPS OR SLEEPS: a read returns.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.hooks import vlogforms as vf

if TYPE_CHECKING:
    from pathlib import Path

_NOT_STARTED = 127
_THREE = 3


def test_the_wrapper_delivers_every_line_and_returns_the_commands_own_status() -> None:
    """The command prints two lines and exits 3: both arrive in order, and 3 comes back."""
    seen: list[str] = []
    code = vf.run_wrapped(
        [sys.executable, "-c", "print('one'); print('two'); raise SystemExit(3)"], seen.append
    )
    assert seen == ["one\n", "two\n"]
    assert code == _THREE


def test_the_wrapper_returns_zero_for_a_command_that_succeeds() -> None:
    """The control: a clean exit is 0, so 3 above was the command's doing, not the wrapper's."""
    seen: list[str] = []
    assert vf.run_wrapped([sys.executable, "-c", "print('ok')"], seen.append) == 0
    assert seen == ["ok\n"]


def test_a_command_that_cannot_start_is_127_and_delivers_nothing() -> None:
    """No such program: 127, the shell's own number, and no lines."""
    seen: list[str] = []
    assert vf.run_wrapped(["/nonexistent-tool-for-vlog"], seen.append) == _NOT_STARTED
    assert not seen


def test_a_file_is_read_whole_lines_only_and_the_rest_is_read_next_time(tmp_path: Path) -> None:
    """`partial` has no newline yet: it is held back, then returned complete once finished."""
    log = tmp_path / "app.log"
    state = tmp_path / "state.json"
    log.write_bytes(b"a\nb\npartial")
    first = vf.read_from_offset(log, state)
    assert first.lines == ["a", "b"]
    vf.commit(state, first)
    log.write_bytes(b"a\nb\npartial-done\nc\n")
    second = vf.read_from_offset(log, state)
    assert second.lines == ["partial-done", "c"]
    assert not second.restarted


def test_an_uncommitted_read_is_repeated_not_lost(tmp_path: Path) -> None:
    """The state is saved only by commit, so a crash before it re-sends the same lines."""
    log = tmp_path / "app.log"
    state = tmp_path / "state.json"
    log.write_bytes(b"a\nb\n")
    assert vf.read_from_offset(log, state).lines == ["a", "b"]
    assert vf.read_from_offset(log, state).lines == ["a", "b"]


def test_a_truncated_file_restarts_at_the_beginning(tmp_path: Path) -> None:
    """The file became shorter than the offset: read it from 0 and say it restarted."""
    log = tmp_path / "app.log"
    state = tmp_path / "state.json"
    log.write_bytes(b"one\ntwo\nthree\n")
    vf.commit(state, vf.read_from_offset(log, state))
    log.write_bytes(b"new\n")
    got = vf.read_from_offset(log, state)
    assert got.lines == ["new"]
    assert got.restarted


def test_a_rotated_file_with_a_new_inode_restarts_even_if_it_is_longer(tmp_path: Path) -> None:
    """A different file at the same path: its first line is not skipped because the offset fits."""
    log = tmp_path / "app.log"
    state = tmp_path / "state.json"
    log.write_bytes(b"old\n")
    vf.commit(state, vf.read_from_offset(log, state))
    rotated = tmp_path / "app.log.new"
    rotated.write_bytes(b"fresh-1\nfresh-2\nfresh-3\n")
    rotated.replace(log)
    got = vf.read_from_offset(log, state)
    assert got.lines == ["fresh-1", "fresh-2", "fresh-3"]
    assert got.restarted


def test_a_missing_file_is_no_lines_and_keeps_the_saved_position(tmp_path: Path) -> None:
    """Nothing to read is not an error and not a restart."""
    log = tmp_path / "app.log"
    state = tmp_path / "state.json"
    log.write_bytes(b"a\n")
    vf.commit(state, vf.read_from_offset(log, state))
    log.unlink()
    got = vf.read_from_offset(log, state)
    assert got.lines == []
    assert got.offset == len(b"a\n")
