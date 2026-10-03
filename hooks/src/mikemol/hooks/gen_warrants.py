# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Emit warrants.bib entries for test modules, transcribed from test docstrings.

Usage: mikemol-gen-warrants [--root DIR] <dist> <module> <section> >> <dist>/warrants.bib
   or: mikemol-gen-warrants [--root DIR] <dist> <module>=<section> [...] >> ...

where <root>/<dist>/tests/test_<module>.py is the file and <section> is the RUBRIC KEY verbatim. A
function whose `-k <name>}` check already appears in warrants.bib is skipped, so re-running over a
grown file emits only the new functions. Several pairs in one call emit in the order given, into
one stream: a whole new distribution in one append, with no shell loop and no interleaving.

⚑ THE ROOT IS THE CWD OR `--root`, NEVER `__file__`. The origin (`.claude/gen_warrants.py`)
derived it from its own location, which is the defect this package exists to end: an installed
module lives in a venv, and a worktree's tests are invisible to a root fixed at the main repo.

⚑ A BRACE IN A DOCSTRING EXITS 2 — the could-not-transcribe code — and writes nothing to stdout,
so a `>>` append never receives a half-stream.

CONSUMED BY: the `mikemol-gen-warrants` console script.
"""

from __future__ import annotations

import argparse
import ast
import sys
import textwrap
from pathlib import Path

_ARTICLES = ("a", "an", "the")
_LEGACY_ARGC = 2


class BraceError(ValueError):
    """A docstring carries a brace, which would corrupt a BibTeX field."""


def _entry(dist: str, module: str, section: str, node: ast.FunctionDef, bib: str) -> str | None:
    """Render one function's entry, or None when the bib already carries it.

    Returns:
        the entry text, or None when already present.

    Raises:
        BraceError: the docstring carries a brace.

    """
    # Keyed on the FILE and the name: two modules may share a test name, and a name-only check
    # skipped the second.
    if f"tests/test_{module}.py -k {node.name}}}" in bib:
        return None
    doc = ast.get_docstring(node) or ""
    if "{" in doc or "}" in doc:
        msg = f"brace in docstring of {node.name}"
        raise BraceError(msg)
    words = node.name[len("test_") :].split("_")
    prefix = f"{dist}-{module.replace('_', '-')}-"
    # An older entry may carry no `check` and keep the leading article in its key.
    if f"{{{prefix}{'-'.join(words)}," in bib:
        return None
    if words[0] in _ARTICLES:
        words = words[1:]
    key = prefix + "-".join(words)
    if f"{{{key}," in bib:
        return None
    first, _, rest = doc.partition("\n")
    title = first.strip().rstrip(".")
    body = " ".join((first + " " + rest).split()).replace("⚑", "").replace("  ", " ")
    claim = textwrap.fill(body, width=88, subsequent_indent=" " * 12)
    return (
        f"@misc{{{key},\n"
        f"  section = {{{section}}},\n"
        f"  title  = {{{title}}},\n"
        f"  claim  = {{{claim}}},\n"
        f"  check  = {{cmd:.venv/bin/python3 -m pytest tests/test_{module}.py -k {node.name}}},\n"
        f"}}\n"
    )


def emit(root: Path, dist: str, pairs: list[tuple[str, str]]) -> list[str]:
    """Return the missing entries for each (module, section) pair, in the order given.

    Returns:
        one entry per test function the bib does not yet carry.

    """
    base = root / dist
    bib = (base / "warrants.bib").read_text(encoding="utf-8")
    out: list[str] = []
    for module, section in pairs:
        src = base / "tests" / f"test_{module}.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                entry = _entry(dist, module, section, node, bib)
                if entry is not None:
                    out.append(entry)
    return out


def _pairs(args: list[str]) -> list[tuple[str, str]]:
    """Read the legacy `<module> <section>` form or the `<module>=<section>` list.

    Returns:
        the (module, section) pairs.

    """
    if len(args) == _LEGACY_ARGC and "=" not in args[0]:
        return [(args[0], args[1])]
    return [(m, s) for m, _, s in (arg.partition("=") for arg in args)]


def main(argv: list[str] | None = None) -> int:
    """Write the missing entries to stdout and the count to stderr.

    Returns:
        0 on success, 2 when a docstring carries a brace.

    """
    parser = argparse.ArgumentParser(prog="mikemol-gen-warrants", description=__doc__)
    parser.add_argument("--root", default=None, help="repo root (default: the cwd)")
    parser.add_argument("dist")
    parser.add_argument("pairs", nargs="+")
    # ⚑ argparse's `Namespace` is untyped; `vars()` is the boundary, narrowed once per value.
    opts: dict[str, object] = vars(parser.parse_args(argv))
    root_arg = opts["root"]
    pairs_arg = opts["pairs"]
    root = Path(root_arg) if isinstance(root_arg, str) else Path.cwd()
    args = [str(a) for a in pairs_arg] if isinstance(pairs_arg, list) else []
    try:
        out = emit(root, str(opts["dist"]), _pairs(args))
    except BraceError as err:
        sys.stderr.write(f"{err}\n")
        return 2
    if out:
        sys.stdout.write("\n" + "\n".join(out))
    sys.stderr.write(f"{len(out)} warrants\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
