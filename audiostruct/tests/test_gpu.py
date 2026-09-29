# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the whisperx bindings, with fakes in place of every library call.

No torch, no whisperx, no GPU. Each fake records its arguments, so the witnesses check what the
real library would have been handed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.audiostruct.gpu import aligner, diarizer, release, transcriber

if TYPE_CHECKING:
    from collections.abc import Callable

_RESULT: dict[str, object] = {"segments": []}


def test_transcriber_loads_once_and_passes_the_batch_size() -> None:
    """The model loads when the factory runs, and every call carries the bound batch size."""
    calls: list[tuple[object, int]] = []
    loads: list[str] = []

    def transcribe(audio: object, batch_size: int) -> dict[str, object]:
        calls.append((audio, batch_size))
        return _RESULT

    def load() -> Callable[[object, int], dict[str, object]]:
        loads.append("load")
        return transcribe

    model = transcriber(load, 4)
    assert model("a") is _RESULT
    assert model("b") is _RESULT
    assert loads == ["load"]
    assert calls == [("a", 4), ("b", 4)]


def test_aligner_binds_model_metadata_and_device_into_every_call() -> None:
    """The aligner hands align the loaded model, its metadata and the device on every call.

    ⚑ The runner calls the aligner with (segments, audio) alone, so a binding that dropped any
    of the three would pass the runner's witnesses and fail on the first real file.
    """
    seen: list[tuple[object, ...]] = []
    metadata: dict[str, object] = {"language": "en"}

    def align(
        segments: list[object], model: object, meta: dict[str, object], audio: object, device: str
    ) -> dict[str, object]:
        seen.append((segments, model, meta, audio, device))
        return _RESULT

    model = aligner(lambda: ("wav2vec", metadata), align, "cuda")
    segments: list[object] = [{"text": "x"}]
    assert model(segments, "clip") is _RESULT
    assert seen == [(segments, "wav2vec", metadata, "clip", "cuda")]


def test_diarizer_hands_the_token_to_the_builder_and_runs_both_calls_in_order() -> None:
    """The token reaches only the builder; each call makes the table, then assigns speakers."""
    log: list[object] = []
    aligned: dict[str, object] = {"segments": []}

    def make(token: str) -> Callable[[object], object]:
        log.append(("make", token))

        def run(audio: object) -> object:
            log.append(("table", audio))
            return "table"

        return run

    def assign(table: object, result: dict[str, object]) -> dict[str, object]:
        log.append(("assign", table, result is aligned))
        return _RESULT

    model = diarizer(make, assign, "hf_token")
    assert model("clip", aligned) is _RESULT
    assert log == [("make", "hf_token"), ("table", "clip"), ("assign", "table", True)]


def test_diarizer_refuses_an_aligned_result_that_is_not_an_object() -> None:
    """assign_word_speakers reads keys, so a non-object result is a TypeError before any call."""
    ran: list[str] = []

    def table(audio: object) -> object:
        ran.append(f"table {audio}")
        return "table"

    def assign(_table: object, result: dict[str, object]) -> dict[str, object]:
        ran.append("assign")
        return result

    model = diarizer(lambda _token: table, assign, "hf_token")
    with pytest.raises(TypeError):
        model("clip", ["not", "an", "object"])
    assert ran == []


def test_release_collects_before_emptying_the_cache() -> None:
    """Garbage is collected first, so the cache empties blocks a cycle was still holding."""
    order: list[str] = []

    def collect() -> int:
        order.append("collect")
        return 0

    def empty() -> None:
        order.append("empty")

    release(collect, empty)
    assert order == ["collect", "empty"]
