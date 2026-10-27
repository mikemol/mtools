# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Which announced next actions the SAME assistant turn goes on to carry out (W2052, host W44).

An announce row ("Running each alone.", "Let me read X") is not owed work if the turn that said it
then does it. `commitledger` attaches a row only by a card or file it NAMES, so every announce read
as open debt whatever the turn did (amr-skills' run of `--resolve` over 14 seed-3 rows: all 7
counted rows open at layer none). This is the turn-boundary layer: an announce is DISCHARGED when a
later `tool_use` follows it before the turn ends; only a row still unattached when the turn ends
is debt (github-8f's ruling, reading the text: the next tool_use after the sentence).

⚑ A TURN ENDS AT THE NEXT RECORD THAT BEGINS ONE (`turnstart.begins_turn`): a human prompt, a
wake, a notification or a peer message. A tool result and a Stop block's feedback continue the
turn they answer, so the tool_use that follows a Stop block is still the same turn's.
⚑ A SUBAGENT'S TOOL CALLS ARE NOT THIS TURN'S: sidechain records are ignored, so a Task's work does
not discharge the announce of the session that launched it.
⚑ THE SENTENCE'S OWN RECORD COUNTS WHEN IT CARRIES A tool_use: a record that holds both the
announcement and the call is discharged by itself.

CONSUMED BY: `--resolve --turns` (`commitrows.resolve`).
"""

from collections.abc import Collection, Iterable

from mikemol.transcriptstruct.blocks import blocks
from mikemol.transcriptstruct.records import AssistantRecord, Record, UserRecord
from mikemol.transcriptstruct.turnstart import begins_turn

TOOL_USE = "tool_use"


def _calls(record: AssistantRecord) -> bool:
    return any(block.kind == TOOL_USE for block in blocks(record))


def discharged(records: Iterable[Record], lines: Collection[int]) -> set[int]:
    """Find the announce lines whose turn goes on to make a tool call.

    Returns:
        the subset of `lines` (each an assistant record's line) followed, in the same turn, by an
        assistant record that holds a `tool_use` (or holding one itself); a line the transcript does
        not contain as an assistant record is never in the answer.

    """
    wanted = set(lines)
    waiting: list[int] = []
    found: set[int] = set()
    for record in records:
        if isinstance(record, UserRecord) and begins_turn(record):
            waiting = []
        elif isinstance(record, AssistantRecord) and not record.is_sidechain:
            if _calls(record):
                found.update(waiting)
                waiting = []
                if record.line in wanted:
                    found.add(record.line)
            elif record.line in wanted:
                waiting.append(record.line)
    return found
