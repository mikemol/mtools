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


@dataclass(frozen=True)
class Shipped:
    """What `ship` did: records spooled, and lines the ceiling dropped doing it."""

    spooled: int
    dropped: int


@dataclass(frozen=True)
class Drain:
    """What `drain_all` did: lines sent, lines left, and why anything was left."""

    sent: int
    left: int
    reason: str = ""


def spool_name(keys: Sequence[str]) -> str:
    """Name the spool file for a set of stream keys, order-independent.

    Returns:
        for example `vlog-repo%2Ctool.spool`.

    """
    joined = ",".join(sorted(keys)) or NO_STREAMS
    return f"{PREFIX}{urllib.parse.quote(joined, safe='')}{SUFFIX}"


def keys_of(name: str) -> list[str]:
    """Read the stream keys back out of a spool file's name.

    Returns:
        the keys, empty for the no-streams spool.

    """
    body = urllib.parse.unquote(name.removeprefix(PREFIX).removesuffix(SUFFIX))
    return [] if body == NO_STREAMS else body.split(",")


def spool_for(config: Config, keys: Sequence[str]) -> vlogspool.Spool:
    """Open the spool for `keys` under the configured directory.

    Returns:
        the spool, created on first append.

    """
    return vlogspool.Spool(config.spool_dir / spool_name(keys), config.max_lines, config.max_bytes)


def ship(
    lines: Iterable[str],
    streams: Mapping[str, str],
    how: vlogrecord.FieldMap,
    config: Config,
    now: Callable[[], str],
) -> Shipped:
    """Turn lines into records and spool them; blank lines are skipped.

    Returns:
        the number spooled and the number the ceiling dropped (also recorded in the spool).

    """
    records = [
        json.dumps(vlogrecord.record_of(line, streams, now(), how), sort_keys=True)
        for line in lines
        if line.strip()
    ]
    spool = spool_for(config, list(streams))
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
    return Shipped(len(records), dropped)


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
