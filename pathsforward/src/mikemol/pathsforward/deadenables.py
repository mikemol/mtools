# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Clear the `enables` edges whose target does not wait on their source (W1614, nemik:W695).

⚑ AN `enables` EDGE SAYS "FINISHING THIS UNBLOCKS THAT", and the ranker adds the target's weight to
the source. When the target is an open card of this queue that does not list the source in
`blocked_on`, the two edges disagree: the target never waited on the source, so finishing the
source unblocks nothing, and the source ranks above its work. nemik reports each as an Info row
(`enables ... which does not wait on it`) and offers two repairs: add the `blocked_on`, or drop the
`enables` edge.

⚑ THIS DROPS THE EDGE, NEVER ADDS THE BLOCK: adding a `blocked_on` would move a ready or working
card to blocked, which changes what the loop does; dropping a dead edge changes only the ranking
weight. A card that should wait is blocked deliberately with `--update`.

⚑ ONLY LOCAL TARGETS ARE JUDGED. A target with a colon (`repo:W<n>`) is another queue's card and
this queue cannot read whether it waits; nemik reads both queues and reports those. A closed
source or a closed target is skipped: `EdgeIntoDroppedShape` and the prune own them.

CONSUMED BY: `--clear-dead-enables [--write]` (`cli._clear_dead_enables`).
"""

from mikemol.pathsforward.model import State, strlist, text

_CLOSED = frozenset({"", "done", "dropped"})


def plan(state: State) -> list[tuple[str, str]]:
    """Name each local `enables` edge whose open target does not list the source as a blocker.

    Returns:
        `(source, target)` pairs in queue order, a source's targets in the order it lists them.

    """
    by_symbol = {text(w, "symbol"): w for w in state.waypoints}
    dead: list[tuple[str, str]] = []
    for card in state.waypoints:
        source = text(card, "symbol")
        if text(card, "status") in _CLOSED:
            continue
        for target in strlist(card, "enables"):
            held = by_symbol.get(target)
            if held is None or text(held, "status") in _CLOSED:
                continue
            if source not in strlist(held, "blocked_on"):
                dead.append((source, target))
    return dead


def apply(state: State, dead: list[tuple[str, str]]) -> None:
    """Drop each dead edge from its source's `enables` list.

    The source's other edges keep their order.
    """
    gone = {source: {t for s, t in dead if s == source} for source, _target in dead}
    for card in state.waypoints:
        drop = gone.get(text(card, "symbol"))
        if drop:
            card["enables"] = [t for t in strlist(card, "enables") if t not in drop]
