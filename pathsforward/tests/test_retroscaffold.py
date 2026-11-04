# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A retro scaffold pre-fills G0 and G1 from a verdict row; findings are the reviewer's (W2079)."""

from mikemol.pathsforward import retros, retroscaffold
from mikemol.pathsforward.model import Json

_STEP_ONE = "Write the shape; do not wire the rule yet."
_STEP_TWO = "Measure the late submits."


def _queue() -> Json:
    return {
        "waypoints": [
            {"symbol": "W1", "next_bounded_step": _STEP_ONE},
            {"symbol": "W2", "next_bounded_step": _STEP_TWO},
            {"symbol": "W3", "next_bounded_step": "  "},
        ]
    }


def _event(waypoints: list[str], reason: str = "ratchet refused a new key") -> Json:
    return {
        "event": "verdict",
        "repo": "mtools",
        "verdict": "REFUSED",
        "reason": reason,
        "rc": 1,
        "waypoints": waypoints,
        "stack_key": "1793744571101672962",
    }


def test_a_refused_row_with_two_cards_yields_g0_for_both_and_g1_with_the_reason() -> None:
    """The precommit carries each card's step as the queue held it; the delta carries the reason."""
    made = retroscaffold.scaffold(_event(["W1", "W2"]), _queue())
    assert made["card"] == "W1, W2"
    assert made["precommit"] == f"W1: {_STEP_ONE}; W2: {_STEP_TWO}"
    assert made["delta"] == (
        "verdict REFUSED, rc 1: ratchet refused a new key (gate record 1793744571101672962)"
    )
    assert made["trigger"] == "REFUSED: ratchet refused a new key"


def test_a_card_the_queue_does_not_hold_or_without_a_step_is_said_so() -> None:
    """A missing baseline reads as missing, never as an empty step."""
    made = retroscaffold.scaffold(_event(["W9", "W3"]), _queue())
    assert made["precommit"] == f"W9: {retroscaffold.NOT_IN_QUEUE}; W3: {retroscaffold.NO_STEP}"
    bare = retroscaffold.scaffold(_event(["W1"]), {})
    assert bare["precommit"] == f"W1: {retroscaffold.NOT_IN_QUEUE}"


def test_the_scaffold_has_no_findings_and_no_layer_and_passes_the_retro_check() -> None:
    """The reviewer fills the findings: the scaffold invents none and is accepted as a scaffold."""
    made = retroscaffold.scaffold(_event(["W1", "W2"]), _queue())
    assert made["findings"] == []
    assert "enforcement_layer" not in made
    assert retros.retro_refusals(made) == []


def test_a_row_with_no_reason_names_the_verdict_alone_as_the_trigger() -> None:
    """No reason means no dangling colon."""
    made = retroscaffold.scaffold(_event(["W1"], reason=""), _queue())
    assert made["trigger"] == "REFUSED"
