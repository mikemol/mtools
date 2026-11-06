# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The round is read, aged and judged against the queue; an absent round refuses nothing (W1942)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from mikemol.hooks import round_wire
from mikemol.hooks.commit_counts import proc_start

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_NOW = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
_NO_PID = 4_000_000
_ROUND = (
    '{"as_of": "2026-10-25T08:00:00Z", "rows": [\n'
    '{"repo": "mtools", "symbol": "W1", "rank": "1", "salience": "5"},\n'
    '{"repo": "mtools", "symbol": "W2", "rank": "2", "salience": "4"},\n'
    '{"repo": "life", "symbol": "W9", "rank": "1", "salience": "3"}\n'
    "]}"
)


def _queue(**status: str) -> dict[str, object]:
    return {"waypoints": [{"symbol": s, "status": v} for s, v in status.items()]}


_STAMP = datetime(2026, 11, 3, 15, 20, 24, tzinfo=UTC)
_LATER = datetime(2026, 11, 3, 16, 20, 24, tzinfo=UTC)


def test_a_stamp_is_kept_once_and_a_new_one_is_appended(tmp_path: Path) -> None:
    """W1949: the same `as_of` read again adds nothing; a later one adds one line."""
    (tmp_path / ".git" / "mtools").mkdir(parents=True)
    assert round_wire.note_stamp(tmp_path, _STAMP)
    assert not round_wire.note_stamp(tmp_path, _STAMP)
    assert round_wire.note_stamp(tmp_path, _LATER)
    kept = (tmp_path / ".git" / "mtools" / "round-stamps").read_text(encoding="utf-8")
    assert kept.splitlines() == [_STAMP.isoformat(), _LATER.isoformat()]


def test_a_log_that_cannot_be_written_is_false_not_an_exception(tmp_path: Path) -> None:
    """The controls: no tools directory means no log and none created; a file there is False."""
    assert not round_wire.note_stamp(tmp_path, _STAMP)
    assert not (tmp_path / ".git").exists()
    (tmp_path / ".git").write_text("not a directory", encoding="utf-8")
    assert not round_wire.note_stamp(tmp_path, _STAMP)


def test_the_reason_records_the_round_stamp_it_read(tmp_path: Path) -> None:
    """Reading the round for a judgement leaves its stamp in the log, once per distinct stamp."""
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".git" / "mtools").mkdir(parents=True)
    (tmp_path / ".claude" / "paths-forward.json").write_text(json.dumps(_queue()), encoding="utf-8")
    round_file = tmp_path / "round.json"
    round_file.write_text(_ROUND, encoding="utf-8")
    round_wire.round_reason(tmp_path, _NOW, round_file)
    round_wire.round_reason(tmp_path, _NOW, round_file)
    kept = (tmp_path / ".git" / "mtools" / "round-stamps").read_text(encoding="utf-8")
    assert kept.splitlines() == ["2026-10-25T08:00:00+00:00"]


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


def test_a_working_card_a_live_submission_names_is_in_progress_not_outside() -> None:
    """Cited by a queued or gating stack: exempt; a mark on no stack stays outside."""
    queue = _queue(W1="ready", W7="working", W8="working")
    found = round_wire.refusals(queue, _ROUND, "mtools", _NOW, frozenset({"W7"}))
    assert len(found) == 1
    assert "W8" in found[0]
    assert "W7" not in found[0]
    cited = frozenset({"W7", "W8"})
    assert round_wire.refusals(queue, _ROUND, "mtools", _NOW, cited) == []


def test_a_ready_round_card_a_live_submission_names_is_not_demanded() -> None:
    """Its status is stale (the stack is queued or gating), so taking it is not owed (W2005)."""
    queue = _queue(W1="ready", W7="working")
    assert len(round_wire.refusals(queue, _ROUND, "mtools", _NOW)) == 1
    named = frozenset({"W1", "W7"})
    assert round_wire.refusals(queue, _ROUND, "mtools", _NOW, named) == []


def test_only_live_entries_of_the_queue_map_exempt_a_card(tmp_path: Path) -> None:
    """The running test is live; a pid with no process, and a recycled one, are not."""
    mapdir = tmp_path / ".git" / "mtools"
    mapdir.mkdir(parents=True)
    alive = {
        "state": "queued",
        "pid": os.getpid(),
        "start": proc_start(os.getpid()),
        "waypoints": ["W7"],
    }
    dead = {"state": "queued", "pid": _NO_PID, "start": "1", "waypoints": ["W8"]}
    recycled = {"state": "queued", "pid": os.getpid(), "start": "0", "waypoints": ["W9"]}
    body = {"1": alive, "2": dead, "3": recycled}
    (mapdir / "commit.counts").write_text(json.dumps(body), encoding="utf-8")
    assert round_wire.in_gate(tmp_path) == frozenset({"W7"})
    assert round_wire.in_gate(tmp_path / "elsewhere") == frozenset()


def test_the_reason_exempts_a_working_card_a_live_submission_names(tmp_path: Path) -> None:
    """Through round_reason: the same queue refuses without a live entry and admits with one."""
    checkout = tmp_path / "mtools"
    (checkout / ".claude").mkdir(parents=True)
    (checkout / ".claude" / "paths-forward.json").write_text(
        json.dumps(_queue(W1="ready", W7="working")), encoding="utf-8"
    )
    round_file = tmp_path / "round.json"
    round_file.write_text(_ROUND, encoding="utf-8")
    assert round_wire.round_reason(checkout, _NOW, round_file) is not None
    mapdir = checkout / ".git" / "mtools"
    mapdir.mkdir(parents=True)
    live: dict[str, object] = {
        "state": "queued",
        "pid": os.getpid(),
        "start": proc_start(os.getpid()),
        "waypoints": ["W7"],
    }
    body: dict[str, object] = {"1": live}
    (mapdir / "commit.counts").write_text(json.dumps(body), encoding="utf-8")
    assert round_wire.round_reason(checkout, _NOW, round_file) is None


_SCRATCH_ENV = "MIKEMOL_SCRATCH_ROOT"


def _checkout(tmp_path: Path, **status: str) -> tuple[Path, Path]:
    """Build the checkout `mtools` with a queue of the given statuses and a round file beside it.

    Returns:
        the checkout and the round file.

    """
    checkout = tmp_path / "mtools"
    (checkout / ".claude").mkdir(parents=True)
    (checkout / ".claude" / "paths-forward.json").write_text(
        json.dumps(_queue(**status)), encoding="utf-8"
    )
    round_file = tmp_path / "round.json"
    round_file.write_text(_ROUND, encoding="utf-8")
    return checkout, round_file


def test_a_working_card_with_a_held_scratch_tree_is_being_built_not_outside(tmp_path: Path) -> None:
    """W2316: an honest outside mark is admitted; an empty one, and another card's tree, are not."""
    checkout, round_file = _checkout(tmp_path, W1="ready", W7="working")
    scratch_root = tmp_path / "scratch"
    environ = {_SCRATCH_ENV: str(scratch_root)}
    assert round_wire.round_reason(checkout, _NOW, round_file, environ) is not None
    (scratch_root / "mtools-W8").mkdir(parents=True)
    assert round_wire.round_reason(checkout, _NOW, round_file, environ) is not None
    (scratch_root / "mtools-W7").mkdir()
    assert round_wire.round_reason(checkout, _NOW, round_file, environ) is None


def test_no_scratch_root_declared_exempts_nothing_and_does_not_raise(tmp_path: Path) -> None:
    """The root is declared, never guessed: unset means no tree is held, so the refusal stands."""
    checkout, round_file = _checkout(tmp_path, W1="ready", W7="working")
    assert round_wire.round_reason(checkout, _NOW, round_file, {}) is not None


def test_a_commit_queue_that_cannot_be_read_keeps_the_refusal_and_says_so(tmp_path: Path) -> None:
    """W2316: an unreadable reading fails toward the refusal, visibly, never silently admitting."""
    checkout, round_file = _checkout(tmp_path, W1="ready", W7="working")
    mapdir = checkout / ".git" / "mtools"
    mapdir.mkdir(parents=True)
    plain = round_wire.round_reason(checkout, _NOW, round_file, {})
    assert plain is not None
    assert "could not be read" not in plain
    (mapdir / "commit.counts").write_text("{ torn", encoding="utf-8")
    torn = round_wire.round_reason(checkout, _NOW, round_file, {})
    assert torn is not None
    assert "the commit queue could not be read" in torn
    assert "W7" in torn


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
    scratch_root = tmp_path / "scratch"
    (scratch_root / "mtools-W7").mkdir(parents=True)
    monkeypatch.setenv(_SCRATCH_ENV, str(scratch_root))
    assert "take W1 first" in str(round_wire.now_reason(checkout))
