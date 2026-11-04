# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""nemik's stackable set is read faithfully; only submittable, unlanded cards are picked (W1428)."""

import pytest

from mikemol.katas import stackable

_OUTPUT = (
    "STACK mtools:W2131 hooks/src/a.py hooks/tests/test_a.py\n"
    "WAITING mtools:W2132 hooks/src/a.py\n"
    "STACK mtools:W2126 hooks/src/b.py\n"
    "STACK mtools:W2135 ratchet/src/c.py\n"
    "\n"
    "3 stackable of 100 ready; 79 have no manifest\n"
)


def test_stack_and_waiting_rows_are_read_with_their_files_in_order() -> None:
    """The count line and the blank line are not rows; each row keeps state, repo, card, files."""
    rows = stackable.parse(_OUTPUT)
    assert [(r.state, r.repo, r.symbol) for r in rows] == [
        ("STACK", "mtools", "W2131"),
        ("WAITING", "mtools", "W2132"),
        ("STACK", "mtools", "W2126"),
        ("STACK", "mtools", "W2135"),
    ]
    assert rows[0].files == ("hooks/src/a.py", "hooks/tests/test_a.py")


def test_text_that_is_not_a_row_yields_no_rows() -> None:
    """An empty output and a bare count line give an empty set, not an error."""
    assert stackable.parse("") == []
    assert stackable.parse("0 stackable of 5 ready; 5 have no manifest\n") == []


def test_a_row_that_does_not_fit_is_refused_naming_the_line() -> None:
    """Silently skipping it would lose a card: a missing or malformed cite raises."""
    for bad in ("STACK", "STACK mtools", "STACK W12 f.py", "WAITING mtools:X3 f.py"):
        with pytest.raises(ValueError, match="no <repo>:W<n>"):
            stackable.parse(f"{bad}\n")


def test_only_stack_rows_not_already_landed_are_submitted_in_order() -> None:
    """WAITING never goes; a card git says landed is left out; the order is the printed one."""
    picked = stackable.submit_set(stackable.parse(_OUTPUT), {"W2126"})
    assert [r.symbol for r in picked] == ["W2131", "W2135"]
    every = stackable.submit_set(stackable.parse(_OUTPUT), set())
    assert [r.symbol for r in every] == ["W2131", "W2126", "W2135"]
