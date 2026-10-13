# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the waiter's `--timeout S` and the `LOG.seconds` a clean run leaves (W1105).

⚑ THE LIMIT IS OBSERVED, NOT INFERRED: a 30 s sleep under `--timeout 0.2` is recorded as timed out
at once, so the flag reached the run; and a failed or timed-out child leaves no seconds, so the
measure a flush derives a ceiling from is only ever a gate that passed.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.katas import waiter

if TYPE_CHECKING:
    from pathlib import Path

_OK = [sys.executable, "-c", "print('fine')"]
_FAIL = [sys.executable, "-c", "import sys; sys.exit(3)"]
_SLEEP = [sys.executable, "-c", "import time; time.sleep(30)"]
_SHORT = "0.2"
_EXIT_THREE = 3


def test_a_clean_run_leaves_the_seconds_it_took(tmp_path: Path) -> None:
    """The seconds file beside the log holds one non-negative number."""
    log = tmp_path / "r.log"
    assert waiter.run(log, _OK) == 0
    assert float(waiter.seconds_of(log).read_text(encoding="utf-8")) >= 0.0
    assert waiter.seconds_of(log).name == "r.log.seconds"


def test_a_failed_run_leaves_no_seconds(tmp_path: Path) -> None:
    """Only a passing gate is a measure of the gate."""
    log = tmp_path / "r.log"
    assert waiter.run(log, _FAIL) == _EXIT_THREE
    assert not waiter.seconds_of(log).exists()


def test_the_timeout_flag_reaches_the_run_and_a_timeout_leaves_no_seconds(tmp_path: Path) -> None:
    """A 30 s sleep under `--timeout 0.2` ends as 124 from the command line."""
    log = tmp_path / "r.log"
    assert waiter.main([str(log), "--timeout", _SHORT, *_SLEEP]) == waiter.TIMED_OUT
    assert not waiter.seconds_of(log).exists()


def test_split_timeout_peels_a_leading_pair_and_otherwise_leaves_the_argv() -> None:
    """A good value is taken; none leaves the argv and the default."""
    assert waiter.split_timeout(["--timeout", "5", "cmd", "a"]) == (5.0, ["cmd", "a"])
    assert waiter.split_timeout(["cmd", "a"]) == (waiter.TIMEOUT_S, ["cmd", "a"])


def test_a_bad_timeout_value_falls_back_to_the_default_limit() -> None:
    """A word, zero or a negative is not a limit: the default stands, the pair is still peeled."""
    for bad in ("soon", "0", "-4"):
        assert waiter.split_timeout(["--timeout", bad, "cmd"]) == (waiter.TIMEOUT_S, ["cmd"])
