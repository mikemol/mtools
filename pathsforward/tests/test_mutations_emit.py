# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A mutation's events become log lines and per-field samples, sent best effort (W1741)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import mutations_emit
from mikemol.pathsforward.mutations import Event

if TYPE_CHECKING:
    from collections.abc import Sequence

STATE = Path("/r/myrepo/.claude/paths-forward.json")
ENV = {"MIKEMOL_OTLP_BIN": "/bin/otlp", "MIKEMOL_ENDPOINTS": "x"}
NO_STORE = {"MIKEMOL_OTLP_BIN": "/bin/otlp", "HOME": "/nonexistent"}
META = mutations_emit.Meta("--update", "agent", "m1", 1_792_000_000_000, "s1", "abc1234")
STATUS = Event("W1", "status", "ready", "working")
BLOCKED = Event("W1", "blocked_on", "[]", '["W2"]')
SENT = 3
BULK = 250
LAST_CHUNK = BULK - 2 * mutations_emit.CHUNK


def _fields(argv: Sequence[str]) -> list[str]:
    return [argv[i + 1] for i, part in enumerate(argv) if part == "--field"]


def test_a_log_line_carries_the_station_the_values_and_the_mutations_context() -> None:
    """The station is repo-qualified, and the context rides every line."""
    body = cast("dict[str, object]", json.loads(mutations_emit.log_line("myrepo", STATUS, META)))
    assert body["station"] == "myrepo:W1"
    assert (body["field"], body["old"], body["new"]) == ("status", "ready", "working")
    assert (body["via"], body["actor"], body["mutation"]) == ("--update", "agent", "m1")
    assert (body["at_ms"], body["session"], body["sha"]) == (META.at_ms, "s1", "abc1234")


def test_the_plan_is_one_log_child_then_one_sample_per_distinct_field() -> None:
    """Three events of two fields: one log child with three lines, two samples."""
    events = [STATUS, BLOCKED, Event("W2", "status", "ready", "working")]
    sends = mutations_emit.plan("/bin/otlp", "myrepo", events, META)
    assert len(sends) == SENT
    assert sends[0][0][:2] == ["/bin/otlp", "log"]
    assert len(sends[0][1].splitlines()) == len(events)
    values = {_fields(a)[1]: a[a.index("--value") + 1] for a, _ in sends[1:]}
    assert values == {"field=status": "2", "field=blocked_on": "1"}


def test_a_sample_is_labelled_by_repo_field_and_via_alone() -> None:
    """No station, value or session reaches a series: those are unbounded."""
    sends = mutations_emit.plan("/bin/otlp", "myrepo", [STATUS], META)
    assert _fields(sends[1][0]) == ["repo=myrepo", "field=status", "via=--update"]
    assert sends[1][0][sends[1][0].index("--name") + 1] == "mikemol.waypoint.event"


def test_a_bulk_edit_is_fed_to_the_log_in_chunks() -> None:
    """The control for the pipe: no child is handed more lines than the chunk."""
    events = [Event(f"W{n}", "status", "ready", "done") for n in range(BULK)]
    logs = [s for s in mutations_emit.plan("/bin/otlp", "myrepo", events, META) if s[1]]
    sizes = [len(s[1].splitlines()) for s in logs]
    assert sizes == [mutations_emit.CHUNK, mutations_emit.CHUNK, LAST_CHUNK]


def test_no_events_start_nothing() -> None:
    """A mutation that changed nothing sends nothing."""
    spawned: list[Sequence[str]] = []
    assert not mutations_emit.emit(STATE, [], META, ENV, lambda a, _s: spawned.append(a))
    assert not spawned


def test_emit_starts_every_child_when_a_binary_and_a_store_exist() -> None:
    """The positive control for the two refusals below."""
    spawned: list[Sequence[str]] = []
    assert mutations_emit.emit(STATE, [STATUS], META, ENV, lambda a, _s: spawned.append(a))
    assert len(spawned) == len(mutations_emit.plan("/bin/otlp", "myrepo", [STATUS], META))


def test_no_store_or_a_failed_start_sends_nothing_and_raises_nothing() -> None:
    """The queue is already saved: a missing store or a dead child never fails the write."""
    spawned: list[Sequence[str]] = []
    assert not mutations_emit.emit(STATE, [STATUS], META, NO_STORE, lambda a, _s: spawned.append(a))
    assert not spawned

    def failing(_argv: Sequence[str], _stdin: str) -> None:
        raise OSError

    assert not mutations_emit.emit(STATE, [STATUS], META, ENV, failing)
