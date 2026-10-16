# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One input line to one VictoriaLogs record: fields kept, nothing dropped (mtools:W1165).

`mikemol-vlog` reads lines that are usually JSON objects already (apply verdicts, gate verdicts,
`mikemol-commit` lines, katas ticks) and ships them as STRUCTURED fields, not as one flattened
string. This is the pure half: a line, the stream fields, the clock and the field mapping in; the
record out. It reads no file, posts nothing and asks no endpoint.

⚑ NOTHING IS DROPPED. A line that is not JSON, or is JSON but not an object, becomes a record whose
message is the line itself and which carries `parse_failure`, so the reader can query for exactly
the lines the producer got wrong. An over-long line is cut to `max_line` characters and says
`truncated`; it is not discarded.

⚑ THE TIME IS RFC3339 WITH MICROSECONDS, NEVER A BARE INTEGER (hooks/refusal_log.py measured it:
VictoriaLogs answers HTTP 200 to an integer time and files the record at the wrong time, which
looks like success). A number is read as epoch seconds, or as the unit the caller names; a string
is kept when it parses; anything else falls back to `now` and says `time_unparsed`.

⚑ THE MAPPING IS EXPLICIT: `message_key` names the field that becomes `_msg` and `time_key` the one
that becomes `_time`; with no `time_key` the first of `_time`, `time`, `timestamp`, `ts` present
is used. The stream fields are added as fields; the sink names them in `_stream_fields`.

CONSUMED BY: the `mikemol-vlog` command (W1169).
"""

import datetime as dt
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

TIME_KEYS = ("_time", "time", "timestamp", "ts")
DEFAULT_MESSAGE_KEY = "message"
DEFAULT_MAX_LINE = 65536
UNITS = {"s": 1.0, "ms": 1e3, "us": 1e6, "ns": 1e9}
Record = dict[str, object]


@dataclass(frozen=True)
class LineStamp:
    """A time embedded in a line's TEXT (W1185): a pattern with one capture group, and its form.

    `form` is `iso` (an ISO-8601 string) or `epoch` (seconds since the epoch). It is applied to a
    line that is not JSON, and to a JSON line that has none of the time keys.
    """

    pattern: re.Pattern[str]
    form: str = "iso"


@dataclass(frozen=True)
class FieldMap:
    """How a line's fields map onto the record: which is the message, which is the time."""

    message_key: str = DEFAULT_MESSAGE_KEY
    time_key: str | None = None
    unit: str = "s"
    max_line: int = DEFAULT_MAX_LINE
    line_stamp: LineStamp | None = None


def stamp(moment: dt.datetime) -> str:
    """Spell an instant as RFC3339 UTC with microseconds.

    Returns:
        for example `2026-10-14T01:02:03.000004Z`.

    """
    return moment.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _instant(value: object, unit: str) -> dt.datetime | None:
    """Read a value as an instant: a number in `unit`, or an ISO-8601 string.

    Returns:
        the instant, or None when it is neither.

    """
    try:
        if isinstance(value, int | float) and not isinstance(value, bool) and unit in UNITS:
            return dt.datetime.fromtimestamp(value / UNITS[unit], dt.UTC)
        if isinstance(value, str):
            return dt.datetime.fromisoformat(value)
    except Exception as caught:
        if not isinstance(caught, (OverflowError, OSError, ValueError)):
            raise
        return None
    return None


def time_of(value: object, unit: str, now: str) -> tuple[str, bool]:
    """Read a line's time value.

    Returns:
        the RFC3339 time and whether it was understood; `now` and False when it was not.

    """
    moment = _instant(value, unit)
    return (stamp(moment), True) if moment is not None else (now, False)


def _text(value: object) -> str:
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True)


def from_text(text: str, how: FieldMap, now: str) -> tuple[str, bool]:
    """Read the time embedded in a line's text with the configured stamp (W1185).

    ⚑ WITH NO STAMP CONFIGURED THIS IS `now` AND UNFLAGGED: only a source that declared a stamp can
    fail to match it, so `time_unparsed` keeps meaning "a time was expected and was not read".

    Returns:
        the RFC3339 time and whether it was read; `now` and False when the stamp did not match.

    """
    stamp_kind = how.line_stamp
    if stamp_kind is None:
        return now, True
    found = stamp_kind.pattern.match(text)
    if found is None:
        return now, False
    raw: object = found.group(1)
    if stamp_kind.form == "epoch":
        try:
            raw = float(found.group(1))
        except ValueError:
            return now, False
        return time_of(raw, "s", now)
    return time_of(raw, how.unit, now)


def _wrapped(line: str, why: str, now: str, how: FieldMap) -> Record:
    """Wrap a line that is not a JSON object, keeping its text and any time it carries.

    Returns:
        a record whose message is the line (cut to `max_line`), flagged `parse_failure`, with the
        stamped time when the source declared a stamp that matched.

    """
    when, understood = from_text(line, how, now)
    record: Record = {"_msg": line[: how.max_line], "_time": when, "parse_failure": why}
    if not understood:
        record["time_unparsed"] = "true"
    if len(line) > how.max_line:
        record["truncated"] = "true"
    return record


def record_of(
    line: str, streams: Mapping[str, str], now: str, how: FieldMap | None = None
) -> Record:
    """Turn one input line into a record.

    Returns:
        the record: `_msg`, `_time`, every field of the line, and the stream fields.

    """
    mapping = how or FieldMap()
    text = line.rstrip("\n")
    try:
        parsed = cast("object", json.loads(text))
    except ValueError:
        return {**_wrapped(text, "not-json", now, mapping), **streams}
    if not isinstance(parsed, dict):
        return {**_wrapped(text, "not-an-object", now, mapping), **streams}
    fields = cast("dict[str, object]", parsed)
    record: Record = {k: v for k, v in fields.items() if k not in {"_msg", "_time"}}
    keys = (mapping.time_key,) if mapping.time_key else TIME_KEYS
    named = next((k for k in keys if k in fields), None)
    if named is None:
        when, understood = from_text(text, mapping, now)
    else:
        when, understood = time_of(fields[named], mapping.unit, now)
    record["_time"] = when
    if not understood:
        record["time_unparsed"] = "true"
    record["_msg"] = _text(fields.get(mapping.message_key, text))[: mapping.max_line]
    clash = sorted(key for key in streams if key in record)
    if clash:
        record["stream_overrode"] = ",".join(clash)
    return {**record, **streams}
