# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the session walk and liveness test (W1289), over a fabricated process table."""

from __future__ import annotations

import os

from mikemol.pathsforward import session

_CLI = 30
_SHELL = 20
_CLAUDE = 10
_STARTED = 500


def _table() -> dict[int, session.Proc]:
    """Build the process table of a tool call: the CLI, its shell, the session, a wrapper.

    Returns:
        the table, keyed by pid.

    """
    return {
        _CLI: session.Proc("mikemol-paths-", _SHELL, 900),
        _SHELL: session.Proc("bash", _CLAUDE, 800),
        _CLAUDE: session.Proc("claude", 5, _STARTED),
        5: session.Proc("drum", 1, 100),
    }


def test_the_walk_names_the_nearest_ancestor_called_claude() -> None:
    """From the CLI, past its shell, the session is the claude process with its start time."""
    table = _table()
    found = session.session_of(_CLI, table.get)
    assert found == session.Session(_CLAUDE, _STARTED)


def test_a_chain_with_no_claude_names_no_session() -> None:
    """The control: a table whose ancestors are never called claude finds nothing."""
    table = _table()
    table[_CLAUDE] = session.Proc("zsh", 5, _STARTED)
    assert session.session_of(_CLI, table.get) is None


def test_a_broken_chain_and_a_parent_loop_both_end_the_walk() -> None:
    """A parent missing from the table, and two processes naming each other, return None."""
    empty: dict[int, session.Proc] = {}
    assert session.session_of(_CLI, empty.get) is None
    loop = {1000: session.Proc("a", 1001, 1), 1001: session.Proc("b", 1000, 1)}
    assert session.session_of(1000, loop.get) is None


def test_alive_needs_the_same_pid_and_the_same_start_time() -> None:
    """Present and same start: alive. Gone, or the pid reused later: not alive."""
    table = _table()
    held = session.Session(_CLAUDE, _STARTED)
    assert session.alive(held, table.get)
    del table[_CLAUDE]
    assert not session.alive(held, table.get)
    table[_CLAUDE] = session.Proc("claude", 5, _STARTED + 1)
    assert not session.alive(held, table.get)


def test_the_real_reader_sees_this_process_and_not_a_missing_one() -> None:
    """The positive control for `/proc`: our own pid parses with a parent; a huge pid is None."""
    mine = session.read_proc(os.getpid())
    assert mine is not None
    assert mine.ppid == os.getppid()
    assert session.read_proc(2**30) is None
