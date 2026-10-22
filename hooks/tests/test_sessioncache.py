# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Each recent session's latest cache turn becomes gauges, one series set per session (W1828).

⚑ ABSENCE IS NOT WARM: a session whose reader fails or that has no turn sends no gauge, a first
turn sends no gap, and the count gauge is sent on every run, 0 included, so a dead producer is a
missing series and not a quiet zero.
"""

import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from mikemol.hooks import commit_span, sessioncache

_ENV = {
    commit_span.BIN_ENV: "/opt/mikemol-otlp",
    commit_span.ENDPOINTS_ENV: "/host/e.json",
    sessioncache.READER_ENV: "/opt/reader",
}
_NOW = 1_000_000.0
_HOUR = 3600
_FOUR = 4
_COLD_CREATE = 200_000
_COLD: dict[str, object] = {
    "model": "m1",
    "cache_read": 24_000,
    "cache_creation": _COLD_CREATE,
    "gap_s": 4882.0,
    "cold": True,
}
_TURN = json.dumps(_COLD)


def _line(record: dict[str, object]) -> str:
    return json.dumps(record)


def _parsed(lines: Sequence[str]) -> list[dict[str, object]]:
    return [cast("dict[str, object]", json.loads(line)) for line in lines]


def _touch(root: Path, name: str, age_s: float) -> Path:
    path = root / "proj" / f"{name}.jsonl"
    path.parent.mkdir(exist_ok=True)
    path.write_text("{}\n", encoding="utf-8")
    os.utime(path, (_NOW - age_s, _NOW - age_s))
    return path


def _reply(_argv: Sequence[str], _cwd: Path) -> tuple[int, str]:
    return 0, ""


def test_the_last_object_line_is_the_latest_turn_and_the_count_line_is_skipped() -> None:
    """`--cache-turns` ends with a '#' line; the turn before it is the one."""
    first = _line({"model": "a"})
    assert sessioncache.latest(f"{first}\n{_TURN}\n# 2 turn(s), 1 cold\n") == _COLD
    assert sessioncache.latest("# 0 turn(s), 0 cold\n") is None
    assert sessioncache.latest("") is None


def test_a_turn_is_four_gauges_labelled_by_session_and_model_only() -> None:
    """Read, creation, gap and cold, with the labels `session` and `model` and no others."""
    rows = _parsed(sessioncache.rows("s1", _COLD))
    assert len(rows) == _FOUR
    assert {tuple(cast("dict[str, str]", r["fields"])) for r in rows} == {("session", "model")}
    assert {r["name"]: r["value"] for r in rows} == {
        "mikemol.session.cache_read": pytest.approx(24_000.0),
        "mikemol.session.cache_creation": pytest.approx(float(_COLD_CREATE)),
        "mikemol.session.gap_s": pytest.approx(4882.0),
        "mikemol.session.cold": pytest.approx(1.0),
    }


def test_a_first_turn_sends_no_gap_and_a_warm_turn_sends_cold_zero() -> None:
    """A null gap is left out, never sent as 0, and a warm turn's cold gauge is 0."""
    turn: dict[str, object] = {
        "model": "m",
        "cache_read": 9,
        "cache_creation": 1,
        "gap_s": None,
        "cold": False,
    }
    rows = _parsed(sessioncache.rows("s", turn))
    assert "mikemol.session.gap_s" not in [r["name"] for r in rows]
    assert rows[-1]["value"] == pytest.approx(0.0)


def test_only_recent_transcripts_are_listed_newest_first_and_capped_by_count(
    tmp_path: Path,
) -> None:
    """A transcript older than the window is left out, and the cap is a count."""
    _touch(tmp_path, "old", 10 * _HOUR)
    _touch(tmp_path, "mid", 2 * _HOUR)
    _touch(tmp_path, "new", 60)
    assert [p.stem for p in sessioncache.recent(tmp_path, _NOW)] == ["new", "mid"]
    assert [p.stem for p in sessioncache.recent(tmp_path, _NOW, cap=1)] == ["new"]


def test_the_count_gauge_comes_first_and_a_failed_reader_leaves_a_session_out(
    tmp_path: Path,
) -> None:
    """Three transcripts read, one reader fails: the count says 3 and two sessions have rows."""
    paths = [_touch(tmp_path, n, 60) for n in ("a", "b", "c")]

    def run(argv: Sequence[str], _cwd: Path) -> tuple[int, str]:
        return (1, "") if "b.jsonl" in argv[1] else (0, _TURN + "\n# 1 turn(s), 1 cold\n")

    lines = sessioncache.collect(paths, "/r", run)
    first = _parsed(lines)[0]
    assert (first["name"], first["fields"]) == (sessioncache.COUNT_NAME, {})
    assert first["value"] == pytest.approx(3.0)
    assert len(lines) == 1 + 2 * _FOUR


def test_a_run_with_no_session_still_sends_the_count_of_zero(tmp_path: Path) -> None:
    """The continuous sibling is sent with nothing else, so silence means a dead producer."""
    sent: list[tuple[list[str], str]] = []

    def spawn(argv: Sequence[str], text: str) -> None:
        sent.append((list(argv), text))

    assert sessioncache.main([str(tmp_path)], _ENV, _reply, spawn, _NOW) == 0
    ((argv, text),) = sent
    assert argv[:2] == ["/opt/mikemol-otlp", "metrics"]
    assert argv[argv.index("--service") + 1] == sessioncache.SERVICE
    row = _parsed(text.splitlines())[0]
    assert row["name"] == sessioncache.COUNT_NAME
    assert row["value"] == pytest.approx(0.0)


def test_no_store_sends_nothing_and_says_so(tmp_path: Path) -> None:
    """Without a named store there is nothing to send to, and nothing is spawned."""
    sent: list[str] = []

    def spawn(_argv: Sequence[str], text: str) -> None:
        sent.append(text)

    no_store = {k: v for k, v in _ENV.items() if k != commit_span.ENDPOINTS_ENV}
    code = sessioncache.main([str(tmp_path)], no_store, _reply, spawn, _NOW)
    assert code == sessioncache.EXIT_NO_STORE
    assert not sent
