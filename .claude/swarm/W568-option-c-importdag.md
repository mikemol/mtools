# W568: option C measured on importdag's imports, closure, dagbzl (feeds mtools:W562)

Spike by a worktree fixer, 2026-10-04. A real port of the three modules with NO sibling dependency, nothing
committed. Advice only; the operator decides.

## Result: C works for this one case, and every gate is green

17 of 17 `//importdag/...` targets passed, including `:mutants`, `:mypy`, `:ratchet`, `:suite`, `:venv` and `:reqs`
(109 tests; ruff, format and mypy clean). Built: `seam.py` (71 lines: `type Writer = Callable[[Path, str], None]` and a
private `replace_write`), `imports.py`, `dagbzl.py`, `closure.py` (545 lines against paperkit's 334), and four test
modules. dagbzl.main and imports.main take `writer: Writer = replace_write`; the library entry `imports.regenerate`
requires one. No `mikemol.atomicwrite` import, no BUILD or pyproject dependency edit, no lock change. warrants.bib
was not touched and `//importdag:suite` needed none.

## The default-writer question is the real cost

- (2) CHOSEN: a private temp-then-replace in seam.py, about 30 lines. The CLI keeps working with no new flag. Cost:
  a second implementation of the atomic-write contract, a fork that can drift from atomicwrite (text only, no bytes
  path), and two more tested defs. This is the duplication option C was meant to avoid, and it is the central finding.
- (1) plain `Path.write_text`: no code, but the CLI loses durability (a crash can leave a torn dag.bzl, a hardlink
  twin is overwritten in place, and the generator-eats-its-own-cooking guarantee goes false). Rejected.
- (3) no default (a required `--writer`, or stdout): changes the contract for every caller (dag.bzl:7,
  boundaries_dag_regen.py:114, boundaries_components.py:186); a `--writer MODULE:FUNC` flag needs a dynamic import,
  which under disallow_any is a cast and an eval-like surface.

## Changes forced versus paperkit

Caused by C: the private writer replaces `durable.write_atomic`; imports and dagbzl `main` accept an injected writer
(paperkit's only visible caller is the subprocess `-m tools.dagbzl` in boundaries_dag_regen.py:114, which cannot
inject, so it gets the private writer).

Forced regardless of C (moving into a dist and the strict gates): the engine location is `--engine DIR` (default
`paperkit` under the cwd) instead of `Path(__file__).parents[1]`, so paperkit call sites add `--engine`
(paperkit/dag.bzl:7, boundaries_dag_regen.py:109-114, boundaries_components.py:186, tools/BUILD.bazel:8,21); the
generated dag.bzl header changed (it named tools/dagbzl.py), so dag.bzl is regenerated once and its freshness check
re-baselined; closure.py, called as a path script at tools/bibtex.bzl:633 and by closure_census's `--closure`
default, moves to `-m mikemol.importdag.closure`; closure's argparse became a hand parser (strict mypy rejects
`argparse.Namespace`), losing `--help` and abbreviations; `dagbzl.literal` (a duplicate of `dagnames.literal`) is
deleted.

Advice from the fixer: imports' `--write` emits the legacy stem-valued format and disagrees with dagbzl's
path-valued one; running both flips the file. Keep only `imports()` and the edge listing, drop the write/check half.
Not done, because the task said to port it.

## Other sibling edges found

closure_census reaches closure BY PATH as a subprocess (a sibling by file path, not an import); once closure is in
the dist its default should become `-m mikemol.importdag.closure`. Within the dist: closure -> imports, dagbzl ->
dagderive and dagnames. Two near-identical `imports()` functions live in one dist (a deliberate fork, because
dagderive's reads package-qualified forms and would change closure's cone). `imports.engine_srcs` is a verbatim
copy of `dagbzl.engine_srcs` (about 5 lines, a trivial follow-up). Nothing here imports paperkit's engine
(grade, bib, mutate) except durable, as the W532 plan said.

## Option C versus A+B (W566), measured

A+B per edge: five BUILD edits, `legacy_create_init = 0` on every consuming py_test, a pyproject dependency plus uv
source, a lock regeneration, a stale requirements.txt, the sibling declared twice with nothing checking agreement,
and a `uv sync` in the main tree's venv for the hook. Zero duplicated code.
C: no BUILD or pyproject dependency edits; 71 lines of seam plus 92 of tests and a writer parameter through two mains,
about 30 lines of which duplicate atomicwrite. More design and duplicated behaviour per edge, less infrastructure.

## Where injection stops (honest read)

C solves the single-writer-callable class and nothing else measured. It does NOT reach: gradekit needing grade and
bibparse (module-sized APIs; see W569, where `clamp` is code); witness_reach needing dagnames in a child interpreter
(no parameter crosses a process boundary, the child must import the module); mdstruct reusing pycodemod's walk
(copying the walk is the duplication C trades for); anything with shared types across the edge. It does work for
other write-only edges (mem_db, mem_project, logs_push, coord_sample) and for pure data edges, and for sites ->
imports (a narrow pure function), though callers must then wire it.

## Fixer's recommendation (advice)

A+B as the general mechanism; C only for a single narrow data or callable edge where the sibling is optional at
runtime. Reasons: C forces a duplicate or a CLI change; C does not reach gradekit, witness_reach or mdstruct; A+B's
cost is mechanical and fixed per edge. B alone (BUILD deps with no pyproject edge) is the cheaper half, but
whether a dist without the pyproject dependency installs correctly outside Bazel was not measured.

## Not measured

Whether `:mutants` exercised every new def-site (it passed; per-module counts not read); any paperkit-side change
(call sites are from grep over the read-only tree); equivalence of the ported closure on real paperkit input (a
synthetic project only); imports `--write` byte equality (header changed by design); closure_census against the
ported closure; Python 3.13.13 versus 3.14.7; plain pip, git+url, CI, remote cache; whether A+B's pyproject edge
works for these three modules (W566 measured it for importdag -> atomicwrite only).
