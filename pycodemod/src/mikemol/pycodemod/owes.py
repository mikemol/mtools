# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Which callers of a name a change did NOT touch — the join of a call census and `git diff`.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`_changed_files`, `fix_owes_callers`).
A def changed; every use of its name in a file the change did not also touch is a caller that may
not have been updated with it. The origin's measured defect: a helper's return tuple widened from
two elements to four, `--calls` found four callers, the author had updated three, and the fourth
still unpacked a pair. `scan` knew the callers and git knew the change; nothing joined them.

⚑⚑⚑ THIS IS A FLOOR, NOT A COUNT. The census is name-scoped (a call through an aliased module is
another key; `Owes.hints` cross-checks it), a name is not a definition (unrelated defs sharing it
all contribute callers), and touched is not updated (a file the change edited for another reason is
excluded). A missed row ships a defect and a spurious one costs a glance, so every blind class is
REPORTED in `Owes`, never assumed away.

What moved and what did not:

⚑⚑ THE REVISION HAS NO DEFAULT. `WORKING` asks for the uncommitted diff against HEAD; anything
else is handed to `git diff --name-only` verbatim. "The callers I did not update" is a different
question for an uncommitted edit than for the last commit, so guessing one answers a question
nobody asked.

⚑⚑ GIT'S REFUSAL RAISES, WITH GIT'S OWN WORDS. The origin returned `(None, message)` beside a
success shape of `(set, description)`, so a caller that forgot the check read a bad revision as an
empty change. An unparseable revision and a clean change are opposite facts; `GitRefusedError`
makes the first unmistakable.

⚑ GIT IS RESOLVED ON PATH ONCE, and its absence is a refusal, not an empty change. ⚑ The repo root
is the CALLER'S; nothing here defaults to a working directory. ⚑ A revision starting with `-` is
refused, and `--` ends the revision list, so no revision string reaches git as an option or path.
⚑ `call` and `ref` both count: a widened signature breaks a `key=fn` handoff as surely as a direct
call. ⚑ The def is not a row.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.hints import AliasHint, alias_hint
from mikemol.pycodemod.sites import Site, Skip, scan

if TYPE_CHECKING:
    from collections.abc import Sequence

WORKING = "WORKING"
_USES = frozenset({"call", "ref"})
_DEF = "def"
_TIMEOUT = 60


class GitRefusedError(RuntimeError):
    """Git could not be run, or refused the revision; the message is git's own."""


@dataclass(frozen=True, slots=True)
class Change:
    """The `.py` files a revision touched, as absolute paths, and how they were asked for."""

    rev: str
    desc: str
    files: frozenset[str]


@dataclass(frozen=True, slots=True)
class Owes:
    """Uses of `name` in files the change did not touch, with the facts that size the answer.

    `defs_changed` of zero means the question has no referent: no def of the name was in the
    change, so every use would read as owed.
    """

    name: str
    change: Change
    owed: list[Site] = field(default_factory=list)
    covered: int = 0
    defs: int = 0
    defs_changed: int = 0
    population: int = 0
    skipped: list[Skip] = field(default_factory=list)
    hints: list[AliasHint] = field(default_factory=list)


def changed_files(rev: str, root: str) -> Change:
    """Ask git which `.py` files `rev` touched under `root`.

    Returns:
        the change, with absolute paths.

    Raises:
        GitRefusedError: git is absent, could not run, or refused the revision.

    """
    git = shutil.which("git")
    if git is None:
        msg = "git is not on PATH"
        raise GitRefusedError(msg)
    if rev.startswith("-"):
        msg = f"refused {rev!r}: a revision starting with '-' would reach git as an option"
        raise GitRefusedError(msg)
    against, desc = (
        ("HEAD", "the uncommitted working diff against HEAD")
        if rev == WORKING
        else (rev, f"git diff --name-only {rev}")
    )
    try:
        proc = subprocess.run(
            [git, "diff", "--name-only", against, "--"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        msg = f"git could not be run: {exc}"
        raise GitRefusedError(msg) from exc
    if proc.returncode != 0:
        msg = f"git refused {rev!r}: {proc.stderr.strip() or '(no message)'}"
        raise GitRefusedError(msg)
    base = Path(root).resolve()
    files = frozenset(
        str(base / rel.strip()) for rel in proc.stdout.splitlines() if rel.strip().endswith(".py")
    )
    return Change(rev, desc, files)


def fix_owes_callers(name: str, rev: str, paths: Sequence[str], root: str) -> Owes:
    """Return the uses of `name` in `paths` that sit in files `rev` did not touch.

    Returns:
        the owed sites, sorted, with the population facts.

    """
    change = changed_files(rev, root)
    population = [str(Path(p).resolve()) for p in paths]
    found = scan(population, name)
    uses = [s for s in found.rows if s.kind in _USES]
    defs = [s for s in found.rows if s.kind == _DEF]
    hints = alias_hint(name, [s.path for s in defs], population)
    return Owes(
        name=name,
        change=change,
        owed=sorted(s for s in uses if s.path not in change.files),
        covered=sum(1 for s in uses if s.path in change.files),
        defs=len(defs),
        defs_changed=sum(1 for s in defs if s.path in change.files),
        population=len(population),
        skipped=[*found.skipped, *hints.skipped],
        hints=hints.rows,
    )
