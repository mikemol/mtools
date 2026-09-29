# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The three-stage runner: transcribe every file, then align every file, then diarize every file.

⚑ PIPELINED BY STAGE, NOT BY FILE, AND ONE MODEL RESIDENT AT A TIME. This is the measured shape of
the baseline (life/transcribe/transcribe.py): holding Whisper, the aligner and pyannote at once
ran out of memory on an 8 GiB GPU (2026-09-28). So each stage loads its model, runs it over every
file, drops its reference, and calls `release` (for the real models, `gc.collect()` and
`torch.cuda.empty_cache()`) BEFORE the next stage loads. The witnesses check the drop itself, not
only the call: a fake `release` holds a weak reference to the previous model and asserts it is dead.

⚑ NO torch AND NO whisperx HERE. Each loaded model is a plain callable, and the models come from
factories on `Pipeline`, so the order and the release are witnessed with fakes. The factories that
bind the real models arrive with the `[gpu]` extra (W264), typed by stubs, and hand back a bound
method, which holds the model exactly as long as the runner holds it.

⚑ A CALLABLE, NOT A `Protocol` WITH A METHOD. Measured (as in ratchet/keys.py): the mutation gate
addresses a def-site by name, so a Protocol's `...` stubs became three sites nothing calls, and all
three SURVIVED.

⚑⚑ THE HUGGING FACE TOKEN IS A SECRET AT THE EDGE (design note D4). It is read by `Pipeline.token`
only when the diarize stage begins, and handed only to the diarizer factory. Any error a stage
raises is rewritten as `StageError` naming the stage, the source label and the error's TYPE,
raised `from None`: a library's message can embed the token or the audio path, so neither the
message nor the original exception is kept as `__cause__` or printed context.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, cast

from mikemol.audiostruct.records import normalize

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from mikemol.audiostruct.records import Record

# A loaded speech-to-text model: one file's audio to a result with a `segments` list.
type Transcriber = Callable[[object], object]
# A loaded forced-alignment model: one file's segments and audio to a word-timed result.
type Aligner = Callable[[list[object], object], object]
# A loaded diarization pipeline: one file's audio and aligned result to a speaker-assigned result.
type Diarizer = Callable[[object, object], object]


@dataclass(frozen=True, slots=True)
class Pipeline:
    """The effects the runner needs, each injected so the order is witnessed with fakes."""

    load_audio: Callable[[str], object]
    transcriber: Callable[[], Transcriber]
    aligner: Callable[[], Aligner]
    diarizer: Callable[[str], Diarizer]
    token: Callable[[], str]
    release: Callable[[], None]


class StageError(Exception):
    """A stage failed. The message names the stage, the label and the error type, nothing more."""


def _segments(result: object) -> list[object]:
    """Narrow a stage's result to its segments list.

    Returns:
        the list.

    Raises:
        TypeError: if the result is not an object with a `segments` list.

    """
    found = cast("dict[str, object]", result).get("segments") if isinstance(result, dict) else None
    if not isinstance(found, list):
        msg = "result has no segments list"
        raise TypeError(msg)
    return cast("list[object]", found)


def _message(stage: str, label: str, exc: BaseException) -> str:
    """Rewrite a stage's error so that nothing from its message survives.

    ⚑ AN OSError ALSO NAMES ITS FILE (W293). Measured: diarize failed at load as
    `diarize: every source: FileNotFoundError`, and nothing said which file. `.filename` is the
    path the library tried to open, a separate attribute from the message, so it carries no
    token. The message text is still dropped.

    Returns:
        the stage, the label and the error's type name, plus the file for an OSError that has one.

    """
    text = f"{stage}: {label}: {type(exc).__name__}"
    if isinstance(exc, OSError):
        filename = cast("str | bytes | int | None", exc.filename)
        if filename is not None:
            text += f" {filename!r}"
    return text


_EVERY = "every source"


def _each(
    stage: str,
    labels: Sequence[str],
    pairs: Sequence[tuple[object, object]],
    step: Callable[[object, object], object],
) -> list[object]:
    """Run one stage's step over every source, in order.

    Returns:
        one result per source.

    Raises:
        StageError: naming the first source whose step fails.

    """
    out: list[object] = []
    for label, (first, second) in zip(labels, pairs, strict=True):
        try:
            out.append(step(first, second))
        except Exception as exc:
            raise StageError(_message(stage, label, exc)) from None
    return out


def _stage[M](
    stage: str,
    labels: Sequence[str],
    pairs: Sequence[tuple[object, object]],
    load: Callable[[], M],
    step: Callable[[M, object, object], object],
) -> list[object]:
    """Load one stage's model, run it over every source, and drop it.

    ⚑ The model's only reference is `model`, and `partial` holds a second one only for the
    duration of `_each`. Both are gone when this returns, so the caller's release frees it.

    Returns:
        one result per source.

    Raises:
        StageError: if the model fails to load, labelled for every source.

    """
    try:
        model = load()
    except Exception as exc:
        raise StageError(_message(stage, _EVERY, exc)) from None
    return _each(stage, labels, pairs, partial(step, model))


def _load_audio(pipeline: Pipeline, path: object, _: object) -> object:
    return pipeline.load_audio(str(path))


def _transcribe(model: Transcriber, clip: object, _: object) -> object:
    return model(clip)


def _align(model: Aligner, clip: object, result: object) -> object:
    return model(_segments(result), clip)


def _diarize(model: Diarizer, clip: object, result: object) -> object:
    return model(clip, result)


def _read(result: object, _: object) -> object:
    return _segments(result)


STAGES = ("transcribe", "align", "diarize")


def run_stage(
    stage: str, pipeline: Pipeline, sources: Sequence[tuple[str, str]], previous: Sequence[object]
) -> list[object]:
    """Run ONE stage over every source, then release its model.

    ⚑ EACH CALL LOADS ITS OWN AUDIO AND TAKES THE PREVIOUS STAGE'S RESULTS AS PLAIN DATA, so a stage
    can run in a process of its own under its own GPU lease (design note D3/O1, W281). whisperx's
    results are JSON objects, so `previous` survives a round-trip through a handoff file.

    A stage that fails raises `StageError`, and the model it was running is not released first.

    Args:
        stage: one of STAGES.
        pipeline: the injected effects.
        sources: `(label, path)` pairs; the label is what records and errors carry.
        previous: the prior stage's results, one per source; empty for transcribe.

    Returns:
        one result per source, in the order given.

    Raises:
        ValueError: for an unknown stage, or `previous` of the wrong length for the stage.

    """
    if stage not in STAGES:
        msg = f"unknown stage {stage!r}"
        raise ValueError(msg)
    if (stage == "transcribe") != (not previous):
        msg = f"{stage}: previous results do not fit this stage"
        raise ValueError(msg)
    labels = [label for label, _ in sources]
    paths: list[tuple[object, object]] = [(path, None) for _, path in sources]
    clips = _each("load", labels, paths, partial(_load_audio, pipeline))

    if stage == "transcribe":
        results = _stage(
            stage, labels, [(c, None) for c in clips], pipeline.transcriber, _transcribe
        )
    elif stage == "align":
        results = _stage(
            stage, labels, list(zip(clips, previous, strict=True)), pipeline.aligner, _align
        )
    else:
        # ⚑ THE TOKEN IS READ HERE AND NOWHERE ELSE, and only the factory ever holds it.
        def diarizer() -> Diarizer:
            return pipeline.diarizer(pipeline.token())

        results = _stage(stage, labels, list(zip(clips, previous, strict=True)), diarizer, _diarize)
    pipeline.release()
    return results


def records(
    sources: Sequence[tuple[str, str]], results: Sequence[object]
) -> list[tuple[str, list[Record]]]:
    """Read the last stage's results into records, per source.

    Returns:
        each label with its records, in the order given.

    """
    labels = [label for label, _ in sources]
    read = _each("read", labels, [(r, None) for r in results], _read)
    return [
        (label, normalize(label, cast("list[object]", segments)))
        for label, segments in zip(labels, read, strict=True)
    ]


def run(pipeline: Pipeline, sources: Sequence[tuple[str, str]]) -> list[tuple[str, list[Record]]]:
    """Transcribe, align and diarize every source, one stage at a time, in this process.

    Returns:
        each label with its records, in the order given.

    """
    results: list[object] = []
    for stage in STAGES:
        results = run_stage(stage, pipeline, sources, results)
    return records(sources, results)
