# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Turn a landing-verdict event into a retro scaffold for `--add-retro` (W2079).

The input is the verdict row the commit tool ships (W2128): `event` is `verdict`, with `repo`,
`verdict`, `reason`, `rc`, `waypoints` and `stack_key`. The output is a retro record (W982's form,
`retros.py`) pre-filled with the two things the reviewer must not reconstruct from memory:

- `precommit` (the ritual's G0): the `next_bounded_step` each reviewed card carried, read from the
  queue document the caller passes. The caller passes the HEAD copy, not the working one, because
  the working copy has been moving since the submit.
- `delta` (G1): the verdict, its exit status and its reason, with the stack key naming the gate
  record. ⚑ `retros.RETRO_FIELDS` has no `frozen_timeline` (nemik's record form lists one, and
  `recurring` and `one_off`), so the key rides in `delta` until the two schemas are reconciled.

⚑ A SCAFFOLD IS NOT A REVIEW. `findings` is `[]` and `enforcement_layer` is unset, so
`retros.retro_refusals` accepts the record as a scaffold and the reviewer fills the findings; a
scaffold with invented findings would be the theater G7 exists to end.

⚑ A CARD THE QUEUE DOES NOT HOLD IS SAID SO, never skipped: the precommit line names it with
`not in the queue`, so a reviewer sees that the baseline is missing and not that it was empty.
"""

from typing import cast

from mikemol.pathsforward.model import Json

NOT_IN_QUEUE = "not in the queue"
NO_STEP = "no next step recorded"


def _step_of(queue: Json, symbol: str) -> str:
    # The next bounded step the queue records for one symbol, or why there is none.
    cards = queue.get("waypoints")
    if not isinstance(cards, list):
        return NOT_IN_QUEUE
    for card in cast("list[object]", cards):
        if isinstance(card, dict) and cast("Json", card).get("symbol") == symbol:
            step = cast("Json", card).get("next_bounded_step")
            return step.strip() if isinstance(step, str) and step.strip() else NO_STEP
    return NOT_IN_QUEUE


def _waypoints(event: Json) -> list[str]:
    listed = event.get("waypoints")
    if not isinstance(listed, list):
        return []
    return [str(item) for item in cast("list[object]", listed)]


def scaffold(event: Json, queue: Json) -> Json:
    """Build a retro scaffold from a verdict event and the queue as it stood at submit.

    Returns:
        a retro record with `card`, `trigger`, `precommit`, `frozen_timeline` and `delta` filled,
        `findings` empty and no `enforcement_layer`.

    """
    symbols = _waypoints(event)
    verdict = str(event.get("verdict", ""))
    reason = str(event.get("reason", ""))
    return {
        "card": ", ".join(symbols),
        "trigger": f"{verdict}: {reason}" if reason else verdict,
        "precommit": "; ".join(f"{symbol}: {_step_of(queue, symbol)}" for symbol in symbols),
        "delta": (
            f"verdict {verdict}, rc {event.get('rc', '')}: {reason} "
            f"(gate record {event.get('stack_key', '')})"
        ),
        "findings": [],
    }
