# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A witness FAMILY: one body, N members, each carrying its own name and its own prose.

Moved from substrate's `substrate/witness_family.py` (N-a row 3); its suite is ported to
`tests/test_witness_family.py`.

⚑⚑ THE `_ARMS` CONVENTION AS A DECLARED SHAPE (substrate's operator: *"The Arms convention is
awesome. If we can take that as parameterizable witness families…"*). A suite is a tuple of arms,
each named as a sentence and carrying prose arguing the defect it prevents; this makes that a
TYPE, so a new suite stops re-deriving it and stops hand-summing its case total.

⚑⚑ THE PROSE IS THE POINT: an apex says why a family exists and each member what it establishes,
which is exactly a paperkit claim (prose plus a check that exits 0). A family is a projected
document and a gate at once. This module is the SHAPE only; it runs nothing (`witness_row` owns
what a witness emits, and a runner owns invocation).

⚑⚑ `count` IS DERIVED, NEVER TYPED, and recurses through split members: splitting an arm into
named members cannot move the population, which is what makes a split auditable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


@dataclass(frozen=True)
class Member:
    """One member of a family — a named claim and the prose that argues it.

    ⚑ `name` is a sentence (`a_dangling_target_is_reported`), so a failure states what did not
    hold. ⚑⚑ `premises` makes a positive control structural: naming the control a member rests on
    turns a prose relationship into a checkable edge. ⚑ A member carries either `cases` (several
    unnamed assertions: an unsplit family) or a sub-`family` (the split one), never both.
    """

    name: str
    claim: str
    cases: int = 1
    premises: tuple[str, ...] = ()
    family: Family | None = None

    @property
    def count(self) -> int:
        """Count the assertions this member makes, split or not.

        Returns:
            the sub-family's count when split, else `cases`.

        """
        return self.family.count if self.family is not None else self.cases


@dataclass(frozen=True)
class Family:
    """A parameterized witness: an apex claim, a roster of members, and the subject they share.

    ⚑ The apex is a claim about having the family at all, not a summary of its members; `subject`
    names what it is parameterized over, which is what lets a family grow without an edit.
    """

    key: str
    apex: str
    subject: str
    members: tuple[Member, ...]

    @property
    def count(self) -> int:
        """Total the assertions this family makes, through split members.

        Returns:
            the sum of member counts.

        """
        return sum(m.count for m in self.members)

    @property
    def names(self) -> tuple[str, ...]:
        """List the member names, in roster order.

        Returns:
            the names; the order is the reading order of the projected prose.

        """
        return tuple(m.name for m in self.members)

    def member(self, name: str) -> Member:
        """Look up one member by name.

        Returns:
            the member.

        Raises:
            KeyError: naming the roster, when no member has that name.

        """
        for got in self.members:
            if got.name == name:
                return got
        msg = (
            f"{self.key}: no member named {name!r} — the roster holds "
            f"{', '.join(self.names) or 'nothing'}"
        )
        raise KeyError(msg)

    def dangling_premises(self) -> tuple[tuple[str, str], ...]:
        """Name every premise this family does not hold.

        ⚑⚑ A premise that resolves to nothing reads as protected and is not.

        Returns:
            `(member, premise)` pairs.

        """
        known = set(self.names)
        return tuple((m.name, p) for m in self.members for p in m.premises if p not in known)

    def unsplit(self) -> tuple[tuple[str, int], ...]:
        """Census the members asserting several facts under one name: the split work list.

        ⚑ A census, not a demand: some members genuinely assert one claim through two comparisons.

        Returns:
            `(member, cases)` for each unsplit member with more than one case.

        """
        return tuple((m.name, m.cases) for m in self.members if m.family is None and m.cases > 1)

    def leaves(self) -> tuple[str, ...]:
        """Flatten the family to every leaf member's dotted path.

        Returns:
            the leaf paths, descending through split members: structure in the declaration,
            flatness at the runner.

        """
        out: list[str] = []
        for m in self.members:
            if m.family is None:
                out.append(m.name)
            else:
                out.extend(f"{m.name}.{leaf}" for leaf in m.family.leaves())
        return tuple(out)

    def depth(self) -> int:
        """Measure how many levels of family this one nests.

        Returns:
            1 for a flat family, more for a split one.

        """
        return 1 + max((m.family.depth() for m in self.members if m.family is not None), default=0)

    def unprotected(self) -> tuple[str, ...]:
        """Census the members no other member names as a premise.

        ⚑ Not a defect: most members stand alone; this lets a reader ask which should have a
        control.

        Returns:
            the uncited member names.

        """
        cited = {p for m in self.members for p in m.premises}
        return tuple(name for name in self.names if name not in cited)


def of(key: str, apex: str, subject: str, members: Iterable[Member]) -> Family:
    """Build a family, refusing a duplicate member name or a split member that also counts.

    ⚑ A duplicate name makes `member()` and every premise edge ambiguous; a split member with its
    own `cases` is a second, hand-typed authority on its size.

    Returns:
        the family.

    Raises:
        ValueError: on a duplicate member name, or a member with both a sub-family and cases.

    """
    roster = tuple(members)
    seen: set[str] = set()
    for got in roster:
        if got.name in seen:
            msg = f"{key}: two members named {got.name!r} — a member name must address exactly one"
            raise ValueError(msg)
        seen.add(got.name)
        if got.family is not None and got.cases != 1:
            msg = (
                f"{key}: member {got.name!r} declares both a sub-family and cases="
                f"{got.cases} — a split member's count comes from its members"
            )
            raise ValueError(msg)
    return Family(key=key, apex=apex, subject=subject, members=roster)


def _rows(family: Family, indent: str) -> list[str]:
    """Render one row per member, showing the nesting rather than flattening it.

    Returns:
        the rows.

    """
    out: list[str] = []
    for m in family.members:
        rests = f"  (rests on {', '.join(m.premises)})" if m.premises else ""
        if m.family is None:
            mark = "" if m.cases == 1 else f"  [{m.cases} case(s), UNSPLIT]"
            out.append(f"{indent}{m.name}{rests}{mark}")
        else:
            out.append(f"{indent}{m.name}{rests}  → {m.family.key}")
            out.extend(_rows(m.family, indent + "  "))
    return out


def render(family: Family) -> str:
    """Render the family: the apex, each member with its claim, then what needs acting on.

    Returns:
        the text, with dangling premises and unsplit members surfaced, not listed as inventory.

    """
    head = f"  {len(family.members)} member(s), {family.count} case(s), depth {family.depth()}"
    lines = [f"{family.key}: {family.apex}", f"  parameterized over: {family.subject}", head]
    lines.extend(_rows(family, "    "))
    lines.extend(
        f"  ⚑ DANGLING PREMISE: {member} rests on {premise}, which is not a member"
        for member, premise in family.dangling_premises()
    )
    lines.extend(
        f"  unsplit: {name} asserts {cases} facts under one name"
        for name, cases in family.unsplit()
    )
    return "\n".join(lines) + "\n"


def summarize(families: Sequence[Family]) -> str:
    """Render one line per family: the roster a reader scans before opening one.

    Returns:
        the lines and a total; "no families" for an empty roster, never an empty string.

    """
    if not families:
        return "  no families\n"
    lines = [f"  {f.key:<24} {len(f.members):>3} member(s)  {f.count:>3} case(s)" for f in families]
    total = sum(f.count for f in families)
    lines.append(f"  {len(families)} famil(ies), {total} case(s)")
    return "\n".join(lines) + "\n"
