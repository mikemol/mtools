# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `errors`: a refusal that a best-effort handler for Exception cannot swallow."""

from __future__ import annotations

import contextlib

import pytest

from mikemol.treeio.errors import AmbientVocabError, MutationContractError


def _raise(refusal: BaseException) -> None:
    """Raise the given exception, so the caller below does not raise within its own try."""
    raise refusal


def _swallowing_caller(refusal: BaseException) -> str:
    """Drive the exact caller shape the base class was chosen for.

    The shape is a best-effort handler around the guard call that carries on, so a refusal that
    reached it would be swallowed and the tool would write anyway.

    Returns:
        SWALLOWED when the handler for Exception contained it, otherwise PASSED-THROUGH.

    """
    try:
        with contextlib.suppress(Exception):
            _raise(refusal)
    except MutationContractError:
        return "PASSED-THROUGH"
    return "SWALLOWED"


def test_a_contract_refusal_is_not_an_exception() -> None:
    """The base is BaseException, so no best-effort except clause for Exception contains it."""
    assert issubclass(MutationContractError, BaseException)
    assert not issubclass(MutationContractError, Exception)


def test_a_vocabulary_refusal_stays_on_the_same_side_of_the_line() -> None:
    """The vocab refusal joins the family and is not also a ValueError, which would be caught."""
    assert issubclass(AmbientVocabError, MutationContractError)
    assert not issubclass(AmbientVocabError, ValueError)
    assert not issubclass(AmbientVocabError, Exception)


def test_a_best_effort_handler_passes_the_refusal_but_swallows_an_ordinary_error() -> None:
    """The negative control: the same handler does swallow an ordinary exception."""
    assert _swallowing_caller(MutationContractError("refused")) == "PASSED-THROUGH"
    assert _swallowing_caller(AmbientVocabError("refused")) == "PASSED-THROUGH"
    assert _swallowing_caller(RuntimeError("an ordinary failure")) == "SWALLOWED"


def test_a_refusal_can_be_contained_by_naming_it() -> None:
    """Containment is available when it is stated: an except clause naming the class catches it."""
    with pytest.raises(MutationContractError, match="stated"):
        _raise(MutationContractError("stated"))
