# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Emit warrants.bib entries for test modules, transcribed from test docstrings.

Usage: mikemol-gen-warrants [--root DIR] [--layout L] <dist> <module> <section>
           >> <dist>/warrants.bib
   or: mikemol-gen-warrants [--root DIR] [--layout L] <dist> <module>=<section> [...] >> ...

where <root>/<dist>/tests/test_<module>.py is the file and <section> is the RUBRIC KEY verbatim. A
function whose `-k <name>}` check already appears in warrants.bib is skipped, so re-running over a
grown file emits only the new functions. Several pairs in one call emit in the order given, into
one stream: a whole new distribution in one append, with no shell loop and no interleaving.

⚑⚑ TWO LAYOUTS, BECAUSE THE ROOT IS NOT A DISTRIBUTION (W669). `--layout dist` (the default) is the
layout above: the file under `tests/`, keys `<dist>-<module>-...`, checks run by the distribution's
own `.venv`. `--layout atom` is the repository root's: a test module BESIDE the script it tests
(the runner every distribution's `mutants` target shares), keyed `root-<module>-...` and checked by
the hooks venv's interpreter from the repository root, which is how `check_mutants/warrants.bib`
was written by hand before this existed. In `atom`, `<dist>` names the directory holding the module
and its bib.

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
from dataclasses import dataclass
from pathlib import Path

_ARTICLES = ("a", "an", "the")
_LEGACY_ARGC = 2


class BraceError(ValueError):
    """A docstring carries a brace, which would corrupt a BibTeX field."""


@dataclass(frozen=True)
class Layout:
    """Where a test module lives and how its warrants are keyed and checked.

    `tests` is the module's path under its base, with `{module}` filled in; `runner` is the
    interpreter the check command names; `key_prefix` replaces the distribution name in the key, or
    is None to keep it.
    """

    tests: str
    runner: str
    key_prefix: str | None


DIST = Layout("tests/test_{module}.py", ".venv/bin/python3", None)
ATOM = Layout("test_{module}.py", "hooks/.venv/bin/python3", "root")
LAYOUTS = {"dist": DIST, "atom": ATOM}
_LAYOUT_NAMES: tuple[str, ...] = tuple(LAYOUTS)


@dataclass(frozen=True)
class Spec:
    """One module to transcribe: where it is, the rubric section its entries land in, its layout."""

    dist: str
    module: str
    section: str
    layout: Layout = DIST

    @property
    def test_file(self) -> str:
        """Name the module's test file as its check commands spell it."""
        return self.layout.tests.format(module=self.module)

    @property
    def key_prefix(self) -> str:
        """Name the prefix every key of this module starts with."""
        return f"{self.layout.key_prefix or self.dist}-{self.module.replace('_', '-')}-"


def _entry(spec: Spec, node: ast.FunctionDef, bib: str) -> str | None:
    """Render one function's entry, or None when the bib already carries it.

    Returns:
        the entry text, or None when already present.

    Raises:
        BraceError: the docstring carries a brace.

    """
    # Keyed on the FILE and the name: two modules may share a test name, and a name-only check
    # skipped the second.
    if f"{spec.test_file} -k {node.name}}}" in bib:
        return None
    doc = ast.get_docstring(node) or ""
    if "{" in doc or "}" in doc:
        msg = f"brace in docstring of {node.name}"
        raise BraceError(msg)
    words = node.name[len("test_") :].split("_")
    prefix = spec.key_prefix
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
    check = f"cmd:{spec.layout.runner} -m pytest {spec.test_file} -k {node.name}"
    return (
        f"@misc{{{key},\n"
        f"  section = {{{spec.section}}},\n"
        f"  title  = {{{title}}},\n"
        f"  claim  = {{{claim}}},\n"
        f"  check  = {{{check}}},\n"
        f"}}\n"
    )


def emit(root: Path, dist: str, pairs: list[tuple[str, str]], layout: Layout = DIST) -> list[str]:
    """Return the missing entries for each (module, section) pair, in the order given.

    Returns:
        one entry per test function the bib does not yet carry.

    """
    base = root / dist
    bib = (base / "warrants.bib").read_text(encoding="utf-8")
    out: list[str] = []
    for module, section in pairs:
        spec = Spec(dist, module, section, layout)
        tree = ast.parse((base / spec.test_file).read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                entry = _entry(spec, node, bib)
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
    parser.add_argument("--layout", choices=_LAYOUT_NAMES, default="dist", help="test layout")
    parser.add_argument("dist")
    parser.add_argument("pairs", nargs="+")
    # ⚑ argparse's `Namespace` is untyped; `vars()` is the boundary, narrowed once per value.
    opts: dict[str, object] = vars(parser.parse_args(argv))
    root_arg = opts["root"]
    pairs_arg = opts["pairs"]
    root = Path(root_arg) if isinstance(root_arg, str) else Path.cwd()
    args = [str(a) for a in pairs_arg] if isinstance(pairs_arg, list) else []
    layout = LAYOUTS[str(opts["layout"])]
    try:
        out = emit(root, str(opts["dist"]), _pairs(args), layout)
    except BraceError as err:
        sys.stderr.write(f"{err}\n")
        return 2
    if out:
        sys.stdout.write("\n" + "\n".join(out))
    sys.stderr.write(f"{len(out)} warrants\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
