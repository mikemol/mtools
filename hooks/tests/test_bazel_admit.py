# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `bazel_admit`: heavy bazel commands wait on the host, light ones never do."""

from __future__ import annotations

import io
import stat
from typing import TYPE_CHECKING

from mikemol.hooks import bazel_admit, host_facts

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    import pytest

REAL = "/real/bazel"
FULL = host_facts.Headroom(used=95, limit=100, ratio=2.0)
ROOMY = host_facts.Headroom(used=10, limit=100, ratio=2.0)
BUILD_MB = bazel_admit.HEAVY_MB["build"]
REFUSED = bazel_admit.EXIT_REFUSED
BAZEL_FAILED = 7


def _reader(*answers: host_facts.Headroom | None) -> Callable[[], host_facts.Headroom | None]:
    """Build a zram reader that answers each call in turn, then repeats the last.

    Returns:
        the reader.

    """
    remaining = list(answers)

    def read() -> host_facts.Headroom | None:
        return remaining.pop(0) if len(remaining) > 1 else remaining[0]

    return read


def _unreadable_light_verb() -> host_facts.Headroom | None:
    """Fail the test if a light verb ever reads zram.

    Raises:
        AssertionError: always, since a light verb must not read zram.

    """
    msg = "a light verb must not read zram"
    raise AssertionError(msg)


class _Clock:
    """A clock that only moves when the code sleeps, so no test waits for real."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def sleep(self, seconds: float) -> None:
        """Advance by `seconds` without sleeping."""
        self.slept.append(seconds)
        self.now += seconds

    def time(self) -> float:
        """Return the pretend time.

        Returns:
            seconds since the clock started.

        """
        return self.now


class _Exec:
    """Record what would have been executed, and answer a fixed exit code."""

    def __init__(self, code: int = 0) -> None:
        self.code = code
        self.runs: list[list[str]] = []

    def __call__(self, argv: Sequence[str]) -> int:
        """Record `argv` and return the fixed code.

        Returns:
            the exit code.

        """
        self.runs.append(list(argv))
        return self.code


def _budget(tmp_path: Path) -> Path:
    """Make a stand-in `mikemol-membudget` file named by MEMBUDGET_BIN.

    Returns:
        its path.

    """
    tool = tmp_path / "mikemol-membudget"
    tool.write_text("#!/bin/sh\n", encoding="utf-8")
    return tool


def test_the_verb_is_the_first_word_that_is_not_a_startup_option() -> None:
    """Startup options come first and are skipped; no verb at all is None."""
    assert bazel_admit.verb_of(["--output_base=/x", "test", "//..."]) == "test"
    assert bazel_admit.verb_of(["build", "--config=x"]) == "build"
    assert bazel_admit.verb_of([]) is None
    assert bazel_admit.verb_of(["--version"]) is None


def test_only_heavy_verbs_have_a_memory_estimate() -> None:
    """build, test, run, coverage and fetch are admitted; info, query and a bare bazel are not."""
    assert bazel_admit.estimate_mb("build") == BUILD_MB
    assert bazel_admit.estimate_mb("test") == BUILD_MB
    for light in ("info", "query", "version", "shutdown", None):
        assert bazel_admit.estimate_mb(light) is None


def test_headroom_admits_at_once_without_sleeping_or_saying_anything() -> None:
    """Below the refusal fraction nothing waits and nothing is printed."""
    clock = _Clock()
    said: list[str] = []
    assert bazel_admit.wait_for_zram(_reader(ROOMY), clock.sleep, clock.time, said.append, 60.0)
    assert not clock.slept
    assert not said


def test_a_full_zram_waits_then_admits_once_it_drains_and_says_it_waited() -> None:
    """The wait polls, states the reading, and admits on the first reading below the fraction."""
    clock = _Clock()
    said: list[str] = []
    read = _reader(FULL, FULL, ROOMY)
    assert bazel_admit.wait_for_zram(read, clock.sleep, clock.time, said.append, 600.0)
    assert clock.slept == [bazel_admit.POLL_S, bazel_admit.POLL_S]
    assert len(said) == 1
    assert "95%" in said[0]
    assert "waiting for zram headroom" in said[0]


def test_a_zram_that_stays_full_is_refused_after_the_wait_is_spent() -> None:
    """A bounded wait: past it the answer is False, so bazel does not run into the limit."""
    clock = _Clock()
    said: list[str] = []
    assert not bazel_admit.wait_for_zram(_reader(FULL), clock.sleep, clock.time, said.append, 30.0)
    assert sum(clock.slept) >= 30.0 - bazel_admit.POLL_S


def test_an_unreadable_zram_admits_and_says_so() -> None:
    """What cannot be read blocks nothing, and the gap is stated."""
    clock = _Clock()
    said: list[str] = []
    assert bazel_admit.wait_for_zram(_reader(None), clock.sleep, clock.time, said.append, 60.0)
    assert "unreadable" in said[0]


def test_a_lease_wraps_bazel_when_membudget_is_found_and_a_note_says_when_it_is_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the tool: membudget run MB -- real args. Without it: bazel as is, and a note."""
    tool = _budget(tmp_path)
    env = {bazel_admit.MEMBUDGET_ENV: str(tool)}
    argv, note = bazel_admit.plan(REAL, ["test", "//..."], BUILD_MB, env, tmp_path)
    assert argv == [str(tool), "hold", str(BUILD_MB), "bazel", "--", REAL, "test", "//..."]
    assert "run" not in argv[:3]
    assert note is None
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    argv, note = bazel_admit.plan(REAL, ["test"], BUILD_MB, {}, tmp_path / "empty")
    assert argv == [REAL, "test"]
    assert note is not None
    assert "without a memory lease" in note


def test_a_light_verb_runs_untouched_and_never_reads_zram() -> None:
    """`bazel info` is executed as given, whatever zram says."""
    run, err = _Exec(), io.StringIO()
    code = bazel_admit.admit([REAL, "info", "workspace"], {}, run, err, _unreadable_light_verb)
    assert code == 0
    assert run.runs == [[REAL, "info", "workspace"]]


def test_a_heavy_verb_is_admitted_under_a_lease_and_its_exit_code_is_returned(
    tmp_path: Path,
) -> None:
    """With headroom, `test` runs under membudget and the command's own status comes back."""
    tool = _budget(tmp_path)
    run, err = _Exec(code=BAZEL_FAILED), io.StringIO()
    env = {bazel_admit.MEMBUDGET_ENV: str(tool), bazel_admit.TRACE_ENV: "1"}
    code = bazel_admit.admit([REAL, "test", "//..."], env, run, err, _reader(ROOMY))
    assert code == BAZEL_FAILED
    assert run.runs == [[str(tool), "hold", str(BUILD_MB), "bazel", "--", REAL, "test", "//..."]]
    assert "admitted `test`" in err.getvalue()


def test_a_full_zram_refuses_a_heavy_verb_with_exit_three_and_runs_nothing() -> None:
    """The point of the gate: with the wait spent and zram still full, bazel does not start."""
    run, err = _Exec(), io.StringIO()
    env = {bazel_admit.MAX_WAIT_ENV: "0"}
    code = bazel_admit.admit([REAL, "build", "//..."], env, run, err, _reader(FULL))
    assert code == REFUSED
    assert not run.runs
    assert "refused" in err.getvalue()
    assert f"{bazel_admit.BYPASS_ENV}=0" in err.getvalue()


def test_the_bypass_runs_bazel_untouched_and_says_it_did() -> None:
    """BAZEL_ADMIT=0 is an explicit, stated override, even with zram full."""
    run, err = _Exec(), io.StringIO()
    env = {bazel_admit.BYPASS_ENV: "0"}
    code = bazel_admit.admit([REAL, "build", "//..."], env, run, err, _reader(FULL))
    assert code == 0
    assert run.runs == [[REAL, "build", "//..."]]
    assert "running without admission" in err.getvalue()


def test_install_writes_an_executable_wrapper_that_fails_open(tmp_path: Path) -> None:
    """tools/bazel runs the admit tool from the repo venv or mtools' build, else bazel untouched."""
    wrapper = bazel_admit.install(tmp_path)
    assert wrapper == tmp_path / "tools" / "bazel"
    assert wrapper.stat().st_mode & stat.S_IXUSR
    text = wrapper.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh")
    assert ".venv/bin/mikemol-bazel-admit" in text
    assert "bazel-bin/hooks/.venv/bin/mikemol-bazel-admit" in text
    assert 'exec "$admit" -- "$BAZEL_REAL" "$@"' in text
    assert text.rstrip().endswith('exec "$BAZEL_REAL" "$@"')


def test_main_installs_a_wrapper_and_refuses_a_bad_command_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--install DIR` prints the wrapper's path; anything else is a usage error, exit 2."""
    assert bazel_admit.main(["--install", str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == str(tmp_path / "tools" / "bazel")
    assert bazel_admit.main([]) == bazel_admit.EXIT_USAGE
    assert "usage: mikemol-bazel-admit" in capsys.readouterr().err
