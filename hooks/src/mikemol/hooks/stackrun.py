# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run a stack: build the commits, gate the tip once, land them, say one verdict per commit (W1162).

Orchestration only: `stackland.build` makes the commits without a hook, `stackgate.gate_tip` runs
the repository's pre-commit once on the tip, `stacklanding.land` moves HEAD against the starting
value and lets the repo push. The verdict grammar is `mikemol-commit`'s own:

    COMMITTED <repo> <sha7> <subject> [PUSHED]      one per commit, oldest first
    REFUSED <repo> (rc=N) ...                       the tip's gate refused; NOTHING landed
    RACED <repo>: HEAD moved ...                    a peer moved HEAD; NOTHING landed (exit 5)
    NOT COMMITTED <repo>: ...                       a commit could not be built; NOTHING landed

⚑ ALL OR NOTHING, STATED: a refusal names that nothing landed, because landing the prefix before
the culprit would need a second gate run on that prefix (see `.claude/design/stack-land.md`).

⚑ THE STACK IS A FILE, NOT A COMMAND LINE: a JSON list of `{waypoint, subject, body, paths}`. A
variadic `--stack W S PATH...` repeated N times has no unambiguous end for each entry's paths, and
a file is a record of what was asked (this deviates from W1162's first wording; recorded there).

CONSUMED BY: `commit_kata.main` (`--stack FILE`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from mikemol.hooks.commit_body import refusal as body_refusal
from mikemol.hooks.stackgate import gate_tip
from mikemol.hooks.stackland import Entry, build
from mikemol.hooks.stacklanding import land

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path
    from typing import TextIO

    from mikemol.hooks.isolated import EnvRunner

BODY_CHECK = body_refusal
EXIT_RACED = 5
SHORT = 7


@dataclass(frozen=True)
class Item:
    """One commit asked for: its waypoint, subject, body and the paths it takes."""

    waypoint: str
    subject: str
    body: str
    paths: tuple[str, ...]


@dataclass(frozen=True)
class Seams:
    """What a test replaces: the git runner, the snapshot namespace, the message and the publish."""

    run: EnvRunner
    namespace: Path
    message_of: Callable[[Item], str]
    published: Callable[[str], str]


def _item_of(entry: object) -> Item | None:
    """Read one entry of the stack file.

    Returns:
        the item, or None when it lacks a string waypoint and subject or a list of string paths.

    """
    if not isinstance(entry, dict):
        return None
    fields = cast("dict[str, object]", entry)
    waypoint, subject = fields.get("waypoint"), fields.get("subject")
    body, paths = fields.get("body", ""), fields.get("paths")
    if not all(isinstance(v, str) for v in (waypoint, subject, body)):
        return None
    if not (isinstance(paths, list) and paths and all(isinstance(p, str) for p in paths)):
        return None
    return Item(str(waypoint), str(subject), str(body), tuple(str(p) for p in paths))


def items_of(path: Path) -> list[Item] | str:
    """Read the stack file.

    Returns:
        the items, or the reason the file is not a stack (unreadable, not a non-empty list, an entry
        missing a waypoint, subject or paths).

    """
    try:
        raw = cast("object", json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        return f"{path}: {exc}"
    if not isinstance(raw, list) or not raw:
        return f"{path}: a stack is a non-empty JSON list of entries"
    found: list[Item] = []
    for place, entry in enumerate(cast("list[object]", raw), start=1):
        item = _item_of(entry)
        if item is None:
            return f"{path}: entry {place} needs string waypoint and subject and a list of paths"
        # ⚑ THE TRAILERS ARE THE TOOL'S (W1273): a body carrying either would have it twice.
        reason = BODY_CHECK(item.body)
        if reason is not None:
            return f"{path}: entry {place}: {reason}"
        found.append(item)
    return found


def culprits(output: str, items: Sequence[Item]) -> list[int]:
    """Name the entries whose paths the gate's output mentions (W1156).

    ⚑ A TOKEN MATCHES AN ENTRY'S PATH WHEN IT IS THAT PATH, ENDS WITH IT AS A TRAILING PATH, OR LIES
    INSIDE IT AS A DIRECTORY. Nothing else is read as blame: a check that names no path in the
    stack (a whole-suite pytest) blames no entry, and the caller says so rather than guessing.

    Returns:
        the zero-based places of the entries mentioned, in stack order.

    """
    words = {word.strip("\"'`:,;()[]") for word in output.split()}
    tokens = words | {word.partition(":")[0] for word in words}
    hits: list[int] = []
    for place, item in enumerate(items):
        for path in item.paths:
            base = path.rstrip("/")
            if any(t == base or t.endswith(f"/{base}") or t.startswith(f"{base}/") for t in tokens):
                hits.append(place)
                break
    return hits


def culprit_note(output: str, items: Sequence[Item]) -> str:
    """Say which entries the refused gate's output names, or that it names none.

    Returns:
        a clause for the REFUSED line.

    """
    hits = culprits(output, items)
    if not hits:
        return "culprit: unattributed (the failing check names no path in this stack)"
    named = ", ".join(f"entry {p + 1}/{len(items)} ({items[p].waypoint})" for p in hits)
    return f"culprit: {named}"


def run_stack(root: Path, items: Sequence[Item], out: TextIO, seams: Seams) -> int:
    """Build, gate once, land, and report.

    Returns:
        0 when every commit landed; EXIT_RACED when HEAD moved; otherwise the gate's or the failed
        step's status (never 0 for a stack that did not land).

    """
    name, run = root.name, seams.run
    before = run(["rev-parse", "HEAD"], {}, root).stdout.strip()
    entries = [Entry(seams.message_of(item), item.paths) for item in items]
    stack = build(root, entries, run, before)
    if stack.failed is not None:
        place = len(stack.commits) + 1
        why = (stack.failed.stderr or stack.failed.stdout).strip()
        out.write(
            f"NOT COMMITTED {name}: stack entry {place}/{len(items)} could not be built: {why}; "
            f"nothing landed, HEAD is still {before[:SHORT]}\n"
        )
        return stack.failed.returncode or 1
    gate = gate_tip(root, stack.trees[-1], run, seams.namespace)
    shown = (gate.stdout + gate.stderr).strip()
    if shown:
        out.write(f"{shown}\n")
    if gate.returncode != 0:
        out.write(
            f"REFUSED {name} (rc={gate.returncode}): the tip of a {len(items)}-commit stack was "
            f"gated once and refused; nothing landed, HEAD is still {before[:SHORT]}; "
            f"{culprit_note(shown, items)}\n"
        )
        return gate.returncode
    paths = [p for item in items for p in item.paths]
    landing = land(root, stack.commits, before, paths, run)
    out.writelines(f"{note}\n" for note in landing.notes)
    if not landing.moved:
        out.write(
            f"RACED {name}: HEAD moved while the stack was gated ({landing.reason}); none of its "
            f"{len(items)} commits landed (HEAD was {before[:SHORT]})\n"
        )
        return EXIT_RACED
    out.writelines(
        f"COMMITTED {name} {sha[:SHORT]} {item.subject} [{seams.published(sha)}]\n"
        for sha, item in zip(stack.commits, items, strict=True)
    )
    return 0
