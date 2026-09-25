# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The UNION census of ambient-cwd dependence: every path a call resolves against cwd.

Cleanroomed from substrate's `scratch/_pycodemod_ambient.py` (W43). A relative-path read is
cwd dependence whatever function spells it, so the predicate is a PROPERTY, not a name: the callee
resolves a path (a declared vocabulary across six families), and the path it is given is not
anchored. Rows are SCOPED (the directory is the caller's question — a feature), REPO (a path
whose first component names a subtree of the tree — the defect class), UNKNOWN (undecidable, a
column and never folded into either side), or MUTATES (`chdir`).

What moved and what did not:

⚑⚑⚑ `getcwd` IS IN THE VOCABULARY. The origin carried a `getcwd` arm — the spelling of the census
this one claims to subsume — but never listed `getcwd` as a callee, so the arm was unreachable and
the "union" dropped exactly the spelling it said it reproduced.

⚑⚑ AN UNDECODABLE FILE IS A SKIP, NOT A CRASH. The origin read strict UTF-8 and caught only
`OSError`; a `UnicodeDecodeError` is a `ValueError`, so one non-UTF-8 file aborted the census.

⚑⚑ THE SUBTREES ARE THE TREE'S OWN. The origin unioned a frozen fallback of substrate's
directory names into every discovery, so in another repository `agda/x` read as REPO. The caller
passes the tree; its top-level directories are the subtrees, and nothing else.

⚑ RESULTS ARE RETURNED, NOT HUNG ON THE FUNCTION: the origin set `ambient.skipped` as an attribute.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# The callee vocabulary by family: the spellings of "resolve a path". Keyed on the UNQUALIFIED
# name, a deliberate over-reach in the safe direction — an alias is what one-spelling censuses miss.
PATH_CALLS: dict[str, tuple[str, ...]] = {
    "os.path": (
        "exists",
        "isfile",
        "isdir",
        "islink",
        "getmtime",
        "getsize",
        "abspath",
        "realpath",
        "relpath",
        "samefile",
        "lexists",
    ),
    "os": (
        "listdir",
        "walk",
        "scandir",
        "stat",
        "lstat",
        "open",
        "remove",
        "unlink",
        "rename",
        "mkdir",
        "makedirs",
        "rmdir",
        "chdir",
    ),
    "cwd": ("getcwd",),
    "builtin": ("open",),
    "pathlib": ("Path",),
    "proc": (
        "run",
        "call",
        "check_call",
        "check_output",
        "Popen",
        "which",
        "copy",
        "copy2",
        "copytree",
        "move",
        "rmtree",
    ),
    "glob": ("glob", "iglob"),
}
_FAMILY = {name: fam for fam, names in PATH_CALLS.items() for name in names}

# Names that ANCHOR a path. Recognised by name — an approximation, declared as one: an anchor
# spelled otherwise reads UNKNOWN, never ambient.
ANCHOR_NAMES = frozenset(
    {
        "ROOT",
        "root",
        "_root",
        "base",
        "basedir",
        "base_dir",
        "HERE",
        "here",
        "REPO",
        "repo",
        "repo_root",
        "prefix",
        "dirname",
        "d",
        "top",
        "topdir",
        "workdir",
        "cwd",
        "tmpdir",
        "tmp",
        "outdir",
        "out_dir",
        "srcdir",
        "dest",
        "destdir",
    }
)
_PATH_KEYWORDS = frozenset({"path", "file", "filename", "dirname", "top", "cwd"})
_ANCHORING_CALLS = frozenset({"abspath", "dirname", "realpath"})
_MODULE = "<module>"
_COMPUTED = "<computed>"

# ⚑⚑ DECLARED, NEVER COMPUTED: a census cannot derive its own blind spots.
KNOWN_MISSES = (
    ("indirection", "a path resolved through a helper one frame away: this is intraprocedural"),
    ("dataflow", "a relative path stored far from its use; only literal and parameter arms"),
    ("alias", "a filesystem function under a rebound name (`ex = os.path.exists`)"),
    ("argv", "a relative path arriving from `sys.argv` or a config file at RUNTIME"),
    ("subprocess-argv", "a relative path after argv[0], and any relative `cwd=` inherited"),
    ("import-time", "`sys.path` manipulation and relative-import resolution"),
    ("non-python", "shell recipes, Makefiles, hook scripts and agent dispatch text"),
)


@dataclass(frozen=True, slots=True, order=True)
class Row:
    """One unanchored filesystem-resolving call: kind, verdict, what it resolves, and where."""

    path: str
    line: int
    kind: str
    verdict: str
    shown: str
    context: str


@dataclass(frozen=True, slots=True, order=True)
class Skip:
    """A file the census could not read, and why."""

    path: str
    why: str
    error: str


@dataclass(frozen=True, slots=True)
class Ambient:
    """The rows, the population they were read from, and the files skipped."""

    rows: list[Row] = field(default_factory=list)
    population: int = 0
    skipped: list[Skip] = field(default_factory=list)


def repo_subtrees(root: Path) -> frozenset[str]:
    """Return the tree's top-level directory names, hidden ones excluded — DISCOVERED.

    Returns:
        the subtree names; empty when the tree cannot be listed.

    """
    try:
        return frozenset(
            e.name for e in root.iterdir() if e.is_dir() and not e.name.startswith(".")
        )
    except OSError:
        return frozenset()


def _first_component(text: str) -> str:
    return text.replace("\\", "/").split("/", 1)[0]


def _str_value(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def callee_name(node: ast.Call) -> str | None:
    """Return a call's unqualified callee name, or None for a call through an expression.

    Returns:
        the name.

    """
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def path_arg(node: ast.Call) -> ast.expr | None:
    """Return the expression a call resolves as a path, or None when it takes none.

    ⚑⚑ A SUBPROCESS ARGV IS A LIST AND ITS HEAD IS THE PATH; the later elements are the declared
    `subprocess-argv` miss, not silently dropped.

    Returns:
        the path expression.

    """
    if node.args:
        first = node.args[0]
        if isinstance(first, (ast.List, ast.Tuple)):
            return first.elts[0] if first.elts else None
        return first
    return next((kw.value for kw in node.keywords if kw.arg in _PATH_KEYWORDS), None)


def _mentions_file(node: ast.AST) -> bool:
    return any(isinstance(n, ast.Name) and n.id == "__file__" for n in ast.walk(node))


def anchored(node: ast.AST) -> bool:
    """Report whether a path expression flows from a recognised ROOT.

    ⚑ A JOIN IS ANCHORED BY ITS FIRST ARGUMENT — the rest are relative by construction. ⚑⚑
    `__file__` is the strongest anchor, bare or under `abspath`/`dirname`/`realpath`.

    Returns:
        whether it is anchored.

    """
    if isinstance(node, ast.Call):
        return _anchored_call(node)
    if _mentions_file(node):
        return True
    if isinstance(node, ast.JoinedStr):
        return _anchored_fstring(node)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return anchored(node.left)
    if isinstance(node, (ast.Name, ast.Attribute)):
        return (node.id if isinstance(node, ast.Name) else node.attr) in ANCHOR_NAMES
    return _absolute(_str_value(node))


def _absolute(text: str | None) -> bool:
    return text is not None and Path(text).is_absolute()


def _anchored_call(node: ast.Call) -> bool:
    name = callee_name(node)
    if name == "join" and node.args:
        return anchored(node.args[0])
    return name in _ANCHORING_CALLS and bool(node.args) and anchored(node.args[0])


def _anchored_fstring(node: ast.JoinedStr) -> bool:
    if not node.values:
        return False
    head = node.values[0]
    if isinstance(head, ast.FormattedValue):
        return anchored(head.value)
    return _absolute(_str_value(head))


def classify(node: ast.AST, params: frozenset[str], subtrees: frozenset[str]) -> tuple[str, str]:
    """Return SCOPED, REPO or UNKNOWN for an UNANCHORED path, with what it resolves.

    ⚑ A path that is the enclosing function's own PARAMETER is the caller's scope; a literal whose
    first component is a subtree is REPO; everything undecided is UNKNOWN, never folded.

    Returns:
        the verdict and the shown text.

    """
    text = _str_value(node)
    if text is not None:
        return ("REPO" if _first_component(text) in subtrees else "UNKNOWN"), text
    if isinstance(node, ast.Call):
        name = callee_name(node)
        if name == "join" and node.args:
            return classify(node.args[0], params, subtrees)
        if name == "getcwd":
            return "SCOPED", "os.getcwd()"
    if isinstance(node, ast.Name):
        return ("SCOPED" if node.id in params else "UNKNOWN"), node.id
    if isinstance(node, (ast.BinOp, ast.JoinedStr)):
        for part in ast.walk(node):
            text = _str_value(part)
            if text is not None and _first_component(text) in subtrees:
                return "REPO", text
    return "UNKNOWN", _COMPUTED


def _params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    args = node.args
    names = {p.arg for p in [*args.posonlyargs, *args.args, *args.kwonlyargs]}
    names.update(p.arg for p in (args.vararg, args.kwarg) if p is not None)
    return names


class _Scan(ast.NodeVisitor):
    """Every unanchored filesystem-resolving call in one tree, with its enclosing scope."""

    def __init__(self, path: str, subtrees: frozenset[str]) -> None:
        self.path = path
        self.subtrees = subtrees
        self.rows: list[Row] = []
        self._context: list[str] = []
        # ⚑ INHERITED, NOT RESET: a nested helper closing over its parent's `root` is anchored.
        self._params: list[frozenset[str]] = [frozenset()]

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._context.append(node.name)
        self._params.append(self._params[-1] | _params(node))
        self.generic_visit(node)
        self._params.pop()
        self._context.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Enter a def: its name scopes the rows, its parameters join the anchors."""
        self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Enter an async def exactly as a def."""
        self._function(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Enter a class: its name scopes the rows."""
        self._context.append(node.name)
        self.generic_visit(node)
        self._context.pop()

    def visit_Call(self, node: ast.Call) -> None:
        """Record a filesystem-resolving call, then keep walking its arguments."""
        name = callee_name(node)
        family = _FAMILY.get(name or "")
        if name is not None and family is not None:
            self._record(node, name, family)
        self.generic_visit(node)

    def _add(self, node: ast.Call, kind: str, verdict: str, shown: str) -> None:
        context = ".".join(self._context) or _MODULE
        self.rows.append(Row(self.path, node.lineno, kind, verdict, shown, context))

    def _record(self, node: ast.Call, name: str, family: str) -> None:
        if name == "getcwd":
            self._add(node, "getcwd", "SCOPED", "os.getcwd()")
            return
        if name == "chdir":
            self._add(node, "chdir", "MUTATES", ast.unparse(node))
            return
        head = path_arg(node)
        if head is None:
            return
        # ⚑⚑⚑ AN EXECUTABLE NAME IS RESOLVED ON `PATH`, NOT CWD: a proc token with no separator is
        # a command, and a subtree sharing its name made the origin's worst REPO rows.
        text = _str_value(head)
        if family == "proc" and text is not None and "/" not in text and "\\" not in text:
            return
        kind = f"{family}:{name}"
        # ⚑⚑ A SECOND, NON-CONSTANT POSITIONAL IS AN EXPLICIT SOURCE: `vfs.listdir(p, head)` is the
        # route OUT of ambient resolution, not an instance of it.
        if len(node.args) > 1 and not isinstance(node.args[1], ast.Constant):
            self._add(node, kind, "SCOPED", ast.unparse(node.args[1]))
            return
        if anchored(head):
            return
        verdict, shown = classify(head, self._params[-1], self.subtrees)
        self._add(node, kind, verdict, shown)


def _read(path: str) -> ast.Module | Skip:
    try:
        src = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    try:
        return ast.parse(src, filename=path)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def ambient(paths: Sequence[str], root: Path) -> Ambient:
    """Census every unanchored filesystem-resolving call in `paths`, against `root`'s subtrees.

    ⚑ THE POPULATION AND ITS SKIPS ARE RETURNED: a silently shrunken population turns "no ambient
    sites" into a fact about the reader.

    Returns:
        the rows, the population size, and the skipped files.

    """
    subtrees = repo_subtrees(root)
    out = Ambient(population=len(paths))
    for path in paths:
        tree = _read(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        scan = _Scan(path, subtrees)
        scan.visit(tree)
        out.rows.extend(scan.rows)
    out.rows.sort()
    return out
