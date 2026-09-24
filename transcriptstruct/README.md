<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-transcriptstruct

This package reads Claude Code session transcripts (`~/.claude/projects/<slug>/*.jsonl`) without
losing anything. It replaces substrate's `scratch/transcriptstruct.py`, which could not see
attachment records: it decoded 0 blocks from 15,113 of them, so a directive typed while the agent
was mid-turn never showed up in its output.

The package is being ported in stages: records, walk, blocks, provenance, query, cli. Only
**stage 1, `records`**, exists so far.

## `mikemol.transcriptstruct.records`

```python
from mikemol.transcriptstruct.records import read_path, parse_line

for rec in read_path(path):
    ...  # UserRecord | AssistantRecord | AttachmentRecord | UnknownRecord | MalformedLine
```

Each input line produces exactly one record:

| record | when |
|---|---|
| `UserRecord` | `type: "user"`. `content` is a str or a tuple of blocks. `is_compact_summary` is set. |
| `AssistantRecord` | `type: "assistant"`. |
| `AttachmentRecord` | `type: "attachment"`, where `message` is null. `prompt` is a str, a tuple of blocks, or None. `origin_kind` is read from `attachment.origin.kind`. |
| `UnknownRecord` | any other `type`, a missing `type`, a non-object line, or a known type with the wrong field shapes. It includes the reason. |
| `MalformedLine` | the line is not JSON. It includes its 1-based line number and the parser error. |

Nothing is skipped, including blank lines. A count over the output is therefore a count over the
input. Each decoded record keeps `raw`, the whole envelope, so the next stage can still find any
field that no decoder claims.
