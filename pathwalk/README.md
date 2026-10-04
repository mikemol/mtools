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
