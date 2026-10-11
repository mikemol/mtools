# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Wait for the host's load to fall before a gate starts (mtools:W982).

⚑ A GATE ON A SATURATED HOST TIMES OUT ITS OWN HEALTHY TARGETS. On 2026-10-11 the load average was
122 to 141 on 24 CPUs, from eight sessions' gates at once; a commit that changed nothing near them
was refused for gatecheck, hooks, fence, mdstruct, importdag and ledger mutants timing out. The
refusal named no defect, and a retry into the same load fails the same way.

⚑ OPT-IN, BOUNDED, AND SAID ALOUD. `MIKEMOL_COMMIT_MAXLOAD=N` makes `mikemol-commit` poll the
one-minute load average until it is under N; unset or zero does nothing, so a host and a test suite
that never asked for it never wait. The wait is bounded by `MIKEMOL_COMMIT_LOAD_WAIT_S` (default
half an hour), after which the commit goes ahead anyway and says so: a wait that can wedge a commit
forever is a worse failure than the one it prevents.

The reader and the sleeper are parameters, so the tests run no clock.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

LOAD_ENV = "MIKEMOL_COMMIT_MAXLOAD"
WAIT_ENV = "MIKEMOL_COMMIT_LOAD_WAIT_S"
DEFAULT_WAIT_S = 1800
POLL_S = 20
_LOADAVG = Path("/proc/loadavg")


def read_load() -> float:
    """Read the one-minute load average.

    Returns:
        the load, or 0.0 when the host does not say (so nothing waits on an unreadable source).

    """
    try:
        return float(_LOADAVG.read_text(encoding="utf-8").split()[0])
    except (OSError, ValueError, IndexError):
        return 0.0


def _number(raw: str, default: int) -> int:
    return int(raw) if raw.isdecimal() else default


def wait_for_load(
    env: Mapping[str, str],
    read: Callable[[], float] = read_load,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    """Wait until the load is under the asked limit, or the bound passes.

    Returns:
        a line saying how long it waited and how it ended, or None when it did not wait (not
        asked for, or the load was already low).

    """
    limit = _number(env.get(LOAD_ENV, ""), 0)
    if limit <= 0:
        return None
    bound = _number(env.get(WAIT_ENV, ""), DEFAULT_WAIT_S)
    waited = 0
    load = read()
    while load >= limit and waited < bound:
        sleep(POLL_S)
        waited += POLL_S
        load = read()
    if waited == 0:
        return None
    ending = "going ahead anyway" if load >= limit else "load fell"
    return f"mikemol-commit: waited {waited}s for load {load:.0f} under {limit}; {ending}"
