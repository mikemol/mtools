# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Could a BARE invocation of this tool write a real file? Asked before a sweep runs it.

Cleanroomed from substrate's `scratch/_pycodemod_census.py` (`writes_by_default`; W43). A
diagnostic that runs a tool once per mode multiplies one accidental write by the number of modes.
A write is INERT when its target is a tempfile, when it sits in a fixture function the caller
names, or when the file gates on a flag the caller names. Anything else writes on a bare run.

⚑⚑ DELIBERATELY CONSERVATIVE: it answers "could a bare run write". A write behind a runtime
condition this cannot see reads as a write, and a mode that is not a string literal reads as a
write: a false "yes" costs one skipped mode, a false "no" an unintended write.

⚑ THE WRITE CALLS SEEN: `open(...)` (also `x.open(...)`) with a mode containing w, a, x or +, and
`.write_text(...)` / `.write_bytes(...)`. A copy or rename through `shutil` or `os` is not seen:
that limit is stated, not hidden.

What moved and what did not:

⚑⚑⚑ WRITES ARE READ FROM THE TREE, NOT FROM LINES. The origin matched `open\([^)]*["'][wa]` per
line. MEASURED 2026-09-26 on the origin: `open(os.path.join("x", "y"), "w")` read "no write call",
because `[^)]*` stops at the `)` of `join` (a `join("a", ...)` matched only by accident, on the
quote before the `a`); and `Path("out.txt").write_text(...)` read "no write call". Both write.

⚑⚑ THE GATE IS A FLAG IN CODE, NOT ANYWHERE IN THE FILE. The origin treated any quoted `--apply` in
the source as a gate; measured, a docstring saying other tools take "--apply" made a file that
writes unconditionally read "gated". A gate flag now counts only as a string constant outside
docstrings. The flag and the fixture-function names are operands (the origin's `--apply` and
`_selftest` are one repo's conventions).

⚑ A TEMPFILE TARGET IS RESOLVED THROUGH ITS BINDING, as in the origin: `tf = mkdtemp()` then
`open(tf, "w")` is inert.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import Skip

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

_WRITE_MODES = frozenset("wax+")
_WRITE_METHODS = frozenset({"write_text", "write_bytes"})
_TEMP_CALLS = frozenset({"mkdtemp", "mkstemp", "NamedTemporaryFile", "TemporaryDirectory"})
_TEMP_MODULE = "tempfile"
_OPEN = "open"
_MODE = "mode"


@dataclass(frozen=True, slots=True, order=True)
class WriteVerdict:
    """One file's answer: whether a bare run could write, why, and the first live write's line."""

    path: str
    writes: bool
    why: str
    line: int


@dataclass(frozen=True, slots=True)
class WriteVerdicts:
    """One verdict per readable file, and the files that could not be read."""

    rows: list[WriteVerdict] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _callee(call: ast.Call) -> str:
    f = call.func
    if isinstance(f, ast.Attribute):
        return f.attr
    return f.id if isinstance(f, ast.Name) else ""


def _is_temp(expr: ast.AST, temp_names: set[str]) -> bool:
    for n in ast.walk(expr):
        if isinstance(n, ast.Name) and (n.id in temp_names or n.id == _TEMP_MODULE):
            return True
        if isinstance(n, ast.Call) and _callee(n) in _TEMP_CALLS:
            return True
    return False


def _temp_names(tree: ast.Module) -> set[str]:
    """Return the names bound to a tempfile expression anywhere in the module.

    Returns:
        the names; a fixpoint, so a name bound from another temp name counts.

    """
    names: set[str] = set()
    changed = True
    while changed:
        changed = False
        for n in ast.walk(tree):
            if not isinstance(n, ast.Assign) or not _is_temp(n.value, names):
                continue
            for t in n.targets:
                for leaf in ast.walk(t):
                    if isinstance(leaf, ast.Name) and leaf.id not in names:
                        names.add(leaf.id)
                        changed = True
    return names


def _open_mode(call: ast.Call) -> str | None:
    """Return an `open` call's mode literal; `r` when omitted; None when not a string literal.

    Returns:
        the mode, or None.

    """
    mode: ast.expr | None = call.args[1] if len(call.args) > 1 else None
    for kw in call.keywords:
        if kw.arg == _MODE:
            mode = kw.value
    if mode is None:
        return "r"
    return mode.value if isinstance(mode, ast.Constant) and isinstance(mode.value, str) else None


def _target(call: ast.Call) -> ast.AST | None:
    """Return what a write call writes to: `open`'s first argument, or a method's receiver.

    Returns:
        the target expression.

    """
    if isinstance(call.func, ast.Attribute) and call.func.attr in _WRITE_METHODS:
        return call.func.value
    return call.args[0] if call.args else None


def _is_write(call: ast.Call) -> bool:
    name = _callee(call)
    if isinstance(call.func, ast.Attribute) and name in _WRITE_METHODS:
        return True
    if name != _OPEN:
        return False
    mode = _open_mode(call)
    return mode is None or bool(_WRITE_MODES & set(mode))


def _docstrings(tree: ast.Module) -> set[int]:
    out: set[int] = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = n.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                out.add(id(body[0].value))
    return out


def _gated(tree: ast.Module, gates: frozenset[str]) -> str | None:
    skip = _docstrings(tree)
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and id(n) not in skip and n.value in gates:
            return str(n.value)
    return None


def _fixture_calls(tree: ast.Module, fixtures: frozenset[str]) -> set[int]:
    out: set[int] = set()
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name in fixtures:
            out.update(id(n) for n in ast.walk(fn) if isinstance(n, ast.Call))
    return out


def _position(call: ast.Call) -> tuple[int, int]:
    return call.lineno, call.col_offset


def _verdict(
    path: str, tree: ast.Module, fixtures: frozenset[str], gates: frozenset[str]
) -> WriteVerdict:
    writes = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and _is_write(n)]
    writes.sort(key=_position)
    if not writes:
        return WriteVerdict(path, writes=False, why="no write call", line=0)
    temps = _temp_names(tree)
    inert = _fixture_calls(tree, fixtures)
    live = [
        w
        for w in writes
        if id(w) not in inert and not ((t := _target(w)) is not None and _is_temp(t, temps))
    ]
    if not live:
        return WriteVerdict(path, writes=False, why="writes only fixtures or tempfiles", line=0)
    first = live[0].lineno
    gate = _gated(tree, gates)
    if gate is not None:
        return WriteVerdict(path, writes=False, why=f"gated on {gate}", line=first)
    return WriteVerdict(path, writes=True, why=f"unguarded write at line {first}", line=first)


def _parse(path: str) -> ast.Module | Skip:
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def writes_by_default(
    paths: Sequence[str], fixtures: Iterable[str] = (), gates: Iterable[str] = ()
) -> WriteVerdicts:
    """Return, per file, whether a bare run could write a real file, and why.

    Returns:
        one verdict per readable file, with the skipped files.

    """
    fixture_names, gate_flags = frozenset(fixtures), frozenset(gates)
    out = WriteVerdicts()
    for path in paths:
        tree = _parse(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        out.rows.append(_verdict(path, tree, fixture_names, gate_flags))
    out.rows.sort()
    return out
