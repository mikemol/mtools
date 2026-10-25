# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The round is read, aged and judged against the queue; an absent round refuses nothing (W1942)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from mikemol.hooks import round_wire

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_NOW = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
_ROUND = (
    '{"as_of": "2026-10-25T08:00:00Z", "rows": [\n'
    '{"repo": "mtools", "symbol": "W1", "rank": "1", "salience": "5"},\n'
    '{"repo": "mtools", "symbol": "W2", "rank": "2", "salience": "4"},\n'
    '{"repo": "life", "symbol": "W9", "rank": "1", "salience": "3"}\n'
    "]}"
)


def _queue(**status: str) -> dict[str, object]:
    return {"waypoints": [{"symbol": s, "status": v} for s, v in status.items()]}


def test_a_ready_round_card_skipped_for_an_outside_card_is_refused() -> None:
    """The composition refusal, through the file reader."""
    found = round_wire.refusals(_queue(W1="ready", W7="working"), _ROUND, "mtools", _NOW)
    assert len(found) == 1
    assert found[0].startswith("W1 is in this repository's round")


def test_a_stale_or_unstamped_round_refuses_nothing() -> None:
    """Older than STALE, or no stamp: no round."""
    late = _NOW + round_wire.STALE + timedelta(minutes=1)
    queue = _queue(W1="ready", W7="working")
    assert round_wire.refusals(queue, _ROUND, "mtools", late) == []
    assert round_wire.refusals(queue, '{"rows": [', "mtools", _NOW) == []


def test_another_repository_and_a_round_wholly_inside_refuse_nothing() -> None:
    """Rows of another repository are not this one's; working only round cards is admitted."""
    assert round_wire.refusals(_queue(W1="ready", W7="working"), _ROUND, "elsewhere", _NOW) == []
    assert round_wire.refusals(_queue(W1="ready", W2="working"), _ROUND, "mtools", _NOW) == []


def test_the_reason_reads_both_files_and_a_missing_one_gives_none(tmp_path: Path) -> None:
    """The reason joins the refusals; an unreadable round or queue gives None."""
    checkout = tmp_path / "mtools"
    (checkout / ".claude").mkdir(parents=True)
    queue_file = checkout / ".claude" / "paths-forward.json"
    queue_file.write_text(json.dumps(_queue(W1="ready", W7="working")), encoding="utf-8")
    round_file = tmp_path / "round.json"
    assert round_wire.round_reason(checkout, _NOW, round_file) is None
    round_file.write_text(_ROUND, encoding="utf-8")
    reason = round_wire.round_reason(checkout, _NOW, round_file)
    assert reason is not None
    assert "take W1 first" in reason


def test_the_path_is_the_environment_override_else_the_nemik_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The environment names the file; without it luthen's export tree holds it."""
    monkeypatch.setenv(round_wire.ENV, "/x/round.json")
    assert str(round_wire.round_path()) == "/x/round.json"
    monkeypatch.delenv(round_wire.ENV)
    assert round_wire.round_path().parts[-3:] == ("luthen", "nemik-export", "round.json")


def test_the_wall_clock_judgement_reads_a_round_stamped_now(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The wall-clock judgement: a round stamped now refuses, a missing one does not."""
    checkout = tmp_path / "mtools"
    (checkout / ".claude").mkdir(parents=True)
    queue_file = checkout / ".claude" / "paths-forward.json"
    queue_file.write_text(json.dumps(_queue(W1="ready", W7="working")), encoding="utf-8")
    round_file = tmp_path / "round.json"
    monkeypatch.setenv(round_wire.ENV, str(round_file))
    assert round_wire.now_reason(checkout) is None
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = '{"repo": "mtools", "symbol": "W1", "rank": "1", "salience": "1"}'
    round_file.write_text(f'{{"as_of": "{stamp}"}}\n{row}\n', encoding="utf-8")
    assert "take W1 first" in str(round_wire.now_reason(checkout))
