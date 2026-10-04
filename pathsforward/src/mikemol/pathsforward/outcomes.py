# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W533: the declared ledger-outcome sets — which OUTCOME words a queue's tick lines may carry.

`--ledger` accepts any OUTCOME word, and atomize decides what counts as an advance with a
deny-list, so an unlisted hand-written word (`filed`) read as an advance. A queue may DECLARE its
vocabulary: `ledger_outcomes: {"advance": [...], "other": [...]}`. The field is OFF BY DEFAULT: a
queue without it behaves exactly as before, because fleet ledgers carry hundreds of distinct words
and a closed vocabulary imposed on every repo would break their ticks.

Shape: `ledger_outcomes: {advance: [word], other: [word]}`, absent when cleared (never `{}`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from mikemol.pathsforward.model import RefusedError

if TYPE_CHECKING:
    from mikemol.pathsforward.model import State

FIELD = "ledger_outcomes"
ADVANCE = "advance"
OTHER = "other"
KEYS = (ADVANCE, OTHER)
GATED_KINDS = frozenset({"tick", "interrupt"})


def _single_token(word: object) -> bool:
    """Say whether a word is a non-empty string with no whitespace.

    Returns:
        True for a single token.

    """
    return isinstance(word, str) and bool(word) and not any(ch.isspace() for ch in word)


def problems(raw: object) -> list[str]:
    """Name each way a stored field is malformed.

    Returns:
        findings; empty for a well-formed object.

    """
    if not isinstance(raw, dict):
        return [f"{FIELD} must be an object, found {type(raw).__name__}"]
    obj = cast("dict[str, object]", raw)
    found = [f"{FIELD}.{k} is not {ADVANCE} or {OTHER}" for k in obj if k not in KEYS]
    sets: dict[str, set[str]] = {}
    for key in KEYS:
        value = obj.get(key)
        if not isinstance(value, list):
            found.append(f"{FIELD}.{key} must be a list")
            continue
        words = cast("list[object]", value)
        found.extend(
            f"{FIELD}.{key} word {w!r} must be a non-empty single token"
            for w in words
            if not _single_token(w)
        )
        sets[key] = {w for w in words if isinstance(w, str)}
    if len(sets) == len(KEYS):
        both = sorted(sets[ADVANCE] & sets[OTHER])
        if both:
            found.append(f"{FIELD}: {both} are in both {ADVANCE} and {OTHER}")
    return found


def declared(state: State) -> tuple[list[str], list[str]] | None:
    """Return the declared (advance, other) sets, or None when undeclared or malformed.

    Returns:
        the two word lists, or None.

    """
    raw = state.doc.get(FIELD)
    if raw is None or problems(raw):
        return None
    obj = cast("dict[str, list[str]]", raw)
    return list(obj[ADVANCE]), list(obj[OTHER])


def _words(csv: str) -> list[str]:
    """Split a comma list, dropping blanks.

    Returns:
        the trimmed non-empty items.

    """
    return [w.strip() for w in csv.split(",") if w.strip()]


def set_sets(state: State, advance_csv: str, other_csv: str) -> None:
    """Store the declared sets.

    Raises:
        RefusedError: on a whitespace word, an empty advance set, or a word in both sets.

    """
    advance = _words(advance_csv)
    if not advance:
        msg = "the advance set must name at least one word"
        raise RefusedError(msg)
    candidate: dict[str, list[str]] = {ADVANCE: advance, OTHER: _words(other_csv)}
    bad = problems(candidate)
    if bad:
        raise RefusedError("; ".join(bad))
    state.doc[FIELD] = candidate


def clear(state: State) -> None:
    """Remove the field entirely.

    Raises:
        RefusedError: when no field is stored.

    """
    if FIELD not in state.doc:
        msg = f"no {FIELD} is declared"
        raise RefusedError(msg)
    state.doc.pop(FIELD)


def refusal(state: State, kind: str, outcome: str) -> str | None:
    """Name why a ledger line is refused, or None when it may be written.

    Returns:
        a message naming both sets, or None.

    """
    sets = declared(state)
    if sets is None or kind not in GATED_KINDS:
        return None
    advance, other = sets
    if outcome in advance or outcome in other:
        return None
    return (
        f"outcome {outcome!r} is in neither declared set for kind {kind}: "
        f"{ADVANCE}={advance} {OTHER}={other}"
    )


def findings(state: State) -> list[str]:
    """Report a malformed stored field.

    Returns:
        findings; empty when the field is absent or well-formed.

    """
    raw = state.doc.get(FIELD)
    return [] if raw is None else problems(raw)
