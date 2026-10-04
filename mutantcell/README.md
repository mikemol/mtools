<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-mutantcell

The mutant-cell tools of paperkit's `tools/`, ported here (mtools:W545, paperkit:W142). Behaviour is
paperkit's; the entry points are a console script and `python -m` modules instead of paths.

| module | entry | does |
|---|---|---|
| `mikemol.mutantcell.eval` | `mikemol-eval`, `-m mikemol.mutantcell.eval` | runs ONE def-sweep cell: stages the counterfactual, runs the check under CPU, address-space and process-tree bounds, and records whether it flipped |
| `mikemol.mutantcell.cellargs` | library | one cell's argv as a typed record |
| `mikemol.mutantcell.cellcgroup` | library | a cell's view of its own cgroup: `memory.peak` (written in paperkit's `.peak` format) and OOM counts |
| `mikemol.mutantcell.cellstage` | library | places the engine's bytecode and delivers one counterfactual (module swap, file inject or drop, content toggle) |
| `mikemol.mutantcell.sens` | `-m` only | folds per-site cell records into a claim's sensitivity set; fails loud on a flipped baseline or a leaked non-monotone cell |
| `mikemol.mutantcell.decisions` | `-m` only | decision-coverage aggregator: the reached-but-unasserted decisions of a claim, or a project summary |
| `mikemol.mutantcell.def_sites` | `-m` only | enumerates a source's def-sites (the mutation surface), or with `--lines` where each sits |

`cellargs`, `cellcgroup` and `cellstage` do nothing at import time: they define names and nothing
else, so they are libraries and carry no script role (paperkit's shebangs on them were stray).

## Not here: `sites`

paperkit's `tools/sites.py` imports the engine module `mutate`, which moves in its own package
first. When it lands, `sites` needs `mikemol.mutantcell.def_sites.def_sites(text)` (the def-drop
specs, one qualname per def-site, unchanged in order) and nothing else from this package.

## Seams the tests drive

`cellcgroup` functions take a `Cgroup(proc, root)` (default: this process's real `/proc/self/cgroup`
and `/sys/fs/cgroup`), and `eval.main` takes that `Cgroup` plus a `caps` callable (default: the
real, irreversible CPU and address-space caps), so a test points them at a planted cgroup directory
and never caps the test runner itself.
