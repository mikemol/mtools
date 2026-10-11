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

## Vendored wheels: `--revendor`

A `VENDORED` row means the repo carries a built wheel whose file name holds the commit. Renaming it
would claim the bytes came from the new commit when they did not, so the survey reports it and the
`--write` above leaves it. Rebuilding it from the new commit is a different move, and it has its own
mode, for ONE repo:

```
mikemol-repin --revendor --sha <40-hex commit> [--root REPO] [--mtools DIR]          # the plan
mikemol-repin --revendor --sha <40-hex commit> [--root REPO] [--mtools DIR] --write  # do it
```

* `--root` is the repo that vendors (default the current directory); `--mtools` is the mtools
  checkout to build from (default `~/github/mtools`). It moves the `hooks` and `pathsforward`
  wheels together; a repo that vendors neither is refused.
* The plan prints first: `git archive` of both dists at the commit, the local version `+g<short>`
  set in the archived pyproject only, `uv build --wheel`, then the swap.
* Before the repo is touched, the new wheels are installed in a throwaway venv and the new writer's
  `--hash` over a COPY of the queue must equal the live writer's. A writer that reads the queue
  differently stops the move and both hashes are named.
* While `pyproject.toml`, `uv.lock` or `vendor/wheels` have uncommitted changes nothing is built.
* On success the old wheels are removed, the two `[tool.uv.sources]` paths moved, `uv lock` and
  `uv sync --frozen` run, and one `SHA256 dist hex` line per wheel is printed for the hand-written
  `vendor/wheels/README.md`. **It never commits.**

To build any dist's wheel at a commit without moving a repo's pins, use `mikemol-wheel` (below).

## Building wheels at a commit: `mikemol-wheel`

No wheels are published anywhere, so a consumer that wants a dist as a content-addressed input
builds it from the commit:

```
mikemol-wheel DIST... --sha <40-hex commit> --out DIR (--mtools REPO | --src TREE)
```

All the named dists are built at that one commit. `--mtools` archives from a git checkout; `--src`
is a tree that already holds the dist directories (an unpacked `git archive`). One JSON object per
wheel is printed, in the order named: `{"dist","wheel","sha256"}`. The bytes depend only on the
commit: a fixed `SOURCE_DATE_EPOCH` and a stamped tree make two builds, and a checkout against an
unpacked archive, byte-identical. A failure is one line on stderr and exit 1; exit 2 is a usage
refusal.
