# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Count a ledger's witnesses BY KIND, printing the kinds nobody uses.

Moved from substrate (N-a row 6).

⚑⚑⚑ THE ZERO ROW IS THE WHOLE CONTRACT. *"No witness uses this kind"* and *"the counter stopped
seeing this kind"* are different facts, and only a printed zero keeps them apart. This census once
printed FIVE zeroes from a classifier that dropped a leading underscore, and was caught only
because five zeroes are absurd — an UNDERCOUNT would have banked. So the rows are a SEAM a suite
can call, not a loop inside a print block.

⚑⚑⚑ THE BEHAVIOURAL KINDS ARE DERIVED FROM THE ORDER, NEVER RESTATED: they are exactly the prefix
before `mode_undocumented`, so a kind added in the right position lands on the right side by
construction. `mode_undocumented` asks whether a mode is DOCUMENTED, which a repair does not
move; `unwitnessed` is always UNRUNNABLE; `standing` never flips.

⚑⚑ THE DEFAULT ORDER IS THE KINDS THIS PACKAGE BUILDS. Substrate's order also declared three kinds
only its own roster builds (`excludes`, `agda_lacks_field`, `agda_grep_count`); those are roster
policy, so a caller with more kinds passes its own order — and the derivation holds for it too.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

# The first kind no code change can flip; everything before it in an order is behavioural.
FIRST_UNFALSIFIABLE = "mode_undocumented"

# ⚑ THE DECLARED KINDS, IN REPORT ORDER: the falsifiable kinds lead.
KIND_ORDER: tuple[str, ...] = (
    "selftest",
    "refuses",
    FIRST_UNFALSIFIABLE,
    "unwitnessed",
    "standing",
)


def behavioural(order: Sequence[str] = KIND_ORDER) -> tuple[str, ...]:
    """Return the kinds a CODE CHANGE can flip: the prefix of `order` before `mode_undocumented`.

    Returns:
        the behavioural kinds.

    Raises:
        ValueError: `order` does not declare `mode_undocumented`, so no cut point exists.

    """
    kinds = tuple(order)
    if FIRST_UNFALSIFIABLE not in kinds:
        msg = f"a kind order must declare {FIRST_UNFALSIFIABLE!r}: it is where behavioural ends"
        raise ValueError(msg)
    return kinds[: kinds.index(FIRST_UNFALSIFIABLE)]


#: The kinds a CODE CHANGE can flip under the default order — derived, never restated.
BEHAVIOURAL: tuple[str, ...] = behavioural()


def rows(
    by_kind: Mapping[str, Sequence[str]], order: Sequence[str] = KIND_ORDER
) -> list[tuple[str, int]]:
    """Return `[(kind, count)]` over EVERY declared kind, then any surplus kind observed.

    ⚑ A DECLARED KIND WITH NO MEMBERS STILL GETS A ROW. A surplus kind — one the grouping produced
    that no declaration names — is appended rather than dropped: an unrecognised kind is a
    finding about the classifier.

    Returns:
        the rows, declared first.

    """
    declared = [(kind, len(by_kind.get(kind, ()))) for kind in order]
    surplus = [(kind, len(members)) for kind, members in by_kind.items() if kind not in order]
    return declared + surplus


def behavioural_total(
    by_kind: Mapping[str, Sequence[str]], order: Sequence[str] = KIND_ORDER
) -> int:
    """Return how many witnesses a code change could flip.

    ⚑ THE FIGURE A LEDGER LEADS WITH: the complement asserts only that a finding is still written.

    Returns:
        the behavioural count.

    """
    return sum(len(by_kind.get(kind, ())) for kind in behavioural(order))


def vacuous_total(by_kind: Mapping[str, Sequence[str]]) -> int:
    """Return how many witnesses no code change can flip — `standing` alone.

    ⚑ `unwitnessed` IS NOT COUNTED HERE: it reports an HONEST GAP on every read, where `standing`
    passes at 0 and looks like a verdict. Folding them would report the honest kind as debt.

    Returns:
        the standing count.

    """
    return len(by_kind.get("standing", ()))
