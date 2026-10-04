<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-treeio

paperkit's `tools/vfs.py` and `tools/edit_snapshot.py` ported together into mtools (mtools:W550,
operator ruling 2026-10-04: port both; bibstruct stays in paperkit and pins this distribution). The
two were 3,109 lines in two files; here they are split one module per responsibility.

One runtime dependency, `pygit2`, for reading a path at a git revision. The snapshot half runs the
`git` binary, so `git` must be on `PATH`.

## The vfs half: one read/write seam over a tree and its history

| module | does |
|---|---|
| `mikemol.treeio.presence` | `Presence`: PRESENT, ABSENT or BROKEN. An unknown name is refused by `of`, never defaulted |
| `mikemol.treeio.result` | `Result`: presence, raw bytes, cause. Truthy only when PRESENT. `require` raises `FileNotFoundError` for ABSENT and the recorded cause for BROKEN |
| `mikemol.treeio.sources` | `WorkingTree` (writable) and `Rev` (read-only; resolves its revision eagerly, so a mistyped sha is BROKEN and never ABSENT) |
| `mikemol.treeio.read` | `read` (raw bytes), `read_text` (UTF-8, `None` if ABSENT), `relpath` |
| `mikemol.treeio.write` | `write`: atomic, UTF-8, working tree only. `write.DRY_RUN` makes the seam refuse |
| `mikemol.treeio.listing` | `listdir` refuses a glob that means different things at a working tree and at a revision (`AmbiguousPatternError`); `suffixed` |
| `mikemol.treeio.census` | `census` splits PRESENT into empty and nonempty; `compare` re-derives the matcher asymmetry |
| `mikemol.treeio.vfs_cli` | `mikemol-vfs`: `--read`, `--at`, `--list`, `--states`, `--census`, `--suffix`, `--compare`. Exit 0 PRESENT, 1 ABSENT, 2 BROKEN, 3 ambiguous pattern |
| `mikemol.treeio.vfs` | the old one-module surface, re-exported: `from mikemol.treeio import vfs` |

## The edit-snapshot half: recoverable before any rewrite

| module | does |
|---|---|
| `mikemol.treeio.errors` | `MutationContractError` (a `BaseException`, on purpose) and `AmbientVocabError` |
| `mikemol.treeio.ambient` | `Ambient`, a write-once per-invocation context variable; `Override`, the registered scoped divergence |
| `mikemol.treeio.context` | `INTENT`, `TENANT`, `SNAPSHOT_STATE`, `naming_tenant`, `resolve_intent`, `sanctioned_setters` |
| `mikemol.treeio.layout` | where the journal and the untracked-copy store live under a root |
| `mikemol.treeio.proc` | the one place a child process is started |
| `mikemol.treeio.gitrun` | `git(root, ...)` and `is_tracked` |
| `mikemol.treeio.snapshot` | `snapshot`: a `git stash create` commit pinned by a ref, untracked files copied aside, a journal row |
| `mikemol.treeio.restore` | `contents` and `restore`; a restore only reports until `apply` is given |
| `mikemol.treeio.contract` | `require_explicit_mutation`, `require_at_entry`, `guard`, `snapshot_once`, `cli_main` |
| `mikemol.treeio.snapshot_cli` | `mikemol-edit-snapshot`: `--list`, `--holding <fragment>`, `--from-snapshot=<sha> [paths] [--apply]` |
| `mikemol.treeio.edit_snapshot` | the old one-module surface, re-exported |

## Behaviour that differs from paperkit's modules

- **The root is a parameter.** paperkit's `ROOT` was the directory above `tools/`. Here `Rev`,
  `WorkingTree`, `snapshot`, `guard`, `snapshot_once`, `contents` and `restore` take an optional
  `root` and default to the current directory. `require_at_entry` always uses the current directory.
- **pygit2 is a hard dependency**, so the "pygit2 is required to read from a revision" arm is gone.
- **`scratch/ratchet` is gone.** The unstated-mutation census that `require_explicit_mutation` tried
  to log imported a sibling `scripts/ratchet`, which does not exist in paperkit, inside a blanket
  `except Exception: pass`. The branch never ran, so removing it changes nothing observable.
- **`--selftest` is gone** from both command lines; the suites are these tests.
- **Renames:** `AmbiguousPattern` is `AmbiguousPatternError` (old name kept as an alias);
  `AmbientConflict` is `AmbientConflictError` (alias kept); `vfs._census`, `_compare`, `_suffixed`
  are public `census`, `compare`, `suffixed`; `vfs._declare` is `write.declare`.
- **Typed signatures:** `Override.run` and `cli_main` take a callable of no arguments (paperkit's
  forwarded `*args, **kwargs`); `resolve_intent` lost its unused `argv`; `restore`'s `apply`,
  `listdir`'s `strict`, `write`'s `mkdirs` and `require_at_entry`'s `store` are keyword-only.
- **`read_text` reads once** where paperkit's read the path up to three times.
- **The journal creates `scratch/`** if it is missing; paperkit's silently wrote no journal in a
  tree without that directory.
- **`INTENT_ORIGIN` and the first `INTENT = ContextVar(...)` are gone**: the second `INTENT`
  assignment shadowed the first, and nothing read the origin variable.
- **`Ambient._reset` is gone**: nothing called it.
- Messages that named `edit_snapshot.<NAME>` now name `mikemol.treeio.context.<NAME>` and
  `mikemol.treeio.ambient.SANCTIONED_OVERRIDES`; the `--holding` restore hint names
  `mikemol-edit-snapshot`.
- `vfs.write` keeps its own atomic write (fsync, default mode) and does not use
  `mikemol.atomicwrite`: no distribution here depends on another, and `write_atomic` also preserves
  the target's permissions, which would be a change on the move.

## Manual equivalence check

mtools CI cannot import paperkit (that would be a cycle), so the proof that a repointed bibstruct
behaves as before is run by a human in paperkit's tree: repoint `tools/bibstruct.py`'s
`from paperkit.tools import vfs` and its three `import edit_snapshot as _es` lines to
`from mikemol.treeio import vfs` and `from mikemol.treeio import edit_snapshot as _es`, then run
paperkit's bibstruct boundaries witnesses.
