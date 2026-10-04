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
| `mikemol.mutantcell.sites` | `mikemol-sites`, `-m mikemol.mutantcell.sites` | prints `module<TAB>spec` for every perturbation site of the named engine modules: def-drops, branch and condition sites, data key-drops and value-perturbs, and absent-import injects |
| `mikemol.mutantcell.def_sites` | `-m` only | enumerates a source's def-sites (the mutation surface), or with `--lines` where each sits |

`cellargs`, `cellcgroup` and `cellstage` do nothing at import time: they define names and nothing
else, so they are libraries and carry no script role (paperkit's shebangs on them were stray).

## `sites` and the sibling edges

paperkit's `tools/sites.py` imported the engine modules `mutate` and `imports`. Both are
distributions of this repository now, so `sites` reads them as siblings (mtools:W562, option A+B):
`mikemol.mutation.mutate` for `branch_sites`, `data_sites` and `flip_sites`, and
`mikemol.importdag.dagderive.flat_imports` for the flat-import reader. `mikemol-importdag` brings
`mikemol-atomicwrite` with it. The edges are declared in `pyproject.toml` (for uv) and in
`BUILD.bazel` (for Bazel); `tests/test_sibling_edge.py` checks they resolve. The paperkit layout
assumption (`Path(__file__).parents[1]`) is gone: the files named on the command line are the
engine, and the module never launches the mutator, so it chooses no interpreter path.

## Seams the tests drive

`cellcgroup` functions take a `Cgroup(proc, root)` (default: this process's real `/proc/self/cgroup`
and `/sys/fs/cgroup`), and `eval.main` takes that `Cgroup` plus a `caps` callable (default: the
real, irreversible CPU and address-space caps), so a test points them at a planted cgroup directory
and never caps the test runner itself.
