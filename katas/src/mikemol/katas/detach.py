# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Start a command detached from the caller, leaving its log for `commits.commit_state` to read.

Ported from the host katas.py `start_commit` (mtools:W796, W874). The commit takes minutes to hours
behind a gate, so the kata starts it and returns; the child outlives the caller in its own session,
with no stdio, and writes `LOG` through `waiter` (output, then `rc=N` when it ends).

⚑ THE CHILD GETS THE CALLER'S WHOLE `sys.path` AS `PYTHONPATH`. It runs `python -m
mikemol.katas.waiter`, which must import this distribution and `mikemol.procrun`; in a Bazel
runfiles tree or a venv the caller found them through paths its own interpreter built, which a
bare child would not inherit.

⚑ A DETACHED START IS NOT `procrun.capture`, which waits: that is why this is its own module, with
its own per-file exemption scoped to the one `Popen`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def waiter_argv(log: Path, argv: Sequence[str], removals: Sequence[Path] = ()) -> list[str]:
    """Build the argv that runs `argv` under the waiter, writing `log`.

    Returns:
        this interpreter running `mikemol.katas.waiter`, the log, a `--rm` pair per path to remove,
        then the command.

    """
    command = [sys.executable, "-m", "mikemol.katas.waiter", str(log)]
    for path in removals:
        command += ["--rm", str(path)]
    return [*command, *argv]


def start(log: Path, argv: Sequence[str], removals: Sequence[Path] = ()) -> None:
    """Start `argv` detached, with `log` emptied first so a stale `rc=` cannot read as this run's.

    The caller returns at once; poll `commits.commit_state(log)` for the outcome.
    """
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("", encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(entry for entry in sys.path if entry)}
    subprocess.Popen(
        waiter_argv(log, argv, removals),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )
