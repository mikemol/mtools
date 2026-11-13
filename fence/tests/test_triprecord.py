# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The trip record is one JSON line per event, appended; the counter is derived (W2359)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from mikemol.fence import triprecord
from mikemol.fence.triprecord import Entry

LIMIT = 4.0
PEAK = 9.5
OWNER = 4242
TWICE = 2
FIELDS = ["at", "command", "event", "guard", "limit", "owner", "peak", "pids", "repo"]
FREEZE = ("kine-latency", "freeze")


def _entry(event: str, guard: str = "kine-latency") -> Entry:
    return Entry(
        at="2026-11-13T10:00:00Z",
        guard=guard,
        event=event,
        pids=(7, 8),
        repo="mtools",
        command="mikemol-commit mtools",
        owner=OWNER,
        limit=LIMIT,
        peak=PEAK,
    )


def _body(text: str) -> dict[str, object]:
    return cast("dict[str, object]", json.loads(text))


def test_a_line_carries_every_field_as_sorted_json() -> None:
    """The grammar luthen reads: all nine fields, one line, newline-terminated."""
    text = triprecord.line(_entry("freeze"))
    assert text.endswith("\n")
    assert text.count("\n") == 1
    body = _body(text)
    assert sorted(body) == FIELDS
    assert body["pids"] == [7, 8]
    assert body["peak"] == PEAK


def test_append_adds_lines_and_never_rewrites_an_earlier_one(tmp_path: Path) -> None:
    """Two appends leave the lines in order, in a directory that did not exist."""
    record = tmp_path / "state" / "events.jsonl"
    triprecord.append(record, [_entry("freeze")])
    first = record.read_text(encoding="utf-8")
    triprecord.append(record, [_entry("resume:cleared"), _entry("cap:kill")])
    lines = record.read_text(encoding="utf-8").splitlines()
    assert lines[0] + "\n" == first
    assert [_body(raw)["event"] for raw in lines] == ["freeze", "resume:cleared", "cap:kill"]


def test_an_empty_batch_creates_nothing(tmp_path: Path) -> None:
    """No event, no file: a quiet run leaves no record behind."""
    record = tmp_path / "events.jsonl"
    triprecord.append(record, [])
    assert not record.exists()


def test_the_counter_is_derived_from_the_lines_by_guard_and_event(tmp_path: Path) -> None:
    """Two freezes and one resume read as two and one, per guard, sorted."""
    record = tmp_path / "events.jsonl"
    triprecord.append(record, [_entry("freeze"), _entry("freeze"), _entry("resume:cleared")])
    triprecord.append(record, [_entry("freeze", guard="other")])
    text = triprecord.counter_text(record)
    assert text.splitlines()[0] == "# TYPE mikemol_guard_events_total counter"
    assert 'mikemol_guard_events_total{guard="kine-latency",event="freeze"} 2' in text
    assert 'mikemol_guard_events_total{guard="kine-latency",event="resume:cleared"} 1' in text
    assert 'mikemol_guard_events_total{guard="other",event="freeze"} 1' in text
    assert triprecord.counts(record)[FREEZE] == TWICE


def test_a_missing_record_and_a_damaged_line_count_nothing_wrong(tmp_path: Path) -> None:
    """A missing record is empty; a torn or foreign line is skipped, the rest still count."""
    record = tmp_path / "events.jsonl"
    assert triprecord.counts(record) == {}
    triprecord.append(record, [_entry("freeze")])
    with record.open("a", encoding="utf-8") as handle:
        handle.write('{"torn": \n[1, 2]\n{"no_guard": true}\n')
    assert triprecord.counts(record) == {FREEZE: 1}


def test_write_counter_replaces_the_file_beside_the_record(tmp_path: Path) -> None:
    """The counter file sits beside the record and is rewritten whole, leaving no temp file."""
    record = tmp_path / "events.jsonl"
    triprecord.append(record, [_entry("freeze")])
    target = triprecord.write_counter(record)
    assert target == tmp_path / "events.jsonl.prom"
    assert 'event="freeze"} 1' in target.read_text(encoding="utf-8")
    triprecord.append(record, [_entry("freeze")])
    triprecord.write_counter(record)
    assert 'event="freeze"} 2' in target.read_text(encoding="utf-8")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["events.jsonl", "events.jsonl.prom"]


def test_a_guard_name_holding_a_quote_a_backslash_and_a_newline_is_escaped(tmp_path: Path) -> None:
    """b65: an unescaped label corrupts the .prom file, and the collector drops all of it."""
    record = tmp_path / "events.jsonl"
    name = 'a"b' + chr(92) + "c" + chr(10) + "d"
    triprecord.append(record, [_entry("freeze", guard=name)])
    text = triprecord.counter_text(record)
    assert r'guard="a\"b\\c\nd",event="freeze"} 1' in text
    assert text.count("\n") == TWICE


def test_the_record_path_is_the_environments_else_the_host_default() -> None:
    """MIKEMOL_GUARD_RECORD wins; with none the default home is used, expanded."""
    assert triprecord.record_path({triprecord.ENV: "/x/y.jsonl"}) == Path("/x/y.jsonl")
    default = triprecord.record_path({})
    assert default.name == "guard-events.jsonl"
    assert "~" not in str(default)
