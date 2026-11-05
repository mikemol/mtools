# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the mirror check: a backlog baseline equals the cards blocked on its card (W2298).

⚑ THE CLEAN CASES ARE THE POSITIVE CONTROLS: a file that agrees with the queue, a baseline that is
not a mirror and a repository with no baseline at all each yield nothing, so an arm that asserts a
finding is not a check that always reports one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward import check as chk
from mikemol.pathsforward import mirror
from mikemol.pathsforward.model import State, validate

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_COUNTER = 9
_FILE = "unmanifested-baseline.txt"
_HEADER = "# blocked-on: W1\n"
_NAME = f".claude/{_FILE}: "
_UNCOUNTED = "{} is blocked on W1 and not listed (parked and uncounted)"
_STALE = "{} is listed but no longer blocked on W1; delete its line"


def _wp(sym: str, status: str = "ready", blocked_on: list[str] | None = None) -> Rec:
    """Build a waypoint, blocked on `blocked_on` when that is given.

    Returns:
        the waypoint.

    """
    blocked = blocked_on is not None
    return {
        "symbol": sym,
        "title": sym,
        "status": status,
        "blocked_on": blocked_on or [],
        "blocked_kind": "agent" if blocked else None,
        "enables": [],
        "evidence": "",
    }


def _state(root: Path, waypoints: list[Rec]) -> State:
    """Build a state over `waypoints`, with the repository rooted at `root`.

    Returns:
        the state.

    """
    return validate(
        {"counter": _COUNTER, "project_root": str(root), "waypoints": waypoints, "residue": []}
    )


def _file(root: Path, body: str, name: str = _FILE) -> None:
    claude = root / ".claude"
    claude.mkdir(exist_ok=True)
    (claude / name).write_text(body, encoding="utf-8")


def _parked(*symbols: str) -> list[Rec]:
    """Build W1 plus one open card blocked on it for each symbol.

    Returns:
        the waypoints.

    """
    return [_wp("W1"), *(_wp(sym, "blocked", ["W1"]) for sym in symbols)]


def test_a_repository_with_no_baseline_has_no_finding(tmp_path: Path) -> None:
    """The positive control: no `.claude/` directory at all."""
    assert mirror.findings(_state(tmp_path, _parked("W2"))) == []


def test_a_mirror_that_lists_exactly_the_parked_cards_is_clean(tmp_path: Path) -> None:
    """Every blocked card is listed and nothing else is: no finding."""
    _file(tmp_path, f"{_HEADER}W2\nW3\n")
    assert mirror.findings(_state(tmp_path, _parked("W2", "W3"))) == []


def test_a_parked_card_missing_from_the_file_is_found(tmp_path: Path) -> None:
    """A card blocked on the named card and absent from the file hides from the ratchet."""
    _file(tmp_path, f"{_HEADER}W2\n")
    found = mirror.findings(_state(tmp_path, _parked("W2", "W3")))
    assert found == [_NAME + _UNCOUNTED.format("W3")]


def test_a_released_card_still_listed_is_found(tmp_path: Path) -> None:
    """A card no longer blocked on the named card keeps the ratchet high until its line goes."""
    _file(tmp_path, f"{_HEADER}W2\nW3\n")
    waypoints = [*_parked("W2"), _wp("W3", "ready")]
    found = mirror.findings(_state(tmp_path, waypoints))
    assert found == [_NAME + _STALE.format("W3")]


def test_a_done_card_is_not_parked_and_a_listed_one_is_found(tmp_path: Path) -> None:
    """A done card is no longer waiting, so its line is stale and it is not owed a line."""
    _file(tmp_path, f"{_HEADER}W2\n")
    waypoints = [_wp("W1"), _wp("W2", "done", ["W1"])]
    found = mirror.findings(_state(tmp_path, waypoints))
    assert found == [_NAME + _STALE.format("W2")]


def test_a_baseline_without_the_header_is_not_a_mirror(tmp_path: Path) -> None:
    """Only a file that names its card is judged, so an ordinary baseline is never refused."""
    _file(tmp_path, "W2\n", "mypy-baseline.txt")
    assert mirror.findings(_state(tmp_path, _parked("W2", "W3"))) == []


def test_comments_and_blank_lines_are_not_entries(tmp_path: Path) -> None:
    """The header, prose comments and blank lines do not count as listed symbols."""
    _file(tmp_path, f"{_HEADER}# prose that mentions W9\n\nW2\n")
    assert mirror.findings(_state(tmp_path, _parked("W2"))) == []


def test_the_whole_check_carries_the_mirror_findings(tmp_path: Path) -> None:
    """`check` runs the mirror, so a stale line fails `--check` and not only this module."""
    _file(tmp_path, f"{_HEADER}W2\n")
    found = chk.check(_state(tmp_path, _parked()))
    assert any(_STALE.format("W2") in line for line in found)
