# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The waypoint fields the realizability policy reads, checked and shaped (W849).

⚑⚑ FORM ONLY, NEVER TRUTH (the charter, W848). This module refuses a malformed field before it is
stored and says nothing about whether a population is really finite or a command really exists:
the Rego policy reads what is declared, and an ABSENT field means "not declared", which the
policy reads as residue and never as clean.

⚑ DEFERRAL YES, WAIVER NO. A deferred gate is a record that it is not yet closed, with the arm it
was judged against and what would close it. There is no field that marks a gate waived, and the
policy treats any such key as a violation.
"""

from __future__ import annotations

from mikemol.pathsforward.model import RefusedError, is_reference

GATES: tuple[str, ...] = ("constructible", "reachable", "observable", "coverable")
UNBOUNDED = "unbounded"

# A deferred entry is `gate|reference_arm|what|closes_by` and may carry a fifth `closes_ref`.
_SEP = "|"
_MIN_PARTS = 4
_MAX_PARTS = 5
_REF_PART = 4
# `--population SOURCE` alone, or `--population SOURCE BOUND`.
_POPULATION_MIN = 1
_POPULATION_MAX = 2


def one_line(name: str, value: str) -> str:
    """Refuse a blank or multi-line value; these fields are one-line names.

    Returns:
        the value unchanged.

    Raises:
        RefusedError: on a blank value or one carrying a line break.

    """
    if not value.strip():
        msg = f"{name} is empty"
        raise RefusedError(msg)
    if "\n" in value or "\r" in value:
        msg = f"{name} {value!r} is not a single line"
        raise RefusedError(msg)
    return value


def population(args: tuple[str, ...]) -> dict[str, object] | None:
    """Shape `--population SOURCE [BOUND]` as {source, bound}.

    ⚑ `bound` IS AN INTEGER OR null: null (spelled `unbounded`, or omitted) means the population is
    not finite, which the policy reads as residue at `coverable`. Nothing here decides which.

    Returns:
        the record, or None for a bare flag (which clears the field).

    Raises:
        RefusedError: on more than two values, a blank source, or a bound that is not a
            non-negative integer or `unbounded`.

    """
    if not args:
        return None
    if not _POPULATION_MIN <= len(args) <= _POPULATION_MAX:
        msg = "population takes a SOURCE and optionally a BOUND (an integer or 'unbounded')"
        raise RefusedError(msg)
    source = one_line("population source", args[0])
    raw = args[1] if len(args) > 1 else UNBOUNDED
    if raw == UNBOUNDED:
        return {"source": source, "bound": None}
    if not raw.isdecimal():
        msg = f"population bound {raw!r} is not a non-negative integer or {UNBOUNDED!r}"
        raise RefusedError(msg)
    return {"source": source, "bound": int(raw)}


def deferred(items: tuple[str, ...]) -> list[dict[str, str]]:
    """Shape each `gate|reference_arm|what|closes_by[|closes_ref]` into a deferred entry.

    ⚑ THE WHOLE LIST IS STATED, like `--enables`: an entry left out is no longer deferred, which
    is the only way a deferral ends, so it is a visible edit and never a silent one.

    Returns:
        the entries, in the order given.

    """
    return [_entry(item) for item in items]


def _entry(item: str) -> dict[str, str]:
    """Shape one deferred entry.

    Returns:
        the entry, with `closes_ref` only when given.

    Raises:
        RefusedError: on a wrong field count, an unknown gate, a blank field or a bad reference.

    """
    parts = item.split(_SEP)
    if not _MIN_PARTS <= len(parts) <= _MAX_PARTS:
        msg = f"deferred {item!r} is not gate|reference_arm|what|closes_by[|closes_ref]"
        raise RefusedError(msg)
    gate, arm, what, closes_by, *ref = (part.strip() for part in parts)
    if gate not in GATES:
        msg = f"deferred gate {gate!r} is not one of {', '.join(GATES)}"
        raise RefusedError(msg)
    entry = {
        "gate": gate,
        "reference_arm": one_line("deferred reference_arm", arm),
        "what": one_line("deferred what", what),
        "closes_by": one_line("deferred closes_by", closes_by),
    }
    if len(parts) > _REF_PART:
        if not is_reference(ref[0]):
            msg = f"deferred closes_ref {ref[0]!r} is not W<n> or repo:W<n>"
            raise RefusedError(msg)
        entry["closes_ref"] = ref[0]
    return entry
