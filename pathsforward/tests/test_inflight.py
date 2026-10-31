# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A card whose stack is queued or in the gate draws no ATOMIZE advice (W2096, paperkit:R2).

⚑ THE FIXTURE IS THE MEASURED FILE (`.git/mtools/commit.counts`, one line `1 TAB {json}`): one
submission in flight naming W2185, one queued naming W2038 and W2106, one with a state that is
neither. The controls: a missing or torn file names no card, so nothing is exempted by a reading
that did not happen.
"""

from pathlib import Path

from mikemol.pathsforward import inflight
from mikemol.pathsforward.atomize import atomize
from mikemol.pathsforward.ledger import Entry, Parsed, Unparsed

_COUNTS = (
    '1\t{"1": {"began_ns": 5, "pid": 7, "start": "9", "state": "inflight", "waypoints": ["W2185"]},'
    ' "2": {"began_ns": null, "state": "queued", "waypoints": ["W2038", "W2106"]},'
    ' "3": {"state": "withdrawn", "waypoints": ["W9"]}}\n'
)


def _project(tmp_path: Path, counts: str) -> Path:
    """Make a project whose git dir holds a count file.

    Returns:
        the project root.

    """
    folder = tmp_path / ".git" / "mtools"
    folder.mkdir(parents=True)
    (folder / "commit.counts").write_text(counts, encoding="utf-8")
    return tmp_path


def test_the_cards_of_an_inflight_and_a_queued_submission_are_named_and_no_others() -> None:
    """In flight and queued count; a withdrawn submission does not."""
    assert inflight.cards_of(_COUNTS) == {"W2185", "W2038", "W2106"}


def test_a_missing_or_torn_file_names_no_card(tmp_path: Path) -> None:
    """No file, torn JSON, a non-object and an empty file each read as nothing."""
    assert inflight.read(tmp_path) == frozenset()
    assert inflight.cards_of('1\t{"1": ') == frozenset()
    assert inflight.cards_of("1\t[1, 2]") == frozenset()
    assert inflight.cards_of("") == frozenset()
    assert inflight.read(_project(tmp_path, _COUNTS)) == {"W2185", "W2038", "W2106"}


def test_atomize_says_nothing_for_a_top_card_with_a_live_stack_and_otherwise_still_speaks(
    tmp_path: Path,
) -> None:
    """W2185 has an advance and a live stack: no advice; the same card with no stack is named."""
    waypoints: list[dict[str, object]] = [{"symbol": "W2185", "status": "ready"}]
    entries: list[Parsed | Unparsed] = [
        Parsed("2026-10-30T02:00:00Z", Entry("tick", "W2185", "advanced", "unblock", "n"))
    ]
    live = _project(tmp_path / "live", _COUNTS)
    assert atomize(waypoints, entries, root=live) is None
    quiet = _project(tmp_path / "quiet", "")
    assert atomize(waypoints, entries, root=quiet) is not None
