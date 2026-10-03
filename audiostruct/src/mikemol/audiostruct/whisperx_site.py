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

import ctypes
import gc
import importlib.util
import warnings
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from mikemol.audiostruct.gpu import TranscribeFn, aligner, diarizer, release, transcriber
from mikemol.audiostruct.stages import Pipeline

# ⚑⚑ CUDA 12 cuBLAS, PRELOADED, BECAUSE ctranslate2 IS A CUDA 12 BUILD (W271, operator
# 2026-10-03). torch runs on CUDA 13 (requirements-gpu-overrides.txt), and its wheels ship only
# libcublas.so.13. ctranslate2 4.8.2 dlopens libcublas.so.12 by soname at its first GEMM, which
# finds nothing on the default search path: without the nvidia-cublas-cu12 wheel the decode fails
# with "Library libcublas.so.12 is not found" (measured 2026-10-03). Loading that wheel's two
# libraries RTLD_GLOBAL first makes the dlopen find them already in the process. ⚑ torch 2.14's
# own import-time loader ALSO maps nvidia/cublas/lib when the wheel is present (measured: the
# gate decoded with this call removed), so the load-bearing part is the wheel; this call keeps
# the guarantee from resting on that torch internal, and fails loudly at import when the wheel is
# missing instead of at the first GEMM. Both cuBLAS versions coexist (torch and faster-whisper
# both ran on the GPU in one process). Retire this when ctranslate2 ships CUDA 13.
CUBLAS12 = ("libcublasLt.so.12", "libcublas.so.12")


def _preload_cublas12() -> None:
    """Load the nvidia-cublas-cu12 wheel's libraries into the process, globally.

    Raises:
        ModuleNotFoundError: if the wheel is not installed; the decode would fail later without it.

    """
    spec = importlib.util.find_spec("nvidia.cublas")
    if spec is None or not spec.submodule_search_locations:
        msg = "nvidia-cublas-cu12 is not installed; ctranslate2 needs libcublas.so.12"
        raise ModuleNotFoundError(msg)
    libdir = Path(next(iter(spec.submodule_search_locations))) / "lib"
    for name in CUBLAS12:
        ctypes.CDLL(str(libdir / name), mode=ctypes.RTLD_GLOBAL)


_preload_cublas12()

# ⚑⚑ ONE WARNING, MATCHED EXACTLY, ONLY FOR THIS IMPORT (W298, reported by life after adoption).
# pyannote warned at import that torchcodec could not load this host's FFmpeg 8.1.3
# (libavutil.so.60): torchcodec 0.7, pinned under torch 2.8, supported 4 through 7. torchcodec
# 0.17 (W271) loaded it without the warning in the 2026-10-03 gate; the filter stays so that a
# torchcodec/FFmpeg drift cannot reopen it. The warning names a decode path audiostruct never
# takes, because diarize is handed audio whisperx.audio already decoded through the ffmpeg CLI.
# `catch_warnings` restores the global filters when the block ends, so no other warning, from
# pyannote or anything else, is silenced. tests/test_whisperx_site.py checks both.
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
