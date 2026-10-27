# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A ratchet may RISE only with a written, warranted re-baseline in the same change (W2024).

    <repo>/rebaselines.json:   {"rebaselines": [{"ratchet": "stubs/x-allowlist.txt", "old": 1,
        "new": 2, "reason": "upstream-dictated name, operator chose (a)",
        "warrant": "bde02714-1533-475a-b934-d2ce58024a15:104181"}]}

⚑ ONE MECHANISM FOR EVERY RATCHET (github-8f, the operator's "find the common structure",
2026-10-26): a declared ratchet (`ratchets.json`) and a dist's own census (`ratchet-preview.txt`
and the baselines the name classifier finds) are the same ROWS of `fleetcensus.census_repo`, so one
comparison over rows covers both. A value that rose against the tree before the change, with no
entry whose `old` and `new` are exactly that rise, is refused. A fall needs nothing: paydown is
what a ratchet is for.

⚑ AN ENTRY IS A CLAIM WITH A WITNESS, NOT A WAIVER. It names the ratchet, the value it was and the
value it became, the reason, and the operator's record (`<transcript uuid>:<line>`), so a rise is
a declared move that can be audited, never a baseline someone edited. It is refused unless it is
a rise (`new` above `old`) with a reason and a warrant of that shape.

⚑ AN UNREAD VALUE IS NOT A NUMBER: a ratchet that could not be read before or after is skipped
here (the census already says UNREAD).

⚑ A BIRTH AT A NONZERO VALUE IS A RISE FROM NOTHING: a ratchet that is new in this change counts
from zero, so a new baseline file already holding N entries is N units of expansion and needs an
entry with `old` 0 and `new` N; a birth at zero needs nothing (W2024's birth judgement).

⚑ ENTRIES ONLY GROW: an entry the tree before the change declared must still be there, unchanged.
A declaration that can be deleted or edited afterwards would make the rise it excused a baseline
someone edited, which is exactly what an entry exists to prevent.

CONSUMED BY: `mikemol-ratchet rebaselines --repo DIR --before DIR`.
"""

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from mikemol.ratchet import expression, fleetcensus
from mikemol.ratchet.declaration import DeclarationError

NAME = "rebaselines.json"
_WARRANT = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}:[0-9]+$")


class RebaselineError(ValueError):
    """A rebaselines file that exists and cannot be trusted."""


@dataclass(frozen=True)
class Rebaseline:
    """One declared rise: the ratchet, its old and new value, the reason and the record."""

    ratchet: str
    old: int
    new: int
    reason: str
    warrant: str


def _entry(item: object, where: int) -> Rebaseline:
    if not isinstance(item, dict):
        msg = f"{NAME}: rebaseline {where} is not an object"
        raise RebaselineError(msg)
    row = cast("dict[str, object]", item)
    ratchet, reason, warrant = row.get("ratchet"), row.get("reason"), row.get("warrant")
    old, new = row.get("old"), row.get("new")
    if not isinstance(ratchet, str) or not ratchet:
        msg = f"{NAME}: rebaseline {where} names no ratchet"
        raise RebaselineError(msg)
    if not isinstance(old, int) or not isinstance(new, int) or isinstance(old, bool):
        msg = f"{NAME}: rebaseline {where} needs integer old and new"
        raise RebaselineError(msg)
    if new <= old:
        msg = f"{NAME}: rebaseline {where} is not a rise (old {old}, new {new}); a fall needs none"
        raise RebaselineError(msg)
    if not isinstance(reason, str) or not reason.strip():
        msg = f"{NAME}: rebaseline {where} gives no reason"
        raise RebaselineError(msg)
    if not isinstance(warrant, str) or not _WARRANT.match(warrant):
        msg = f"{NAME}: rebaseline {where} warrant must be <transcript uuid>:<line>"
        raise RebaselineError(msg)
    return Rebaseline(ratchet, old, new, reason, warrant)


def read(repo: Path) -> list[Rebaseline]:
    """Read a repository's declared rises.

    Returns:
        the entries in file order; empty when the repository has no file.

    Raises:
        RebaselineError: when the file exists (and is no link) but cannot be trusted.

    """
    file = repo / NAME
    if file.is_symlink() or not file.is_file():
        return []
    try:
        doc: object = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as fault:
        msg = f"{NAME}: cannot be read as JSON: {fault}"
        raise RebaselineError(msg) from fault
    listed = cast("dict[str, object]", doc).get("rebaselines") if isinstance(doc, dict) else None
    if not isinstance(listed, list):
        msg = f"{NAME}: no `rebaselines` list"
        raise RebaselineError(msg)
    items = cast("list[object]", listed)
    return [_entry(item, where) for where, item in enumerate(items, start=1)]


def values(repo: Path) -> dict[str, int | None]:
    """Read every ratchet value of a repository, by the path of its file.

    Returns:
        path to value, None where the file could not be read.

    """
    return {row.ratchet: row.value for row in fleetcensus.census_repo(repo)}


def refusals(
    before: Mapping[str, int | None],
    after: Mapping[str, int | None],
    entries: Sequence[Rebaseline],
) -> list[str]:
    """Name every ratchet that rose without a matching declared re-baseline.

    Returns:
        one line per unexplained rise, in path order; empty when every rise is declared.

    """
    declared = {(e.ratchet, e.old, e.new) for e in entries}
    found: list[str] = []
    for path in sorted(after):
        born = path not in before
        was, now = (0 if born else before[path]), after[path]
        if was is None or now is None or now <= was:
            continue
        if (path, was, now) not in declared:
            moved = f"was born at {now}" if born else f"rose {was} to {now}"
            found.append(
                f"{path}: {moved} with no rebaselines entry "
                f'{{"ratchet": "{path}", "old": {was}, "new": {now}, reason, warrant}}'
            )
    return found


def lost(before: Sequence[Rebaseline], after: Sequence[Rebaseline]) -> list[str]:
    """Name every declared rise the tree before had that the tree after no longer carries.

    Returns:
        one line per entry that was removed or changed, in the order the tree before declared them.

    """
    kept = set(after)
    return [
        f"{e.ratchet}: the entry {e.old} to {e.new} was removed or changed; entries only grow"
        for e in before
        if e not in kept
    ]


def check(repo: Path, before: Path) -> list[str]:
    """Compare a repository's ratchets with the same repository before the change.

    Returns:
        the refusals of `refusals` over the two trees' census rows, judged by the entries in
        `repo`, then each entry the tree before declared that is gone or changed (`lost`); a
        declaration or an expression that cannot be trusted raises as `census_repo` does.

    """
    now_entries = read(repo)
    return [
        *refusals(values(before), values(repo), now_entries),
        *lost(read(before), now_entries),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Run `mikemol-ratchet rebaselines --repo DIR --before DIR`.

    Returns:
        0 when every rise is declared; 1 with each unexplained rise printed, or when a file
        cannot be trusted.

    """
    parser = argparse.ArgumentParser(prog="mikemol-ratchet rebaselines")
    parser.add_argument("--repo", type=Path, required=True, help="the tree with the change")
    parser.add_argument("--before", type=Path, required=True, help="the same tree before it")
    opts: dict[str, object] = vars(parser.parse_args(list(sys.argv[1:] if argv is None else argv)))
    try:
        lines = check(Path(str(opts["repo"])), Path(str(opts["before"])))
    except (DeclarationError, expression.ExpressionError, RebaselineError) as fault:
        sys.stderr.write(f"mikemol-ratchet rebaselines: {fault}\n")
        return 1
    for line in lines:
        sys.stdout.write(f"{line}\n")
    return 1 if lines else 0
