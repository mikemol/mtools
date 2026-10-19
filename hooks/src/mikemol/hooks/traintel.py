# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One record per merge train: stacks joined, gates run, bisect steps, landed and refused (W1676).

⚑ SO 'DID THE TRAIN CUT LATENCY' IS A PANEL, NOT A RECOLLECTION (github-8f, 2026-10-19): a train
is one span, `train` in the service `mikemol-train`, from the moment the leader began to join
followers to the moment the last verdict was decided, carrying as fields the counts that decide
whether it paid: `joined` stacks, `gates` run, `bisect_steps` among them, `rounds` (a refusal
starts another round over the new head), and how many stacks `landed`, were `refused` and were
`dropped` as unbuildable. A train that bisects often shows as a `bisect_steps` signal, and a
train's gates against its `joined` is the saving: one gate for N stacks.

⚑ ITS OWN FAMILY, NOT A FIELD ON THE COMMIT SPAN: the commit span is one run's wait and gate; a
train spans several stacks' verdicts, so putting it on one stack's span would count it once per
leader and hide a train that joined nobody. A train that joined nobody is not recorded at all.

⚑ THE SEND IS FIRE AND FORGET AND SILENT, as the commit span's: no binary or no store means no
record, a failed spawn is ignored, and the record never changes a verdict.

CONSUMED BY: `trainlead.lead`; `traindrive.drive` fills the counts.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from mikemol.hooks.commit_span import binary, store_named
from mikemol.hooks.vlogdetach import spawn_detached

SERVICE = "mikemol-train"
NAME = "train"
MIN_JOINED = 2
Spawn = Callable[[Sequence[str]], None]


@dataclass
class Stats:
    """What a train did, counted as it ran."""

    joined: int = 0
    gates: int = 0
    bisect_steps: int = 0
    rounds: int = 0
    landed: int = 0
    refused: int = 0
    dropped: int = 0

    def fields(self) -> dict[str, str]:
        """Spell the counts as the span's fields.

        Returns:
            each count under its own name, as text.

        """
        return {
            "joined": str(self.joined),
            "gates": str(self.gates),
            "bisect_steps": str(self.bisect_steps),
            "rounds": str(self.rounds),
            "landed": str(self.landed),
            "refused": str(self.refused),
            "dropped": str(self.dropped),
        }


def argv_for(program: str, repo: str, stats: Stats, window: tuple[int, int]) -> list[str]:
    """Build the `mikemol-otlp trace` argv for one train.

    Returns:
        the argv; the span is an error when anything was refused or dropped.

    """
    status = "ERROR" if stats.refused or stats.dropped else "OK"
    argv = [program, "trace", "--service", SERVICE, "--namespace", repo, "--status", status]
    argv += ["--name", NAME, "--start-ns", str(window[0]), "--end-ns", str(window[1])]
    for key, value in {"repo": repo, **stats.fields()}.items():
        argv += ["--field", f"{key}={value}"]
    return argv


CONSIDERED = "mikemol.train.considered"


def considered_argv(program: str, repo: str, followers: int) -> list[str]:
    """Build the `mikemol-otlp metric` argv for one stack run that considered leading a train.

    Returns:
        the argv; the value is 1 and `followers` says how many stacks it found behind it.

    """
    argv = [program, "metric", "--service", SERVICE, "--namespace", repo, "--name", CONSIDERED]
    argv += ["--value", "1", "--field", f"repo={repo}", "--field", f"followers={followers}"]
    return argv


def consider(
    repo: str, followers: int, env: Mapping[str, str], spawn: Spawn = spawn_detached
) -> bool:
    """Tick the continuous sibling of the train span: this stack run looked for followers.

    ⚑ THE TRAIN SPAN IS EVENT-DRIVEN (no train, no span), so a freshness rule cannot tell 'no train
    was needed' from 'the producer is dark'. This ticks on EVERY stack run, whether or not anyone
    was found, so a quiet `mikemol.train.considered` is a dark producer and a quiet `train` span
    beside a live counter is a repository with nothing queued (luthen's registry, via github-8f).

    Returns:
        whether the child was started; False with no binary or store or a failed spawn.

    """
    program = binary(env)
    if program is None or not store_named(env):
        return False
    try:
        spawn(considered_argv(program, repo, followers))
    except OSError:
        return False
    return True


def emit(
    repo: str,
    stats: Stats,
    window: tuple[int, int],
    env: Mapping[str, str],
    spawn: Spawn = spawn_detached,
) -> bool:
    """Start the span child for a finished train, when a child and a store exist.

    Returns:
        whether the child was started; False when nobody was joined, there is no binary or store,
        or the spawn failed (never raised).

    """
    program = binary(env)
    if stats.joined < MIN_JOINED or program is None or not store_named(env):
        return False
    try:
        spawn(argv_for(program, repo, stats, window))
    except OSError:
        return False
    return True
