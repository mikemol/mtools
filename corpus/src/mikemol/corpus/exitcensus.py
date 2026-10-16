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

import ast
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

PREFIX = "EXIT_"
EXIT_FOUND = 1
EXIT_USAGE = 2
_USAGE = (
    "usage: python3 -m mikemol.corpus.exitcensus [--all] [--baseline F | --write-baseline F] "
    "TABLE.json ROOT [ROOT ...]\n"
)
_BLIND = "# cannot see: a constant computed at run time, or a status that is not a named EXIT_\n"
_SKIP = frozenset({".git", ".venv", "node_modules", "build", "__pycache__"})

Table = dict[str, tuple[int, str, tuple[str, ...]]]


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

    The JSON is `{"<VERDICT>": {"value": int, "names": [str, ...], "modules": [str, ...]}}`,
    `modules` optional. ⚑ A VERDICT WITH `modules` IS SCOPED: the harness fixes hook entry points'
    exit 2 as BLOCK (Claude Code's hook protocol), so that name is allowed at that value only in
    the listed files (`<dist>/src/...py`, as the baseline keys them), and a violation anywhere else.

    Returns:
        for each allowed name (without the prefix), its verdict's value, word and scope.

    """
    out: Table = {}
    raw = cast("dict[str, dict[str, object]]", doc)
    for verdict, entry in raw.items():
        value = cast("int", entry["value"])
        scope = tuple(cast("list[str]", entry.get("modules", [])))
        for name in cast("list[str]", entry["names"]):
            out[name] = (value, verdict, scope)
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
    value, word, scope = entry
    if scope and path_of(constant) not in scope:
        return Row(constant, "VIOLATION", f"{word} is only for {', '.join(scope)}")
    if constant.value == value:
        return Row(constant, "OK", word)
    return Row(constant, "VIOLATION", f"{word} is {value}")


def census(roots: Sequence[Path], table: Table, everything: bool = False) -> list[Row]:
    """Judge every EXIT_ constant of every `src` tree under the roots.

    ⚑ `everything` IS FOR A ROOT THAT HAS NO `src` DIRECTORY (luthen's `checks/`, 2026-10-15): every
    `.py` under the root counts except a `tests` directory's, and a path is named from the root's
    own name (`checks/apply_set.py`), so a baseline written for it holds in another checkout.

    Returns:
        the rows, in path order.

    """
    rows: list[Row] = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            parts = set(path.parts)
            if _SKIP & parts or ("tests" in parts and everything):
                continue
            if not everything and "src" not in parts:
                continue
            named = str(path.relative_to(root.parent)) if everything else str(path)
            rows.extend(judge(c, table) for c in constants(path.read_text(encoding="utf-8"), named))
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


def path_of(constant: Constant) -> str:
    """Name a constant's file from the directory above `src`, so no checkout root is in it.

    Returns:
        `<dist>/src/...py`.

    """
    parts = Path(constant.path).parts
    at = parts.index("src") - 1 if "src" in parts and parts.index("src") > 0 else 0
    return "/".join(parts[at:])


def key_of(constant: Constant) -> str:
    """Name a constant for the baseline: its file, name and value.

    ⚑ THE ROOT IS NOT PART OF THE KEY, so a baseline written from one checkout holds in another.

    Returns:
        `<dist>/src/...py NAME value`.

    """
    return f"{path_of(constant)} {constant.name} {constant.value}"


def keys_of(rows: Sequence[Row]) -> list[str]:
    """List the baseline keys of the rows that violate the table.

    Returns:
        the keys, sorted.

    """
    return sorted(key_of(r.constant) for r in rows if r.status == "VIOLATION")


def diff(rows: Sequence[Row], baseline: Sequence[str]) -> tuple[list[str], list[str]]:
    """Compare today's violations with the baseline that may only shrink.

    Returns:
        (new, fixed): violations the baseline does not list, and baseline keys that no longer
        violate. Both are failures: a new one is a regression, a fixed one must leave the file.

    """
    today, listed = set(keys_of(rows)), {k for k in baseline if k.strip()}
    return sorted(today - listed), sorted(listed - today)


def _baseline_main(args: list[str], mode: str, rows: Sequence[Row]) -> int:
    """Write or check the baseline named by `args[0]`.

    Returns:
        0 on a write or a match, 1 on a new or a stale-listed violation.

    """
    path = Path(args[0])
    if mode == "--write-baseline":
        path.write_text("".join(f"{k}\n" for k in keys_of(rows)), encoding="utf-8")
        return 0
    listed = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    new, fixed = diff(rows, listed)
    sys.stdout.write("".join(f"NEW {k}\n" for k in new) + "".join(f"FIXED {k}\n" for k in fixed))
    return EXIT_FOUND if new or fixed else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the census.

    Returns:
        0 when nothing violates the table (or, with a baseline, nothing differs from it), 1 when
        something does, 2 for a usage refusal.

    """
    given = list(sys.argv[1:] if argv is None else argv)
    everything = "--all" in given
    args = [a for a in given if a != "--all"]
    modes = ("--baseline", "--write-baseline")
    mode = args.pop(0) if args and args[0] in modes else ""
    keep = [args.pop(0)] if mode and args else []
    if len(args) < EXIT_USAGE or not Path(args[0]).is_file() or (mode and not keep):
        sys.stderr.write(_USAGE)
        return EXIT_USAGE
    doc = cast("object", json.loads(Path(args[0]).read_text(encoding="utf-8")))
    table = table_of(doc)
    rows = census([Path(a) for a in args[1:]], table, everything=everything)
    if mode:
        return _baseline_main(keep, mode, rows)
    sys.stdout.write(render(rows))
    return EXIT_FOUND if any(r.status == "VIOLATION" for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
