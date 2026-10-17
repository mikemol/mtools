# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""How much unblocked work a queue holds, for the idle-session watchdog (W1474, W1475).

The watchdog fires only when a session has stopped beating AND there is work it could be doing. A
card the writer calls `ready` is by construction not blocked (a blocked card has status `blocked`),
so the count of ready cards that carry no witness is the queue check's whole answer: a witnessed
card is marked done by its evaluator, never by a mind, and is not work (`model.workable`).

⚑ A WORKING CARD IS NOT COUNTED. A session marks a card `working` while it builds, queues or gates
it, so counting those would let a session that has queued everything it can look available. The
operator's fire condition is unblocked READY cards (2026-10-17).
"""

from mikemol.pathsforward.model import State, text


def ready_count(state: State) -> int:
    """Count the cards a session could start now.

    Returns:
        the waypoints with status `ready` and no witness.

    """
    return sum(
        1 for w in state.waypoints if text(w, "status") == "ready" and not text(w, "witness")
    )
