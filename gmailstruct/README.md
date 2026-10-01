<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-gmailstruct

This package reads Gmail API message JSON without losing anything. life asked for it (life:W27,
mtools:W287). A message the reader cannot narrow becomes an `Unreadable` record with a reason, so a
count over the output is a count over the input.

The package is being built in stages: **`records.message`** (one `users.messages.get` response,
`format=metadata`), **`records.pages`** (a run of `users.messages.list` responses) and
**`records.parts`** (the MIME tree of a `format=full` response) exist. Auth (W288) and the CLI (W289) are separate, and neither reaches this layer.

## `mikemol.gmailstruct.records`

```python
from mikemol.gmailstruct.records import message

rec = message(json.loads(body))  # Message | Unreadable
```

| record | when |
|---|---|
| `Message` | `id`, `thread_id`, `labels`, `snippet`, `internal_date_ms`, and the `headers` as ordered (name, value) pairs, repeats kept |
| `Unreadable` | the response is not an object, or a field is missing or the wrong type. It carries the `id` when one could be read, and the `reason`. |

`records.pages(values)` takes the list responses in fetch order and returns one `Listed` (`id`,
`thread_id`, `page`, `ordinal`) per entry, with an `Unreadable` for each page or entry out of
shape. `resultSizeEstimate` is never read as the count. If the pages do not chain (a page before
the last without `nextPageToken`, or a last page that still has one), an `Unreadable` says the
listing is truncated, so a partial count cannot read as complete.

`records.parts(value)` walks the MIME tree depth first and returns one `Part` (`path`, `part_id`,
`mime_type`, `filename`, `data`, `attachment_id`) per node, containers included. `body.data` is
decoded from base64url strictly: text a lenient decoder would quietly repair is `Unreadable`. A
node out of shape is an `Unreadable` naming its path, and its children are still walked.

The tests are synthetic (`@example.invalid`). Keep them so: no real mail enters this tree.
