# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Begin and end a tick on the HOST queue: the lock, and the bookkeeping that closes it.

Ported from the host katas.py `tick` (mtools:W796, W877). The host queue is one file a session
writes only through `mikemol-paths-forward`, so every step here is a call to that tool through
`procrun.capture`.

⚑ NO ZRAM CHECK HERE. The host copy refused `tick begin` when the compressed-RAM device was past
85%. That refusal now lives in hooks' `tick_gate`, which covers the prompt (including the host
session's own cron prompt, github d717a73) and reads the lock itself; copying it here would be a
second threshold to keep in step.

⚑ THE HOST'S NAMES ARE THE CALLER'S: the queue file, the lock holder, the standing waypoint that
carries the tick's note, and the file holding the live cron job id. This module knows the order of
the steps (arm, ledger, evidence, flush, unlock) and nothing about whose queue it is.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.procrun.proc import capture

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@dataclass(frozen=True)
class HostQueue:
    """The host queue and who writes it: the pathsforward tool, the state file, the lock holder."""

    tool: Path
    state: Path
    holder: str
    standing: str = "W2"


@dataclass(frozen=True)
class Closing:
    """What a tick records when it ends: the date, the note, the next step, the cron job file."""

    today: str
    note: str = ""
    next_step: str = ""
    job_file: Path | None = None


def _call(queue: HostQueue, *args: str) -> str:
    """Run the pathsforward tool on the host queue.

    Returns:
        what it printed (output then errors), stripped.

    """
    done = capture((str(queue.tool), "--state", str(queue.state), *args))
    return (done.stdout + done.stderr).strip()


def begin(queue: HostQueue) -> str:
    """Take the host queue's tick lock.

    Returns:
        what `--lock` printed (who holds it, or that it was acquired).

    """
    return _call(queue, "--lock", queue.holder)


def end(queue: HostQueue, closing: Closing, flush: Callable[[], object]) -> list[str]:
    """Close a tick: record the cron job, ledger and evidence the note, flush, release the lock.

    ⚑ THE LOCK IS RELEASED LAST: `flush` is the caller's and may start many commits, but it runs
    before the unlock so a session never holds the lock past its own work.

    Returns:
        what each step printed, in order.

    """
    lines: list[str] = []
    job = closing.job_file
    if job is not None and job.exists():
        lines.append(_call(queue, "--armed", job.read_text(encoding="utf-8").strip()))
    if closing.note:
        lines.append(_call(queue, "--ledger", queue.standing, "advanced", "sweep", closing.note))
        update = ["--update", queue.standing, "--evidence-append"]
        update.append(f"{closing.today} {closing.note}")
        if closing.next_step:
            update += ["--next", closing.next_step]
        lines.append(_call(queue, *update))
    flush()
    lines.append(_call(queue, "--unlock", queue.holder))
    return lines
