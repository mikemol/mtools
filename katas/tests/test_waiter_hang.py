# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that the waiter ends a child only when it is hung, never for being slow (W1130).

The operator's rule is to avoid wall-clock timeouts. ⚑ THE SLOW CHILD IS THE CONTROL: a child that
runs far longer than the patience, but whose CPU advances (or whose log grows), is not ended and
exits on its own with 0. A child that sleeps in silence is the one that is ended, with rc 125.
The CPU reader is injected where a test must control it; the hung case uses the real `proctree`
on a real sleeping child, which gets no CPU.
"""

from __future__ import annotations

import itertools
import sys
from typing import TYPE_CHECKING

from mikemol.katas import commits, waiter

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_POLL_S = 0.05
_PATIENCE = 4
_BACKSTOP = 10.0
_SHORT_BACKSTOP = 0.3
_SILENT = [sys.executable, "-c", "import time; time.sleep(20)"]
_SLOW = [sys.executable, "-c", "import time; time.sleep(1.0)"]
_CHATTY = [
    sys.executable,
    "-c",
    "import time\nfor i in range(20):\n    print(i, flush=True)\n    time.sleep(0.05)\n",
]
_TICKS = itertools.count(1)


# A CPU reader that always reports more than before, and one that never moves.
def _advancing(_pid: int) -> float:
    return float(next(_TICKS))


def _frozen(_pid: int) -> float:
    return 1.0


def _watch(cpu: Callable[[int], float | None]) -> waiter.Watch:
    return waiter.Watch(_POLL_S, _PATIENCE, cpu)


def test_a_silent_child_is_ended_as_hung_and_the_log_says_why(tmp_path: Path) -> None:
    """No log growth and no tree CPU for the patience: rc 125, the reason logged."""
    log = tmp_path / "fx.log"
    watch = waiter.Watch(_POLL_S, _PATIENCE)
    status = waiter.run(log, _SILENT, timeout=_BACKSTOP, watch=watch)
    assert status == waiter.HUNG
    assert "no progress" in log.read_text(encoding="utf-8")
    assert commits.commit_state(log) == f"FAILED rc={waiter.HUNG}"


def test_a_slow_child_whose_cpu_advances_is_never_ended(tmp_path: Path) -> None:
    """The control: it outlasts the patience many times over, its CPU moves, it exits 0 itself."""
    log = tmp_path / "fx.log"
    status = waiter.run(log, _SLOW, timeout=_BACKSTOP, watch=_watch(_advancing))
    assert status == 0
    assert commits.commit_state(log) == commits.DONE


def test_a_child_whose_log_keeps_growing_is_never_ended_though_its_cpu_is_frozen(
    tmp_path: Path,
) -> None:
    """Output alone is progress: twenty lines over a second against a patience of four polls."""
    log = tmp_path / "fx.log"
    status = waiter.run(log, _CHATTY, timeout=_BACKSTOP, watch=_watch(_frozen))
    assert status == 0
    assert "19" in log.read_text(encoding="utf-8")


def test_the_backstop_still_ends_a_child_that_always_looks_busy(tmp_path: Path) -> None:
    """A runaway that always looks busy is bounded by the one wall-clock backstop, rc 124."""
    log = tmp_path / "fx.log"
    status = waiter.run(log, _SILENT, timeout=_SHORT_BACKSTOP, watch=_watch(_advancing))
    assert status == waiter.TIMED_OUT
    assert "timed out" in log.read_text(encoding="utf-8")
