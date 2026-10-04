# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--unlinked`: n of m live waypoints linked, counting an edge from either end (W535)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.pathsforward import cli
from mikemol.pathsforward.unlinked import report

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from mikemol.pathsforward.model import Json

_REFUSED = 2


def _w(sym: str, status: str = "ready", **fields: object) -> Json:
    return {"symbol": sym, "title": f"title {sym}", "status": status, **fields}


def _write(tmp_path: Path, waypoints: list[Json]) -> Path:
    path = tmp_path / "paths-forward.json"
    doc = {"counter": 99, "heartbeat": "t0", "residue": [], "waypoints": waypoints}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_a_planted_isolated_waypoint_is_named() -> None:
    """A waypoint with no edge either way is counted and named, in queue order."""
    ws = [_w("W1", enables=["W2"]), _w("W2"), _w("W3"), _w("W4")]
    assert report(ws) == [
        "2 of 4 live waypoints linked",
        "UNLINKED W3 title W3",
        "UNLINKED W4 title W4",
    ]


def test_an_incoming_edge_alone_counts_as_linked() -> None:
    """W2 declares nothing but W1 enables it, so W2 is linked (the one-off script erred here)."""
    ws = [_w("W1", enables=["W2"]), _w("W2"), _w("W3", blocked_on=["W4"]), _w("W4")]
    assert report(ws) == ["4 of 4 live waypoints linked"]


def test_an_outgoing_edge_alone_counts_as_linked() -> None:
    """A foreign symbol or a prose blocker is an outgoing edge, so the waypoint is linked."""
    ws = [_w("W1", blocked_on=["peer:W9"]), _w("W2", blocked_on=["operator: decide x"])]
    assert report(ws) == ["2 of 2 live waypoints linked"]


def test_a_done_waypoint_is_excluded_from_n_and_m() -> None:
    """A done waypoint is not counted, and its own edges link nobody."""
    ws = [_w("W1", "done", enables=["W2"]), _w("W2"), _w("W3")]
    assert report(ws) == [
        "0 of 2 live waypoints linked",
        "UNLINKED W2 title W2",
        "UNLINKED W3 title W3",
    ]


def test_an_edge_to_a_done_waypoint_still_links_the_live_one() -> None:
    """The live waypoint declared the edge, so it is linked though the target is done."""
    assert report([_w("W1", enables=["W2"]), _w("W2", "done")]) == ["1 of 1 live waypoints linked"]


def test_an_empty_queue_exits_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """No live waypoint is refused with exit 2, never printed as `0 of 0`."""
    path = _write(tmp_path, [_w("W1", "done")])
    assert cli.main(["--state", str(path), "--unlinked"]) == _REFUSED
    out = capsys.readouterr()
    assert (out.out, "REFUSED" in out.err) == ("", True)


def test_the_run_prints_and_leaves_the_state_file_byte_identical(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """It exits 0 with unlinked waypoints present, and never rewrites the state file."""
    path = _write(tmp_path, [_w("W1", enables=["W2"]), _w("W2"), _w("W3")])
    before = path.read_bytes()
    assert cli.main(["--state", str(path), "--unlinked"]) == 0
    assert (path.read_bytes() == before, capsys.readouterr().out) == (
        True,
        "2 of 3 live waypoints linked\nUNLINKED W3 title W3\n",
    )


def test_a_stray_field_flag_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """`--unlinked --enables W1` reads no field flag, so it is refused before any read."""
    path = _write(tmp_path, [_w("W1")])
    assert cli.main(["--state", str(path), "--unlinked", "--enables", "W1"]) == _REFUSED
    assert "--enables does not apply to --unlinked" in capsys.readouterr().err
