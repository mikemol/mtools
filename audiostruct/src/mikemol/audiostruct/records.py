# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Stage 1: WhisperX's segment list, read so that every segment lands in exactly one record.

WhisperX returns, per audio file, a list of segment objects: `start` and `end` in seconds, `text`,
an optional `speaker` once diarized, and `words` once aligned. This module turns that list into
two record kinds:

- `Segment`: a segment whose timing and text are well-formed. Its `speaker` is None when
  diarization assigned none, never a stand-in label. Each `Word` keeps its own timing, which the
  aligner leaves off digits and symbols, as None rather than 0.0;
- `Unplaced`: a segment that cannot be placed on the timeline or read as text. It carries the
  reason and the segment verbatim.

⚑ THE POSITIVE-CONTROL RULE, AT SEGMENT GRAIN: `normalize` returns exactly one record per input
segment, in order, with `index` its position. The baseline this replaces
(life/transcribe/transcribe.py) read a segment with `seg.get("start", 0.0)` and
`seg.get("speaker", "UNKNOWN")`, so a segment with no timing printed as `[00:00]`, looking like a
real one. Here a default is never substituted (.claude/design/W255-audiostruct.md, D2).

Nothing here imports torch or whisperx: the input is plain parsed JSON, so every case is witnessed
over synthetic data with no GPU and no audio.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Sequence

type Json = dict[str, object]


@dataclass(frozen=True, slots=True)
class Word:
    """One aligned word. A timing or score the aligner did not give is None."""

    text: str
    start: float | None
    end: float | None
    score: float | None
    speaker: str | None


@dataclass(frozen=True, slots=True)
class Segment:
    """One well-formed segment, `index` its position in the input list."""

    source: str
    index: int
    start: float
    end: float
    speaker: str | None
    text: str
    words: tuple[Word, ...]


@dataclass(frozen=True, slots=True)
class Unplaced:
    """A segment that cannot be placed or read. `raw` is its JSON, keys sorted. Never skipped."""

    source: str
    index: int
    raw: str
    reason: str


type Record = Segment | Unplaced


class _ShapeError(Exception):
    """A segment is not the shape WhisperX documents. The message is the `Unplaced` reason."""


def _number(value: object, key: str) -> float:
    """Narrow a time or score.

    Returns:
        the value as a float.

    Raises:
        _ShapeError: if it is not a finite number.

    """
    # ⚑ bool IS AN int: `True` is not a time.
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        msg = f"{key} is not a finite number"
        raise _ShapeError(msg)
    return float(value)


def _required(body: Json, key: str) -> float:
    """Read a time the segment must have.

    Returns:
        the value as a float.

    Raises:
        _ShapeError: if it is absent or not a finite number.

    """
    if key not in body:
        msg = f"no {key}"
        raise _ShapeError(msg)
    return _number(body[key], key)


def _optional(body: Json, key: str) -> float | None:
    """Read a time or score the aligner may leave off.

    Returns:
        the value as a float, or None if it is absent.

    """
    return _number(body[key], key) if key in body else None


def _speaker(body: Json) -> str | None:
    """Read an optional speaker label.

    Returns:
        the label, or None if diarization assigned none.

    Raises:
        _ShapeError: if it is present and not a string.

    """
    value = body.get("speaker")
    if value is None or isinstance(value, str):
        return value
    msg = "speaker is not a string"
    raise _ShapeError(msg)


def _text(body: Json, key: str) -> str:
    """Read the required text under `key`.

    ⚑⚑ A SEGMENT'S TEXT IS "text", A WORD'S IS "word" (W296). Measured on the first real run
    (2026-09-30, jfk.flac): WhisperX's aligned words are {"word", "start", "end", "score"}. The
    synthetic fixtures had guessed "text", so every real segment landed Unplaced. There is no
    fallback from one key to the other: a word without "word" is Unplaced with that reason.

    Returns:
        the text, verbatim.

    Raises:
        _ShapeError: if it is absent or not a string.

    """
    value = body.get(key)
    if not isinstance(value, str):
        msg = f"{key} is absent or not a string"
        raise _ShapeError(msg)
    return value


def _object(value: object, what: str) -> Json:
    """Narrow a parsed JSON value to an object.

    Returns:
        the object.

    Raises:
        _ShapeError: if it is not one.

    """
    if not isinstance(value, dict):
        msg = f"{what} is not an object"
        raise _ShapeError(msg)
    return cast("Json", value)


def _words(body: Json) -> tuple[Word, ...]:
    """Read the optional aligned words.

    Returns:
        one Word per entry, or none if the segment was not aligned.

    Raises:
        _ShapeError: naming the word, if any entry is malformed.

    """
    value = body.get("words", [])
    if not isinstance(value, list):
        msg = "words is not a list"
        raise _ShapeError(msg)
    words: list[Word] = []
    for n, entry in enumerate(cast("list[object]", value)):
        try:
            word = _object(entry, "it")
            words.append(
                Word(
                    text=_text(word, "word"),
                    start=_optional(word, "start"),
                    end=_optional(word, "end"),
                    score=_optional(word, "score"),
                    speaker=_speaker(word),
                )
            )
        except _ShapeError as exc:
            msg = f"word {n}: {exc}"
            raise _ShapeError(msg) from None
    return tuple(words)


def _segment(source: str, index: int, value: object) -> Segment:
    """Read one segment.

    Returns:
        the Segment.

    Raises:
        _ShapeError: if it cannot be placed or read.

    """
    body = _object(value, "segment")
    start, end = _required(body, "start"), _required(body, "end")
    if end < start:
        msg = "end is before start"
        raise _ShapeError(msg)
    return Segment(source, index, start, end, _speaker(body), _text(body, "text"), _words(body))


def normalize(source: str, segments: Sequence[object]) -> list[Record]:
    """Read WhisperX's segment list for one audio file.

    Args:
        source: the label the records carry, not necessarily a path.
        segments: the parsed `segments` list.

    Returns:
        exactly one record per segment, in order.

    """
    records: list[Record] = []
    for index, value in enumerate(segments):
        try:
            records.append(_segment(source, index, value))
        except _ShapeError as exc:
            raw = json.dumps(value, sort_keys=True, default=repr)
            records.append(Unplaced(source, index, raw, str(exc)))
    return records
