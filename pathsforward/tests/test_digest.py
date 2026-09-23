# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the hash: one tagged form emitted, every legacy form accepted as a transition."""

from __future__ import annotations

import hashlib
import json

import pytest

from mikemol.pathsforward.digest import (
    FULL_HEX,
    LEGACY_FORMS,
    LEGACY_MIN_HEX,
    TAG,
    V2_HEX,
    Outcome,
    legacy_digests,
    v2,
    verify,
)

# Non-ASCII on purpose: it is what separates the ensure_ascii forms (the survey's fixture had 129).
_WAYPOINTS: list[dict[str, object]] = [
    {"symbol": "W1", "title": "café — unicode", "status": "ready"},
]
_ASCII: list[dict[str, object]] = [{"symbol": "W1", "title": "plain", "status": "ready"}]
_SRE_PREFIX = 12
_OTHERS_PREFIX = 16
_TOO_SHORT = LEGACY_MIN_HEX - 1
_FOREIGN = "0" * _OTHERS_PREFIX
_FORM_COUNT = 4


def _independent(separators: tuple[str, str], *, ensure_ascii: bool) -> str:
    """Hash the fixture without the module, as the survey's schemes.py did.

    Returns:
        the full hex digest.

    """
    blob = json.dumps(_WAYPOINTS, sort_keys=True, separators=separators, ensure_ascii=ensure_ascii)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def test_v2_is_tagged_compact_ascii_sixteen_hex() -> None:
    """v2 is `v2:` plus the first 16 hex of the compact, ASCII-escaped serialisation (D1)."""
    expected = TAG + _independent((",", ":"), ensure_ascii=True)[:V2_HEX]
    assert v2(_WAYPOINTS) == expected


def test_the_four_legacy_forms_are_four_digests_on_non_ascii() -> None:
    """On non-ASCII waypoints the four forms are four distinct digests (the grid is real)."""
    digests = legacy_digests(_WAYPOINTS)
    assert len(set(digests.values())) == _FORM_COUNT


def test_the_legacy_forms_match_an_independent_computation() -> None:
    """Each named form is the byte-form its name says."""
    expected = {
        name: _independent(seps, ensure_ascii=ascii_only)
        for name, (seps, ascii_only) in LEGACY_FORMS.items()
    }
    assert legacy_digests(_WAYPOINTS) == expected


def test_ascii_waypoints_collapse_the_ascii_axis() -> None:
    """On pure-ASCII waypoints C/A and C/U coincide, as the survey measured on gabion."""
    digests = legacy_digests(_ASCII)
    assert digests["C/A"] == digests["C/U"]


def test_an_exact_v2_matches() -> None:
    """The file's own v2 value is a match."""
    assert verify(_WAYPOINTS, v2(_WAYPOINTS)).outcome is Outcome.MATCH


def test_a_different_v2_diverges() -> None:
    """A different tagged value is a divergence; a tagged value is never prefix-matched."""
    short = v2(_WAYPOINTS)[: len(TAG) + _SRE_PREFIX]
    assert verify(_WAYPOINTS, short).outcome is Outcome.DIVERGENCE


@pytest.mark.parametrize("form", list(LEGACY_FORMS))
@pytest.mark.parametrize("width", [_SRE_PREFIX, _OTHERS_PREFIX, FULL_HEX])
def test_every_legacy_prefix_is_a_transition(form: str, width: int) -> None:
    """Every legacy form at 12, 16 or 64 hex is a transition naming that form, not a divergence."""
    claimed = legacy_digests(_WAYPOINTS)[form][:width]
    verdict = verify(_WAYPOINTS, claimed)
    assert (verdict.outcome, verdict.forms) == (Outcome.TRANSITION, (form,))


def test_a_foreign_hex_diverges() -> None:
    """Hex that no form explains is a divergence, and names no form."""
    verdict = verify(_WAYPOINTS, _FOREIGN)
    assert (verdict.outcome, verdict.forms) == (Outcome.DIVERGENCE, ())


@pytest.mark.parametrize("claimed", ["a" * _TOO_SHORT, "A" * _OTHERS_PREFIX, "xyz", ""])
def test_a_malformed_claim_is_malformed(claimed: str) -> None:
    """Under 12 hex, uppercase, or not hex at all is malformed rather than a divergence."""
    assert verify(_WAYPOINTS, claimed).outcome is Outcome.MALFORMED


def test_the_verdict_carries_the_current_hash() -> None:
    """Whatever the outcome, the verdict names the file's current v2 value."""
    assert verify(_WAYPOINTS, _FOREIGN).current == v2(_WAYPOINTS)
