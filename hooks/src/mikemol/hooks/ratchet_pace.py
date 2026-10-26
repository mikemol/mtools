# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read nemik's ratchet pace file and say which ratchets this repository still owes (W1920).

nemik writes one verdict row per ratchet to `ratchet-pace.json` (nemik:W997): a head line carrying
`as_of` and `window`, then one flat object per line with `repo`, `ratchet`, `state`, `observed` and
`required`, the numbers as quoted text. This module READS it and never recomputes it (the fact is
nemik's, W990). A repository whose ratchet is `behind` owes paydown, and the commit gate may refuse
a commit that lowers none (the wiring is a later step of W1920).

⚑ AN UNSATISFIABLE REQUIREMENT IS IGNORED (github-8f 2026-10-26, nemik:W1105): a ratchet whose
required fall exceeds the entries its own file holds cannot be paid (panflute: required 6 against 1
entry), and a refusal on it would punish a debt nobody can pay. The entries are counted from the
file; a file whose entries cannot be counted (a JSON document) is never judged unsatisfiable,
because an unknown stays unknown and the requirement stands.
⚑ A ROW THAT DOES NOT PARSE IS SKIPPED AND COUNTED, NEVER READ AS OK: `read_rows` returns how many
lines it could not read, so a caller can say the file was partly unread.
"""

import json
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from mikemol.hooks.round_wire import STALE, published_at
from mikemol.hooks.stackrun import items_of

BEHIND = "behind"
ENV = "MIKEMOL_PACE_FILE"
_COUNTED = (".txt", ".tsv")
_QUEUE_FILES = frozenset(
    {".claude/paths-forward.json", ".claude/paths-forward.ledger", ".claude/paths-forward.md"}
)
_QUEUE = ".claude/paths-forward.json"
_OPEN = ("ready", "working", "blocked")


@dataclass(frozen=True, slots=True)
class Row:
    """One ratchet's verdict as nemik wrote it."""

    repo: str
    ratchet: str
    state: str
    observed: int
    required: int


@dataclass(frozen=True, slots=True)
class Owed:
    """A ratchet this repository must pay down: what is required, what fell, what it holds."""

    ratchet: str
    required: int
    observed: int
    entries: int | None


def _row(text: str) -> Row | None:
    """Read one row line.

    Returns:
        the Row, or None when the line is not a flat object with the five fields.

    """
    try:
        raw = cast("object", json.loads(text))
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    fields = cast("dict[str, object]", raw)
    try:
        return Row(
            str(fields["repo"]),
            str(fields["ratchet"]),
            str(fields["state"]),
            int(str(fields["observed"])),
            int(str(fields["required"])),
        )
    except (KeyError, ValueError):
        return None


def read_rows(text: str) -> tuple[list[Row], int]:
    """Read the pace file's rows, skipping its head line.

    Returns:
        the rows in file order, and the number of non-blank lines after the head that were not
        rows.

    """
    lines = [line for line in text.splitlines() if line.strip()]
    rows: list[Row] = []
    unread = 0
    for line in lines[1:]:
        row = _row(line)
        if row is None:
            unread += 1
        else:
            rows.append(row)
    return rows, unread


def entries_in(root: Path, ratchet: str) -> int | None:
    """Count the entries of a ratchet file: its non-blank lines that are not comments.

    Returns:
        the count for a `.txt` or `.tsv` file, or None when it is another kind or cannot be read
        (the entries are then unknown).

    """
    path = root / ratchet
    if path.suffix not in _COUNTED:
        return None
    try:
        body = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return sum(1 for line in body.splitlines() if line.strip() and not line.startswith("#"))


def owed(rows: Iterable[Row], repo: str, root: Path) -> list[Owed]:
    """List the ratchets of `repo` that are behind and whose requirement can be met.

    Returns:
        one Owed per behind row of the repo whose requirement does not exceed the entries its file
        holds (or whose entries are unknown), in file order.

    """
    out: list[Owed] = []
    for row in rows:
        if row.repo != repo or row.state != BEHIND:
            continue
        held = entries_in(root, row.ratchet)
        if held is not None and row.required > held:
            continue
        out.append(Owed(row.ratchet, row.required, row.observed, held))
    return out


def pace_path() -> Path:
    """Find the pace file.

    Returns:
        the path named by MIKEMOL_PACE_FILE, else `ratchet-pace.json` in luthen's nemik-export tree.

    """
    named = os.environ.get(ENV)
    return (
        Path(named) if named else Path.home() / ".local/share/luthen/nemik-export/ratchet-pace.json"
    )


def _touches(paths: Iterable[str], ratchet: str) -> bool:
    """Say whether any path is the ratchet's file or a directory holding it.

    Returns:
        True when a path names the ratchet or holds it.

    """
    return any(p == ratchet or ratchet.startswith(p.rstrip("/") + "/") for p in paths)


def paydown_cards(queue: object, ratchet: str) -> list[str]:
    """Name the open cards that pay a ratchet down: those touching `file:<ratchet>`.

    The `!w` suffix on a tag is ignored (nemik:W988).

    Returns:
        the symbols, in queue order.

    """
    raw = cast("dict[str, object]", queue).get("waypoints") if isinstance(queue, dict) else None
    cards = cast("list[object]", raw) if isinstance(raw, list) else []
    tag = f"file:{ratchet}"
    out: list[str] = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        fields = cast("dict[str, object]", card)
        touches = fields.get("touches")
        held = cast("list[object]", touches) if isinstance(touches, list) else []
        tags = [str(t).removesuffix("!w") for t in held]
        if fields.get("status") in _OPEN and tag in tags:
            out.append(str(fields.get("symbol")))
    return out


def operator_held(queue: object, ratchet: str) -> bool:
    """Say whether a ratchet's paydown waits only on an operator decision (github-8f, W1920).

    ⚑ A ROW AWAITING AN OPERATOR IS NOT REFUSABLE: panflute's last allowlist entry cannot be paid
    without a policy the operator has not chosen (W1977, github:W63), and refusing every commit on
    a debt nobody but the operator can move traps a turn on something the session cannot fix. The
    hold is real only when there IS a paydown card, it is open, and EVERY such card is blocked on
    a human; one ready or working card means the debt is payable and the row stays owed.

    Returns:
        True when the open cards touching `file:<ratchet>` are all blocked with kind `human`.

    """
    raw = cast("dict[str, object]", queue).get("waypoints") if isinstance(queue, dict) else None
    cards = cast("list[object]", raw) if isinstance(raw, list) else []
    tag = f"file:{ratchet}"
    open_cards: list[dict[str, object]] = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        fields = cast("dict[str, object]", card)
        touches = fields.get("touches")
        held = cast("list[object]", touches) if isinstance(touches, list) else []
        if fields.get("status") in _OPEN and tag in [str(t).removesuffix("!w") for t in held]:
            open_cards.append(fields)
    return bool(open_cards) and all(
        c.get("status") == "blocked" and c.get("blocked_kind") == "human" for c in open_cards
    )


def stack_reason(
    directory: Path, stack_paths: Iterable[str], now: datetime, pace_file: Path | None = None
) -> str | None:
    """Judge a submitted stack against the repository's paydown pace.

    ⚑ NO PACE MEANS NO REFUSAL, in every way the pace can be absent: no file, an unreadable file or
    queue, a stamp missing or older than the round's staleness bound, no rows behind for this repo,
    or only rows nobody can pay. A guard that refuses on a missing input traps a turn on something
    the session cannot fix.
    ⚑ A STACK OF QUEUE FILES ALONE IS ADMITTED (a queue-state commit), and so is any stack that
    touches a ratchet this repository owes: it is the paydown.

    Returns:
        the reason to refuse, naming each owed ratchet, its required and observed fall and the
        paydown cards to take; None when the stack may wait.

    """
    try:
        text = (pace_file or pace_path()).read_text(encoding="utf-8")
        queue: object = json.loads((directory / _QUEUE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    stamp = published_at(text)
    if stamp is None or now - stamp > STALE:
        return None
    rows, _ = read_rows(text)
    behind = [
        o for o in owed(rows, directory.name, directory) if not operator_held(queue, o.ratchet)
    ]
    paths = list(stack_paths)
    if not behind or (paths and all(p in _QUEUE_FILES for p in paths)):
        return None
    if any(_touches(paths, o.ratchet) for o in behind):
        return None
    lines = []
    for o in behind:
        cards = ", ".join(paydown_cards(queue, o.ratchet)) or "none named: add one touching it"
        lines.append(
            f"{o.ratchet}: required fall {o.required}, observed {o.observed}; "
            f"paydown cards: {cards}"
        )
    return (
        f"{directory.name} is behind its ratchet paydown and this stack lowers none of the "
        f"ratchets it owes ({'; '.join(lines)}): land a stack that touches one"
    )


def refusal(root: Path, stack_file: Path, env: Mapping[str, str]) -> str | None:
    """Judge a submitted stack file against the paydown pace, as the other submit refusals do.

    Returns:
        what `stack_reason` says for the paths of every entry, now; None when the stack file cannot
        be read or the pace asks nothing (MIKEMOL_PACE_FILE names the pace file, as the round's
        variable names the round).

    """
    items = items_of(stack_file)
    if isinstance(items, str):
        return None
    named = env.get(ENV)
    paths = [path for item in items for path in item.paths]
    return stack_reason(root, paths, datetime.now(UTC), Path(named) if named else None)
