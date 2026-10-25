# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Resolve each commitment row against durable follow-through, and keep the ledger (W1933, W44).

The extractor (`commitments`) finds what an assistant said it still had to do. This asks of each
statement the one question that matters: is there a persisted means of follow-through, and how
strong is it? The answer is the row's LAYER, the strongest persisted form of its follow-through,
from the ladder of the retrospective ritual's G9, weakest first: none, memory, instructions, card,
trigger, hook, gate.

⚑ A ROW IS COUNTED WHILE ITS FOLLOW-THROUGH IS NONE, MEMORY OR INSTRUCTIONS. A memory file or an
instruction file is prose a later session may not read; a recurring class resolved only there is a
coverability residue and stays in the metric (luthen-observability:W1599, github-8f). A card, a
trigger, a hook or a gate is something that acts or is acted on, and is not counted.

⚑ THE INFERENCE IS THE PART TO MEASURE FIRST, and it is deliberately narrow. A statement's
follow-through is read only from what it NAMES:
 - a card of THIS repository (`W12`, or `<repo>:W12` with this repository's name) that exists in
   the queue: `card` while it is open; once done, `gate` when its manifest touches the commit hook
   or a standing rule, `hook` when it touches another hook file, else `card`;
 - a memory file (`MEMORY.md`, or a path under a `memory/` directory): `memory`;
 - an instruction file (`CLAUDE.md`, the loop prompt, a skill file): `instructions`.
A cite of another repository's card is NOT resolved here: this reads one queue and cannot see
whether that card exists, so the row stays open rather than claim a follow-through it did not read.
A row naming nothing stays open until a card cites its uuid (the contract's rule).

CONSUMED BY: the `--ledger` mode and the metric emitter (W1933, next parts).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from mikemol.transcriptstruct.commitments import Commitment

LAYERS = ("none", "memory", "instructions", "card", "trigger", "hook", "gate")
COUNTED = frozenset({"none", "memory", "instructions"})
_OPEN = frozenset({"ready", "working", "blocked"})
_DONE = frozenset({"done", "landed"})
_INSTRUCTION_FILES = frozenset({"CLAUDE.md", "loop-prompt.md"})


@dataclass(frozen=True, slots=True)
class LedgerRow:
    """One commitment, its state, its layer and the follow-through that gave them."""

    commitment: Commitment
    state: str
    layer: str
    resolved_by: tuple[str, str] | None
    uncertain: bool = False
    families: tuple[str, ...] = ()


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in cast("list[object]", value) if isinstance(item, str)]


def _own_symbol(name: str, repo: str) -> str | None:
    bare = name.removeprefix(f"{repo}:")
    return bare if bare[:1] == "W" and bare[1:].isdigit() else None


def _card_layer(card: Mapping[str, object]) -> str:
    status = card.get("status")
    if status in _OPEN:
        return "card"
    if status not in _DONE:
        return "none"
    paths = _strings(card.get("manifest"))
    if any(".githooks/" in path or path.endswith("standing.rego") for path in paths):
        return "gate"
    if any("hook" in path for path in paths):
        return "hook"
    return "card"


def _file_layer(name: str) -> str:
    leaf = name.rsplit("/", 1)[-1]
    if leaf == "MEMORY.md" or "memory/" in name:
        return "memory"
    if leaf in _INSTRUCTION_FILES or "/skills/" in name:
        return "instructions"
    return "none"


def _follow_through(row: Commitment, queue: dict[str, Mapping[str, object]]) -> LedgerRow:
    best: tuple[str, tuple[str, str] | None] = ("none", None)
    for name in row.names:
        symbol = _own_symbol(name, row.repo)
        if symbol is not None and symbol in queue:
            found = (_card_layer(queue[symbol]), ("card", symbol))
        else:
            found = (_file_layer(name), ("evidence", name))
        if LAYERS.index(found[0]) > LAYERS.index(best[0]):
            best = found
    layer, by = best
    return LedgerRow(row, "open" if layer == "none" else "resolved", layer, by)


def resolve(rows: Sequence[Commitment], cards: Sequence[Mapping[str, object]]) -> list[LedgerRow]:
    """Resolve each commitment against the queue's cards and the files it names.

    Returns:
        one `LedgerRow` per commitment, in order; the layer is the strongest follow-through any
        name gave, `none` (state open) when none gave one.

    """
    queue: dict[str, Mapping[str, object]] = {}
    for card in cards:
        symbol = card.get("symbol")
        if isinstance(symbol, str):
            queue[symbol] = card
    return [_follow_through(row, queue) for row in rows]


def record(row: LedgerRow) -> dict[str, object]:
    """Render a ledger row as the contract's JSON object.

    Returns:
        repo, session, line, uuid, at, text, names, state, layer and resolved_by (null while open,
        else {kind, ref}).

    """
    said = row.commitment
    by: dict[str, str] | None = None
    if row.resolved_by is not None:
        by = {"kind": row.resolved_by[0], "ref": row.resolved_by[1]}
    out: dict[str, object] = {
        "repo": said.repo,
        "session": said.session,
        "line": said.line,
        "uuid": said.uuid,
        "at": said.at,
        "text": said.text,
        "names": list(said.names),
        "state": row.state,
        "layer": row.layer,
        "resolved_by": by,
    }
    # W1986: only a row that came from a rows file names its sources or says it was a guess.
    if row.uncertain:
        out["uncertain"] = True
    if row.families:
        out["families"] = list(row.families)
    return out


def document(as_of: str, rows: Sequence[LedgerRow]) -> dict[str, object]:
    """Build the ledger document, `commitments.json`.

    Returns:
        {as_of, rows: [record(row) ...]}.

    """
    return {"as_of": as_of, "rows": [record(row) for row in rows]}


def counted(rows: Sequence[LedgerRow]) -> dict[str, int]:
    """Count the rows the metric counts, by layer.

    Returns:
        the number of rows at each COUNTED layer that has any, an UNCERTAIN row never counted (a
        flagged guess must not inflate the debt, W1986); a sum over the values is the
        repository's open count.

    """
    tally: dict[str, int] = {}
    for row in rows:
        if row.layer in COUNTED and not row.uncertain:
            tally[row.layer] = tally.get(row.layer, 0) + 1
    return tally


def uncertain_count(rows: Sequence[LedgerRow]) -> int:
    """Count the rows flagged uncertain, which `counted` leaves out.

    Returns:
        how many of the rows are guesses the classifier was unsure of.

    """
    return sum(1 for row in rows if row.uncertain)
