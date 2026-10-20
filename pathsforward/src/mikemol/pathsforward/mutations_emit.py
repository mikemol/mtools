# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Send a mutation's events to the store as OTLP log records and metric samples (W1741).

⚑ ONE LOG RECORD PER EVENT, ONE SAMPLE PER FIELD. Each event is a JSON line on the stdin of a
detached `mikemol-otlp log` child, carrying the station `<repo>:W<n>`, the field, the old and new
values, and the mutation's own context (via, actor, a mutation id shared by the command's events,
UTC milliseconds, session, writer sha). The metric is `mikemol.waypoint.event`, one value per
distinct field in the mutation, labelled `repo`, `field` and `via` and nothing else: the values and
the station are unbounded and live in the log record only.

⚑ `mikemol-otlp` HAS NO DELTA COUNTER (gauge and up-down only), so the sample's value is how many
events of that field the mutation made, and a reader sums it over a window (`sum_over_time`).

⚑ THE CHILD, ITS RESOLVER AND ITS SPAWN ARE `refusal_record`'S (W1248), NOT A SECOND COPY: one
way to find `mikemol-otlp`, one way to name a store, one detached start. The log lines go in
chunks, so a bulk edit never writes more into the pipe than the child is sure to drain.

⚑ BEST EFFORT, NEVER RAISING INTO THE WRITE: a missing binary or store, or a child that cannot be
started, means the events are not shipped. The queue is already saved when this runs.

CONSUMED BY: `cli._mutate` (W1742).
"""

import json
import os
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.pathsforward import foreign, refusal_record
from mikemol.pathsforward.mutations import Event
from mikemol.pathsforward.refusal_record import Spawn

NAME = "mikemol.waypoint.event"
CHUNK = 100
"""The most event lines one log child is handed, well under a pipe's buffer."""


@dataclass(frozen=True, slots=True)
class Meta:
    """What one mutation shares across its events."""

    via: str
    actor: str
    mutation: str
    at_ms: int
    session: str
    sha: str


def log_line(repo: str, event: Event, meta: Meta) -> str:
    """Spell one event as the JSON line a log record carries.

    Returns:
        one line, keys sorted, no trailing newline.

    """
    body = {
        "station": f"{repo}:{event.station}",
        "field": event.field,
        "old": event.old,
        "new": event.new,
        "via": meta.via,
        "actor": meta.actor,
        "mutation": meta.mutation,
        "at_ms": meta.at_ms,
        "session": meta.session,
        "sha": meta.sha,
    }
    return json.dumps(body, sort_keys=True, ensure_ascii=False)


def metric_argv(program: str, repo: str, field: str, count: tuple[int, str]) -> list[str]:
    """Build the `mikemol-otlp metric` argv for one field of a mutation.

    `count` is the number of that field's events and the mutation's via.

    Returns:
        the argv; the labels are repo, field and via alone.

    """
    number, via = count
    argv = [program, "metric", "--service", refusal_record.SERVICE, "--namespace", repo]
    argv += ["--name", NAME, "--value", str(number)]
    for label in (("repo", repo), ("field", field), ("via", via)):
        argv += ["--field", f"{label[0]}={label[1]}"]
    return argv


def plan(
    program: str, repo: str, events: Sequence[Event], meta: Meta
) -> list[tuple[list[str], str]]:
    """Build every child a mutation starts, each with the text for its stdin.

    Returns:
        one log child per chunk of events, each fed one line per event, then one metric child per
        distinct field with the number of that field's events as its value; empty with no events.

    """
    head = [program, "log", "--service", refusal_record.SERVICE, "--namespace", repo]
    log = [*head, "--field", f"repo={repo}"]
    lines = [log_line(repo, e, meta) for e in events]
    sends = [(log, "\n".join(lines[i : i + CHUNK])) for i in range(0, len(lines), CHUNK)]
    sends += [
        (metric_argv(program, repo, field, (number, meta.via)), "")
        for field, number in Counter(e.field for e in events).items()
    ]
    return sends


def emit(
    state: Path,
    events: Sequence[Event],
    meta: Meta,
    env: Mapping[str, str] | None = None,
    start: Spawn | None = None,
) -> bool:
    """Start the children for a saved mutation's events, when a binary and a store exist.

    Returns:
        whether every child was started; False with no events, no binary or store, or a child that
        could not be started (never raised).

    """
    where = os.environ if env is None else env
    program = refusal_record.binary(where, foreign.default_root())
    if program is None or not refusal_record.store_named(where) or not events:
        return False
    repo = state.parent.parent.name
    run = refusal_record.spawn if start is None else start
    try:
        for argv, stdin in plan(program, repo, events, meta):
            run(argv, stdin)
    except OSError:
        return False
    return True
