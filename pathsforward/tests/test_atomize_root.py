# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`atomize` reads a card's landings from the project root the writer gives it (W2170)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward.atomize import atomize
from mikemol.pathsforward.ledger import Entry, Parsed, Unparsed

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_WAYPOINTS: list[dict[str, object]] = [{"symbol": "W7", "status": "ready"}]


def _advance_at(stamp: str) -> list[Parsed | Unparsed]:
    return [Parsed(stamp, Entry("tick", "W7", "advanced", "unblock", "note"))]


def _unreadable(_root: Path) -> dict[str, str] | None:
    return None


def test_a_root_reads_the_landings_from_there_and_an_unreadable_repository_skips_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The root reaches the reader; a landing after the advance spends it; None skips nothing."""
    asked: list[Path] = []

    def landings(root: Path) -> dict[str, str] | None:
        asked.append(root)
        return {"W7": "2026-10-30T03:00:00Z"}

    entries = _advance_at("2026-10-30T02:00:00Z")
    monkeypatch.setattr("mikemol.pathsforward.atomize.landings_of", landings)
    assert atomize(_WAYPOINTS, entries, root=tmp_path) is None
    assert asked == [tmp_path]
    monkeypatch.setattr("mikemol.pathsforward.atomize.landings_of", _unreadable)
    assert atomize(_WAYPOINTS, entries, root=tmp_path) is not None
