# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the human views: the mirror says it is derived, and the queue is in rank order."""

from __future__ import annotations

import re
from pathlib import Path

from mikemol.pathsforward import payload as pl
from mikemol.pathsforward import render
from mikemol.pathsforward.digest import v2
from mikemol.pathsforward.model import State, validate

_PATH = Path("/scratch/paths-forward.json")
_NOW = "2026-09-23T00:00:00Z"
_BLOCKED = "blocked"
_DONE = "done"
# File order is the reverse of the rank: a blocked W22 above a ready W24 is the defect.
_FILE_ORDER = (
    ("W1", _DONE),
    ("W2", _BLOCKED),
    ("W3", "ready"),
    ("W4", _BLOCKED),
    ("W5", "working"),
    ("W6", "ready"),
)
_RANKED = ("W5", "W3", "W6", "W2", "W4", "W1")
_ROW = re.compile(r"^\| \d+ \|")
_STANZA = re.compile(r"^  (W\d+) \[", re.MULTILINE)


def _state(residue: list[dict[str, object]]) -> State:
    """Build a two-waypoint state.

    Returns:
        the state.

    """
    return validate(
        {
            "counter": 2,
            "heartbeat": "h",
            "job_id": "j",
            "waypoints": [
                {"symbol": "W2", "title": "a | b", "status": "ready", "rank_reason": "unblocks W1"},
                {"symbol": "W1", "title": "t", "status": "blocked", "blocked_on": ["mikemol"]},
            ],
            "residue": residue,
        }
    )


def _mixed() -> State:
    """Build a state whose file order disagrees with the rank order, with a done one.

    Returns:
        the state.

    """
    return validate(
        {
            "counter": len(_FILE_ORDER),
            "project_root": "/proj",
            "waypoints": [
                {
                    "symbol": sym,
                    "title": sym,
                    "status": status,
                    "next_bounded_step": "s",
                    "blocked_on": ["mikemol"] if status == _BLOCKED else [],
                    "blocked_kind": "human" if status == _BLOCKED else None,
                }
                for sym, status in _FILE_ORDER
            ],
            "residue": [],
        }
    )


def _queue_symbols(state: State) -> list[str]:
    """Read the symbols `--queue` lists, in its order.

    Returns:
        the symbols.

    """
    return [row.split()[1] for row in render.queue(state).splitlines()]


def _mirror_symbols(state: State) -> list[str]:
    """Read the symbols the mirror's table lists, in its order.

    Returns:
        the symbols.

    """
    rows = (ln for ln in render.mirror(state, _PATH).splitlines() if _ROW.match(ln))
    return [row.split("|")[2].strip() for row in rows]


def _payload_symbols(state: State) -> list[str]:
    """Read the symbols the payload's waypoint stanzas list, in its order.

    Returns:
        the symbols.

    """
    return [m.group(1) for m in _STANZA.finditer(pl.build(pl.Request(state, _PATH, _NOW)))]


def test_the_mirror_says_it_is_derived() -> None:
    """The mirror's first line says it is derived and must not be edited."""
    assert render.mirror(_state([]), _PATH).splitlines()[0] == render.DERIVED


def test_the_mirror_carries_the_v2_hash() -> None:
    """The mirror carries the same v2 hash the payload does."""
    state = _state([])
    assert f"hash `{v2(state.waypoints)}`" in render.mirror(state, _PATH)


def test_a_pipe_in_a_title_does_not_break_the_table() -> None:
    """A pipe in a title is escaped inside its cell."""
    assert "| a \\| b |" in render.mirror(_state([]), _PATH)


def test_an_empty_residue_says_none() -> None:
    """An empty residue renders as (none); a populated one lists its reasons."""
    full = render.mirror(_state([{"symbol": "W3", "reason": "why", "title": "x"}]), _PATH)
    assert ("- (none)" in render.mirror(_state([]), _PATH), "x: why" in full) == (True, True)


def test_the_queue_is_numbered_in_array_order() -> None:
    """The queue numbers its rows and carries each waypoint's rank reason."""
    rows = render.queue(_state([])).splitlines()
    assert (rows[0].split()[:2], rows[1].split()[:2], rows[0].endswith("unblocks W1")) == (
        ["1.", "W2"],
        ["2.", "W1"],
        True,
    )


def test_the_queue_lists_working_then_ready_then_blocked() -> None:
    """--queue lists working, ready, blocked, then done, each group in file order."""
    assert _queue_symbols(_mixed()) == list(_RANKED)


def test_the_mirror_lists_working_then_ready_then_blocked() -> None:
    """The mirror's table lists working, ready, blocked, then done, each group in file order."""
    assert _mirror_symbols(_mixed()) == list(_RANKED)


def test_queue_mirror_and_payload_agree_on_order() -> None:
    """--queue, the mirror and the payload list the live waypoints in one order."""
    state = _mixed()
    done = {sym for sym, status in _FILE_ORDER if status == _DONE}
    queue = [sym for sym in _queue_symbols(state) if sym not in done]
    mirror = [sym for sym in _mirror_symbols(state) if sym not in done]
    assert (queue, mirror) == (_payload_symbols(state), _payload_symbols(state))
