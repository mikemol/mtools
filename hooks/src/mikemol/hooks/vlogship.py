# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The shipper core of `mikemol-vlog`: spool every record first, then drain to the endpoint (W1177).

⚑ SPOOL FIRST, ALWAYS. `ship` turns lines into records (`vlogrecord`) and appends them to a spool
before anything touches the network, so the caller's work is a local file append and a stalled or
refusing endpoint can only grow the spool, never the caller's wait. `drain_all` is the other half,
run by a detached drainer (W1179): it asks the host's resolver for the endpoint by NAME, and posts
each spool with its own stream fields.

⚑ ONE SPOOL PER STREAM-FIELD SET. VictoriaLogs is told the stream fields in the ingest query, so a
batch must share them. The spool is named for the SORTED KEYS of the caller's `--stream K=V`
pairs, and the drainer reads the keys back from the file name, so two producers with different
stream keys never share a batch and nothing is guessed at drain time.

⚑ A LOSS IS A RECORD. When the spool's ceiling dropped lines, `ship` appends one record saying how
many, with the same stream fields, so the reader of the log sees the gap instead of a silence.

⚑ A REFUSED OR UNRESOLVED DRAIN LEAVES THE SPOOL INTACT and says why (`Drain.reason`), so the next
run, after a restart or an endpoint coming back, replays it in order.

CONSUMED BY: the `mikemol-vlog` command (W1179).
"""

from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import vlogrecord, vlogsink, vlogspool, vlogwatch

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence

NO_STREAMS = "_none"
PREFIX = "vlog-"
SUFFIX = ".spool"
HOLD = "hold"
PROGRESS = ".vlog.progress"
WATCH = ".vlog.watch"
note_progress = vlogwatch.record_progress_here
watch_holder = vlogwatch.observe


@dataclass(frozen=True)
class Config:
    """Where the spools live, which service to ship to, how to resolve it, and the bounds."""

    spool_dir: Path
    service: str | None
    resolver: tuple[str, ...]
    max_lines: int
    max_bytes: int
    on_full: str = "drop-oldest"
    source: str | None = None


@dataclass(frozen=True)
class Shipped:
    """What `ship` did: records spooled, lines the ceiling dropped, and under `hold` the rest.

    `consumed` counts INPUT lines taken (blank ones included, up to the last record spooled), so a
    file form can commit exactly that prefix and leave the held tail in the file.
    """

    spooled: int
    dropped: int
    held: int = 0
    consumed: int = 0


@dataclass(frozen=True)
class Drain:
    """What `drain_all` did: lines sent, lines left, and why anything was left."""

    sent: int
    left: int
    reason: str = ""


def spool_name(keys: Sequence[str], source: str | None = None) -> str:
    """Name the spool file for a set of stream keys and, optionally, a source, order-independent.

    ⚑ A SOURCE HAS ITS OWN SPOOL (W1213): the file name is the sorted KEYS, so every source that
    streams the same keys (a `stream` and a `file` field, say) shared one file and one ceiling, and
    a volume source filled it and starved the rest. A source adds `@NAME` after the keys; the `@`
    is percent-encoded inside both parts, so it can only be the separator. The ceiling that
    `[source.NAME]` declares is then that file's.

    Returns:
        for example `vlog-repo%2Ctool.spool`, or the same keys with the source's name after an
        `@` just before the `.spool` (source `containerd`).

    """
    joined = ",".join(sorted(keys)) or NO_STREAMS
    tail = f"@{urllib.parse.quote(source, safe='')}" if source else ""
    return f"{PREFIX}{urllib.parse.quote(joined, safe='')}{tail}{SUFFIX}"


def keys_of(name: str) -> list[str]:
    """Read the stream keys back out of a spool file's name, ignoring the source.

    Returns:
        the keys, empty for the no-streams spool.

    """
    keyed = name.removeprefix(PREFIX).removesuffix(SUFFIX).partition("@")[0]
    body = urllib.parse.unquote(keyed)
    return [] if body == NO_STREAMS else body.split(",")


def spool_for(config: Config, keys: Sequence[str]) -> vlogspool.Spool:
    """Open the spool for `keys` (and the config's source) under the configured directory.

    Returns:
        the spool, created on first append.

    """
    path = config.spool_dir / spool_name(keys, config.source)
    return vlogspool.Spool(path, config.max_lines, config.max_bytes)


def ship(
    lines: Iterable[str],
    streams: Mapping[str, str],
    how: vlogrecord.FieldMap,
    config: Config,
    now: Callable[[], str],
) -> Shipped:
    """Turn lines into records and spool them; blank lines are skipped.

    ⚑ THE CEILING POLICY IS THE CONFIG'S (W1184): `drop-oldest` (the default) makes room by
    dropping the oldest and recording how many; `hold` appends only what fits and reports the rest
    as `held` with `consumed` input lines, so a file form can leave the tail in the file.

    Returns:
        the number spooled, dropped (also recorded in the spool), held and consumed.

    """
    every = list(lines)
    kept = [(place, line) for place, line in enumerate(every) if line.strip()]
    records = [
        json.dumps(vlogrecord.record_of(line, streams, now(), how), sort_keys=True)
        for _, line in kept
    ]
    spool = spool_for(config, list(streams))
    if config.on_full == HOLD:
        return _hold(spool, records, [place for place, _ in kept], len(every))
    spool.append(records)
    dropped = spool.take_dropped()
    if dropped:
        gap = {
            "_msg": f"mikemol-vlog dropped {dropped} spooled lines at the ceiling",
            "_time": now(),
            "dropped": dropped,
            **streams,
        }
        spool.append([json.dumps(gap, sort_keys=True)])
    return Shipped(len(records), dropped, 0, len(every))


def _hold(spool: vlogspool.Spool, records: list[str], places: list[int], total: int) -> Shipped:
    """Append what fits and say how many input lines that consumed.

    Returns:
        the shipped count: spooled, no drops, the held records, and the input lines consumed
        (all of them when everything fit, else up to the last record that did).

    """
    taken = spool.append_up_to(records)
    if taken == len(records):
        return Shipped(taken, 0, 0, total)
    consumed = places[taken - 1] + 1 if taken else 0
    return Shipped(taken, 0, len(records) - taken, consumed)


def spools_in(config: Config) -> list[vlogspool.Spool]:
    """Find every spool under the configured directory.

    Returns:
        the spools, in name order.

    """
    found = sorted(Path(config.spool_dir).glob(f"{PREFIX}*{SUFFIX}"))
    return [vlogspool.Spool(p, config.max_lines, config.max_bytes) for p in found]


def drain_all(
    config: Config,
    opener: vlogsink.Opener = vlogsink.http_opener,
    resolver: vlogsink.Resolver = vlogsink.run_resolver,
    kill: Callable[[int], None] = vlogwatch.kill_group,
    alive: Callable[[int], bool] = vlogwatch.pid_alive,
) -> Drain:
    """Resolve the endpoint by name and post every spool, leaving what is refused.

    ⚑ A BUSY SPOOL IS AN OBSERVATION (W1180): another drainer holds it, and `vlogwatch.observe`
    compares that drainer's progress file with what the previous run saw; one that has not moved
    for several runs in a row is ended. Every batch taken updates the progress file.

    Returns:
        lines sent, lines left, and the first reason anything was left.

    """
    spools = spools_in(config)
    base = vlogsink.resolve(config.service, config.resolver, resolver) if config.service else None
    if base is None:
        left = sum(s.count() for s in spools)
        return Drain(0, left, "no destination: no service named, or the resolver gave no endpoint")
    progress, watch = Path(config.spool_dir) / PROGRESS, Path(config.spool_dir) / WATCH
    reason = ""
    totals = [0, 0]
    for spool in spools:
        url = vlogsink.ingest_url(base, keys_of(spool.path.name))
        refusal: list[str] = []

        def take(lines: list[str], url: str = url, refusal: list[str] = refusal) -> bool:
            posted = vlogsink.post(url, lines, opener)
            if posted.ok:
                totals[0] += len(lines)
                totals[1] += 1
                note_progress(progress, totals[0], totals[1])
            else:
                refusal.append(f"{posted.status} {posted.reason}".strip())
            return posted.ok

        result = spool.drain(take)
        if result.busy:
            seen = watch_holder(progress, watch, kill=kill, alive=alive)
            reason = reason or f"busy: another drainer holds it ({seen.state})"
        reason = reason or (refusal[0] if refusal else "")
    return Drain(totals[0], sum(s.count() for s in spools), reason)
