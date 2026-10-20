# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-commit REPO --withdraw KEY`: take a submission out of the queue (W1703, W1705).

A stack submitted over a base that will refuse it (a cumulative registry naming files only a
predecessor adds) holds a place in the strictly serial queue and costs a whole gate to learn what
its owner already knows. The loop prompt tells a session to withdraw a queued run it knows will
fail, and until this the only way was a signal sent by hand, which is not the tool's own path.

⚑ A QUEUED SUBMISSION IS ENDED. It waits on the one ahead of it and holds no child process, so
SIGTERM to that one process ends nothing else.

⚑ AN IN-FLIGHT ONE IS ASKED TO STOP, NEVER SIGNALLED (W1705). It owns a gate: its `git hook run`,
the bash script and bazel are children of it, and ending the parent alone would orphan them to keep
mutating the staged tree, the defect this repository has already measured. So a marker file keyed
to the submission is written and the gate's `phase()` stops at its next boundary, between stages,
with no child live.

⚑ THE BAZEL PHASE HAS NO BOUNDARY, SO ITS CLIENT IS INTERRUPTED TOO (W1757): a gate known to be
dead burned 20 to 36 minutes under load waiting for a boundary that bazel's phase never reaches.
SIGINT goes to the bazel CLIENT among the submission's descendants (`bazelstop`), bazel's own
cancellation, never the server and never the process group; the gate then takes its normal release
path. The marker stays as the fallback for every phase that is not bazel.

⚑ A LEADER WITH JOINED FOLLOWERS IS REFUSED, NAMING THE COUNT. A train that gates the joined tip
treats a gate that stops as a red tip and bisects it, so withdrawing the leader would refuse every
follower that asked for nothing (option (b), carded for when the train has real runs behind it).

⚑ THE KEY IS READ FROM THE LIVE MAP, AND THE PID WITH ITS START TIME: a recycled pid is not the
submission and is never signalled, and a marker is named for its key so a stale one cannot stop a
later gate.
"""

import os
import signal
from collections.abc import Callable
from pathlib import Path

from mikemol.hooks import bazelstop
from mikemol.hooks.commit_counts import INFLIGHT, Live, Probe, live, pid_of, proc_start

Kill = Callable[[int, int], None]
EXIT_WITHDRAWN = 0
EXIT_FAILED = 1
EXIT_REFUSED = 4
MARKER_PREFIX = "withdraw-"
STOPS_AT = "its gate stops at the next phase boundary"
INTERRUPTED = "its bazel client was interrupted (pid {pids}); its gate takes its release path"


def marker_path(counts: Path, key: str) -> Path:
    """Name the file whose presence asks the gate of submission `key` to stop.

    Returns:
        the marker's path, beside the live-commit map and named for the key.

    """
    return counts.parent / f"{MARKER_PREFIX}{key}"


def clear_marker(counts: Path, key: str) -> None:
    """Remove the stop marker of submission `key` once its run ends; never raises.

    ⚑ THE MARKER GOES WHEN THE RUN ENDS, WHATEVER ENDED IT, and the gate removes it itself when it
    stops, so a marker cannot outlive its submission; the key in its name keeps a stale one from
    meeting a later gate.
    """
    try:
        marker_path(counts, key).unlink(missing_ok=True)
    except OSError:
        return


def _ask_to_stop(
    counts: Path, row: Live, pid: int, stop: tuple[Kill, bazelstop.Table]
) -> tuple[int, str]:
    # An in-flight submission: a marker for its gate, its bazel client interrupted, or a refusal
    # naming the followers it leads.
    if row.joined:
        said = f"leads {row.joined} joined stack(s); withdrawing it would refuse them too"
        return EXIT_REFUSED, f"mikemol-commit: {row.key} is in flight and {said}"
    marker_path(counts, row.key).write_text("", encoding="utf-8")
    sent = bazelstop.interrupt(pid, *stop)
    if sent:
        return EXIT_WITHDRAWN, f"WITHDRAW REQUESTED {row.key}: " + INTERRUPTED.format(
            pids=", ".join(str(each) for each in sent)
        )
    return EXIT_WITHDRAWN, f"WITHDRAW REQUESTED {row.key}: {STOPS_AT}"


def withdraw(
    path: Path,
    key: str,
    probe: Probe = proc_start,
    kill: Kill = os.kill,
    table: bazelstop.Table = bazelstop.process_table,
) -> tuple[int, str]:
    """Withdraw the submission `key`, or say why it cannot be.

    Returns:
        the exit code (0 withdrawn or asked to stop, 1 no live submission, 4 refused) and the line
        to print.

    """
    rows = {row.key: row for row in live(path, probe)}
    row = rows.get(key)
    pid = pid_of(path, key, probe)
    if row is None or pid is None:
        return EXIT_FAILED, f"mikemol-commit: no live submission {key}"
    if row.state == INFLIGHT:
        return _ask_to_stop(path, row, pid, (kill, table))
    kill(pid, signal.SIGTERM)
    return EXIT_WITHDRAWN, f"WITHDRAWN {key} ({', '.join(row.waypoints) or 'no waypoints'})"
