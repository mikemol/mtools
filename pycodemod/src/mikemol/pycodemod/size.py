# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Modules too large to read whole and write back: code lines against a per-file cap.

Cleanroomed from substrate's `scratch/_pycodemod_census.py` (`_code_lines`, `module_size`,
`module_size_all`, `_threshold_for`; W43). The rule is a READING rule: a file too large to read
whole and write back, modified, needs decomposing. Every file gets a row, the ones under their cap
too, because "how far under did the split land" is the question after every cut.

⚑⚑ ONLY CODE IS COMPARED TO THE CAP; `physical` IS REPORTED BESIDE IT, NEVER CAPPED. Dense
commentary must not flag the best-documented modules, and a reader still scrolls past every line.

⚑ A SECOND `__main__` GUARD IS REPORTED AT ANY SIZE: one entry point exits and the other is dead.

⚑ THE CAP IS HALVED ONCE PER RECORDED INCIDENT. The incident map and the base cap are the
CALLER's (an operand, matched on the path suffix); the origin hard-coded its own repo's files.

What moved and what did not:

⚑⚑⚑ A DOCSTRING IS NOT CODE. `module_size_all` counted every non-blank line not starting with
`#`, so every docstring line counted against the cap, against its own docstring ("counting
comment lines as bulk would flag the most carefully documented modules"). The origin's separate
`_code_lines` was not called there, and was not right either. MEASURED 2026-09-25 on the test
fixture: it returned lines 1, 3, 5, 6, 8, 9 where the code is 5 and 6. It counted the first and
last line of a multi-line docstring when they carry text, and a lone `]`. One counter now serves
both.

⚑⚑ AN UNREAD FILE IS REPORTED. The origin skipped an unreadable or unparseable file with
`continue`, so it was neither over nor under its cap and the count of files still included it.

⚑ THE ENTRY GUARD IS `__name__ == "__main__"`, EXACTLY (placement's reading). The origin matched
any `if` whose test dump contained the text `__main__`.

⚑ CODE LINES ARE READ FROM THE TOKENS: a line is code when a token other than a comment, a string
or a lone bracket, comma or colon STARTS on it. The origin stripped string literals from each line
with a regex, which an escaped quote defeats: a list item `"a\"b",` left a stray quote and read as
code (line 8 of the same measurement).
"""

from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.placement import is_entry_test
from mikemol.pycodemod.sites import Skip

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

OVERLARGE_LINES = 1200
_NOT_CODE = frozenset(
    {
        tokenize.COMMENT,
        tokenize.STRING,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENDMARKER,
        tokenize.ENCODING,
    }
)
_PUNCTUATION = frozenset({"(", ")", "[", "]", "{", "}", ",", ":"})


@dataclass(frozen=True, slots=True, order=True)
class Size:
    """One module's code and physical line counts, its cap, and why it is over (empty if not)."""

    path: str
    code: int
    physical: int
    defs: int
    entrypoints: tuple[int, ...]
    cap: int
    incidents: int
    why: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Sizes:
    """Every module's size row, and the files that could not be read."""

    rows: list[Size] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)

    def over(self) -> list[Size]:
        """Keep the rows with a reason: over the cap, or more than one entry guard.

        Returns:
            the offending rows.

        """
        return [r for r in self.rows if r.why]


def code_lines(src: str) -> frozenset[int]:
    """Return the 1-based lines that hold code: not blank, not only comment, not only string.

    Returns:
        the code line numbers.

    """
    out: set[int] = set()
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type in _NOT_CODE or tok.string in _PUNCTUATION:
            continue
        out.add(tok.start[0])
    return frozenset(out)


def cap_for(path: str, base: int, incidents: Mapping[str, int]) -> tuple[int, int]:
    """Return a file's cap and incident count: `base` halved once per incident on its suffix.

    Returns:
        the cap and the number of halvings.

    """
    for rel, hits in incidents.items():
        if path == rel or path.endswith("/" + rel):
            return base >> hits, hits
    return base, 0


def _read(path: str) -> tuple[str, ast.Module] | Skip:
    try:
        src = Path(path).read_text(encoding="utf-8")
        return src, ast.parse(src, filename=path)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def _row(path: str, src: str, tree: ast.Module, cap: int, hits: int) -> Size:
    code = len(code_lines(src))
    defs = sum(
        isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for n in ast.walk(tree)
    )
    entry = tuple(
        n.lineno for n in tree.body if isinstance(n, ast.If) and is_entry_test(ast.unparse(n.test))
    )
    why: list[str] = []
    if len(entry) > 1:
        why.append(f"{len(entry)} __main__ guards at {','.join(map(str, entry))}")
    if code > cap:
        halved = f" (halved x{hits}: recorded incidents)" if hits else ""
        why.append(f"{code} code lines > {cap}{halved}")
    return Size(path, code, len(src.splitlines()), defs, entry, cap, hits, tuple(why))


def module_sizes(
    paths: Sequence[str],
    base: int = OVERLARGE_LINES,
    incidents: Mapping[str, int] | None = None,
) -> Sizes:
    """Return every module's size row, under its cap or over it, with the unread files.

    Returns:
        one row per readable file, with the skipped files.

    """
    out = Sizes()
    for path in paths:
        got = _read(path)
        if isinstance(got, Skip):
            out.skipped.append(got)
            continue
        src, tree = got
        cap, hits = cap_for(path, base, incidents or {})
        out.rows.append(_row(path, src, tree, cap, hits))
    out.rows.sort()
    return out
