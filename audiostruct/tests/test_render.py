# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the readable transcript: a gap is marked as a gap, never printed as a result.

Every record is synthetic, built here or by `normalize` over an inline WhisperX-shaped list.
"""

from __future__ import annotations

import pytest

from mikemol.audiostruct.records import Segment, Unplaced, normalize
from mikemol.audiostruct.render import UNATTRIBUTED, line, markdown, stamp

_SOURCE = "synthetic call"


def _segment(start: float, speaker: str | None, text: str) -> Segment:
    """Build a segment with no words.

    Returns:
        the Segment.

    """
    return Segment(_SOURCE, 0, start, start + 1.0, speaker, text, ())


def test_segment_line_carries_time_speaker_and_text() -> None:
    """A segment is its start, its speaker and its text, stripped of WhisperX's leading space."""
    assert line(_segment(75.9, "SPEAKER_01", " Synthetic hello. ")) == (
        "**[1:15] SPEAKER_01:** Synthetic hello.  "
    )


def test_unattributed_segment_is_not_a_stand_in_speaker() -> None:
    """A segment with no speaker says `unattributed`, never UNKNOWN, which reads as a speaker."""
    rendered = line(_segment(0.0, None, "x"))
    assert rendered == f"**[0:00] {UNATTRIBUTED}:** x  "
    assert "UNKNOWN" not in rendered


def test_unplaced_segment_is_marked_and_has_no_time() -> None:
    """An unplaced segment is a `!` line naming its position and reason, with no `[0:00]`.

    ⚑ The baseline printed a segment with no timing as `[00:00]`, exactly like a real one.
    """
    rendered = line(Unplaced(_SOURCE, 4, "{}", "no start"))
    assert rendered == "**[! unplaced segment 4]** no start  "
    assert "0:00" not in rendered


def test_transcript_has_one_line_per_record_in_order() -> None:
    """The body under the heading is exactly one line per record, so it counts the input."""
    records = normalize(
        _SOURCE,
        [
            {"start": 0, "end": 1, "text": "a"},
            {"end": 1, "text": "b"},
            {"start": 2, "end": 3, "text": "c"},
        ],
    )
    assert markdown("A synthetic call", records).splitlines() == [
        "# Transcript: A synthetic call",
        "",
        f"**[0:00] {UNATTRIBUTED}:** a  ",
        "**[! unplaced segment 1]** no start  ",
        f"**[0:02] {UNATTRIBUTED}:** c  ",
    ]


@pytest.mark.parametrize(
    ("seconds", "shown"),
    [(0.0, "0:00"), (59.99, "0:59"), (60.0, "1:00"), (3599.0, "59:59"), (3725.5, "1:02:05")],
)
def test_stamp_truncates_and_grows_hours(seconds: float, shown: str) -> None:
    """Offsets truncate to the second and gain an hours field from one hour on."""
    assert stamp(seconds) == shown
