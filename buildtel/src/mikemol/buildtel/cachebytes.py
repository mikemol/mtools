# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Measure the bytes bazel's caches hold, by kind, and say which output bases are dead (W1659).

    python -m mikemol.buildtel.cachebytes [REPO_DIR]

⚑ ONE ROW PER CONSUMER, NOT ONE TOTAL (github-8f, 2026-10-18, imagefs_gc_pressure at 82%): the
cache a presubmit warms is also the cache that fills the disk, and a total cannot say which
consumer grew. A row is `kind`, `path`, `workspace`, `live`, `bytes`, `exclusive` and
`measured_at`.

⚑ `bytes` OVERCOUNTS AND `exclusive` IS WHAT A DELETION RETURNS (W1664, github-8f): output bases
share extents through reflinks and dedup, so blocks summed per base double-count. Measured on one
base: 36.9 GB by blocks, 18.4 GB by `btrfs filesystem du`, and only 4.5 GB exclusive. `exclusive`
is that third figure, None on a filesystem the tool cannot ask, and the dead total is summed over
it where it is known, so 'dead bytes' reads as what expunging would free.

⚑ THE PLACES ARE READ, NOT TYPED: `--output_user_root` and `--disk_cache` come from the user's
`~/.bazelrc` and the repo's `.bazelrc`, the user's last, as bazel itself resolves them, so the
tool measures where bazel writes and cannot drift from it. An option bazel does not set is a row
the tool does not print, not a guessed path.

⚑ AN OUTPUT BASE NAMES ITS OWN WORKSPACE: bazel writes the workspace path it was made for into
`<output_base>/DO_NOT_BUILD_HERE`, so a base whose workspace no longer exists is DEAD, which is
what a removed worktree leaves behind. A base with no readable name is `live: null`, never
assumed dead: nothing here deletes, it only measures, and reclaiming is a separate act.

⚑ BYTES ARE BLOCKS ON DISK (`st_blocks * 512`), not apparent size, because the disk fills by
blocks; a link is counted as a link and never followed (no-symlinks ruling).

⚑ FRESHNESS IS IN THE ROW: `measured_at` is the UTC time of the walk, so a reader can refuse a
row older than the rate its consumer grows at, instead of trusting a number of unknown age.
"""

import json
import os
import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from mikemol.buildtel import proc

NAME_FILE = "DO_NOT_BUILD_HERE"
BLOCK = 512
EXIT_USAGE = 2
DU_FIELDS = 4
Sizer = Callable[[Path], int]
Exclusive = Callable[[Path], int | None]


@dataclass(frozen=True)
class Row:
    """One cache consumer: what it is, where, whose it was, whether that lives, how big."""

    kind: str
    path: str
    workspace: str
    live: bool | None
    size: int
    measured_at: str
    exclusive: int | None = None

    def as_json(self) -> str:
        """Spell the row as one JSON line, the size under the key `bytes`.

        Returns:
            the line, without a newline.

        """
        fields = {
            "kind": self.kind,
            "path": self.path,
            "workspace": self.workspace,
            "live": self.live,
            "bytes": self.size,
            "exclusive": self.exclusive,
            "measured_at": self.measured_at,
        }
        return json.dumps(fields)

    def freed(self) -> int:
        """Say what deleting this consumer would return: exclusive bytes where known.

        Returns:
            the exclusive bytes, else the block bytes.

        """
        return self.size if self.exclusive is None else self.exclusive


def disk_bytes(root: Path) -> int:
    """Sum the blocks on disk under `root`, links counted as links and never followed.

    Returns:
        bytes; 0 for a path that does not exist.

    """
    total = 0
    pending = [str(root)]
    while pending:
        try:
            with os.scandir(pending.pop()) as entries:
                for entry in entries:
                    total += entry.stat(follow_symlinks=False).st_blocks * BLOCK
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(entry.path)
        except OSError:
            continue
    return total


def exclusive_bytes(path: Path, run: proc.Runner = proc.capture) -> int | None:
    """Ask btrfs how many bytes under `path` no other file shares.

    Returns:
        the Exclusive column of `btrfs filesystem du -s --raw`, or None when the command fails
        (not btrfs, no tool, no access) or prints something else.

    """
    try:
        code, out, _err = run(["btrfs", "filesystem", "du", "-s", "--raw", str(path)])
    except OSError:
        return None
    lines = out.splitlines()
    fields = lines[-1].split() if code == 0 and lines else []
    if len(fields) >= DU_FIELDS and fields[1].isdigit():
        return int(fields[1])
    return None


def option(files: Sequence[Path], name: str) -> Path | None:
    """Read a bazelrc option's value, the last file and the last line winning.

    Returns:
        the path the option names, or None when no file sets it.

    """
    found: Path | None = None
    pattern = re.compile(rf"^\s*(?:startup|build)\s+--{name}=(\S+)", re.MULTILINE)
    for rc in files:
        try:
            hits = cast("list[str]", pattern.findall(rc.read_text(encoding="utf-8")))
        except OSError:
            continue
        if hits:
            found = Path(hits[-1])
    return found


def workspace_of(base: Path) -> str:
    """Read the workspace path bazel recorded in an output base.

    Returns:
        the path, or "" when the file is absent or unreadable.

    """
    try:
        return (base / NAME_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _unknown(_path: Path) -> int | None:
    return None


def _freed_of(row: Row) -> int:
    return row.freed()


def output_rows(root: Path, size: Sizer, now: str, exclusive: Exclusive = _unknown) -> list[Row]:
    """Measure every output base under `root`, each against its own workspace.

    Returns:
        one row per base, the one a deletion would free most first; `live` is None for a base
        that names no workspace.

    """
    rows: list[Row] = []
    if not root.is_dir():
        return rows
    for base in sorted(root.iterdir()):
        if not (base / "execroot").is_dir():
            continue
        space = workspace_of(base)
        live = Path(space).is_dir() if space else None
        rows.append(Row("output_base", str(base), space, live, size(base), now, exclusive(base)))
    return sorted(rows, key=_freed_of, reverse=True)


def main(
    argv: Sequence[str] | None = None,
    size: Sizer = disk_bytes,
    exclusive: Exclusive = exclusive_bytes,
) -> int:
    """Print one JSON row per consumer, then a summary row of the dead bytes.

    Returns:
        0; 2 for a usage error.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1 or any(a.startswith("-") for a in args):
        sys.stderr.write("cachebytes [REPO_DIR]\n")
        return EXIT_USAGE
    repo = Path(args[0]) if args else Path.cwd()
    rcs = [repo / ".bazelrc", Path.home() / ".bazelrc"]
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: list[Row] = []
    out_root = option(rcs, "output_user_root")
    if out_root is not None:
        rows += output_rows(out_root, size, now, exclusive)
    disk = option(rcs, "disk_cache")
    if disk is not None:
        free = exclusive(disk)
        cache = Row("disk_cache", str(disk), "", disk.is_dir() or None, size(disk), now, free)
        rows.append(cache)
    for row in rows:
        sys.stdout.write(row.as_json() + "\n")
    dead = [r for r in rows if r.live is False]
    summary = {
        "kind": "dead_output_bases",
        "bytes": sum(r.size for r in dead),
        "freed": sum(r.freed() for r in dead),
        "measured_at": now,
    }
    sys.stdout.write(json.dumps(summary) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
