# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.ledger.finding_restem`: substrate's suite, ported case for case.

⚑⚑⚑ THE TRAILING HYPHEN IS ASSERTED BY CONSEQUENCE rather than by inspecting the pattern: the
fixture carries `aa-F10-…`, which shares the prefix `aa-F1` without the boundary, so a matcher
that drops the hyphen both consumes it and loses the genuine pair.

⚑⚑ THE DOUBLE-COUNT IS ASSERTED AS AN INEQUALITY, not as a number that expires when the
population moves.
"""

from __future__ import annotations

from mikemol.ledger import finding_restem

_WITNESS_ONLY = ["aa-F1", "bb-F2", "cc-F3", "dd-F4"]
_BIB_ONLY = [
    "aa-F1-the-real-descriptive-tail",  # the genuine pair for aa-F1
    "aa-F10-a-completely-different-one",  # the trap: shares the prefix, not the boundary
    "bb-F2-one",  # two candidates for bb-F2 → ambiguous, no pair
    "bb-F2-two",
    "ee-F5-orphan",  # matches nothing
]


def test_a_stem_pairs_with_its_descriptive_spelling_and_not_a_longer_sibling() -> None:
    """`aa-F1` pairs with its tail, and `aa-F10-…` is NOT consumed: THE HYPHEN ARM."""
    pairs, _, bib_only = finding_restem.restem(_WITNESS_ONLY, _BIB_ONLY)
    assert dict(pairs).get("aa-F1") == "aa-F1-the-real-descriptive-tail"
    assert "aa-F10-a-completely-different-one" in bib_only


def test_an_ambiguous_stem_stays_honest() -> None:
    """A stem with two candidates does not pair; it and both candidates stay unpaired."""
    pairs, witness_only, bib_only = finding_restem.restem(_WITNESS_ONLY, _BIB_ONLY)
    assert "bb-F2" not in dict(pairs)
    assert "bb-F2" in witness_only
    assert "bb-F2-one" in bib_only
    assert "bb-F2-two" in bib_only


def test_unmatched_keys_stay_on_their_own_side() -> None:
    """A bib key matching nothing stays bib-only; an unmatched witness stays witness-only."""
    _, witness_only, bib_only = finding_restem.restem(_WITNESS_ONLY, _BIB_ONLY)
    assert "ee-F5-orphan" in bib_only
    assert "cc-F3" in witness_only


def test_a_pair_is_consumed_from_both_sides() -> None:
    """A paired key leaves both remainder lists, or the same finding is reported twice."""
    _, witness_only, bib_only = finding_restem.restem(_WITNESS_ONLY, _BIB_ONLY)
    assert "aa-F1" not in witness_only
    assert "aa-F1-the-real-descriptive-tail" not in bib_only


def test_a_pair_counts_once_and_the_reduction_is_visible() -> None:
    """The raw rows exceed the true drift, by exactly one per pair."""
    split = finding_restem.restem(_WITNESS_ONLY, _BIB_ONLY)
    drift = finding_restem.true_drift(split)
    raw = finding_restem.raw_rows(_WITNESS_ONLY, _BIB_ONLY)
    assert raw > drift
    assert drift == len(split[0]) + len(split[1]) + len(split[2])
    assert raw - drift == len(split[0])


def test_an_empty_read_is_a_fact_about_the_input() -> None:
    """No input yields no pairs, no remainders, and zero drift."""
    assert finding_restem.restem([], []) == ([], [], [])
    assert finding_restem.true_drift(([], [], [])) == 0
