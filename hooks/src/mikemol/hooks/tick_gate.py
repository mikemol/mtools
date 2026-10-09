# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W812: the UserPromptSubmit tick gate: a tick prompt that cannot run is refused before a turn.

The host's loop prompt ("paths-forward tick (host session ...)") arrives every ten minutes. When the
machine cannot do the work, answering it costs a model turn and achieves nothing: on 2026-10-06 the
zram device behind the temp filesystems reached its ceiling, every shell command failed, and about
fifteen ticks each spent a turn saying so. A hook runs in its own process, outside the shell tool's
output path, so this one still works when every command fails.

For a tick prompt it answers one of three ways:
  - the zram device is at or past REFUSE_FRACTION of its real ceiling: BLOCK, saying so;
  - the host tick lock is held and fresh: BLOCK ("held under 30 minutes old: exit silently" is
    already the procedure; this makes it free);
  - otherwise: add the two facts as context, so the tick starts knowing them.
Any other prompt passes untouched, and the facts are not even read.

⚑ A FACT THAT CANNOT BE READ BLOCKS NOTHING (host_facts: absent, never zeros): an unreadable
mm_stat or queue is named in the context line as "not checked", and the tick proceeds.

⚑ THE PAYLOAD'S PROMPT KEY IS READ AS `prompt`, FALLING BACK TO `user_message`. MEASURED LIVE
(mtools:W820, 2026-10-09): a `[paths-forward tick] ...` cron prompt in the mtools session received
the "tick gate: zram1 ..." line as UserPromptSubmit context, so the payload does carry the prompt
under one of the two keys this reads. Which of the two it is was not isolated (no payload was
captured), and the fallback makes that immaterial to the gate.

⚑ NO ARMING VARIABLE: it blocks or adds context, with no advisory mode, and this file must not
spell that variable's name (the wiring arm reads a module that does as one that arms).
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING, NamedTuple

from mikemol.hooks.host_facts import GIB, REFUSE_FRACTION, zram_headroom
from mikemol.hooks.payload import as_record, text_of
from mikemol.hooks.tick_stop import fresh, payload_lock

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TextIO

    from mikemol.hooks.host_facts import Headroom, HostLock

# The loop prompt begins with this; a user mentioning a tick mid-sentence is not one.
TICK_PREFIX = "paths-forward tick"
# The host session's own cron prompt (github-45, 2026-10-09) begins with this instead, so the zram
# gate never saw it: "tick: host session paths-forward loop (...)". The whole phrase, not "tick:",
# so a user typing "tick:" is not gated.
HOST_LOOP_PREFIX = "tick: host session paths-forward loop"


class Gate(NamedTuple):
    """What to do with a tick prompt: refuse it with a reason, or let it through with context."""

    reason: str | None
    context: str | None


def is_tick(prompt: str) -> bool:
    """Say whether a prompt is the loop's tick prompt.

    ⚑ BOTH SPELLINGS (W820, github-45, 2026-10-09): the host's `paths-forward tick (...)` and the
    bracketed `[paths-forward tick] Invoke ...` that `mikemol-paths-forward --payload` emits for
    every other repository. Matching only the first meant no mtools cron prompt was ever gated. The
    lock the gate reads is the one under the PAYLOAD'S cwd, i.e. the session's own queue, so the
    skip it makes for a fresh lock is the loop's own "held and under 30 minutes: exit silently".

    ⚑ A THIRD SPELLING (github-45, 2026-10-09): the host session's own cron prompt reads `tick: host
    session paths-forward loop (...)`, which neither of the two above matches, so the host's ticks
    were never gated against zram (the operator's open question).

    Returns:
        True when the prompt, ignoring leading whitespace and one opening bracket, begins with
        TICK_PREFIX or with HOST_LOOP_PREFIX.

    """
    return prompt.lstrip().removeprefix("[").startswith((TICK_PREFIX, HOST_LOOP_PREFIX))


def facts_line(headroom: Headroom | None, lock: HostLock | None) -> str:
    """Say what the two facts read, for the tick's context.

    Returns:
        one line naming the zram use and the lock, each "not checked" when it could not be read.

    """
    if headroom is None:
        zram = "zram1 unreadable (not checked)"
    else:
        zram = (
            f"zram1 {headroom.fraction():.0%} of its {headroom.limit / GIB:.0f} GiB ceiling, "
            f"{headroom.ratio:.2f}:1, about {headroom.logical_room_gib():.0f} GiB of data fits"
        )
    if lock is None:
        held = "tick lock unreadable (not checked)"
    elif lock.held():
        held = (
            f"stale tick lock from {lock.holder} since {lock.taken_at} (tick begin takes it over)"
        )
    else:
        held = "tick lock free"
    return f"tick gate: {zram}; {held}."


def gate(headroom: Headroom | None, lock: HostLock | None, now: datetime) -> Gate:
    """Decide a tick prompt's fate from the two facts.

    Returns:
        a Gate with a reason (refused) or a context line (admitted); never both.

    """
    if headroom is not None and headroom.fraction() >= REFUSE_FRACTION:
        return Gate(
            reason=(
                f"tick refused: zram1 is at {headroom.fraction():.0%} of its "
                f"{headroom.limit / GIB:.0f} GiB ceiling (about {headroom.logical_room_gib():.0f} "
                f"GiB of data left at {headroom.ratio:.2f}:1). A write failure remounts the temp "
                "filesystems read-only and kills every shell command; free space first."
            ),
            context=None,
        )
    if lock is not None and fresh(lock, now):
        return Gate(
            reason=(
                f"tick skipped: the host tick lock is held ({lock.holder} since {lock.taken_at}) "
                "and under 30 minutes old, so a tick is running or died; the next prompt retries."
            ),
            context=None,
        )
    return Gate(reason=None, context=facts_line(headroom, lock))


def run(
    payload: dict[str, object],
    read_headroom: Callable[[], Headroom | None],
    now: datetime,
    out: TextIO,
) -> int:
    """Apply the gate to one UserPromptSubmit payload.

    Returns:
        0 always: a refusal is the decision JSON on `out`, never a nonzero exit.

    """
    prompt = text_of(payload.get("prompt")) or text_of(payload.get("user_message"))
    if not is_tick(prompt):
        return 0
    verdict = gate(read_headroom(), payload_lock(payload), now)
    if verdict.reason is not None:
        refusal: dict[str, str] = {"decision": "block", "reason": verdict.reason}
        out.write(json.dumps(refusal) + "\n")
    elif verdict.context is not None:
        admitted: dict[str, dict[str, str]] = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": verdict.context,
            }
        }
        out.write(json.dumps(admitted) + "\n")
    return 0


def main() -> int:
    """Read the UserPromptSubmit payload on stdin and apply the gate.

    An unreadable payload passes: a gate that cannot read its input must not eat a prompt.

    Returns:
        the exit code from `run`, or 0.

    """
    try:
        raw: object = json.load(sys.stdin)
    except ValueError:
        sys.stderr.write("tick-gate: the payload was not JSON; not checked\n")
        return 0
    return run(as_record(raw), zram_headroom, datetime.now(UTC), sys.stdout)
