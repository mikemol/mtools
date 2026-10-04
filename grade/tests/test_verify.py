# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `verify_hop`: one hop of the clamp recomputed from its own data alone."""

from __future__ import annotations

from mikemol.grade import grade


def _hop(
    rung: str,
    effective: str | None,
    delegates_to: dict[str, grade.Json] | None = None,
) -> grade.Record:
    """Build a recorded hop: its self grade, the effective grade it claims, any delegation.

    Returns:
        The record.

    """
    rec: grade.Record = {"key": "k", "grade": rung}
    if effective is not None:
        rec["effective_grade"] = effective
    if delegates_to is not None:
        rec["delegates_to"] = delegates_to
    return rec


_EDGE: dict[str, grade.Json] = {"owner": "o", "claim": "c"}


def test_a_hop_with_no_premises_is_its_own_grade() -> None:
    """The base case: effective equals self."""
    assert grade.verify_hop(_hop("vacuous", "vacuous"), {}) == (True, "vacuous", "self")


def test_a_hop_is_pinned_by_its_weakest_premise() -> None:
    """The hop recomputes to the lowest premise and names it."""
    record = _hop("behavioral", "vacuous")
    premises = {"p": "existence", "q": "vacuous"}
    assert grade.verify_hop(record, premises) == (True, "vacuous", "q")


def test_a_stronger_premise_does_not_pin_the_hop() -> None:
    """A premise above the self grade leaves the hop on itself."""
    assert grade.verify_hop(_hop("vacuous", "vacuous"), {"p": "behavioral"}) == (
        True,
        "vacuous",
        "self",
    )


def test_a_forged_hop_is_refuted_with_the_recomputed_grade() -> None:
    """A record claiming more than its premises allow fails, saying what it recomputes to."""
    forged = _hop("behavioral", "behavioral")
    assert grade.verify_hop(forged, {"b": "vacuous"}) == (
        False,
        "vacuous",
        "hop recomputes to vacuous (via b), record says behavioral",
    )


def test_a_hop_missing_its_effective_grade_is_refuted() -> None:
    """No recorded effective grade reads as None and cannot match."""
    assert grade.verify_hop(_hop("existence", None), {}) == (
        False,
        "existence",
        "hop recomputes to existence (via self), record says None",
    )


def test_a_hop_with_an_unknown_self_grade_recomputes_from_rank_zero() -> None:
    """An unrecognised grade ranks as vacuous."""
    assert grade.verify_hop(_hop("mystery", "vacuous"), {}) == (True, "vacuous", "self")


def test_a_delegation_clamps_the_hop_to_the_owners_bare_grade() -> None:
    """A weak owner grade pins the hop and the pin is named owner#claim."""
    record = _hop("imported", "existence", _EDGE)
    owned: dict[tuple[str, str], grade.Json] = {("o", "c"): "existence"}
    assert grade.verify_hop(record, {}, owned) == (True, "existence", "o#c")


def test_a_delegation_reads_the_owners_effective_grade_then_its_grade() -> None:
    """The owner's pair is read by its effective grade, falling back to its grade."""
    record = _hop("imported", "vacuous", _EDGE)
    effective: dict[tuple[str, str], grade.Json] = {
        ("o", "c"): {"grade": "behavioral", "effective_grade": "vacuous"},
    }
    assert grade.verify_hop(record, {}, effective) == (True, "vacuous", "o#c")
    plain = _hop("imported", "indeterminate", _EDGE)
    only_grade: dict[tuple[str, str], grade.Json] = {("o", "c"): {"grade": "indeterminate"}}
    assert grade.verify_hop(plain, {}, only_grade) == (True, "indeterminate", "o#c")


def test_a_delegation_to_a_stronger_owner_or_to_nobody_leaves_the_hop_on_itself() -> None:
    """Held-but-strong, absent and half-named owners all impose nothing."""
    record = _hop("existence", "existence", _EDGE)
    strong: dict[tuple[str, str], grade.Json] = {("o", "c"): "imported"}
    assert grade.verify_hop(record, {}, strong) == (True, "existence", "self")
    assert grade.verify_hop(record, {}) == (True, "existence", "self")
    half = _hop("existence", "existence", {"owner": "o"})
    assert grade.verify_hop(half, {}, strong) == (True, "existence", "self")


def test_a_premise_pins_a_hop_past_its_delegation() -> None:
    """The lowest of owner and premises wins, and the pin names the one that won."""
    record = _hop("imported", "vacuous", _EDGE)
    owned: dict[tuple[str, str], grade.Json] = {("o", "c"): "existence"}
    assert grade.verify_hop(record, {"p": "vacuous"}, owned) == (True, "vacuous", "p")
