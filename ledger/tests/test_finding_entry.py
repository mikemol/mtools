# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.ledger.finding_entry`: substrate's suite, with the anchor supplied.

⚑⚑ THE DOUBLE-QUOTED KEY IS ASSERTED DIRECTLY, because `repr` gets it wrong and the failure is
invisible from inside this module.

⚑ THE REJOIN IS CHECKED THROUGH `ast.parse`, NEVER `eval`: the wrapper's output is source text,
and a suite that executed it would run the very agent-supplied string `repr` exists to neutralise.
Walking the parsed expression for string constants also asserts the wrapper emitted STRING
literals rather than anything that merely parses.
"""

from __future__ import annotations

import ast
from typing import Protocol, cast

import pytest

from mikemol.ledger import finding_entry, finding_kindspec

_LONG = (
    "This note is deliberately long enough that the wrapper must break it across more than one "
    "literal, so the trailing-space rejoin is exercised rather than assumed, and it carries a "
    "quote-free body so the comparison is about wrapping alone."
)
_SHORT = "a short note"
# ⚑ A NOTE THAT WOULD BREAK AN UNQUOTED EMIT — the reason the note goes through `repr`.
_HOSTILE = 'it said "no" and used a backslash \\ and a single \' quote'

# A roster terminator, as a caller whose roster ends this way would pass it.
_ANCHOR = "}\n\n\ndef _bib_keys():"


class _SpliceWithoutAnchor(Protocol):
    """`splice` as a caller who supplied no anchor would call it."""

    def __call__(self, source: str, entry: str) -> tuple[str, str]: ...


def _text_of(node: ast.Constant) -> str:
    """Return a constant's string value, or a marker when it is not a string.

    Returns:
        the text, or a marker that cannot equal any note.

    """
    return node.value if isinstance(node.value, str) else "<NOT-A-STRING>"


def _rejoined(wrapped: str) -> str:
    """Return the text the emitted literals concatenate back to.

    Returns:
        the rejoined text, or a marker when the source does not parse.

    """
    try:
        tree = ast.parse("(" + wrapped + ")", mode="eval")
    except SyntaxError:
        return "<DOES-NOT-PARSE>"
    return "".join(_text_of(node) for node in ast.walk(tree) if isinstance(node, ast.Constant))


def _spec(kind: str) -> finding_kindspec.Spec:
    """Parse a kind the fixtures know to be well formed.

    Returns:
        the spec.

    """
    spec, why = finding_kindspec.parse(kind)
    assert spec is not None, why
    return spec


def test_the_key_is_double_quoted_never_single() -> None:
    """The key is DOUBLE-quoted, which the resolver regex requires, and never `repr`-quoted."""
    row = finding_entry.render("k-bare", _spec("standing"), _SHORT)
    assert row.startswith('    "k-bare":')
    assert "'k-bare'" not in row


def test_each_kind_renders_its_own_builder_and_arguments() -> None:
    """A bare kind renders its builder; a command kind its argv; a mode kind tool, flag, no note."""
    bare = finding_entry.render("k-bare", _spec("standing"), _SHORT)
    cmd = finding_entry.render("k-cmd", _spec("selftest:python3 -m some.suite"), _SHORT)
    moded = finding_entry.render("k-mode", _spec("mode:toolmodes.py:--divergence"), _SHORT)
    assert "lambda: _standing(" in bare
    assert "'python3'" in cmd
    assert "lambda: _selftest(" in cmd
    assert "'toolmodes.py'" in moded
    assert "'--divergence'" in moded
    assert _SHORT not in moded
    assert all(r.startswith("    ") and r.endswith(",\n") for r in (bare, cmd, moded))


def test_a_long_note_wraps_and_rejoins() -> None:
    """A long note breaks across literals that concatenate back to it; a short one does not."""
    wrapped = finding_entry.wrap_note(_LONG)
    assert finding_entry.CONT in wrapped
    assert finding_entry.CONT not in finding_entry.wrap_note(_SHORT)
    assert _rejoined(wrapped) == " ".join(_LONG.split())
    assert _rejoined(finding_entry.wrap_note(_SHORT)) == _SHORT


def test_a_hostile_note_survives_the_round_trip() -> None:
    """Quotes and a backslash survive: an unquoted emit would write a file that does not parse."""
    assert _rejoined(finding_entry.wrap_note(_HOSTILE)) == _HOSTILE


def test_an_empty_note_still_emits_a_literal() -> None:
    """An empty note emits `''`: emitting nothing, as the original did, splices a syntax error."""
    assert finding_entry.wrap_note("") == "''"


def test_a_unique_anchor_splices_the_entry_ahead_of_it() -> None:
    """The entry lands before the terminator, and the original content survives."""
    body = 'WITNESSES = {\n    "a": 1,\n' + _ANCHOR
    entry = '    "b": 2,\n'
    spliced, why = finding_entry.splice(body, entry, anchor=_ANCHOR)
    assert not why
    assert spliced.index(entry) < spliced.index(_ANCHOR)
    assert '"a": 1' in spliced


def test_a_missing_or_duplicated_anchor_refuses() -> None:
    """Zero or two anchors REFUSE, saying how many and why a guess is unsafe."""
    body = 'WITNESSES = {\n    "a": 1,\n' + _ANCHOR
    entry = '    "b": 2,\n'
    missing, missing_why = finding_entry.splice("no terminator here", entry, anchor=_ANCHOR)
    doubled, doubled_why = finding_entry.splice(body + body, entry, anchor=_ANCHOR)
    assert not missing
    assert "0 occurrence" in missing_why
    assert not doubled
    assert "2 occurrence" in doubled_why
    assert "can still parse" in doubled_why


def test_the_anchor_is_the_callers_with_no_default() -> None:
    """No module anchor remains, and a splice without one is a TypeError."""
    assert not hasattr(finding_entry, "ANCHOR")
    unanchored = cast("_SpliceWithoutAnchor", finding_entry.splice)
    with pytest.raises(TypeError, match="anchor"):
        unanchored("x", "y")
