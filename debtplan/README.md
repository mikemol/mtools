<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-debtplan

The order in which a per-file debt ledger can be paid down. luthen-observability's `checks/mypy_plan`
drained into mtools (mtools:W790) and atomized: the import resolver went into `mikemol-importdag`
(`mikemol.importdag.resolve`), and this distribution is the planning core over it. This is the first
unit; the queue writer and the command line, which bring in `mikemol-pathsforward`, are the second.
The dependency is the sibling `mikemol-importdag` (mechanism A+B, mtools:W562), and through it
`mikemol-atomicwrite`.

A per-file edit gate refuses an edit to a file whose import closure still carries findings, so the
order of a pay-down is a fact about the import graph, not a choice. A debt file waits on every other
debt file in its closure, and the files that nothing stands in front of come first.

| module | does |
|---|---|
| `mikemol.debtplan.rows` | `Row`: a debt file's count, the debt files it waits on, and the ones that wait on it; `ready` when it waits on nothing. `order_key` sorts ready files first |
| `mikemol.debtplan.cycle` | `find_cycle(waits)` returns one cycle in a wait graph, or none, so a plan that could block its own cards is refused |
| `mikemol.debtplan.reduce` | `direct_waits(rows)` drops the waits another wait implies (the transitive reduction); the order is unchanged |
| `mikemol.debtplan.plan` | `plan(ledger, root, universe)` derives the waits from the import closure through `importdag.resolve` and `importdag.dagderive.cone`, treats a cycle as one unit, and returns the rows with the import names it could not settle |

## What changed from luthen-observability's `mypy_plan`

- The resolver is `importdag.resolve`, not a copy, and the closure is `dagderive.cone`. The
  `package` and `base` arguments are gone: a dotted name is resolved against the paths themselves,
  so a `checks.*` tree, a `src/` tree and a flat script directory are one case.
- `plan` takes a `universe`, every file of the tree, so the closure runs through CLEAN modules. The
  origin derived edges among the ledger's own files only, which missed a file that reaches a debt file
  through a clean one; the gate sees that closure. With no universe the narrower reading remains
  available and is the default, so it is chosen and not stumbled into.
- What could not be settled is returned (`Plan.ambiguous`), where the origin dropped it silently.
- The cycle check `find_cycle`, the reduction `direct_waits` and the row order are the origin's, each in
  its own module with its own witnesses.
