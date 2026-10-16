# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""mikemol.rulerseq: table rules whose pattern carries a row enumeration's binary structure.

The 2-adic valuation of a row boundary (OEIS A007814) rendered as a self-similar Morse motif, so a
rule's pattern, not its colour, says which bit rolls over there (WCAG 2.2 SC 1.4.1). Ported from
paperkit's render/checks/rulerseq.py (W1048, paperkit:W338); the public names are the original's.
`rule_name` and `css_stops` were `_rule_name` and `_css_stops` there. The selftest is
`python -m mikemol.rulerseq`.
"""

from mikemol.rulerseq.ruler import (
    column_encoding,
    css_defs,
    css_stops,
    cycle_order,
    dash_pattern,
    emit_f,
    morse_motif,
    nicematrix_defs,
    rule,
    rule_name,
)
from mikemol.rulerseq.selftest import main

__all__ = [
    "column_encoding",
    "css_defs",
    "css_stops",
    "cycle_order",
    "dash_pattern",
    "emit_f",
    "main",
    "morse_motif",
    "nicematrix_defs",
    "rule",
    "rule_name",
]
