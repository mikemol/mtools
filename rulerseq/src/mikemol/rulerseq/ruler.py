# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Accessible table rules whose PATTERN encodes a row enumeration's binary structure (W1048).

Ported from paperkit's render/checks/rulerseq.py (paperkit d6096c9, last changed by 0893d86;
paperkit:W338, nemik:W389). In any row enumeration counted in binary (a truth table, a K-map
listing, a binary counter) the horizontal rule between two adjacent rows can be CHOSEN BY THE
STRUCTURE instead of drawn uniformly. The rule at row-boundary `i` is governed by the cycle order
of that boundary: `cycle_order(i)` is the 2-adic valuation of `i` (OEIS A007814), the trailing-zero
count, which says which bit rolls over there. Rendered as a self-similar dot/dash (Morse) motif,
the rule's pattern, not its colour and not its thickness, carries the counting structure, so a
reader who cannot perceive colour (WCAG 2.2 SC 1.4.1, Use of Colour) still recovers which bit each
boundary flips.

The owned object is the ruler sequence itself. The down-column sequence of rule orders for an
m-row table is the binary encoding of the row numbers read as a column, for ARBITRARY m: an m that
is not a power of two gets a faithful prefix of the ruler sequence. The render forms (a nicematrix
tex reading, an arydshln md reading, a CSS html reading) are projections of the one generator,
and none is capped:

    motif family F: order k PREFIXES order k+1, len(F(B)) == value(B), F injective.

    cycle_order(i)              the 2-adic valuation of the boundary index
    morse_motif(k)              the order-k self-similar dot/dash motif (the generator)
    rule(i, target)             the rule at boundary i, projected to "tex", "html" or "md"
    nicematrix_defs(n)          the custom-line preamble for an n-variable table
    css_defs(n)                 one CSS class per cycle order, for a style block
"""

DOT = "·"
DASH = "-"
_ON_DOT_PT = 0.5
_ON_DASH_PT = 2.2
_GAP_PT = 1.1
_LINE_WIDTH_PT = 0.5
_MD_ON_BASE_PT = 0.5
_MD_OFF_PT = 1.5
_CSS_DOT_PX = 2.0
_CSS_DASH_PX = 8.0
_CSS_GAP_PX = 4.0
_FIRST_BOUNDARY = 1


def cycle_order(i: int) -> int:
    """Give the cycle order at row-boundary `i`: its trailing-zero count (2-adic valuation).

    The order of the highest-index input that flips at that boundary. Defined for i >= 1; the
    header rule (i == 0) has no lowest set bit.

    Returns:
        the index of the lowest set bit of `i`.

    Raises:
        ValueError: when `i` is below 1.

    """
    if i < _FIRST_BOUNDARY:
        msg = f"cycle_order is defined on row-boundaries i>=1; got {i}"
        raise ValueError(msg)
    return (i & -i).bit_length() - 1


def emit_f(bits: list[int], i: int = 0, s: str = DOT) -> str:
    """Emit F over a binary tuple, least significant bit first.

    Empty if `i` is past the end; F(i+1, s) if bit i is 0; s repeated 2^i times followed by
    F(i+1, the other symbol) if bit i is 1. len(F(B)) == value(B) and F is injective.

    Returns:
        the motif string for the tuple.

    """
    if i >= len(bits):
        return ""
    if bits[i] == 0:
        return emit_f(bits, i + 1, s)
    return s * (1 << i) + emit_f(bits, i + 1, DASH if s == DOT else DOT)


def morse_motif(k: int) -> str:
    """Give the order-k motif: F over the all-ones tuple up to bit k, with no cap on k.

    Returns:
        the self-similar dot/dash string; order k is a prefix of order k+1.

    """
    return emit_f([1] * (k + 1))


def rule_name(k: int) -> str:
    """Give a nicematrix custom-line command name for cycle order k, generated and uncapped.

    The Morse motif in TeX-safe letters (a dot is o, a dash is X), a bijection into the only
    characters nicematrix accepts in a command name.

    Returns:
        the command name, unique per order.

    """
    return "Rule" + "".join("o" if c == DOT else "X" for c in morse_motif(k))


def dash_pattern(
    k: int, dot: float = _ON_DOT_PT, dash: float = _ON_DASH_PT, gap: float = _GAP_PT
) -> str:
    """Give a TikZ dash-pattern spec rendering the order-k motif; the geometry is exposed.

    Returns:
        the `dash pattern=` clause, lengths in pt.

    """
    return "dash pattern=" + " ".join(
        f"on {dot if c == DOT else dash}pt off {gap}pt" for c in morse_motif(k)
    )


def nicematrix_defs(n_vars: int, line_width: float = _LINE_WIDTH_PT) -> str:
    r"""Give one `\Rule<k>` nicematrix custom-line per cycle order an n-variable table uses.

    An n-variable (2^n row) table has boundaries of orders 0..n-1, so the highest order is
    derived from the table, not fixed.

    Returns:
        the preamble lines for the tex file, one per order.

    """
    return "\n".join(
        r"\NiceMatrixOptions{custom-line={command=\\"
        + rule_name(k)
        + r", tikz={line width="
        + f"{line_width}"
        + r"pt, "
        + dash_pattern(k)
        + r"}}}"
        for k in range(max(n_vars, 1))
    )


def _md_dash(k: int) -> str:
    r"""Give the arydshln `\hdashline[on/off]` whose lengths encode order k, uncapped.

    The on-length doubles with the order, mirroring the motif's 2^k growth, so each order is
    visually distinct and monotone.

    Returns:
        the dash command.

    """
    on = _MD_ON_BASE_PT * (1 << k)
    return rf"\hdashline[{on:g}pt/{_MD_OFF_PT:g}pt]"


def css_stops(
    k: int, dot: float = _CSS_DOT_PX, dash: float = _CSS_DASH_PX, gap: float = _CSS_GAP_PX
) -> str:
    """Give a CSS repeating-linear-gradient stop list rendering the order-k motif.

    A dot is a short opaque run, a dash a long one, with transparent gaps; lengths in px.

    Returns:
        the `repeating-linear-gradient(...)` value.

    """
    stops: list[str] = []
    pos = 0.0
    for c in morse_motif(k):
        on = dot if c == DOT else dash
        stops.append(f"currentColor {pos:g}px {pos + on:g}px")
        pos += on
        stops.append(f"transparent {pos:g}px {pos + gap:g}px")
        pos += gap
    return f"repeating-linear-gradient(90deg, {', '.join(stops)})"


def _css_rule(k: int) -> str:
    """Give the CSS declarations for a boundary of cycle order k.

    A bottom border-image paints the motif. The pattern carries the structure, never colour
    (it uses currentColor) nor thickness.

    Returns:
        the declaration text.

    """
    return (
        "border-bottom: 2px solid transparent; "
        f"border-image: {css_stops(k)} 2; border-image-slice: 2;"
    )


def css_defs(n_orders: int, prefix: str = "rs") -> str:
    """Give one CSS class `.<prefix>-<k>` per cycle order a table uses.

    `n_orders` is derived from the table (its highest cycle order plus one), not a fixed cap.

    Returns:
        the rules for a style block or stylesheet, one per order.

    """
    return "\n".join(f".{prefix}-{k} {{ {_css_rule(k)} }}" for k in range(max(n_orders, 1)))


def rule(i: int, target: str = "tex") -> str:
    r"""Give the rule at row-boundary `i`; the pattern, not thickness or colour, carries order.

    tex gives the nicematrix `\Rule<k>` Morse custom-line; html gives the CSS class `rs-<k>`
    whose border-image gradient paints the motif; md gives the arydshln `\hdashline[on/off]`
    whose lengths encode the order.

    Returns:
        the rule in the target's form.

    Raises:
        ValueError: when `target` is none of tex, html or md.

    """
    k = cycle_order(i)
    if target == "tex":
        return "\\" + rule_name(k)
    if target == "html":
        return f"rs-{k}"
    if target == "md":
        return _md_dash(k)
    msg = f"unknown target {target!r} (expected 'tex' or 'md')"
    raise ValueError(msg)


def column_encoding(n_rows: int) -> list[int]:
    """Give the down-column sequence of rule orders for an n_rows table, boundaries 1..n_rows-1.

    By construction the binary encoding of the row numbers read as a column.

    Returns:
        the cycle order of each boundary, in order.

    """
    return [cycle_order(i) for i in range(_FIRST_BOUNDARY, n_rows)]
