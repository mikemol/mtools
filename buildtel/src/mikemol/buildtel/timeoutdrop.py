# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W1580: remove an explicit timeout from a grid whose shards now fit the size default.

    python -m mikemol.buildtel.targettimes <commit-log> > rows.jsonl
    python -m mikemol.buildtel.timeoutdrop rows.jsonl <repo-root> [--apply]

⚑ THE SECOND HALF OF W1573 (github-8f, 2026-10-18; the operator's 2026-10-10 ruling that a raised
limit is the wall-clock fix and finer shards are the cure): `shardplan` adds shards to a grid whose
slowest run took over half its size default, and names the explicit `timeout` it would leave. This
removes that timeout, but ONLY when the same rows show the slowest shard at or under the fraction of
the DEFAULT, so the attribute can go without the grid timing out: a grid still over the fraction is
`shardplan`'s to reshard first and is left alone here.

⚑ A DRY RUN UNLESS ASKED, ALL OR NONE, as `shardplan --apply`: only the grid's `timeout` line is
removed, every other line is kept byte for byte, and a BUILD file whose timeout is no longer the
one the plan read is a stale plan, exit 3 with nothing written.
"""

import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from mikemol.buildtel import shardplan

EXIT_USAGE = 2
EXIT_STALE = 3
_ARGC = 2
_MS = 1000
_TIMEOUT_LINE = re.compile(r'\n[ \t]*timeout\s*=\s*"(?P<v>[^"]+)",?')


@dataclass(frozen=True)
class Drop:
    """One grid whose explicit timeout can go: its slowest shard fits the size default."""

    dist: str
    name: str
    timeout: str
    slowest_s: float
    limit_s: int

    def line(self) -> str:
        """Spell the dry-run line.

        Returns:
            the drop as one line with the share of the default the slowest shard took.

        """
        share = round(100 * self.slowest_s / self.limit_s)
        said = f"{self.dist}/BUILD.bazel {self.name}: REMOVE timeout = {self.timeout!r}"
        return f"{said} (slowest {self.slowest_s:.1f} s of a {self.limit_s} s default, {share}%)"


def plan(rows: Sequence[shardplan.Row], read_build: shardplan.ReadBuild) -> list[Drop]:
    """Find every grid with an explicit timeout whose slowest shard fits the size default.

    Returns:
        the drops, in the order the grids were read; a grid still over the fraction, one with no
        timeout and one with no block are left out.

    """
    grids, _plain = shardplan.shard_times(rows)
    out: list[Drop] = []
    for (dist, name), times in grids.items():
        build = read_build(dist)
        block = None if build is None else shardplan.block_of(build, name)
        if block is None or not block.timeout:
            continue
        limit = shardplan.LIMITS.get(block.size, shardplan.LIMITS[shardplan.DEFAULT_SIZE])
        slowest = max(times) / _MS
        if slowest <= shardplan.FRACTION * limit:
            out.append(Drop(dist, name, block.timeout, slowest, limit))
    return out


def rewrite(build: str, drop: Drop) -> str:
    """Remove one grid's `timeout` line, changing nothing else.

    Returns:
        the BUILD text without that grid's timeout line.

    Raises:
        shardplan.StaleDiffError: when no block of that name exists or its timeout is not the
            one the plan read.

    """
    for found in shardplan.block_spans(build):
        body = cast("str", found.group("body"))
        if shardplan.name_of(body) != drop.name:
            continue
        line = _TIMEOUT_LINE.search(body)
        seen = cast("str", line.group("v")) if line is not None else ""
        if line is None or seen != drop.timeout:
            msg = f"{drop.dist}: {drop.name} no longer has timeout = {drop.timeout!r}"
            raise shardplan.StaleDiffError(msg)
        changed = body[: line.start()] + body[line.end() :]
        return build[: found.start("body")] + changed + build[found.end("body") :]
    msg = f"{drop.dist}: no mutants_sharded block named {drop.name}"
    raise shardplan.StaleDiffError(msg)


def apply(root: Path, drops: Sequence[Drop]) -> list[str]:
    """Write every drop into its dist's BUILD.bazel, all or none, one temp file and a replace.

    Returns:
        one line per grid whose timeout went.

    Raises:
        shardplan.StaleDiffError: before anything is written, when a drop no longer matches.

    """
    texts: dict[Path, str] = {}
    for drop in drops:
        build = root / drop.dist / "BUILD.bazel"
        if build.is_symlink() or not build.is_file():
            msg = f"{drop.dist}: BUILD.bazel is missing or a link"
            raise shardplan.StaleDiffError(msg)
        texts[build] = rewrite(texts.get(build) or build.read_text(encoding="utf-8"), drop)
    for build, text in texts.items():
        staging = build.with_name(f"{build.name}.timeoutdrop.tmp")
        staging.write_text(text, encoding="utf-8")
        staging.replace(build)
    return [f"{d.dist} {d.name}: removed timeout = {d.timeout!r}" for d in drops]


def main(argv: Sequence[str] | None = None) -> int:
    """Print the drops for a rows file; with `--apply` write them into the BUILD files.

    Returns:
        0; 2 for a usage error or an unreadable rows file; 3 for a stale plan.

    """
    args = sys.argv[1:] if argv is None else list(argv)
    applying = args[_ARGC:] == [shardplan.APPLY_FLAG]
    if len(args) != _ARGC + int(applying):
        sys.stderr.write("timeoutdrop <rows.jsonl> <repo-root> [--apply]\n")
        return EXIT_USAGE
    path, root = Path(args[0]), Path(args[1])
    if path.is_symlink():
        sys.stderr.write(f"timeoutdrop: {path} is a symlink; refused\n")
        return EXIT_USAGE
    try:
        rows = shardplan.read_rows(path)
    except (OSError, ValueError) as err:
        sys.stderr.write(f"timeoutdrop: {path}: {err}\n")
        return EXIT_USAGE

    def read_build(dist: str) -> str | None:
        build = root / dist / "BUILD.bazel"
        return None if build.is_symlink() or not build.is_file() else build.read_text("utf-8")

    drops = plan(rows, read_build)
    for drop in drops:
        sys.stdout.write(drop.line() + "\n")
    sys.stdout.write(f"{len(drops)} grid(s) whose timeout can go\n")
    if not applying:
        return 0
    try:
        for said in apply(root, drops):
            sys.stdout.write(f"APPLIED {said}\n")
    except shardplan.StaleDiffError as err:
        sys.stderr.write(f"timeoutdrop: nothing written: {err}\n")
        return EXIT_STALE
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
