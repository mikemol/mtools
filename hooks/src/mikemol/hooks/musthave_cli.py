# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The `mikemol-repin --must-have` and `--check-must-have` modes (mtools:W1137).

    mikemol-repin --must-have SHA --dists D --reason R [--requires SHA ...] [--write]
    mikemol-repin --check-must-have [--mtools DIR]

`--dists` may repeat, as may `--requires`.

⚑ A DRY RUN UNLESS `--write`, as the rest of `mikemol-repin`: the verb says `WOULD ADDED` (or
`WOULD UPDATED`, `WOULD UNCHANGED`) and writes nothing. Anything refused (a short sha, no dists, a
reason of two lines, a sha that is not a commit in history) exits 2 with the file untouched.

CONSUMED BY: `repin_cli.main`, which hands over the parsed options.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.hooks import musthave

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

    type Runner = Callable[[Sequence[str], Path], tuple[int, str]]

EXIT_FAILED = 1
EXIT_USAGE = 2


def run(
    mtools: Path, valued: Mapping[str, Sequence[str]], flags: frozenset[str], runner: Runner
) -> int:
    """Run one of the two modes against the file in the mtools checkout.

    Returns:
        0 when the file is sound (check) or the entry was added, updated or unchanged (verb);
        1 when the check finds a problem; 2 for a usage refusal, with nothing written.

    """
    path = mtools / musthave.FILE
    loaded = musthave.load(path)
    if isinstance(loaded, str):
        sys.stderr.write(f"mikemol-repin: {loaded}\n")
        return EXIT_USAGE
    if "--check-must-have" in flags:
        problems = [
            *musthave.shape_problems(loaded),
            *musthave.history_problems(loaded, mtools, runner),
        ]
        sys.stdout.writelines(f"PROBLEM {p}\n" for p in problems)
        sys.stdout.write(f"{len(loaded)} fix(es), {len(problems)} problem(s)\n")
        return EXIT_FAILED if problems else 0
    sha = valued["--must-have"][-1]
    reason = valued.get("--reason", [""])[-1]
    merged, status = musthave.add(
        loaded, sha, list(valued.get("--dists", ())), reason, list(valued.get("--requires", ()))
    )
    fresh = [e for e in merged if e.get("sha") == sha]
    problems = [*musthave.shape_problems(merged), *musthave.history_problems(fresh, mtools, runner)]
    if problems:
        sys.stderr.writelines(f"mikemol-repin: {p}\n" for p in problems)
        return EXIT_USAGE
    write = "--write" in flags
    sys.stdout.write(f"{'' if write else 'WOULD '}{status.upper()} {sha[:12]}\n")
    if write and status != "unchanged":
        musthave.save(path, merged)
    return 0
