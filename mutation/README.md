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

## Declared defect classes

The def-site grid asks whether a suite reaches a def. A distribution can also name the defects it fears, and the
`:mutants` target plants each one and runs the distribution's own suite against it. The declaration is a
`mutants.regex` file beside the distribution's `pyproject.toml`, one line per defect:

```text
<module>|<name>|<pattern>|<replacement>|<scope>
```

The module is a path relative to the distribution (`src/mikemol/x/walk.py`), the other four fields are
`parse_regex_spec`'s own (`%7C` is a literal `|`, the scope is empty, `def=<qualname>` or `lines=<a>-<b>`), and a blank
line or a line starting with `#` is ignored. `read_declarations` reads it, refusing a malformed line by its number, and
`plant` applies one declared spec to a source.

- **None by default.** A distribution with no file is asked nothing, and the report says `none declared`.
- **Only `killed` passes.** `survived` is a suite blind to a defect the distribution named; `unapplied` is a stale
  declaration, a pattern that matches nothing in its scope; `errored` is a declaration that was never run.
- **A distribution that declares any adds the file to its `:mutants` data**, and every `:mutants` target stages
  `//mutation:mutation`, which the runner imports from source (`MUTATE_MUTATION_SRC`).
- **An equivalent mutant is a bad declaration, not a blind suite.** `followlinks=False` to `True` in pathwalk's walk
  survived because the walk already drops a linked directory itself; the declaration was replaced with the check whose
  removal does change behaviour.

## Command line

`mikemol-mutate <module.py> <spec>` (or `python -m mikemol.mutation.mutate`) prints the perturbed
module to stdout, as paperkit's `mutate.py <module.py> <spec>` did.
