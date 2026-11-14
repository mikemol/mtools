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

⚑ A LEADER WITH LIVE FOLLOWERS IS REFUSED, NAMING THE COUNT. A train that gates the joined tip
treats a gate that stops as a red tip and bisects it, so withdrawing the leader would refuse every
follower that asked for nothing (option (b), carded for when the train has real runs behind it).

⚑ ONLY LIVE FOLLOWERS COUNT (W2067): the leader recorded how many stacks it joined once, at join
time, and a follower whose client exited (a withdraw, a kill, exit 143) left the live map while the
count stayed, so a lead could not be withdrawn over followers that no longer existed (nemik's
stack596, then this repository's stack 36). `live_followers` caps the recorded count by the live
submissions with a later key.

⚑ THE KEY IS READ FROM THE LIVE MAP, AND THE PID WITH ITS START TIME: a recycled pid is not the
submission and is never signalled, and a marker is named for its key so a stale one cannot stop a
later gate.
"""

import os
import signal
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks import bazelstop
from mikemol.hooks.commit_counts import INFLIGHT, Live, Probe, live, pid_of, proc_start

Kill = Callable[[int, int], None]
EXIT_WITHDRAWN = 0
EXIT_FAILED = 1
EXIT_REFUSED = 4
EXIT_LANDED = 5
EXIT_UNKNOWN = 7
POLL_S = 2.0
SHORT = 7
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


def live_followers(row: Live, rows: dict[str, Live]) -> int:
    """Count the followers a train leader still has, capping its recorded joined count.

    ⚑ A FOLLOWER IS A LIVE SUBMISSION WITH A LATER KEY: keys are submission times, and a joined
    stack stays in the map until its client exits.

    Returns:
        the followers a withdraw of the leader would still refuse.

    """
    behind = sum(1 for other in rows.values() if int(other.key) > int(row.key))
    return min(row.joined, behind)


def _ask_to_stop(
    counts: Path, row: Live, pid: int, stop: tuple[Kill, bazelstop.Table], followers: int
) -> tuple[int, str]:
    # An in-flight submission: a marker for its gate, its bazel client interrupted, or a refusal
    # naming the followers it leads.
    if followers:
        said = f"leads {followers} joined stack(s); withdrawing it would refuse them too"
        return EXIT_REFUSED, f"mikemol-commit: {row.key} is in flight and {said}"
    marker_path(counts, row.key).write_text("", encoding="utf-8")
    sent = bazelstop.interrupt(pid, *stop)
    if sent:
        return EXIT_WITHDRAWN, f"WITHDRAW REQUESTED {row.key}: " + INTERRUPTED.format(
            pids=", ".join(str(each) for each in sent)
        )
    return EXIT_WITHDRAWN, f"WITHDRAW REQUESTED {row.key}: {STOPS_AT}"


@dataclass(frozen=True)
class Witness:
    """The repository facts and hands a settled withdraw uses after it asks a gate to stop (W2378).

    `head` is the repository's HEAD sha (None when unreadable), `since` the (sha, subject) of the
    commits after a sha, newest first (None when the log could not be read, which is NOT the same
    as no commits), and `sleep` how the wait between two looks at the live map is spent: the wait
    ends when the submission leaves the map, never on a clock. `probe`, `kill` and `table` are the
    same effects `withdraw` takes, so one object carries them all.
    """

    repo: str
    head: Callable[[], str | None]
    since: Callable[[str], list[tuple[str, str]] | None]
    sleep: Callable[[float], None] = time.sleep
    probe: Probe = proc_start
    kill: Kill = os.kill
    table: bazelstop.Table = bazelstop.process_table


def _landed(row: Live, commits: list[tuple[str, str]]) -> str | None:
    """Name the commit among `commits` that landed for submission `row`.

    ⚑ THE SUBMISSION IS RECOGNISED BY ITS FIRST WAYPOINT AT THE START OF A SUBJECT, within the
    commits that appeared since the withdraw was asked: a heuristic, so a companion that recurs
    across stacks (W2219) cannot be mistaken for it from an older commit.

    Returns:
        the short sha of the first such commit, or None when none matches.

    """
    if not row.waypoints:
        return None
    lead = row.waypoints[0] + " "
    found = (sha[:SHORT] for sha, subject in commits if subject.startswith(lead))
    return next(found, None)


def _unknown(witness: Witness, row: Live, why: str) -> tuple[int, str]:
    """Say that what became of the entry could not be read, which is never WITHDRAWN.

    ⚑ AN UNKNOWN OUTCOME IS NOT A GOOD ONE (github-cb, B1 of the b66 review): the three incidents
    of this card were each a WITHDRAWN that was not true, so a withdraw that cannot read HEAD or the
    log says UNKNOWN with the fleet's cannot-judge exit and the pinned trees stay pinned.

    Returns:
        EXIT_UNKNOWN and the UNKNOWN line naming what could not be read.

    """
    return EXIT_UNKNOWN, f"UNKNOWN {witness.repo} {row.key}: {why}"


def _settle(path: Path, row: Live, witness: Witness, before: str | None) -> tuple[int, str]:
    """Wait for an asked-to-stop submission to leave the live map, then say what became of it.

    ⚑ A WITHDRAW IS AN OUTCOME, NOT AN INTENT (W2378, three incidents): the gate may already be
    past its last boundary and land anyway, so the verdict is read after the entry resolves.

    Returns:
        EXIT_LANDED and a LANDED line naming the sha when the commit landed, EXIT_WITHDRAWN and a
        WITHDRAWN line when HEAD and the log were read and nothing landed, else EXIT_UNKNOWN.

    """
    while any(each.key == row.key for each in live(path, witness.probe)):
        witness.sleep(POLL_S)
    if before is None:
        return _unknown(witness, row, "HEAD could not be read when the withdraw was asked")
    commits = witness.since(before)
    if commits is None:
        return _unknown(witness, row, f"the commits since {before[:SHORT]} could not be read")
    sha = _landed(row, commits)
    if sha is not None:
        return EXIT_LANDED, f"LANDED {witness.repo} {sha} (withdraw too late)"
    return EXIT_WITHDRAWN, f"WITHDRAWN {witness.repo} {row.key}"


def _inflight(
    path: Path,
    target: tuple[Live, int],
    rows: dict[str, Live],
    stop: tuple[Kill, bazelstop.Table],
    witness: Witness | None,
) -> tuple[int, str]:
    # Ask the gate to stop; with a witness, wait for the outcome and report it.
    row, pid = target
    before = witness.head() if witness is not None else None
    code, text = _ask_to_stop(path, row, pid, stop, live_followers(row, rows))
    if code != EXIT_WITHDRAWN or witness is None:
        return code, text
    return _settle(path, row, witness, before)


def _run(
    path: Path, key: str, hands: tuple[Probe, Kill, bazelstop.Table], witness: Witness | None
) -> tuple[int, str]:
    probe, kill, table = hands
    rows = {row.key: row for row in live(path, probe)}
    row = rows.get(key)
    pid = pid_of(path, key, probe)
    if row is None or pid is None:
        return EXIT_FAILED, f"mikemol-commit: no live submission {key}"
    if row.state == INFLIGHT:
        return _inflight(path, (row, pid), rows, (kill, table), witness)
    kill(pid, signal.SIGTERM)
    return EXIT_WITHDRAWN, f"WITHDRAWN {key} ({', '.join(row.waypoints) or 'no waypoints'})"


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
        to print. An in-flight submission is only ASKED to stop here; `withdraw_settled` waits.

    """
    return _run(path, key, (probe, kill, table), None)


def withdraw_settled(path: Path, key: str, witness: Witness) -> tuple[int, str]:
    """Withdraw the submission `key` and, when it is in flight, wait for what became of it.

    ⚑ ONE VERDICT LINE, THE FINAL STATE (W2378): WITHDRAWN when the gate stopped, LANDED with the
    sha when it was already past its last boundary and committed anyway. A queued submission is
    ended at once, as `withdraw` does.

    Returns:
        the exit code (0 withdrawn, 1 no live submission, 4 refused, 5 landed anyway, 7 the
        outcome could not be read) and the line.

    """
    return _run(path, key, (witness.probe, witness.kill, witness.table), witness)
