# W255 — audiostruct design note

Asked for by life (letter 2026-09-28, life:W12): absorb `life/transcribe/transcribe.py`
(117 lines, WhisperX) into an mtools distribution, `mikemol-audiostruct`.

## The measured baseline (life/transcribe/transcribe.py, read 2026-09-28)

- **Pipelined by stage, not by file.** Whisper (large-v3, float16) transcribes every file, and
  then it is freed. The aligner aligns every file, and then it is freed. Diarization (pyannote,
  gated weights, HF token) runs last. Only one model is resident at a time.
- **Measured memory:** holding all three models at once ran out of memory on the 8 GiB GPU.
  Batch 8 ran out of memory even with Whisper alone resident, with about 6.5 GiB free after the
  desktop's own use. Batch 4 fits. Batch size changes speed, not accuracy.
- **Outputs:** `<stem>.json` holds every aligned segment (start, end, speaker, words), and
  `<stem>.md` holds `[mm:ss] SPEAKER_nn: text`. Its docstring says "none is dropped", but that
  is not checked: `seg.get("start", 0.0)` and `seg.get("speaker", "UNKNOWN")` silently
  substitute defaults. A segment with no timing prints as `[00:00]`, indistinguishable from a
  real one.
- **Secrets:** the HF token file is read and passed through; nothing redacts it from errors.
- **Typing:** it uses `dict[str, Any]` throughout, and whisperx ships no py.typed.

## Decisions

**D1 — Split a pure layer from an effectful edge.** This is the icsstruct shape (lexical and
expand are pure; source is the edge).
- `records.py` (pure): normalize WhisperX's per-file output (a `segments` list of dicts) into
  typed records. No torch and no whisperx import. All witnesses run over synthetic
  WhisperX-shaped dicts, so CI needs no GPU and no audio.
- `render.py` (pure): the markdown transcript from records.
- `stages.py` (edge): the three-stage runner. It is the only module that imports
  torch/whisperx, which ship as an optional extra (`[gpu]`). Its seams are a `Protocol` per
  stage, so the pipeline order and the free-between-stages rule can be tested with fakes.

**D2 — Record shape, against transcriptstruct's.** Use frozen, slotted dataclasses, one per
shape, plus a carried remainder, exactly as transcriptstruct keeps `UnknownRecord` and
`MalformedLine` and icsstruct keeps `Malformed`.
- `Segment(source, index, start, end, speaker, text, words)`.
  - `speaker: str | None`. None means diarization assigned none; it is never "UNKNOWN".
  - `words: tuple[Word, ...]`, where `Word(text, start, end, score, speaker)` has optional
    timings. WhisperX's aligner leaves digits and symbols untimed, and that is recorded as
    None, not 0.0.
- `Unplaced(source, index, raw, reason)` is a segment the normalizer cannot place: missing or
  non-numeric start/end, end < start, or non-string text. It is carried, never defaulted. This
  closes the baseline's silent `[00:00]`.
- The invariant witnessed: the count of `Segment` plus `Unplaced` equals `len(segments)` in
  the input, per file. That is lexical's "every line in exactly one record" at segment grain.
- `source` is a label, not a path, when the caller gives one. The audio is the operator's own
  calls, so the label discipline is the one icsstruct uses for secret URLs.

**D3 — GPU admission goes through `mikemol-membudget hold`, not a new mechanism.**
- `fence/membudget_cli.py` already has `hold N [LABEL] -- CMD`: "the ledger without the fence,
  for a resource no cap can enforce — CUDA contexts, a device's memory". It uses a unitless
  ledger TOTAL (here, MiB of VRAM), and says on every admission that nothing enforces the
  number. That matches the case exactly: VRAM cannot be cgroup-capped.
- One lease per **stage**, not per run. The pipeline frees between stages, so the lease should
  track what is resident. The stage sizes come from the measured baseline. Whisper at batch 4
  is under 6.5 GiB. Aligner and pyannote are **UNMEASURED**, so they are measured at stage-2
  time, not guessed.
- Open (O1): `hold` wraps a *command*. So either each stage runs as a subprocess under `hold`
  (the CLI re-invokes itself with `--stage N`, and hands off intermediate results as JSON on
  disk), or fence grows an in-process lease API. Recommend the subprocess form: it needs no
  fence change, and a crashed stage releases its lease through the kernel, as every membudget
  claim does. This goes to fence as an ask only if the subprocess form measures wrong.

**D4 — The token is a secret at the edge.** It is read once, in the diarize stage only. Errors
from the pipeline are rewritten `from None` with the type name only, as `source.SourceError`
does. The witness plants a token in a stub reader and asserts it is absent from every repr and
every traceback.

**D5 — Types.** whisperx and pyannote are untyped. Their surface in `stages.py` is 5 calls:
`load_audio`, `load_model(...).transcribe`, `load_align_model`, `align`,
`DiarizationPipeline(...)()` and `assign_word_speakers`. That is stubbed under `stubs/` and
checked by stubtest, as W258 did for icalendar. It is only needed once the `[gpu]` extra is
installed in some environment. The stubtest witness **refuses** when the extra is absent; a
skip would read green over nothing, so it is not allowed to skip. Open (O2): whether bazel can
stage torch at all. If it cannot, `stages.py` lives outside the bazel graph's test set, and
this note must say so rather than letting the gap read as coverage.

## Amendments

- **D1, amended at W263 (dd02a9f):** the stage seams are plain callables, not Protocols. The
  mutation grid addresses def-sites by name, so the Protocols' `...` stubs became three sites
  nothing calls, and all three SURVIVED. The real factories hand back bound methods.
- **O2, first half measured (W267, 2026-09-28):** the extra RESOLVES. `uv pip compile` of bare
  `whisperx`, for py3.13 and x86_64-manylinux_2_28 with hashes, gives 118 packages, all from
  plain PyPI with no extra index:
  - whisperx 3.8.6, pyannote-audio 4.0.7, faster-whisper 1.2.1 and ctranslate2 4.8.2;
  - torch and torchaudio 2.8.0, and triton 3.4.0;
  - 14 `nvidia-*-cu12` wheels (the CUDA runtime is 12.8.90, cudnn 9.10.2.21).

  The CUDA runtime therefore arrives inside the wheels, which is what luthen's executor needs
  ("bring your own CUDA runtime; the driver comes from the host", luthen reply to W270). The
  host driver is 615.71, which is new enough for CUDA 12.8. **Not yet measured:** whether
  rules_python `pip.parse` stages this lock as a hub. That is the second half of W267.
- **The GPU executor (W270 → luthen:W229):** one RTX 3070 Ti with 8192 MiB, shared with the
  desktop, so there is at most one GPU slot. The one-model-at-a-time rule is therefore required,
  not optional.

## Waypoints minted from this note

- W262: records.py + render.py over synthetic WhisperX dicts (the pure layer; the count
  invariant; `Unplaced`), plus the distribution skeleton.
- W263: stages.py behind per-stage Protocols; fakes witness the order and the free between
  stages; token redaction (D4).
- W264: whisperx stubs + stubtest (D5), and settle O2.
- W265: the `mikemol-audio` CLI, with one `membudget hold` per stage via `--stage` re-invoke
  (D3/O1). The aligner and pyannote leases are measured on the real GPU here.
- W255 (the umbrella) blocks on W265.
