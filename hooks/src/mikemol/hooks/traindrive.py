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

⚑ A WITHDRAWN GATE IS NOT A RED TIP (W1944): a gate that exits the withdraw code was stopped on
purpose, by `mikemol-commit --withdraw`, at a phase boundary. Bisecting it would burn gates on a
tree nobody judged and refuse followers that asked for nothing. So the train stops, lands
nothing, tells the leader's own process it was withdrawn, and gives every other group NO
verdict: `trainverdict` reads a missing file as 'run on your own turn as before', so each
follower gates its own stack singly.

⚑ THE TRAIN COUNTS ITSELF (W1676): `Stats` gets the stacks joined, gates run, bisect steps, rounds,
and how many landed, were refused and were dropped, for `traintel` to record as one span.

CONSUMED BY: the merge train in `commit_kata` (W1654); `trainjoin` supplies the groups.
"""

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks import trainbisect, trainround
from mikemol.hooks.commit_verdict import WITHDRAW_RC
from mikemol.hooks.gatephase import failed_checks
from mikemol.hooks.isolated import Done
from mikemol.hooks.stackgate import gate_tip
from mikemol.hooks.stackland import Entry, Stack, build
from mikemol.hooks.stacklanding import land
from mikemol.hooks.stackrun import (
    EXIT_RACED,
    SHORT,
    History,
    Item,
    Seams,
    culprit_note,
    entries_for,
    refusal_line,
)
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


def _entries(groups: Sequence[Group], seams: Seams) -> list[Entry]:
    # The stack entries of every group's items, in order, for one build. ⚑ EACH GROUP IS BUILT
    # ALONE: the Admission trailer is a group's own, judged on its own items, so a group a row
    # admits is not judged by what rides beside it (the 759a7e68 review, F1).
    return [entry for group in groups for entry in entries_for(group.items, seams)]


def _drop_paced(
    remaining: list[Group],
    verdicts: list[Verdict],
    count: Stats,
    seams: Seams,
    who: tuple[str, str],
) -> bool:
    # Tell the first group the pace still refuses at the landing, drop it from the train and say
    # whether one was dropped. ⚑ A REFUSAL IS A GROUP'S VERDICT, NEVER AN EXCEPTION (the 759a7e68
    # review, F2): the other groups go on.
    name, before = who
    for place, group in enumerate(remaining):
        reason = seams.landing_refusal(group.items)
        if reason is not None:
            text = refusal_line(name, reason) + f" HEAD is {before[:SHORT]}.\n"
            verdicts.append(Verdict(group.key, 1, text))
            count.dropped += 1
            del remaining[place]
            return True
    return False


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


def _round_record(
    shape: tuple[int, int, tuple[int, int]], rnd: _Round | None, bad: int | None, verdict: str
) -> trainround.RoundRecord:
    # What one round did: the full-tip gate says how it was run, the culprit's says what failed.
    number, members, window = shape
    gates = rnd.gates if rnd is not None else {}
    first = gates.get(len(rnd.ends) - 1) if rnd is not None else None
    culprit = gates.get(bad) if bad is not None else None
    facts = trainround.facts_of(first.stdout + first.stderr) if first else trainround.GateFacts()
    failed = "; ".join(failed_checks(culprit.stdout + culprit.stderr)) if culprit else ""
    return trainround.RoundRecord(number, members, verdict, failed, len(gates), facts, window)


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


def _refused(
    group: Group, gate: Done, before: str, name: str, history: History | None = None
) -> Verdict:
    shown = (gate.stdout + gate.stderr).strip()
    head = f"{shown}\n" if shown else ""
    text = head + (
        f"REFUSED {name} (rc={gate.returncode}): the tip of the train was gated and a bisection "
        f"found this stack the first to fail; none of it landed, HEAD is {before[:SHORT]}; "
        f"{culprit_note(shown, group.items, history)}\n"
    )
    return Verdict(group.key, gate.returncode, text)


def _withdrawn(leader: Group, gate: Done, before: str, name: str) -> Verdict:
    # The leader's verdict for a train whose gate was withdrawn: a refusal the verdict reader
    # classifies as WITHDRAWN by its code, and the followers' own turns named.
    shown = (gate.stdout + gate.stderr).strip()
    head = f"{shown}\n" if shown else ""
    text = head + (
        f"REFUSED {name} (rc={gate.returncode}): the train's gate was withdrawn; nothing landed, "
        f"HEAD is still {before[:SHORT]}; the stacks that joined it run again on their own turn\n"
    )
    return Verdict(leader.key, gate.returncode, text)


def _stopped(
    gate: Done, groups: Sequence[Group], remaining: Sequence[Group], before: str, name: str
) -> list[Verdict] | None:
    # What a train whose full-tip gate was withdrawn tells its groups, or None when it was not.
    # The leader's process is `groups[0]`; once it has its verdict, nobody is left to tell.
    if gate.returncode != WITHDRAW_RC:
        return None
    if remaining[0].key != groups[0].key:
        return []
    return [_withdrawn(groups[0], gate, before, name)]


def _land_prefix(
    root: Path, groups: Sequence[Group], rnd: _Round, before: str
) -> list[Verdict] | None:
    # Land the commits of `groups` (a green prefix) and say COMMITTED for each, or None on a race.
    if not groups:
        return []
    ends = rnd.ends[: len(groups)]
    paths = [p for item in _flat(groups) for p in item.paths]
    chain = rnd.stack.commits[: ends[-1]]
    if ends[-1] < len(rnd.stack.commits):
        # ⚑ A PREFIX OF THE BUILT CHAIN WAS GATED AT ITS OWN TIP, NOT AT THE CHAIN'S (W1651, after
        # W1745): the commits were stamped for the whole chain's tip, which is red and does not
        # land, so they would name it as the tree that was tested. The prefix is built again, the
        # same trees (a commit's tree does not depend on its message), so its last commit carries
        # Gated-Tree for the boundary that was gated and the rest name that tip. A rebuild that
        # fails or yields other trees leaves the first chain, whose trees are the gated ones.
        again = build(root, _entries(groups, rnd.seams), rnd.seams.run, before)
        if again.failed is None and again.trees == rnd.stack.trees[: ends[-1]]:
            chain = again.commits
    landing = land(root, chain, before, paths, rnd.seams.run)
    if not landing.moved:
        return None
    out, start = [], 0
    for group, end in zip(groups, ends, strict=True):
        out.append(_committed(group, chain[start:end], root.name, rnd.seams))
        start = end
    return out


def _round_of(remaining: Sequence[Group], seams: Seams) -> tuple[list[Group], list[Group]]:
    """Split the groups into this round's and the ones held for a later round (W2333, B1).

    ⚑ A GROUP THAT NEEDS AN ADMISSION ENDS THE ROUND BEFORE IT: a birth's accident checks and a
    repin's one-new-sha test read HEAD, and a round judges every group at its START HEAD, not the
    HEAD after the groups before it land. Held back, the group is judged alone on the landed HEAD
    in the next round. The first group needs no break: nothing lands before it in its round.

    Returns:
        the groups up to the first one, after the first, that needs an admission, and the rest.

    """
    for at, group in enumerate(remaining):
        if at and seams.needs_admission(group.items):
            return list(remaining[:at]), list(remaining[at:])
    return list(remaining), []


def _raced(groups: Sequence[Group], name: str) -> list[Verdict]:
    """Tell each group that HEAD moved while the train was gated and none of it landed.

    Returns:
        one RACED verdict per group.

    """
    said = f"RACED {name}: HEAD moved while the train was gated; none of it landed\n"
    return [Verdict(group.key, EXIT_RACED, said) for group in groups]


def drive(
    root: Path,
    groups: Sequence[Group],
    seams: Seams,
    stats: Stats | None = None,
    on_round: Callable[[trainround.RoundRecord], object] | None = None,
) -> list[Verdict]:
    """Land what the train can and say, per group, what became of it.

    `stats`, when given, is filled with what the train did. `on_round`, when given, is called
    with a record as each round ends (W1715), so a long train is not silent until it is over.

    Returns:
        the verdicts, one per group: landed, refused, raced or not committed exactly once.

    """
    count = stats if stats is not None else Stats()
    count.joined = len(groups)
    verdicts: list[Verdict] = []
    remaining = list(groups)
    began = time.time_ns()

    def tell(verdict: str, rnd: _Round | None = None, bad: int | None = None) -> None:
        if on_round is not None:
            shape = (count.rounds, len(remaining), (began, time.time_ns()))
            on_round(_round_record(shape, rnd, bad, verdict))

    while remaining:
        began = time.time_ns()
        before = seams.run(["rev-parse", "HEAD"], {}, root).stdout.strip()
        batch, later = _round_of(remaining, seams)
        if _drop_paced(batch, verdicts, count, seams, (root.name, before)):
            remaining = [*batch, *later]
            continue
        stack = build(root, _entries(batch, seams), seams.run, before)
        count.rounds += 1
        if stack.failed is not None:
            tell(trainround.UNBUILT)
            at, verdict = _unbuilt(batch, stack, before, root.name)
            verdicts.append(verdict)
            count.dropped += 1
            del batch[at]
            remaining = [*batch, *later]
            continue
        rnd = _Round(root, batch, (stack, count), seams)
        ended = _stopped(rnd.gate(len(batch) - 1), groups, [*batch, *later], before, root.name)
        if ended is not None:
            tell(trainround.WITHDRAWN, rnd)
            return [*verdicts, *ended]
        bad = rnd.first_bad()
        landed = _land_prefix(root, batch[: len(batch) if bad is None else bad], rnd, before)
        if landed is None:
            tell(trainround.RACED, rnd, bad)
            return [*verdicts, *_raced([*batch, *later], root.name)]
        tell(trainround.GREEN if bad is None else trainround.RED, rnd, bad)
        verdicts.extend(landed)
        count.landed += len(landed)
        if bad is None:
            remaining = later
            continue
        verdicts.append(
            _refused(batch[bad], rnd.gate(bad), before, root.name, seams.history(root.name))
        )
        count.refused += 1
        remaining = [*batch[bad + 1 :], *later]
    return verdicts
