# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Enumerate the def-sites of a .py source, the unit of def-resolution mutation.

Ported from paperkit's `tools/def_sites.py` (paperkit:W142), behaviour unchanged. `def_sites`
mirrors paperkit's `grader._def_sites` (the SAME rule the in-process sweep uses): every def or
method whose body starts on a line after its signature (a one-liner cannot be body-isolated, so
it is skipped), qualname-prefixed by the enclosing classes and defs. The CLI emits
`relpath<TAB>qualname` per site, so a generator can declare one cell per (claim, site).

Usage:  python -m mikemol.mutantcell.def_sites [--lines] <file.py> ...
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

_USAGE_EXIT = 2
_USAGE = (
    "usage: def_sites.py [--lines] <file.py> ...\n"
    "  bare      relpath<TAB>qualname: the mutation surface (grader._def_sites)\n"
    "  --lines   relpath<TAB>qualname<TAB>first-last: where each site SITS\n"
)
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _collect_sites(node: ast.AST, prefix: str, out: list[str]) -> None:
    """Append the qualname of every body-isolable def under `node`, in source order."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            if child.body[0].lineno > child.lineno:
                out.append(prefix + child.name)
            _collect_sites(child, prefix + child.name + ".", out)
        elif isinstance(child, ast.ClassDef):
            _collect_sites(child, prefix + child.name + ".", out)
        else:
            _collect_sites(child, prefix, out)


def def_sites(text: str) -> list[str]:
    """List the def-sites of a source: the mutation surface.

    Returns:
        The qualnames in source order; empty when the text does not parse.

    """
    out: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    _collect_sites(tree, "", out)
    return out


def _collect_lines(node: ast.AST, prefix: str, out: dict[str, tuple[int, int]]) -> None:
    """Record `(first_line, last_line)` of every def and class under `node`, by qualname."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _SCOPES):
            out[prefix + child.name] = (child.lineno, child.end_lineno or child.lineno)
            _collect_lines(child, prefix + child.name + ".", out)
        else:
            _collect_lines(child, prefix, out)


def def_lines(text: str) -> dict[str, tuple[int, int]]:
    """Locate each def-site: where it SITS.

    A SEPARATE WALK, DELIBERATELY, AND `def_sites` IS UNTOUCHED. That function's output IS the
    mutation surface: every claim's sensitivity fingerprint is a set of `module::qualname`
    strings drawn from it, so a change to what it emits (or the order) silently re-keys the whole
    grid. This walk answers a different question, WHERE a site is, for a reader, and shares only
    the recursion shape. It also lists classes and the one-liners the sweep cannot isolate.

    Returns:
        `{qualname: (first_line, last_line)}`; empty when the text does not parse.

    """
    out: dict[str, tuple[int, int]] = {}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    _collect_lines(tree, "", out)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    """Print each file's def-sites; `--lines` adds where each sits.

    `--lines` IS OPT-IN so the DEFAULT output stays byte-identical: a generator consumes this
    stdout, and an unconditional extra column would change every emitted cell name.

    Returns:
        0 on success; 2 (with a usage note on stderr) when no file is named.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    want_lines = "--lines" in args
    files = [a for a in args if a != "--lines"]
    if not files:
        sys.stderr.write(_USAGE)
        return _USAGE_EXIT
    for arg in files:
        text = Path(arg).read_text(encoding="utf-8")
        if want_lines:
            for qn, (first, last) in def_lines(text).items():
                sys.stdout.write(f"{arg}\t{qn}\t{first}-{last}\n")
        else:
            for qn in def_sites(text):
                sys.stdout.write(f"{arg}\t{qn}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
