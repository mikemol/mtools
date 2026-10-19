# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A waypoint carries a location string, set and cleared like dtstart, and a VTODO says it."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli
from mikemol.pathsforward.vtodo import todo

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

Rec = dict[str, object]
_ADDRESS = "1 Main St, Detroit, MI"
_OK = cli.EXIT_OK
_REFUSED = cli.EXIT_REFUSED
_STAMP = "20261001T090000Z"


def _wp(sym: str, **extra: object) -> Rec:
    w: Rec = {
        "symbol": sym,
        "title": f"t{sym}",
        "status": "ready",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }
    w.update(extra)
    return w


def _file(tmp_path: Path) -> Path:
    doc: Rec = {
        "counter": 2,
        "project_root": str(tmp_path),
        "state_path": "/elsewhere/live/paths-forward.json",
        "waypoints": [_wp("W1"), _wp("W2")],
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _run(path: Path, *args: str) -> int:
    return cli.main(["--state", str(path), *args])


def _waypoints(path: Path) -> list[Rec]:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    return cast("list[Rec]", doc["waypoints"])


def test_update_sets_the_location_as_written_and_the_empty_string_clears_it(tmp_path: Path) -> None:
    """The address is stored verbatim; '' removes it, as it removes a dtstart."""
    path = _file(tmp_path)
    assert _run(path, "--update", "W1", "--location", _ADDRESS) == _OK
    assert _waypoints(path)[0]["location"] == _ADDRESS
    assert _run(path, "--update", "W1", "--location", "") == _OK
    assert _waypoints(path)[0]["location"] is None


def test_a_location_over_more_than_one_line_is_refused_and_saves_nothing(tmp_path: Path) -> None:
    """An iCalendar LOCATION is one line, so a newline is refused before it is stored."""
    path = _file(tmp_path)
    before = path.read_bytes()
    assert _run(path, "--update", "W1", "--location", "line one\nline two") == _REFUSED
    assert path.read_bytes() == before


def test_the_bulk_form_does_not_take_a_location_as_it_takes_no_dates(tmp_path: Path) -> None:
    """A place is one card's, like a date: --update-many refuses the flag and saves nothing."""
    path = _file(tmp_path)
    before = path.read_bytes()
    assert _run(path, "--update-many", "W1", "W2", "--location", _ADDRESS, "--write") == _REFUSED
    assert path.read_bytes() == before


def test_the_vtodo_carries_the_location_escaped_and_a_card_without_one_has_none() -> None:
    """RFC 5545 escapes the comma; no field, no LOCATION line."""
    placed = todo(_wp("W9", location=_ADDRESS), repo="life", host="box", stamp=_STAMP)
    assert "LOCATION:1 Main St\\, Detroit\\, MI" in placed
    bare = todo(_wp("W9"), repo="life", host="box", stamp=_STAMP)
    assert not any(line.startswith("LOCATION") for line in bare)


def test_location_is_an_update_field_so_add_refuses_it_by_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With --add the mode refuses the flag, naming it."""
    path = _file(tmp_path)
    assert _run(path, "--add", "t", "--location", _ADDRESS) == _REFUSED
    assert "--location" in capsys.readouterr().err
