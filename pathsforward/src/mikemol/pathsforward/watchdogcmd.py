# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The command `--tick-open` prints so a session starts the idle watchdog in the background (W1476).

The watchdog's whole alarm is its process exit, and the harness tells a session about the exit of
a background task THE SESSION STARTED. A process the writer detached would exit unseen, so the
writer does not start it: it prints the command, and the session runs it with `run_in_background`.

⚑ THE WATCHDOG LIVES IN MTOOLS' HOOKS DIST, and a repo's writer may be installed anywhere, so the
command is found in this order: a `mikemol-watchdog` on PATH, then the installed script in the
mtools checkout under the home directory, then that checkout's interpreter running the module. The
last is the form that works before a venv has been rebuilt with the console script. None found:
no command, and `--tick-open` says so rather than printing one that cannot run.

⚑ THE WRITER IS NAMED BY ITS OWN PATH (`sys.argv[0]`, made absolute and NOT resolved, W1567), so the
watchdog asks the same writer that printed the command, a different copy on PATH cannot disagree
with it, and a symlinked `.venv` is not followed into a bazel output tree a rebuild can delete.
"""

from collections.abc import Callable
from pathlib import Path

CHECKOUT = ("github", "mtools")
SCRIPT = "mikemol-watchdog"
MODULE = "mikemol.hooks.watchdog"


def command(
    state: Path,
    writer: str,
    home: Path,
    which: Callable[[str], str | None],
) -> str | None:
    """Spell the command that starts the watchdog for this queue.

    Returns:
        a shell-ready line, or None when no watchdog can be found.

    """
    venv_bin = home.joinpath(*CHECKOUT, "hooks", ".venv", "bin")
    found = which(SCRIPT) or (str(venv_bin / SCRIPT) if (venv_bin / SCRIPT).is_file() else None)
    if found is not None:
        runner = found
    elif (venv_bin / "python").is_file():
        runner = f"{venv_bin / 'python'} -m {MODULE}"
    else:
        return None
    return f"{runner} --state {state} --writer {writer}"


def writer_named(argv0: str, which: Callable[[str], str | None]) -> str:
    """Name the writer by the path the caller used, made absolute but never resolved (W1567).

    ⚑ A RESOLVED PATH IS A BAZEL OUTPUT TREE (nemik-84, 2026-10-18): a checkout whose `.venv` is a
    symlink to `bazel-bin/.venv` resolved to `/var/cache/bazel-mikemol/<hash>/execroot/...`, a path
    a rebuild or a cache GC swaps or deletes under a running watchdog, which then cannot call its
    writer. The path the caller typed is the stable one. A bare name is looked up on PATH, and kept
    as it was typed when it is not found.

    Returns:
        the absolute unresolved path, the PATH lookup of a bare name, or `argv0` unchanged.

    """
    if "/" in argv0:
        return str(Path(argv0).absolute())
    return which(argv0) or argv0


def tick_line(
    state: Path,
    argv0: str,
    home: Path,
    which: Callable[[str], str | None],
) -> str:
    """Spell the line `--tick-open` prints about the watchdog.

    ⚑ THE WRITER IS THE ONE THAT IS RUNNING: `argv0` by the path it was run as (`writer_named`), so
    the watchdog asks the copy that printed the command and a different one on PATH cannot
    disagree with it. A session starts the
    command with `run_in_background`; the writer never starts it, because the harness only tells a
    session about the exit of a process the session started.

    Returns:
        `watchdog: start it in the background: <command>`, or a line saying none was found.

    """
    found = command(state, writer_named(argv0, which), home, which)
    if found is None:
        return "watchdog: none found (no mikemol-watchdog on PATH or in the mtools checkout)"
    return f"watchdog: start it in the background: {found}"
