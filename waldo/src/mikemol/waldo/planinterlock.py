# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Evaluate an activation's preconditions as Rego over live facts (W1847).

Ported from luthen's `checks/interlock.py`, behind `PlanConfig` and `Tools`.

`<policy>/interlocks/<kind>.rego` declares `defer`: a set of messages, one per unmet precondition.
`defer` asks the pinned opa for that set over the facts and returns the sorted messages, empty
meaning every precondition holds.

⚑ COULD-NOT-ASK IS NOT MET: None means the question could not be asked (no opa, an opa that is not
the pinned version, a kind that is not an identifier, an evaluation error), and a caller treats it
as DEFERRED too. An interlock that cannot be evaluated has not been met.

⚑ A GATE IN FRONT OF THE PIPELINE, NOT A STEP IN IT: the consumer asks `defer` before it plans or
applies; the in-pipeline ordering is `planprecond`. The package and directory come from
`PlanConfig.interlock_query` and `interlocks`, so nothing here names luthen.
"""

import hashlib
import json

from mikemol.waldo.planconfig import PlanConfig
from mikemol.waldo.planjson import Json, as_list, as_object, list_at, parse_object
from mikemol.waldo.planopa import pinned_opa
from mikemol.waldo.plantools import Tools


def defer(
    tools: Tools, config: PlanConfig, kind: str, facts: dict[str, object]
) -> list[str] | None:
    """Ask which preconditions of `kind` are unmet over `facts`.

    Returns:
        the sorted unmet-precondition messages, or None when it could not be evaluated.

    """
    opa = pinned_opa(tools, config.opa_pin)
    if opa is None or not kind.isidentifier():
        return None
    query = config.interlock_query(kind)
    args = ("eval", "-f", "json", "-d", str(config.interlocks()), "-I", query)
    done = tools.run(opa, *args, stdin_text=json.dumps(facts))
    results = list_at(parse_object(done.stdout or ""), "result")
    exprs = list_at(as_object(results[0]), "expressions") if results else []
    value = as_object(exprs[0]).get("value") if exprs else None
    if not isinstance(value, list):
        return None
    return sorted(str(m) for m in as_list(value))


def ledger_field(kind: str, facts: dict[str, object], messages: list[str] | None) -> Json:
    """Spell one interlock gate as the field its apply's ledger entry carries (W1867).

    The consumer returns it from `Seams.run_fields`, so an interlock is recorded beside the apply
    it gated instead of living only in the caller's output. The facts are HASHED, never echoed:
    they are live readings and may name things a ledger should not hold, and the hash still says
    which readings the gate saw.

    Returns:
        `{"interlock": {kind, facts_sha256, defer, met}}`; `defer` is None and `met` False when
        the question could not be asked, since an interlock that could not be evaluated has not
        been met.

    """
    digest = hashlib.sha256(json.dumps(facts, sort_keys=True).encode("utf-8")).hexdigest()
    recorded: Json = {
        "kind": kind,
        "facts_sha256": digest,
        "defer": messages,
        "met": messages == [],
    }
    return {"interlock": recorded}
