# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The file's consistency check: every mechanically checkable charter property, reported.

⚑⚑ gabion's check, whole, with el-openglo's reasonless-drop arm. The survey measured
el-openglo's `--check` passing a state with a duplicate live `W1` and a `W999` above counter=24;
gabion's caught both. Each property is its own function so a failure names itself.

⚑ IT REPORTS AND DOES NOT REPAIR (D8, pending the operator). A live file missing `W17` is a
finding for its owner, not something this tool grandfathers by writing residue on their behalf.

⚑ `status=dropped` IS A FINDING (D5, pending the operator): dropping means moving to residue with
a reason, which `--drop` does. The finding says so rather than reading as an unknown status.

⚑ THE EVIDENCE READ IS OPT-IN. `evidence_findings` stats every absolute path a waypoint's
evidence names (skill section 7.8); it touches the filesystem once per path, so it runs only
under `--check-evidence`, never as the bare check.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pathsforward.model import BLOCKED_KINDS, STATUSES, strlist, symbol_number, text

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json, State

_DROPPED = "dropped"
_PATH_TRIM = ",;:()[]'\"`"
# ⚑ A BAZEL LABEL IS NOT A PATH: `//pkg:f`, `@repo//pkg:f`, `@@//pkg:f`. summit's W37 evidence
# names `//paperkit:components.bzl`, which `--check-evidence` reported missing.
_LABEL = re.compile(r"@{0,2}[\w.~+-]*//")


def _claimed(state: State) -> list[str]:
    """List every symbol a record claims, live first, in file order.

    Returns:
        the symbols.

    """
    return [text(rec, "symbol") for rec in (*state.waypoints, *state.residue)]


def coverage(state: State) -> list[str]:
    """Charter gate *coverable*: W1..W<counter> each resolve to a live or residue record.

    Returns:
        one finding per issued symbol that resolves to nothing.

    """
    claimed = set(_claimed(state))
    return [
        f"W{n}: issued (counter={state.counter}) but in neither waypoints nor residue"
        for n in range(1, state.counter + 1)
        if f"W{n}" not in claimed
    ]


def duplicates(state: State) -> list[str]:
    """Report a symbol claimed by more than one record, live or residue.

    Returns:
        one finding per symbol claimed twice or more.

    """
    counts = Counter(_claimed(state))
    return [f"{sym}: claimed {n} times" for sym, n in sorted(counts.items()) if n > 1]


def historical(rec: Json) -> bool:
    """Say whether a residue record is an admitted historical name: not `W<n>`, with a reason.

    ⚑ OPERATOR RULING: summit's `W50b` was issued by a tick that broke the integer rule. It is
    admitted in residue ONLY, and only with a reason, so a stale reference resolves to "W50b,
    residue, here's why". It is never counted against `counter` (it has no number).

    Returns:
        True for a non-`W<n>` symbol whose `reason` is non-blank.

    """
    return symbol_number(text(rec, "symbol")) is None and bool(text(rec, "reason").strip())


def malformed(state: State) -> list[str]:
    """Report a symbol that is not `W<n>` — refused, never `int()`-ed into a crash.

    A historical name in residue with a reason is admitted; live, or reasonless, it is refused.

    Returns:
        one finding per malformed symbol.

    """
    live = [text(w, "symbol") for w in state.waypoints]
    dead = [text(r, "symbol") for r in state.residue if not historical(r)]
    return [f"{sym!r}: not a W<n> symbol" for sym in (*live, *dead) if symbol_number(sym) is None]


def above_counter(state: State) -> list[str]:
    """Report a symbol numbered above `counter`, which no mint could have issued.

    Returns:
        one finding per such symbol.

    """
    return [
        f"{sym}: above counter={state.counter}"
        for sym in _claimed(state)
        if (symbol_number(sym) or 0) > state.counter
    ]


def reasons(state: State) -> list[str]:
    """Report a residue entry with no reason: dropping is a recorded judgement.

    Returns:
        one finding per reasonless residue entry.

    """
    return [
        f"{text(rec, 'symbol')}: residue without a reason"
        for rec in state.residue
        if not text(rec, "reason").strip()
    ]


def edges(state: State) -> list[str]:
    """Report an `enables` or `blocked_on` target that looks like a symbol and resolves nowhere.

    Returns:
        one finding per dangling edge.

    """
    claimed = set(_claimed(state))
    return [
        f"{text(w, 'symbol')} -> {target}: dangling edge"
        for w in state.waypoints
        for target in (*strlist(w, "enables"), *strlist(w, "blocked_on"))
        if symbol_number(target) is not None and target not in claimed
    ]


def statuses(state: State) -> list[str]:
    """Report a live waypoint whose status is outside the enum.

    Returns:
        one finding per bad status; `dropped` names the residue move instead.

    """
    found: list[str] = []
    for w in state.waypoints:
        status = text(w, "status")
        if status == _DROPPED:
            found.append(f"{text(w, 'symbol')}: status=dropped in the live list; "
                         "use --drop to move it to residue with a reason (D5)")
        elif status not in STATUSES:
            found.append(f"{text(w, 'symbol')}: invalid status {status!r}")
    return found


def blocked(state: State) -> list[str]:
    """Report a blocked waypoint that does not say on whom, or of what kind.

    Returns:
        one finding per under-specified block.

    """
    return [
        f"{text(w, 'symbol')}: blocked without blocked_on and an agent|human blocked_kind"
        for w in state.waypoints
        if text(w, "status") == "blocked"
        and (not strlist(w, "blocked_on") or text(w, "blocked_kind") not in BLOCKED_KINDS)
    ]


def field_types(state: State) -> list[str]:
    """Report a list field stored as something other than a list.

    Returns:
        one finding per mistyped list field.

    """
    return [
        f"{text(w, 'symbol')}: {key} is {type(w.get(key)).__name__}, not a list"
        for w in state.waypoints
        for key in ("blocked_on", "enables", "touches")
        if key in w and not isinstance(w.get(key), list)
    ]


def root(state: State) -> list[str]:
    """Report a `project_root` that is not an absolute, existing directory.

    Returns:
        [] or one finding.

    """
    value = text(state.doc, "project_root")
    path = Path(value)
    if value and path.is_absolute() and path.is_dir():
        return []
    return [f"project_root {value!r}: not an absolute existing directory"]


def check(state: State) -> list[str]:
    """Run every property.

    Returns:
        every finding, grouped by property in a fixed order.

    """
    return [
        *coverage(state), *duplicates(state), *malformed(state), *above_counter(state),
        *reasons(state), *edges(state), *statuses(state), *blocked(state),
        *field_types(state), *root(state),
    ]


def _absolute_paths(rec: Json) -> list[str]:
    """Pick the absolute-path tokens out of a record's evidence; a bazel label is not one.

    Returns:
        the tokens, trimmed of surrounding punctuation.

    """
    tokens = (token.strip(_PATH_TRIM) for token in text(rec, "evidence").split())
    return [token for token in tokens if token.startswith("/") and not _LABEL.match(token)]


def evidence_findings(state: State) -> list[str]:
    """Report an absolute path named in evidence that does not exist (opt-in: it stats files).

    Returns:
        one finding per missing path.

    """
    return [
        f"{text(w, 'symbol')}: evidence names {path}, which does not exist"
        for w in state.waypoints
        for path in _absolute_paths(w)
        if not Path(path).exists()
    ]
