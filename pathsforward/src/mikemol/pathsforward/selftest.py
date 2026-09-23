# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The installed tool's own witness: arms an adopter can run without the test suite.

⚑ summit's hash arms (a heartbeat change does not move the hash; a waypoint change does), with
the transition rule, the check's sight of a vanished symbol, and the payload's refusal beside
them. Every arm is in memory; the selftest touches no file.
"""

from __future__ import annotations

from pathlib import Path

from mikemol.pathsforward.check import check
from mikemol.pathsforward.digest import Outcome, legacy_digests, v2, verify
from mikemol.pathsforward.model import State, validate
from mikemol.pathsforward.payload import PayloadOverBudgetError, Request, build

_SMALL_BUDGET = 200
_LEGACY_PREFIX = 16
_ROOT = "/"


def _state(*, heartbeat: str = "t0", status: str = "ready", counter: int = 1) -> State:
    """Build a one-waypoint state.

    Returns:
        the state.

    """
    return validate({
        "counter": counter, "project_root": _ROOT, "heartbeat": heartbeat, "residue": [],
        "waypoints": [{"symbol": "W1", "title": "t", "status": status, "blocked_on": [],
                       "blocked_kind": None, "next_bounded_step": "s", "evidence": "e",
                       "ticks_blocked": 0}],
    })


def _refuses_over_budget() -> bool:
    """Say whether a budget nothing fits is refused rather than overshot.

    Returns:
        True when the payload raised.

    """
    req = Request(_state(), Path(_ROOT), "now", budget=_SMALL_BUDGET)
    try:
        build(req)
    except PayloadOverBudgetError:
        return True
    return False


def arms() -> list[tuple[str, bool]]:
    """Evaluate every arm.

    Returns:
        (label, held) pairs.

    """
    base = _state()
    legacy = legacy_digests(base.waypoints)["C/U"][:_LEGACY_PREFIX]
    return [
        ("a heartbeat change does not move the hash",
         v2(_state(heartbeat="t1").waypoints) == v2(base.waypoints)),
        ("a waypoint change moves the hash",
         v2(_state(status="done").waypoints) != v2(base.waypoints)),
        ("a legacy C/U prefix is a transition",
         verify(base.waypoints, legacy).outcome is Outcome.TRANSITION),
        ("a foreign hash is a divergence",
         verify(base.waypoints, "0" * _LEGACY_PREFIX).outcome is Outcome.DIVERGENCE),
        ("a clean state checks clean", not check(base)),
        ("a vanished symbol is seen", any("W2" in f for f in check(_state(counter=2)))),
        ("an over-budget payload is refused", _refuses_over_budget()),
    ]


def run() -> tuple[int, list[str]]:
    """Run every arm.

    Returns:
        (how many held, the labels of those that did not).

    """
    results = arms()
    return sum(held for _, held in results), [label for label, held in results if not held]
