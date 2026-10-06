# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`atomize-imports`: plan, check as a set, and only then write.

⚑⚑ A WRITE NEEDS SET EQUALITY, NOT A COUNT. The sites the rewriter planned are compared, as a set of
(path, line, module), with the sites `importers` finds by an independent walk of the same files;
any member of the symmetric difference refuses the write and is printed. After a write the census is
taken again, and what remains must be exactly the sites the rewriter refused.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod import atomize, report
from mikemol.pycodemod.imports import importers

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

type _Key = tuple[str, int, str]


@dataclass(frozen=True, slots=True)
class AtomizeFlags:
    """What `atomize-imports` was asked: the package, its flat modules' directory, write or not."""

    package: str
    package_dir: str
    write: bool


def _census(paths: Sequence[str], modules: Iterable[str]) -> set[_Key]:
    return {(r.path, r.line, m) for m in sorted(modules) for r in importers(paths, m).rows}


def _say(line: str) -> None:
    sys.stdout.write(f"{line}\n")


def print_atomize(paths: Sequence[str], flags: AtomizeFlags) -> int:
    """Plan the rewrite of every flat sibling import, and write it when the sets agree.

    Returns:
        0 when every site was rewritten and none remains, 1 when a site was refused or the sets
        disagree, 2 when a file could not be read.

    """
    siblings = atomize.siblings_of(flags.package_dir)
    for stem in sorted(siblings.shadowing):
        _say(f"atomize shadowed-sibling {stem} (a stdlib module of that name exists)")
    result = atomize.atomize(paths, siblings, flags.package)
    for site in result.sites:
        why = f" {site.why}" if site.why else ""
        _say(f"atomize {site.verdict} {site.module} {site.path}:{site.line}{why}")
    planned = {(s.path, s.line, s.module) for s in result.sites}
    census = _census(paths, siblings.modules)
    delta = sorted(planned ^ census)
    for path, line, module in delta:
        side = "planned-only" if (path, line, module) in planned else "census-only"
        _say(f"atomize delta {side} {module} {path}:{line}")
    refused = {(s.path, s.line, s.module) for s in result.sites if s.verdict == atomize.REFUSED}
    unfinished = len(delta) + len(refused)
    if flags.write and not delta:
        for path, text in sorted(result.texts.items()):
            Path(path).write_text(text, encoding="utf-8", newline="")
        remaining = sorted(_census(paths, siblings.modules) ^ refused)
        for path, line, module in remaining:
            _say(f"atomize remaining {module} {path}:{line}")
        unfinished = len(remaining) + len(refused)
        _say(f"atomize wrote {len(result.texts)} files")
    elif flags.write:
        _say("atomize refused to write: the planned sites and the census are not the same set")
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], len(paths))
    for text in lines:
        report.note(f"{text}\n")
    return code or (1 if unfinished else 0)
