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

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO, cast

from mikemol.hooks import flakes
from mikemol.hooks.commit_body import refusal as body_refusal
from mikemol.hooks.gateclass import classify_all
from mikemol.hooks.gatephase import failed_checks, stage_note
from mikemol.hooks.isolated import EnvRunner
from mikemol.hooks.queuecarry import carry
from mikemol.hooks.stackgate import gate_tip
from mikemol.hooks.stackland import Entry, build
from mikemol.hooks.stacklanding import land
from mikemol.hooks.stackmutants import Lint, no_lint, refusals
from mikemol.hooks.stacksnap import Frozen

BODY_CHECK = body_refusal
EXIT_RACED = 5
SHORT = 7
KINDS_SHOWN = 3
KIND_CUT = 60
History = Mapping[str, tuple[bool, ...]]


@dataclass(frozen=True)
class Item:
    """One commit asked for: its waypoint, subject, body and the paths it takes.

    `files` are those paths frozen at submit (W1447), when the caller froze them.
    """

    waypoint: str
    subject: str
    body: str
    paths: tuple[str, ...]
    files: tuple[Frozen, ...] | None = None


def no_history(_repo: str) -> History | None:
    """Say that no gate history is available.

    Returns:
        None, so a refusal says nothing about the kind of red.

    """
    return None


@dataclass(frozen=True)
class Seams:
    """What a test replaces: the git runner, the namespace, the message, publish and history."""

    run: EnvRunner
    namespace: Path
    message_of: Callable[[Item], str]
    published: Callable[[str], str]
    history: Callable[[str], History | None] = no_history
    lint: Lint = no_lint


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
    except Exception as exc:
        if not isinstance(exc, (OSError, ValueError)):
            raise
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


def kind_note(output: str, history: History | None) -> str:
    """Say which kind of red each failed check is against its history (W1721).

    Returns:
        'kind: <label> is <class>; ...' for the first few failed checks, or '' when the
        output lists none or no history could be read (nothing is guessed).

    """
    labels = failed_checks(output)
    if not labels or history is None:
        return ""
    kinds = classify_all(labels, history)
    shown = "; ".join(
        f"{label[:KIND_CUT]} is {kind}" for label, kind in list(kinds.items())[:KINDS_SHOWN]
    )
    return f"kind: {shown}; "


def culprit_note(output: str, items: Sequence[Item], history: History | None = None) -> str:
    """Say which entries the refused gate's output names, or that it names none.

    Returns:
        a clause for the REFUSED line, with the failing steps' kind when `history` is given.

    """
    stage = stage_note(output) + kind_note(output, history)
    hits = culprits(output, items)
    if not hits:
        return f"{stage}culprit: unattributed (the failing check names no path in this stack)"
    named = ", ".join(f"entry {p + 1}/{len(items)} ({items[p].waypoint})" for p in hits)
    return f"{stage}culprit: {named}"


def _judged(root: Path, tree: str, shown: str, code: int, seams: Seams) -> str:
    # Keep this tip's verdict (W2007); the line a pass on an already-refused tree prints, else "".
    where = seams.run(["rev-parse", "--absolute-git-dir"], {}, root)
    if where.returncode != 0:
        return ""
    kind = flakes.PASSED if code == 0 else flakes.REFUSED
    failed = [] if code == 0 else failed_checks(shown)
    before = flakes.record(Path(where.stdout.strip()), tree, kind, failed)
    if before is None:
        return ""
    named = "; ".join(before) or "no check named"
    return (
        f"FLAKE {root.name}: this exact tree was refused before ({named}) and passes now. The "
        "code did not change and the verdict did: a nondeterminism, recorded in "
        "gate-verdicts.jsonl (W2007). It is a blocker to deconstruct, not luck.\n"
    )


def run_stack(root: Path, items: Sequence[Item], out: TextIO, seams: Seams) -> int:
    """Build, gate once, land, and report.

    Returns:
        0 when every commit landed; EXIT_RACED when HEAD moved; otherwise the gate's or the failed
        step's status (never 0 for a stack that did not land).

    """
    name, run = root.name, seams.run
    items, carried = carry(root, items, run)
    if carried:
        out.write(
            f"stack: carrying {', '.join(carried)} in the last entry (the working queue differs "
            "from HEAD and no entry named it, W1941)\n"
        )
    before = run(["rev-parse", "HEAD"], {}, root).stdout.strip()
    entries = [Entry(seams.message_of(item), item.paths, item.files) for item in items]
    stack = build(root, entries, run, before)
    if stack.failed is not None:
        place = len(stack.commits) + 1
        why = (stack.failed.stderr or stack.failed.stdout).strip()
        out.write(
            f"NOT COMMITTED {name}: stack entry {place}/{len(items)} could not be built: {why}; "
            f"nothing landed, HEAD is still {before[:SHORT]}\n"
        )
        return stack.failed.returncode or 1
    broken = refusals(
        root, stack.trees[-1], seams.namespace, [p for i in items for p in i.paths], seams.lint
    )
    if broken:
        out.writelines(f"{line}\n" for line in broken)
        out.write(
            f"REFUSED {name} (rc=1): the tip of a {len(items)}-commit stack declares mutants "
            f"that cannot be planted (before the gate, W1704); nothing landed, HEAD is still "
            f"{before[:SHORT]}\n"
        )
        return 1
    gate = gate_tip(root, stack.trees[-1], run, seams.namespace)
    shown = (gate.stdout + gate.stderr).strip()
    if shown:
        out.write(f"{shown}\n")
    out.write(_judged(root, stack.trees[-1], shown, gate.returncode, seams))
    if gate.returncode != 0:
        out.write(
            f"REFUSED {name} (rc={gate.returncode}): the tip of a {len(items)}-commit stack was "
            f"gated once and refused; nothing landed, HEAD is still {before[:SHORT]}; "
            f"{culprit_note(shown, items, seams.history(name))}\n"
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
