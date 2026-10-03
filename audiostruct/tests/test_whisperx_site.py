# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the one whisperx import site: each seam gets its real call, and nothing loads.

The whisperx functions a factory would call are replaced with recorders on the imported modules,
so no model is downloaded and no GPU is touched. What is checked is WHICH function each seam
reaches and WHAT it is handed.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import warnings
from typing import TYPE_CHECKING

from mikemol.audiostruct import whisperx_site
from mikemol.audiostruct.whisperx_site import Settings, pipeline

# ⚑ The same scoped filter as the site's own import (W298): this module imports whisperx directly
# to patch its loaders, so without it the test run itself would print the torchcodec warning.
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore", message=r"\s*torchcodec is not installed correctly", category=UserWarning
    )
    from whisperx import alignment, asr, audio, diarize

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _settings(token_file: str) -> Settings:
    return Settings(
        model="large-v3",
        device="cuda",
        compute_type="float16",
        batch_size=4,
        language="en",
        token_file=token_file,
    )


class _Model:
    def __init__(self, log: list[object]) -> None:
        self.log = log

    def transcribe(self, audio_: object, batch_size: int) -> dict[str, object]:
        self.log.append(("transcribe", audio_, batch_size))
        return {"segments": []}


def test_building_the_pipeline_loads_no_model_and_reads_no_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """pipeline() only binds: no load_model, no load_align_model, no DiarizationPipeline, no read.

    ⚑ A pipeline that loaded at build time would hold all three models at once, the
    out-of-memory the stage runner exists to avoid, and would read the token in every stage.
    """
    log: list[object] = []

    def load_model(_arch: str, _device: str, **_kwargs: str) -> None:
        log.append("load_model")

    def load_align_model(_language: str, _device: str) -> None:
        log.append("load_align")

    def make_diarizer(**_kwargs: str) -> None:
        log.append("diarizer")

    monkeypatch.setattr(asr, "load_model", load_model)
    monkeypatch.setattr(alignment, "load_align_model", load_align_model)
    monkeypatch.setattr(diarize, "DiarizationPipeline", make_diarizer)
    built = pipeline(_settings(str(tmp_path / "absent")))
    assert log == []
    assert built.load_audio is audio.load_audio


def test_each_factory_reaches_its_whisperx_call_with_the_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The transcriber, aligner and diarizer each call the right function with the settings."""
    log: list[object] = []

    def load_model(arch: str, device: str, **kwargs: str) -> _Model:
        log.append(("load_model", arch, device, kwargs))
        return _Model(log)

    def load_align_model(language: str, device: str) -> tuple[object, dict[str, object]]:
        log.append(("load_align", language, device))
        return "wav2vec", {}

    def table(_audio: object) -> object:
        return "table"

    def make_diarizer(**kwargs: str) -> object:
        log.append(("diarizer", kwargs))
        return table

    monkeypatch.setattr(asr, "load_model", load_model)
    monkeypatch.setattr(alignment, "load_align_model", load_align_model)
    monkeypatch.setattr(diarize, "DiarizationPipeline", make_diarizer)
    token_file = tmp_path / "token"
    token_file.write_text("hf_value\n", encoding="utf-8")
    built = pipeline(_settings(str(token_file)))

    built.transcriber()("clip")
    built.aligner()
    built.diarizer(built.token())
    assert log == [
        ("load_model", "large-v3", "cuda", {"compute_type": "float16", "language": "en"}),
        ("transcribe", "clip", 4),
        ("load_align", "en", "cuda"),
        ("diarizer", {"token": "hf_value", "device": "cuda"}),
    ]


def test_the_token_is_read_from_its_file_only_when_asked(tmp_path: Path) -> None:
    """token() reads the file's stripped contents at call time, not at build time."""
    token_file = tmp_path / "token"
    built = pipeline(_settings(str(token_file)))
    token_file.write_text("  hf_later \n", encoding="utf-8")
    assert built.token() == "hf_later"
    assert whisperx_site.Settings is Settings


def test_importing_the_site_makes_cublas12_resolvable_by_soname() -> None:
    """After the import, a bare-soname dlopen of each CUDA 12 cuBLAS library finds it loaded.

    ⚑⚑ THIS IS ctranslate2's OWN LOOKUP (W271). It dlopens `libcublas.so.12` by soname at its
    first GEMM; torch's cu13 wheels ship none, and the default search path has none, so without
    the nvidia-cublas-cu12 wheel the decode fails. RTLD_NOLOAD only succeeds for a library already
    in the process (otherwise CDLL raises OSError), so the check needs no GPU. F-armed by
    uninstalling that wheel (the import itself then refuses); removing only the preload call
    stays green, because torch 2.14's loader maps the wheel too (W271).
    """
    loaded = [
        ctypes.CDLL(name, mode=os.RTLD_NOLOAD | os.RTLD_GLOBAL) for name in whisperx_site.CUBLAS12
    ]
    assert len(loaded) == len(whisperx_site.CUBLAS12)


# A fresh interpreter imports the site (this process has it cached), then raises an unrelated
# UserWarning, so both halves of the claim are observed on stderr.
_PROBE = (
    "import warnings\n"
    "import mikemol.audiostruct.whisperx_site\n"
    "warnings.warn('w298-probe-still-prints', UserWarning, stacklevel=1)\n"
)


def test_importing_the_site_prints_no_torchcodec_warning_and_silences_nothing_else() -> None:
    """The torchcodec/FFmpeg warning is gone at import, and a later UserWarning still prints.

    ⚑ Reported by life after adoption (W298): the warning printed once per process, three or four
    times a run, for a decode path audiostruct never takes. The filter is scoped to the import by
    `catch_warnings`, so the probe after it must still reach stderr.
    """
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
    )
    assert proc.returncode == 0, proc.stderr
    assert "torchcodec" not in proc.stderr
    assert "w298-probe-still-prints" in proc.stderr
