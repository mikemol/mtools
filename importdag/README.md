<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-importdag

Six of paperkit's `tools/` modules moved into mtools (a cut of W532): `dagderive`, `dagnames` and
`closure_census` first (mtools:W563), then `imports`, `closure` and `dagbzl` (mtools:W547). The one
dependency is the sibling distribution `mikemol-atomicwrite`, for the atomic write of the generated
DAG file (mechanism A+B, mtools:W562).

| module | does |
|---|---|
| `mikemol.importdag.dagderive` | `imports(text, names, pkg)` reads an engine-internal import from the syntax tree in all its spellings; `stem_index(paths)` maps stem to path and refuses a duplicate stem; `edges(eng, paths)` records each edge as importer path and imported path; `cone(start, edges_by_mod)` is the transitive closure. A library: no script |
| `mikemol.importdag.dagnames` | `module_names(eng, skip, pkg)` names every module of the `COMPONENTS` partition importably; `unresolvable(names, eng, root)` proves each name imports, one child interpreter per name; console script `mikemol-dagnames` |
| `mikemol.importdag.closure_census` | flags a witness that shells out to a sibling script whose engine imports its declared closure does not hold; console script `mikemol-closure-census` |
| `mikemol.importdag.closure` | a claim witness's engine closure roots plus its file and content toggle rows; console script `mikemol-closure` |
| `mikemol.importdag.dagbzl` | owns the path-valued `dag.bzl`: `render`, and `--write` / `--check` through the sibling's `write_atomic`; console script `mikemol-dagbzl` |
| `mikemol.importdag.imports` | the LEGACY stem-valued writer of the same file, plus the edge listing; console script `mikemol-imports` |
| `mikemol.importdag.resolve` | `derive(root, paths)` resolves a file set's imports against each other for any layout (`src/` roots, several packages, flat scripts): each file is indexed by every dotted suffix of its path; an absolute name resolves at its longest dotted prefix, preferring the sibling and otherwise reporting the ambiguous prefix with its candidates as `Unsettled` in `Resolution.ambiguous` (never guessed; a `declared` name-to-path map settles it, honoured only when the path is a candidate); a relative import is looked up exactly from its level (a package before a module). A library: no script |

## The two import readers, and the two writers

`dagderive.imports` reads every spelling of an import (flat and package-qualified);
`dagderive.flat_imports` and `dagderive.node_imports` read only the flat spelling. The closure tool is defined over the
flat reading, and the package-qualified one would widen every cone it computes, so both exist and
are named for what they read. `imports --write` and `dagbzl --write` write different formats to
the same `dag.bzl` (a stem per value against a module path per value): running one after the other
flips the file. `dagbzl` is the current writer; `imports --write` is kept as ported and should have
one owner of the file only.

## What changed from paperkit in the second move (mtools:W547)

- The engine is `--engine DIR` (default `paperkit` under the working directory) for `imports`,
  `dagbzl` and the helpers, not `Path(__file__).parents[1] / "paperkit"`.
- The generated `dag.bzl` header names `mikemol.importdag.dagbzl` and `mikemol.importdag.dagderive`
  (it named `tools/dagbzl.py`), so paperkit regenerates it once. The body is byte identical.
- `closure` keeps argparse, with a typed namespace subclass, so `--help` and option abbreviations
  survive. `closure_census` runs `python -m mikemol.importdag.closure` by default; `--closure
  SCRIPT` still names a script.
- `dagbzl.literal` is gone (it duplicated `dagnames.literal`), and `imports.engine_srcs` and
  `dagbzl.engine_srcs` are one function, `dagnames.engine_srcs`. `imports.imports` became
  `dagderive.flat_imports`, and `closure`'s private `_imports` became `dagderive.node_imports`.
- `closure`'s private helpers are public (a private name cannot be imported by its witnesses).
- `imports.render(eng, rows)` lost its unused `eng` parameter.

## What changed from paperkit in the first move

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
