# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-rail`: sample memory headroom and keep the fence's ledger total at what it can carry.

W1034, the entry point over `railloop.py`. It reads `/proc/meminfo` every `--interval-s`, lets the
second-order rail (`rail.py`) decide how many cells of `--cell-mb` may run, and when that changes
runs `mikemol-membudget init --reset <MB>` so NEW admissions are throttled (a held lease cannot be
resized yet, mtools:W1029). `--textfile PATH` publishes the allowance, the reading and the
engagement counts for luthen to chart (mtools:W1030); without it they go to stdout.

    mikemol-rail --cell-mb 2048 --reserve-mb 4096 --ceiling 24 --textfile /var/lib/node/rail.prom
    mikemol-rail --cell-mb 2048 --ceiling 24 --dry-run --rounds 3      # decide and print only

⚑ A LIVE RUN WITH NO FENCE ON THE PATH IS REFUSED, NOT SILENT. A sampler that decided and published
allowances while its resizes went nowhere would look like a rail that works; `--dry-run` is the
honest way to run without the fence.

⚑ THE TEXTFILE IS WRITTEN BY RENAME. A scraper reading it mid-write must see the old file or the
new one, never half of one, so the text goes to a sibling temporary file and replaces the target.

⚑ BEST-EFFORT: meminfo that cannot be read is a skipped round (the loop treats empty text so), and
Ctrl-C ends the loop with exit 0. The ledger total stays wherever the rail last put it.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.memres import railloop
from mikemol.memres.rail import Rail
from mikemol.memres.railloop import Plan, Seams

if TYPE_CHECKING:
    from collections.abc import Sequence

MEMINFO = Path("/proc/meminfo")
FENCE = "mikemol-membudget"
EXIT_USAGE = 2
EXIT_NOT_FOUND = 127
EXIT_TIMED_OUT = 124
_RUN_TIMEOUT_S = 30
_DEFAULT_HORIZON_S = 10.0


@dataclass(frozen=True)
class Options:
    """What the command line asked for: the plan, where to publish, whether to leave the ledger."""

    plan: Plan
    textfile: Path | None
    dry_run: bool


def parse(argv: Sequence[str]) -> Options:
    """Read the command line into options (argparse exits 2 on a usage error).

    ⚑ Each Namespace attribute is read once under an explicit annotation, which confines the `Any`
    argparse hands back instead of letting it fan out through the program.

    Returns:
        the options; a `ValueError` from a rail that could not exist (a cell of no size, a ceiling
        below the floor) is left to the caller.

    """
    ap = argparse.ArgumentParser(prog="mikemol-rail", description="Keep the ledger total in step.")
    ap.add_argument("--cell-mb", type=float, required=True, help="memory one cell costs, in MB")
    ap.add_argument("--ceiling", type=int, required=True, help="most cells ever allowed")
    ap.add_argument("--floor", type=int, default=1, help="fewest cells ever allowed")
    ap.add_argument("--reserve-mb", type=float, default=0.0, help="MB kept back from the cells")
    ap.add_argument("--horizon-s", type=float, default=_DEFAULT_HORIZON_S, help="look-ahead")
    ap.add_argument("--swap-weight", type=float, default=0.0, help="share of free swap counted")
    ap.add_argument("--interval-s", type=float, default=railloop.DEFAULT_INTERVAL_S)
    ap.add_argument("--rounds", type=int, default=None, help="stop after N rounds (default: never)")
    ap.add_argument("--textfile", default="", help="write the metrics here (default: stdout)")
    ap.add_argument("--dry-run", action="store_true", help="decide and publish; leave the ledger")
    ns = ap.parse_args(list(argv))
    cell_mb: float = ns.cell_mb
    ceiling: int = ns.ceiling
    floor: int = ns.floor
    reserve_mb: float = ns.reserve_mb
    horizon_s: float = ns.horizon_s
    swap_weight: float = ns.swap_weight
    interval_s: float = ns.interval_s
    rounds: int | None = ns.rounds
    textfile: str = ns.textfile
    dry_run: bool = ns.dry_run
    limits = Rail(cell_mb, reserve_mb, horizon_s, ceiling, floor)
    plan = Plan(limits, swap_weight, interval_s, rounds)
    return Options(plan, Path(textfile) if textfile else None, dry_run)


def write_textfile(path: Path, text: str) -> None:
    """Write `text` to `path` by renaming a sibling temporary file over it."""
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f"{path.name}.")
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(text)
    Path(temporary).replace(path)


def run_fence(argv: Sequence[str]) -> int:
    """Run a fence command, finding its program on the path.

    Returns:
        the exit status; 127 when the program is not on the path, 124 when it ran too long.

    """
    found = shutil.which(argv[0])
    if found is None:
        return EXIT_NOT_FOUND
    try:
        done = subprocess.run(
            [found, *argv[1:]], check=False, capture_output=True, timeout=_RUN_TIMEOUT_S
        )
    except subprocess.TimeoutExpired:
        return EXIT_TIMED_OUT
    return done.returncode


def _read(meminfo: Path) -> str:
    """Read meminfo, or nothing: the loop skips a round it cannot read.

    Returns:
        the text, or "" when the file cannot be read.

    """
    try:
        return meminfo.read_text(encoding="utf-8")
    except OSError:
        return ""


def default_seams(options: Options, meminfo: Path = MEMINFO) -> Seams:
    """Wire the real effects: the host's meminfo, clock and sleep, the textfile, the fence.

    Returns:
        the seams; the runner is None for a dry run.

    """
    textfile = options.textfile

    def publish(text: str) -> None:
        if textfile is None:
            sys.stdout.write(text)
        else:
            write_textfile(textfile, text)

    return Seams(
        read=lambda: _read(meminfo),
        clock=time.monotonic,
        sleep=time.sleep,
        write=publish,
        runner=None if options.dry_run else run_fence,
    )


def main(argv: Sequence[str] | None = None, seams: Seams | None = None) -> int:
    """Run the sampler until its rounds are done or it is interrupted.

    Returns:
        0 on a clean end, 2 for a rail that cannot exist or a live run with no fence on the path.

    """
    try:
        options = parse(sys.argv[1:] if argv is None else argv)
    except ValueError as problem:
        sys.stderr.write(f"mikemol-rail: {problem}\n")
        return EXIT_USAGE
    if seams is None and not options.dry_run and shutil.which(FENCE) is None:
        sys.stderr.write(f"mikemol-rail: {FENCE} is not on the path; use --dry-run without it\n")
        return EXIT_USAGE
    chosen = default_seams(options) if seams is None else seams
    try:
        railloop.run_loop(options.plan, chosen)
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
