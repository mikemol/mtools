# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the commit time limit's override (paperkit:W299, mtools:W946).

⚑ THE DEFAULT IS THE POSITIVE CONTROL: an override that is ignored and one that is always taken both
read as "unset" until a value that must be refused is tried.
"""

from __future__ import annotations

import pytest

from mikemol.hooks import commit_kata

_RAISED = 14400


def test_unset_means_the_default() -> None:
    """No variable, no change."""
    assert commit_kata.commit_limit({}) == commit_kata.COMMIT_TIMEOUT_S


def test_a_positive_integer_raises_the_limit() -> None:
    """A cold sweep can ask for more than the default."""
    assert commit_kata.commit_limit({commit_kata.COMMIT_LIMIT_ENV: str(_RAISED)}) == _RAISED


@pytest.mark.parametrize("bad", ["", "0", "-5", "1.5", "soon", " 60"])
def test_anything_else_is_ignored_not_read_as_no_limit(bad: str) -> None:
    """Zero or text must not remove the bound that stops a wedged gate."""
    assert commit_kata.commit_limit({commit_kata.COMMIT_LIMIT_ENV: bad}) == (
        commit_kata.COMMIT_TIMEOUT_S
    )
