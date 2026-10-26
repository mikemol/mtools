# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""An unmeasured test is projected from measured siblings, as an estimate and never a sum (W1997).

⚑ THE CONTROLS: the nearest cut with a measured neighbour answers (a closer sibling is not
averaged with a distant one), a cut never goes below two words, a test is not its own neighbour, a
word boundary is respected, and no neighbour is None, never zero.
"""

from mikemol.importdag import cost
from mikemol.importdag.cost import Measured

_TABLE = {
    "tests/test_ratchet_pace.py": Measured(2.0, 3.0, 5),
    "tests/test_ratchet_pace_path.py": Measured(4.0, 5.0, 5),
    "tests/test_ratchet.py": Measured(100.0, 120.0, 5),
    "tests/test_ratchetx.py": Measured(1000.0, 1000.0, 5),
    "tests/test_other.py": Measured(7.0, 8.0, 5),
}
_PAIR = 2
_WIDE = (2.0 + 4.0 + 100.0) / 3


def test_the_nearest_cut_with_a_measured_sibling_answers() -> None:
    """test_ratchet_pace_held is near the two test_ratchet_pace tests, not test_ratchet."""
    assert cost.neighbour("tests/test_ratchet_pace_held.py", _TABLE) == (3.0, _PAIR)


def test_a_wider_cut_answers_only_when_no_closer_sibling_exists() -> None:
    """test_ratchet_zzz has no closer sibling, so test_ratchet answers; test_ratchetx is none."""
    got = cost.neighbour("tests/test_ratchet_zzz.py", _TABLE)
    assert got is not None
    assert got[0] == _WIDE


def test_nothing_in_common_beyond_test_is_no_projection() -> None:
    """A test sharing only `test_` is None; so is a test whose only match is itself."""
    assert cost.neighbour("tests/test_unrelated_thing.py", _TABLE) is None
    assert cost.neighbour("tests/test_other.py", _TABLE) is None
