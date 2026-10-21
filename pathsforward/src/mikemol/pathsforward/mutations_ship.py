# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Ship the events of one saved mutation from the writer's single save point (W1742).

⚑ THE CONTEXT IS THE WRITER'S, NOT THE CALLER'S, so no mutation can skip it and no flag has to be
remembered. `via` is the mode the command ran (`--update`, `--add`, `--tick-close`), `actor` is
what the writer can honestly know, and the mutation id is the command's start time and pid, shared
by every field event of one command, so one `--update` of three fields is one change.

⚑ ACTOR IS THREE VALUES AND NO MORE (nemik-84, 2026-10-19): `automation` for the modes that run
unattended (a prune, a bump, a reconcile), `agent` when a tick lock is held, `unattributed` when
neither is so. The writer cannot tell the operator from an agent, and does not claim to.

⚑ THE VERSION STANDS FOR THE WRITER'S SHA: a vendored wheel's local version is `0.1.0+g<sha>`, so
the field says which writer made the change; a checkout reads as the bare version.

CONSUMED BY: `cli._mutate` (W1742).
"""

import os
from collections.abc import Mapping
from datetime import datetime
from importlib import metadata
from pathlib import Path

from mikemol.pathsforward import lock, mutations, mutations_emit
from mikemol.pathsforward.ledger import session_id
from mikemol.pathsforward.model import State

AUTOMATIC = frozenset(
    {
        "bump_blocked",
        "prune_landed",
        "block_behind_open",
        "block_matching",
        "close_umbrellas",
        "reconcile",
        "triage",
        "gate_red",
        "gate_green",
        "gate_note",
        "close_gate",
    }
)
DIST = "mikemol-pathsforward"
_MS = 1000


def actor_of(mode: str, *, held: bool) -> str:
    """Say who made the change, as far as the writer can know.

    Returns:
        `automation` for an unattended mode, else `agent` when a tick lock is held, else
        `unattributed`.

    """
    if mode in AUTOMATIC:
        return "automation"
    return "agent" if held else "unattributed"


def writer_version() -> str:
    """Read the installed writer's version, whose local part is the commit of a vendored wheel.

    Returns:
        the version, or the empty string when the distribution is not installed.

    """
    try:
        return metadata.version(DIST)
    except metadata.PackageNotFoundError:
        return ""


def meta_of(
    mode: str, now: datetime, environ: Mapping[str, str], *, held: bool
) -> mutations_emit.Meta:
    """Build the context one command's events share.

    Returns:
        the Meta: via from the mode, the actor, a mutation id of start time and pid, the clock in
        UTC milliseconds, the session's transcript id and the writer's version.

    """
    at_ms = int(now.timestamp() * _MS)
    return mutations_emit.Meta(
        via=f"--{mode.replace('_', '-')}",
        actor=actor_of(mode, held=held),
        mutation=f"{at_ms}-{os.getpid()}",
        at_ms=at_ms,
        session=session_id(environ),
        sha=writer_version(),
    )


STATION = "fleet:intervention"
KINDS = ("atomize", "stack", "shard", "repin", "other")


def ship_intervention(
    path: Path, said: tuple[str, str], state: State, run: tuple[str, datetime]
) -> bool:
    """Send a card-less intervention event: something done to the queue that is no card's field.

    ⚑ THE KIND IS ONE OF A FIXED SET (`KINDS`), because it becomes the `field` label of the metric
    and a free-text label would grow without bound; the note is free text and rides the log record
    only. The station is `fleet:intervention`, qualified by the repo as every station is (W1739,
    asked by nemik-84 for nemik:W743), and the event carries the same context as any mutation's.

    Returns:
        whether the event was sent; False with no binary or store, or a child that did not start.

    """
    kind, note = said
    mode, now = run
    meta = meta_of(mode, now, os.environ, held=lock.current(state) is not None)
    return mutations_emit.emit(path, [mutations.Event(STATION, kind, "", note)], meta)


def ship(path: Path, before: mutations.Snapshot, state: State, run: tuple[str, datetime]) -> bool:
    """Diff the saved state against the snapshot taken before the edit and send the events.

    `run` is the mode the command ran and the clock it read once.

    Returns:
        whether events were sent; False when nothing changed or nothing could be started.

    """
    events = mutations.events(before, state)
    if not events:
        return False
    mode, now = run
    meta = meta_of(mode, now, os.environ, held=lock.current(state) is not None)
    return mutations_emit.emit(path, events, meta)
