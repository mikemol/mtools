# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Advice a dry run gives, recorded once in the queue where nemik can read it (W1242, W1140).

A dry run (`--block-matching`, `--update-many`, `--prune-landed`, `--block-behind-open`) prints
WOULD lines: deterministic advice that nobody has to act on, and that a session can ignore by not
running `--write`. This keeps each piece of advice as ONE row in the state file's `advice` list, so
the queue itself says what a tool indicated, how often, and what a session decided about it.

⚑ A ROW IS KEYED BY (tool, rule, subject, action): the same advice seen again updates `last_run`
and adds nothing, which is what makes "new" countable. A row is `open`, `rejected` (a session said
no and gave a REASON, which the next dry run prints instead of re-proposing) or `applied` (the
change landed, so the card is no longer indicated).

⚑ THE LIST IS A TOP-LEVEL KEY OF THE DOCUMENT, like `standing`: it survives the round trip, the
state hash covers the waypoints and not it, and nemik reads the one file without parsing a ledger.

CONSUMED BY: the four dry-run modes (W1244) and `--reject-advice` (W1243).
"""

from typing import cast

from mikemol.pathsforward.model import Json, MalformedStateError

KEY = "advice"
OPEN = "open"
REJECTED = "rejected"
APPLIED = "applied"
NEW = "new"
SEEN = "seen"
Advice = tuple[str, str, str, str]


def rows(doc: Json) -> list[Json]:
    """Return the document's advice list, creating it empty when absent.

    Returns:
        the list, as stored in `doc`.

    Raises:
        MalformedStateError: when `advice` exists and is not a list of objects.

    """
    raw = doc.setdefault(KEY, [])
    if not isinstance(raw, list) or not all(isinstance(r, dict) for r in cast("list[object]", raw)):
        msg = f"`{KEY}` is not a list of objects"
        raise MalformedStateError(msg)
    return cast("list[Json]", raw)


def _is(row: Json, advice: Advice) -> bool:
    tool, rule, subject, action = advice
    mine = (row.get("tool"), row.get("rule"), row.get("subject"), row.get("action"))
    return mine == (tool, rule, subject, action)


def upsert(doc: Json, advice: Advice, run_id: str) -> str:
    """Record one piece of advice, or note that it was seen again.

    Returns:
        `rejected` when a session rejected it (the caller prints the stated reason, not the advice),
        `seen` when it was already recorded, `new` when this run first recorded it.

    """
    for row in rows(doc):
        if _is(row, advice):
            row["last_run"] = run_id
            return REJECTED if row.get("status") == REJECTED else SEEN
    tool, rule, subject, action = advice
    rows(doc).append(
        {
            "tool": tool,
            "rule": rule,
            "subject": subject,
            "action": action,
            "first_run": run_id,
            "last_run": run_id,
            "status": OPEN,
        }
    )
    return NEW


def exclude(doc: Json, advice: Advice, reason: str, run_id: str) -> None:
    """Record one piece of advice as rejected at once, with a reason (an `--except`).

    ⚑ AN EXCLUSION IS A REJECTION WRITTEN BEFORE THE ADVICE WAS EVER MADE: the row is created if it
    is absent, then set to rejected with the stated reason, so a later dry run that would propose
    it prints the reason instead (mtools:W1158).

    Raises:
        ValueError: when the reason is empty.

    """
    if not reason.strip():
        msg = "an exclusion needs a reason"
        raise ValueError(msg)
    upsert(doc, advice, run_id)
    for row in rows(doc):
        if _is(row, advice):
            row["status"] = REJECTED
            row["reason"] = reason.strip()


def reason_for(doc: Json, advice: Advice) -> str | None:
    """Read the stated reason a piece of advice was rejected.

    Returns:
        the reason, or None when the advice is not a rejected row.

    """
    for row in rows(doc):
        if _is(row, advice) and row.get("status") == REJECTED:
            return str(row.get("reason", ""))
    return None


def reject(doc: Json, tool: str, rule: str, reason: str, subject: str | None = None) -> int:
    """Reject every open row of a tool and rule (or of one subject), with a reason.

    ⚑ A REJECTION WITHOUT A REASON IS REFUSED: the reason is what the next dry run prints in place
    of the advice, and a bare "no" is the silence this store exists to remove.

    Returns:
        the number of rows rejected.

    Raises:
        ValueError: when the reason is empty.

    """
    if not reason.strip():
        msg = "a rejection needs a reason"
        raise ValueError(msg)
    changed = 0
    for row in rows(doc):
        wanted = row.get("tool") == tool and row.get("rule") == rule and row.get("status") == OPEN
        if wanted and (subject is None or row.get("subject") == subject):
            row["status"] = REJECTED
            row["reason"] = reason.strip()
            changed += 1
    return changed


def close_applied(doc: Json, tool: str, rule: str, still_indicated: set[str]) -> int:
    """Mark open rows of a tool and rule whose subject is no longer indicated as applied.

    Returns:
        the number of rows closed.

    """
    closed = 0
    for row in rows(doc):
        mine = row.get("tool") == tool and row.get("rule") == rule and row.get("status") == OPEN
        if mine and row.get("subject") not in still_indicated:
            row["status"] = APPLIED
            closed += 1
    return closed


def mark_applied(doc: Json, tool: str, rule: str, subjects: set[str]) -> int:
    """Mark the open rows of a tool and rule for these subjects as applied: the change was made.

    Returns:
        the number of rows closed.

    """
    closed = 0
    for row in rows(doc):
        mine = row.get("tool") == tool and row.get("rule") == rule and row.get("status") == OPEN
        if mine and row.get("subject") in subjects:
            row["status"] = APPLIED
            closed += 1
    return closed


def counts(outcomes: list[str]) -> tuple[int, int, int]:
    """Count a run's advice by what `upsert` returned for each piece.

    Returns:
        (proposed, rejected, new): proposed is the rows shown as advice (new and seen), rejected the
        ones suppressed by a stated reason, new the ones first recorded by this run.

    """
    new = outcomes.count(NEW)
    return new + outcomes.count(SEEN), outcomes.count(REJECTED), new
