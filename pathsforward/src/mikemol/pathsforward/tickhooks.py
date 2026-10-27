# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A repo's own commands for `--tick-open` to run, stored in its queue (W1348, nemik:W450).

⚑⚑ THE LIST LIVES IN THE QUEUE STATE, SET BY A WRITER MODE, NOT IN A LOOSE FILE. `--tick-hooks-set
FILE` stores the file's commands as `tick_hooks` (one per non-blank, non-`#` line), SET whole like
`standing`: a command left out of the file is a command retired, a visible edit. An unbalanced
quote is refused when it is stored, so a bad line cannot surface mid-tick; an empty file clears the
list, which is a decision a repo may make.

⚑ A HOOK NEVER BREAKS THE TICK. `--tick-open` runs the commands in order, in the project root,
after its own steps, and prints `HOOK <line> exit N` with the command's output indented beneath
(capped). A command that fails or is not found is REPORTED and the next one still runs; the lock and
the exit status `--tick-open` returns are not touched by any hook. Nothing here is bounded by a
timer: the hooks are the repo's own and run to completion, one after another.

⚑ WHOEVER CAN WRITE THE QUEUE CAN MAKE `--tick-open` RUN A COMMAND. That is the same trust the
state file already carries (it is the repo's own, tracked, and written only through this tool).

The process is a seam (`Runner`), so the tests run no command except where they say so.
"""

import shlex
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from mikemol.pathsforward.model import RefusedError

KEY = "tick_hooks"
NOT_FOUND = 127
SHOWN = 20
Runner = Callable[[Sequence[str], Path], tuple[int, str]]


def lines_of(text: str) -> list[str]:
    """Pick the commands out of a file's text.

    Returns:
        each non-blank line that does not start with `#`, stripped, in order.

    Raises:
        RefusedError: naming the first line `shlex` cannot split (an unbalanced quote).

    """
    found: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            shlex.split(line)
        except ValueError as bad:
            msg = f"tick hook {line!r}: {bad}"
            raise RefusedError(msg) from None
        found.append(line)
    return found


DECLARES = ("# replaces:", "# retires:")


def declared_gone(text: str) -> set[str]:
    """Pick the hook lines a file says it replaces or retires, by comment.

    Returns:
        the lines named after `# replaces:` or `# retires:`, stripped.

    """
    gone: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        for mark in DECLARES:
            if line.startswith(mark):
                gone.add(line[len(mark) :].strip())
    return gone


def dropped(prior: Sequence[str], text: str) -> list[str]:
    """Name the stored hook lines a new file loses without saying so (W1930).

    ⚑ A HOOK LEFT OUT IS A SENSOR DROPPED, AND SETTING THE LIST WHOLE MADE THAT SILENT (github-8f,
    2026-10-27: a measured per-repo landings hook went while another was widened, and a retro's
    witness went false with no refusal). A prior line missing from the new file is refused unless
    the file declares it with `# replaces: <line>` or `# retires: <line>`. The prior list is the
    writer's own stored one, because the host's queue is not under git.

    Returns:
        the prior lines absent from the file's commands and not declared gone, in stored order.

    """
    kept = set(lines_of(text))
    gone = declared_gone(text)
    return [line for line in prior if line not in kept and line not in gone]


def stored(doc: dict[str, object]) -> list[str]:
    """Read the stored commands out of a state document.

    Returns:
        the lines, or none when the key is absent or not a list of strings.

    """
    value = doc.get(KEY)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def run_process(argv: Sequence[str], cwd: Path) -> tuple[int, str]:
    """Run one command to completion in `cwd` and capture its status and combined output.

    Returns:
        (exit status, stdout then stderr); 127 with the reason when the command is not found.

    """
    try:
        done = subprocess.run(
            list(argv),
            cwd=cwd,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except OSError as missing:
        return NOT_FOUND, f"{missing}\n"
    return done.returncode, done.stdout + done.stderr


def run_all(lines: Sequence[str], cwd: Path, runner: Runner = run_process) -> list[str]:
    """Run every command in order and describe each result.

    Returns:
        one `HOOK <line> exit N` line per command, each followed by up to `SHOWN` output lines
        indented two spaces (with a count of the rest).

    """
    said: list[str] = []
    for line in lines:
        code, output = runner(shlex.split(line), cwd)
        said.append(f"HOOK {line} exit {code}")
        body = output.splitlines()
        said.extend(f"  {row}" for row in body[:SHOWN])
        if len(body) > SHOWN:
            said.append(f"  ... {len(body) - SHOWN} more line(s)")
    return said
