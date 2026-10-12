# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the ruler-sequence generator and its three readings, pinned to paperkit's.

W1048. ⚑ THE GOLDEN STRINGS ARE THE ORIGINAL'S OWN OUTPUT (paperkit d6096c9, render/checks/
rulerseq.py), read once and written here: a port that drifted would fail them, and a differential
run over 300 boundaries, 13 orders and 70 table sizes found 0 differences when it was ported.
"""

from __future__ import annotations

import pytest

from mikemol.rulerseq import (
    column_encoding,
    css_defs,
    css_stops,
    cycle_order,
    dash_pattern,
    emit_f,
    main,
    morse_motif,
    nicematrix_defs,
    rule,
    rule_name,
)
from mikemol.rulerseq.ruler import DASH, DOT

_DASHES = 2
_FOUR = 4
_NINE = 9
_THIRTEEN = 13
_BYTE = 256
_BITS = 8
_DEPTH = 12
_BANNER_LINES = 5


def test_cycle_order_is_the_two_adic_valuation() -> None:
    """Boundaries 1..8 have orders 0,1,0,2,0,1,0,3 (OEIS A007814)."""
    assert [cycle_order(i) for i in range(1, _NINE)] == [0, 1, 0, 2, 0, 1, 0, 3]


@pytest.mark.parametrize("below", [0, -1, -8])
def test_cycle_order_refuses_the_header_rule_and_below(below: int) -> None:
    """Row-boundary 0 (the header rule) has no lowest set bit, so it is an error naming it."""
    with pytest.raises(ValueError, match="row-boundaries i>=1") as caught:
        cycle_order(below)
    assert str(below) in str(caught.value)


def test_the_motif_family_is_self_similar_and_prefix_closed() -> None:
    """Order 1 is a dot and two dashes, order 2 adds four dots, and each order prefixes the next."""
    assert morse_motif(0) == DOT
    assert morse_motif(1) == DOT + DASH * _DASHES
    assert morse_motif(2) == DOT + DASH * _DASHES + DOT * _FOUR
    assert all(morse_motif(k + 1).startswith(morse_motif(k)) for k in range(_DEPTH))


def test_f_is_length_faithful_over_every_byte() -> None:
    """The motif of an 8-bit tuple has exactly the tuple's value as its length."""
    for value in range(_BYTE):
        bits = [(value >> b) & 1 for b in range(_BITS)]
        assert len(emit_f(bits)) == value


def test_the_tex_names_are_the_original_letters_and_unique() -> None:
    """A dot is o and a dash is X, so the names are fixed strings and differ per order."""
    assert [rule_name(k) for k in range(_FOUR)] == [
        "Ruleo",
        "RuleoXX",
        "RuleoXXoooo",
        "RuleoXXooooXXXXXXXX",
    ]
    assert rule(_FOUR) == "\\RuleoXXoooo"


def test_the_md_reading_doubles_its_on_length_each_order() -> None:
    """Orders 0..3 give 0.5, 1, 2 and 4 pt on-lengths with a 1.5 pt gap, so no order flattens."""
    assert [rule(1 << k, "md") for k in range(_FOUR)] == [
        "\\hdashline[0.5pt/1.5pt]",
        "\\hdashline[1pt/1.5pt]",
        "\\hdashline[2pt/1.5pt]",
        "\\hdashline[4pt/1.5pt]",
    ]


def test_the_html_reading_names_one_class_per_order() -> None:
    """Boundary i carries the class rs-<order>."""
    assert [rule(i, "html") for i in (1, 2, _FOUR, 8)] == ["rs-0", "rs-1", "rs-2", "rs-3"]


def test_an_unknown_target_is_refused_with_the_original_words() -> None:
    """The message is the original's, including its omission of html from the list."""
    with pytest.raises(ValueError, match=r"unknown target 'pdf' \(expected 'tex' or 'md'\)"):
        rule(1, "pdf")


def test_the_dash_pattern_and_the_gradient_follow_the_motif() -> None:
    """Order 1 is one dot and two dashes in pt for tikz and in px for the gradient."""
    assert dash_pattern(1) == (
        "dash pattern=on 0.5pt off 1.1pt on 2.2pt off 1.1pt on 2.2pt off 1.1pt"
    )
    assert css_stops(1) == (
        "repeating-linear-gradient(90deg, currentColor 0px 2px, transparent 2px 6px, "
        "currentColor 6px 14px, transparent 14px 18px, currentColor 18px 26px, "
        "transparent 26px 30px)"
    )


def test_the_geometry_is_a_parameter_not_baked() -> None:
    """Changing the lengths changes the output, so the numbers are not magic."""
    assert dash_pattern(0, 1.0, 3.0, 0.7) == "dash pattern=on 1.0pt off 0.7pt"
    stops = css_stops(0, 1.0, 5.0, 2.0)
    assert stops.startswith("repeating-linear-gradient(90deg, currentColor 0px 1px")


def test_the_preamble_has_one_custom_line_per_order() -> None:
    """A two-variable table has orders 0 and 1, so two lines; zero variables still gives order 0."""
    two = nicematrix_defs(2).split("\n")
    assert len(two) == _DASHES
    assert two[0] == (
        "\\NiceMatrixOptions{custom-line={command=\\\\Ruleo, "
        "tikz={line width=0.5pt, dash pattern=on 0.5pt off 1.1pt}}}"
    )
    assert nicematrix_defs(0) == two[0]


def test_the_stylesheet_has_one_class_per_order_with_the_prefix() -> None:
    """Order 0 is `.rs-0` with the border-image gradient; a prefix renames the class."""
    assert css_defs(1) == (
        ".rs-0 { border-bottom: 2px solid transparent; border-image: repeating-linear-gradient("
        "90deg, currentColor 0px 2px, transparent 2px 6px) 2; border-image-slice: 2; }"
    )
    assert css_defs(1, "q").startswith(".q-0 {")


def test_any_row_count_gets_a_prefix_of_the_ruler_sequence() -> None:
    """Thirteen rows, not a power of two, encode as the first twelve boundaries of A007814."""
    full = [cycle_order(i) for i in range(1, 64)]
    assert column_encoding(_THIRTEEN) == full[: _THIRTEEN - 1]
    assert column_encoding(_NINE) == [0, 1, 0, 2, 0, 1, 0, 3]


def test_the_selftest_passes_and_says_so(capsys: pytest.CaptureFixture[str]) -> None:
    """The ported selftest returns 0 with the five-line banner paperkit's printed."""
    assert main() == 0
    shown = capsys.readouterr().out.splitlines()
    assert len(shown) == _BANNER_LINES
    assert shown[0].startswith("rulerseq: ok")
    assert shown[-1].endswith("(WCAG 1.4.1)")
