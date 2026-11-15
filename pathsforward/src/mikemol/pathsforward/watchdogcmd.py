# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The command `--tick-open` prints so a session starts the idle watchdog in the background (W1476).

The watchdog's whole alarm is its process exit, and the harness tells a session about the exit of
a background task THE SESSION STARTED. A process the writer detached would exit unseen, so the
writer does not start it: it prints the command, and the session runs it with `run_in_background`.

⚑ THE WATCHDOG LIVES IN MTOOLS' HOOKS DIST, and a repo's writer may be installed anywhere, so the
command is found in this order: the `mikemol-watchdog` BESIDE THE WRITER that is running (its own
bin directory, W1898), then the installed script in THIS repository's own `hooks/.venv`, then a
`mikemol-watchdog` on PATH, then this repository's own interpreter running the module. The last
is the form that works before a venv has been rebuilt with the console script. None found: no
command, and `--tick-open` says so rather than printing one that cannot run.

⚑ THE REPOSITORY IS THE ONE THE QUEUE BELONGS TO, NOT A CHECKOUT UNDER THE HOME DIRECTORY (W2382,
github-14, found by linux-sources): the lookup was `~/github/mtools/hooks/.venv`, mtools' own
live working tree, so every other repo's writer could print a command into a venv that is neither
its own nor pinned. `hooks/.venv` is now read under the queue's own root, which exists only in
mtools itself; another repo gets its watchdog from beside its writer or from PATH, or none.

⚑ PATH COMES AFTER THE WRITER'S OWN BIN, NOT BEFORE (the 2026-10-19 no-sibling-paths ruling; the
host's pinned writer printed another repository's venv because PATH named it first): a tool the
writer was installed with is the one that belongs to it, and PATH is whatever the shell happened
to hold.

⚑ THE WRITER IS NAMED BY ITS OWN PATH (`sys.argv[0]`, made absolute and NOT resolved, W1567), so the
watchdog asks the same writer that printed the command, a different copy on PATH cannot disagree
with it, and a symlinked `.venv` is not followed into a bazel output tree a rebuild can delete.
"""

from collections.abc import Callable
from pathlib import Path

SCRIPT = "mikemol-watchdog"
MODULE = "mikemol.hooks.watchdog"


def command(
    state: Path,
    writer: str,
    which: Callable[[str], str | None],
) -> str | None:
    """Spell the command that starts the watchdog for this queue.

    Returns:
        a shell-ready line, or None when no watchdog can be found.

    """
    own_bin = state.parent.parent / "hooks" / ".venv" / "bin"
    beside = [Path(writer).parent / SCRIPT] if "/" in writer else []
    installed = next((str(c) for c in (*beside, own_bin / SCRIPT) if c.is_file()), None)
    found = installed or which(SCRIPT)
    if found is not None:
        runner = found
    elif (own_bin / "python").is_file():
        runner = f"{own_bin / 'python'} -m {MODULE}"
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
    found = command(state, writer_named(argv0, which), which)
    if found is None:
        return "watchdog: none found (not beside the writer, on PATH or in this repo)"
    return f"watchdog: start it in the background: {found}"
