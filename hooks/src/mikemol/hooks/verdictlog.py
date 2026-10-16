# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Turn `mikemol-commit`'s verdict lines into structured events and ship them (mtools:W1168).

The verdict is ONE LINE of a fixed grammar, and the operator asked that tool output which is
already structured reach VictoriaLogs as fields, not as a flattened string:

    COMMITTED <repo> <sha7> <subject> [<pushed>]
    REFUSED <repo> (rc=N): <why>
    NOT COMMITTED <repo>: <why>
    RACED <repo>: <why>

⚑ THE LINE IS KEPT WHOLE AS `_msg` AND ITS PARTS ARE ADDED AS FIELDS: `verdict`, `repo`, `sha`,
`subject`, `pushed`, `rc`. A line that fits none of the four (git's own output, the routing line)
is not an event and is left alone; nothing is invented for it.

⚑ SHIPPING IS THE SPOOL, NOT THE NETWORK (`vlogship.ship`): the commit's caller waits for a local
file append and a detached drainer is started, never for the endpoint.

CONSUMED BY: `commit_kata.main` with `--ship`.
"""

import datetime as dt
import json
import re
from collections.abc import Callable, Sequence
from pathlib import Path

from mikemol.hooks import vlogconfig, vlogdetach, vlogrecord, vlogship

COMMITTED = re.compile(
    r"^COMMITTED (?P<repo>\S+) (?P<sha>[0-9a-f]+) (?P<subject>.*?) \[(?P<pushed>[^\]]*)\]$"
)
REFUSED = re.compile(r"^REFUSED (?P<repo>\S+) \(rc=(?P<rc>-?\d+)\)(?:: (?P<why>.*))?$")
NOT_COMMITTED = re.compile(r"^NOT COMMITTED (?P<repo>\S+): (?P<why>.*)$")
RACED = re.compile(r"^RACED (?P<repo>\S+): (?P<why>.*)$")
VERDICTS = (
    ("COMMITTED", COMMITTED),
    ("REFUSED", REFUSED),
    ("NOT COMMITTED", NOT_COMMITTED),
    ("RACED", RACED),
)


def event_of(line: str) -> dict[str, str] | None:
    """Read one output line as a verdict event.

    Returns:
        the fields (`verdict`, `repo`, the parts that line has, and `_msg` the whole line), or
        None when the line is not one of the four verdicts.

    """
    text = line.rstrip("\n")
    for verdict, pattern in VERDICTS:
        found = pattern.match(text)
        if found:
            parts = {k: v for k, v in found.groupdict().items() if v is not None}
            return {"verdict": verdict, **parts, "_msg": text}
    return None


GATE_JOBS = re.compile(
    r"^pre-commit: gate jobs=(?P<jobs>\d+) cores=(?P<cores>\d+) load1=(?P<load1>\S+) "
    r"floor=(?P<floor>\d+)(?P<held> \(held at the floor\))?$"
)
GATE_REFUSED = "pre-commit: REFUSED — the following check(s) failed:"
CHECK_BULLET = re.compile(r"^  - (?P<check>\S.*)$")


def gate_event_of(line: str, in_refusal: bool) -> dict[str, str] | None:
    """Read one output line as an event of the commit gate (W1181).

    ⚑ THE GATE'S OWN LINES RIDE IN THE COMMIT'S OUTPUT, so no hook is touched: the job cap it was
    sized to (`GATE`, with the cores, load and floor, and `held` when the floor held it up), and
    each check the refusal named (`CHECK_FAILED`, only after the refusal header).

    Returns:
        the event, or None when the line is neither.

    """
    text = line.rstrip("\n")
    jobs = GATE_JOBS.match(text)
    if jobs:
        parts = {k: v for k, v in jobs.groupdict().items() if v is not None}
        return {"verdict": "GATE", **parts, "held": str(bool(jobs["held"])).lower(), "_msg": text}
    bullet = CHECK_BULLET.match(text) if in_refusal else None
    if bullet:
        return {"verdict": "CHECK_FAILED", "check": bullet["check"], "_msg": text}
    return None


def events_of(text: str) -> list[dict[str, str]]:
    """Read every verdict and gate line out of a block of output.

    Returns:
        the events, in order.

    """
    found: list[dict[str, str]] = []
    in_refusal = False
    for line in text.splitlines():
        if line.rstrip() == GATE_REFUSED:
            in_refusal = True
            continue
        event = event_of(line) or gate_event_of(line, in_refusal=in_refusal)
        if event is not None:
            found.append(event)
        elif not line.startswith("  - "):
            in_refusal = False
    return found


def ship_events(
    events: Sequence[dict[str, str]],
    config: vlogship.Config,
    now: Callable[[], str],
) -> int:
    """Spool the events, to be sent by a detached drainer.

    Returns:
        how many were spooled.

    """
    lines = [json.dumps(event, sort_keys=True) for event in events]
    streams = {"tool": "mikemol-commit"}
    how = vlogrecord.FieldMap(message_key="_msg")
    return vlogship.ship(lines, streams, how, config, now).spooled


def ship_text(
    text: str,
    spawn: Callable[[Sequence[str]], None] = vlogdetach.spawn_detached,
    path: Path = vlogconfig.CONFIG_PATH,
) -> int:
    """Ship the verdict lines of a block of output with the host's vlog settings.

    ⚑ BEST EFFORT AND NEVER RAISING INTO THE COMMIT: the verdict is already decided and printed, so
    a missing config or an unwritable spool can only mean the lines are not shipped.

    Returns:
        how many events were spooled, 0 when there were none or the spool could not be written.

    """
    events = events_of(text)
    if not events:
        return 0
    config = vlogconfig.build(vlogconfig.read_toml(path), vlogconfig.Flags())
    try:
        count = ship_events(events, config, lambda: vlogrecord.stamp(dt.datetime.now(dt.UTC)))
    except OSError:
        return 0
    spawn(vlogdetach.drain_argv(config))
    return count
