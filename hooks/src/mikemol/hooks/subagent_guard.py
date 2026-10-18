# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""PreToolUse(Agent): refuse a second concurrent subagent of the same session (W1275).

⚑ A RULE ONLY IN THE PROMPT FAILED (github-8f, 2026-10-18): el-openglo dispatched three waves of
five concurrent subagents on typing debt, which the no-swarming rule forbids (operator, 2026-10-15:
no concurrent subagents in a repo, one at a time is fine, more only on "dispatch a subagent"), and
the operator wrote "I don't remember authorizing this". So the rule is a hook, counted from the
harness's own records and not from anyone's recollection.

⚑ THE RECORDS ARE MEASURED, NOT GUESSED (2026-10-18): a session `<id>.jsonl` has a sibling
directory `<id>/subagents/` holding `agent-<id>.jsonl` and `agent-<id>.meta.json` for each spawned
subagent, and a finished subagent's last record carries `toolEndsTurn` true. So a subagent is
RUNNING when its transcript's last parsable record lacks that mark and the file was written within
`LIVE_S`; an older file belongs to an agent that died without ending its turn and is not counted,
or one crashed agent would block the session for ever.

⚑ THE ESCAPE IS THE OPERATOR'S OWN WORDS IN THE LATEST HUMAN TURN: "dispatch a subagent" or "swarm"
in the most recent message typed by a person (a tool result, a scheduled prompt's system wrapper
or a peer's relayed message is not one). Anything else is a refusal that says to card the work
and queue it. The harness's payload names `transcript_path`, so no environment is read.
CONSUMED BY: `.claude/settings.json` (a PreToolUse entry matching `Agent`, operator-applied).
"""

import json
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from mikemol.hooks import payload

AGENT_TOOL = "Agent"
LIVE_S = 1800.0
PHRASES = ("dispatch a subagent", "swarm")
_TAIL = 262144
_END_MARK = "toolEndsTurn"


def _tail_records(path: Path) -> list[dict[str, object]]:
    """Read the parsable records of the last bytes of a transcript, oldest first.

    Returns:
        the records, empty when the file cannot be read.

    """
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - _TAIL))
            raw = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    records: list[dict[str, object]] = []
    for text in raw.splitlines():
        try:
            got: object = json.loads(text)
        except ValueError:
            continue
        records.append(payload.as_record(got))
    return records


def running(subagents: Path, now: float) -> list[str]:
    """Name the subagents of a session that are still running.

    Returns:
        the ids (file stems) of those whose last record does not end a turn and whose file was
        written within `LIVE_S` of `now`, in name order.

    """
    found: list[str] = []
    for path in sorted(subagents.glob("agent-*.jsonl")):
        try:
            fresh = now - path.stat().st_mtime <= LIVE_S
        except OSError:
            continue
        records = _tail_records(path)
        ended = bool(records) and records[-1].get(_END_MARK) is True
        if fresh and not ended:
            found.append(path.stem)
    return found


def _typed(record: dict[str, object]) -> str:
    """Take the words a person typed from one transcript record, or "" when it is not one.

    Returns:
        the text of a user record whose content is a plain string, never a tool result and never
        a system-wrapped notification.

    """
    if record.get("type") != "user":
        return ""
    content = payload.as_record(record.get("message")).get("content")
    if isinstance(content, str):
        return "" if content.lstrip().startswith("<") else content
    return ""


def operator_dispatches(transcript: Path) -> bool:
    """Say whether the latest human turn carries an authorising phrase.

    Returns:
        True when the newest typed message contains "dispatch a subagent" or "swarm" in any case.

    """
    for record in reversed(_tail_records(transcript)):
        words = _typed(record)
        if words:
            lowered = words.lower()
            return any(phrase in lowered for phrase in PHRASES)
    return False


def decide(raw: object, now: float) -> str | None:
    """Judge one PreToolUse payload.

    Returns:
        the refusal reason, or None when the call is not an Agent call, no other subagent is
        running, or the operator's latest words authorise it.

    """
    record = payload.as_record(raw)
    if payload.text_of(record.get("tool_name")) != AGENT_TOOL:
        return None
    transcript = Path(payload.text_of(record.get("transcript_path")))
    if not transcript.name:
        return None
    others = running(transcript.with_suffix("") / "subagents", now)
    if not others or operator_dispatches(transcript):
        return None
    return (
        f"no swarming: {len(others)} subagent(s) of this session still running ({others[0]}...). "
        "One at a time is fine; more only on the operator's own words 'dispatch a subagent' or "
        "'swarm' (operator, 2026-10-15). Card the extra work in the queue and run it after."
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Read the PreToolUse payload from stdin and refuse a second concurrent subagent.

    Returns:
        0 always: the decision travels in the printed JSON, never the status.

    """
    del argv
    try:
        raw: object = json.load(sys.stdin)
    except ValueError:
        return 0
    reason = decide(raw, time.time())
    if reason is None:
        return 0
    decision: dict[str, dict[str, str]] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    json.dump(decision, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
