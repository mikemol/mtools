# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-cpu-census`: cores used per cgroup over a window; what is using the host, in one call.

W1051. Read `usage_usec` from every cgroup's `cpu.stat` twice, `--window-s` apart, and print the
cgroups that used the most CPU as cores (microseconds used over microseconds elapsed). On
2026-10-12 this was done by a scratch script and answered the question the commit gate's timeouts
raised: 24.14 of 24 cores in use, 9.97 of them in one kubernetes pod, CPU pressure about 46 percent,
memory and I/O pressure about zero.

    mikemol-cpu-census [--window-s 10] [--top 25] [--depth 5] [--root /sys/fs/cgroup]

⚑ A PARENT'S NUMBER INCLUDES ITS CHILDREN. The root row is the whole host and a slice's row is the
sum of the cgroups beneath it, so rows are not additive; read down the tree to find the leaf that
spends it.

⚑ A CGROUP THAT ENDED OR RESTARTED IN THE WINDOW HAS NO HONEST NUMBER. Its counter is gone or went
backwards, so it is left out of the table, never printed as zero or as a negative.

⚑ THE WALK DOES NOT FOLLOW LINKS, and the filesystem is read through two seams (`snapshot`,
`sleep`) so the table is tested over made-up counters.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

ROOT = Path("/sys/fs/cgroup")
USAGE_KEY = "usage_usec"
STAT = "cpu.stat"
HOST_NAME = "/"
EXIT_USAGE = 2
_MICROSECONDS = 1_000_000.0
_DEFAULT_WINDOW_S = 10.0
_DEFAULT_TOP = 25
_DEFAULT_DEPTH = 5

type Snapshot = Callable[[Path, int], dict[str, int]]


@dataclass(frozen=True, slots=True)
class Row:
    """One cgroup's CPU use over the window, in cores."""

    cores: float
    name: str


def _busiest_first(row: Row) -> tuple[float, str]:
    return -row.cores, row.name


def parse_usage(stat_text: str) -> int | None:
    """Read `usage_usec` from a `cpu.stat` file's text.

    Returns:
        the counter in microseconds, or None when the text has no such line or it is not a number.

    """
    for line in stat_text.splitlines():
        key, _, value = line.partition(" ")
        if key == USAGE_KEY and value.strip().isdecimal():
            return int(value)
    return None


def rows_between(before: Mapping[str, int], after: Mapping[str, int], window_s: float) -> list[Row]:
    """Turn two counter snapshots into cores per cgroup, busiest first.

    Returns:
        a row for every cgroup in both snapshots whose counter did not go backwards; ties are in
        name order.

    """
    found = [
        Row((after[name] - before[name]) / _MICROSECONDS / window_s, name)
        for name in after
        if name in before and after[name] >= before[name]
    ]
    return sorted(found, key=_busiest_first)


def render(rows: Sequence[Row], top: int) -> str:
    """Print the `top` busiest rows, one `cores  name` line each.

    Returns:
        the text, newline-terminated, empty when there are no rows.

    """
    return "".join(f"{row.cores:6.2f} cores  {row.name}\n" for row in rows[:top])


def read_tree(root: Path, depth: int) -> dict[str, int]:
    """Read every cgroup's `usage_usec` at most `depth` levels below `root`.

    Returns:
        the counter by cgroup path relative to `root` (the root itself is `/`); an unreadable or
        malformed `cpu.stat` is left out.

    """
    found: dict[str, int] = {}
    for here, subdirs, files in os.walk(root):
        name = Path(here).relative_to(root).as_posix()
        level = 0 if name == "." else name.count("/") + 1
        if level >= depth:
            subdirs.clear()
        if STAT not in files:
            continue
        try:
            usage = parse_usage((Path(here) / STAT).read_text(encoding="utf-8"))
        except OSError:
            continue
        if usage is not None:
            found[HOST_NAME if name == "." else name] = usage
    return found


def main(
    argv: Sequence[str] | None = None,
    snapshot: Snapshot = read_tree,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Take two snapshots a window apart and print the busiest cgroups.

    Returns:
        0 on success, 2 for a window that is not positive.

    """
    ap = argparse.ArgumentParser(prog="mikemol-cpu-census", description="Cores used per cgroup.")
    ap.add_argument("--window-s", type=float, default=_DEFAULT_WINDOW_S, help="seconds apart")
    ap.add_argument("--top", type=int, default=_DEFAULT_TOP, help="rows to print")
    ap.add_argument("--depth", type=int, default=_DEFAULT_DEPTH, help="levels below the root")
    ap.add_argument("--root", default=str(ROOT), help="the cgroup filesystem root")
    ns = ap.parse_args(list(sys.argv[1:] if argv is None else argv))
    window_s: float = ns.window_s
    top: int = ns.top
    depth: int = ns.depth
    root: str = ns.root
    if window_s <= 0:
        sys.stderr.write("mikemol-cpu-census: --window-s must be positive\n")
        return EXIT_USAGE
    first = snapshot(Path(root), depth)
    sleep(window_s)
    second = snapshot(Path(root), depth)
    sys.stdout.write(render(rows_between(first, second, window_s), top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
