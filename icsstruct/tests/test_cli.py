# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-ics`: one line per occurrence, every defect on the page, by label.

The sources are life's synthetic fixtures (life 4a652ec, UIDs @life.invalid).
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import cast

import pytest

from mikemol.icsstruct.cli import main

_FIXTURES = Path(__file__).parent / "fixtures"
_WEEKLY = str(_FIXTURES / "01-weekly-rrule-exdate.ics")
_DAMAGED = str(_FIXTURES / "06-malformed.ics")
_BAD_ARGS = 2


def _run(*argv: str) -> tuple[int, list[str], str]:
    """Run the CLI with captured streams.

    Returns:
        the exit status, the stdout lines, and the stderr text.

    """
    out, err = io.StringIO(), io.StringIO()
    status = main(list(argv), out, err)
    return status, out.getvalue().splitlines(), err.getvalue()


def test_text_prints_one_line_per_occurrence_by_label() -> None:
    """Fixture 01 over September to November: five tab-separated lines, each labelled."""
    status, lines, err = _run("--from", "2026-09-01", "--window", "91d", _WEEKLY)
    assert (status, err) == (0, "")
    assert [line.split("\t") for line in lines] == [
        [f"2026-{day}T09:00:00-04:00", "Synthetic Weekly", "Synthetic weekly standup"]
        for day in ("09-07", "09-14", "09-28", "10-05", "10-12")
    ]


def test_json_carries_every_defect_beside_the_occurrence() -> None:
    """Fixture 06 as `--json`: stage 1's three defects and the one well-formed occurrence.

    ⚑ Nothing the reader found is left out: each defect is a record with its reason and span.
    """
    status, lines, _ = _run("--json", "--from", "2026-10-01", "--window", "30d", _DAMAGED)
    # ⚑ cast, as //pathsforward's test_cli does: json.loads is typed Any.
    records = [cast("dict[str, object]", json.loads(line)) for line in lines]
    assert status == 0
    assert [(r["kind"], r.get("reason"), r.get("uid")) for r in records] == [
        ("malformed", "END:VTODO with no open BEGIN", None),
        ("malformed", "BEGIN:VEVENT is never closed", None),
        ("malformed", "no colon outside quotes, so no value", None),
        ("occurrence", None, "fixture-06-ok@life.invalid"),
    ]
    assert {r["calendar"] for r in records} == {_DAMAGED}


def test_text_marks_defects_with_a_bang() -> None:
    """In text mode each defect is a `!malformed` line naming its lines and reason."""
    _, lines, _ = _run("--from", "2026-10-01", "--window", "30d", _DAMAGED)
    assert [line.split("\t")[0] for line in lines] == [
        "!malformed",
        "!malformed",
        "!malformed",
        "2026-10-06T15:00:00+00:00",
    ]


def test_unreadable_source_is_reported_and_the_rest_still_print() -> None:
    """A missing path is one stderr line and exit 1; the readable source still prints."""
    missing = str(_FIXTURES / "absent.ics")
    status, lines, err = _run("--from", "2026-09-01", "--window", "91d", missing, _WEEKLY)
    assert status == 1
    assert err == f"mikemol-ics: {missing}: FileNotFoundError\n"
    assert len(lines) == len(("09-07", "09-14", "09-28", "10-05", "10-12"))


@pytest.mark.parametrize("window", ["14", "0d", "2w", "-3d"])
def test_bad_window_is_refused(window: str) -> None:
    """A window that is not a positive count of days is refused by argparse, exit 2."""
    with pytest.raises(SystemExit) as caught:
        _run("--window", window, _WEEKLY)
    assert caught.value.code == _BAD_ARGS
