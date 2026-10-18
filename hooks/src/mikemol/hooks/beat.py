# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-hook-beat`: every tool call leaves the session heartbeat (W1475, github-8f 2026-10-17).

The idle watchdog (`watchdog.py`) measures how long a session has been quiet, and until now only the
writer, `mikemol-commit` and `mikemol-scratch` beat, so a long Bash build, a read or an edit left no
beat and el-openglo's session was woken twice while it worked. The operator's rule is that USING THE
TOOLING IS THE HEARTBEAT. The harness runs a hook around every tool call, so a PostToolUse hook that
writes the stamp is that rule, literally, for every tool and with no transcript reader.

⚑ A BEAT IS THE SESSION'S OWN ACTION. A hook runs because the session called a tool, so it cannot be
fooled by the background-task notifications and peer messages the harness writes into a transcript
while the session is idle, which is why this is the primary signal and a transcript check only a
second opinion before firing.

⚑ IT NEVER BLOCKS AND NEVER SPEAKS. Exit 0 whatever the payload, the project or the file system is:
a heartbeat that cannot be written is a missed sample (`heartbeat.try_beat`), and a hook that
refused a tool call over it would stop the work it exists to witness.

⚑ THE PROJECT IS THE ONE THE HARNESS NAMES: `CLAUDE_PROJECT_DIR`, then the payload's `cwd`. A
project whose `.git` is not a directory (a worktree) is skipped, as the writer's beat is.

CONSUMED BY: the `PostToolUse` and `PostToolUseFailure` entries of a repo's `.claude/settings.json`.
"""

import json
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import TextIO, cast

from mikemol.hooks import heartbeat, hook_argv

PROG = "mikemol-hook-beat"
PROJECT_ENV = "CLAUDE_PROJECT_DIR"
UNKNOWN_TOOL = "tool"


def _field(raw: object, key: str) -> str | None:
    # A non-empty string field of the payload, or None for anything else.
    if not isinstance(raw, dict):
        return None
    value = cast("dict[str, object]", raw).get(key)
    return value if isinstance(value, str) and value else None


def tool_of(raw: object) -> str:
    """Name the tool a PostToolUse payload reports.

    Returns:
        the payload's `tool_name`, or a generic word when it has none.

    """
    return _field(raw, "tool_name") or UNKNOWN_TOOL


def project_of(raw: object, env: Mapping[str, str]) -> Path | None:
    """Find the project directory the beat belongs to.

    Returns:
        `CLAUDE_PROJECT_DIR` when set, else the payload's `cwd`, else None.

    """
    named = env.get(PROJECT_ENV) or _field(raw, "cwd")
    return Path(named) if named else None


def run(
    stdin: TextIO,
    env: Mapping[str, str],
    now_ns: Callable[[], int] = time.time_ns,
) -> int:
    """Leave one beat for the tool call the payload reports.

    Returns:
        0 always.

    """
    try:
        raw: object = json.load(stdin)
    except ValueError:
        raw = None
    project = project_of(raw, env)
    if project is not None and (project / ".git").is_dir():
        heartbeat.try_beat(project / ".git", f"hook:{tool_of(raw)}", now_ns())
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the hook.

    Returns:
        0 always, or the argv contract's refusal for an argument.

    """
    args = list(sys.argv if argv is None else argv)
    if hook_argv.mode(PROG, args) is not None:
        return hook_argv.EXIT_REFUSED
    return run(sys.stdin, os.environ)


if __name__ == "__main__":
    raise SystemExit(main())
