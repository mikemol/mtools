# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""What plan admission asks of its host: find a tool, run it, run it bounded by CPU (W1845).

luthen's `checks/run_tool.py` is one subprocess seam, and it carries luthen's policy: as root it
resolves tools from the system directories alone (W60, so a shim in a user-writable `.venv/bin`
cannot run as root), otherwise from the repo's `.venv` first. A generic dist must not decide that
for a second repo, and waldo itself spawns nothing (its execution goes through seams the consumer
supplies), so plan admission takes a `Tools` and never imports `subprocess`.

⚑ THE CONSUMER OWNS TOOL RESOLUTION: where a tool comes from is the consumer's security decision,
and the dist runs whatever `find` returns, so a consumer that wants luthen's rules implements `find`
the way luthen does. The dist adds no search path of its own.

⚑ BOUNDED BY CPU TIME, NEVER BY THE CLOCK (operator ruling 2026-09-24): `run_bounded` takes
`cpu_seconds`, and a consumer enforces it with RLIMIT_CPU (luthen uses prlimit and `--cpu`), not
with a timer.
"""

from pathlib import Path
from typing import Protocol


class Completed(Protocol):
    """What plan admission reads of a finished child: its exit code and its output."""

    returncode: int
    stdout: str
    stderr: str


class Tools(Protocol):
    """The three things plan admission does to the host, implemented by the consumer."""

    def find(self, name: str) -> Path | None:
        """Resolve `name` to an executable, or None when the consumer cannot."""
        ...

    def run(
        self, tool: Path, *args: str, cwd: Path | None = None, stdin_text: str | None = None
    ) -> Completed:
        """Run `tool` with `args`, never raising on a non-zero exit."""
        ...

    def run_bounded(
        self, tool: Path, *args: str, cwd: Path | None = None, cpu_seconds: int
    ) -> Completed:
        """Run `tool` like `run`, captured, killed by the kernel after `cpu_seconds` of CPU."""
        ...
