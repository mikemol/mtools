# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""A script run by path becomes a module run by package: `python3 tools/x.py` to `-m tools.x`.

A script run by path puts ITS OWN directory first on `sys.path`, so whatever it imports as a
package works only because something else put the package's parent there too. `python3 -m pkg.x`
run from the root puts the root first, and the package is simply importable: no bootstrap, no
`PYTHONPATH`, no shadowing from the script's own directory (paperkit:W297, operator 2026-10-06).

This reads text that is not Python (shell, Starlark, Makefiles, docs) for the one shape that
matters: an interpreter, then `<package>/<module>.py`.

⚑⚑ TWO READS OF THE SAME TEXT, AND THE DIFFERENCE IS PRINTED. A RUN is an interpreter token, then
the script; a MENTION is the script's name anywhere else (a comment, a docstring, a path in prose).
Only runs are rewritten. Both are found by their own pattern, so a mention is never silently left
as though it were handled, and a run the interpreter pattern does not know shows up as a mention
to read rather than as nothing.

⚑ AFTER A WRITE, THE RUN CENSUS OF THE NEW TEXT MUST BE EMPTY. That is checked by running the same
census over what was written, not by trusting the substitution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.core import Skip

if TYPE_CHECKING:
    from collections.abc import Sequence

# An interpreter word as it appears in shell and Starlark strings: python3, "$PY", "$(command -v
# python3)", ${PY}; its closing quotes or paren; then whitespace.
INTERPRETER = r"""(?:python3?|\bPY\b)[)"'}]*[ \t]+(?:-[A-Za-z][ \t]+)*"""


@dataclass(frozen=True, slots=True, order=True)
class Run:
    """One occurrence of a package script's name: where, and which."""

    path: str
    line: int
    column: int
    script: str


@dataclass(slots=True)
class Runs:
    """The runs found, the mentions beside them, the new text, and the files not read."""

    runs: list[Run] = field(default_factory=list)
    mentions: list[Run] = field(default_factory=list)
    texts: dict[str, str] = field(default_factory=dict)
    skipped: list[Skip] = field(default_factory=list)


def _script(packages: Sequence[str]) -> str:
    return r"(?:\./)?(?:" + "|".join(re.escape(p) for p in packages) + r")/\w+\.py"


def _run_pattern(packages: Sequence[str], interpreter: str) -> re.Pattern[str]:
    return re.compile(rf"(?P<lead>{interpreter})(?P<script>{_script(packages)})")


def _mention_pattern(packages: Sequence[str]) -> re.Pattern[str]:
    return re.compile(_script(packages))


def _module(script: str) -> str:
    return script.removeprefix("./").removesuffix(".py").replace("/", ".")


def _rewrite(text: str, pattern: re.Pattern[str]) -> str:
    pieces: list[str] = []
    last = 0
    for found in pattern.finditer(text):
        begin, end = found.span("script")
        pieces.extend([text[last:begin], "-m " + _module(text[begin:end])])
        last = end
    pieces.append(text[last:])
    return "".join(pieces)


def scan(paths: Sequence[str], packages: Sequence[str], interpreter: str = INTERPRETER) -> Runs:
    """Find each run of a package script by path, and the mentions that are not runs.

    Returns:
        the runs, the mentions, the text with every run rewritten (only files that had one), and
        the files not read.

    """
    run_re = _run_pattern(packages, interpreter)
    mention_re = _mention_pattern(packages)
    out = Runs()
    for path in paths:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            out.skipped.append(Skip(path, "undecodable", type(exc).__name__))
            continue
        except OSError as exc:
            out.skipped.append(Skip(path, "unreadable", type(exc).__name__))
            continue
        spans: set[tuple[int, int]] = set()
        for number, line in enumerate(text.splitlines(), start=1):
            for found in run_re.finditer(line):
                start = found.start("script")
                spans.add((number, start))
                out.runs.append(Run(path, number, start, found.group("script")))
            for found in mention_re.finditer(line):
                if (number, found.start()) not in spans:
                    out.mentions.append(Run(path, number, found.start(), found.group()))
        if any(r.path == path for r in out.runs):
            out.texts[path] = _rewrite(text, run_re)
    out.runs.sort()
    out.mentions.sort()
    return out
