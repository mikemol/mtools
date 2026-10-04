<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-mutation

The pure perturbation leaf of paperkit's engine (`paperkit/mutate.py`), ported here (mtools:W556,
umbrella mtools:W531). Given a `.py` source and a mutation spec it emits the perturbed source.
Standard library only. Behaviour is paperkit's; the cross-package seam is public.

| spec | perturbation |
|---|---|
| `""` | the identity: the source, byte for byte |
| `<qualname>` or `def:<qualname>` | a def's body becomes an uncatchable `raise BaseException('PAPERKIT_MUT')` |
| `branch:<qualname>#<n>` | one branch arm's body becomes the same raise |
| `flip:<qualname>#<n>` | one `if`/`while` condition `C` becomes `not (C)` |
| `data-:<name>#<n>` | one key or element of a module-level dict, list, set or tuple literal is dropped |
| `dflip:<name>#<n>` | one value of such a literal becomes a counterfactual |
| `import-:<name>` | the top-level `import <name>` or `from <name> import ...` is dropped |
| `import+:<name>` | a dead `if False:` guarded `import <name>` is injected |

A spec naming no such element raises `KeyError`; a miss is never a silent no-op.

## Public names

`emit_mutant`, the site generators `def_sites`, `branch_sites`, `flip_sites` and `data_sites`,
and the appliers `mutate_lines`, `flip_condition` and `drop_data_multi`. In paperkit these were
underscore names (`_branch_sites`, `_data_sites`, `_flip_sites` imported by `tools/sites.py`;
`_def_sites`, `_mutate_lines`, `_drop_data_multi`, `_flip_condition` imported by `grader.py` and
`cache.py`), so repointing them is a rename at each import.

## Command line

`mikemol-mutate <module.py> <spec>` (or `python -m mikemol.mutation.mutate`) prints the perturbed
module to stdout, as paperkit's `mutate.py <module.py> <spec>` did.
