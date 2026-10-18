# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The watchdog exits when a session is quiet past its learned limit with ready work waiting."""

import os
import stat
from collections.abc import Callable
from pathlib import Path

import pytest

from mikemol.hooks import watchdog
from mikemol.hooks.heartbeat import MIN_GAPS, Beat

_S = 1_000_000_000
_POLL = 20.0
_THREE = 3
_FOUR = 4
_PID = 4242


def _beat(at_s: int, mean_s: int | None = None) -> Beat:
    gaps = tuple(mean_s * _S for _ in range(MIN_GAPS)) if mean_s is not None else ()
    return Beat("mikemol-commit", at_s * _S, gaps)


def _seams(
    beats: list[Beat | None],
    ready: Callable[[], int | None],
    clock_s: list[int],
    lives: int = 100,
) -> watchdog.Seams:
    # Each poll reads the next beat (the last repeats), and the clock steps with it.
    state = {"poll": 0, "alive": lives}

    def read() -> Beat | None:
        return beats[min(state["poll"], len(beats) - 1)]

    def now() -> int:
        return clock_s[min(state["poll"], len(clock_s) - 1)] * _S

    def sleep(_s: float) -> None:
        state["poll"] += 1

    def alive() -> bool:
        state["alive"] -= 1
        return state["alive"] >= 0

    return read, ready, now, sleep, alive


def test_a_repo_with_no_history_is_woken_by_the_latest_limit() -> None:
    """Too few gaps to learn a mean: the band's far edge, ten minutes."""
    assert watchdog.silence_limit_s(_beat(0), 1.0) == watchdog.MAX_FIRE_S


def test_a_fast_repo_is_not_woken_sooner_than_the_band_allows() -> None:
    """Beats ten seconds apart suspect a silence at 23 s, and the band holds it at five minutes."""
    assert watchdog.silence_limit_s(_beat(0, mean_s=10), 1.0) == watchdog.MIN_FIRE_S


def test_a_slow_repo_is_woken_inside_the_band_not_at_its_own_pace() -> None:
    """A mean of 40 minutes would wait an hour and a half; the band caps it at ten minutes."""
    assert watchdog.silence_limit_s(_beat(0, mean_s=2400), 1.0) == watchdog.MAX_FIRE_S


def test_a_learned_mean_inside_the_band_picks_the_moment() -> None:
    """Mean 200 s at one-in-ten suspicion is 200 * ln 10, about 460 s, between the edges."""
    limit = watchdog.silence_limit_s(_beat(0, mean_s=200), 1.0)
    assert watchdog.MIN_FIRE_S < limit < watchdog.MAX_FIRE_S


def test_quiet_past_the_limit_with_ready_cards_prints_one_line_and_exits_idle(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The exit is the alarm, and its line says how many cards wait and how long it has been."""
    seams = _seams([_beat(0)], lambda: _THREE, [700])
    assert watchdog.watch(seams, 1.0, _POLL) == watchdog.EXIT_IDLE
    said = capsys.readouterr().out
    assert said == "idle with 3 ready cards, last heartbeat 700s ago (mikemol-commit)\n"


def test_quiet_inside_the_limit_keeps_watching_and_asks_nothing() -> None:
    """A session that beat a minute ago is working."""
    asked: list[int] = []

    def ready() -> int | None:
        asked.append(1)
        return _FOUR

    seams = _seams([_beat(0)], ready, [60], lives=4)
    assert watchdog.watch(seams, 1.0, _POLL) == 0
    assert asked == []


def test_a_session_with_no_ready_cards_is_asked_once_per_beat_and_never_fired_on() -> None:
    """Really blocked: the check is recorded, quietly, and not repeated until it beats again."""
    asked: list[int] = []

    def ready() -> int | None:
        asked.append(1)
        return 0

    seams = _seams([_beat(0)], ready, [700, 800, 900], lives=4)
    assert watchdog.watch(seams, 1.0, _POLL) == 0
    assert asked == [1]


def test_a_new_beat_reopens_the_question() -> None:
    """The earlier answer was about the earlier silence."""
    asked: list[int] = []

    def ready() -> int | None:
        asked.append(1)
        return 0

    seams = _seams([_beat(0), _beat(1000)], ready, [700, 1800], lives=4)
    assert watchdog.watch(seams, 1.0, _POLL) == 0
    assert asked == [1, 1]


def test_a_writer_that_cannot_answer_does_not_fire() -> None:
    """An unknown count is not evidence of work."""
    seams = _seams([_beat(0)], lambda: None, [700], lives=3)
    assert watchdog.watch(seams, 1.0, _POLL) == 0


def test_no_heartbeat_file_is_a_beat_at_the_watchdogs_own_start(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A repo with ready cards and no beat at all is fired on after the band, and says why."""
    seams = _seams([None], lambda: _FOUR, [0, 700])
    assert watchdog.watch(seams, 1.0, _POLL) == watchdog.EXIT_IDLE
    said = capsys.readouterr().out.splitlines()
    assert said[0] == "mikemol-watchdog: no heartbeat file: counting from my start"
    assert said[1] == "idle with 4 ready cards, last heartbeat 700s ago (no heartbeat source)"


def test_no_heartbeat_file_and_no_ready_cards_does_not_fire_and_says_so_once(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The note is for the old pin, not a per-poll chatter, and a blocked repo is left alone."""
    seams = _seams([None], lambda: 0, [0, 700, 800], lives=4)
    assert watchdog.watch(seams, 1.0, _POLL) == 0
    assert capsys.readouterr().out.count("no heartbeat file") == 1


def test_no_heartbeat_file_inside_the_band_does_not_fire() -> None:
    """Counting from the start is still a silence measured against the band."""
    seams = _seams([None], lambda: _FOUR, [0, 60], lives=3)
    assert watchdog.watch(seams, 1.0, _POLL) == 0


def test_the_parent_going_away_ends_the_watch_quietly() -> None:
    """A watchdog that outlives its session is an orphan."""
    seams = _seams([_beat(0)], lambda: 9, [10_000], lives=0)
    assert watchdog.watch(seams, 1.0, _POLL) == 0


def _writer(tmp_path: Path, body: str) -> str:
    script = tmp_path / "writer"
    script.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return str(script)


def test_the_ready_count_is_the_writers_answer(tmp_path: Path) -> None:
    """The count has one definition, and the watchdog only asks."""
    got = watchdog.ready_from(_writer(tmp_path, "echo 4"), tmp_path / "q.json")
    assert got == _FOUR


def test_an_answer_that_is_not_a_number_or_a_failing_writer_is_unknown(tmp_path: Path) -> None:
    """Neither reads as zero work, because zero would be a claim."""
    queue = tmp_path / "q.json"
    assert watchdog.ready_from(_writer(tmp_path, "echo none"), queue) is None
    assert watchdog.ready_from(_writer(tmp_path, "echo 4\nexit 1"), queue) is None
    assert watchdog.ready_from(str(tmp_path / "absent"), queue) is None


def test_without_a_writer_the_watchdog_cannot_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No writer on PATH and none named: exit 7, the instrument fault."""
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    assert watchdog.main(["--state", str(tmp_path / "q.json")]) == watchdog.EXIT_CANNOT_RUN


def test_the_watch_announces_it_is_armed_on_the_first_poll_and_every_few_after() -> None:
    """The armed gauge goes stale when the watchdog dies, so it is refreshed while it runs."""
    sent: list[int] = []
    seams = _seams([_beat(0)], lambda: 0, [0], lives=watchdog.ARMED_EVERY_POLLS * 2 + 1)
    watchdog.watch(seams, 1.0, _POLL, lambda: sent.append(1))
    assert len(sent) == len((0, 1, 2))


def _env(**extra: str) -> dict[str, str]:
    return {"MIKEMOL_OTLP_BIN": "/bin/otlp", "MIKEMOL_ENDPOINTS": "/e", **extra}


def test_the_publisher_sends_one_armed_sample_naming_the_repo() -> None:
    """A detached mikemol-otlp metric, as the commit gauges are sent."""
    spawned: list[list[str]] = []
    watchdog.armed_publisher(_env(), "myrepo", lambda argv: spawned.append(list(argv)))()
    argv = spawned[0]
    assert argv[:2] == ["/bin/otlp", "metric"]
    assert argv[argv.index("--name") + 1] == watchdog.ARMED_NAME
    assert "repo=myrepo" in argv
    assert argv[argv.index("--value") + 1] == "1"


def test_without_a_store_the_publisher_sends_nothing() -> None:
    """No MIKEMOL_ENDPOINTS means nowhere to send, and the watch goes on."""
    spawned: list[list[str]] = []
    env = {"MIKEMOL_OTLP_BIN": "/bin/otlp"}
    watchdog.armed_publisher(env, "myrepo", lambda argv: spawned.append(list(argv)))()
    assert spawned == []


def test_a_publisher_whose_child_cannot_start_never_raises() -> None:
    """A failed start is a missed sample."""

    def broken(_argv: object) -> None:
        raise OSError

    watchdog.armed_publisher(_env(), "myrepo", broken)()


def test_a_pid_file_naming_a_live_process_is_a_running_watchdog(tmp_path: Path) -> None:
    """The record is the repo's own, and the probe is the process, not a process list."""
    watchdog.claim(tmp_path, _PID)
    assert watchdog.running(tmp_path, lambda pid: pid == _PID) is True
    assert watchdog.running(tmp_path, lambda _pid: False) is False


def test_no_pid_file_or_an_unreadable_one_is_no_watchdog(tmp_path: Path) -> None:
    """Absent, empty and garbled all read as not running."""
    assert watchdog.running(tmp_path, lambda _pid: True) is False
    watchdog.pidfile_of(tmp_path).parent.mkdir(parents=True)
    watchdog.pidfile_of(tmp_path).write_text("not a pid\n", encoding="utf-8")
    assert watchdog.running(tmp_path, lambda _pid: True) is False


def test_release_removes_only_its_own_pid_file(tmp_path: Path) -> None:
    """A newer watchdog that took the file over keeps it when the older one exits."""
    watchdog.claim(tmp_path, 7)
    watchdog.release(tmp_path, 8)
    assert watchdog.pidfile_of(tmp_path).is_file()
    watchdog.release(tmp_path, 7)
    assert not watchdog.pidfile_of(tmp_path).exists()


def test_the_default_probe_finds_this_process_and_not_a_dead_one() -> None:
    """Signal zero: this process is alive, and a pid no process holds is not."""
    assert watchdog.running(Path("/nonexistent")) is False
    assert watchdog.is_alive(os.getpid()) is True


def test_main_holds_the_pid_file_while_it_watches_and_removes_it_on_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The file exists during the watch and is gone after, whatever the watch returned."""
    seen: list[bool] = []

    def watching(*_args: object) -> int:
        seen.append(watchdog.pidfile_of(tmp_path / ".git").is_file())
        return watchdog.EXIT_IDLE

    monkeypatch.setattr(watchdog, "watch", watching)
    code = watchdog.main(
        ["--state", str(tmp_path / ".claude" / "q.json"), "--writer", _writer(tmp_path, "echo 0")]
    )
    assert code == watchdog.EXIT_IDLE
    assert seen == [True]
    assert not watchdog.pidfile_of(tmp_path / ".git").exists()
