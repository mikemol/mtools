# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A pinned row admits ONE reviewed change past the paydown pace, byte for byte (W2301, W2310).

The pace guard refuses a stack that lowers none of the ratchets its repository owes. A row is the
narrow exception the design allows: it pins a repository, a card and, for each path, the BLOB the
change must carry, so admission is "this exact change", never "anything in these paths".

⚑ NOTHING HERE FORGIVES A DEBT. A row lets one reviewed change land; no ratchet value is waived, and
a spent row is inert (`stackland` refuses a second `Admission:` trailer for it).

⚑ A ROW IS A LITERAL IN THIS FILE, REVIEWED AS THE CHANGE THAT ADDS IT. There is no generic class
and no repository-side declaration: a repository cannot admit itself, because the table is part of
the pinned guard it runs. `ROWS` is empty until a reviewed change adds one.

⚑ THE JUDGEMENT IS PURE: it reads the stack's waypoints and its FROZEN files (`stacksnap.Frozen`,
path, mode and blob as they were at submit) and nothing else. Queue files ride free, as everywhere
in the guard.

CONSUMED BY: the pace guard (`ratchet_pace`), once wired (W2310's next step), and the landing paths
that write the `Admission:` trailer (W2312).
"""

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from mikemol.hooks import birth_checks
from mikemol.hooks.stacksnap import QUEUE_FILES, Frozen

REPAIR = "repair"
BIRTH = "birth"


@dataclass(frozen=True, slots=True)
class Row:
    """One pinned admission: the repository, the card and the blob of each path it admits.

    A birth row also names the ratchet file it creates, the rise it declares (`old` to `new`)
    and the operator record (`<uuid>:<line>`) the stack's rebaselines entry must cite.
    """

    repo: str
    card: str
    blobs: Mapping[str, str] = field(default_factory=dict)
    review: str = ""
    kind: str = REPAIR
    ratchet: str = ""
    old: int = 0
    new: int = 0
    record: str = ""

    def ident(self) -> str:
        """Name the row as the `Admission:` trailer carries it.

        Returns:
            `<repo>/<card>`, the id `stackland` reads as an exact line.

        """
        return f"{self.repo}/{self.card}"


# Empty: a row is added by a reviewed change to this file, each citing its own review.
ROWS: tuple[Row, ...] = ()


def _frozen_blobs(frozen: Iterable[Frozen]) -> dict[str, str]:
    # The stack's non-queue files by path. A path frozen twice keeps the LAST blob, as the landing
    # does (a later entry's file replaces an earlier one's in the cumulative index).
    return {f.path: f.blob for f in frozen if f.path not in QUEUE_FILES}


def refusal(row: Row, waypoints: Iterable[str], frozen: Iterable[Frozen]) -> str | None:
    """Say why a stack is not the change a row pins, if it is not.

    Returns:
        the reason, naming the card, path or blob that differs; None when every entry's waypoint is
        the row's card and the stack's non-queue files are exactly the pinned paths at the pinned
        blobs.

    """
    if not row.blobs:
        return "the row pins no path, so it admits nothing"
    named = set(waypoints)
    if not named or named != {row.card}:
        return f"the stack's waypoints {sorted(named)} are not only {row.card}"
    held = _frozen_blobs(frozen)
    extra = sorted(set(held) - set(row.blobs))
    if extra:
        return f"the stack carries a path the row does not pin: {extra[0]}"
    missing = sorted(set(row.blobs) - set(held))
    if missing:
        return f"the row pins a path the stack does not carry: {missing[0]}"
    for path in sorted(row.blobs):
        if held[path] != row.blobs[path]:
            return f"{path} is not the pinned blob (the stack holds {held[path] or 'a deletion'})"
    return None


def accident(row: Row, head_paths: Collection[str], rebaselines: str | None) -> str | None:
    """Run the birth row's accident checks (W2309); a repair row has none.

    Args:
        row: the row that matched the stack.
        head_paths: the paths HEAD holds.
        rebaselines: the stack's frozen rebaselines.json text, None when it has none.

    Returns:
        why this birth looks like an accident; None for a repair row and for a birth no
        check refuses.

    """
    if row.kind != BIRTH:
        return None
    return birth_checks.absent_at_head(head_paths, row.ratchet) or birth_checks.warrant_matches(
        rebaselines, row.ratchet, row.old, row.new, row.record
    )


def admitting(
    rows: Sequence[Row], repo: str, waypoints: Iterable[str], frozen: Iterable[Frozen]
) -> Row | None:
    """Find the row that admits this stack, if any.

    Returns:
        the first row for `repo` that `refusal` accepts; None when none does (an unknown card, an
        extra path and a changed byte all read as no row, never as an exception).

    """
    held = list(frozen)
    named = list(waypoints)
    for row in rows:
        if row.repo == repo and refusal(row, named, held) is None:
            return row
    return None
