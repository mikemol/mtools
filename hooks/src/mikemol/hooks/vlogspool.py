# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A bounded on-disk spool for lines an endpoint refused, replayed first next time (mtools:W1166).

`mikemol-vlog` must never make its caller wait for VictoriaLogs. A line the endpoint did not take
goes here, one JSON line per line of a file, and the next run sends the spool before anything new.

⚑ NO WALL-CLOCK TIMEOUT ANYWHERE (operator, standing): a stalled endpoint backs up into this file,
never into the caller. Nothing here sleeps, polls or counts seconds; the bounds are in LINES and
BYTES, and they are measured, not assumed.

⚑ THE CEILING DROPS THE OLDEST AND COUNTS WHAT IT DROPPED. Over `max_lines` or `max_bytes` the
oldest lines go until the spool fits, and the number dropped is kept beside it (`<spool>.dropped`)
for `take_dropped` to hand back, so the loss is itself a record the caller can ship, not a silence.

⚑ A SEND NEVER HOLDS THE LOCK. `append` takes a short `flock`; `drain` reads a batch under it,
releases it, sends, and re-takes it only to remove exactly the lines that were sent from the FRONT.
A producer appending while a send is stalled is never blocked, and appends at the end cannot be
confused with the sent front. Only one drain runs at a time (a second reports `busy` and leaves
the spool alone), so a batch is never removed twice.

CONSUMED BY: the `mikemol-vlog` command (W1169).
"""

from __future__ import annotations

import fcntl
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence
    from pathlib import Path

DEFAULT_BATCH = 500


@dataclass(frozen=True)
class Drained:
    """What a drain did: lines sent, lines still spooled, and whether another drain held it."""

    sent: int
    left: int
    busy: bool = False


@contextmanager
def _held(lock: Path, *, wait: bool = True) -> Iterator[bool]:
    """Hold an flock on `lock`.

    Yields:
        True once the lock is held; False when `wait` is off and another holder has it.

    """
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a", encoding="utf-8") as handle:
        flags = fcntl.LOCK_EX if wait else fcntl.LOCK_EX | fcntl.LOCK_NB
        try:
            fcntl.flock(handle, flags)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


class Spool:
    """The spool at `path`, bounded by `max_lines` and `max_bytes`."""

    def __init__(self, path: Path, max_lines: int, max_bytes: int) -> None:
        """Name the spool; nothing is created until a line is appended."""
        self.path = path
        self.max_lines = max_lines
        self.max_bytes = max_bytes
        self._lock = path.with_name(path.name + ".lock")
        self._drain_lock = path.with_name(path.name + ".drain")
        self._dropped = path.with_name(path.name + ".dropped")

    def _read(self) -> list[str]:
        return self.path.read_text(encoding="utf-8").splitlines() if self.path.is_file() else []

    def _write(self, lines: Sequence[str]) -> None:
        """Replace the spool with `lines`, whole or not at all."""
        scratch = self.path.with_name(self.path.name + ".new")
        scratch.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
        scratch.replace(self.path)

    def _fit(self, lines: list[str]) -> tuple[list[str], int]:
        """Cut the oldest lines until the spool is within both ceilings.

        Returns:
            the lines kept and how many were dropped.

        """
        drop = max(0, len(lines) - self.max_lines)
        kept = lines[drop:]
        size = sum(len(line.encode("utf-8")) + 1 for line in kept)
        while kept and size > self.max_bytes:
            size -= len(kept[0].encode("utf-8")) + 1
            kept = kept[1:]
            drop += 1
        return kept, drop

    def _dropped_so_far(self) -> int:
        if not self._dropped.is_file():
            return 0
        text = self._dropped.read_text(encoding="utf-8").strip()
        return int(text) if text.isdecimal() else 0

    def count(self) -> int:
        """Count the spooled lines.

        Returns:
            how many lines wait.

        """
        with _held(self._lock):
            return len(self._read())

    def append(self, new: Sequence[str]) -> int:
        """Add lines at the end, then enforce the ceilings.

        Returns:
            how many lines the ceiling dropped (oldest first) to make room.

        Raises:
            ValueError: when a line holds a newline, which would split it in two.

        """
        if any("\n" in line for line in new):
            msg = "a spooled line is one line; it holds a newline"
            raise ValueError(msg)
        with _held(self._lock):
            kept, dropped = self._fit([*self._read(), *new])
            self._write(kept)
            if dropped:
                total = self._dropped_so_far() + dropped
                self._dropped.write_text(f"{total}\n", encoding="utf-8")
            return dropped

    def append_up_to(self, new: Sequence[str]) -> int:
        """Add lines at the end only while they FIT, in order, and drop nothing (W1184).

        ⚑ THE `hold` POLICY: when the spool is at its ceiling the rest is not accepted, and the
        caller keeps it (a file form leaves it in the file for the next run). The first line that
        does not fit ends the batch, so what is held is always a suffix and order is kept.

        Returns:
            how many of `new`, from the front, were appended.

        Raises:
            ValueError: when a line holds a newline, which would split it in two.

        """
        if any("\n" in line for line in new):
            msg = "a spooled line is one line; it holds a newline"
            raise ValueError(msg)
        with _held(self._lock):
            kept = self._read()
            size = sum(len(line.encode("utf-8")) + 1 for line in kept)
            taken = 0
            for line in new:
                cost = len(line.encode("utf-8")) + 1
                if len(kept) + taken >= self.max_lines or size + cost > self.max_bytes:
                    break
                size += cost
                taken += 1
            self._write([*kept, *new[:taken]])
            return taken

    def take_dropped(self) -> int:
        """Hand back how many lines the ceiling has dropped since the last call, and reset it.

        Returns:
            the count, 0 when nothing was dropped.

        """
        with _held(self._lock):
            count = self._dropped_so_far()
            self._dropped.unlink(missing_ok=True)
            return count

    def drain(self, send: Callable[[list[str]], bool], batch: int = DEFAULT_BATCH) -> Drained:
        """Send the spool from the front in batches until it is empty or a send is refused.

        Returns:
            the lines sent, the lines left, and `busy` when another drain held the spool.

        """
        sent = 0
        with _held(self._drain_lock, wait=False) as taken:
            if not taken:
                return Drained(0, self.count(), busy=True)
            while True:
                with _held(self._lock):
                    front = self._read()[:batch]
                if not front or not send(front):
                    break
                with _held(self._lock):
                    self._write(self._read()[len(front) :])
                sent += len(front)
        return Drained(sent, self.count())
