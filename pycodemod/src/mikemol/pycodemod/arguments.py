# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""What a call's ARGUMENTS say and where it SITS, read off a `Sites` scan.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`guarded`, `forwards`, `asserted`,
`values`, `values_many`, `_value_at`; W43). Every reading reports BOTH sides of its split, so a
bare list of what is missing can never read as the whole population.

What moved and what did not:

⚑⚑ `forwards` HAS A THIRD SIDE. A call passing `**cfg` may carry the keyword, and the origin
reported it as LACKING — migration debt that is not debt. It is now `cannot_tell`, neither side.

⚑⚑ EACH READING TAKES THE `Sites` IT READS, never paths: the scan that produced a fact travels
with it, and `values_many` REFUSES a scan narrowed to one name — it would report every other name
as having no calls, a zero that is a fact about the scan.

⚑ AN ORDINAL IS AN `int`, A KEYWORD IS A `str`. The origin also read a digit string as an ordinal,
so one spelling had two meanings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from mikemol.pycodemod.core import Value
    from mikemol.pycodemod.sites import CallFacts, Sites, Text


@dataclass(frozen=True, slots=True, order=True)
class Where:
    """One call site: its file, line and column."""

    path: str
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class Guarded:
    """Calls under an `if` (with their tests, outermost first) and calls at the top of a scope."""

    under: list[tuple[Where, tuple[Text, ...]]] = field(default_factory=list)
    top: list[Where] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Forwards:
    """Calls that pass the keyword, calls that do not, and calls whose `**` hides the answer."""

    passes: list[Where] = field(default_factory=list)
    lacks: list[Where] = field(default_factory=list)
    cannot_tell: list[Where] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Asserted:
    """Calls passing the keyword as a LITERAL (asserted) or a COMPUTED value (measured)."""

    literal: list[Where] = field(default_factory=list)
    computed: list[Where] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ValueRow:
    """The value a call passes for one argument — or UNKNOWN — and the scope it sits in."""

    where: Where
    value: Value
    context: str


@dataclass(frozen=True, slots=True)
class Values:
    """The rows passing the argument, and the TOTAL calls — the denominator a bare list lacks."""

    rows: list[ValueRow]
    total: int


def calls(sites: Sites, name: str | None = None) -> list[tuple[Where, CallFacts]]:
    """Return the scan's calls in span order, optionally only those of one callee.

    Returns:
        each call's site and facts.

    """
    return [
        (Where(key[0], key[1], key[2]), facts)
        for key, facts in sorted(sites.facts.items())
        if name is None or facts.name == name
    ]


def guarded(sites: Sites) -> Guarded:
    """Split calls by whether they sit under an `if` — source text, never reachability.

    ⚑⚑ THE AXIS THAT HID A GATE: a mutation-intent guard written under `if apply:` runs only once
    intent is already stated. An `else` carries the NEGATED test, never the test itself.

    Returns:
        the calls under a test, and those at the top of their scope.

    """
    out = Guarded()
    for where, facts in calls(sites):
        if facts.conds:
            out.under.append((where, facts.conds))
        else:
            out.top.append(where)
    return out


def forwards(sites: Sites, keyword: str) -> Forwards:
    """Split calls by whether they pass `keyword` — the question a rollout asks of its callers.

    Returns:
        the calls that pass it, lack it, or hide the answer behind `**`.

    """
    out = Forwards()
    for where, facts in calls(sites):
        if keyword in facts.keywords:
            out.passes.append(where)
        elif facts.splat:
            out.cannot_tell.append(where)
        else:
            out.lacks.append(where)
    return out


def asserted(sites: Sites, keyword: str) -> Asserted:
    """Split the calls passing `keyword` by whether its value is a literal or computed.

    ⚑ A LITERAL IS NOT A DEFECT — `size=1` is right for a singular population — so this reports,
    never judges. Calls not passing the keyword are on neither side.

    Returns:
        the literal and computed passers.

    """
    out = Asserted()
    for where, facts in calls(sites):
        shape = facts.shapes.get(keyword)
        if shape == "literal":
            out.literal.append(where)
        elif shape is not None:
            out.computed.append(where)
    return out


def value_at(facts: CallFacts, argument: str | int) -> Value | _Missing:
    """Return what one call passes for a keyword (`str`) or a positional ordinal (`int`).

    Returns:
        the constant, UNKNOWN, or MISSING when the call does not pass that argument.

    """
    if isinstance(argument, int):
        return facts.positions.get(argument, MISSING)
    return facts.constants.get(argument, MISSING)


def _values_of(pairs: list[tuple[Where, CallFacts]], argument: str | int) -> Values:
    rows = [
        ValueRow(where, got, facts.context)
        for where, facts in pairs
        if not isinstance(got := value_at(facts, argument), _Missing)
    ]
    return Values(rows, len(pairs))


def values(sites: Sites, argument: str | int) -> Values:
    """Return the VALUE each call passes for one argument, over the total call count.

    ⚑⚑ IT NEVER GUESSES: an interpolated f-string, a name or a call reads UNKNOWN, a distinct row —
    `reset=flag` rendered as a value would read as clearance to run a DROP.

    Returns:
        the value rows and the total calls.

    """
    return _values_of(calls(sites), argument)


def values_many(sites: Sites, wanted: Mapping[str, str | int]) -> dict[str, Values]:
    """Return `values` for several callees from ONE whole-corpus scan.

    Returns:
        callee to its value rows and total.

    Raises:
        ValueError: when the scan was narrowed to one name.

    """
    if sites.target is not None:
        msg = f"values_many needs an unnarrowed scan; this one read only {sites.target!r}"
        raise ValueError(msg)
    return {name: _values_of(calls(sites, name), arg) for name, arg in wanted.items()}


class _Missing:
    """The argument is not passed at all — distinct from UNKNOWN, and from `None`."""

    __slots__ = ()

    def __repr__(self) -> str:
        """Render as a word.

        Returns:
            "MISSING".

        """
        return "MISSING"


MISSING = _Missing()
