# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The readable transcript: one markdown line per record, and a gap never looks like a result.

- A `Segment` is `**[m:ss] SPEAKER:** text`, with hours once the call passes one. A segment
  diarization assigned no one says `unattributed`, a word no diarizer emits, never a stand-in
  label such as the baseline's `UNKNOWN`, which reads like a speaker;
- An `Unplaced` segment is `**[! unplaced segment N]** reason`. It has no timestamp at all,
  because it has no time: the baseline printed it as `[00:00]` (.claude/design/W255-audiostruct.md).

⚑ One line per record, in the records' order, so the transcript's body is a count over the input.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.audiostruct.records import Segment

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.audiostruct.records import Record

UNATTRIBUTED = "unattributed"
_MINUTE = 60
_HOUR = 60 * _MINUTE


def stamp(seconds: float) -> str:
    """Render a time offset, truncated to the second.

    Returns:
        `m:ss`, or `h:mm:ss` from one hour on.

    """
    whole = int(seconds)
    hours, rest = divmod(whole, _HOUR)
    minutes, secs = divmod(rest, _MINUTE)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def line(record: Record) -> str:
    """Render one record.

    Returns:
        its markdown line, with a hard break and no terminator.

    """
    if isinstance(record, Segment):
        speaker = record.speaker if record.speaker is not None else UNATTRIBUTED
        return f"**[{stamp(record.start)}] {speaker}:** {record.text.strip()}  "
    return f"**[! unplaced segment {record.index}]** {record.reason}  "


def markdown(title: str, records: Sequence[Record]) -> str:
    """Render a whole transcript.

    Returns:
        a heading, then one line per record, newline-terminated.

    """
    return "\n".join([f"# Transcript: {title}", "", *map(line, records)]) + "\n"
