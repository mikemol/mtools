# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The outcome -> column map of the differential line, declared total and checked (W374).

⚑ ONE DECLARED MAP, NOT A PROBE OF THE FAILURE TEXT. Every case is placed on three axes — what
the verdict was, how it stood against the case's `expect`, and its declared disposition — and
`RULES` sends each cell of that product to a column. `problems` checks that every cell lands in
EXACTLY ONE rule and that every rule names a real column; the module refuses to import if not,
so a gap or an overlap is a load error rather than a miscount found later.
"""

from collections.abc import Iterable
from itertools import product

from mikemol.pytestspec.spec import (
    DO_NOT_PORT,
    PORT_FIX,
    UNMEASURED,
    Disposition,
    Expect,
    Verdict,
    rule_id,
)

# The verdict axis. `unevaluated`: opa absent, an eval error, or `--skip-declared`.
ADMITTED = "admitted"
DENIED = "denied"
WITHHELD = "withheld"
UNEVALUATED = "unevaluated"
VERDICTS = (ADMITTED, DENIED, WITHHELD, UNEVALUATED)

# The expect axis: no `expect`, met, or unmet — split by whether the deny half is wrong.
NO_EXPECT = "none"
MET = "met"
DENY_UNMET = "deny-unmet"
WITHHELD_UNMET = "withheld-unmet"
EXPECTS = (NO_EXPECT, MET, DENY_UNMET, WITHHELD_UNMET)

# The disposition axis.
UNDISPOSED = "none"
DISPOSED = (UNDISPOSED, DO_NOT_PORT, UNMEASURED, PORT_FIX)

# The columns an outcome can land in (the declaration-only columns are counted elsewhere).
REFUSED = "refused"
WITHHELD_EXPECTED = "withheld-expected"
UNMEASURED_COLUMN = "unmeasured"
OUTCOME_COLUMNS = (ADMITTED, DENIED, REFUSED, WITHHELD_EXPECTED, UNMEASURED_COLUMN)

Rule = tuple[frozenset[str], frozenset[str], frozenset[str], str]
Cell = tuple[str, str, str]
Axes = tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]

_EVALUATED = frozenset({ADMITTED, DENIED, WITHHELD})
_RUN_AS_WRITTEN = frozenset({UNDISPOSED, DO_NOT_PORT, PORT_FIX})
_ALL_EXPECTS = frozenset(EXPECTS)

RULES: tuple[Rule, ...] = (
    # Nothing was measured, whatever was expected or declared.
    (frozenset({UNEVALUATED}), _ALL_EXPECTS, frozenset(DISPOSED), UNMEASURED_COLUMN),
    # A declared unmeasured case is xfail(strict): it never reads as anything else.
    (_EVALUATED, _ALL_EXPECTS, frozenset({UNMEASURED}), UNMEASURED_COLUMN),
    (frozenset({ADMITTED}), frozenset({NO_EXPECT, MET}), _RUN_AS_WRITTEN, ADMITTED),
    (frozenset({DENIED}), frozenset({NO_EXPECT}), _RUN_AS_WRITTEN, DENIED),
    (frozenset({WITHHELD}), frozenset({NO_EXPECT}), _RUN_AS_WRITTEN, UNMEASURED_COLUMN),
    (frozenset({DENIED}), frozenset({MET}), _RUN_AS_WRITTEN, REFUSED),
    (frozenset({WITHHELD}), frozenset({MET}), _RUN_AS_WRITTEN, WITHHELD_EXPECTED),
    # An unmet expect is a failure: a wrong deny set is a deny finding, a wrong withheld set
    # alone is a could-not-measure finding.
    (_EVALUATED, frozenset({DENY_UNMET}), _RUN_AS_WRITTEN, DENIED),
    (_EVALUATED, frozenset({WITHHELD_UNMET}), _RUN_AS_WRITTEN, UNMEASURED_COLUMN),
)


def _matches(cell: Cell, rule: Rule) -> bool:
    verdicts, expects, disposed, _ = rule
    verdict, expect, disposition = cell
    return verdict in verdicts and expect in expects and disposition in disposed


def problems(
    rules: Iterable[Rule],
    axes: Axes = (VERDICTS, EXPECTS, DISPOSED),
    columns: Iterable[str] = OUTCOME_COLUMNS,
) -> list[str]:
    """Check that `rules` place every cell of the axes' product in exactly one column.

    Returns:
        one line per unknown column and per cell matched by no rule or by more than one;
        empty when the map is total and functional.

    """
    rules = tuple(rules)
    known = frozenset(columns)
    found = [f"unknown column {rule[3]!r}" for rule in rules if rule[3] not in known]
    for cell in product(axes[0], axes[1], axes[2]):
        hits = [rule[3] for rule in rules if _matches(cell, rule)]
        if len(hits) != 1:
            found.append(f"{cell} lands in {len(hits)} columns: {hits}")
    return found


_PROBLEMS = problems(RULES)
if _PROBLEMS:
    raise RuntimeError("outcome map is not total: " + "; ".join(_PROBLEMS))


def column(verdict: str, expect: str, disposition: str) -> str:
    """Look up the column a classified case lands in.

    Returns:
        the one column the declared map sends this cell to.

    """
    return next(rule[3] for rule in RULES if _matches((verdict, expect, disposition), rule))


def verdict_kind(verdict: Verdict | None) -> str:
    """Classify a verdict; None means it was not evaluated.

    Returns:
        one of VERDICTS; a case both denied and withheld is DENIED (the deny is the finding).

    """
    if verdict is None:
        return UNEVALUATED
    if verdict.deny:
        return DENIED
    return WITHHELD if verdict.withheld else ADMITTED


def expect_kind(verdict: Verdict | None, expect: Expect | None) -> str:
    """Classify how a verdict stood against its case's `expect`.

    Returns:
        one of EXPECTS; an unevaluated verdict against an expect is MET (the verdict axis
        already sends it to unmeasured).

    """
    if expect is None or verdict is None:
        return NO_EXPECT if expect is None else MET
    if frozenset(rule_id(m) for m in verdict.deny) != expect.deny:
        return DENY_UNMET
    if frozenset(rule_id(m) for m in verdict.withheld) != expect.withheld:
        return WITHHELD_UNMET
    return MET


def disposition_kind(disposition: Disposition | None) -> str:
    """Name a case's disposition on the map's axis.

    Returns:
        one of DISPOSED.

    """
    return UNDISPOSED if disposition is None else disposition.kind
