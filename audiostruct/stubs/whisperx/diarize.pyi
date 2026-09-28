# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑ Diarization is TWO calls: the pipeline turns audio into a speaker table, then
# `assign_word_speakers` writes speakers into the aligned result. So the diarizer the runner sees
# is a wrapper over both. The table is a pandas DataFrame at runtime, typed `object` here
# because audiostruct only passes it from one call to the other.
#
# ⚑⚑ `token` IS THE HUGGING FACE SECRET (design note D4). Only the diarizer factory passes it.

class DiarizationPipeline:
    def __init__(
        self,
        model_name: str | None = None,
        token: str | None = None,
        device: str = "cpu",
        cache_dir: str | None = None,
    ) -> None: ...
    def __call__(
        self,
        audio: object,
        num_speakers: int | None = None,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
        return_embeddings: bool = False,
        progress_callback: object = None,
    ) -> object: ...

def assign_word_speakers(
    diarize_df: object,
    transcript_result: dict[str, object],
    speaker_embeddings: dict[str, list[float]] | None = None,
    fill_nearest: bool = False,
) -> dict[str, object]: ...
