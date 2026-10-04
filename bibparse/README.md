<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-bibparse

paperkit's `bibparse` moved alone into mtools (mtools:W560, the decided cut (b) of W558), plus the
three things paperkit's `tools/effective.py` needs of `bib.parse_project` and nothing more. A
library: standard library only, no console script.

| module | does |
|---|---|
| `mikemol.bibparse.bibparse` | `parse(text, path)` returns `Entry` records (type, key, ordered fields, start line); a malformed bib raises `BibSyntaxError` naming line and column. A column-0 `}` inside a field truncates nothing. Ported faithfully from `paperkit/bibparse.py` |
| `mikemol.bibparse.resolve` | `bib_paths(project_dir)` returns the bib files `paper.toml`'s `[paper] warrants` names (default `warrants.bib`); a Bazel label token `//pkg:file` is `project/pkg/file` |
| `mikemol.bibparse.edges` | `claim_edges(project_dir)` returns `{key: {"rests_on": [str], "check": str}}`; `collect` and `edges_of` do it for an explicit path list; two entries with one key raise `DuplicateKeyError` |

## What no longer runs

`effective.py` called `bib.parse_project`, which also ran paperkit's `paper.toml` guards. Through
this package they do NOT run: the misplaced `[paper]` key refusals (`_misplaced_paper_key`,
`_misplaced_consumer_fields`), the unknown-field stderr warnings, and the `entails` refusal. They
still fire in paperkit's own gate. The resolver also differs on purpose in three refusals, all in
the safe direction: a bib named by `warrants` that is not a file raises (paperkit returned `{}`), a
key repeated inside ONE bib raises (paperkit refused across files only), and a label token with no
`//` raises (paperkit hit an `IndexError`).

## Manual equivalence check

mtools CI cannot import paperkit (that would be a cycle), so the proof that this reader agrees with
paperkit's real parser is run by a human, in paperkit's tree. Save this as `/tmp/equiv.py`:

```python
import sys
from pathlib import Path

import bib
from mikemol.bibparse.edges import claim_edges

for name in sys.argv[1:]:
    project = Path(name)
    want = {
        key: {"rests_on": fields["rests-on"], "check": fields.get("check", "")}
        for key, fields in bib.parse_project(project).items()
    }
    got = claim_edges(project)
    assert got == want, f"{project}: edges differ"
    print(project, len(got), "claims equal")
```

then, from the root of the paperkit checkout (the paths are its projects, add `paper` and
`library` for the 12-bib and `concept:` cases):

```
cd /home/mikemol/github/paperkit
PYTHONPATH=paperkit:/home/mikemol/github/mtools/bibparse/src python3 /tmp/equiv.py arch talk report boundaries setup render
```

Every line must print `N claims equal`; an `AssertionError` or a `BibSyntaxError` is a divergence to
file against mtools:W560.
