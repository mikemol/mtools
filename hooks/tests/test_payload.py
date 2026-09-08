# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The cases for `mikemol.hooks.payload` — untrusted input, and the arming switch.

⚑⚑ THE ARMING CASES ARE THE LOAD-BEARING ONES. A hook that reports itself armed while exiting 0
detects every violation and refuses none — it reads as armed in review and off in fact, which is
strictly worse than being visibly disabled. Each state below has its own case, and the unset
state is asserted to be OFF rather than merely not-on.
"""

from __future__ import annotations

import pytest

from mikemol.hooks import payload

# ⚑⚑⚑ THE EMPTY STRING, NAMED, BECAUSE A PREVIEW RULE WANTS THE ASSERTION WEAKENED AND IT MUST
# NOT BE. `compare-to-empty-string` reports `x == ""` as simplifiable to `not x` — and `not x` is
# satisfied by `None`, `0` and `[]`, so the rewrite would keep passing if `text_of` began
# returning any of them. These arms exist to pin the empty STRING specifically.
# ⚑⚑ MEASURED ACROSS FOUR FORMS RATHER THAN CHOSEN. `isinstance(...) and x == ""` still fires —
# the rule reads the equality half regardless of the conjunction. `len(x) == 0` silences it and
# rejects `None` and `0` with a TypeError, but ACCEPTS `[]` and `{}`, which `== ""` rejects: not
# strictly stronger, a different set of false accepts. Comparing to a named constant silences the
# rule and preserves the original predicate EXACTLY, because it IS the original predicate.
_EMPTY = ""


def test_a_mapping_is_rebuilt_with_string_keys() -> None:
    """A record's keys become strings and its values survive."""
    assert payload.as_record({1: "a", "b": 2}) == {"1": "a", "b": 2}


@pytest.mark.parametrize("value", [None, "text", 3, [1, 2], ()])
def test_a_non_mapping_is_an_empty_record(value: object) -> None:
    """⚑ EVERY NON-MAPPING SHAPE, not just None — the payload is untrusted JSON."""
    assert payload.as_record(value) == {}


def test_a_string_reads_as_itself() -> None:
    """Text passes through unchanged."""
    assert payload.text_of("hello") == "hello"


@pytest.mark.parametrize("value", [None, 3, ["a"], {"a": 1}])
def test_a_non_string_reads_as_empty(value: object) -> None:
    """A non-string field yields empty text rather than a repr of the value."""
    assert payload.text_of(value) == _EMPTY


def test_the_own_switch_arms(monkeypatch: pytest.MonkeyPatch) -> None:
    """The hook's own switch set to 1 arms it."""
    monkeypatch.setenv(payload.OWN_SWITCH, "1")
    monkeypatch.delenv(payload.SHARED_SWITCH, raising=False)
    assert payload.armed() is True


def test_the_own_switch_wins_over_the_shared_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """⚑ SET-TO-ZERO IS A DECISION, NOT AN ABSENCE.

    An explicit `0` on the own switch must DISARM even while the shared switch is on — otherwise
    a repo cannot opt one hook out of a fleet-wide arming, and the only way to quiet one is to
    disarm all of them.
    """
    monkeypatch.setenv(payload.OWN_SWITCH, "0")
    monkeypatch.setenv(payload.SHARED_SWITCH, "1")
    assert payload.armed() is False


def test_the_shared_switch_arms_when_the_own_one_is_unset(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """With no own switch, the shared one decides."""
    monkeypatch.delenv(payload.OWN_SWITCH, raising=False)
    monkeypatch.setenv(payload.SHARED_SWITCH, "1")
    assert payload.armed() is True


def test_neither_switch_is_disarmed(monkeypatch: pytest.MonkeyPatch) -> None:
    """⚑ THE DEFAULT IS ADVISORY, ASSERTED RATHER THAN ASSUMED.

    Without this case every arming test above would pass against a function that returned True
    unconditionally — the positive control for the whole arming surface.
    """
    monkeypatch.delenv(payload.OWN_SWITCH, raising=False)
    monkeypatch.delenv(payload.SHARED_SWITCH, raising=False)
    assert payload.armed() is False


@pytest.mark.parametrize("value", ["", "0", "true", "yes", "2"])
def test_only_the_exact_value_arms(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """⚑ `true`/`yes` DO NOT ARM, and that is worth pinning rather than discovering.

    An operator who writes `PYCHECK_HOOK_BLOCK=true` gets an ADVISORY hook. The behaviour is
    deliberate — one spelling, no truthiness table — and a test is the only place a reader learns
    it before an unrefused violation does.
    """
    monkeypatch.setenv(payload.OWN_SWITCH, value)
    monkeypatch.delenv(payload.SHARED_SWITCH, raising=False)
    assert payload.armed() is False
