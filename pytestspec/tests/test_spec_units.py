# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Unit witnesses for the spec module's rule ids, mismatch text and dispositions.

W1013. ⚑ A declared defect in each survived the plugin and spec tests: a rule id that kept its
spaces or was cut at the wrong colon, ids reported in set order, withheld messages run together,
an unknown expect key hidden behind another refusal, and a port-fix paired with itself, a stranger
or nothing. Each is driven directly here.
"""

import pytest

from mikemol.pytestspec.spec import (
    Case,
    Disposition,
    Expect,
    SpecDataError,
    Verdict,
    disposition_of,
    expectation,
    judge,
    rule_id,
)

_NAMES = frozenset({"c", "o"})
_IDS = ("A", "B", "C", "D", "E", "F")


def _case(**fields: object) -> Case:
    """Build a case named `c` with the given extra fields.

    Returns:
        the case.

    """
    return {"case": "c", **fields}


def test_a_rule_id_is_the_stripped_token_before_the_first_colon() -> None:
    """Spaces around the id are dropped, and a later colon belongs to the message."""
    assert rule_id("  S0 : a: b") == "S0"
    assert rule_id("bare") == "bare"


def test_an_unknown_expect_key_is_named_beside_a_good_one() -> None:
    """A stray key is refused for being unknown, not hidden behind the ids that were valid."""
    with pytest.raises(SpecDataError, match="unknown keys admit"):
        expectation("c", _case(expect={"deny": ["S0"], "admit": ["S1"]}))


def test_missing_ids_are_listed_in_sorted_order() -> None:
    """Several missing ids read as a sorted list, however the set happens to iterate."""
    failure = judge(Verdict(), Expect(deny=frozenset(_IDS)))
    assert failure == "DENY MISMATCH: missing A, B, C, D, E, F; unexpected none"


def test_unexpected_ids_are_listed_in_sorted_order() -> None:
    """Several unexpected ids read as a sorted list, however the set happens to iterate."""
    denied = Verdict(deny=tuple(f"{i}: x" for i in reversed(_IDS)))
    failure = judge(denied, Expect(withheld=frozenset({"W"})))
    assert failure is not None
    assert failure.startswith("DENY MISMATCH: missing none; unexpected A, B, C, D, E, F")


def test_withheld_messages_are_joined_with_semicolons() -> None:
    """Every withheld reason is kept, separated, in the unmeasured failure."""
    failure = judge(Verdict(withheld=("a", "b")))
    assert failure == "UNMEASURED (withheld, not passed): a; b"


def test_a_case_that_declares_no_disposition_has_none() -> None:
    """The absence of a disposition is None, not a refusal."""
    assert disposition_of("c", _case(), _NAMES) is None


def test_a_disposition_that_is_not_port_fix_carries_no_pair() -> None:
    """Do-not-port and unmeasured keep their reason and have no `pairs_with`."""
    declared = _case(disposition="unmeasured", reason="why")
    assert disposition_of("c", declared, _NAMES) == Disposition("unmeasured", "why")


def test_a_port_fix_keeps_the_case_it_pairs_with() -> None:
    """The origin's pinning case is carried on the disposition."""
    declared = _case(disposition="port-fix", reason="why", pairs_with="o")
    assert disposition_of("c", declared, _NAMES) == Disposition("port-fix", "why", "o")


@pytest.mark.parametrize("pair", ["c", "zzz", None, 5])
def test_a_port_fix_must_pair_with_another_case_of_the_spec(pair: object) -> None:
    """Itself, a case not in the spec, and no string at all are each refused."""
    declared = _case(disposition="port-fix", reason="why", pairs_with=pair)
    with pytest.raises(SpecDataError, match="must name another case"):
        disposition_of("c", declared, _NAMES)


@pytest.mark.parametrize("reason", ["", "  ", None])
def test_a_disposition_needs_a_reason_that_says_something(reason: object) -> None:
    """A missing, empty or blank reason is refused: a declaration must argue itself."""
    declared = _case(disposition="unmeasured", reason=reason)
    with pytest.raises(SpecDataError, match="needs a `reason`"):
        disposition_of("c", declared, _NAMES)


def test_an_unknown_disposition_is_refused() -> None:
    """Only the three kinds exist."""
    with pytest.raises(SpecDataError, match="is not one of"):
        disposition_of("c", _case(disposition="skip", reason="why"), _NAMES)
