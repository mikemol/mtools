<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-debtplan

The order in which a per-file debt ledger can be paid down. luthen-observability's `checks/mypy_plan`
drained into mtools (mtools:W790) and atomized: the import resolver went into `mikemol-importdag`
(`mikemol.importdag.resolve`), and this distribution is the planning core over it, the queue writer
and the command line (`mikemol-debtplan`). The dependencies are the siblings `mikemol-importdag`,
`mikemol-pathsforward` and `mikemol-pathwalk` (mechanism A+B, mtools:W562), and through importdag
`mikemol-atomicwrite`.

A per-file edit gate refuses an edit to a file whose import closure still carries findings, so the
order of a pay-down is a fact about the import graph, not a choice. A debt file waits on every other
debt file in its closure, and the files that nothing stands in front of come first.

| module | does |
|---|---|
| `mikemol.debtplan.rows` | `Row`: a debt file's count, the debt files it waits on, the ones that wait on it, and the ambiguous import names in its closure (`unsettled`); `ready` when it waits on nothing and nothing is unsettled. `order_key` sorts ready files first |
| `mikemol.debtplan.resolutions` | `read_resolutions(path)` reads a JSON object of an ambiguous import name to the file it is declared to mean, and refuses everything else by name |
| `mikemol.debtplan.cycle` | `find_cycle(waits)` returns one cycle in a wait graph, or none, so a plan that could block its own cards is refused |
| `mikemol.debtplan.reduce` | `direct_waits(rows)` drops the waits another wait implies (the transitive reduction); the order is unchanged |
| `mikemol.debtplan.plan` | `plan(ledger, root, universe)` derives the waits from the import closure through `importdag.resolve` and `importdag.dagderive.cone`, treats a cycle as one unit, holds back every file whose closure imports a name it could not settle, and returns the rows with those names and their candidates (`Plan.ambiguous`); `resolutions` declares what a name means |
| `mikemol.debtplan.ledger` | `read_ledger(path)` reads a JSON object of file path to a positive integer count, and refuses everything else by name |
| `mikemol.debtplan.universe` | `python_files(root, exclude)` walks the tree's Python files through `mikemol.pathwalk`, relative and sorted, with the worktrees, virtualenvs, symlinks and named directories it skipped counted |
| `mikemol.debtplan.queue` | `Queue(state)` runs `mikemol-paths-forward` in this process (its `main`, captured) and reads the cards back; the runner is a parameter |
| `mikemol.debtplan.mint` | `mint(plan, queue, style)` syncs the queue to the plan under the tick lock: add what is missing, rewrite every card with the direct waits only, retire what left; each unsettled import name is a card of its own (`<repo> debt ambiguity: <name>`) that the held files wait on; a card being worked keeps its status |
| `mikemol.debtplan.cli` | `mikemol-debtplan plan` and `mint` |

## What changed from luthen-observability's `mypy_plan`

- The resolver is `importdag.resolve`, not a copy, and the closure is `dagderive.cone`. The
  `package` and `base` arguments are gone: a dotted name is resolved against the paths themselves,
  so a `checks.*` tree, a `src/` tree and a flat script directory are one case.
- `plan` takes a `universe`, every file of the tree, so the closure runs through CLEAN modules. The
  origin derived edges among the ledger's own files only, which missed a file that reaches a debt file
  through a clean one; the gate sees that closure. With no universe the narrower reading remains
  available and is the default, so it is chosen and not stumbled into.
- What could not be settled is a BLOCKER, not a guess, and only where it could matter. The origin
  dropped an ambiguous import silently. Here the waits already known stay modelled; a name blocks a
  file only when one of its candidates is or reaches a debt file (otherwise every answer leaves the
  plan as it is), and the mint gives such a name its own card listing the candidates, which the
  held files wait on once along a chain, not at every file behind them. Settling it means planning
  again, which recalculates the order. It clears by a code change, or by a declaration
  (`--resolutions FILE`, name to path) that names one of the candidates; a stale declaration
  naming anything else is ignored and the name stays blocked.
- The writer is `mikemol-paths-forward`'s own `main`, called in this process, not a child process and
  not a reimplementation through `ops`: that command is what also writes the ledger line, the
  mirror and the flock. A writer that refuses a card now stops the sync and is raised with its own
  words, where the origin ignored the refusal; the tick lock is released on every path.
- A card being worked (`working`) keeps its status when the queue is minted again, in everything
  else rewritten. The origin demoted it to `ready`.
- The universe is walked by `mikemol.pathwalk` (worktree copies, virtualenvs and symlinks skipped
  and counted, a directory excluded only by name), not by a walk of this package's own.
- The ledger is validated into `dict[str, int]` at the boundary, and a count of zero is refused.
- The cycle check `find_cycle`, the reduction `direct_waits` and the row order are the origin's, each in
  its own module with its own witnesses.
