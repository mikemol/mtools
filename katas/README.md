<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-katas

The host orchestration katas, graduated into a tracked distribution (mtools:W796, W872). The host's
`~/github/.claude/katas/katas.py` sits under `.claude/`, where standing rule 16 refuses executable
code, so it cannot be edited in place; what it does that no mtools tool already does lives here
instead, and it calls those tools (`mikemol-commit`, `mikemol-pycheck --census`, `mikemol-paths-forward
--gate-red`) for the rest. A library for now: no console script, standard library only.

| module | does |
|---|---|
| `mikemol.katas.workstreams` | `repos(root)` names the workstream directories that carry a queue |
| `mikemol.katas.commits` | `commit_argv(...)` builds the `mikemol-commit` argv; `commit_state(log)` reads a detached commit's log |

The detached commit itself (`start_commit`, `wait`) arrives with the process seam
(`mikemol-procrun`) in the next slice.
