# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The lease holder joins the stacks queued behind it and runs one train (W1654).

⚑ THE GLUE, NOT THE PARTS: `trainjoin` reads the followers back from the ledger, `traindrive` gates
the joined tip once and decides each stack, `trainverdict` leaves each follower its verdict. This
asks the live-commit map which stacks are queued, joins those behind the leader, runs the train and
splits the result: the leader's own text goes to its output and its code is returned, every other
stack's verdict is written for its waiting process (W1671) to print at its turn.

⚑ NOBODY BEHIND IS NO TRAIN: when no queued stack behind this one can be read from the ledger, this
returns None and the caller runs its stack exactly as before, so a repository with one stack at a
time, or a ledger that cannot be written, behaves as it always did. `MIKEMOL_TRAIN=0` is the
operator's off switch.

⚑ A VERDICT THAT CANNOT BE WRITTEN IS SAID: that follower's stack has already landed or been
refused, and its process will run again on its turn, so the leader names it on stderr rather than
let the surprise be silent.

⚑ EVERY TRAIN IS RECORDED (W1676): one `train` span with the counts `traintel` defines, from the
moment the leader began to join to the last verdict, so the saving is a panel.

CONSUMED BY: `commit_kata.run_stack_mode`.
"""

import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import TextIO

from mikemol.hooks import (
    commit_counts,
    traindrive,
    trainjoin,
    trainround,
    traintel,
    trainverdict,
)
from mikemol.hooks.stackrun import Seams

TRAIN_ENV = "MIKEMOL_TRAIN"
OFF = "0"
MISSING = 1


def queued_keys(ledger: Path) -> list[str]:
    """List the submit keys of the commits waiting for their turn.

    Returns:
        the keys of the live map's queued entries.

    """
    rows = commit_counts.live(ledger / "commit.counts")
    return [row.key for row in rows if row.state == commit_counts.QUEUED]


def _behind(ledger: Path | None, key: str, env: Mapping[str, str]) -> list[trainjoin.Follower]:
    # The stacks that can join this one: none with no ledger or with the train switched off.
    if ledger is None or env.get(TRAIN_ENV) == OFF:
        return []
    return trainjoin.followers(ledger, key, queued_keys(ledger))


def lead(
    root: Path,
    ledger: Path | None,
    own: trainjoin.Follower,
    seams_env: tuple[Seams, Mapping[str, str]],
    out: TextIO,
) -> int | None:
    """Join the stacks behind `own` and run the train, or say there is none.

    Returns:
        this stack's exit code after writing its text to `out`; None when the train is off or no
        queued stack behind it could be joined.

    """
    seams, env = seams_env
    began = time.time_ns()
    followers = _behind(ledger, own.key, env)
    # ⚑ THE CONTINUOUS SIBLING TICKS ON EVERY STACK RUN, so a dark producer reads differently from
    # a repository with nothing queued; the train span below is event-driven.
    traintel.consider(root.name, len(followers), env)
    if ledger is None or not followers:
        return None
    # ⚑ W1705: THE COUNT IS LEFT IN THE LEDGER so a withdraw of this run names the followers it
    # would refuse too, and says no.
    commit_counts.note_joined(ledger / "commit.counts", own.key, len(followers))
    stats = traintel.Stats()
    code: int | None = None
    ends = traindrive.drive(
        root, [own, *followers], seams, stats, lambda rec: trainround.emit(root.name, rec, env)
    )
    for verdict in ends:
        if verdict.key == own.key:
            out.write(verdict.text)
            code = verdict.code
        elif not trainverdict.write(ledger, verdict):
            sys.stderr.write(f"mikemol-commit: no verdict could be left for stack {verdict.key}\n")
    traintel.emit(root.name, stats, (began, time.time_ns()), env)
    return MISSING if code is None else code
