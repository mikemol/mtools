# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The seams every pycodemod query sits on: argv, constants, round-trips, a corpus scope.

Cleanroomed from substrate's `scratch/_pycodemod_core.py` (W43 letter). What moved and what did not:

⚑⚑⚑ NO `ROOT`, AND NO `global ROOT` REBIND. The origin's `corpus` context manager rebound a
module-level `ROOT` so `--archive`/`--in` swapped the tree under every mode at once — a global
mutated under every reader. Here `corpus(path)` YIELDS the tree, and every query takes its tree or
its files as an argument. The corpus WALK itself (which files a tree holds) is not here: it is
`mikemol.corpus`, already ported, and the driver resolves a tree to files through it.

⚑⚑ libcst IS REQUIRED. The origin guarded every CST path with `if cst is None: return []`, so a
missing library read as "nothing found" — one of the four false zeros the W43 letter and this
repo's bisect measured. A missing libcst is now an import error.

⚑ AN UNREADABLE FILE IS REPORTED, NEVER SKIPPED. The origin's `escapes` read with
`errors="replace"` and passed over an `OSError`, so a file it could not read contributed a silent
nothing to the census. Here a reader returns what it could not read beside what it found.
"""

from __future__ import annotations

import ast
import concurrent.futures
import contextlib
import importlib.util
import re
import shutil
import tarfile
import tempfile
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

# The token that ends the flags: everything after it is an operand, however flag-shaped.
END_OF_FLAGS = "--"

# A bounded grouping key: longer source text is clipped and marked, never left unbounded.
SRC_LIMIT = 60
_ELLIPSIS = "…"

# Below this many files a process pool costs more to start than it saves.
POOL_THRESHOLD = 12

# ⚑ EITHER QUOTE: CPython 3.13 names the sequence as '\ ', a later host as "\ ". MEASURED: the
# double-quote-only pattern read every escape as "?" under the bazel interpreter.
_ESCAPE_SEQ = re.compile(r"""["'](\\.)["']""")


def flagged_argv(argv: Sequence[str]) -> list[str]:
    """Return the argv slice in which a `-`-leading token is a FLAG: everything before `--`.

    ⚑⚑ `--` MUST GOVERN FLAG RECOGNITION, NOT ONLY OPERAND COLLECTION: the origin once honoured it
    while collecting operands and ignored it while testing for `--selftest`, so
    `--literal -- --selftest` ran the suite. Every "is this flag present" asks of THIS slice.

    Returns:
        the arguments after the program name and before `--`.

    """
    rest = list(argv[1:])
    return rest[: rest.index(END_OF_FLAGS)] if END_OF_FLAGS in rest else rest


def operand_tail(argv: Sequence[str]) -> list[str]:
    """Return the tokens after `--`: operands, unfiltered, however flag-shaped they look.

    Returns:
        the arguments after `--`, or an empty list when there is none.

    """
    rest = list(argv[1:])
    return rest[rest.index(END_OF_FLAGS) + 1 :] if END_OF_FLAGS in rest else []


@dataclass(frozen=True, slots=True)
class Escape:
    """One string literal whose escape sequence does not exist, so it means something else."""

    path: str
    line: int
    text: str
    seq: str


@dataclass(frozen=True, slots=True)
class Escapes:
    """The invalid escapes found, and the files that could not be read — never one alone.

    ⚑⚑ THE UNREAD LIST IS WHAT MAKES AN EMPTY `found` A FACT: a census whose unread files were
    dropped reports their contents as absent.
    """

    found: list[Escape] = field(default_factory=list)
    unread: list[str] = field(default_factory=list)


def escape_seq(message: str) -> str:
    r"""Return the escape a SyntaxWarning names, such as `\ `, or "?" when it names none.

    Returns:
        the sequence.

    """
    match = _ESCAPE_SEQ.search(message)
    got = match.group(1) if match is not None else None
    return got if isinstance(got, str) else "?"


def escapes(paths: Sequence[str]) -> Escapes:
    r"""Return string literals whose escape sequence does not exist, and the files not read.

    ⚑ AN INVALID ESCAPE IS AN INTENT FAILURE: `"\ "` PARSES and silently means backslash-space, so
    a regex containing one matches a pattern its author did not write. A file that is not UTF-8 or
    will not compile is UNREAD, reported — never decoded into a guess, never silently skipped.

    Returns:
        the invalid escapes found, and the paths that could not be read or compiled.

    """
    out = Escapes()
    for path in paths:
        try:
            src = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            out.unread.append(path)
            continue
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", SyntaxWarning)
            try:
                compile(src, path, "exec")
            except SyntaxError:
                out.unread.append(path)
                continue
        lines = src.splitlines()
        for warned in caught:
            message = str(warned.message)
            if not issubclass(warned.category, SyntaxWarning) or "escape sequence" not in message:
                continue
            line = warned.lineno or 0
            text = lines[line - 1].strip() if 0 < line <= len(lines) else ""
            out.found.append(Escape(path, line, text, escape_seq(message)))
    return out


def package_root(modname: str) -> tuple[str | None, str]:
    """Return where an INSTALLED module's source lives, or (None, why).

    ⚑ IMPORTING IS THE ONLY HONEST RESOLVER: a `site-packages/<name>` guess is wrong for namespace
    packages, editable installs and vendored trees alike. ⚑ A PACKAGE IS ITS DIRECTORY: its search
    locations are asked for BEFORE its `origin`, or a package reads as its one `__init__.py`.

    Returns:
        the source path and its detail, or None and why it could not be found.

    """
    try:
        spec = importlib.util.find_spec(modname)
    except (ImportError, ValueError) as exc:
        return None, f"not importable here: {exc}"
    if spec is None:
        return None, "not importable here: no such module"
    locations = [p for p in (spec.submodule_search_locations or []) if Path(p).is_dir()]
    if locations:
        return locations[0], "; ".join(locations)
    origin = spec.origin
    if origin and origin != "namespace" and Path(origin).is_file():
        return origin, origin
    return None, "importable but has no source on disk (built-in or frozen)"


def roundtrip(path: str) -> tuple[bool, str]:
    """Report whether parse-then-emit reproduces the file BYTE-FOR-BYTE.

    Returns:
        whether it round-trips, and why not when it does not.

    """
    try:
        src = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return False, f"unreadable: {exc}"
    try:
        out = cst.parse_module(src).code
    except cst.ParserSyntaxError as exc:
        return False, f"parse failed: {type(exc).__name__}"
    return (out == src), ("identical" if out == src else "DIFFERS after re-emit")


class _Unknown:
    """The NOT-A-LITERAL marker for `value_of`.

    ⚑ A SENTINEL AND NOT `None`, BECAUSE `None` IS A LITERAL VALUE: `f(reset=None)` asserts a
    constant; `f(reset=flag)` is a value this reader cannot see. It compares by identity only and
    renders as a word no reader can mistake for data.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        """Render as a word, never as data.

        Returns:
            "UNKNOWN".

        """
        return "UNKNOWN"


UNKNOWN = _Unknown()

type Value = int | float | complex | str | bool | _Unknown | None

_NAMED: dict[str, Value] = {"True": True, "False": False, "None": None}


def _unary(op: cst.BaseUnaryOp, inner: Value) -> Value:
    """Apply a unary operator to a known constant, or UNKNOWN when it would not evaluate.

    ⚑ `-"abc"` PARSES AND DOES NOT EVALUATE: it is UNKNOWN, never a guess.

    Returns:
        the value.

    """
    if isinstance(op, cst.Not):
        return UNKNOWN if isinstance(inner, _Unknown) else not inner
    if isinstance(inner, (int, float, complex)):
        if isinstance(op, cst.Minus):
            return -inner
        if isinstance(op, cst.Plus):
            return +inner
        if isinstance(op, cst.BitInvert) and isinstance(inner, int):
            return ~inner
    return UNKNOWN


def _joined(left: Value, right: Value) -> Value:
    """Concatenate two known strings, or UNKNOWN.

    Returns:
        the joined string.

    """
    if isinstance(left, str) and isinstance(right, str):
        return left + right
    return UNKNOWN


def _literal(text: str) -> Value:
    """Evaluate one literal token's source, or UNKNOWN.

    Returns:
        the value.

    """
    try:
        got: object = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return UNKNOWN
    if isinstance(got, (int, float, complex, str, bool)) or got is None:
        return got
    return UNKNOWN


def _fstring(node: cst.FormattedString) -> Value:
    """Return an f-string's text when nothing is interpolated into it, else UNKNOWN.

    Returns:
        the constant text, or UNKNOWN.

    """
    if any(isinstance(p, cst.FormattedStringExpression) for p in node.parts):
        return UNKNOWN
    return "".join(p.value for p in node.parts if isinstance(p, cst.FormattedStringText))


def value_of(node: cst.CSTNode) -> Value:
    """Return the VALUE of a constant expression, or UNKNOWN — never a guess.

    ⚑ THE STEP THAT DECIDES WHETHER A CALL IS DANGEROUS: `reset=True` and `reset=flag` are both
    "a keyword was passed", and only the value says which drops every relation in a tenant. An
    interpolated f-string, a bare name, an attribute, a call or a container is UNKNOWN.

    Returns:
        the constant, or UNKNOWN.

    """
    if isinstance(node, cst.UnaryOperation):
        return _unary(node.operator, value_of(node.expression))
    if isinstance(node, (cst.Integer, cst.Float, cst.Imaginary, cst.SimpleString)):
        return _literal(node.value)
    if isinstance(node, cst.Name):
        return _NAMED.get(node.value, UNKNOWN)
    if isinstance(node, cst.ConcatenatedString):
        return _joined(value_of(node.left), value_of(node.right))
    if isinstance(node, cst.FormattedString):
        return _fstring(node)
    return UNKNOWN


def shape_of(node: cst.CSTNode) -> str:
    """Return "literal" when the argument is a constant expression, else "computed".

    ⚑ DERIVED FROM `value_of`, NOT A SECOND WALK: one classifier, so "literal" MEANS "a value came
    back" and the two can never disagree about what a site is.

    Returns:
        "literal" or "computed".

    """
    return "computed" if isinstance(value_of(node), _Unknown) else "literal"


def src_of(node: cst.CSTNode, limit: int = SRC_LIMIT) -> str | _Unknown:
    """Return the node's SOURCE TEXT, whitespace-collapsed and bounded, or UNKNOWN.

    ⚑ BOUNDED BY CONSTRUCTION, because this text becomes a GROUPING KEY: an unbounded condition
    would mint a singleton bucket per site. Truncation is marked, so a clipped key is never read as
    a complete one.

    Returns:
        the source text, or UNKNOWN when there is none.

    """
    text = " ".join(cst.Module(body=[]).code_for_node(node).split())
    if not text:
        return UNKNOWN
    return text if len(text) <= limit else text[:limit] + _ELLIPSIS


def _safe_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    """Return the archive members that stay inside the extraction directory.

    ⚑ MEMBERS ARE FILTERED, NOT TRUSTED: an absolute or `..` member would write OUTSIDE the temp
    tree — the one way a read-only query could damage the repository it runs from.

    Returns:
        the safe members.

    """
    return [
        m
        for m in archive.getmembers()
        if not Path(m.name).is_absolute() and ".." not in Path(m.name).parts
    ]


@contextlib.contextmanager
def corpus(path: str) -> Iterator[Path]:
    """Yield the tree a query should read: `path` itself, or a temp extraction of an archive.

    ⚑⚑ A SCOPE, NOT A MODE, AND NOW NOT A GLOBAL. The origin rebound a module `ROOT` so every mode
    followed; here the tree is yielded and the caller passes it on. The temp tree is removed by the
    protocol, on the error path too.

    Yields:
        the tree to query.

    """
    if Path(path).is_dir():
        yield Path(path).absolute()
        return
    tmp = Path(tempfile.mkdtemp(prefix="pycodemod-corpus-"))
    try:
        with tarfile.open(path) as archive:
            archive.extractall(tmp, members=_safe_members(archive), filter="data")
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def per_file[T](
    fn: Callable[[str], list[T]], paths: Sequence[str], workers: int | None = None
) -> list[T]:
    """Map `fn` over files — in PROCESSES when it pays, serially when it does not.

    ⚑ THE VEHICLE WAS MEASURED, NOT CHOSEN: per-file CST metadata resolution is pure-Python tree
    walking, where substrate measured 8 threads at 0.73x (slower than serial) and 8 processes at
    3.32x. ⚑ A POOL FAILURE MUST NOT FAIL THE QUERY: a refused spawn falls back to serial, never to
    fewer rows. `fn` must be a module-level callable, since a closure cannot cross processes.

    Returns:
        every row `fn` produced, in file order.

    """
    files = list(paths)
    if len(files) < POOL_THRESHOLD:
        return [row for path in files for row in fn(path)]
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            return [row for rows in pool.map(fn, files, chunksize=4) for row in rows]
    except (OSError, RuntimeError, concurrent.futures.process.BrokenProcessPool):
        return [row for path in files for row in fn(path)]
