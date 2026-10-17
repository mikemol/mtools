# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-watchdog`: exit when a session has gone quiet while it has work to do (W1474, W1476).

    mikemol-watchdog --state .claude/paths-forward.json [--writer PATH] [--poll-s S] [--phi-fire P]

Run it as a background task (`run_in_background`): the harness tells the session when a background
process exits, and that exit is the whole alarm. It reads the heartbeat the tools leave
(`hooks/heartbeat.py`, written by `mikemol-commit`, `mikemol-scratch` and the paths-forward writer),
and when the silence since the last beat passes the repo's own limit it asks the writer how many
ready cards are waiting. Cards waiting: it prints one line and exits with `EXIT_IDLE`. None: the
session is really blocked, the watchdog notes it and goes on watching.

⚑ THE LIMIT IS LEARNED AND BOUNDED (operator, 2026-10-17: "closer to a 5-10m cadence, with the cron
30m cadence as the fallback"). The suspicion model `phi(t) = t / (mean * ln 10)` picks the moment,
`phi_fire` being the level (1.0 is a silence that happens one time in ten), and the moment is held
inside `MIN_FIRE_S` to `MAX_FIRE_S`: a repo whose beats come every ten seconds is not woken after
twenty-three, and one with no history, or a long mean, is woken by ten minutes at the latest.

⚑ NO DEADLINE ON THE WATCH. The poll interval paces the reads and decides nothing. The only ends are
the alarm, and the parent going away: a watchdog that outlives its session is an orphan.

⚑ ITS OWN QUESTION IS NOT A BEAT. The ready count goes through the writer's `--ready-count`, which
does not beat (a beat is the SESSION's own action), so asking never resets the silence it measures.

CONSUMED BY: `--tick-open`, which prints the command to start it (W1476).
"""

import argparse
import math
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from mikemol.hooks import heartbeat
from mikemol.hooks.heartbeat import Beat

EXIT_IDLE = 8
EXIT_CANNOT_RUN = 7
MIN_FIRE_S = 300.0
MAX_FIRE_S = 600.0
DEFAULT_PHI_FIRE = 1.0
DEFAULT_POLL_S = 20.0
_NS_PER_S = 1_000_000_000

Seams = tuple[
    Callable[[], Beat | None],
    Callable[[], int | None],
    Callable[[], int],
    Callable[[float], None],
    Callable[[], bool],
]
"""(read the beat, count ready cards, now in ns, sleep, is the parent still alive)."""


def silence_limit_s(last: Beat, phi_fire: float) -> float:
    """Say how long a silence after `last` may run before the watchdog asks about work.

    Returns:
        the silence at which the suspicion reaches `phi_fire`, held between `MIN_FIRE_S` and
        `MAX_FIRE_S`; `MAX_FIRE_S` when too few gaps are recorded to learn a mean.

    """
    mean = heartbeat.mean_gap_s(last)
    if mean is None:
        return MAX_FIRE_S
    return min(max(phi_fire * mean * math.log(10), MIN_FIRE_S), MAX_FIRE_S)


def idle_line(waiting: int, last: Beat, now_ns: int) -> str:
    """Spell the one line the alarm prints.

    Returns:
        `idle with N ready cards, last heartbeat Ts ago (tool)`.

    """
    ago = max(now_ns - last.at_ns, 0) // _NS_PER_S
    return f"idle with {waiting} ready cards, last heartbeat {ago}s ago ({last.tool})"


def watch(seams: Seams, phi_fire: float, poll_s: float) -> int:
    """Watch until the silence passes the limit with work waiting, or the parent goes away.

    Returns:
        EXIT_IDLE after printing the idle line; 0 when the parent is gone.

    """
    read, ready, now_ns, sleep, alive = seams
    asked_about: int | None = None
    while alive():
        last = read()
        if last is not None and last.at_ns != asked_about:
            silent_s = (now_ns() - last.at_ns) / _NS_PER_S
            if silent_s >= silence_limit_s(last, phi_fire):
                waiting = ready()
                if waiting:
                    sys.stdout.write(idle_line(waiting, last, now_ns()) + "\n")
                    return EXIT_IDLE
                asked_about = last.at_ns
        sleep(poll_s)
    return 0


def ready_from(writer: str, state: Path) -> int | None:
    """Ask the writer how many ready cards the queue holds.

    The writer is the one place the count is defined, so this is a question to it, not a reading
    of the queue file.

    Returns:
        the count, or None when the writer cannot run or does not answer with a number.

    """
    try:
        done = subprocess.run(
            [writer, "--state", str(state), "--ready-count"],
            capture_output=True,
            text=True,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except OSError:
        return None
    said = done.stdout.strip()
    return int(said) if done.returncode == 0 and said.isdecimal() else None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mikemol-watchdog")
    parser.add_argument("--state", required=True, help="the queue file the session works from")
    parser.add_argument("--writer", help="the paths-forward writer (default: the one on PATH)")
    parser.add_argument("--poll-s", type=float, default=DEFAULT_POLL_S)
    parser.add_argument("--phi-fire", type=float, default=DEFAULT_PHI_FIRE)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the watchdog.

    Returns:
        EXIT_IDLE when the session went quiet with work waiting, 0 when its parent went away,
        EXIT_CANNOT_RUN when no writer is found.

    """
    opts: dict[str, object] = vars(_parser().parse_args(sys.argv[1:] if argv is None else argv))
    named = opts.get("writer")
    writer = str(named) if named else shutil.which("mikemol-paths-forward")
    if writer is None:
        sys.stderr.write("mikemol-watchdog: no paths-forward writer found (use --writer)\n")
        return EXIT_CANNOT_RUN
    state = Path(str(opts["state"])).absolute()
    git_dir = state.parent.parent / ".git"
    parent = os.getppid()
    seams: Seams = (
        lambda: heartbeat.read(git_dir),
        lambda: ready_from(writer, state),
        time.time_ns,
        time.sleep,
        lambda: os.getppid() == parent,
    )
    return watch(seams, float(str(opts["phi_fire"])), float(str(opts["poll_s"])))


if __name__ == "__main__":
    raise SystemExit(main())
