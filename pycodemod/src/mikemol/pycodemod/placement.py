# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""WHEN a mutation guard fires on a bare invocation, not where it is written.

Cleanroomed from substrate's `scratch/_pycodemod_placement.py` (`placement`, `_verdict_for`,
`_called_unconditionally`, `_entry_span`, `_dispatch_conds`; W43). A census by source position
scores a guard at entry and a guard consulted only at the first pending write identically; the
second never refuses a read-only mode or a restoring dry run. Per file, the strongest verdict:

    entry        an entry form reached with no dispatch condition on a bare invocation
    dispatched   an entry form under a dispatch condition: written, not fired
    first-write  a first-write form (`_snapshot_once`): consulted only once a write is pending

A file calling no recognised form is absent from the result, not `unguarded`: the population is
the caller's, and absence is theirs to read against it.

⚑⚑ WHAT THIS CANNOT DECIDE is `UNDECIDABLE`, returned with every result, never only documented.

What moved and what did not:

⚑⚑⚑ THE ENTRY BLOCK IS THE `if` WHOSE TEST IS `__name__ == "__main__"`, READ FROM THE SCAN'S OWN
CONDITIONS. The origin recovered it from text by indentation: its span ended at the first line not
indented past the `if`, so a comment at column 0 inside the block cut the span short and every
later guard read `dispatched`. The scan already records each call's `if` tests; the entry test is
one of them, and the rest are dispatch conditions. Either operand order and either quote match.

⚑⚑ ONE HOP FOLLOWS THE CALLER'S SCOPE, NOT ITS LINE. A guard inside a def is `entry` only when that
def is called from the entry block, at module scope, under no dispatch condition. The origin
matched a call by line range, so a call from a helper defined INSIDE the block counted, though
defining a function runs none of it. A method's scope is qualified (`Tool.main`); its own name is
what the entry block calls.

⚑⚑ A SCRIPT WITH NO `__main__` BLOCK RUNS ITS MODULE SCOPE AT ENTRY, FOR THE ONE-HOP CASE TOO. The
origin applied that rule to a guard called at module scope but not to a def called there, which
its one-hop check refused for want of a span: `def main(): require_at_entry(); main()` read
`dispatched`.

⚑ A FILE THE SCAN COULD NOT READ is returned in `skipped`. The origin read each file a second time
for its span and dropped one that failed.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import MODULE, Skip, scan

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.sites import CallFacts, Sites, Text

ENTRY_FORMS = ("require_at_entry", "require_explicit_mutation")
FIRST_WRITE_FORMS = ("_snapshot_once",)
ENTRY = "entry"
DISPATCHED = "dispatched"
FIRST_WRITE = "first-write"
_RANK = {ENTRY: 3, DISPATCHED: 2, FIRST_WRITE: 1}
_MAIN_NAME = "__name__"
_MAIN_VALUE = "__main__"

UNDECIDABLE = (
    (
        "a guard reached through a helper TWO hops deep: this follows one, a def called from the "
        "entry block of its own file"
    ),
    "a guard behind a runtime-computed condition: conditions are source text, never evaluated",
    "a guard reached only through an import side effect or a decorator-registered path",
    "whether a tool that never writes needs a guard: this reports placement, never necessity",
)


@dataclass(frozen=True, slots=True, order=True)
class Placement:
    """One file's strongest verdict, and the form and line that earned it."""

    path: str
    verdict: str
    form: str
    line: int


@dataclass(frozen=True, slots=True)
class Placements:
    """Each guarded file's verdict, the files that could not be read, and what cannot be decided."""

    rows: list[Placement] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)
    undecidable: tuple[str, ...] = UNDECIDABLE


def _is_main_operand(node: ast.expr, want: str) -> bool:
    if want == _MAIN_NAME:
        return isinstance(node, ast.Name) and node.id == _MAIN_NAME
    return isinstance(node, ast.Constant) and node.value == _MAIN_VALUE


def is_entry_test(cond: Text) -> bool:
    """Say whether an `if` test is the module's entry point, `__name__ == "__main__"`.

    Returns:
        True for that comparison in either operand order; False for anything else.

    """
    if not isinstance(cond, str):
        return False
    try:
        tree = ast.parse(cond, mode="eval").body
    except SyntaxError:
        return False
    if not (isinstance(tree, ast.Compare) and len(tree.ops) == 1):
        return False
    if not isinstance(tree.ops[0], ast.Eq):
        return False
    left, right = tree.left, tree.comparators[0]
    return (_is_main_operand(left, _MAIN_NAME) and _is_main_operand(right, _MAIN_VALUE)) or (
        _is_main_operand(left, _MAIN_VALUE) and _is_main_operand(right, _MAIN_NAME)
    )


def _dispatch(conds: tuple[Text, ...]) -> list[Text]:
    """Keep the conditions that make a call conditional: every test but the entry test.

    Returns:
        the dispatch conditions.

    """
    return [c for c in conds if not is_entry_test(c)]


def _has_entry_block(path: str) -> bool | None:
    """Say whether a file has an `if __name__ == "__main__"` block; None when it cannot be read.

    Returns:
        True, False, or None for an unreadable or unparseable file.

    """
    try:
        tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None
    return any(isinstance(n, ast.If) and is_entry_test(ast.unparse(n.test)) for n in tree.body)


def _at_entry(facts: CallFacts, *, has_block: bool) -> bool:
    """Say whether a call runs on a bare invocation.

    Returns:
        True at module scope under no dispatch condition, inside the entry block when there is one.

    """
    if facts.context != MODULE or _dispatch(facts.conds):
        return False
    return not has_block or any(is_entry_test(c) for c in facts.conds)


def called_at_entry(path: str, fname: str, *, has_block: bool) -> bool:
    """Say whether `fname` is called at entry in its own file (the one hop).

    Returns:
        True when some call of `fname` in `path` runs on a bare invocation.

    """
    return any(_at_entry(f, has_block=has_block) for f in scan([path], fname).facts.values())


def _verdict(facts: CallFacts, path: str, *, first_write: bool, has_block: bool) -> str:
    if first_write:
        return FIRST_WRITE
    if _dispatch(facts.conds):
        return DISPATCHED
    if facts.context != MODULE:
        caller = facts.context.rsplit(".", 1)[-1]
        return ENTRY if called_at_entry(path, caller, has_block=has_block) else DISPATCHED
    return ENTRY if _at_entry(facts, has_block=has_block) else DISPATCHED


def _collect(sites: Sites, form: str, best: dict[str, Placement], *, first_write: bool) -> None:
    for key, facts in sites.facts.items():
        path, line = key[0], key[1]
        has_block = _has_entry_block(path)
        if has_block is None:
            continue
        verdict = _verdict(facts, path, first_write=first_write, has_block=has_block)
        found = Placement(path, verdict, form, line)
        prev = best.get(path)
        if prev is None or _RANK[found.verdict] > _RANK[prev.verdict]:
            best[path] = found


def placement(
    paths: Sequence[str],
    forms: Sequence[str] = ENTRY_FORMS,
    first_write_forms: Sequence[str] = FIRST_WRITE_FORMS,
) -> Placements:
    """Return, per file, WHEN its mutation guard fires: entry, dispatched or first-write.

    ⚑ PER FILE, NOT PER CALL: a tool calls the entry form once and the first-write form at every
    write, and the strongest verdict is the one it earned.

    Returns:
        each guarded file's verdict and witness, with the skipped files and the undecidable set.

    """
    best: dict[str, Placement] = {}
    skipped: set[Skip] = set()
    for form in (*forms, *first_write_forms):
        sites = scan(paths, form)
        skipped.update(sites.skipped)
        _collect(sites, form, best, first_write=form in first_write_forms)
    return Placements(rows=sorted(best.values()), skipped=sorted(skipped))
