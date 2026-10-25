# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The idle rung's round order is the repository's rows best rank first, or nothing (W1950)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from mikemol.hooks import round_order, round_wire

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
ROUND = (
    '{"as_of": "2026-10-25T11:00:00Z"}\n'
    '{"repo": "mtools", "symbol": "W9", "rank": "2", "salience": "1"}\n'
    '{"repo": "mtools", "symbol": "W7", "rank": "1", "salience": "2"}\n'
    '{"repo": "nemik", "symbol": "W5", "rank": "1", "salience": "3"}\n'
)


def _round(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    file = tmp_path / "round.json"
    file.write_text(text, encoding="utf-8")
    monkeypatch.setenv(round_wire.ENV, str(file))


def test_the_repositorys_rows_come_back_best_rank_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only this repository's rows, by rank."""
    _round(tmp_path, monkeypatch, ROUND)
    assert round_order.order(tmp_path / "mtools", NOW) == ["W7", "W9"]


def test_every_way_a_round_is_absent_gives_an_empty_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No file, no stamp, a stale stamp and a repository with no rows are all nothing."""
    monkeypatch.setenv(round_wire.ENV, str(tmp_path / "missing.json"))
    assert round_order.order(tmp_path / "mtools", NOW) == []
    _round(tmp_path, monkeypatch, '{"repo": "mtools", "symbol": "W7", "rank": "1"}\n')
    assert round_order.order(tmp_path / "mtools", NOW) == []
    _round(tmp_path, monkeypatch, ROUND)
    late = NOW + round_wire.STALE + timedelta(hours=1)
    assert round_order.order(tmp_path / "mtools", late) == []
    assert round_order.order(tmp_path / "elsewhere", NOW) == []
