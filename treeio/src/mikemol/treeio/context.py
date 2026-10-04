# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The three invocation-wide variables: intent, tenant and the snapshot record.

Ported from paperkit's `tools/edit_snapshot.py`. Intent is transmitted as a context variable, not
as a parameter (operator, 2026-08-26): if a caller's `intent=` is assumed correct, something else
will stuff something in there thinking it means something else. Snapshot state is a per-invocation
RECORD, and the tenant is the third variable and the worst of the three, because its failure is
invisible: a wrong intent either writes or refuses, observable either way, while a wrong tenant
returns PLAUSIBLE ROWS NOBODY CAN DISTINGUISH.

The measured tenant incident was not "someone passed the wrong flag". One report opened a stale
local database for coverage while another read the live store, so two stores sat in one report;
the live relations do not exist in the stale file, every probe returned nothing, a handler
swallowed the error, and the relations defaulted to candidates. NOBODY STUFFED A WRONG VALUE IN:
two functions each resolved the tenant independently and disagreed, which is the argument for a
single ambient resolver in its sharpest form.

WHY A ContextVar AND NOT A MODULE GLOBAL. A global is per-PROCESS and per-CALL to reset; a
ContextVar is per-INVOCATION and unwinds with the scope that set it. That difference is exactly the
bug the snapshot record dissolves: twenty-three tools each kept a module-level latch that armed on
file one and did nothing after, which is right for the whole-worktree stash and WRONG for the
per-path copy of untracked files, so files two to N were never copied aside. A latch can only say
"once"; the state wanted to say "once for the stash, accumulating for the copies".

THE ADMISSION RULE FOR A FOURTH VARIABLE. Three variables is where this stops being three fixes and
becomes an architecture, and an architecture without an admission rule grows a fifth member because
the pattern was there. A value BELONGS in this context if and only if ALL FOUR hold:

    1. It is a property of the INVOCATION, not of a call: decided once, where the operator's
       request is read, and the same fact for every frame below. A per-file path does not qualify.
    2. A callee CANNOT AUTHENTICATE it as a parameter: it has no way to tell a correct value from a
       wrong one. If the callee can check it, check it; do not make it ambient.
    3. A wrong value is SILENT or near-silent. A value whose wrongness throws, or shows in the
       output, does not need this and should not pay its cost.
    4. It has a CLOSED, SMALL vocabulary, because refuse-on-disagreement needs equality to be
       meaningful. A path, a count or a connection object cannot be compared this way.

And the disqualifier, which is not merely the negation: a value a caller may LEGITIMATELY VARY
MID-INVOCATION does not belong, since every change would be a false refusal and a guard that fires
on correct behaviour trains everyone to route around it. The snapshot record sits at the edge of
this and is admitted only because it is a RECORD rather than a compared value, so it has no
`resolve`.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass, field

from mikemol.treeio.ambient import Ambient, AmbientConflictError, Tokens

INTENT = Ambient(
    "intent",
    ("apply", "dry-run"),
    "These are two different propositions spelled the same way — 'what the operator asked for'"
    "\n  and 'what this branch actually does'.",
)
"""What this invocation is doing to the filesystem: apply or dry-run.

Bound ONCE, at the point where the operator's statement is read, and read everywhere below it. A
callee that wants to know the intent ASKS THE CONTEXT rather than accepting a parameter it cannot
authenticate. The two readings are named in the refusal so a reader sees WHY two values differ and
not only THAT they do."""

TENANT = Ambient(
    "tenant",
    ("live", "sandbox"),
    "A read against the wrong tenant returns plausible rows nobody can distinguish; two"
    "\n  independent resolutions in one process is how one report read two stores.",
)
"""Which store this invocation reads: live or sandbox.

The refusal is unconditional and env-independent; an earlier environment switch for it no longer
exists, so there is nothing here to duplicate and nothing to defer to."""

IntentConflict = AmbientConflictError
"""Paperkit's earlier name for the conflict, from before the tenant variable forced the mechanism
to be named for its shape rather than its first member."""


@dataclass
class SnapshotState:
    """The per-invocation snapshot record: the stash sha, the copied set, and the first label.

    SPLITTING THE STATE BY KIND IS WHAT FIXES THE LATCH. The sha is taken once, because the stash
    is whole-worktree and taking it twice is waste. The copied set GROWS, because the untracked
    copy is per-path. A record can express that difference; a latch cannot.
    """

    sha: str | None
    label: str
    copied: set[str] = field(default_factory=set)


SNAPSHOT_STATE = contextvars.ContextVar[SnapshotState | None](
    "substrate_edit_snapshot_state", default=None
)
"""The snapshot record of this invocation, or None before anything has snapshotted."""


def bind_intent(value: str, origin: str) -> Tokens:
    """Bind the intent and its origin; a name that reads well at the call sites.

    Returns:
        The tokens of the two writes.

    """
    return INTENT.set(value, origin)


def resolve_intent(label: str, stated: str | None = None) -> str | None:
    """Resolve the intent: THE intent resolver, a thin spelling of `INTENT.resolve`.

    Unlike paperkit's version this takes no argv: the parameter was accepted and never read.

    Returns:
        The intent bound for this invocation, or None when none is bound and none stated.

    """
    return INTENT.resolve(label, stated)


def naming_tenant(value: str, label: str) -> str:
    """Bind the tenant for this invocation, and return the string a RESULT should carry.

    NAMING THE TENANT IN THE OUTPUT IS HALF THE FIX, NOT A NICETY: one resolver, and name the
    tenant in the output. A read whose verdict does not carry which store answered it is
    UNVERIFIABLE AFTER THE FACT, and a well-formed figure arriving without its scope is a repeated
    instance. So the binder RETURNS the label, and a caller that prints a result has the string in
    hand at the moment it prints it.

    Returns:
        The label, of the form [tenant=live].

    """
    TENANT.resolve(label, stated=value)
    return f"[tenant={value}]"


def sanctioned_setters() -> dict[tuple[str, str], str]:
    """List the call sites permitted to BIND an ambient: the census a gate would ratchet.

    The honest form of the unforgeability gap. Since `set` cannot be prevented, the next best
    thing is that every sanctioned binding is enumerable, so a NEW one is a new key and refusable.
    It is returned as data rather than prose so a gate can consume it without re-deriving the list.

    Returns:
        A map from the variable name and the binding function to what that binding is for.

    """
    return {
        ("intent", "require_explicit_mutation"): "reads the operator's argv statement",
        ("intent", "resolve_intent"): "binds a stated intent when none is ambient",
        ("tenant", "naming_tenant"): "binds the tenant and returns the result's label",
        ("snapshot", "snapshot_once"): "per-invocation snapshot record",
        ("snapshot", "snapshot"): "establishes the record for a direct guard() caller",
    }
