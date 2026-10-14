# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that one line becomes one record with its fields kept, a good time, and nothing lost.

W1165. ⚑ THE FAILURE LINES ARE THE POINT: a non-JSON line, a JSON array, an over-long line and an
unreadable time must each come back as a record that says what was wrong, never as a dropped line
or a silently wrong time. ⚑ THE CONTROLS: a line with no time field falls back to `now` WITHOUT
`time_unparsed`, so that flag means "a time was there and was not understood", not "no time".
"""

from __future__ import annotations

from mikemol.hooks import vlogrecord as vr

_NOW = "2026-10-14T00:00:00.000000Z"
_STREAMS = {"tool": "commit", "repo": "mtools"}


def _record(line: str, how: vr.FieldMap | None = None) -> vr.Record:
    return vr.record_of(line, _STREAMS, _NOW, how)


def test_a_json_object_keeps_its_fields_and_gains_the_stream_fields() -> None:
    """Fields survive as fields, `message` becomes `_msg`, the time is RFC3339 microseconds."""
    line = '{"message": "landed", "sha": "abc1234", "time": "2026-10-13T20:11:40-04:00"}'
    got = _record(line)
    assert got["_msg"] == "landed"
    assert got["sha"] == "abc1234"
    assert got["_time"] == "2026-10-14T00:11:40.000000Z"
    assert got["tool"] == "commit"
    assert got["repo"] == "mtools"
    assert "parse_failure" not in got


def test_a_number_is_epoch_seconds_or_the_unit_named_and_never_left_an_integer() -> None:
    """1 is one second after the epoch; 1500 ms is 1.5 s; both come back as strings."""
    assert _record('{"ts": 1, "message": "m"}')["_time"] == "1970-01-01T00:00:01.000000Z"
    got = _record('{"ts": 1500, "message": "m"}', vr.FieldMap(unit="ms"))
    assert got["_time"] == "1970-01-01T00:00:01.500000Z"


def test_a_line_that_is_not_json_is_wrapped_with_a_parse_failure_and_kept() -> None:
    """The text is the message, the time is now, the flag says why, the streams are still there."""
    got = _record("COMMITTED mtools abc1234 W1: subject [PUSHED]\n")
    assert got["_msg"] == "COMMITTED mtools abc1234 W1: subject [PUSHED]"
    assert got["_time"] == _NOW
    assert got["parse_failure"] == "not-json"
    assert got["repo"] == "mtools"


def test_json_that_is_not_an_object_is_wrapped_not_dropped() -> None:
    """A list parses as JSON but has no fields to keep: it is a message with its own flag."""
    got = _record("[1, 2, 3]")
    assert got["_msg"] == "[1, 2, 3]"
    assert got["parse_failure"] == "not-an-object"


def test_an_over_long_line_is_cut_and_says_so() -> None:
    """Truncated at `max_line`, flagged, and still a record."""
    short = vr.FieldMap(max_line=10)
    got = _record("x" * 50, short)
    assert got["_msg"] == "x" * 10
    assert got["truncated"] == "true"
    assert "truncated" not in _record("x" * 10, short)


def test_an_unreadable_time_falls_back_to_now_and_says_so_but_a_missing_one_does_not() -> None:
    """The control: no time field is not an error, so no `time_unparsed`."""
    bad = _record('{"time": "yesterday-ish", "message": "m"}')
    assert bad["_time"] == _NOW
    assert bad["time_unparsed"] == "true"
    missing = _record('{"message": "m"}')
    assert missing["_time"] == _NOW
    assert "time_unparsed" not in missing


def test_the_named_keys_override_the_defaults() -> None:
    """`when` is the time and `verdict` the message when the caller says so."""
    line = '{"when": "2026-01-02T03:04:05Z", "verdict": "REFUSED", "time": "1999-01-01T00:00:00Z"}'
    got = _record(line, vr.FieldMap(time_key="when", message_key="verdict"))
    assert got["_msg"] == "REFUSED"
    assert got["_time"] == "2026-01-02T03:04:05.000000Z"


def test_a_stream_field_that_replaces_a_lines_own_key_is_flagged_with_the_keys() -> None:
    """The stream wins, as it must, but the loss is visible: both clashing keys, sorted."""
    got = _record('{"message": "m", "tool": "from-the-line", "repo": "r", "other": 1}')
    assert got["tool"] == "commit"
    assert got["repo"] == "mtools"
    assert got["stream_overrode"] == "repo,tool"
    assert got["other"] == 1


def test_no_flag_is_set_when_no_line_key_collides_with_a_stream_field() -> None:
    """The control: a line with only its own keys has no `stream_overrode`."""
    assert "stream_overrode" not in _record('{"message": "m", "sha": "1"}')


def test_a_line_without_the_message_key_keeps_its_whole_text_as_the_message() -> None:
    """No `message` field: the line itself is `_msg`, so the record is never message-less."""
    got = _record('{"sha": "abc"}')
    assert got["_msg"] == '{"sha": "abc"}'
    assert got["sha"] == "abc"
