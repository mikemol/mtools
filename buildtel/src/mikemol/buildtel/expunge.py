# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Remove the bazel output bases whose workspace is gone, largest exclusive bytes first (W1656).

    python -m mikemol.buildtel.expunge [REPO_DIR]            # dry run: what would be removed
    python -m mikemol.buildtel.expunge [REPO_DIR] --write    # remove it

⚑ ONLY A DEAD BASE, AND ONLY WHEN NOTHING IS USING IT (github-8f, 2026-10-19: 84 of 110 output bases
under /var/cache/bazel-mikemol belonged to workspaces that no longer exist, 118 GB by blocks):
`cachebytes` already calls a base dead when the workspace its DO_NOT_BUILD_HERE names is gone, and
this removes exactly those. A base whose workspace still exists, one that names none (unknown,
never assumed dead) and one whose bazel server is still running (`server/server.pid.txt` names a
live process) are each LEFT and the reason is printed, because deleting a base under a running
server breaks that server's build.

⚑ WHAT A DELETION RETURNS IS EXCLUSIVE BYTES, NOT BLOCKS: bases share extents through reflinks, so
the plan sorts by the btrfs exclusive figure (`cachebytes.Row.freed`) and prints it, and the total
is what the removal would free. A base on a filesystem that cannot say falls back to blocks.

⚑ A DRY RUN UNLESS ASKED, as every other bulk command here: without `--write` nothing is removed.
Each removal is named as it happens, and one that fails is said and does not stop the rest.

⚑ THE ROOT IS READ FROM BAZEL'S OWN CONFIG (`cachebytes.option`), and a base is removed only when it
is a direct child of that root that holds an `execroot`, so a path outside it is never touched.
"""

import os
import shutil
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from mikemol.buildtel import cachebytes

EXIT_USAGE = 2
WRITE_FLAG = "--write"
PID_FILE = Path("server") / "server.pid.txt"
GIB = 2**30
OWNER_ALL = 0o700
Remove = Callable[[Path], None]
Alive = Callable[[int], bool]


@dataclass(frozen=True)
class Step:
    """One base and what the plan does with it."""

    row: cachebytes.Row
    action: str
    reason: str


def pid_alive(pid: int) -> bool:
    """Say whether a process with this pid exists.

    Returns:
        True when /proc has an entry for it.

    """
    return Path("/proc", str(pid)).is_dir()


def server_pid(base: Path) -> int | None:
    """Read the pid of the bazel server that owns a base.

    Returns:
        the pid, or None when the file is absent or does not hold a number.

    """
    try:
        text = (base / PID_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return int(text) if text.isdigit() else None


def _order(step: Step) -> tuple[bool, int]:
    return step.action != "remove", -step.row.freed()


def plan(rows: Sequence[cachebytes.Row], alive: Alive = pid_alive) -> list[Step]:
    """Decide, for each output base, whether it is removed or left and why.

    Returns:
        one step per output base, the removals first and largest freed bytes first.

    """
    steps: list[Step] = []
    for row in rows:
        if row.kind != "output_base":
            continue
        pid = server_pid(Path(row.path))
        if row.live is not False:
            why = "its workspace exists" if row.live else "it names no workspace"
            steps.append(Step(row, "keep", why))
        elif pid is not None and alive(pid):
            steps.append(Step(row, "keep", f"its bazel server (pid {pid}) is running"))
        else:
            steps.append(Step(row, "remove", "its workspace is gone"))
    return sorted(steps, key=_order)


def _unlock(base: Path) -> None:
    # Bazel makes its trees read-only; every directory is made writable so its entries can go.
    pending = [str(base)]
    while pending:
        here = Path(pending.pop())
        here.chmod(OWNER_ALL)
        with os.scandir(here) as entries:
            pending += [e.path for e in entries if e.is_dir(follow_symlinks=False)]


def remove_tree(base: Path) -> None:
    """Remove one output base, read-only directories included, never following a link."""
    _unlock(base)
    shutil.rmtree(base)


def run(
    root: Path, steps: Sequence[Step], *, write: bool, remove: Remove = remove_tree
) -> list[str]:
    """Print the plan and, with `write`, carry out its removals.

    Returns:
        the lines to print, the last a total of what was or would be removed.

    """
    lines: list[str] = []
    count = 0
    freed = 0
    for step in steps:
        path = Path(step.row.path)
        if step.action != "remove":
            lines.append(f"KEEP {path.name}: {step.reason}")
            continue
        size = f"{step.row.freed() / GIB:.1f} GiB"
        if not write:
            lines.append(f"WOULD REMOVE {path.name} ({size}, workspace {step.row.workspace})")
        elif path.parent != root or not (path / "execroot").is_dir():
            lines.append(f"KEEP {path.name}: it is not a base directly under {root}")
            continue
        else:
            try:
                remove(path)
            except OSError as err:
                lines.append(f"FAILED {path.name}: {err}")
                continue
            lines.append(f"REMOVED {path.name} ({size})")
        count += 1
        freed += step.row.freed()
    verb = "removed" if write else "would remove"
    lines.append(f"{verb} {count} base(s), {freed / GIB:.1f} GiB exclusive")
    return lines


def _no_blocks(_path: Path) -> int:
    return 0


def main(
    argv: Sequence[str] | None = None,
    exclusive: cachebytes.Exclusive = cachebytes.exclusive_bytes,
    remove: Remove = remove_tree,
) -> int:
    """Print what would be removed, or remove it with `--write`.

    Returns:
        0; 2 for a usage error or when bazel's config names no output root.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    write = WRITE_FLAG in args
    names = [a for a in args if a != WRITE_FLAG]
    if len(names) > 1 or any(a.startswith("-") for a in names):
        sys.stderr.write("expunge [REPO_DIR] [--write]\n")
        return EXIT_USAGE
    repo = Path(names[0]) if names else Path.cwd()
    root = cachebytes.option([repo / ".bazelrc", Path.home() / ".bazelrc"], "output_user_root")
    if root is None:
        sys.stderr.write("expunge: bazelrc names no output_user_root\n")
        return EXIT_USAGE
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = cachebytes.output_rows(root, _no_blocks, now, exclusive)
    lines = run(root, plan(rows), write=write, remove=remove)
    sys.stdout.write("\n".join(lines) + "\n")
    return 0
