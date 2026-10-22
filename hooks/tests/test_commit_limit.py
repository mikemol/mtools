# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the commit stall limit's overrides (paperkit:W299, mtools:W946, W1804).

⚑ THE DEFAULT IS THE POSITIVE CONTROL: an override that is ignored and one that is always taken both
read as "unset" until a value that must be refused is tried. A zero or text must never read as no
bound, which would let a wedged gate hold the repository's lease for good.
"""

from __future__ import annotations

import pytest

from mikemol.hooks import commitprogress

_RAISED = 240
_SLOW = 5.5


def test_unset_means_the_default_looks_and_period() -> None:
    """No variable, no change."""
    assert commitprogress.looks_from({}) == commitprogress.DEFAULT_LOOKS
    assert commitprogress.period_from({}) == commitprogress.DEFAULT_PERIOD_S


def test_a_positive_value_changes_the_looks_and_the_period() -> None:
    """A cold sweep can ask for more looks, a slow host for a longer gap."""
    assert commitprogress.looks_from({commitprogress.LOOKS_ENV: str(_RAISED)}) == _RAISED
    assert commitprogress.period_from({commitprogress.PERIOD_ENV: "5.5"}) == _SLOW


@pytest.mark.parametrize("bad", ["", "0", "-5", "1.5", "soon", " 60"])
def test_anything_else_for_the_looks_is_ignored_not_read_as_no_bound(bad: str) -> None:
    """Zero or text must not remove the bound that stops a wedged gate."""
    assert commitprogress.looks_from({commitprogress.LOOKS_ENV: bad}) == (
        commitprogress.DEFAULT_LOOKS
    )


@pytest.mark.parametrize("bad", ["", "0", "-1", "soon"])
def test_anything_else_for_the_period_is_ignored(bad: str) -> None:
    """A zero gap would spin; a negative or text one is not a gap."""
    assert commitprogress.period_from({commitprogress.PERIOD_ENV: bad}) == (
        commitprogress.DEFAULT_PERIOD_S
    )
