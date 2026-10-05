<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-pathwalk

The directory-operand walk, extracted from mikemol-pycodemod (mtools:W573) so a caller that
cannot afford libcst can reuse it (mdstruct, mtools:W561). A library: no console script, standard
library only.

| module | does |
|---|---|
| `mikemol.pathwalk.walk` | `expand(operands, include_worktrees=...)` turns directory operands into their `*.py` files |

Behaviour: a registered git worktree other than the root's own tree is skipped and counted; a
directory holding `pyvenv.cfg` is pruned and counted; a symlink is refused as data and counted; git
absent or failing raises `WorktreeRefusedError` rather than reading as no worktrees.

## Counts

`expand` returns an `Expansion` whose counts a driver prints for every directory operand, zero
included. `worktrees` is the registered worktrees skipped (`skipped N registered worktrees`),
`virtualenvs` is the directories pruned for holding `pyvenv.cfg` (`skipped N virtualenvs`), `excluded`
is the directories pruned by name (`skipped N excluded directories`), and `links` is the symlinks
refused (`refused N symlinks (not followed)`). `directories` is how many operands were directories,
which is what decides whether a driver prints the counts at all.

## Exclude

`expand(operands, include_worktrees=..., exclude=[...])` prunes the directories the caller names.
Each entry is a glob matched with `fnmatch.fnmatchcase` against one directory's own name, so `build`
prunes `build/` at any depth but not `builder/`, and `bazel-*` prunes `bazel-bin`. There is no
default list: `exclude` of `None` or empty prunes nothing, so a repo's `build/` is never silently
dropped. An entry that is empty or holds a `/` raises `ValueError` naming the entry. A virtualenv or
a registered worktree is counted as itself first and never again as excluded.
