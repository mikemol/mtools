# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Load every witness the way the bib spells it: a bare interpreter, the project as cwd.

Ported from paperkit's `tools/witness_reach.py` (mtools:W565). Behaviour changes forced by the
move: paperkit located the repository from the module's own path, an installed tool has none, so
the root is the current directory, or `--root PATH`; the child interpreter is the running one
(`sys.executable`) rather than a PATH lookup of `python3`; and the child's import path is carried
in its `PYTHONPATH` environment variable, built by `mikemol.importdag.dagnames.child_env`, instead
of a `sys.path` edit in its code string. The child binds `mikemol.importdag.dagnames` first, as
every consumer of the partition does, then imports the witness by name.

The interpreter in the bib is not the one a developer types. Every `cmd:` check reads
`python3 checks/NAME.py`, which is an interpreter with no virtualenv. A developer probing with the
project's own environment gets the editable install and therefore the project package on the
path; the gate gets neither. A check module once passed every route probed by hand and then
reddened a very large sweep with a missing-module error.

A gate also stops at the first red per project, so one failure says nothing about the other
checks in that project. This asks for all of them in seconds, so the set that cannot load is known
before the next sweep rather than one red per multi-hour run.

It loads and does not run, deliberately. Most render witnesses shell out to heavy converters and
take minutes; the question here is only whether the module loads, which is exactly what a
missing-module error answers. A witness that loads may still fail its own check; that is a
different question and the gate's to ask.

    mikemol-witness-reach                  # every witness tree under the current directory
    mikemol-witness-reach render           # one project's checks directory
    mikemol-witness-reach --root DIR       # the repository is DIR
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.importdag import dagnames

if TYPE_CHECKING:
    from collections.abc import Sequence

EXCLUDE = frozenset({"__init__.py"})
"""File names in a checks directory that are not witnesses."""

CHILD_TIMEOUT = 120
"""Seconds a child interpreter may take to load one witness."""

TAIL_WIDTH = 96
"""Characters of a failing child's last output line that are reported."""


class Options(argparse.Namespace):
    """What the command line asked for."""

    root: Path
    projects: list[str]


def trees(root: Path) -> list[Path]:
    """Find every project checks directory under the repository root.

    Returns:
        The sorted directories named `checks` that sit directly inside a child of `root`.

    """
    return sorted(p for p in root.glob("*/checks") if p.is_dir())


def child_environment(tree: Path) -> dict[str, str]:
    """Build the environment a witness-loading child runs under.

    A script's own directory is the first entry on the path when it runs as
    `python3 checks/NAME.py`, which is how sibling imports between witnesses resolve on the real
    route. The checks directory therefore leads `PYTHONPATH`, ahead of the roots that
    `dagnames.child_env` supplies for the project.

    Returns:
        The `dagnames.child_env` environment with the checks directory prepended to `PYTHONPATH`.

    """
    env = dagnames.child_env(tree.parent)
    env["PYTHONPATH"] = os.pathsep.join([str(tree), env["PYTHONPATH"]])
    return env


def probe(tree: Path, name: str) -> tuple[int, str]:
    """Load one witness on the route the bib spells and report how it went.

    The route is the whole point. Importing the witness as a package from the repository root
    reports failures that are sibling imports, which resolve on the real route because a script's
    own directory leads its path. A probe answering for a route nobody takes manufactures findings
    exactly as readily as it misses them. So the cwd is the project directory and the checks
    directory leads the child's path; importing the module by name then executes everything
    except the main-guard body.

    Returns:
        The child's return code, and the last non-blank line of its output cut at 96 characters
        (empty when it said nothing).

    """
    stem = name.removesuffix(".py")
    code = dagnames.CHILD_PRELUDE + f"importlib.import_module({stem!r})"
    r = subprocess.run(
        [sys.executable or "python3", "-c", code],
        cwd=tree.parent,
        env=child_environment(tree),
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT,
        check=False,
    )
    tail = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip()]
    return r.returncode, (tail[-1][:TAIL_WIDTH] if tail else "")


def parse_args(argv: Sequence[str] | None) -> Options:
    """Read the command line.

    Returns:
        The options, with the current directory as the root when `--root` is not given.

    """
    ap = argparse.ArgumentParser(prog="mikemol-witness-reach", description=__doc__)
    ap.add_argument("--root", type=Path, default=Path.cwd(), help="the repository root")
    ap.add_argument("projects", nargs="*", help="only these projects (default: every project)")
    return ap.parse_args(argv, namespace=Options())


def main(argv: Sequence[str] | None = None) -> int:
    """Report which witnesses fail to load under the interpreter and cwd the bib names.

    Returns:
        0 when every witness loads, 1 when any does not.

    """
    args = parse_args(argv)
    want = set(args.projects)
    out = sys.stdout
    total = bad = 0
    for tree in trees(args.root.resolve()):
        project = tree.parent.name
        if want and project not in want:
            continue
        names = sorted(p.name for p in tree.glob("*.py") if p.name not in EXCLUDE)
        out.write(f"\n{project}/checks — {len(names)} witnesses\n")
        for n in names:
            total += 1
            rc, last = probe(tree, n)
            if rc:
                bad += 1
                out.write(f"  XX {n:<24} {last}\n")
    out.write(f"\n{total - bad} of {total} load cleanly under a bare interpreter · {bad} FAIL\n")
    if bad:
        out.write("  ⚑ each failure is a gate red waiting for a sweep to reach it.\n")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
