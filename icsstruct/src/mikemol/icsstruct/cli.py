# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-ics`: occurrences in a window, from one or more calendar sources.

    mikemol-ics [--from YYYY-MM-DD] [--window 14d] [--json] SOURCE...

A SOURCE is an `.ics` path or an http, https or webcal URL, read once through `source.read`, so
a secret URL never reaches the output: every line names the calendar by its label.

- Text: one tab-separated line per occurrence, `start`, `label`, `summary`. A malformed line
  (stage 1) or an unexpandable VEVENT (stage 2) is a line too, starting `!`, so nothing the
  reader found is left off the page;
- `--json`: one JSON object per record, with `kind` one of `occurrence`, `malformed`,
  `unexpandable`, and the source's `calendar` label;
- a source that cannot be read is reported on stderr by label, the other sources still print,
  and the exit status is 1. An unknown flag or a bad `--window` is refused by argparse (exit 2).

Options are read through `vars()` into a `dict[str, object]` and narrowed per key, as the
siblings' CLIs do, because argparse's Namespace is untyped.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from typing import TYPE_CHECKING, cast

from mikemol.icsstruct.expand import Occurrence, Unexpandable, expand
from mikemol.icsstruct.lexical import Malformed, lex
from mikemol.icsstruct.source import SourceError, read

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import TextIO

_DEFAULT_DAYS = 14


def _days(text: str) -> int:
    """Parse a window such as `14d`.

    Returns:
        the number of days.

    Raises:
        argparse.ArgumentTypeError: if it is not a positive count of days.

    """
    count = text.removesuffix("d")
    if not text.endswith("d") or not count.isdigit() or int(count) == 0:
        msg = f"window must be a positive number of days, such as 14d, not {text!r}"
        raise argparse.ArgumentTypeError(msg)
    return int(count)


def _parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        the parser.

    """
    parser = argparse.ArgumentParser(
        prog="mikemol-ics", description="Occurrences in a window, from calendar sources."
    )
    parser.add_argument("sources", nargs="+", metavar="SOURCE")
    parser.add_argument(
        "--from", dest="start", type=datetime.date.fromisoformat, help="window start (today)"
    )
    parser.add_argument("--window", type=_days, default=_DEFAULT_DAYS, help="length, e.g. 14d")
    parser.add_argument("--json", action="store_true", help="one JSON record per line")
    return parser


def _iso(value: datetime.date | None) -> str | None:
    """Render a date or datetime for output.

    Returns:
        its ISO form, or None.

    """
    return None if value is None else value.isoformat()


def _record(label: str, record: Occurrence | Unexpandable | Malformed) -> dict[str, object]:
    """Shape one record for `--json`.

    Returns:
        the JSON object.

    """
    if isinstance(record, Occurrence):
        return {
            "kind": "occurrence",
            "calendar": label,
            "uid": record.uid,
            "start": _iso(record.start),
            "end": _iso(record.end),
            "all_day": record.all_day,
            "summary": record.summary,
            "recurrence_id": _iso(record.recurrence_id),
            "line_span": [record.first, record.last],
        }
    kind = "malformed" if isinstance(record, Malformed) else "unexpandable"
    return {
        "kind": kind,
        "calendar": label,
        "reason": record.reason,
        "line_span": [record.first, record.last],
        "raw": list(record.raw),
    }


def _text(label: str, record: Occurrence | Unexpandable | Malformed) -> str:
    """Shape one record as a text line.

    Returns:
        the line, without its terminator.

    """
    if isinstance(record, Occurrence):
        return f"{_iso(record.start)}\t{label}\t{record.summary or ''}"
    kind = "malformed" if isinstance(record, Malformed) else "unexpandable"
    return f"!{kind}\t{label}\tlines {record.first}-{record.last}\t{record.reason}"


def main(
    argv: Sequence[str] | None = None, out: TextIO | None = None, err: TextIO | None = None
) -> int:
    """Print the occurrences of every source in the window.

    Returns:
        0 if every source was read, 1 if any was not. argparse exits 2 on a bad flag or value.

    """
    opts: dict[str, object] = vars(_parser().parse_args(sys.argv[1:] if argv is None else argv))
    sink, errors = out or sys.stdout, err or sys.stderr
    given = opts["start"]
    start = (
        given
        if isinstance(given, datetime.date)
        else datetime.datetime.now(datetime.UTC).astimezone().date()
    )
    days = opts["window"]
    stop = start + datetime.timedelta(days=days if isinstance(days, int) else _DEFAULT_DAYS)
    as_json = opts["json"] is True
    # ⚑ cast, as //transcriptstruct's `_texts` does: isinstance(..., list) narrows to list[Any].
    locations = tuple(str(v) for v in cast("list[object]", opts["sources"]))
    status = 0
    for location in locations:
        try:
            source = read(location)
        except SourceError as exc:
            errors.write(f"mikemol-ics: {exc}\n")
            status = 1
            continue
        records = lex(source.text)
        found = [r for r in records if isinstance(r, Malformed)]
        for record in [*found, *expand(records, start, stop)]:
            line = (
                json.dumps(_record(source.label, record))
                if as_json
                else _text(source.label, record)
            )
            sink.write(line + "\n")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
