<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-importdag

Three of paperkit's `tools/` modules moved together into mtools (mtools:W563, a cut of W532):
`dagderive`, `dagnames` and `closure_census`. Standard library only, `dependencies = []`, and no
dependency on any other mtools distribution.

| module | does |
|---|---|
| `mikemol.importdag.dagderive` | `imports(text, names, pkg)` reads an engine-internal import from the syntax tree in all its spellings; `stem_index(paths)` maps stem to path and refuses a duplicate stem; `edges(eng, paths)` records each edge as importer path and imported path; `cone(start, edges_by_mod)` is the transitive closure. A library: no script |
| `mikemol.importdag.dagnames` | `module_names(eng, skip, pkg)` names every module of the `COMPONENTS` partition importably; `unresolvable(names, eng, root)` proves each name imports, one child interpreter per name; console script `mikemol-dagnames` |
| `mikemol.importdag.closure_census` | flags a witness that shells out to a sibling script whose engine imports its declared closure does not hold; console script `mikemol-closure-census` |

## What is NOT here, and why

`imports`, `closure` and `dagbzl` stay in paperkit's `tools/`. Each depends on a module in
paperkit's engine or on a sibling mtools distribution (`atomicwrite`, via `paperkit.durable`), and
a distribution depending on another is a mechanism the operator has not ruled on (mtools:W562).
`closure_census` asks the closure tool what roots a claim gets, so it takes the closure script as
an option (`--closure`, default `tools/closure.py` under the root) until `closure` is ported and
that call can name a module.

## What changed from paperkit

Every change is a consequence of leaving `tools/`, where the modules found the tree by their own
file location.

- No module computes `ROOT` or `ENGINE` from `__file__`. `module_names` and `unresolvable` take the
  engine directory; the census takes a `Tree` (root, engine, closure script). The command lines
  take `--engine` (default `paperkit` under the working directory), and the census takes `--root`
  (default the working directory) and `--closure`.
- `dagnames.unresolvable`'s child interpreter no longer runs `sys.path.insert` and then
  `import tools.dagnames`. DECISION: the child imports `mikemol.importdag.dagnames` and the paths
  reach it through the `PYTHONPATH` environment variable, set by `child_env`: the engine
  directory, its parent, and the directory this package was imported from, then whatever
  `PYTHONPATH` the parent had. This keeps every `sys.path` edit out of code, binds the
  consumer's first module before the name under test as before, and works from a source tree or
  an installed package. The alternative, `-m`, cannot bind a module first and then import another
  name in one process, so it was not chosen. `tests/test_dagnames.py` runs real children under
  `tmp_path` against it.
- `unresolvable(names, eng, root=None)`: the child runs in `root`, default the engine's parent
  (paperkit's was the repository root, which is the engine's parent there).
- `main(argv=None)` on both scripts, each with a `__main__` guard; `dagderive` has none (library).
  Output goes to `sys.stdout` at call time, not a module constant.
- Files are read with `encoding="utf-8"`. `closure_census` prints `GAP` where it printed a flag
  glyph, and the same words elsewhere with no glyphs. The census is otherwise the same algorithm.

## What the gate's held-out `witness_reach` needs of this package (mtools:W544)

`witness_reach` loads every witness as the bib spells it, from a fresh interpreter with a bare
`python3`, and its child code once reached `tools.dagnames` by path. From this package it needs:

1. `mikemol.importdag.dagnames.unresolvable` (the child-interpreter name check) importable by
   module path from a fresh interpreter, with nothing on `sys.path` but what the environment
   gives it. `test_module_path_import_from_a_fresh_interpreter` witnesses that.
2. `mikemol.importdag.dagderive.cone` (the closure function), with `edges` and `stem_index`
   beneath it, for any witness that derives a cone.

Paperkit call sites that name these modules and must be repointed by the paperkit side: the two
test importers of `dagderive` and one of `dagnames` in `paperkit/tests/boundaries_config.py` and
`boundaries_components.py`, and `tests/boundaries_closure_census.py` for `closure_census`.
