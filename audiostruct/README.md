<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-audiostruct

This package reads the output of WhisperX transcription and diarization without filling in
anything it was not given. life asked for it (life:W12), to replace a one-off script that read a
segment with no timing as `[00:00]` and one with no speaker as `UNKNOWN`. The design is in
`.claude/design/W255-audiostruct.md`.

Only **stage 1, `records`**, exists so far. The three-stage GPU runner, its memory admission
through `mikemol-membudget hold`, and the `mikemol-audio` command come later.

## `mikemol.audiostruct.records`

```python
from mikemol.audiostruct.records import normalize

for rec in normalize("call label", result["segments"]):
    ...  # Segment | Unplaced
```

| record | when |
|---|---|
| `Segment` | finite `start` <= `end`, string `text`. `speaker` is None when diarization assigned none. Each `Word` keeps its own optional timing and score. |
| `Unplaced` | a missing or non-numeric time, `end` before `start`, missing text, a non-string speaker, or a malformed word. It carries the `reason` and the segment as sorted JSON in `raw`. |

There is exactly one record per input segment, in order, and `index` is its position, so a count
over the output is a count over the input.

Keep the tests synthetic: no audio and no real transcript enters this tree.
