life → mtools: ask — a structured reader for audio (transcription + diarization)

## What's missing

life needed to transcribe the operator's own recorded phone calls (evidence in a billing dispute).
Nothing in the ecosystem does this:
- `summit capability whisper` and `summit capability speech-to-text` both miss;
- no `pyproject.toml` under `~/github` depends on whisper, faster-whisper or vosk;
- nothing is installed system-wide.

Because of a deadline, life built a one-off:
`~/github/life/transcribe/transcribe.py` (WhisperX 3.8.6 → faster-whisper large-v3 + wav2vec2
alignment + pyannote `speaker-diarization-community-1`), in its own uv sub-project on Python 3.13.
**This is a B1 re-derivation.** It belongs with transcriptstruct, as mtools' second reader of a
foreign format.

## What was measured (luthen, RTX 3070 Ti 8 GiB, ~6.5 GiB free with the desktop running)

- float16 / batch 8 with all three models resident → **CUDA OOM**.
- **Pipelined by stage** (Whisper over every file, then free; the aligner over every file, then
  free; diarization last) with float16 / batch 4 → 5 files, ~13 min of audio, done in ~1 minute,
  fully offline (`HF_HUB_OFFLINE=1`) after the first model fetch.
- Batch 8 OOMs even with Whisper *alone* resident. Batch size trades speed, not accuracy.
- pyannote 4 gated models need a HF token **only for the first download**. The token lives in
  `~/.config/life/hf-token` (mode 600), outside every repo.
- torchcodec could not find FFmpeg libs (`libavutil.so.5x`), which is harmless when you pass
  decoded arrays.
- Diarization mislabels some lines in short, fast back-and-forth, so a consumer must be able to
  correct labels.

## What "done" looks like

`mikemol-audiostruct` (or similar), pinned by sha:
- **Records, the transcriptstruct way:** one record per segment, with start, end, speaker, text,
  words and scores. Nothing is dropped, so a count of records is a count of segments.
- **Stage-pipelined by construction**, so it fits one consumer GPU. CPU fallback.
- **Diarization is optional**, so the reader works without a gated model.
- **A CLI**, e.g. `mikemol-audio transcribe --out DIR FILE…`, plus `--json`.
- ⚑ **Content is private by default:** no telemetry, no network after the model fetch, no
  transcript text in logs.

life will switch to it and delete `transcribe/` when it exists. Tracked as `life:W12`.
