# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ahead-stack refusal names the shared paths and the way out (W2078).

⚑ NO PATHS IS NO REFUSAL: the empty case returns None, so a caller never refuses on a message.
"""

from mikemol.hooks import aheadrefusal
from mikemol.hooks.aheadrefusal import refusal


def test_no_unbuilt_path_is_no_refusal() -> None:
    """An empty list returns None, not an empty message."""
    assert refusal([]) is None
    assert refusal(()) is None


def test_the_refusal_names_the_paths_the_count_and_the_escape() -> None:
    """Two paths: both named, sorted, the count stated, the --freeze-from way out given."""
    said = refusal(["hooks/warrants.bib", "hooks/mutants.regex"])
    assert said is not None
    assert "2 file(s)" in said
    assert "hooks/mutants.regex, hooks/warrants.bib" in said
    assert "more" not in said
    assert "--freeze-from" in said


def test_a_long_list_is_capped_and_says_how_many_are_hidden() -> None:
    """Seven paths: the first five by name, two hidden."""
    paths = [f"p{n}.py" for n in range(7)]
    said = refusal(paths)
    assert said is not None
    assert "7 file(s)" in said
    assert "p4.py and 2 more" in said
    assert "p5.py" not in said


def test_exactly_the_cap_hides_nothing() -> None:
    """Five paths show all five and no 'more'."""
    paths = [f"p{n}.py" for n in range(aheadrefusal.SHOWN)]
    said = refusal(paths)
    assert said is not None
    assert "more" not in said
    assert "p4.py" in said
