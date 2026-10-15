# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read every `EXIT_<NAME> = <int>` of a tree and judge each against the fleet exit table (W1294).

    python3 -m mikemol.corpus.exitcensus TABLE.json ROOT [ROOT ...]

⚑ THE TABLE IS DATA AND EACH DIST KEEPS ITS OWN CONSTANTS. A shared constants module would be the
first import between fence and pathsforward, which declare no dependencies on purpose; so the
agreement is checked from outside, by reading syntax trees. The table maps a verdict to its one
value and to the names that may carry it (`.claude/design/exit-table.md`, W1291).

⚑ A VIOLATION IS A KNOWN NAME AT ANOTHER VERDICT'S VALUE: `EXIT_REFUSED = 2` where the table says
REFUSE is 3. A name the table does not list is reported apart (`UNKNOWN`), because it is a gap in
the table before it is a defect in the tool. Only module-level assignments of an integer constant
are read; a value computed at run time is not seen (said in the output's first line).

⚑ OUTPUT: one row per constant, `OK|VIOLATION|UNKNOWN path:line NAME value detail`, exit 0 when
there is no VIOLATION, 1 when there is one, 2 for a usage refusal.
"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Sequence

PREFIX = "EXIT_"
EXIT_FOUND = 1
EXIT_USAGE = 2
_USAGE = "usage: python3 -m mikemol.corpus.exitcensus TABLE.json ROOT [ROOT ...]\n"
_BLIND = "# cannot see: a constant computed at run time, or a status that is not a named EXIT_\n"
_SKIP = frozenset({".git", ".venv", "node_modules", "build", "__pycache__"})

type Table = dict[str, tuple[int, str]]


@dataclass(frozen=True)
class Constant:
    """One `EXIT_<NAME> = <int>` found in a file."""

    path: str
    line: int
    name: str
    value: int


@dataclass(frozen=True)
class Row:
    """A constant and the table's judgement of it."""

    constant: Constant
    status: str
    detail: str


def constants(source: str, path: str) -> list[Constant]:
    """Read the module-level EXIT_ integer constants of one source text.

    Returns:
        the constants in file order; an unparseable file yields none.

    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    found: list[Constant] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        if not (isinstance(value, ast.Constant) and type(value.value) is int):
            continue
        found.extend(
            Constant(path, node.lineno, target.id, value.value)
            for target in targets
            if isinstance(target, ast.Name) and target.id.startswith(PREFIX)
        )
    return found


def table_of(doc: object) -> Table:
    """Turn the table's JSON into each allowed name's value and verdict.

    The JSON is `{"<VERDICT>": {"value": int, "names": [str, ...]}}`.

    Returns:
        for each allowed name (without the prefix), its verdict's value and the verdict's word.

    """
    out: Table = {}
    raw = cast("dict[str, dict[str, object]]", doc)
    for verdict, entry in raw.items():
        value = cast("int", entry["value"])
        for name in cast("list[str]", entry["names"]):
            out[name] = (value, verdict)
    return out


def judge(constant: Constant, table: Table) -> Row:
    """Judge one constant against the table.

    Returns:
        OK when the name sits at its verdict's value, VIOLATION when it sits elsewhere, UNKNOWN
        when the table does not list the name.

    """
    entry = table.get(constant.name.removeprefix(PREFIX))
    if entry is None:
        return Row(constant, "UNKNOWN", "the table does not list this name")
    value, word = entry
    if constant.value == value:
        return Row(constant, "OK", word)
    return Row(constant, "VIOLATION", f"{word} is {value}")


def census(roots: Sequence[Path], table: Table) -> list[Row]:
    """Judge every EXIT_ constant of every `src` tree under the roots.

    Returns:
        the rows, in path order.

    """
    rows: list[Row] = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            if _SKIP & set(path.parts) or "src" not in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            rows.extend(judge(c, table) for c in constants(text, str(path)))
    return rows


def render(rows: Sequence[Row]) -> str:
    """Format the rows, the blind-spot line first.

    Returns:
        the report text.

    """
    lines = [_BLIND]
    for row in rows:
        c = row.constant
        lines.append(f"{row.status} {c.path}:{c.line} {c.name} {c.value} {row.detail}\n")
    return "".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the census.

    Returns:
        0 when nothing violates the table, 1 when something does, 2 for a usage refusal.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < EXIT_USAGE or not Path(args[0]).is_file():
        sys.stderr.write(_USAGE)
        return EXIT_USAGE
    doc = cast("object", json.loads(Path(args[0]).read_text(encoding="utf-8")))
    table = table_of(doc)
    rows = census([Path(a) for a in args[1:]], table)
    sys.stdout.write(render(rows))
    return EXIT_FOUND if any(r.status == "VIOLATION" for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
