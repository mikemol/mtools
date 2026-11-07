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
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from mikemol.hooks import admission, runproc, stacksnap
from mikemol.hooks.round_wire import STALE, published_at
from mikemol.hooks.stackfreeze import SNAP_ENV
from mikemol.hooks.stackrun import Item, items_of
from mikemol.hooks.stacksnap import QUEUE_FILES

BEHIND = "behind"
ENV = "MIKEMOL_PACE_FILE"
_COUNTED = (".txt", ".tsv")
_GLOB = "*?["
_QUEUE_FILES = QUEUE_FILES
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


def unmatchable(ratchet: str) -> bool:
    """Say whether no stack path can ever satisfy a ratchet key.

    ⚑ A GLOB KEY IS A SENSOR DEFECT, NOT DEBT (github-94, github:W59, mtools:W2244): the pace
    file once carried the row `*.py`, which `entries_in` cannot count and `_touches` cannot
    match (a stack path equals a file, never a pattern), so the guard asked for something no
    stack can do. A key with a wildcard is reported UNMATCHABLE and is never owed.

    Returns:
        True when the key holds `*`, `?` or `[`.

    """
    return any(char in ratchet for char in _GLOB)


def owed(rows: Iterable[Row], repo: str, root: Path) -> list[Owed]:
    """List the ratchets of `repo` that are behind and whose requirement can be met.

    Returns:
        one Owed per behind row of the repo whose requirement does not exceed the entries its file
        holds (or whose entries are unknown), in file order.

    """
    out: list[Owed] = []
    for row in rows:
        if row.repo != repo or row.state != BEHIND or unmatchable(row.ratchet):
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


def split_dir(ratchet: str) -> str:
    """Name the directory a ratchet kept one file per module would live in (W2192).

    ⚑ A BASELINE KEPT PER MODULE IS STILL THE SAME RATCHET (nemik on W2186): `mypy-baseline.json`
    split into `mypy-baseline.d/<module>.json` keeps its name and its summed value, and a stack that
    lowers only its own module's file must count as touching it.

    Returns:
        the ratchet's path without its last suffix, plus `.d/` (`x/mypy-baseline.json` gives
        `x/mypy-baseline.d/`); the whole path plus `.d/` when its name has no suffix.

    """
    head, _, name = ratchet.rpartition("/")
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return f"{head}/{stem}.d/" if head else f"{stem}.d/"


def _touches(paths: Iterable[str], ratchet: str) -> bool:
    """Say whether any path is the ratchet's file, a directory holding it, or one of its parts.

    Returns:
        True when a path names the ratchet, holds it, or is a file in its per-module directory
        (`split_dir`).

    """
    parts = split_dir(ratchet)
    return any(
        p == ratchet or ratchet.startswith(p.rstrip("/") + "/") or p.startswith(parts)
        for p in paths
    )


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
    directory: Path,
    stack_paths: Iterable[str],
    now: datetime,
    pace_file: Path | None = None,
    admitted: Callable[[], bool] | None = None,
) -> str | None:
    """Judge a submitted stack against the repository's paydown pace.

    ⚑ NO PACE MEANS NO REFUSAL, in every way the pace can be absent: no file, an unreadable file or
    queue, a stamp missing or older than the round's staleness bound, no rows behind for this repo,
    or only rows nobody can pay. A guard that refuses on a missing input traps a turn on something
    the session cannot fix.
    ⚑ A STACK OF QUEUE FILES ALONE IS ADMITTED (a queue-state commit), and so is any stack that
    touches a ratchet this repository owes: it is the paydown.
    ⚑ A PINNED ROW IS ASKED LAST (W2301), only for a stack that would otherwise be refused, so an
    honest paydown never spends one: `admitted` answers whether a row in `admission.ROWS` is
    exactly this change. It forgives no debt; the row is spent by its trailer at landing.

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
    if admitted is not None and admitted():
        return None
    lines = []
    for o in behind:
        cards = ", ".join(paydown_cards(queue, o.ratchet)) or "none named: add one touching it"
        lines.append(
            f"{o.ratchet}: required fall {o.required}, observed {o.observed}; "
            f"paydown cards: {cards}"
        )
    skipped = sorted(
        {
            r.ratchet
            for r in rows
            if r.repo == directory.name and r.state == BEHIND and unmatchable(r.ratchet)
        }
    )
    note = f" (UNMATCHABLE, not owed: {', '.join(skipped)})" if skipped else ""
    return (
        f"{directory.name} is behind its ratchet paydown and this stack lowers none of the "
        f"ratchets it owes ({'; '.join(lines)}): land a stack that touches one{note}"
    )


REBASELINES = "rebaselines.json"


def _git_text(root: Path, argv: Sequence[str]) -> str | None:
    # What git printed for `argv` in `root`; None when git failed, so a failed read never
    # reads as an empty one.
    done = runproc.run(["git", "-C", str(root), *argv])
    return done.stdout if done.returncode == 0 else None


def _birth_clear(row: admission.Row, root: Path, files: Sequence[stacksnap.Frozen]) -> bool:
    # A birth row also passes its accident checks (W2309): the ratchet file is new at HEAD and
    # the stack's frozen rebaselines.json carries the entry citing the pinned record.
    # ⚑ FAILS CLOSED: a git read that fails, or a rebaselines blob that cannot be read, refuses.
    if row.kind != admission.BIRTH:
        return True
    listing = _git_text(root, ["ls-tree", "-r", "--name-only", "-z", "HEAD"])
    if listing is None:
        return False
    blob = next((f.blob for f in files if f.path == REBASELINES), "")
    entry = _git_text(root, ["cat-file", "blob", blob]) if blob else None
    return admission.accident(row, frozenset(listing.split("\0")), entry) is None


def _admitted_by(
    root: Path, waypoints: Sequence[str], env: Mapping[str, str], rows: Sequence[admission.Row]
) -> Callable[[], bool]:
    # Whether a pinned row is exactly this stack, read from the FROZEN snapshot the submit made.
    # ⚑ NO SNAPSHOT MEANS NO ADMISSION: an unreadable or absent snapshot never admits.
    def check() -> bool:
        named = env.get(SNAP_ENV, "")
        frozen = stacksnap.load(Path(named)) if named else None
        if frozen is None:
            return False
        files = [f for entry in frozen for f in entry]
        row = admission.admitting(rows, root.name, waypoints, files)
        return row is not None and _birth_clear(row, root, files)

    return check


def admitted_ident(
    root: Path,
    items: Sequence[Item],
    env: Mapping[str, str],
    rows: Sequence[admission.Row] = admission.ROWS,
    now: datetime | None = None,
) -> str | None:
    """Name the pinned row a stack NEEDS and matches, for the Admission trailer (W2312).

    ⚑ A ROW IS SPENT ONLY WHEN IT WAS NEEDED: a stack the pace would admit anyway (a paydown, queue
    state, no pace) answers None, so an honest landing never writes the trailer and never spends a
    row. ⚑ IT READS THE ITEMS BEING LANDED, not the stack file judged at submit, so the row that
    admits a stack at landing is judged on the bytes that land (the re-check against the refrozen
    snapshot, W2301 point 4).

    Returns:
        the row's `<repo>/<card>` id, or None when the pace asks nothing or no row is this stack.

    """
    named = env.get(ENV)
    paths = [path for item in items for path in item.paths]
    pace = Path(named) if named else None
    if stack_reason(root, paths, now or datetime.now(UTC), pace) is None:
        return None
    frozen = [file for item in items for file in item.files or ()]
    row = admission.admitting(rows, root.name, [item.waypoint for item in items], frozen)
    if row is None or not _birth_clear(row, root, frozen):
        return None
    return row.ident()


def refusal(
    root: Path,
    stack_file: Path,
    env: Mapping[str, str],
    rows: Sequence[admission.Row] = admission.ROWS,
) -> str | None:
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
    admitted = _admitted_by(root, [item.waypoint for item in items], env, rows)
    return stack_reason(root, paths, datetime.now(UTC), Path(named) if named else None, admitted)
