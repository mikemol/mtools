# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run the merge train: gate the joined tip once, bisect a red, land the green (W1670).

⚑ ONE GATE FOR THE QUEUE, A BISECTION ONLY WHEN IT IS RED (github-8f and the operator, 2026-10-18:
"test the tip work and move it to the front of the queue"; line 81742 of the host transcript:
untested intermediates are accepted, "on failure, we can bisect, and then we get the tested states
as we need them"). The groups are a leader's stack and the followers `trainjoin` found. One
`stackland.build` over all their entries makes a cumulative commit and tree per entry, so the tree
after each group's last entry is already the tree a gate would judge for 'groups 0..k':

    green tip   land every commit at once; each group reports its own COMMITTED lines.
    red tip     `trainbisect.first_bad` probes boundary trees, about log2(n) gates, for the first
                group whose prefix fails; the green prefix lands, that group is REFUSED with the
                failing gate's output and a culprit note, and the groups after it are built again
                over the new head and judged as a new tip. A group that fails alone is the same
                case with an empty prefix, so a refusal never stalls the groups behind it.

⚑ EACH GROUP GETS ITS OWN VERDICT, a code and the text `run_stack` would have printed for it
(COMMITTED, REFUSED, RACED or NOT COMMITTED lines), so the leader prints its own and writes the
others' to files their waiting processes read (W1671).

⚑ A GROUP THAT CANNOT BE BUILT (a path that is not there) IS NOT COMMITTED AND DROPPED, and the
rest go on: one broken submission is not a reason to refuse the queue.

⚑ THE TRAIN COUNTS ITSELF (W1676): `Stats` gets the stacks joined, gates run, bisect steps, rounds,
and how many landed, were refused and were dropped, for `traintel` to record as one span.

CONSUMED BY: the merge train in `commit_kata` (W1654); `trainjoin` supplies the groups.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks import trainbisect
from mikemol.hooks.isolated import Done
from mikemol.hooks.stackgate import gate_tip
from mikemol.hooks.stackland import Entry, Stack, build
from mikemol.hooks.stacklanding import land
from mikemol.hooks.stackrun import EXIT_RACED, SHORT, Item, Seams, culprit_note
from mikemol.hooks.trainjoin import Follower as Group
from mikemol.hooks.traintel import Stats


@dataclass(frozen=True)
class Verdict:
    """What one group of the train is told: an exit code and the lines it would have printed."""

    key: str
    code: int
    text: str


def _ends(groups: Sequence[Group]) -> list[int]:
    # The number of entries up to and including each group: where its last commit sits.
    total, ends = 0, []
    for group in groups:
        total += len(group.items)
        ends.append(total)
    return ends


def _flat(groups: Sequence[Group]) -> list[Item]:
    return [item for group in groups for item in group.items]


class _Round:
    """One build of the remaining groups, and the gates run on its boundary trees."""

    def __init__(
        self, root: Path, groups: Sequence[Group], built: tuple[Stack, Stats], seams: Seams
    ) -> None:
        self.root, self.seams = root, seams
        self.stack, self.stats = built
        self.ends = _ends(groups)
        self.gates: dict[int, Done] = {}

    def gate(self, k: int) -> Done:
        """Gate the tree after group k's last entry, once.

        Returns:
            the gate's result.

        """
        if k not in self.gates:
            tree = self.stack.trees[self.ends[k] - 1]
            self.gates[k] = gate_tip(self.root, tree, self.seams.run, self.seams.namespace)
            self.stats.gates += 1
        return self.gates[k]

    def green(self, k: int) -> bool:
        """Say whether the prefix ending at group k passed.

        Returns:
            True when its gate exited 0.

        """
        return self.gate(k).returncode == 0

    def first_bad(self) -> int | None:
        """Find the first group whose prefix fails, gating the full tip first.

        Returns:
            its place, or None when the whole tip is green.

        """
        last = len(self.ends) - 1
        if self.green(last):
            return None
        found = trainbisect.first_bad(len(self.ends), self.green)
        self.stats.bisect_steps += found.gates
        return found.index


def _committed(group: Group, shas: Sequence[str], name: str, seams: Seams) -> Verdict:
    lines = [
        f"COMMITTED {name} {sha[:SHORT]} {item.subject} [{seams.published(sha)}]\n"
        for sha, item in zip(shas, group.items, strict=True)
    ]
    return Verdict(group.key, 0, "".join(lines))


def _unbuilt(groups: Sequence[Group], stack: Stack, before: str, name: str) -> tuple[int, Verdict]:
    # The group whose entry could not be built, and its NOT COMMITTED verdict.
    place = len(stack.commits)
    at = next((i for i, end in enumerate(_ends(groups)) if place < end), len(groups) - 1)
    why = ((stack.failed.stderr or stack.failed.stdout) if stack.failed else "").strip()
    code = (stack.failed.returncode if stack.failed else 0) or 1
    text = (
        f"NOT COMMITTED {name}: stack entry {place + 1} could not be built: {why}; "
        f"nothing landed, HEAD is still {before[:SHORT]}\n"
    )
    return at, Verdict(groups[at].key, code, text)


def _refused(group: Group, gate: Done, before: str, name: str) -> Verdict:
    shown = (gate.stdout + gate.stderr).strip()
    head = f"{shown}\n" if shown else ""
    text = head + (
        f"REFUSED {name} (rc={gate.returncode}): the tip of the train was gated and a bisection "
        f"found this stack the first to fail; none of it landed, HEAD is {before[:SHORT]}; "
        f"{culprit_note(shown, group.items)}\n"
    )
    return Verdict(group.key, gate.returncode, text)


def _land_prefix(
    root: Path, groups: Sequence[Group], rnd: _Round, before: str
) -> list[Verdict] | None:
    # Land the commits of `groups` (a green prefix) and say COMMITTED for each, or None on a race.
    if not groups:
        return []
    ends = rnd.ends[: len(groups)]
    paths = [p for item in _flat(groups) for p in item.paths]
    landing = land(root, rnd.stack.commits[: ends[-1]], before, paths, rnd.seams.run)
    if not landing.moved:
        return None
    out, start = [], 0
    for group, end in zip(groups, ends, strict=True):
        out.append(_committed(group, rnd.stack.commits[start:end], root.name, rnd.seams))
        start = end
    return out


def drive(
    root: Path, groups: Sequence[Group], seams: Seams, stats: Stats | None = None
) -> list[Verdict]:
    """Land what the train can and say, per group, what became of it.

    `stats`, when given, is filled with what the train did.

    Returns:
        the verdicts, one per group: landed, refused, raced or not committed exactly once.

    """
    name, run = root.name, seams.run
    count = stats if stats is not None else Stats()
    count.joined = len(groups)
    verdicts: list[Verdict] = []
    remaining = list(groups)
    while remaining:
        before = run(["rev-parse", "HEAD"], {}, root).stdout.strip()
        entries = [Entry(seams.message_of(i), i.paths, i.files) for i in _flat(remaining)]
        stack = build(root, entries, run, before)
        count.rounds += 1
        if stack.failed is not None:
            at, verdict = _unbuilt(remaining, stack, before, name)
            verdicts.append(verdict)
            count.dropped += 1
            del remaining[at]
            continue
        rnd = _Round(root, remaining, (stack, count), seams)
        bad = rnd.first_bad()
        cut = len(remaining) if bad is None else bad
        landed = _land_prefix(root, remaining[:cut], rnd, before)
        if landed is None:
            text = f"RACED {name}: HEAD moved while the train was gated; none of it landed\n"
            return [*verdicts, *(Verdict(g.key, EXIT_RACED, text) for g in remaining)]
        verdicts.extend(landed)
        count.landed += len(landed)
        if bad is None:
            return verdicts
        verdicts.append(_refused(remaining[bad], rnd.gate(bad), before, name))
        count.refused += 1
        remaining = remaining[bad + 1 :]
    return verdicts
