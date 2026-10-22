# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A refusal's culprit note says which kind of red each failed check is (W1721).

⚑ NO HISTORY IS NO CLAIM: with no reading of the store the note is exactly what it was before, so
a refusal never asserts NEW (a regression) for want of a record.
"""

from __future__ import annotations

from mikemol.hooks import stackrun

_SUMMARY = (
    "pre-commit: REFUSED — the following check(s) failed:\n"
    "  - corpus: pytest — every case passes\n"
    "  - hooks: mypy\n"
)
_HISTORY = {"corpus: pytest — every case passes": (True, True, True, True, True)}


def test_a_failed_check_is_named_with_its_class_from_the_history() -> None:
    """A step red in every recent round is broken; one the history never saw red is new."""
    note = stackrun.kind_note(_SUMMARY, _HISTORY)
    assert note == "kind: corpus: pytest — every case passes is broken; hooks: mypy is new; "


def test_no_history_or_no_failed_check_says_nothing() -> None:
    """None is no reading, and output with no summary has no check to classify."""
    assert not stackrun.kind_note(_SUMMARY, None)
    assert not stackrun.kind_note("FAIL: //x:y\n", _HISTORY)


def test_the_culprit_note_carries_the_kind_after_the_failed_checks() -> None:
    """The kind sits between the failed list and the culprit clause; none leaves it unchanged."""
    plain = stackrun.culprit_note(_SUMMARY, [])
    kinded = stackrun.culprit_note(_SUMMARY, [], _HISTORY)
    assert "kind: " not in plain
    assert "and 0 more" not in kinded
    assert kinded.index("failed: ") < kinded.index("kind: ") < kinded.index("culprit: ")
    assert stackrun.culprit_note(_SUMMARY, [], None) == plain
