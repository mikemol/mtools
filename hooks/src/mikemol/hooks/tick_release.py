# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W815: at SessionEnd, release the host tick lock if this session still holds it.

The Stop guard (tick_stop) catches a turn that ends mid-tick. A session that DIES mid-tick (the
terminal closes, the harness is killed, the context is cleared) never reaches another Stop, and its
lock then makes the next tick wait out thirty minutes. SessionEnd is the last place a hook runs.

⚑ THE LOCK IS RELEASED THROUGH THE ONE WRITER, NEVER BY EDITING THE QUEUE. The queue has exactly one
writer, mikemol-paths-forward, and its `--unlock HOLDER` is the operation that means "release". This
module runs that command, passing the holder the queue itself recorded, so the writer's own check
(the holder owns it, or nobody does) still decides. The writer is found in a fixed order: the
PATHS_FORWARD_BIN environment variable, the project's own `.venv/bin`, then PATH. Not finding it is
SAID on stderr and the lock is left held, never worked around.

⚑ ONLY A FRESH LOCK IS RELEASED. A lock older than the stale bound belongs to a holder that already
died, and the next `tick begin` takes it over by design; releasing it here would change nothing the
next tick does not already do, and could release a lock whose holder is merely slow.

⚑ ONE SECOND, NOT MORE. SessionEnd hooks share a 1.5 s budget, so the writer runs under a one-second
timeout; a timeout is a failed release, said on stderr, and the lock is left held.

⚑ NO ARMING VARIABLE: it releases or says nothing, with no advisory mode, and this file must not
spell that variable's name (the wiring arm reads a module that does as one that arms).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks.payload import as_record
from mikemol.hooks.tick_stop import QUEUE, fresh, payload_dir, payload_lock

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TextIO

# The environment variable that names the writer, first in the search order.
WRITER_ENV = "PATHS_FORWARD_BIN"

# The writer's command name, looked up under the project's venv and on PATH.
WRITER_NAME = "mikemol-paths-forward"

# Inside SessionEnd's shared 1.5 s budget.
RELEASE_TIMEOUT_S = 1.0


def find_writer(directory: Path) -> Path | None:
    """Find the queue's one writer, in the fixed order.

    Returns:
        the first executable file among $PATHS_FORWARD_BIN, `<directory>/.venv/bin/<name>` and
        PATH; None when there is none.

    """
    candidates = [
        os.environ.get(WRITER_ENV, ""),
        str(directory / ".venv" / "bin" / WRITER_NAME),
        shutil.which(WRITER_NAME) or "",
    ]
    for name in candidates:
        if name and Path(name).is_file() and os.access(name, os.X_OK):
            return Path(name)
    return None


def release_with_writer(
    writer: Path, queue: Path, holder: str, timeout_s: float = RELEASE_TIMEOUT_S
) -> bool:
    """Run the writer's `--unlock` for `holder` on `queue`, bounded by `timeout_s`.

    Returns:
        True when the writer exited 0; False when it failed, could not start, or timed out.

    """
    try:
        done = subprocess.run(
            [str(writer), "--state", str(queue), "--unlock", holder],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


def run(
    payload: dict[str, object],
    now: datetime,
    release: Callable[[Path, Path, str], bool],
    err: TextIO,
) -> int:
    """Release the host tick lock named by one SessionEnd payload, if it is held and fresh.

    Returns:
        0 always: a session end is never blocked, and every outcome is a line on `err`.

    """
    lock = payload_lock(payload)
    if lock is None or lock.holder is None or not fresh(lock, now):
        return 0
    directory = payload_dir(payload)
    writer = find_writer(directory)
    if writer is None:
        err.write(
            f"tick-release: the host tick lock is held by {lock.holder} but no {WRITER_NAME} was "
            f"found (set {WRITER_ENV}); left held\n"
        )
        return 0
    if release(writer, directory / QUEUE, lock.holder):
        err.write(f"tick-release: released the host tick lock held by {lock.holder}\n")
    else:
        err.write(f"tick-release: releasing the lock held by {lock.holder} failed; left held\n")
    return 0


def main() -> int:
    """Read the SessionEnd payload on stdin and release the lock if it is ours to release.

    Returns:
        the exit code from `run`, or 0 for a payload that is not JSON.

    """
    try:
        raw: object = json.load(sys.stdin)
    except ValueError:
        sys.stderr.write("tick-release: the payload was not JSON; nothing released\n")
        return 0
    return run(as_record(raw), datetime.now(UTC), release_with_writer, sys.stderr)
