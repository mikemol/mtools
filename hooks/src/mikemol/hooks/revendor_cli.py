# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-repin --revendor`: move a repo's VENDORED hooks and pathsforward wheels (mtools:W991).

    mikemol-repin --revendor --sha SHA40 [--root REPO] [--mtools DIR] [--write]

⚑ A DRY RUN UNLESS `--write`, like the rest of `mikemol-repin`. Without it the plan is printed and
nothing is built; with it the wheels are built at the commit, the new writer is checked against the
live one over a copy of the queue, and only then are the wheels and the two pins moved
(`revendor_apply`). `--root` is the ONE repo to move (default the current directory), because a
re-vendor rebuilds and replaces files in that repo and syncs its venv; it is never a fleet sweep.

⚑ THE ONE THING IT NEVER DOES IS COMMIT: the result is a diff for the repo's own session, with the
new wheels' sha256 printed for the hand-written `vendor/wheels/README.md`. A repo that vendors no
hooks or pathsforward wheel is refused rather than handed wheels nothing references.

Exit 0 planned or applied · 1 refused or failed · 2 a usage refusal.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import revendor, revendor_apply

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

type Runner = Callable[[Sequence[str], Path], tuple[int, str]]

EXIT_FAILED = 1
EXIT_USAGE = 2


def _say(line: str) -> None:
    sys.stdout.write(f"{line}\n")


def _refuse(why: str) -> int:
    sys.stderr.write(f"mikemol-repin: {why}\n")
    return EXIT_USAGE


def run_revendor(repo: Path, sha: str, mtools: Path, runner: Runner, *, write: bool) -> int:
    """Print the plan and, with `write`, re-vendor the repo at the commit.

    Returns:
        0 when planned or applied, 1 when refused or failed, 2 for a usage refusal.

    """
    project = repo / "pyproject.toml"
    if not revendor.is_full_sha(sha):
        return _refuse("--revendor needs --sha, a full 40-hex commit")
    if not project.is_file() or not mtools.is_dir():
        return _refuse(f"needs a pyproject.toml in {repo} and an mtools checkout at {mtools}")
    old = revendor.pinned_shorts(project.read_text(encoding="utf-8"))
    if not old:
        return _refuse(f"{repo.name} vendors no hooks or pathsforward wheel")
    for line in revendor.plan_lines(sha, old, mtools.name):
        _say(f"PLAN {line}")
    if not write:
        return 0
    writer = repo / ".venv" / "bin" / "mikemol-paths-forward"
    target = revendor_apply.Target(repo, mtools, sha, writer)
    failure = revendor_apply.apply(runner, target)
    if failure is not None:
        _say(f"REFUSED {failure}")
        return EXIT_FAILED
    for dist, digest in revendor_apply.checksums(target).items():
        _say(f"SHA256 {dist} {digest}")
    _say(f"APPLIED {repo.name} at {revendor.short_of(sha)}")
    return 0
