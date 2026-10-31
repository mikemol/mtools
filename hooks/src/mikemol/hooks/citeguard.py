# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W2064: PreToolUse(SendMessage): refuse a message citing a transcript line the turn never read.

A relayed ruling cited "host transcript line 107690" from recall, and the number was wrong; a
peer cannot tell a quoted line from a remembered one. The rule is mechanical: a message that
names a transcript line (`line 107690`, `L107690`) is admitted only when a tool result IN THE
SAME TURN holds that number, as `transcriptstruct --raw` or `--human` output does for a line it
printed.

⚑ A TRANSCRIPT LINE IS A LONG NUMBER, A FILE LINE IS NOT: a source file's line 1126 names a place
in code and needs no transcript read, so only a number of at least MIN_DIGITS digits is a
citation. That is a convention, not a proof, and it is the cost of not asking the sender which
kind it meant.

⚑ THE GUARD BOUNDS A CLAIM, NEVER FORBIDS A MESSAGE: it names the unread lines and the command
that reads them. A transcript that cannot be read admits the message, because a guard that
refused on doubt would stop every message when the file moved.

⚑ ARMED, NOT ADVISORY, like its siblings: its own variable first, then the shared one. Unarmed
it exits 0 with no decision. The host's paths are CONFIG (the payload's `transcript_path`), not
constants.
"""

import json
import sys
from pathlib import Path
from typing import TextIO, cast

from mikemol.hooks.payload import armed, as_record, text_of

OWN_SWITCH = "CITEGUARD_HOOK_BLOCK"
MIN_DIGITS = 5
_PUNCT = str.maketrans(dict.fromkeys(",.;:()[]{}\"'`", " "))


def _words(text: str) -> list[str]:
    return text.translate(_PUNCT).split()


def _long(word: str, min_digits: int) -> int | None:
    # A word that is digits, or `L` and digits, of at least `min_digits` digits.
    digits = word[1:] if word[:1] in {"L", "l"} else word
    return int(digits) if digits.isdigit() and len(digits) >= min_digits else None


def cited(text: str, min_digits: int = MIN_DIGITS) -> frozenset[int]:
    """Name the transcript lines a message cites.

    Returns:
        the long numbers that follow the word `line` or are written `L<N>`.

    """
    words = _words(text)
    found: set[int] = set()
    for here, word in enumerate(words):
        spelled = word[:1] in {"L", "l"} and word[1:].isdigit()
        after = words[here - 1].lower() == "line" if here else False
        if spelled or after:
            number = _long(word, min_digits)
            if number is not None:
                found.add(number)
    return frozenset(found)


def numbers_in(text: str, min_digits: int = MIN_DIGITS) -> frozenset[int]:
    """Name the long numbers a tool result holds.

    Returns:
        every word of at least `min_digits` digits (or `L` and digits) in `text`, as integers.

    """
    return frozenset(n for n in (_long(w, min_digits) for w in _words(text)) if n is not None)


def refusal(text: str, seen: frozenset[int]) -> str | None:
    """Decide whether a message cites a line the turn did not read.

    Returns:
        the reason to deny; None when it cites no transcript line or every one was seen.

    """
    unread = sorted(cited(text) - seen)
    if not unread:
        return None
    named = ", ".join(str(n) for n in unread)
    return (
        f"cite-guard: this message cites transcript line {named} but no tool result in this "
        "turn holds it. Read the line first (mikemol-transcriptstruct ... --raw or --human on "
        "that line), then quote it; or drop the number if it is from memory."
    )


def _blocks(record: dict[str, object]) -> list[object]:
    content = as_record(record.get("message")).get("content")
    return cast("list[object]", content) if isinstance(content, list) else []


def _result_text(block: dict[str, object]) -> str:
    body = block.get("content")
    if isinstance(body, str):
        return body
    parts = cast("list[object]", body) if isinstance(body, list) else []
    return " ".join(text_of(as_record(part).get("text")) for part in parts)


def turn_results(transcript: str) -> str:
    """Collect the tool-result text of the current turn.

    The turn starts after the last record that is a human prompt: a `user` record whose content
    is a string, not a list of tool results.

    Returns:
        the joined text of every `tool_result` block since then; empty when none.

    """
    records: list[dict[str, object]] = []
    for raw in transcript.splitlines():
        try:
            parsed: object = json.loads(raw)
        except ValueError:
            continue
        records.append(as_record(parsed))
    start = 0
    for index, record in enumerate(records):
        content = as_record(record.get("message")).get("content")
        if record.get("type") == "user" and isinstance(content, str):
            start = index + 1
    found: list[str] = []
    for record in records[start:]:
        for block in _blocks(record):
            item = as_record(block)
            if item.get("type") == "tool_result":
                found.append(_result_text(item))
    return "\n".join(found)


def run(payload: dict[str, object], out: TextIO) -> int:
    """Apply the guard to one PreToolUse(SendMessage) payload.

    Returns:
        0 always: a denial is the decision JSON on `out`, never a nonzero exit.

    """
    message = text_of(as_record(payload.get("tool_input")).get("message"))
    if not cited(message):
        return 0
    try:
        transcript = Path(text_of(payload.get("transcript_path"))).read_text(encoding="utf-8")
    except OSError:
        return 0
    reason = refusal(message, numbers_in(turn_results(transcript)))
    if reason is None:
        return 0
    decision: dict[str, dict[str, str]] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    out.write(json.dumps(decision))
    return 0


def main() -> int:
    """Read the harness payload and deny a message citing an unread transcript line, if armed.

    Returns:
        0 always: unarmed, unreadable and admitted all say nothing.

    """
    if not armed(OWN_SWITCH):
        return 0
    try:
        raw: object = json.load(sys.stdin)
    except ValueError:
        return 0
    return run(as_record(raw), sys.stdout)
