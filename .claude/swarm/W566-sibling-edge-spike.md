# W566: option A for a dist-to-dist dependency, measured (feeds the operator ruling mtools:W562)

Spike by a worktree fixer on 2026-10-04, pair importdag (consumer) and atomicwrite (sibling).
Nothing was committed; the main tree and paperkit were untouched. The fixer's recommendation is
advice, and the decision is the operator's. This file is a report of what it measured, with what it did not.

## Short answer

Option A's pyproject and uv.lock edits work for uv. Under Bazel they work only if the pip hubs are NOT
asked to resolve the sibling; the working combination is A's pyproject/uv.lock plus Option B's Bazel
`py_library` dependency edges, with the shipping hub left empty (variant c below).

## uv side (offline, measured)

- `dependencies = ["mikemol-atomicwrite"]` plus `[tool.uv.sources] mikemol-atomicwrite = { path = "../atomicwrite" }`
  resolves with `uv lock --offline`. The lock records a relative `source = { directory = "../atomicwrite" }`
  and no hash, so it is relocatable.
- Use the path source WITHOUT `editable = true`. The editable variant installs a finder hook, and mypy then
  reports `import-not-found` for the sibling (pytest still passes). The copy variant passes pytest, ruff and mypy.
  The namespace package (no src/mikemol/__init__.py) merges fine.
- `uv pip compile` writes the bare line `../atomicwrite` into requirements.txt and requirements-dev.txt: no
  name, no hash, relative to the compile cwd.

## Bazel side

| variant | result | text |
|---|---|---|
| a1: hubs untouched, requirements.txt regenerated | fails, and breaks the pip module extension for EVERY dist | invalid user-provided repo name 'importdag_deps_313_/atomicwrite' |
| a2: requirements.txt left empty, no BUILD edits | loads; the uv_lock dev hub silently drops the sibling; 4 of 14 tests fail | ModuleNotFoundError: No module named 'mikemol.atomicwrite'; mutants ERRORED |
| b: hub resolves the path (`mikemol-atomicwrite @ file:../atomicwrite`) | loads (lazy hub), fails when the target is built | pip wheel runs in the repo cache dir: FileNotFoundError |
| c: pip hubs independent, BUILD `py_library` deps on `//atomicwrite:atomicwrite` | WORKS, 14 of 14 targets including `:mutants`, `:mypy`, `:venv` | two intermediate failures, fixed below |

Not tried for b: an absolute `file:///` URL (not relocatable), `local_path_override`, `pip.override`.

## The minimum edits for variant c, per consuming dist

- pyproject.toml: `dependencies = ["mikemol-atomicwrite"]` and the `[tool.uv.sources]` path entry.
- uv.lock: regenerate with `uv lock --offline`. MODULE.bazel: no change.
- requirements.txt and requirements-dev.txt: do NOT regenerate (it breaks Bazel, a1). A stale file then disagrees
  with pyproject; whether `:reqs` or the gates catch that was not measured (`:reqs` passed).
- BUILD.bazel, five edits: (1) the `py_library` gets `deps = ["//atomicwrite:atomicwrite"]`; (2) the `py_test`
  deps get the same; (3) the `py_test` gets `legacy_create_init = 0` (without it every test fails with
  `No module named 'mikemol.importdag'`: two source roots plus legacy implicit `__init__.py` turn `mikemol` into
  a regular package from the first root, shadowing the namespace); (4) `mypy_runner` deps get the sibling, which is
  how mypy sees it in the sandbox; (5) `venv_from_hub` `.venv` srcs get `glob(...) + ["//atomicwrite:atomicwrite"]`.

## Gates

- `//importdag:mutants`: 25 def-sites attempted, 25 killed; the sibling's defs are not mutated or required to be
  covered. `//importdag:mypy` checks the dist's own files and resolves the sibling's types through py.typed.
- The pycheck hook in a linked worktree uses the main tree's dist venv; the first sibling edge needs `uv sync`
  in the main tree's dist venv before the hook admits an edit (the editable variant fails it too).

## Costs of variant c

Five BUILD edits per sibling edge; `legacy_create_init = 0` on every consuming `py_test`; `uv pip compile`
cannot regenerate requirements while a path source exists; the sibling is declared twice (pyproject and BUILD),
and nothing observed checks that the two agree.

## Install and pinning

- `uv pip install --offline ./importdag` in a clean venv works (uv honours the source and installs a copy).
  Plain pip does not read `[tool.uv.sources]` and would look for `mikemol-atomicwrite` on PyPI; not measured.
- A throwaway consumer that depends on importdag by path locks offline: uv applies the dependency's sources
  transitively for path deps, so the sibling must sit at the same relative path.
- A paperkit git+url pin could not be measured offline. It would need a `#subdirectory=importdag` pin, and for
  robustness paperkit should also pin mikemol-atomicwrite with its own subdirectory source. A published dist
  would need `mikemol-atomicwrite>=0.1.0` on a real index, and `[tool.uv.sources]` is stripped on publish.

## Not measured

Option C (inject as data); plain pip; git+url, remote cache, CI and BuildBuddy; the other dists' hubs; the
pre-commit domain witnesses, orphan_check and preflight (so whether a `dependencies` entry or a dist-to-dist
edge affects them is unknown); the dagnames and closure_census binaries with the sibling imported; `bazel run`
of the console scripts; building the wheel; absolute file URLs; Python 3.14 (uv) versus 3.13.13 (Bazel).
