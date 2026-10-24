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
