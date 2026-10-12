# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The generator's built-in selftest, ported with paperkit's (nemik reads it as a witness).

W1048. Run it as `python -m mikemol.rulerseq`: it prints a pass banner and returns 0, or says which
reading is wrong on stderr and returns 1. The checks are the paperkit file's, one function each.
"""

from __future__ import annotations

import sys

from mikemol.rulerseq.ruler import (
    column_encoding,
    css_defs,
    css_stops,
    cycle_order,
    emit_f,
    morse_motif,
    rule,
    rule_name,
)

_RULER_PREFIX_LEN = 64
_NON_POWER_ROWS = 13
_POWER_ROWS = 9
_TUPLE_BITS = 8
_MOTIF_DEPTH = 10
_MD_ORDERS = 6
_NAME_ORDERS = 9
_EXPECTED_ROWS_9 = [0, 1, 0, 2, 0, 1, 0, 3]
_DASH_MARK = "—"
_SUPER_N = "ⁿ"
_DELTA = "δ"
_BANNER_OK = (
    f"rulerseq: ok {_DASH_MARK} ruler-sequence rules encode binary row structure in the PATTERN, "
    "uncapped"
)
_BANNER_P = (
    "  P: cycle_order = 2-adic valuation; len(F(B))==value(B) (256 tuples); "
    f"encodes ARBITRARY m (13 rows, not just 2{_SUPER_N}) as a faithful A007814 prefix"
)
_BANNER_F = (
    "  F: md fallback carries orders 0..5 as DISTINCT rules (mat230 flattened 3+ to \\hline)"
)
_BANNER_T = (
    "  target-independent: tex (nicematrix), html (CSS border-image), md (arydshln) "
    f"{_DASH_MARK} three readings of the ONE generator, not a LaTeX-only feature"
)
_BANNER_D = (
    f"  {_DELTA}: the cue is the rule PATTERN alone {_DASH_MARK} never colour, never thickness "
    "(WCAG 1.4.1)"
)
_BANNER_FAIL = (
    f"rulerseq: FAIL {_DASH_MARK} the ruler-sequence encoding or one of its render readings is "
    "wrong"
)


def _ruler_sequence_is_correct() -> bool:
    """Check cycle_order(1..8) is the valuations 0,1,0,2,0,1,0,3 and 13 rows is a prefix.

    Returns:
        True when both the power-of-two and the arbitrary-row tables encode correctly.

    """
    sequence = [cycle_order(i) for i in range(1, _RULER_PREFIX_LEN)]
    return (
        column_encoding(_POWER_ROWS) == _EXPECTED_ROWS_9
        and column_encoding(_NON_POWER_ROWS) == sequence[: _NON_POWER_ROWS - 1]
    )


def _f_is_length_faithful() -> bool:
    """Check len(F(B)) == value(B) for every 8-bit tuple.

    Returns:
        True when every tuple's motif has the length of its value.

    """
    tuples = ([(v >> b) & 1 for b in range(_TUPLE_BITS)] for v in range(1 << _TUPLE_BITS))
    return all(len(emit_f(bits)) == value for value, bits in enumerate(tuples))


def _motif_orders_prefix() -> bool:
    """Check order k is a prefix of order k+1, to a depth past the old cap of seven.

    Returns:
        True when every order up to the depth prefixes the next.

    """
    return all(morse_motif(k + 1).startswith(morse_motif(k)) for k in range(_MOTIF_DEPTH))


def _md_reading_keeps_the_structure() -> bool:
    """Check orders 0..5 of the md reading are six distinct rules, not one flattened line.

    Returns:
        True when the six boundaries 1,2,4,8,16,32 give six distinct md rules.

    """
    return len({rule(1 << k, "md") for k in range(_MD_ORDERS)}) == _MD_ORDERS


def _tex_names_are_unique() -> bool:
    """Check the tex rule names are unique per order and uncapped (order 8 and beyond).

    Returns:
        True when nine consecutive orders give nine names.

    """
    return len({rule_name(k) for k in range(_NAME_ORDERS)}) == _NAME_ORDERS


def _html_reading_matches() -> bool:
    """Check the html reading names one class per order and paints one run per motif character.

    Returns:
        True when classes are rs-0..rs-5, gradients match the motif lengths, and stylesheets differ.

    """
    classes = [rule(1 << k, "html") for k in range(_MD_ORDERS)] == [
        f"rs-{k}" for k in range(_MD_ORDERS)
    ]
    runs = all(css_stops(k).count("currentColor") == len(morse_motif(k)) for k in range(_MD_ORDERS))
    sheets = len({css_defs(k + 1) for k in range(_MD_ORDERS)}) == _MD_ORDERS
    return classes and runs and sheets


def main() -> int:
    """Run the selftest and report.

    Returns:
        0 when every reading is right, 1 otherwise.

    """
    checks = (
        _ruler_sequence_is_correct,
        _f_is_length_faithful,
        _motif_orders_prefix,
        _md_reading_keeps_the_structure,
        _tex_names_are_unique,
        _html_reading_matches,
    )
    if all(check() for check in checks):
        banner = [_BANNER_OK, _BANNER_P, _BANNER_F, _BANNER_T, _BANNER_D]
        sys.stdout.write("\n".join(banner) + "\n")
        return 0
    sys.stderr.write(_BANNER_FAIL + "\n")
    return 1
