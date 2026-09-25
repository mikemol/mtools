# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.ledger.finding_census`: substrate's suite, and the caller's order.

⚑⚑⚑ THE ZERO ROW IS ASSERTED BY ABSENCE FROM THE INPUT. A fixture handing the reader every kind
cannot tell a roster-driven census from one that iterates its input — they agree exactly when
nothing is missing. So the fixture is DELIBERATELY PARTIAL, with one surplus kind.

⚑ THE BEHAVIOURAL KINDS ARE ASSERTED AS A DERIVATION, not a list: pinning members would let two
rosters drift apart.
"""

from __future__ import annotations

import pytest

from mikemol.ledger import finding_census

_SELFTESTS = ("a", "b", "c")
_STANDINGS = ("d", "e")
_UNWITNESSED = ("f",)
_SURPLUS = ("g",)
_SURPLUS_KIND = "a-kind-nobody-declared"

_PARTIAL: dict[str, tuple[str, ...]] = {
    "selftest": _SELFTESTS,
    "standing": _STANDINGS,
    "unwitnessed": _UNWITNESSED,
    _SURPLUS_KIND: _SURPLUS,
}

# Substrate's own order: three roster-only kinds before the cut, as a caller would pass it.
_SUBSTRATE_BEHAVIOURAL: tuple[str, ...] = (
    "selftest",
    "refuses",
    "excludes",
    "agda_lacks_field",
    "agda_grep_count",
)
_SUBSTRATE_ORDER: tuple[str, ...] = (
    *_SUBSTRATE_BEHAVIOURAL,
    "mode_undocumented",
    "unwitnessed",
    "standing",
)


def test_an_absent_declared_kind_gets_a_zero_row() -> None:
    """`refuses` is absent from the input and still reported, at zero: THE LOAD-BEARING ARM."""
    got = dict(finding_census.rows(_PARTIAL))
    assert got.get("refuses") == 0
    assert all(kind in got for kind in finding_census.KIND_ORDER)
    assert got.get("selftest") == len(_SELFTESTS)


def test_a_surplus_kind_is_reported_after_the_declared_rows() -> None:
    """A kind no declaration names is reported, never dropped; the declared rows lead."""
    table = finding_census.rows(_PARTIAL)
    assert dict(table).get(_SURPLUS_KIND) == len(_SURPLUS)
    kinds = [kind for kind, _ in table]
    assert kinds[: len(finding_census.KIND_ORDER)] == list(finding_census.KIND_ORDER)


def test_behavioural_is_the_prefix_before_mode_undocumented() -> None:
    """The behavioural kinds are a PREFIX of the order, cut at `mode_undocumented`."""
    order = finding_census.KIND_ORDER
    kinds = finding_census.BEHAVIOURAL
    assert order[: len(kinds)] == kinds
    assert order[len(kinds)] == finding_census.FIRST_UNFALSIFIABLE
    assert {"selftest", "refuses"} <= set(kinds)
    assert not {"mode_undocumented", "unwitnessed", "standing"} & set(kinds)


def test_a_callers_longer_order_keeps_the_derivation() -> None:
    """Substrate's order, with its roster-only kinds, derives its own behavioural prefix."""
    assert finding_census.behavioural(_SUBSTRATE_ORDER) == _SUBSTRATE_BEHAVIOURAL
    assert dict(finding_census.rows({}, _SUBSTRATE_ORDER)).get("agda_grep_count") == 0


def test_an_order_without_the_cut_point_is_refused() -> None:
    """An order that never declares `mode_undocumented` has no cut, and is refused, not guessed."""
    with pytest.raises(ValueError, match="mode_undocumented"):
        finding_census.behavioural(("selftest", "standing"))


def test_the_two_totals_keep_the_honest_gap_apart() -> None:
    """Behavioural counts flippable witnesses; vacuous counts standing; unwitnessed is neither."""
    behavioural = finding_census.behavioural_total(_PARTIAL)
    vacuous = finding_census.vacuous_total(_PARTIAL)
    assert behavioural == len(_SELFTESTS)
    assert vacuous == len(_STANDINGS)
    only_unwitnessed = {"unwitnessed": ("x", "y")}
    assert finding_census.vacuous_total(only_unwitnessed) == 0
    assert finding_census.behavioural_total(only_unwitnessed) == 0
    total = sum(len(v) for v in _PARTIAL.values())
    assert behavioural + vacuous + len(_UNWITNESSED) + len(_SURPLUS) == total


def test_an_empty_ledger_reports_every_kind_at_zero() -> None:
    """Every declared kind appears at zero, and both totals answer rather than raise."""
    got = dict(finding_census.rows({}))
    assert len(got) == len(finding_census.KIND_ORDER)
    assert all(count == 0 for count in got.values())
    assert finding_census.behavioural_total({}) == 0
    assert finding_census.vacuous_total({}) == 0
