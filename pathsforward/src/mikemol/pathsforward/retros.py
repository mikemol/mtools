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


FLAG_FIELDS: tuple[str, ...] = ("recurring", "one_off")


def _shape_refusals(retro: Json) -> list[str]:
    # A record with no findings list never ran G7, and a key outside the schema is a misspelling.
    # `recurring` and `one_off` are booleans (nemik's record form, W2268): a string "false" is true.
    refused: list[str] = []
    if not isinstance(retro.get("findings"), list):
        refused.append("a retro has no findings list (G7 never ran); give [] only if it found none")
    known = {"id", "findings", *RETRO_FIELDS}
    unknown = sorted(key for key in retro if key not in known)
    if unknown:
        refused.append(f"unknown top-level key {', '.join(unknown)}")
    refused.extend(
        f"{key} must be true or false, not {retro[key]!r}"
        for key in FLAG_FIELDS
        if key in retro and not isinstance(retro[key], bool)
    )
    return refused


def _cause_refusals(retro: Json) -> list[str]:
    # A reviewed record (one that names its enforcement layer) carries the spec's trigger and root
    # (nemik:W982), never the host's old `cause`, and a root that only restates the trigger found
    # nothing (W1935). A scaffold has no layer yet and is judged by the shape rules alone.
    refused = [
        f"a reviewed retro has no {key} (the spec of record, nemik:W982, names trigger and root)"
        for key in ("trigger", "root")
        if not _filled(retro, key)
    ]
    trigger, root = retro.get("trigger"), retro.get("root")
    if _filled(retro, "trigger") and _filled(retro, "root") and trigger == root:
        refused.append("root equals trigger: the root names what made the trigger possible")
    return refused


BLAME_FIELDS: tuple[str, ...] = ("delta", "root")
BLAME_PHRASES: tuple[str, ...] = (
    "should have caught",
    "should have noticed",
    "should have known",
    "my mistake",
    "my fault",
    "i forgot",
    "i missed",
)


def _blame_refusals(retro: Json) -> list[str]:
    # A retro names what the system allowed, never who failed: self-reproach in `delta` or the
    # cause is the affect the ritual replaces with a gate (W2162), so each hit names field + phrase.
    refused: list[str] = []
    for field in BLAME_FIELDS:
        value = retro.get(field)
        text = value.lower() if isinstance(value, str) else ""
        refused.extend(
            f"{field} blames a person instead of naming what let it happen: {phrase!r}"
            for phrase in BLAME_PHRASES
            if phrase in text
        )
    return refused


def retro_refusals(retro: Json) -> list[str]:
    """Say what is wrong with a retro record.

    Returns:
        the refusals, empty when the record has a findings list and only schema keys, the layer
        and handoff operator are in their vocabularies, a reviewed record (one with a layer) has
        a trigger and a distinct root, no delta or cause blames a person, and every finding
        passes `finding_refusals`.

    """
    refused = _shape_refusals(retro) + _blame_refusals(retro)
    layer = retro.get("enforcement_layer")
    if layer is not None:
        refused.extend(_cause_refusals(retro))
    if layer is not None and layer not in LAYERS:
        refused.append(f"enforcement_layer {layer!r} is not one of {', '.join(LAYERS)}")
    handoff = retro.get("handoff")
    if isinstance(handoff, dict) and cast("Json", handoff).get("operator") not in OPERATORS:
        refused.append(f"handoff operator is not one of {', '.join(OPERATORS)}")
    findings = retro.get("findings")
    if isinstance(findings, list):
        refused.extend(_finding_lines(cast("list[object]", findings)))
    return refused


HANDOFF_KEYS: tuple[str, ...] = ("instrument", "channel", "operator", "self_probe")


def _copied(row: Json) -> Json:
    # The handoff values the older row ALREADY STATES, copied verbatim: from its handoff block,
    # else from a flat top-level key of the same name. A copy, never a derivation: nothing is
    # invented, and trigger, root and contributing are never touched (the operator's ruling).
    block = row.get("handoff")
    source: Json = cast("Json", block) if isinstance(block, dict) else {}
    found: Json = {}
    for key in HANDOFF_KEYS:
        value = source.get(key, row.get(key))
        if value is not None:
            found[key] = value
    return found


def _carried(row: Json) -> Json:
    # Everything the older row says, VERBATIM, so the live row of the chain keeps its trigger, root,
    # precommit, delta and findings for every reader that judges only the live row. Dropped: the
    # id (a new one is minted), the old supersedes (replaced), the handoff block and any flat
    # handoff key (both are rebuilt as the new handoff). A copy is not a derivation: nothing that
    # the older row does not state is ever invented.
    skipped = {"id", "supersedes", "handoff", *HANDOFF_KEYS}
    return {key: value for key, value in row.items() if key not in skipped}


def scaffolds(doc: Json, repo: str) -> list[tuple[str, Json, list[str]]]:
    """List a scaffold superseding row for each live retro whose handoff fails the shape (W2888).

    Replaces the in-place `cause` to `root` rename, which the operator ruled a meaning change:
    nothing here relabels a field. A live retro is one nothing supersedes.

    Returns:
        (the older id, the scaffold row, its refusals) in list order. The refusals are exactly what
        `add_retro` would raise on the row, so a scaffold with none is one `--write` adds: the
        older row's content copied verbatim, its handoff fields copied from its own values. One
        with refusals needs a reviewer, and its missing fields stay empty.

    """
    rows = _rows(doc)
    superseded = {row.get("supersedes") for row in rows}
    found: list[tuple[str, Json, list[str]]] = []
    for row in rows:
        ident = str(row.get("id"))
        block = row.get("handoff")
        shaped = isinstance(block, dict) and not handoff_refusals(cast("Json", block))
        if ident in superseded or shaped:
            continue
        scaffold: Json = {**_carried(row), "supersedes": ident, "handoff": _copied(row)}
        refused = retro_refusals(scaffold) + _supersede_refusals(doc, repo, scaffold)
        found.append((ident, scaffold, refused))
    return found


RETRO_FIELDS: tuple[str, ...] = (
    "title",
    "card",
    "trigger",
    "root",
    "contributing",
    "precommit",
    "frozen_timeline",
    "delta",
    "sustain",
    "enforcement_layer",
    "recurring",
    "one_off",
    "handoff",
    "supersedes",
)
FINDING_FIELDS: tuple[str, ...] = (
    "finding_card",
    "finding_owner",
    "due",
    "finding_witness",
    "certify_change",
)


def _present(rec: Json, key: str) -> bool:
    return key in rec and rec[key] not in (None, "", [], {})


def _finding_block(number: int, finding: Json) -> list[str]:
    lines = [f"  finding {number}:"]
    lines.extend(f"    {key}: {finding[key]}" for key in FINDING_FIELDS if _present(finding, key))
    return lines


def _retro_block(retro: Json) -> list[str]:
    lines = [str(retro.get("id", "?"))]
    lines.extend(f"  {key}: {retro[key]}" for key in RETRO_FIELDS if _present(retro, key))
    findings = retro.get("findings")
    if isinstance(findings, list):
        for number, finding in enumerate(cast("list[object]", findings), start=1):
            if isinstance(finding, dict):
                lines.extend(_finding_block(number, cast("Json", finding)))
    return lines


def _named(retro: Json, wanted: list[str]) -> bool:
    ident = str(retro.get("id", ""))
    return ident in wanted or ident.rsplit(":", 1)[-1] in wanted


def _rows(doc: Json) -> list[Json]:
    existing = doc.get("retros")
    if not isinstance(existing, list):
        return []
    return [cast("Json", row) for row in cast("list[object]", existing) if isinstance(row, dict)]


def render_full(doc: Json, wanted: list[str]) -> tuple[list[str], list[str]]:
    """Print retro records in full: the fields and every finding with its card, owner and witness.

    ⚑ `--export` carries no retros and `--render` prints a summary line, so a reviewer re-spawned
    from the queue (the reviewed-loop skill) had no way to read a record back (W2088).

    Returns:
        the lines, and the wanted ids no retro carries. A wanted id is `<repo>:R<n>` or `R<n>`;
        none wanted means every retro.

    """
    rows = _rows(doc)
    chosen = [row for row in rows if _named(row, wanted)] if wanted else rows
    unknown = [one for one in wanted if not any(_named(row, [one]) for row in rows)]
    return [line for row in chosen for line in _retro_block(row)], unknown


SELF_PROBE = "executed-and-failed"


def handoff_refusals(handoff: Json) -> list[str]:
    """Say what is wrong with a handoff block, by the shape nemik pins (nemik:W2488).

    The shared fixture `tests/corpus/retro-handoff-blocks.json` holds the cases both sides test.

    Returns:
        the refusals, empty when the block has a non-empty instrument and channel, an operator of
        `self` or `other`, and, for `other`, a self_probe of exactly `executed-and-failed`; a
        self_probe on a `self` block is ignored.

    """
    refused = [
        f"handoff has no {key}" for key in ("instrument", "channel") if not _filled(handoff, key)
    ]
    operator = handoff.get("operator")
    if operator not in OPERATORS:
        refused.append(f"handoff operator is not one of {', '.join(OPERATORS)}")
    elif operator == "other" and handoff.get("self_probe") != SELF_PROBE:
        refused.append(f"handoff operator other needs self_probe {SELF_PROBE!r}")
    return refused


def _supersede_refusals(doc: Json, repo: str, retro: Json) -> list[str]:
    # A superseding row names an older retro of THIS repository that nothing has superseded yet, so
    # a chain has one live row (nemik:W2478), and it carries the COMPLETE handoff the older row
    # lacked. The older row is never touched: supersession adds a row, it does not relabel one
    # (the operator's ruling on the in-place cause-to-root rename).
    if "supersedes" not in retro:
        return []
    target = retro["supersedes"]
    if not isinstance(target, str) or not target.startswith(f"{repo}:R"):
        return [f"supersedes {target!r} is not a retro id of {repo}"]
    rows = _rows(doc)
    if target not in {str(row.get("id")) for row in rows}:
        return [f"supersedes {target}: no such retro"]
    taken = [str(row.get("id")) for row in rows if row.get("supersedes") == target]
    if taken:
        return [f"supersedes {target}: already superseded by {taken[0]}"]
    handoff = retro.get("handoff")
    if not isinstance(handoff, dict):
        return ["a superseding row has no handoff block"]
    return handoff_refusals(cast("Json", handoff))


def add_retro(doc: Json, repo: str, retro: Json) -> str:
    """Mint the next retro id and append the record, or refuse it.

    Returns:
        the new id, `<repo>:R<n>`.

    Raises:
        ValueError: when the record fails `retro_refusals` or names a retro it may not supersede;
            nothing is changed then.

    """
    refused = retro_refusals(retro) + _supersede_refusals(doc, repo, retro)
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
