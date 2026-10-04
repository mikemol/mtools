<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-gatecheck

The pre-commit and gate helpers of paperkit's `tools/`, ported here (mtools:W544, paperkit:W142).
Behaviour is paperkit's; the entry points are console scripts and `python -m` modules instead of
paths, and a hard-coded repo root becomes the current directory (or `--root`).

| module | script | does |
|---|---|---|
| `mikemol.gatecheck.hook_index` | `mikemol-hook-index` | refuses when the worktree differs from the index outside the allowlist |
| `mikemol.gatecheck.indexdiverge` | none (library) | the pure predicate `hook_index` uses: which paths diverge |
| `mikemol.gatecheck.hook_grid` | `mikemol-hook-grid` | the hand-transcribed `//:hook` member list against `MODULE.bazel`'s declarations |
| `mikemol.gatecheck.rungate` | none (`-m` only) | runs a gate target under the repo's sweep budget |
| `mikemol.gatecheck.absence_audit` | `mikemol-absence-audit` | flags an absence claim asserted without running the owning tool |
| `mikemol.gatecheck.lint_bzl` | `mikemol-lint-bzl` | refuses program logic and JSON built in a `.bzl` shell string |

`witness_reach` is NOT here: its child-interpreter code string imports `tools.dagnames`, which moves
in a later package.
