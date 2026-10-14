# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Batch lines into the spool and count how many INPUT lines were consumed (W1186).

⚑ A FILE FORM COMMITS ONLY THE CONSUMED PREFIX. Under `on_full = hold` a batch can be only partly
taken, and the spool is then at its ceiling, so every later batch would be refused too. Once a batch
holds anything this stops shipping and counts nothing more: the lines after the held ones stay in
the file with them, so what was consumed is always a prefix and the offset saved after it loses
nothing. Under `drop-oldest` every batch is taken and the count is the number of lines read.

CONSUMED BY: `vlogcli`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import vlogship

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from mikemol.hooks import vlogrecord

BATCH = 200


class Batcher:
    """Collect lines, ship them in batches of `BATCH`, and know how many input lines it consumed."""

    def __init__(
        self,
        streams: Mapping[str, str],
        how: vlogrecord.FieldMap,
        config: vlogship.Config,
        now: Callable[[], str],
    ) -> None:
        """Name where lines go; nothing is shipped until a batch fills or `flush` is called."""
        self.streams = streams
        self.how = how
        self.config = config
        self.now = now
        self.pending: list[str] = []
        self.consumed = 0
        self.blocked = False

    def take(self, line: str) -> None:
        """Add one input line, shipping a batch when it is full."""
        self.pending.append(line)
        if len(self.pending) >= BATCH:
            self.flush()

    def flush(self) -> None:
        """Ship what is pending, unless an earlier batch already held something back."""
        if self.pending and not self.blocked:
            shipped = vlogship.ship(self.pending, self.streams, self.how, self.config, self.now)
            self.consumed += shipped.consumed
            self.blocked = shipped.held > 0
        self.pending.clear()
