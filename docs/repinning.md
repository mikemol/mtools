<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# Repinning the fleet to an mtools commit

A repo that adopts an mtools distribution names it at a commit. When mtools lands a fix a repo needs
(an example: the queue writer keeping file ownership, `6868dd2`), each repo has to move its pins.
`mikemol-repin` does the survey and the move for every repo at once; it is the `hooks` distribution's
maintainer tool, installed beside `mikemol-gen-warrants`.

## Survey first

```
mikemol-repin --sha <40-hex commit>
```

One line per pin, tab separated: `repo dist form pinned STATUS`.

| STATUS | meaning |
|---|---|
| `SAME` | the pin already names that commit (an abbreviated pin is compared by prefix) |
| `DIFFERS` | the pin names another commit; `--write` would move it |
| `VENDORED` | a wheel under `vendor/wheels/`, named for the commit it was built from; never rewritten |

Without `--sha` the status column is `-`. `--root DIR` changes the directory scanned (default
`~/github`), `--dist D` (repeatable) narrows to named distributions. mtools itself, hidden
directories and `.claude` worktrees are not scanned.

## Then write

```
mikemol-repin --sha <40-hex commit> --write
```

* The target must be a full 40-character lowercase hex commit; a short sha or a branch is refused,
  because it would write a pin that does not pin.
* All the chosen pins move to the one commit together. Two specs of one repo at different commits
  can resolve to two copies of the shared `mikemol` namespace, which is why the tool does not move
  one dist alone unless you name it.
* A repo whose `pyproject.toml` or `uv.lock` has uncommitted changes is `skipped-dirty` and not
  touched, so the rewrite never lands inside someone's half-made edit.
* Each repo that changed gets `uv sync` (skip with `--no-sync`), and the run ends with one
  `RESULT repo written|synced|sync-failed|skipped-dirty|current` line per repo. The exit is 1 when a
  sync failed.
* **The tool never commits.** Each repo's own session reviews the diff and commits it.

## Vendored wheels are yours to rebuild

A `VENDORED` row means the repo carries a built wheel whose file name holds the commit. Renaming it
would claim the bytes came from the new commit when they did not, so the tool reports it and leaves
it. Re-vendor from the new commit and edit the path.
