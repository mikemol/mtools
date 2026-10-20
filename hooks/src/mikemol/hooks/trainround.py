# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One record per train ROUND, sent when the round ends, so a long train answers for itself (W1715).

⚑ A TRAIN THAT RUNS THREE AND A HALF HOURS AND WRITES NOTHING UNTIL IT ENDS CANNOT ANSWER 'which
round, did it refuse, why so slow' (github-8f, 2026-10-19, operator: engineer the information source
to contain the information the question needs). `traintel` records the whole train once at its end;
this records each round as it ends: the round's number, how many stacks it carried, its verdict
(`green`, `red`, `unbuilt` or `raced`), the checks the gate's own summary lists as failed (W1728),
the gates it ran, and what the admission step told the gate.

⚑ THE ADMISSION THROTTLE IS IN THE RECORD, READ FROM THE GATE'S OWN OUTPUT: the hook prints
`gate jobs=N cores=C load1=L floor=F` before its bazel run (`gatejobs.explain`), so `jobs` and
`load1` here are what that gate was held to, and a round that took long because the host was at
load forty reads as such rather than as a slow suite. The bazel invocation id is read from the same
output, so a round's targets can be fetched by id after the fact.

⚑ A SPAN FOR THE ROUND AND TWO SAMPLES (the emitter `traintel` uses): `train.round` in the service
`mikemol-train` with the fields above and the round's own start and end, an ERROR when the round was
not green; `mikemol.train.round{repo, verdict}`, one sample per round, summed over a window; and
`mikemol.train.jobs{repo, cores}`, the admitted jobs, so the throttle is an alert and not a
recollection.

⚑ BEST EFFORT, NEVER CHANGING A VERDICT: no binary or store, or a failed spawn, means nothing is
sent, exactly as `traintel`.

CONSUMED BY: `traindrive.drive` builds the record, `trainlead.lead` sends it.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from mikemol.hooks.commit_span import binary, store_named
from mikemol.hooks.vlogdetach import spawn_detached

SERVICE = "mikemol-train"
NAME = "train.round"
ROUND_METRIC = "mikemol.train.round"
JOBS_METRIC = "mikemol.train.jobs"
GREEN = "green"
RED = "red"
UNBUILT = "unbuilt"
RACED = "raced"
Spawn = Callable[[Sequence[str]], None]

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_JOBS = re.compile(r"gate jobs=(\d+) cores=(\d+) load1=([0-9.]+)")
_INVOCATION = re.compile(rf"Invocation ID:\s*({_UUID})")


@dataclass(frozen=True, slots=True)
class GateFacts:
    """What a gate's output says about how it was run; empty where it says nothing."""

    jobs: str = ""
    cores: str = ""
    load1: str = ""
    invocation: str = ""


@dataclass(frozen=True, slots=True)
class RoundRecord:
    """One round of a train, as it ended."""

    number: int
    members: int
    verdict: str
    failed: str
    gates: int
    facts: GateFacts
    window: tuple[int, int]


def facts_of(output: str) -> GateFacts:
    """Read the admission line and the bazel invocation id out of a gate's output.

    Returns:
        the first admission line's jobs, cores and load, and the first invocation id; each empty
        when the output does not carry it (an older hook, a gate that stopped before bazel).

    """
    jobs = _JOBS.search(output)
    invocation = _INVOCATION.search(output)
    return GateFacts(
        jobs=jobs.group(1) if jobs else "",
        cores=jobs.group(2) if jobs else "",
        load1=jobs.group(3) if jobs else "",
        invocation=invocation.group(1) if invocation else "",
    )


def span_argv(program: str, repo: str, rec: RoundRecord) -> list[str]:
    """Build the `mikemol-otlp trace` argv for one round.

    Returns:
        the argv; the span is an error unless the round was green.

    """
    status = "OK" if rec.verdict == GREEN else "ERROR"
    argv = [program, "trace", "--service", SERVICE, "--namespace", repo, "--status", status]
    argv += ["--name", NAME, "--start-ns", str(rec.window[0]), "--end-ns", str(rec.window[1])]
    shown = {
        "repo": repo,
        "round": str(rec.number),
        "members": str(rec.members),
        "verdict": rec.verdict,
        "failed": rec.failed,
        "gates": str(rec.gates),
        "jobs": rec.facts.jobs,
        "cores": rec.facts.cores,
        "load1": rec.facts.load1,
        "invocation": rec.facts.invocation,
    }
    for key, value in shown.items():
        argv += ["--field", f"{key}={value}"]
    return argv


def metric_argv(who: tuple[str, str], name: str, value: str, label: tuple[str, str]) -> list[str]:
    """Build the `mikemol-otlp metric` argv for one sample.

    `who` is the program and the repo; `label` is the one pair beside `repo`.

    Returns:
        the argv.

    """
    program, repo = who
    argv = [program, "metric", "--service", SERVICE, "--namespace", repo, "--name", name]
    argv += ["--value", value, "--field", f"repo={repo}", "--field", f"{label[0]}={label[1]}"]
    return argv


def plan(program: str, repo: str, rec: RoundRecord) -> list[list[str]]:
    """Build every child one round starts.

    Returns:
        the span, the round sample, and the jobs sample when the gate said how many it was given.

    """
    who = (program, repo)
    sends = [
        span_argv(program, repo, rec),
        metric_argv(who, ROUND_METRIC, "1", ("verdict", rec.verdict)),
    ]
    if rec.facts.jobs:
        sends.append(metric_argv(who, JOBS_METRIC, rec.facts.jobs, ("cores", rec.facts.cores)))
    return sends


def emit(
    repo: str, rec: RoundRecord, env: Mapping[str, str], spawn: Spawn = spawn_detached
) -> bool:
    """Start the children for a finished round, when a binary and a store exist.

    Returns:
        whether every child was started; False with no binary or store, or a failed spawn.

    """
    program = binary(env)
    if program is None or not store_named(env):
        return False
    try:
        for argv in plan(program, repo, rec):
            spawn(argv)
    except OSError:
        return False
    return True
