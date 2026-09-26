# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Where a SOURCE SHAPE occurs, located: a regex over lines, in code only by default.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`shape_sites`; W43). The defects this
finds are spellings (`X or None`, `len({...}) file(s)`), not AST shapes, so the pattern is a regex
over source LINES and every row is `path:line`, like the rest of the toolkit.

⚑⚑ COMMENTS AND DOCSTRINGS ARE EXCLUDED BY DEFAULT: prose describing a defect must not match the
scan for it. `in_code_only=False` asks the other question, whether anything MENTIONS the shape.
Code lines are `size.code_lines`: a code line with a trailing comment is still code.

What moved and what did not:

⚑⚑⚑ NO WHOLE-FILE PRE-FILTER, SO AN ANCHOR CANNOT PRODUCE A FALSE ZERO. The origin searched the
whole source first (with `re.M`, after `^` and `$` had already bitten it twice) and skipped a file
that did not match, calling that filter a superset of the per-line match. For `\A` it is not:
whole-file `\A` is the start of the FILE, per-line `\A` the start of every line. MEASURED
2026-09-25 on the origin: `\Aimport` returned nothing over a file whose line 2 is `import os`,
while `^import` found it. Lines are now matched first, which is cheap and exact, and only a file
with a matching line is tokenized.

⚑⚑ AN UNDECODABLE FILE IS SKIPPED, NOT MATCHED AS MOJIBAKE. The origin read with
`errors="replace"`, so a non-UTF-8 file matched and was reported with replacement characters in
its text (measured: `'�� import os'`). It is now in `skipped`, as is an unreadable
file (the origin dropped it with `continue`) and one that will not tokenize.
"""

from __future__ import annotations

import re
import tokenize
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import Skip
from mikemol.pycodemod.size import code_lines

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True, order=True)
class Shape:
    """One line where the shape occurs, and its stripped text."""

    path: str
    line: int
    text: str


@dataclass(frozen=True, slots=True)
class Shapes:
    """The matching lines, and the files that could not be read."""

    rows: list[Shape] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _read(path: str) -> str | Skip:
    try:
        return Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)


def shape_sites(pattern: str, paths: Sequence[str], *, in_code_only: bool = True) -> Shapes:
    """Return every line in `paths` matching `pattern`, in code lines only unless told otherwise.

    Returns:
        the matching lines, with the skipped files.

    """
    rx = re.compile(pattern)
    out = Shapes()
    for path in paths:
        src = _read(path)
        if isinstance(src, Skip):
            out.skipped.append(src)
            continue
        hits = [(i, ln) for i, ln in enumerate(src.splitlines(), 1) if rx.search(ln)]
        if not hits:
            continue
        if in_code_only:
            try:
                code = code_lines(src)
            except (tokenize.TokenError, SyntaxError) as exc:
                out.skipped.append(Skip(path, "untokenizable", type(exc).__name__))
                continue
            hits = [(i, ln) for i, ln in hits if i in code]
        out.rows.extend(Shape(path, i, ln.strip()) for i, ln in hits)
    out.rows.sort()
    return out
