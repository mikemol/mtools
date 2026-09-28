# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑ The waveform is a numpy array at runtime. It is typed `object` here because audiostruct only
# hands it back to whisperx and never reads it, so numpy stays out of the type surface.

SAMPLE_RATE: int

def load_audio(file: str, sr: int = ...) -> object: ...
