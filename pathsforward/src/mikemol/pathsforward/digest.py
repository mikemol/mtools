# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The waypoints hash: one tagged scheme emitted, four legacy byte-forms still accepted.

⚑⚑ OPERATOR RULING D1. `v2:` is sha256 over `waypoints` serialised with `sort_keys=True`,
compact separators and `ensure_ascii=True`, first 16 hex digits. The survey measured six tools
occupying all four cells of a 2x2 grid (separators x ensure_ascii), so an untagged value from an
armed payload may be any of them, at 12 (sre) or 16 characters.

⚑ A LEGACY VALUE IS A TRANSITION, NOT A DIVERGENCE. An untagged hex value of 12 or more digits
that PREFIXES any legacy form's full digest is accepted and reported with the form(s) it matched;
the ledger records the transition. Only a value no form explains is a divergence, and then the
file wins (skill section 4.2).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json

TAG = "v2:"
V2_HEX = 16
LEGACY_MIN_HEX = 12
FULL_HEX = 64

_DEFAULT = (", ", ": ")
_COMPACT = (",", ":")

# name -> (separators, ensure_ascii); the order is the order a multi-match is reported in.
LEGACY_FORMS: dict[str, tuple[tuple[str, str], bool]] = {
    "D/A": (_DEFAULT, True),
    "D/U": (_DEFAULT, False),
    "C/A": (_COMPACT, True),
    "C/U": (_COMPACT, False),
}

_LEGACY = re.compile(f"[0-9a-f]{{{LEGACY_MIN_HEX},{FULL_HEX}}}")


class Outcome(StrEnum):
    """What a claimed hash says about the file."""

    MATCH = "match"
    TRANSITION = "transition"
    DIVERGENCE = "divergence"
    MALFORMED = "malformed"


@dataclass(frozen=True)
class Verdict:
    """The outcome of comparing a claimed hash with the file's waypoints."""

    outcome: Outcome
    current: str
    forms: tuple[str, ...] = ()


def _full(waypoints: list[Json], separators: tuple[str, str], *, ensure_ascii: bool) -> str:
    """Hash one byte-form in full.

    Returns:
        the 64-hex sha256 of the serialised waypoints.

    """
    blob = json.dumps(waypoints, sort_keys=True, separators=separators, ensure_ascii=ensure_ascii)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def v2(waypoints: list[Json]) -> str:
    """Compute the canonical tagged hash.

    Returns:
        `v2:` followed by 16 hex digits.

    """
    return TAG + _full(waypoints, _COMPACT, ensure_ascii=True)[:V2_HEX]


def legacy_digests(waypoints: list[Json]) -> dict[str, str]:
    """Compute every legacy form in full.

    Returns:
        form name -> 64-hex digest.

    """
    return {
        name: _full(waypoints, seps, ensure_ascii=ascii_only)
        for name, (seps, ascii_only) in LEGACY_FORMS.items()
    }


def verify(waypoints: list[Json], claimed: str) -> Verdict:
    """Compare a payload's claimed hash with the file.

    Returns:
        MATCH for an exact `v2:` value; TRANSITION, naming the forms, for an untagged value that
        prefixes a legacy digest; MALFORMED for an untagged value that is not 12-64 lowercase hex;
        DIVERGENCE otherwise.

    """
    current = v2(waypoints)
    if claimed.startswith(TAG):
        return Verdict(Outcome.MATCH if claimed == current else Outcome.DIVERGENCE, current)
    if not _LEGACY.fullmatch(claimed):
        return Verdict(Outcome.MALFORMED, current)
    forms = tuple(
        name for name, full in legacy_digests(waypoints).items() if full.startswith(claimed)
    )
    return Verdict(Outcome.TRANSITION if forms else Outcome.DIVERGENCE, current, forms)
