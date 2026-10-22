# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A failing step is classified against its history, not guessed at (W1720).

⚑ THE THREE HISTORIES AND THE SHORT ONE ARE THE TABLE: each class has a record that is it and a
record next to it that is not, so a classifier that ignored the record, or counted the window wrong,
fails a row.
"""

import pytest

from mikemol.hooks import gateclass

_BROKEN = (True, True, True)
_FLAKY = (False, True, False)
_CLEAN = (False, False, False)
_WINDOW = 3


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        ((), gateclass.UNKNOWN),
        (_CLEAN, gateclass.NEW),
        ((False,), gateclass.NEW),
        (_FLAKY, gateclass.INTERMITTENT),
        ((True, False), gateclass.INTERMITTENT),
        (_BROKEN, gateclass.BROKEN),
        ((True,), gateclass.BROKEN),
    ],
)
def test_each_history_gives_its_class(record: tuple[bool, ...], expected: str) -> None:
    """Never failed is new, some red is intermittent, every round red is broken, none is unknown."""
    assert gateclass.classify(record) == expected


def test_only_the_most_recent_rounds_count() -> None:
    """A red long ago under green rounds is new; a red run under old green is broken."""
    old_red = (False, False, False, False, False, True, True)
    assert gateclass.classify(old_red, recent=_WINDOW) == gateclass.NEW
    recent_red = (True, True, True, False, False)
    assert gateclass.classify(recent_red, recent=_WINDOW) == gateclass.BROKEN
    assert gateclass.classify(recent_red, recent=len(recent_red)) == gateclass.INTERMITTENT


def test_a_window_below_one_still_looks_at_the_newest_round() -> None:
    """Zero or a negative window is read as one round, never as an empty record."""
    assert gateclass.classify((True, False), recent=0) == gateclass.BROKEN
    assert gateclass.classify((False, True), recent=-3) == gateclass.NEW


def test_a_step_absent_from_a_history_that_covers_rounds_is_new_and_from_none_unknown() -> None:
    """The history lists only steps that ever failed, so absent means passed every round."""
    history = {"//a:t": _BROKEN, "//b:t": _FLAKY}
    got = gateclass.classify_all(["//a:t", "//b:t", "//c:t"], history)
    assert got == {
        "//a:t": gateclass.BROKEN,
        "//b:t": gateclass.INTERMITTENT,
        "//c:t": gateclass.NEW,
    }
    assert gateclass.classify_all(["//c:t"], {}) == {"//c:t": gateclass.UNKNOWN}
