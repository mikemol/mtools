# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W810: facts about the HOST the hooks guard: the zram device behind /tmp, and the tick lock.

Hooks that gate a tick (a prompt that cannot run, a turn that ends holding the lock) need two
readings the standing facts do not carry. They are gathered here, in the facts-gatherer's own
convention (standing_facts): a fact that cannot be read is ABSENT (None), never zeros and never
empty. An absent fact lets a rule stay undefined; a zero would assert headroom nobody measured.

⚑ `df` LIES ABOUT /tmp AND /var/tmp. They are ext4 on one zram device shown through project quotas
(128G, 32G, 252G), but the device stops accepting writes at `mem_limit` of COMPRESSED RAM (48 GiB),
so the logical room left is (limit - used) x the live compression ratio, and the ratio is set by the
data (bazel outputs sit near 1.5:1). At the limit ext4 fails on inode creation and the kernel
remounts every mount on the device read-only; every host shell command then dies, because the
shell tool writes its output there (operator, 2026-10-06; a reboot cleared it).

CONSUMED BY: the host's tick hooks, none written yet (mtools:W811 the Stop guard, W812 the
UserPromptSubmit tick gate, W813 the compaction pair, W815 the SessionEnd unlock), and the host
katas (`tick begin` reads the same zram ceiling until W796 moves them into a package).

⚑ THE LOCK IS READ, NEVER WRITTEN. The queue has one writer, mikemol-paths-forward; reading its JSON
directly is what standing_facts already does (held_symbols, embargoes). W819 swaps the read for
`mikemol.pathsforward.lock.current` when hooks gains that dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks.payload import as_record, text_of
from mikemol.hooks.standing_facts import queue_doc

# The device behind /tmp, /var/tmp and luthen's scratch; mm_stat's first four fields are
# orig_data_size, compr_data_size, mem_used_total and mem_limit.
ZRAM_MM_STAT = Path("/sys/block/zram1/mm_stat")

# How many leading mm_stat fields the reading needs.
MM_STAT_FIELDS = 4

# The fraction of the compressed ceiling at which new work is refused (the host's tick gate, and
# the katas' `tick begin` until they call this module): past it a write failure can remount /tmp
# read-only.
REFUSE_FRACTION = 0.85

GIB = 2**30


@dataclass(frozen=True, slots=True)
class Headroom:
    """The zram device's use against its real ceiling, in compressed bytes."""

    used: int
    limit: int
    ratio: float

    def fraction(self) -> float:
        """Return how much of the ceiling is used.

        Returns:
            used over limit; the limit is positive by construction.

        """
        return self.used / self.limit

    def logical_room_gib(self) -> float:
        """Return how many GiB of data like what is stored would still fit.

        Returns:
            the compressed bytes left, times the live ratio, in GiB.

        """
        return (self.limit - self.used) * self.ratio / GIB


@dataclass(frozen=True, slots=True)
class HostLock:
    """The queue's tick lock, or the reading that nobody holds it."""

    holder: str | None
    taken_at: str | None

    def held(self) -> bool:
        """Report whether anyone holds the lock.

        Returns:
            True when the queue names a holder.

        """
        return self.holder is not None


def zram_headroom(stat: Path = ZRAM_MM_STAT) -> Headroom | None:
    """Read the zram device's use and ceiling.

    ⚑ A `mem_limit` of 0 means no limit is set, so there is no headroom to state: that is absent,
    not an infinite fraction.

    Returns:
        the Headroom; None when the file is missing, short, not numbers, or sets no limit.

    """
    try:
        fields = stat.read_text(encoding="utf-8").split()
        orig, compressed, used, limit = (int(value) for value in fields[:MM_STAT_FIELDS])
    except (OSError, ValueError):
        return None
    if limit <= 0:
        return None
    return Headroom(used=used, limit=limit, ratio=orig / compressed if compressed else 0.0)


def host_lock(state: Path) -> HostLock | None:
    """Read the tick lock out of a queue file.

    Returns:
        the lock (holder and taken_at None when the queue records none); None when the queue
        cannot be read, which is not the same fact as "nobody holds it".

    """
    doc = queue_doc(state)
    if doc is None:
        return None
    record = as_record(doc.get("lock"))
    holder = text_of(record.get("holder"))
    if not holder:
        return HostLock(holder=None, taken_at=None)
    return HostLock(holder=holder, taken_at=text_of(record.get("taken_at")) or None)
