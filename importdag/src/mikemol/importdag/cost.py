# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Project what landing a card costs from its manifest and the distribution's import graph (W1997).

A card names the files it changes (its manifest). The tests a change must rerun are the tests that
import one of those files, directly or through any chain of imports, or declare they read it, or are
themselves in the manifest: the REVERSE CONE over `graph.json` (W1503), the same query
`mutate_runner.selected_tests` makes for one module. The projection prices that set from a table of
measured CPU seconds per test, and says what it could not price.

⚑ CPU SECONDS, NEVER WALL (luthen W1645; the standing rule against wall-clock bounds): the table's
figures are medians and 90th percentiles of CPU time, and each carries the number of gate runs it
rests on.

⚑ UNKNOWN STAYS UNKNOWN (nemik W1056): a test with no measured figure is listed in `unknown` and
adds nothing to the sums, so a total over an unmeasured set reads as a floor with its gap named, and
is never padded with an invented average. The sample count is carried (`fewest`), not hidden behind
a threshold typed here.

⚑ TWO CARDS TOGETHER COUNT AN OVERLAP ONCE (`together`), and a card after its enabler has landed
pays only for the tests the enabler did not already rerun (`after`). Both work on the sets of
tests, not on prices, so the table is read once.

CONSUMED BY: nemik's rank, as the divisor of salience (github:W50); a command line is a later step.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import cast

Entries = Mapping[str, Mapping[str, list[str]]]


@dataclass(frozen=True, slots=True)
class Measured:
    """One test's measured CPU seconds (median, 90th percentile) and the runs behind them."""

    median_s: float
    p90_s: float
    samples: int


@dataclass(frozen=True, slots=True)
class Price:
    """What a set of tests costs: sums over those measured, and the ones that were not."""

    median_s: float
    p90_s: float
    fewest: int | None
    unknown: tuple[str, ...]


def _section(doc: Mapping[str, object], key: str) -> Entries:
    got = doc.get(key)
    return cast("Entries", got) if isinstance(got, dict) else {}


def affected(doc: Mapping[str, object], manifest: Iterable[str]) -> frozenset[str]:
    """Find the tests a change to the manifest files must rerun.

    ⚑ A FILE THE GRAPH DOES NOT NAME REACHES NOTHING HERE, and the caller must not read that as
    "no test needs it": an unnamed path is returned by `unnamed`, which a caller asks first.

    Returns:
        the dist-relative test paths whose import cone holds a manifest module, that declare a read
        of a manifest file, or that are in the manifest themselves.

    """
    changed = set(manifest)
    modules, tests = _section(doc, "modules"), _section(doc, "tests")
    reaches = set(changed)
    grew = True
    while grew:
        grew = False
        for path, entry in modules.items():
            if path not in reaches and reaches.intersection(entry.get("imports", [])):
                reaches.add(path)
                grew = True
    return frozenset(
        path
        for path, entry in tests.items()
        if path in changed
        or reaches.intersection(entry.get("imports", []))
        or changed.intersection(entry.get("reads", []))
    )


def unnamed(doc: Mapping[str, object], manifest: Iterable[str]) -> tuple[str, ...]:
    """List the manifest paths the graph names neither as a module nor as a test.

    Returns:
        the paths, sorted; a non-empty answer means `affected` is a floor, not the whole set.

    """
    known = set(_section(doc, "modules")) | set(_section(doc, "tests"))
    return tuple(sorted(set(manifest) - known))


def price(tests: Iterable[str], table: Mapping[str, Measured]) -> Price:
    """Add up what the measured tests cost and name those with no measurement.

    Returns:
        the summed medians and 90th percentiles, the smallest sample count among the measured
        tests (None when none was measured), and the unmeasured tests, sorted.

    """
    chosen = sorted(set(tests))
    seen = [table[path] for path in chosen if path in table]
    return Price(
        sum(m.median_s for m in seen),
        sum(m.p90_s for m in seen),
        min((m.samples for m in seen), default=None),
        tuple(path for path in chosen if path not in table),
    )


def neighbour(path: str, table: Mapping[str, Measured]) -> tuple[float, int] | None:
    """Project an unmeasured test from the measured tests that share its name (W1997).

    ⚑ A PROJECTION IS NOT A MEASUREMENT AND IS NEVER ADDED TO ONE: `price` leaves an unmeasured test
    out so its sums are a floor, and this gives the caller a SEPARATE figure to show beside the
    floor, labelled as an estimate with the number of tests it rests on. A test is a neighbour when
    its stem starts with this test's stem cut back one `_` word at a time, never below two words
    (`test_ratchet` is a neighbour of `test_ratchet_pace_held`; `test` alone matches everything and
    says nothing). The nearest cut that has any measured neighbour answers, so a closer sibling is
    never averaged with a distant one.

    Returns:
        the mean of the neighbours' median CPU seconds and how many there were; None when no cut
        with at least two words has a measured neighbour.

    """
    stem = path.rsplit("/", 1)[-1].removesuffix(".py")
    words = stem.split("_")
    for keep in range(len(words) - 1, 1, -1):
        prefix = "_".join(words[:keep])
        near = [
            m
            for p, m in table.items()
            if p != path and (_stem(p) == prefix or _stem(p).startswith(prefix + "_"))
        ]
        if near:
            return sum(m.median_s for m in near) / len(near), len(near)
    return None


def _stem(path: str) -> str:
    return path.rsplit("/", 1)[-1].removesuffix(".py")


def together(first: frozenset[str], second: frozenset[str]) -> frozenset[str]:
    """Join two cards' test sets so a test both reach is priced once.

    Returns:
        the union.

    """
    return first | second


def after(enabler: frozenset[str], card: frozenset[str]) -> frozenset[str]:
    """Take away what the enabler's landing already reran.

    Returns:
        the tests of `card` that `enabler` does not reach.

    """
    return card - enabler
