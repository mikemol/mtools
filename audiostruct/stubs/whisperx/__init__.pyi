# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑ EMPTY ON PURPOSE. whisperx 3.8.6 ships no py.typed, and its top-level `load_model`, `align`
# and friends are `(*args, **kwargs)` wrappers that lazily import a submodule. A typed signature
# here would describe nothing the runtime checks. The stage runner's factories import from the
# submodules (`whisperx.audio`, `whisperx.asr`, `whisperx.alignment`, `whisperx.diarize`), which
# carry the real signatures, and those are what these stubs declare (W268, design note D5).
