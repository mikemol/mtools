# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑ `load_align_model` returns the model AND its metadata, and `align` needs both plus the device
# on every call. So the aligner factory binds all three and hands the runner a callable of
# (segments, audio) alone. The model is a torch module at runtime, typed `object` here.

from collections.abc import Iterable

def load_align_model(
    language_code: str,
    device: str,
    model_name: str | None = None,
    model_dir: str | None = None,
    model_cache_only: bool = False,
) -> tuple[object, dict[str, object]]: ...
def align(
    transcript: Iterable[object],
    model: object,
    align_model_metadata: dict[str, object],
    audio: object,
    device: str,
    interpolate_method: str = "nearest",
    return_char_alignments: bool = False,
    print_progress: bool = False,
    combined_progress: bool = False,
    progress_callback: object = None,
) -> dict[str, object]: ...
