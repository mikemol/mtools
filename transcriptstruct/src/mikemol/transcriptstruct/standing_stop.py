# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W513: standing rule 8 at Stop — a hold on the operator set this turn is asked this turn.

Operator ruling 2026-10-03: "a hold set this turn" is read from the TRANSCRIPT. Since the last
real user record, every Bash tool_use running `mikemol-paths-forward` with `--blocked-kind human`
must be paired with an AskUserQuestion tool_use in that same span. A hold is paired when an
AskUserQuestion in the span names its symbol; a hold whose symbol cannot be read is paired by any
AskUserQuestion in the span.

The transcript is read by `mikemol.transcriptstruct.records`, not re-parsed here. ⚑ IT LIVES
IN THIS DISTRIBUTION, NOT IN `mikemol.hooks`, because a hooks module importing a sibling
distribution broke three ways when tried (W513): bazel's generated `mikemol/__init__.py` makes
the namespace a regular package so only one root resolves, the `//hooks:venv` check installs
hooks alone, and adopters `uv add mikemol-hooks` without this package. The launcher,
`hooks/bin/mikemol-hook-standing-stop`, stays with the other hook launchers.

⚑ LOOP SAFETY: when `stop_hook_active` is true this NEVER blocks, since Claude is already
continuing because of a Stop block and a second one would trap the turn. ⚑ CLOSED ONCE PER
TURN (operator ruling 2026-10-03): a payload or transcript that cannot be read BLOCKS with the
reason when stop_hook_active is not true, so the failure surfaces; when it is true, the reason
goes to stderr and the turn ends. Unparseable input counts as not active.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path
from typing import cast

from mikemol.transcriptstruct.records import AssistantRecord, Record, UserRecord, read_path

_TOOL = "mikemol-paths-forward"
_SYMBOL = re.compile(r"\bW\d+\b")


def _blocks(content: object) -> list[dict[str, object]]:
    """Return the dict blocks of a content tuple; a string content has none.

    Returns:
        the blocks that are objects.

    """
    if not isinstance(content, tuple):
        return []
    return [cast("dict[str, object]", b) for b in content if isinstance(b, dict)]


def is_real_user(record: Record) -> bool:
    """Return whether a record is a message the operator typed, not tool output or meta.

    Returns:
        True for a main-chain, non-meta, non-summary user record carrying text.

    """
    if not isinstance(record, UserRecord) or record.is_sidechain or record.is_compact_summary:
        return False
    if record.raw.get("isMeta") is True:
        return False
    if isinstance(record.content, str):
        return True
    kinds = {b.get("type") for b in _blocks(record.content)}
    return "text" in kinds and "tool_result" not in kinds


def _tool_uses(record: Record) -> list[dict[str, object]]:
    """Return the tool_use blocks of a main-chain assistant record.

    Returns:
        the tool_use blocks.

    """
    if not isinstance(record, AssistantRecord) or record.is_sidechain:
        return []
    return [b for b in _blocks(record.content) if b.get("type") == "tool_use"]


def _words(command: str) -> list[str]:
    """Split a command line into words, falling back to whitespace on a quoting error.

    Returns:
        the words.

    """
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def hold_symbol(command: str) -> str | None:
    """Return the card a human-hold command sets, '' when unreadable, None when not a hold.

    Returns:
        the symbol, '' for a hold whose symbol cannot be read, or None.

    """
    words = _words(command)
    if not any(Path(w).name == _TOOL for w in words):
        return None
    pairs = list(zip(words, [*words[1:], ""], strict=True))
    human = any(
        w == "--blocked-kind=human" or (w == "--blocked-kind" and nxt == "human")
        for w, nxt in pairs
    )
    if not human:
        return None
    for w, nxt in pairs:
        if w == "--update" and _SYMBOL.fullmatch(nxt):
            return nxt
    found = _SYMBOL.search(command)
    return found.group(0) if found else ""


def _is_paired(symbol: str, asked: list[str]) -> bool:
    """Return whether a hold is answered by an AskUserQuestion in the span.

    Returns:
        True when some question names the symbol, or the symbol is unreadable and any was asked.

    """
    if not symbol:
        return bool(asked)
    return any(re.search(rf"\b{symbol}\b", a) for a in asked)


def unpaired_holds(records: list[Record]) -> list[str]:
    """Return the human holds set since the last real user record with no AskUserQuestion.

    Returns:
        the unpaired symbols in order ('' for a hold whose symbol could not be read).

    """
    start = 0
    for index, record in enumerate(records):
        if is_real_user(record):
            start = index + 1
    holds: list[str] = []
    asked: list[str] = []
    for record in records[start:]:
        for use in _tool_uses(record):
            raw_input = use.get("input")
            body = cast("dict[str, object]", raw_input) if isinstance(raw_input, dict) else {}
            if use.get("name") == "AskUserQuestion":
                asked.append(json.dumps(body))
                continue
            command = body.get("command")
            if use.get("name") == "Bash" and isinstance(command, str):
                symbol = hold_symbol(command)
                if symbol is not None:
                    holds.append(symbol)
    return [s for s in holds if not _is_paired(s, asked)]


def cannot(why: str, *, active: bool) -> tuple[dict[str, str] | None, str | None]:
    """Report a check that could not run: a block when not active, else a stderr note.

    Returns:
        (block decision, None) when not active; (None, note) when active.

    """
    reason = f"standing-stop (rule 8) could not run: {why}; not checked"
    if active:
        return None, reason
    return {"decision": "block", "reason": reason}, None


def decide(payload: dict[str, object]) -> tuple[dict[str, str] | None, str | None]:
    """Decide a Stop payload: the block JSON, and a non-blocking note for stderr.

    Returns:
        (block decision or None, note or None).

    """
    active = payload.get("stop_hook_active") is True
    path = payload.get("transcript_path")
    if not isinstance(path, str) or not path:
        return cannot("no transcript_path in the payload", active=active)
    if not Path(path).is_file():
        return cannot(f"transcript {path} is not readable", active=active)
    if active:
        return None, None
    missing = unpaired_holds(list(read_path(Path(path))))
    if not missing:
        return None, None
    named = ", ".join(s or "(unnamed card)" for s in missing)
    reason = (
        f"Standing rule 8: {named} set blocked_kind human this turn with no AskUserQuestion "
        "naming it. Ask the operator now via AskUserQuestion, naming each card."
    )
    return {"decision": "block", "reason": reason}, None


def main() -> int:
    """Read a Stop payload on stdin and print a block decision when rule 8 is unmet.

    Returns:
        0 always; an unreadable payload blocks once (unparseable counts as not active).

    """
    try:
        payload = cast("object", json.load(sys.stdin))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        decision, note = cannot(f"payload is not JSON ({exc})", active=False)
    else:
        if isinstance(payload, dict):
            decision, note = decide(cast("dict[str, object]", payload))
        else:
            decision, note = cannot("payload is not an object", active=False)
    if note:
        sys.stderr.write(note + "\n")
    if decision:
        sys.stdout.write(json.dumps(decision) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
