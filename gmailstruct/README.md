<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-gmailstruct

This package reads Gmail API message JSON without losing anything. life asked for it (life:W27,
mtools:W287). A message the reader cannot narrow becomes an `Unreadable` record with a reason, so a
count over the output is a count over the input.

The package is being built in stages: **`records.message`** (one `users.messages.get` response,
`format=metadata`) exists so far. Listing pages (W334) and `format=full` MIME parts (W335) come
next. Auth (W288) and the CLI (W289) are separate, and neither reaches this layer.

## `mikemol.gmailstruct.records`

```python
from mikemol.gmailstruct.records import message

rec = message(json.loads(body))  # Message | Unreadable
```

| record | when |
|---|---|
| `Message` | `id`, `thread_id`, `labels`, `snippet`, `internal_date_ms`, and the `headers` as ordered (name, value) pairs, repeats kept |
| `Unreadable` | the response is not an object, or a field is missing or the wrong type. It carries the `id` when one could be read, and the `reason`. |

The tests are synthetic (`@example.invalid`). Keep them so: no real mail enters this tree.
