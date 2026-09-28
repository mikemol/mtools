# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for stage 1: every WhisperX segment in exactly one record, no default ever substituted.

Every input is a synthetic, WhisperX-shaped list written here. No audio and no real transcript
enters this tree.
"""

from __future__ import annotations

import json
import math
from typing import cast

import pytest

from mikemol.audiostruct.records import Segment, Unplaced, Word, normalize

_SOURCE = "synthetic call"

_GOOD: dict[str, object] = {
    "start": 1.5,
    "end": 3.25,
    "text": " Synthetic hello.",
    "speaker": "SPEAKER_00",
    "words": [
        {"word": "x", "text": "Synthetic", "start": 1.5, "end": 2.0, "score": 0.9},
        {"text": "42", "speaker": "SPEAKER_00"},
    ],
}


def test_one_record_per_segment_in_order() -> None:
    """A list mixing good and bad segments yields exactly one record each, `index` its position.

    ⚑ The count invariant: Segment + Unplaced == len(input), so a count over the output is a
    count over the input.
    """
    given: list[object] = [_GOOD, {"end": 1.0, "text": "no start"}, _GOOD, "not a segment"]
    records = normalize(_SOURCE, given)
    assert [(type(r), r.index) for r in records] == [
        (Segment, 0),
        (Unplaced, 1),
        (Segment, 2),
        (Unplaced, 3),
    ]
    assert {r.source for r in records} == {_SOURCE}


def test_well_formed_segment_keeps_every_field() -> None:
    """Timing, text verbatim, speaker and words all come through; an untimed word is None, not 0.0.

    ⚑ WhisperX's aligner leaves digits and symbols untimed; the baseline would have read 0.0.
    """
    (record,) = normalize(_SOURCE, [_GOOD])
    assert record == Segment(
        source=_SOURCE,
        index=0,
        start=1.5,
        end=3.25,
        speaker="SPEAKER_00",
        text=" Synthetic hello.",
        words=(
            Word(text="Synthetic", start=1.5, end=2.0, score=0.9, speaker=None),
            Word(text="42", start=None, end=None, score=None, speaker="SPEAKER_00"),
        ),
    )


def test_undiarized_segment_has_no_speaker() -> None:
    """A segment diarization assigned no one is `speaker=None`, never a stand-in like UNKNOWN."""
    (record,) = normalize(_SOURCE, [{"start": 0, "end": 1, "text": "x"}])
    assert isinstance(record, Segment)
    assert (record.speaker, record.words, record.start) == (None, (), 0.0)


@pytest.mark.parametrize(
    ("segment", "reason"),
    [
        ({"end": 1.0, "text": "x"}, "no start"),
        ({"start": 0.0, "text": "x"}, "no end"),
        ({"start": "0.0", "end": 1.0, "text": "x"}, "start is not a finite number"),
        ({"start": True, "end": 1.0, "text": "x"}, "start is not a finite number"),
        ({"start": 0.0, "end": math.inf, "text": "x"}, "end is not a finite number"),
        ({"start": 2.0, "end": 1.0, "text": "x"}, "end is before start"),
        ({"start": 0.0, "end": 1.0}, "text is absent or not a string"),
        ({"start": 0.0, "end": 1.0, "text": "x", "speaker": 3}, "speaker is not a string"),
        ({"start": 0.0, "end": 1.0, "text": "x", "words": {}}, "words is not a list"),
        (
            {"start": 0.0, "end": 1.0, "text": "x", "words": [{"text": "a"}, {}]},
            "word 1: text is absent or not a string",
        ),
        ({"start": 0.0, "end": 1.0, "text": "x", "words": ["a"]}, "word 0: it is not an object"),
        (
            {"start": 0.0, "end": 1.0, "text": "x", "words": [{"text": "a", "score": "high"}]},
            "word 0: score is not a finite number",
        ),
        ("a bare string", "segment is not an object"),
    ],
)
def test_unplaceable_segment_is_carried_with_its_reason(segment: object, reason: str) -> None:
    """Each shape the baseline would have defaulted is an `Unplaced` record naming what is wrong."""
    (record,) = normalize(_SOURCE, [segment])
    assert isinstance(record, Unplaced)
    assert record.reason == reason


def test_unplaced_raw_is_the_segment_verbatim() -> None:
    """`raw` is the segment's JSON with keys sorted, so it parses back to exactly the input."""
    segment: dict[str, object] = {"text": "x", "end": 1.0, "extra": [1, 2]}
    (record,) = normalize(_SOURCE, [segment])
    assert isinstance(record, Unplaced)
    # ⚑ cast, as //transcriptstruct's records does: json.loads is typed Any.
    assert cast("object", json.loads(record.raw)) == segment
    assert record.raw == json.dumps(segment, sort_keys=True)
