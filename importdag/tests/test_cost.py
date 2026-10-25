# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A card's landing cost is the measured CPU of the tests its manifest reaches (W1997).

⚑ THE FIXTURE GRAPH: gamma is imported by beta, beta by alpha; test_a imports alpha (so it reaches
gamma through two edges), test_b imports nothing of the chain, test_c declares a read of gamma's
data file, and test_g is itself a manifest path.
"""

import pytest

from mikemol.importdag import cost

_DOC: dict[str, object] = {
    "modules": {
        "m/alpha.py": {"imports": ["m/beta.py"], "reads": []},
        "m/beta.py": {"imports": ["m/gamma.py"], "reads": []},
        "m/gamma.py": {"imports": [], "reads": []},
        "m/other.py": {"imports": [], "reads": []},
    },
    "tests": {
        "t/test_a.py": {"imports": ["m/alpha.py"], "reads": []},
        "t/test_b.py": {"imports": ["m/other.py"], "reads": []},
        "t/test_c.py": {"imports": [], "reads": ["data/gamma.txt"]},
        "t/test_g.py": {"imports": [], "reads": []},
    },
}
_TABLE = {
    "t/test_a.py": cost.Measured(2.0, 3.0, 7),
    "t/test_b.py": cost.Measured(10.0, 20.0, 5),
    "t/test_c.py": cost.Measured(1.0, 1.5, 3),
}
_A_AND_C_MEDIAN = 3.0
_A_AND_C_P90 = 4.5
_A_AND_B_MEDIAN = 12.0
_FEWEST = 3


def test_a_change_reaches_the_tests_through_a_chain_of_imports() -> None:
    """Gamma is two edges below test_a, so a change to it reruns test_a and not test_b."""
    assert cost.affected(_DOC, ["m/gamma.py"]) == {"t/test_a.py"}
    assert cost.affected(_DOC, ["m/alpha.py"]) == {"t/test_a.py"}


def test_a_declared_read_and_a_manifest_test_are_reached() -> None:
    """A test that reads a changed file, and a changed test itself, are both rerun."""
    assert cost.affected(_DOC, ["data/gamma.txt"]) == {"t/test_c.py"}
    assert cost.affected(_DOC, ["t/test_g.py"]) == {"t/test_g.py"}


def test_a_path_the_graph_does_not_name_is_reported_not_read_as_nothing() -> None:
    """The caller learns the set is a floor: the unnamed path comes back."""
    assert cost.unnamed(_DOC, ["m/gamma.py", "m/new.py", "a.md"]) == ("a.md", "m/new.py")
    assert cost.affected(_DOC, ["m/new.py"]) == frozenset()


def test_the_price_adds_the_measured_and_names_the_rest() -> None:
    """Sums over the measured tests, the smallest sample count, and the unmeasured ones listed."""
    got = cost.price(["t/test_a.py", "t/test_c.py", "t/test_g.py"], _TABLE)
    assert got.median_s == pytest.approx(_A_AND_C_MEDIAN)
    assert got.p90_s == pytest.approx(_A_AND_C_P90)
    assert got.fewest == _FEWEST
    assert got.unknown == ("t/test_g.py",)
    nothing = cost.price(["t/test_g.py"], _TABLE)
    assert (nothing.median_s, nothing.fewest, nothing.unknown) == (0, None, ("t/test_g.py",))


def test_two_cards_count_an_overlap_once_and_a_card_after_its_enabler_pays_the_rest() -> None:
    """Test_a is reached by both cards: together prices it once; after removes what ran."""
    first = cost.affected(_DOC, ["m/gamma.py"])
    second = cost.affected(_DOC, ["m/alpha.py", "m/other.py"])
    both = cost.together(first, second)
    assert both == {"t/test_a.py", "t/test_b.py"}
    assert cost.price(both, _TABLE).median_s == pytest.approx(_A_AND_B_MEDIAN)
    assert cost.after(first, second) == {"t/test_b.py"}
