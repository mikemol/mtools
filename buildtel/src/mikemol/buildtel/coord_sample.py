# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Sample the COORDINATOR's memory to a durable file, live.

Ported from paperkit's `tools/coord_sample.py` (paperkit:W142). Behaviour unchanged; the `/proc`
and cgroup roots, the liveness probe and the sleep are parameters so a test drives them with a
planted tree and a counted clock, and the SIGINT exit moved from the `__main__` guard into `main`
so the console script has it too.

WHY THIS EXISTS, and it is a correction to the end-of-run pushers.  `logs_push` (and the retired
`otlp_push`, W44) POST at the END of a run, which by construction cannot report a crash that
kills the run: they buffer, and they die with the thing they are recording.  Measured cost -
the bazel server died twice with `Build completed successfully, 32325 total actions` directly
above `java.lang.OutOfMemoryError`, and BOTH runs pushed nothing.  The runs worth keeping are
exactly the ones that never report.

SCOPED TO THE COORDINATOR, NOT THE BOX.  A peer's host collectors already sample host memory
and PSI continuously - queried across that crash window, memory PSI peaked near 4%, so the box
was never stressed and its series were never missing.  What NOTHING sampled was the bazel server
itself: every sweep cell runs under a per-action cgroup lease, and the process holding them all
runs unbudgeted and unobserved.  That is the curve that would have shown a ceiling being
approached, and it is the only one this adds.

APPEND, NEVER BUFFER.  One flush per sample, so a SIGKILL loses at most the current line.  A
replayed timeline is a fabrication rather than a recovery.

    mikemol-coord-sample <pid> <out.jsonl> [--interval=SECONDS]

Exits when the pid does.  Best-effort in every arm: a sampler that can fail a build is a
liability, not an instrument - the same rule the pushers follow.  An unrecognised argument is
REFUSED (exit 2) rather than read as a path to append to.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

USAGE = "mikemol-coord-sample <pid> <out.jsonl> [--interval=SECONDS]"
EXIT_USAGE = 2
POSITIONALS = 2
INTERVAL_FLAG = "--interval="
STATM_RSS_FIELD = 1
PROC_ROOT = Path("/proc")
CGROUP_ROOT = Path("/sys/fs/cgroup")
DEFAULT_INTERVAL_S = 1.0
CLOCK_DIGITS = 3


def rss_bytes(pid: int, proc_root: Path = PROC_ROOT) -> int | None:
    """Read the resident set from statm (pages) - cheap, and present on every Linux.

    Returns:
        the resident set in bytes, or None when the pid's statm is unreadable.

    """
    try:
        fields = (proc_root / str(pid) / "statm").read_text(encoding="ascii").split()
        return int(fields[STATM_RSS_FIELD]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError):
        return None


def cgroup_current(
    pid: int, proc_root: Path = PROC_ROOT, cgroup_root: Path = CGROUP_ROOT
) -> int | None:
    """Read memory.current for the pid's OWN cgroup, or None where v2 is not reachable.

    Read via /proc/<pid>/cgroup rather than a computed path: the depth differs by QoS class
    under a kubelet, and a hardcoded relative path is right for some and wrong for others.

    Returns:
        the cgroup's current memory in bytes, or None.

    """
    try:
        line = (proc_root / str(pid) / "cgroup").read_text(encoding="ascii").strip()
        rel = line.rsplit(":", 1)[-1].lstrip("/")
        return int((cgroup_root / rel / "memory.current").read_text(encoding="ascii").strip())
    except (OSError, ValueError, IndexError):
        return None


def alive(pid: int) -> bool:
    """Say whether the pid is alive, by signal 0: nothing is delivered.

    Returns:
        True when the signal could be sent.

    """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def parse(argv: Sequence[str]) -> tuple[int, Path, float] | None:
    """Read `(pid, out, interval)` from argv, or None when it is not the documented shape.

    Returns:
        the triple, or None.

    """
    positional: list[str] = []
    every = DEFAULT_INTERVAL_S
    for arg in argv:
        if arg.startswith(INTERVAL_FLAG):
            try:
                every = float(arg.removeprefix(INTERVAL_FLAG))
            except ValueError:
                return None
        elif arg.startswith("-"):
            return None
        else:
            positional.append(arg)
    if len(positional) != POSITIONALS or not positional[0].isdigit():
        return None
    return int(positional[0]), Path(positional[1]), every


def sample(
    pid: int,
    out: Path,
    every: float,
    is_alive: Callable[[int], bool],
    sleep: Callable[[float], None],
) -> None:
    """Append one record per interval until the pid is gone or its memory is unreadable."""
    with out.open("a", buffering=1, encoding="utf-8") as sink:  # line-buffered: one flush each
        while is_alive(pid):
            rss = rss_bytes(pid)
            current = cgroup_current(pid)
            if rss is None and current is None:
                return  # unreadable: gone, or not ours
            rec: dict[str, object] = {
                "t": round(time.time(), CLOCK_DIGITS),
                "pid": pid,
                "rss": rss,
                "cgroup_current": current,
            }
            sink.write(json.dumps(rec) + "\n")
            sleep(every)


def main(
    argv: Sequence[str] | None = None,
    *,
    is_alive: Callable[[int], bool] = alive,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Append one sample per interval until the coordinator is gone.

    Returns:
        0 when the pid is gone, unreadable, or the sampler is interrupted; 2 for bad arguments.

    """
    parsed = parse(sys.argv[1:] if argv is None else argv)
    if parsed is None:
        sys.stderr.write(USAGE + "\n")
        return EXIT_USAGE
    pid, out, every = parsed
    try:
        sample(pid, out, every, is_alive, sleep)
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
