# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`docshape`: split a docstring's multi-line first paragraph at its first sentence end (D205).

mtools:W1044, the pure planner under paperkit:W335's ask (a census found D205 279 times).
Text in, `Plan` out, nothing written here: `judge` measures the candidate, a later verb writes it.

⚑ ONLY THE SHAPE IS CHANGED. The first paragraph (the lines before the first blank line) becomes a
summary line, a blank line, and the remainder re-wrapped to `WIDTH` columns at the docstring's own
indent. Every word stays, in order; the later paragraphs and the closing quote are untouched.

⚑ WHAT IT WILL NOT SPLIT IS A WORKLIST ROW, NEVER A GUESS. A backslash in the paragraph (a line
continuation or an escape changes meaning when lines are joined), a continuation line indented
past the docstring or opening a bullet or a doctest (layout carries meaning), a paragraph with no
sentence end or `: ` to split at, and a summary that would not fit in `WIDTH` columns are
each refused with the reason, so the verb never trades D205 for E501 or for a changed docstring.

⚑ THE SPLIT POINT is the first sentence end (`.`, `!`, `?` before whitespace) that leaves a
remainder; failing that the first `: `. A one-sentence paragraph with neither has nothing to split
at. A ` - ` is NOT a split point though paperkit:W335 named it: splitting there would have to drop
the dash, and this verb keeps every word.
"""

import ast
import re
import textwrap
from dataclasses import dataclass

from mikemol.pycodemod.cli_typedargs import Plan

WIDTH = 100
_PREFIXES = ("", "r", "R")
_QUOTES = ('"""', "'''")
_BULLET = re.compile(r"\s*(?:[-*+] |\d+[.)] |>>> )")
_SENTENCE = re.compile(r"[.!?](?=\s)")
_COLON = re.compile(r":(?=\s)")
_FIRST_CONTENT_LINE = 1
_ONE_LINE = 1

Owner = ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True, slots=True)
class Site:
    """One docstring's position: its first and last line (1-based), indent, prefix and quote."""

    first: int
    last: int
    indent: str
    prefix: str
    quote: str


def split_point(text: str) -> tuple[str, str] | None:
    """Split a joined paragraph into its summary and the remainder.

    Returns:
        (summary, remainder) at the first sentence end that leaves a remainder, else at the first
        `: `; None when nothing splits it.

    """
    for found in _SENTENCE.finditer(text):
        if text[found.end() :].strip():
            return text[: found.end()], text[found.end() :].strip()
    colon = _COLON.search(text)
    if colon is not None and text[colon.end() :].strip():
        return text[: colon.end()], text[colon.end() :].strip()
    return None


def _opening(owner: Owner, lines: list[str]) -> tuple[str, Site] | None:
    """Read one owner's docstring site, when it is multi-line, triple-quoted and on its own lines.

    Returns:
        (owner name, site), or None when the owner has no such docstring.

    """
    head = owner.body[0] if owner.body else None
    if not (isinstance(head, ast.Expr) and isinstance(head.value, ast.Constant)):
        return None
    if not isinstance(head.value.value, str) or head.end_lineno is None:
        return None
    if head.end_lineno - head.lineno < _ONE_LINE:
        return None
    opening = lines[head.lineno - 1]
    indent = opening[: head.col_offset]
    shut = lines[head.end_lineno - 1].rstrip()
    for prefix in _PREFIXES:
        for quote in _QUOTES:
            if (
                not indent.strip()
                and opening[head.col_offset :].startswith(prefix + quote)
                and shut.endswith(quote)
                and len(shut) == head.end_col_offset
            ):
                name = "<module>" if isinstance(owner, ast.Module) else owner.name
                return name, Site(head.lineno, head.end_lineno, indent, prefix, quote)
    return None


def _sites(tree: ast.Module, lines: list[str]) -> list[tuple[str, Site]]:
    """Find every docstring the planner can read.

    Returns:
        (owner name, site) rows in tree order.

    """
    owners: list[Owner] = [tree]
    owners.extend(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    )
    return [row for row in (_opening(owner, lines) for owner in owners) if row is not None]


def _refusal(paragraph: list[str], indent: str) -> str | None:
    """Say why a paragraph cannot be joined without changing meaning.

    Returns:
        the reason, or None when it can be joined.

    """
    if "\\" in "\n".join(paragraph):
        return "a backslash in the paragraph: joining lines could change its meaning"
    for line in paragraph[_FIRST_CONTENT_LINE:]:
        if line.strip() and (len(line) - len(line.lstrip()) > len(indent) or _BULLET.match(line)):
            return "a continuation line is indented or opens a bullet or doctest"
    return None


def _rewrite(body: list[str], site: Site, width: int) -> tuple[list[str] | None, str]:
    """Rewrite one docstring's content lines, or say why not.

    Returns:
        (new lines, "") when the paragraph was split, (None, "") when it needed no split, and
        (None, reason) when it was refused.

    """
    start = _FIRST_CONTENT_LINE if not body[0].strip() else 0
    end = next((i for i in range(start + 1, len(body)) if not body[i].strip()), len(body))
    paragraph = body[start:end]
    if len(paragraph) <= _ONE_LINE:
        return None, ""
    why = _refusal(paragraph, site.indent)
    if why is not None:
        return None, why
    pieces = split_point(" ".join(part.strip() for part in paragraph))
    if pieces is None:
        return None, "no sentence end or ': ' to split the first paragraph at"
    summary, remainder = pieces
    opener = site.indent + site.prefix + site.quote
    lead = opener if start == 0 else site.indent
    if len(lead + summary) > width:
        return None, f"the summary would be {len(lead + summary)} columns, over {width}"
    wrapped = textwrap.wrap(
        remainder, width=width - len(site.indent), break_long_words=False, break_on_hyphens=False
    )
    out = [] if start == 0 else [opener + body[0]]
    out += [lead + summary, "", *(site.indent + line for line in wrapped)]
    out += body[end:]
    return out, ""


def plan(text: str, width: int = WIDTH) -> Plan:
    """Plan `docshape` for one file's text.

    Returns:
        the Plan: the candidate text, how many docstrings were split, and each refusal as a
        (line, owner, why) worklist row. A file that does not parse is returned unchanged.

    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return Plan(text, 0, ((0, "<file>", "does not parse"),))
    lines = text.split("\n")
    changed = 0
    refused: list[tuple[int, str, str]] = []
    for name, site in reversed(_sites(tree, lines)):
        raw = lines[site.first - 1 : site.last]
        opener = site.indent + site.prefix + site.quote
        body = [raw[0][len(opener) :], *raw[1:]]
        body[-1] = body[-1].rstrip()[: -len(site.quote)]
        new, why = _rewrite(body, site, width)
        if why:
            refused.append((site.first, name, why))
        if new is None:
            continue
        new[-1] += site.quote
        lines[site.first - 1 : site.last] = new
        changed += 1
    return Plan("\n".join(lines), changed, tuple(reversed(refused)))
