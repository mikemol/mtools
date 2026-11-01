# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The Codon idiom census as OTLP gauge rows for `mikemol-otlp metrics`, one batch per repo (W1366).

    {"name": "mikemol.codon.idiom_modules", "value": 3, "fields": {"target": "...", "rule": "..."},
     "description": "...", "unit": "{module}", "time_ns": 1700000000000000000}

⚑ THE TEXTFILE FORM STAYS (`websubset_prom`, W1350) until luthen no longer reads textfiles. This is
the same four series as OTel gauges: dotted names under `mikemol.codon.`, the REPOSITORY as the
batch's `service.namespace` (so it is not repeated as a label), and `target` and `rule` as the
datapoint attributes. The service name for the batch is `mikemol-websubset`.

⚑ A BATCH IS ONE REPOSITORY'S, BECAUSE THE NAMESPACE IS A PER-INVOCATION FACT of `mikemol-otlp
metrics`: the caller runs it once per key of the returned mapping. The rows carry the time the
census was taken, not the arrival time at the store.

⚑ NO FRESHNESS CLASS IS DECLARED YET. luthen's registry wants a census run on demand to be
`event_driven` with a companion continuous series and a reason, and no continuous source exists for
it; naming a companion that nothing emits would be a false declaration. The rows leave the field
absent, which `mikemol-otlp` accepts as "not declared", and the choice is luthen's (carded).

This module is pure: it builds rows and sends nothing; the CLI wiring calls `mikemol-otlp`.
"""

import json
from collections.abc import Sequence

from mikemol.hooks import websubset
from mikemol.hooks.websubset_tree import TreeCensus

PREFIX = "mikemol.codon"
SERVICE = "mikemol-websubset"
_FAMILIES = {
    "modules": ("src modules read", "{module}"),
    "clean_modules": ("src modules with no finding under the target", "{module}"),
    "idiom_modules": ("modules the rule blocks", "{module}"),
    "idiom_sites": ("sites of the rule across all modules", "{site}"),
}


def _row(name: str, value: int, fields: dict[str, str], now_ns: int) -> str:
    description, unit = _FAMILIES[name]
    row = {
        "name": f"{PREFIX}.{name}",
        "value": value,
        "fields": fields,
        "description": description,
        "unit": unit,
        "time_ns": now_ns,
    }
    return json.dumps(row, sort_keys=True)


def _reach(found: TreeCensus, rule: str) -> tuple[int, int]:
    for count in found.rules:
        if count.rule == rule:
            return count.modules, count.sites
    return 0, 0


def batches(counted: Sequence[tuple[str, TreeCensus]], now_ns: int) -> dict[str, list[str]]:
    """Build one batch of gauge rows per repository.

    ⚑ EVERY RULE OF THE TARGET IS WRITTEN, 0 INCLUDED, as the textfile does, so the last module
    leaving a rule shows as a step to 0 and not as a series that stopped.

    Returns:
        repository name to its JSON rows, in census order; a repository seen twice has its rows
        appended in order.

    """
    out: dict[str, list[str]] = {}
    for repo, found in counted:
        rows = out.setdefault(repo, [])
        base = {"target": found.target}
        rows.append(_row("modules", found.total, base, now_ns))
        rows.append(_row("clean_modules", found.clean, base, now_ns))
        for rule in sorted(websubset.RULES[found.target]):
            modules, sites = _reach(found, rule)
            rows.append(_row("idiom_modules", modules, {**base, "rule": rule}, now_ns))
            rows.append(_row("idiom_sites", sites, {**base, "rule": rule}, now_ns))
    return out
