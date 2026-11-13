# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The guard's trip record: one JSON line per event, and the counter read from those lines (W2359).

A guard that signals or freezes a gate leaves only a stderr line today, so a fire is invisible to
anyone not watching that terminal (luthen-observability:W2036 asked for it to be visible). This is
the record half of W2356's unit 3: `guard_cli` appends one line per event (`trip`, `freeze`,
`resume:cleared`, `cap:resume`, `cap:kill`) and renders the counter beside it.

⚑ THE RECORD SHAPE IS THE FENCE'S, THE CONSUMER IS LUTHEN'S: this module owns the line grammar;
luthen reads the JSON lines and the counter file through its textfile collector. The counter is
`mikemol_guard_events_total{guard,event}` in Prometheus text form, DERIVED from the lines every
time (never kept as a second count that could drift). No runtime dependency on another dist: the
text form is what the host's textfile collector already reads, and an OTLP push is the consumer's
step.
⚑ A RECORD THAT CANNOT BE WRITTEN NEVER BLOCKS THE COMMAND: the caller says so on stderr, as a
broken policy is said and the command still runs (guard_cli's own rule).
"""

import json
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

ENV = "MIKEMOL_GUARD_RECORD"
DEFAULT_RECORD = Path("~/.local/state/mikemol/guard-events.jsonl")
COUNTER_SUFFIX = ".prom"
COUNTER_NAME = "mikemol_guard_events_total"
_MODE = 0o644


@dataclass(frozen=True)
class Entry:
    """One event of one guard, with what is needed to place it afterwards."""

    at: str
    guard: str
    event: str
    pids: tuple[int, ...]
    repo: str
    command: str
    owner: int
    limit: float
    peak: float | None


def record_path(environ: Mapping[str, str]) -> Path:
    """Choose where the record goes: the environment's path, else the host default.

    Returns:
        the path, with a leading `~` expanded.

    """
    return Path(environ.get(ENV) or DEFAULT_RECORD).expanduser()


def counter_path(record: Path) -> Path:
    """Name the counter file that sits beside a record.

    Returns:
        the record's path with the counter suffix appended.

    """
    return record.with_name(record.name + COUNTER_SUFFIX)


def line(entry: Entry) -> str:
    """Render one entry as a JSON line.

    Returns:
        a single line of sorted-key JSON ending in a newline.

    """
    body = {
        "at": entry.at,
        "guard": entry.guard,
        "event": entry.event,
        "pids": list(entry.pids),
        "repo": entry.repo,
        "command": entry.command,
        "owner": entry.owner,
        "limit": entry.limit,
        "peak": entry.peak,
    }
    return json.dumps(body, sort_keys=True) + "\n"


def append(record: Path, entries: Iterable[Entry]) -> None:
    """Append the entries to the record in one write, creating its directory.

    ⚑ ONE `write` OF ONE BUFFER ON AN `O_APPEND` DESCRIPTOR: two guards finishing together cannot
    interleave inside a line, and an earlier record is never rewritten.

    """
    blob = "".join(line(entry) for entry in entries)
    if not blob:
        return
    record.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(record, os.O_WRONLY | os.O_APPEND | os.O_CREAT, _MODE)
    try:
        os.write(descriptor, blob.encode("utf-8"))
    finally:
        os.close(descriptor)


def _key_of(raw: str) -> tuple[str, str] | None:
    try:
        row = cast("object", json.loads(raw))
    except ValueError:
        return None
    if not isinstance(row, dict):
        return None
    fields = cast("dict[str, object]", row)
    guard = fields.get("guard")
    return (guard, str(fields.get("event", ""))) if isinstance(guard, str) else None


def counts(record: Path) -> dict[tuple[str, str], int]:
    """Count the record's lines by guard and event.

    Returns:
        the count per `(guard, event)`; a blank or unparseable line is skipped, a missing record
        is empty.

    """
    try:
        text = record.read_text(encoding="utf-8")
    except OSError:
        return {}
    tally: dict[tuple[str, str], int] = {}
    for raw in text.splitlines():
        key = _key_of(raw)
        if key is not None:
            tally[key] = tally.get(key, 0) + 1
    return tally


def _label(value: str) -> str:
    """Escape a label value as the Prometheus exposition format requires.

    ⚑ AN UNESCAPED QUOTE, BACKSLASH OR NEWLINE CORRUPTS THE WHOLE FILE (github-cb, b65): the
    textfile collector drops a .prom file it cannot parse, every series in it, and the policy
    accepts any non-empty guard name.

    Returns:
        the value with each backslash, double quote and newline written as an escape.

    """
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def counter_text(record: Path) -> str:
    """Render the counter in Prometheus text form, derived from the record.

    Returns:
        a `# TYPE` line and one sample per `(guard, event)`, sorted; just the type line when the
        record holds no event.

    """
    head = f"# TYPE {COUNTER_NAME} counter\n"
    samples = [
        f'{COUNTER_NAME}{{guard="{_label(guard)}",event="{_label(event)}"}} {count}\n'
        for (guard, event), count in sorted(counts(record).items())
    ]
    return head + "".join(samples)


def write_counter(record: Path) -> Path:
    """Write the counter file beside the record, replacing it whole.

    Returns:
        the counter file's path.

    """
    target = counter_path(record)
    scratch = target.with_name(target.name + f".{os.getpid()}.tmp")
    scratch.write_text(counter_text(record), encoding="utf-8")
    scratch.replace(target)
    return target
