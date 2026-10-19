# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""W1516: write the types a run observed into the annotations a file lacks.

    plan(text, {"Class.method": Signature(...)}) -> Planned(text, sites, worklist)

⚑ A PLANNER, NOT A JUDGE: this module turns observed signatures (`observed.py`) into candidate text
and nothing else. `cli_annotate` hands it to the shared judge, which writes a file only where the
house mypy count falls, so a type this module guesses wrong is refused there and never lands.

⚑ ONLY WHAT NEEDS NO IMPORT IS WRITTEN: an observed type spelled with a module (`numpy.ndarray`)
would need an import the planner cannot place, so that parameter or return goes to the worklist,
and a function the run never reached is not listed at all.

⚑ A WRITTEN ANNOTATION IS NEVER REPLACED: a parameter or return that already has one is left alone.
Edits are character offsets into the original text, applied last to first, so nothing else in the
file moves (comments, quoting and layout stay as written).
"""

import ast
import io
import tokenize
from collections.abc import Mapping
from dataclasses import dataclass

from mikemol.pycodemod.observed import Signature

_SELF = frozenset({"self", "cls"})
_NONE = "None"
_OPEN = frozenset({"(", "[", "{"})
_CLOSE = frozenset({")", "]", "}"})
Function = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True, slots=True)
class Planned:
    """The candidate text, how many annotations it wrote, and what was left with why."""

    text: str
    sites: int
    worklist: tuple[tuple[str, str], ...] = ()


def _last_none(name: str) -> tuple[bool, str]:
    return (name == _NONE, name)


def _spelling(seen: set[str]) -> str | None:
    """Spell the observed set as one annotation.

    Returns:
        the annotation, or None when the set is empty or a type in it needs an import.

    """
    if not seen or any("." in name.partition("[")[0] for name in seen):
        return None
    return " | ".join(sorted(seen, key=_last_none))


def _offsets(text: str) -> list[int]:
    starts = [0]
    for line in text.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    return starts


def _at(text: str, starts: list[int], line: int, byte_col: int) -> int:
    """Turn an `ast` (line, UTF-8 byte column) into a character offset.

    Returns:
        the offset into `text`.

    """
    row = text[starts[line - 1] : starts[line]]
    return starts[line - 1] + len(row.encode()[:byte_col].decode())


def _colons(text: str) -> dict[tuple[int, int], int]:
    """Map each `def`'s (line, column) to the character offset of its header's closing colon.

    Returns:
        the offsets by the `def` keyword's position.

    """
    starts = _offsets(text)
    found: dict[tuple[int, int], int] = {}
    depth = 0
    opened: tuple[int, int] | None = None
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.NAME and token.string == "def" and opened is None:
            opened = token.start
            depth = 0
        elif opened is not None and token.type == tokenize.OP:
            depth += token.string in _OPEN
            depth -= token.string in _CLOSE
            if token.string == ":" and depth == 0:
                found[opened] = starts[token.start[0] - 1] + token.start[1]
                opened = None
    return found


def _functions(tree: ast.Module) -> list[tuple[str, Function]]:
    out: list[tuple[str, Function]] = []

    def walk(body: list[ast.stmt], scope: str) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                walk(node.body, f"{scope}{node.name}.")
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                out.append((f"{scope}{node.name}", node))
                walk(node.body, f"{scope}{node.name}.")

    walk(tree.body, "")
    return out


def _params(function: Function) -> list[ast.arg]:
    args = function.args
    return [*args.posonlyargs, *args.args, *args.kwonlyargs]


def plan(text: str, seen: Mapping[str, Signature]) -> Planned:
    """Annotate what `seen` (qualified name to signature, for this file) shows and the file lacks.

    Returns:
        the candidate text, the number of annotations written and the sites left out with why.

    """
    tree = ast.parse(text)
    starts = _offsets(text)
    colons = _colons(text)
    edits: list[tuple[int, str]] = []
    worklist: list[tuple[str, str]] = []
    for qual, function in _functions(tree):
        signature = seen.get(qual)
        if signature is None:
            continue
        for arg in _params(function):
            if arg.annotation is not None or arg.arg in _SELF or arg.arg not in signature.params:
                continue
            spelled = _spelling(signature.params[arg.arg])
            if spelled is None:
                worklist.append((f"{qual}({arg.arg})", "the observed type needs an import"))
                continue
            end = _at(text, starts, arg.end_lineno or arg.lineno, arg.end_col_offset or 0)
            edits.append((end, f": {spelled}"))
        if function.returns is not None:
            continue
        spelled = _spelling(signature.returns)
        colon = colons.get((function.lineno, function.col_offset))
        if spelled is None or colon is None:
            worklist.append((f"{qual}()", "the observed return needs an import"))
            continue
        edits.append((colon, f" -> {spelled}"))
    out = text
    for offset, extra in sorted(edits, reverse=True):
        out = out[:offset] + extra + out[offset:]
    return Planned(out, len(edits), tuple(worklist))
