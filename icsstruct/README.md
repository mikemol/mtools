<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-icsstruct

This package reads iCalendar (`.ics`, RFC 5545) files without losing anything. life asked for it
(life:W13), for life and nemik. No iCalendar library is lossless: a strict parser raises on a
malformed line and a lenient one skips it, so neither output can be counted against its input. The
design is in `.claude/design/W247-icsstruct.md`.

The package is being built in two layers: a **lexical** layer written here, then an **expansion**
layer that hands well-formed VEVENTs to `icalendar` + `recurring-ical-events`. Only **stage 1,
`lexical`**, exists so far.

## `mikemol.icsstruct.lexical`

```python
from mikemol.icsstruct.lexical import lex

for rec in lex(path.read_text(encoding="utf-8")):
    ...  # ContentLine | Malformed
```

| record | when |
|---|---|
| `ContentLine` | one unfolded content line: `name`, `params`, `value`, and `path`, the enclosing components with their ordinals |
| `Malformed` | no colon, a bad parameter, an empty line, a continuation with nothing to fold onto, a stray `END`, or the `BEGIN` of a component that is never closed. It carries the `reason`. |

Every record has `first` and `last`, its span of physical lines, and `raw`, those lines verbatim.
The spans partition the input, so a count over the output is a count over the input. CRLF and bare
LF are both accepted.

The test fixtures in `tests/fixtures/` are life's synthetic set (life 4a652ec). Keep the tests
synthetic: nothing from a real calendar enters this tree.
