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

import contextlib
import fcntl
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


@contextlib.contextmanager
def try_exclusive(path: Path) -> Iterator[bool]:
    """Try an exclusive kernel flock on `path` without waiting, creating the file if absent.

    ⚑ THE NON-BLOCKING SIBLING OF `exclusive` (mtools:W1264, luthen-observability:W1073): a holder
    elsewhere is an answer, not a wait. It asks the kernel once with `LOCK_NB`, so there is no
    deadline, no sleep and no retry loop in it: a caller that wants to try again does so on an event
    of its own. The lock is released when the body ends if, and only if, this call took it.

    Yields:
        True while the lock is held by this call; False when another holder has it, in which case
        the body runs without the lock and nothing is released.

    """
    with path.open("ab") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
