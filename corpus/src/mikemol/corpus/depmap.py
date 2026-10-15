# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A dependency map of one or more repos, derived from their syntax trees (mtools:W1251).

    python3 -m mikemol.corpus.depmap [--rows] [--mention WORD] ROOT [ROOT ...]

⚑ FOUR EDGE KINDS, ONE WALK PER FILE, EACH READ FROM THE TREE, NEVER FROM A TEXT SEARCH OF CODE:

    import       a module-level or deferred import, collapsed to its owner (`mikemol.<dist>`
                 for the shared namespace, else the top-level name); the standard library is
                 left out
    subprocess   the first element of a literal argv list passed to a spawn call (the CLI
                 contract: which executable one tool runs), or the name given to `which`
    path         a string constant, docstrings excluded, that names a file by suffix (the
                 file-format contract: which file one tool reads or writes)
    mention      a comment or string token that names WORD, so the places one lineage speaks
                 of another are listed rather than remembered (`--mention nemik`)

⚑ A SOURCE IS `<repo>/<dist>`, the dist being the first directory of the path when that directory
holds a pyproject.toml, else the repo alone; one repo with many dists reads as many sources. A
file under a `tests` directory reads as `<source>:tests`, so a fixture's file names are not the
dist's own contract.

⚑ OUTPUT IS AGGREGATE BY DEFAULT: `COUNT kind source target` rows, an import row marked `deferred`
when no occurrence is module-level. `--rows` prints one row per occurrence instead, with file and
line (import rows carry line 0: the import census is per file, not per statement).

⚑ WHAT IT CANNOT SEE, said in the output's first line too: a tool reached through a variable argv,
a file named by a computed path, an executable named outside a call's first list, and anything a
build file or a container image wires. Those are not absent edges; they are edges this reader
returns empty for.
"""

from __future__ import annotations

import ast
import io
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from mikemol.corpus import corpus, import_edges

if TYPE_CHECKING:
    from collections.abc import Sequence

NAMESPACE = "mikemol"
EXIT_USAGE = 2
_SPAWN = frozenset({"run", "Popen", "check_output", "check_call", "call", "create_subprocess_exec"})
_SUFFIXES = "json|jsonl|ledger|md|toml|tsv|bib|rego|txt|yaml|yml"
_PATH = re.compile(rf"^[\w./-]+\.({_SUFFIXES})$")
_USAGE = "usage: python3 -m mikemol.corpus.depmap [--rows] [--mention WORD] ROOT [ROOT ...]\n"
_BLIND = (
    "# cannot see: a variable argv, a computed path, an executable named outside a call's first\n"
    "# list, build-file and image wiring\n"
)
_DEFS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
_DEFERRED = "\tdeferred"


@dataclass(frozen=True)
class Edge:
    """One dependency one file declares."""

    kind: str
    source: str
    file: str
    line: int
    target: str
    deferred: bool = False


def owner(name: str) -> str:
    """Name the distribution a dotted module belongs to.

    Returns:
        `mikemol.<dist>` for the shared namespace, else the top-level name.

    """
    parts = name.split(".")
    if parts[0] == NAMESPACE and len(parts) > 1:
        return f"{NAMESPACE}.{parts[1]}"
    return parts[0]


def source_of(root: Path, path: Path) -> str:
    """Label the source a file belongs to: `<repo>/<dist>`, or the repo when it has no dists.

    Returns:
        the label.

    """
    rel = path.relative_to(root)
    first = rel.parts[0]
    label = root.name
    if len(rel.parts) > 1 and (root / first / "pyproject.toml").is_file():
        label = f"{root.name}/{first}"
    return f"{label}:tests" if "tests" in rel.parts[:-1] else label


def _tree(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    except (OSError, SyntaxError):
        return None


def _imports(path: Path, source: str, rel: str) -> list[Edge]:
    """List the owners a file imports, module-level and deferred apart.

    Returns:
        one edge per owner and reading; the standard library is left out.

    """
    readings = (
        (import_edges.module_level_dotted(str(path)), False),
        (import_edges.deferred_dotted(str(path)), True),
    )
    return [
        Edge("import", source, rel, 0, target, deferred)
        for names, deferred in readings
        for target in sorted({owner(n) for n in names} - sys.stdlib_module_names)
    ]


def _docstrings(tree: ast.Module) -> set[int]:
    """Collect the ids of the string nodes that are a docstring.

    Returns:
        the node ids, so a path-like word in prose is not read as a file the code names.

    """
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, _DEFS):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                found.add(id(first.value))
    return found


def _callee(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return None


def _text(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _executable(call: ast.Call) -> str | None:
    """Name the executable a spawn call runs, when its argv is a literal list.

    Returns:
        the basename of the first element, or the `which` argument; None otherwise.

    """
    name = _callee(call)
    first = call.args[0] if call.args else None
    if name in _SPAWN and isinstance(first, (ast.List, ast.Tuple)) and first.elts:
        head = _text(first.elts[0])
        # ⚑ A LEADING `-` IS A FLAG OF A TOOL THE CALLER NAMED ELSEWHERE (`["-C", repo, ...]`
        # handed to a git runner), not an executable: reading it as one listed `-C` 18 times.
        return None if head is None or head.startswith("-") else PurePosixPath(head).name
    if name == "which" and first is not None:
        return _text(first)
    return None


def _order(edge: Edge) -> tuple[int, str, str]:
    return edge.line, edge.kind, edge.target


def _literals(tree: ast.Module, source: str, rel: str) -> list[Edge]:
    """List the subprocess and path edges a file declares.

    Returns:
        the edges, in line order.

    """
    docs = _docstrings(tree)
    found: list[Edge] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            exe = _executable(node)
            if exe is not None:
                found.append(Edge("subprocess", source, rel, node.lineno, exe))
        elif isinstance(node, ast.Constant) and id(node) not in docs:
            text = _text(node)
            if text is not None and _PATH.match(text):
                found.append(Edge("path", source, rel, node.lineno, text))
    return sorted(found, key=_order)


def _mentions(path: Path, word: str, source: str, rel: str) -> list[Edge]:
    """List the comments and strings of a file that name `word`.

    Returns:
        one edge per such token, in line order; none when the file cannot be tokenized.

    """
    pattern = re.compile(re.escape(word), re.IGNORECASE)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (OSError, tokenize.TokenError, SyntaxError):
        return []
    return [
        Edge("mention", source, rel, tok.start[0], word.lower())
        for tok in tokens
        if tok.type in {tokenize.COMMENT, tokenize.STRING} and pattern.search(tok.string)
    ]


def derive(roots: Sequence[Path], mention: str | None = None) -> list[Edge]:
    """Derive every edge of every Python file under each repo root.

    ⚑ NO LINK IS READ: a symlinked file is skipped (operator 2026-10-02).

    Returns:
        the edges, grouped by root in the order given.

    """
    found: list[Edge] = []
    for root in roots:
        for name in corpus.py_files(str(root), root=root):
            path = Path(name)
            if path.is_symlink():
                continue
            source, rel = source_of(root, path), str(path.relative_to(root))
            found += _imports(path, source, rel)
            tree = _tree(path)
            if tree is not None:
                found += _literals(tree, source, rel)
            if mention is not None:
                found += _mentions(path, mention, source, rel)
    return found


def aggregate(edges: Sequence[Edge]) -> list[str]:
    """Count the edges by kind, source and target.

    Returns:
        `COUNT<TAB>kind<TAB>source<TAB>target` rows, an import row ending in `<TAB>deferred` when
        no occurrence is module-level; sorted.

    """
    counts: dict[tuple[str, str, str], int] = {}
    eager: dict[tuple[str, str, str], bool] = {}
    for e in edges:
        key = (e.kind, e.source, e.target)
        counts[key] = counts.get(key, 0) + 1
        eager[key] = eager.get(key, False) or not e.deferred
    rows: list[str] = []
    for key in sorted(counts):
        suffix = _DEFERRED if key[0] == "import" and not eager[key] else ""
        rows.append(f"{counts[key]}\t{key[0]}\t{key[1]}\t{key[2]}{suffix}")
    return rows


def occurrences(edges: Sequence[Edge]) -> list[str]:
    """Render one row per occurrence.

    Returns:
        `kind<TAB>source<TAB>file:line<TAB>target` rows, `<TAB>deferred` on a deferred import.

    """
    return [
        f"{e.kind}\t{e.source}\t{e.file}:{e.line}\t{e.target}{_DEFERRED if e.deferred else ''}"
        for e in edges
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Print a dependency map.

    Returns:
        0, or EXIT_USAGE for a usage refusal or a root that is not a directory.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    rows = "--rows" in args
    args = [a for a in args if a != "--rows"]
    mention: str | None = None
    if "--mention" in args:
        at = args.index("--mention")
        if at + 1 >= len(args):
            sys.stderr.write(_USAGE)
            return EXIT_USAGE
        mention = args[at + 1]
        del args[at : at + 2]
    roots = [Path(a).absolute() for a in args]
    if not roots or not all(r.is_dir() for r in roots):
        sys.stderr.write(_USAGE)
        return EXIT_USAGE
    edges = derive(roots, mention)
    lines = occurrences(edges) if rows else aggregate(edges)
    sys.stdout.write(_BLIND + "".join(f"{row}\n" for row in lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
