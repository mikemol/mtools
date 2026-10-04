# W552: survey of the four paperkit engine modules the tools/ modules import (cites mtools:W531, W532-plan.md sec. 0 and 5)

Drafted 2026-10-03, read-only. Measured with wc/grep over /home/mikemol/github/paperkit. Operator ruling 2026-10-04: move the engine modules into mtools (or only the used parts); paperkit then pins them. Everything not measured is marked UNMEASURED.

All four live in /home/mikemol/github/paperkit/paperkit/ (the engine package; `build/lib/paperkit/` holds stale copies, ignore). Engine modules import each other BARE (`import bib`, `from grade import ...`), which works only because the engine dir is on sys.path (the flat-import regime paperkit's W141 is retiring); that is why `import grade` inside tools works at all.

## 1. Summary table

| module | file | lines | tools/ uses | non-tools, non-test importing files | test files importing | stdlib-only? | verdict |
|---|---|---|---|---|---|---|---|
| durable | paperkit/durable.py | 78 | `write_atomic` | 2 (project.py:38, cache.py:13) | 1 (boundaries_write_atomic.py:31) | yes | CHEAP: move whole |
| mutate | paperkit/mutate.py | 579 | `_branch_sites`, `_data_sites`, `_flip_sites` (all private) | 2 (grader.py:34, cache.py:52 lazy) | 2 (boundaries_mutate_atom.py:30, boundaries_data_atom.py:37) | yes (ast, sys) | CHEAP: move whole, publish the three names |
| grade | paperkit/grade.py | 487 | `_grade_from_sens`, `clamp`, `below` | 9 files (see 2.3) | 5 | one lazy edge to `bib` | MEDIUM: move whole, but cut one edge to bib first |
| bib | paperkit/bib.py | 731 | `parse_project` (only) | 10 files (see 2.4) | 6 | stdlib + `bibparse` (264 lines, stdlib) | ENTANGLED: do not move whole; interface instead |

## 2. Per module

### 2.1 durable (paperkit/durable.py, 78 lines)
- Purpose (docstring :1-12): "the DURABLE-WRITE primitive: replace the path, never the inode's contents"; the docstring says it deliberately depends on "nothing but the standard library".
- Defs: `_umask` (:22), `write_atomic(path: Path, data: str | bytes)` (:29). No constants.
- Tools use: dagbzl.py:40 `from paperkit import durable`, used at dagbzl.py:120 `durable.write_atomic(dag, want)`; imports.py:119-120 lazy `import durable` then `durable.write_atomic(dag, want)`. Only `write_atomic`.
- Imports (durable.py:16-19): contextlib, os, tempfile, pathlib. No paperkit-internal, no third-party.
- Other paperkit callers: project.py:38, cache.py:13 (2 files outside tools/ and tests). Tests: boundaries_write_atomic.py:31; boundaries_dag_regen.py:76,110,169 holds the literal string `from paperkit import durable` as a probe fixture (a string, would need rewriting).
- State/env: no module state. `_umask` calls `os.umask(0)` then restores it (:22-26): a process-wide, thread-unsafe toggle, not state. No cwd, no sys.path, no subprocess.
- Also: verdict.py:47 DUPLICATES write_atomic "on purpose, and gated for agreement" (a paperkit witness compares them). Moving durable into mtools gives that duplicate a natural home to fold into, but the agreement gate is paperkit's and must be re-pointed.
- Smallest cut: move WHOLE. Package: `mikemol.atomicwrite` / dist `mikemol-atomicwrite` (one function; if too small for a dist, fold into an existing mtools dist that already writes files, UNMEASURED which). Call-site cost for paperkit: 2 engine imports + 2 tools imports.

### 2.2 mutate (paperkit/mutate.py, 579 lines)
- Purpose (docstring :1-40): "Ζ·mutant — the PURE perturbation leaf: given a .py module and a mutation SPEC, emit the perturbed module" (def:, branch:, flip:, data-:, dflip:, import-:, import+: specs). "The mechanical AST surgery ONLY"; sensitivity interpretation stays in grader.py.
- Public entry: `emit_mutant(text, spec)` (:551). CLI at :577-579 (`mutate.py <module.py> <spec>`, uses sys.argv/sys.stdout).
- Tools use: sites.py:42 `from mutate import _branch_sites, _data_sites, _flip_sites`, called at sites.py:53,55,57 (unpacks `(qn, n, arm)`, `(qn, n, test)`, `(qn, n, kind, k, v)`). All three are PRIVATE (underscore) names, so the move must promote them to public API (a contract change that is mtools' to define). sites.py ALSO runs `mutate.py <module> <spec>` per site by path through the grid (sites.py:27 docstring), which becomes `-m` or a console script.
- Imports: `ast`, `sys` only (:44-45). No lazy imports (grep of indented imports empty). No paperkit-internal, no third-party. Internal helpers `_def_sites` (:48), `_base_catching_regions` (:76) etc. are all in-file.
- Other callers outside tools/: grader.py:34 (multi-name import), cache.py:52 (lazy). 2 files. Tests: boundaries_mutate_atom.py:30, boundaries_data_atom.py:37.
- State/env: no module-level mutable state (module-level assignments: none found by grep); no env, cwd, sys.path, subprocess. Only the `__main__` block touches sys.argv.
- Smallest cut: move WHOLE (all 579 lines are one pure AST concern; the used `_*_sites` helpers share the same private helpers, so a subset cut would copy most of the file). Package: `mikemol.mutation` / dist `mikemol-mutation`, with `sites` (and its siblings in the planned mutantcell dist) importing it. Note the plan's mutantcell dist (W532-plan.md:82) would then depend on this dist: the first inter-dist dependency in the migration.

### 2.3 grade (paperkit/grade.py, 487 lines)
- Purpose (docstring :1-11): "the GRADE LADDER + interpretation (Μ·grade)": the pure half of the Δ grader (rungs, clamp/strength/corroboration orders, how a flip-set becomes a grade). Docstring claims "A LEAF: pure data + one pure function, no engine imports"; that is NOT fully true, see the bib edge below.
- Constants (:17-98): STRENGTH, ORDER, RANK_C, GRADE_C, CORRO_C, DECISIONS_C, RESOLUTION_C, BASELINE_C; `SCOPE_C = _ScopeC()` (:163). Functions: `rungs` (:173), `below` (:180), `_grade_from_sens` (:189), `mark_content_sensitive` (:219), `clamp` (:231, signature `clamp(records, owner_grades=None, keys=None)`), `verify_hop` (:389), `_bracket` (:435).
- Tools use (exact): read_grade.py:41 `import grade`, :50 `grade._grade_from_sens(c["baseline"], c["sens"], reachable=...)`; grades_rec.py:28 `import grade`, :60 `grade.clamp(graded, keys=...)`; effective.py:33 `import grade`, :111 `grade.clamp(records(...), owner_grades(owners))`; verdict.py:177 lazy `import grade`, :178 `grade.below(...)`. So 3 of its names: `_grade_from_sens` (private), `clamp`, `below`.
- Imports: top level `from pathlib import Path` only (:15). One LAZY edge: `import bib` at :143 inside `_ScopeC._fill`, reading `bib._SCOPES` (bib.py:70, `("fragment", "full")`). It is lazy on purpose (:126-130: an eager derivation made grade unimportable wherever bib was not staged and broke every calc cell). Nothing else, no third-party.
- Does the used subset need bib? `_grade_from_sens`, `clamp`, `below` do not touch SCOPE_C (grep of SCOPE_C/bib in grade.py finds only :121-163 plus prose). So the tools' used subset is bib-free; only SCOPE_C consumers (UNMEASURED which: the 5 test files, report/grades.py, discriminate.py) pull bib.
- Other callers outside tools/ and tests: discriminate.py:103 (`from grade import (`), grader.py:31 (`_grade_from_sens`), prove.py:50 (lazy `_grade_from_sens`), library/concepts.py:560 (lazy), checks/readme.py:136 (lazy), paper/checks/claims.py:331 (lazy), report/figure.py:15, report/gen.py:26, report/grades.py:37 (`from paperkit.grade import RANK_C`, the package spelling). 9 files; 3 of them already use sys.path-staged bare spelling from outside the engine dir (report/, checks/), so each repoint also needs its sys.path hack reviewed. Tests: boundaries_ladder.py:30, boundaries_clamp.py:18, boundaries_scope.py:32, boundaries_decisions.py:34, boundaries_surface.py:72.
- State/env: `SCOPE_C` is a lazily-filled dict subclass singleton with class attribute `_loaded` (:140-145): mutable, one-shot, process-wide. No env, cwd, sys.path, subprocess.
- Staging constraint (:127-129): read_grade.py "stages grade ALONE" into a Bazel cell. A moved grade must stay importable alone, which means keeping the lazy `bib` edge lazy or severing it.
- Smallest cut: move WHOLE, but replace the `import bib` at :143 with a constant owned by grade (or by the new dist) that bib then imports back: `_SCOPES` is a 2-tuple, so the cheapest cut is to relocate `_SCOPES = ("fragment", "full")` into the grade package and have `bib` import it (the comment at :121-125 already says the constant is owned by bib only because "the parser is what must refuse a typo"; direction can flip). That makes grade a true leaf, as its docstring claims. Package: `mikemol.grade` / dist `mikemol-grade` (ladder, clamp). Alternatively move only `_grade_from_sens`, `clamp`, `below` and their constants; but `clamp` calls `_bracket`, `verify_hop` is in the same fold, and all ladders are shared constants, so the used subset is most of the file: not worth splitting.

### 2.4 bib (paperkit/bib.py, 731 lines)
- Purpose (docstring :1-17): "the ONE parser + data model for a warrants .bib (the claim-DAG)": config load, rubric, dependency order, placement; the grammar lives in `bibparse`.
- Tools use (exact): effective.py:32 `import bib`, :55 `bib.parse_project(project_dir)`. ONLY `parse_project`. (bibstruct.py:478 `import paperkit.bib as B` is not ported, W61.) Transitively `parse_project` (:544) calls `load_config` (:492) and `parse` (:207), so the "used subset" is the config+parse spine, roughly :45-300 and :492-600.
- Public surface (defs): parse (:207), paper_keys (:309), load_config (:492), parse_project (:544), load_bib (:589), rubric_rows (:605), rubric (:633), dep_order (:638), is_placed (:655), emit_anchors (:664), emit_path (:696), rests_closure (:708). Constants `_SCALAR` (:45), `_LIST` (:66), `_SCOPES` (:70). Module state: `_WARNED: set` (:93), a process-wide dedupe set for warnings.
- Imports: stdlib ast, csv, inspect, re, sys, tomllib, pathlib, typing (:21-28) and `import bibparse` (:37), paperkit-internal sibling (264 lines; its imports are `dataclasses` only, bibparse.py:43-44). No third-party.
- THE ENTANGLEMENT: `load_config` calls `_misplaced_paper_key(cfg)` (:497) which calls `_param_config_keys()` (:455), which at :325-350 globs `Path(__file__).resolve().parent.glob("*.py")` and AST-parses every sibling engine module for `Param(..., config="x")` declarations. Moved into mtools, that glob scans mtools' directory, finds no Params, and the [paper]-key misplacement guard silently loses the keys the engine's Params own (e.g. `root`, per the :342-346 docstring). Also `paper_keys()` (:309) does `inspect.getsource(load_config)`, i.e. source-introspection of itself (fine if moved whole, breaks if the function is wrapped or compiled). `sys.exit` is called from the module (:376, :485, :496) and `sys.stderr.write` at :267. Also: UNMEASURED which other engine modules (config.py? Params?) own those `Param(` declarations; only their existence is known from the docstring.
- Other callers outside tools/ and tests: gen_fields.py:16 (checks/), demo/checks/carries.py:23, paper/checks/gen_formulas.py:23, paper/checks/claims.py:1195 (lazy, `as B`), paperkit/coherence.py:67, discriminate.py:83, gate.py:49, project.py:37,41,42 (three statements, one file), rhetoric.py:91, footdeps.py:39. 10 files. paperkit/__init__.py:9,32 mention it in a doc (the "package spelling" contract: `from paperkit import bib`). Tests: boundaries_bib.py:23, boundaries_emit.py:22, boundaries_genre_pure.py:60, boundaries_closure_census.py:99, boundaries_package_shadow.py:48 (a string probe), boundaries_scope.py:30. bib is the engine's center (project, gate, coherence, rhetoric, footdeps all depend on it): moving it whole would make paperkit's core import from a pinned dependency, the largest repoint of the four.
- Smallest cut for the TOOLS: do not move bib. The tools use one function (`effective.records`, effective.py:52-62, joins grade files to the bib's `rests-on` edges). Cut options, in order of preference:
  (a) Interface: effective takes the edges as DATA, a `{key: {"rests-on": [...]}}` mapping (or a Protocol `ClaimGraph` with `rests_on(key)`), supplied by paperkit's caller; the CLI reads a JSON the paperkit side emits. Behaviour change: effective.py no longer parses a project's bib itself (this is the "accept the call as data" option of W532-plan.md:160).
  (b) Move `bibparse` (264 lines, dataclasses only) alone into mtools as `mikemol-bibparse`, and a small `mikemol.warrants.edges(bib_text) -> {key: [rests-on]}` over it; effective uses that. `bib.py` then imports bibparse from the pinned dist (paperkit's bib.py:37 is a one-line repoint). Mind: mtools already has a bib reader, `raw_bib` in mikemol-witness (ported in 72830da, "the full-fidelity bib reader"): UNMEASURED whether it already subsumes bibparse; measure before minting a second parser.
  (c) Move bib whole after splitting out `_param_config_keys` (the engine-layout coupling). Largest cost; only do it if the operator wants the claim-DAG model itself in mtools.

## 3. Which are cheap, which entangled

- Cheap, no transitive closure: durable (stdlib, 78 lines), mutate (stdlib, 579 lines).
- Medium: grade. Closure is `grade` + one lazy 2-tuple constant from `bib`; severing it makes grade a true leaf. No other engine module comes along (grade imports no other engine module; verified: its only non-stdlib import is the lazy `bib` at :143).
- Entangled: bib. Closure to move whole is bib.py + bibparse.py (995 lines together) AND the layout coupling of `_param_config_keys` to the sibling engine files (whichever module declares `Param(config=...)`, UNMEASURED). It drags nothing else by import, but its introspection ties it to the engine's directory. It is also the most-imported (10 non-test files).
- Dependency note: grade -> bib (lazy) is the only engine-to-engine edge among the four; mutate and durable are independent of all three.

## 4. Cost model from existing mtools carvings (git log, ledger/corpus/witness)

- mikemol-corpus: 5 module commits (4f1afc2 ... 250ca18), each "module N of M: X moves with its <root/tenant> made the caller's argument".
- mikemol-witness: 5 module commits (2b108cf ... 719587d); commit 9239e52 shows the pattern for engine coupling: "moves with its bib path and the engine's parse as required arguments, because the split removed both of its defaults"; 719587d: "engine-free and without the ROOT-derived project".
- mikemol-ledger: 12 module commits (09d0e2d ... 45c8d35); 4690616 "moves with its bib tool supplied by the caller".
- Cost model, therefore: one commit per module; every ROOT/cwd/default becomes a required argument; the engine is injected, never imported; new suite written where none existed (ae7e6f9). Per dist fixed cost is high (W532-plan.md:78: ratchet/ carries ~10 files). So: durable+mutate (2 small leaf modules) = at most 2 module commits each; grade = 1-2; bib (interface route) = 1 interface + `effective` adaptation.

## 5. Recommended order and waypoint titles

1. durable (cheapest, unblocks dagbzl and imports, which unblocks importdag).
2. mutate (unblocks sites, so mutantcell; promotes 3 private names to public).
3. grade, after relocating `_SCOPES` (unblocks read_grade, grades_rec, verdict, and half of effective).
4. bib interface (option a or b) last, since it only blocks effective.py (one of five gradekit modules) and is the most invasive; effective can wait while the other four gradekit modules ship.

Waypoint titles (each under 150 chars, one clause):
- `mikemol-atomicwrite: move paperkit durable.write_atomic whole so tools dagbzl and imports stop importing the engine (paperkit:W142, mtools:W531)`
- `mikemol-mutation: move paperkit mutate.py whole and publish _branch_sites, _data_sites and _flip_sites for the sites tool (mtools:W531)`
- `mikemol-grade: move paperkit grade.py whole after relocating _SCOPES out of bib, making the ladder a true leaf (mtools:W531)`
- `mikemol-warrants: give effective its rests-on edges as data or a bibparse-based reader instead of importing paperkit bib (mtools:W531)`
- `survey whether mikemol-witness raw_bib already subsumes paperkit bibparse before minting a second bib parser (mtools:W531)`
- `paperkit: repoint grade, mutate and durable imports (9, 2 and 2 non-test files) to the pinned mtools dists (paperkit side, not mtools' to mint)`

## 6. Open questions

1. bib: interface (a), bibparse+edges (b), or whole move (c)? The load-bearing hazard is `_param_config_keys` globbing the engine dir (bib.py:325-350); a whole move needs an owner decision on where `Param(config=...)` declarations live.
2. Publishing private names: `_grade_from_sens`, `_branch_sites`, `_data_sites`, `_flip_sites` are underscore-private today. Promote to public names in the mtools dists (renames break paperkit callers: grader.py:31 and :34), or keep the underscores and document them as the cross-package seam?
3. Does `raw_bib` (mikemol-witness) already subsume bibparse? UNMEASURED (not read).
4. durable and verdict.py:47 duplicate write_atomic under a paperkit agreement gate; after the move should verdict import it (dropping the duplicate and the gate), or keep the intentional duplicate? (verdict.py is staged how in Bazel cells? UNMEASURED.)
5. Package spellings under `mikemol.<name>`: atomicwrite, mutation, grade, warrants, bibparse are proposals; mtools owns naming. Is a 78-line durable worth its own dist, or does it fold into an existing one (UNMEASURED which)?
6. Consumers of SCOPE_C and which engine modules declare `Param(config=...)`: UNMEASURED.
7. Also UNMEASURED: whether the 8 non-guarded read_grade/grades_rec style scripts' Bazel cells (stage `grade` alone, grade.py:127-129) can switch to an installed dist; this is the point of the whole move and needs a Bazel-side probe.
