# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The retro record: a node beside the waypoints, not a field on a card (W1918, nemik:W982).

A retrospective (the retrospective-ritual skill's ten gates) is its own node. The queue document
carries a `retros` list beside `waypoints` and a `retro_counter` that only rises; a retro's id is
`<repo>:R<n>`. The spelling of every field was settled with nemik on 2026-10-24 (nemik:W982).

⚑ A FINDING IS ONE OF TWO THINGS (G7): a card-finding, `finding_card` with `finding_owner`, `due`
and `finding_witness`, or `certify_change` alone, a verdict change that running something
demonstrates. A finding with neither is the theater the ritual exists to end, and one with a card
but no owner, due date or witness is an intention, not a commitment; both are refused.

⚑ THE ACTION CARD LINKS BACK BY `caused_by` = THE RETRO ID, a field cards already carry, so the link
is checkable from either side and the card gains no owner or due field.

⚑ AN ABSENT LIST IS EMPTY, AN ABSENT COUNTER IS 0: an older document needs no migration.
"""

from typing import cast

from mikemol.pathsforward.model import Json

LAYERS: tuple[str, ...] = ("memory", "instructions", "trigger", "hook", "gate")
OPERATORS: tuple[str, ...] = ("self", "other")
CARD_FINDING_FIELDS: tuple[str, ...] = ("finding_owner", "due", "finding_witness")


def _filled(rec: Json, key: str) -> bool:
    value = rec.get(key)
    return isinstance(value, str) and bool(value.strip())


def finding_refusals(finding: Json) -> list[str]:
    """Say what is wrong with one finding.

    Returns:
        the refusals, empty when the finding is a card-finding with its owner, due date and
        witness, or a `certify_change` alone.

    """
    if _filled(finding, "certify_change") and not _filled(finding, "finding_card"):
        return []
    if not _filled(finding, "finding_card"):
        return ["a finding names neither a finding_card nor a certify_change"]
    return [
        f"a card-finding has no {key}" for key in CARD_FINDING_FIELDS if not _filled(finding, key)
    ]


def _finding_lines(findings: list[object]) -> list[str]:
    refused: list[str] = []
    for number, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict):
            refused.append(f"finding {number} is not an object")
            continue
        why = finding_refusals(cast("Json", finding))
        refused.extend(f"finding {number}: {line}" for line in why)
    return refused


def retro_refusals(retro: Json) -> list[str]:
    """Say what is wrong with a retro record.

    Returns:
        the refusals, empty when the layer and handoff operator are in their vocabularies and
        every finding passes `finding_refusals`.

    """
    refused: list[str] = []
    layer = retro.get("enforcement_layer")
    if layer is not None and layer not in LAYERS:
        refused.append(f"enforcement_layer {layer!r} is not one of {', '.join(LAYERS)}")
    handoff = retro.get("handoff")
    if isinstance(handoff, dict) and cast("Json", handoff).get("operator") not in OPERATORS:
        refused.append(f"handoff operator is not one of {', '.join(OPERATORS)}")
    findings = retro.get("findings")
    if isinstance(findings, list):
        refused.extend(_finding_lines(cast("list[object]", findings)))
    return refused


UNSPLIT = "unsplit"


def _migrated(retro: Json) -> Json | None:
    """Rewrite one host-schema retro (`cause`, no `root`) into the spec schema.

    Returns:
        the rewritten record, or None when it needs no change: it already has a `root`, or it has
        no `cause` to rename. `cause` becomes `root` and an absent or blank `trigger` becomes
        `unsplit`, the honest word for a record whose cause was never split from its trigger.

    """
    if "cause" not in retro or _filled(retro, "root"):
        return None
    record: Json = {key: value for key, value in retro.items() if key != "cause"}
    record["root"] = retro["cause"]
    if not _filled(record, "trigger"):
        record["trigger"] = UNSPLIT
    return record


def migrate(doc: Json) -> list[str]:
    """Rename `cause` to `root` on every retro that carries the host schema (W2091).

    ⚑ ONLY THE TWO FIELDS MOVE: ids, the counter, findings and every other field are untouched, and
    a record already in the spec schema is left byte for byte, so a second run changes nothing.

    Returns:
        the ids of the retros that changed, in list order; empty when none did.

    """
    existing = doc.get("retros")
    if not isinstance(existing, list):
        return []
    changed: list[str] = []
    rewritten: list[object] = []
    for item in cast("list[object]", existing):
        record = _migrated(cast("Json", item)) if isinstance(item, dict) else None
        if record is None:
            rewritten.append(item)
            continue
        rewritten.append(record)
        changed.append(str(record.get("id", "?")))
    if changed:
        doc["retros"] = rewritten
    return changed


def add_retro(doc: Json, repo: str, retro: Json) -> str:
    """Mint the next retro id and append the record, or refuse it.

    Returns:
        the new id, `<repo>:R<n>`.

    Raises:
        ValueError: when the record fails `retro_refusals`; nothing is changed then.

    """
    refused = retro_refusals(retro)
    if refused:
        raise ValueError("; ".join(refused))
    counter = doc.get("retro_counter")
    number = (counter if isinstance(counter, int) and not isinstance(counter, bool) else 0) + 1
    ident = f"{repo}:R{number}"
    existing = doc.get("retros")
    retros: list[object] = []
    if isinstance(existing, list):
        retros = list(cast("list[object]", existing))
    record: Json = {**retro, "id": ident}
    doc["retros"] = [*retros, record]
    doc["retro_counter"] = number
    return ident
