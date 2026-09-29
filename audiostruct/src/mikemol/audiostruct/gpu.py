# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The bindings from whisperx's call surface to the stage runner's seams (W269).

⚑⚑ NO whisperx IMPORT HERE. Each binding takes the library calls it makes as arguments, so every
function in this module runs under fakes in the light test environment, and the mutation grid
reaches each one. The one place that imports whisperx and hands its functions to these bindings
is the CLI edge (W265), which is where a GPU is.

The shapes come from whisperx 3.8.6, as stubs/whisperx records them (W268):
- `asr.load_model(...)` returns a pipeline whose `transcribe(audio, batch_size)` is the
  transcriber;
- `alignment.load_align_model` returns (model, metadata), and `alignment.align` needs both plus
  the device on EVERY call, so the aligner binds all three;
- diarization is TWO calls: `DiarizationPipeline(token=...)(audio)` makes a speaker table, then
  `assign_word_speakers(table, aligned)` writes speakers into the aligned result.

⚑ `release` collects garbage BEFORE emptying the CUDA cache. The runner has dropped its last
reference to the model, but a cycle can still hold it, and `empty_cache` only returns blocks
nothing points at.
"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable

    from mikemol.audiostruct.stages import Aligner, Diarizer, Transcriber

# `pipeline.transcribe(audio, batch_size)`.
type TranscribeFn = Callable[[object, int], dict[str, object]]
# `alignment.align(transcript, model, align_model_metadata, audio, device)`.
type AlignFn = Callable[[list[object], object, dict[str, object], object, str], dict[str, object]]
# `diarize.assign_word_speakers(diarize_df, transcript_result)`.
type AssignFn = Callable[[object, dict[str, object]], dict[str, object]]


def _transcribe(transcribe: TranscribeFn, batch_size: int, audio: object) -> object:
    return transcribe(audio, batch_size)


def transcriber(load: Callable[[], TranscribeFn], batch_size: int) -> Transcriber:
    """Load the speech-to-text model and bind its batch size.

    Returns:
        the transcriber the runner calls once per file.

    """
    return partial(_transcribe, load(), batch_size)


def _align(
    align: AlignFn,
    bound: tuple[object, dict[str, object], str],
    segments: list[object],
    audio: object,
) -> object:
    model, metadata, device = bound
    return align(segments, model, metadata, audio, device)


def aligner(
    load: Callable[[], tuple[object, dict[str, object]]], align: AlignFn, device: str
) -> Aligner:
    """Load the alignment model and bind it, its metadata and the device into every call.

    Returns:
        the aligner the runner calls with (segments, audio) alone.

    """
    model, metadata = load()
    return partial(_align, align, (model, metadata, device))


def _diarize(
    pipeline: Callable[[object], object], assign: AssignFn, audio: object, aligned: object
) -> object:
    """Make the speaker table, then write its speakers into the aligned result.

    Returns:
        the aligned result with speakers assigned.

    Raises:
        TypeError: if the aligned result is not an object; assign_word_speakers reads its keys.

    """
    if not isinstance(aligned, dict):
        msg = "aligned result is not an object"
        raise TypeError(msg)
    return assign(pipeline(audio), cast("dict[str, object]", aligned))


def diarizer(
    make: Callable[[str], Callable[[object], object]], assign: AssignFn, token: str
) -> Diarizer:
    """Build the diarization pipeline with the token, and wrap its two calls as one.

    ⚑⚑ THE TOKEN GOES TO `make` AND NOWHERE ELSE (design note D4): the wrapper holds the built
    pipeline, never the token.

    Returns:
        the diarizer the runner calls with (audio, aligned).

    """
    return partial(_diarize, make(token), assign)


def release(collect: Callable[[], int], empty_cache: Callable[[], None]) -> None:
    """Free a dropped model's memory: collect garbage first, then empty the CUDA cache."""
    collect()
    empty_cache()
