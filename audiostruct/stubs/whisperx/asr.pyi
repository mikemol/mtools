# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑ `load_model` and the pipeline's `transcribe`, the only asr calls the transcriber factory
# makes. The result is WhisperX's TypedDict at runtime; it is `dict[str, object]` here because
# records.normalize narrows every field itself and trusts none of them.

class FasterWhisperPipeline:
    def transcribe(
        self,
        audio: object,
        batch_size: int | None = None,
        num_workers: int = 0,
        language: str | None = None,
        task: str | None = None,
        chunk_size: int = 30,
        print_progress: bool = False,
        combined_progress: bool = False,
        verbose: bool = False,
        progress_callback: object = None,
    ) -> dict[str, object]: ...

def load_model(
    whisper_arch: str,
    device: str,
    device_index: int = 0,
    compute_type: str = "default",
    asr_options: dict[str, object] | None = None,
    language: str | None = None,
    vad_model: object = None,
    vad_method: str | None = "pyannote",
    vad_options: dict[str, object] | None = None,
    model: object = None,
    task: str = "transcribe",
    download_root: str | None = None,
    local_files_only: bool = False,
    threads: int = 4,
    use_auth_token: str | bool | None = None,
) -> FasterWhisperPipeline: ...
