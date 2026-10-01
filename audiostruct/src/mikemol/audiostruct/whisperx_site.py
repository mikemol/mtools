# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ONE module that imports whisperx and torch: the real Pipeline for the stage runner (W284).

⚑⚑ BUILDING THE PIPELINE LOADS NOTHING. Every model is behind a factory that stages.run_stage calls
when its stage begins, so `pipeline(...)` only binds names. That is what lets it be witnessed
without a GPU, a model download, or a token. Its witness runs in the gpu hub, and so does the
mutation grid (the audiostruct .venv carries the GPU set, operator 2026-09-29).

The bindings themselves, and their order, are gpu.py's and are witnessed there with fakes. This
module only says WHICH real function fills each seam, with the signatures stubs/ records and
tests/test_stub_authority.py holds to the installed packages.

⚑⚑ THE TOKEN IS A FILE PATH HERE, NOT A VALUE (design note D4). It is read when the diarize stage
begins (stages.run_stage), so a transcribe-only or align-only process never holds it.
"""

from __future__ import annotations

import gc
import warnings
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from mikemol.audiostruct.gpu import TranscribeFn, aligner, diarizer, release, transcriber
from mikemol.audiostruct.stages import Pipeline

# ⚑⚑ ONE WARNING, MATCHED EXACTLY, ONLY FOR THIS IMPORT (W298, reported by life after adoption).
# pyannote warns at import that torchcodec cannot load this host's FFmpeg: the host has FFmpeg
# 8.1.3 (libavutil.so.60), and torchcodec 0.7 (pinned under torch 2.8) supports 4 through 7. The
# warning names a decode path audiostruct never takes, because diarize is handed audio
# whisperx.audio already decoded through the ffmpeg CLI. It printed in the parent and in every
# stage child. `catch_warnings` restores the global filters when the block ends, so no other
# warning, from pyannote or anything else, is silenced. tests/test_whisperx_site.py checks both.
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore", message=r"\s*torchcodec is not installed correctly", category=UserWarning
    )
    from torch.cuda import empty_cache
    from whisperx import alignment, asr, audio, diarize


@dataclass(frozen=True, slots=True)
class Settings:
    """What the real models need, all from the caller: nothing here is guessed."""

    model: str  # a whisper architecture, e.g. large-v3
    device: str  # cuda or cpu
    compute_type: str  # float16 on the GPU
    batch_size: int  # 4 fits the 8 GiB card with Whisper alone (design note, measured baseline)
    language: str  # the alignment model is per language
    token_file: str  # the Hugging Face token's FILE; its contents are read only when diarizing


def _read_token(token_file: str) -> str:
    """Read the token file's contents when the diarize stage asks for them.

    Returns:
        the token, stripped of surrounding whitespace.

    """
    return Path(token_file).read_text(encoding="utf-8").strip()


def _load_transcriber(settings: Settings) -> TranscribeFn:
    return asr.load_model(
        settings.model,
        settings.device,
        compute_type=settings.compute_type,
        language=settings.language,
    ).transcribe


def _make_diarizer(device: str, token: str) -> diarize.DiarizationPipeline:
    return diarize.DiarizationPipeline(token=token, device=device)


def pipeline(settings: Settings) -> Pipeline:
    """Bind whisperx's real calls into the runner's seams. Loads no model and reads no token.

    Returns:
        the Pipeline stages.run_stage drives.

    """
    return Pipeline(
        load_audio=audio.load_audio,
        transcriber=partial(transcriber, partial(_load_transcriber, settings), settings.batch_size),
        aligner=partial(
            aligner,
            partial(alignment.load_align_model, settings.language, settings.device),
            alignment.align,
            settings.device,
        ),
        diarizer=partial(
            diarizer, partial(_make_diarizer, settings.device), diarize.assign_word_speakers
        ),
        token=partial(_read_token, settings.token_file),
        release=partial(release, gc.collect, empty_cache),
    )
