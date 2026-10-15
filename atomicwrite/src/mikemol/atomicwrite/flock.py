# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The EXCLUSIVE-LOCK primitive: one blocking kernel flock on a path, released on exit (W1286).

⚑ ONE HELPER FOR THE RAW `fcntl.flock` PAIRS (github-8f's convergent-patterns audit, 2026-10-15):
pathsforward's store and fence's ledger each wrote their own lock/unlock around a `yield`. This is
the blocking half. It waits on the kernel and never on a clock, so no timeout lives here; a caller
that must give up does so with a witness of its own (the avoid-wall-clock-timeouts ruling), not a
deadline in the lock.

⚑ A KERNEL FLOCK IS NOT A RECORD LOCK: the kernel drops it when the holder's descriptor closes or
the process dies, so a crashed holder leaves nothing to reap. A lock that is a JSON record of who
holds it (pathsforward's tick lock) is a different thing and keeps its own staleness story.

Depends on nothing but the standard library, as `durable` does.
"""

from __future__ import annotations

import contextlib
import fcntl
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@contextlib.contextmanager
def exclusive(path: Path) -> Iterator[None]:
    """Hold an exclusive kernel flock on `path` for the body, creating the file if absent.

    The lock is taken blocking and released when the body ends, whether it returns or raises.

    Yields:
        nothing; the lock is held until the body ends.

    """
    with path.open("ab") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
