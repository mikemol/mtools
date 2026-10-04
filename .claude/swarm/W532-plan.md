# W532 plan: adopting paperkit's tools/ into mtools (cites paperkit:W142)

Drafted 2026-10-03, read-only. Measured over /home/mikemol/github/paperkit/tools/*.py (51 modules + `__init__.py`; 12,167 lines + 39 for `__init__.py` = 12,206 by `wc -l`) and the mtools layout (ratchet/ is the template read in full: pyproject.toml, BUILD.bazel). Anything not measured is marked UNMEASURED.

## 0. The two measured findings that change the shape of the plan

1. **The letter's import graph is incomplete.** It listed 3 edge groups. Measured (grep of `import`/`from` lines, tools/*.py) there are more, and several run to the paperkit engine itself, which would make a pinned mtools dist import paperkit (a cycle, since paperkit pins mtools):
   - inside tools/: eval->cellargs,cellcgroup,cellstage (eval.py:43); dagbzl->dagderive (dagbzl.py:41); closure_census->dagderive,dagnames (closure_census.py:33); closure->imports (closure.py:32); sites->def_sites,imports (sites.py:38-39); mem_db->mem_learn (mem_db.py:37); mem_project->mem_db (mem_project.py:26); mem_harvest->mem_learn,mem_db (mem_harvest.py:36-37,77); bibstruct->vfs (bibstruct.py:131), bibstruct->edit_snapshot (bibstruct.py:171,846,889,930).
   - to the paperkit ENGINE (outside tools/): `grade` from grades_rec.py:28, read_grade.py:41, effective.py:33, verdict.py:177 (lazy); `bib` from effective.py:32; `mutate` from sites.py:42; `paperkit.durable` from dagbzl.py:40 and (lazy, via sys.path.insert) imports.py:118-119; `paperkit.bib` from bibstruct.py:478.
2. **Seventeen modules shell out** and **13 mutate or construct `sys.path`** (list in the table). Of the 51, 43 have a top-level `if __name__ ==` guard; 8 do not (cellstage, cellargs, cellcgroup, dagderive, indexdiverge, pyinfo, read_grade, grades_rec). The two without a guard that are Bazel-invoked scripts (read_grade, grades_rec) need a `main()` wrapper added to atomize: a mechanical change, but a change. UNMEASURED: whether they run their body at import time or use another idiom (not read past the first lines).

## 1. Module table (all 51)

Columns: lines | purpose (from docstring) | cluster -> destination | sys.path (real mutation site, else `-`) | subprocess import | shebang/main-guard (S=shebang, G=`__main__` guard) | paperkit invocation by path (file:line; "mention" = seen only in a comment/doc, invocation form unverified) | tools/-internal edges (out -> / in <-) | external python importers.

Destinations are the proposed distributions of section 2.

| module | lines | purpose | dest | sys.path | subproc | S/G | invoked by path in paperkit | internal edges | ext. importers |
|---|---|---|---|---|---|---|---|---|---|
| absence_audit | 233 | refuse an unverified "nothing gates this" claim | gatecheck | - | no | S,G | .claude/settings.json:112 (hook command) | none | none |
| bb_records | 155 | read BuildBuddy execution records for one invocation, count them | buildtel | - | no | -,G | none found | none | none |
| bibstruct | 2316 | structural questions about a warrants .bib (claim DAG) | NOT PORTED (W61) | bibstruct.py:477 | no | S,G | components.bzl:49 mention | -> vfs, edit_snapshot | none found |
| buildpulse | 355 | report a running //:hook's windowed action rate | buildtel | - | yes | -,G | none found | none | none |
| cellargs | 90 | typed record of one sweep cell's argv | mutantcell | - | no | S,no G | none (BUILD.bazel:57 srcs of eval) | <- eval | none |
| cellcgroup | 97 | a sweep cell's view of its own cgroup | mutantcell | - | no | S,no G | none (BUILD.bazel:57 srcs of eval) | <- eval | none |
| cellstage | 143 | place engine bytecode and deliver one counterfactual | mutantcell | - | no | S,no G | none (BUILD.bazel:57 srcs of eval) | <- eval | none |
| closure_census | 255 | which witnesses reach the engine via a subprocess closure cannot see | importdag | - (docstring) | yes | -,G | none found | -> dagderive, dagnames | 1 (tests/boundaries_closure_census.py:67) |
| closure | 334 | a witness's engine-module closure roots | importdag | - (comment :268) | no | S,G | none found | -> imports | none |
| coord_sample | 118 | sample the coordinator's memory to a durable file | buildtel | - | no | S,G | .githooks/pre-commit:279 | none | none |
| cpuweight | 304 | put the build's own cgroup under a proportional CPU weight | memres | - | no | S,G | .githooks/pre-commit:294 | none | 1 (tests/boundaries_cpuweight.py, by name; form UNMEASURED) |
| dagbzl | 129 | own paperkit/dag.bzl: render, write, check fresh | importdag | - | no | -,G | paperkit/dag.bzl:1,5,7 (`python3 tools/dagbzl.py --write`) | -> dagderive | none |
| dagderive | 159 | derive the engine's import DAG, both edge sides in one namespace | importdag | - | no | -,no G | paperkit/BUILD.bazel (form unverified), dag.bzl:4 mention | <- dagbzl, closure_census | 2 (boundaries_config.py:32, boundaries_components.py:48) |
| dagnames | 157 | name every engine module importably from the component partition | importdag | dagnames.py:109 (string for a child interpreter) | yes | -,G | paperkit/library/BUILD.bazel (form unverified) | <- closure_census | 1 (boundaries_config.py:33) |
| decisions | 112 | decision-coverage aggregator (grid twin of grader.decisions_unasserted) | mutantcell | - | no | S,G | none found | none | none (tests/boundaries_decisions.py exists; edge UNMEASURED) |
| def_sites | 84 | enumerate def-sites of a .py source (mutation unit) | mutantcell | - | no | S,G | none found | <- sites | none |
| edit_snapshot | 1902 | recoverable snapshot for any tool that rewrites tree files | treeio (deferred) | edit_snapshot.py:1043 (+6 child-code strings :1378-1565) | yes | S,G | none found | <- bibstruct | none found |
| effective | 123 | effective-grade reading over assembled grade records | gradekit | effective.py:31 | no | S,G | none found | none; engine: bib, grade | none |
| eval | 388 | run a claim's check against a mutated engine, report whether it flips | mutantcell | - | yes | S,G | tools/calc.bzl:433,479; tools/BUILD.bazel:56 (py_binary main) | -> cellargs, cellcgroup, cellstage | none |
| flatorder | 215 | the flat-import population and its repair order | importaudit | - (docs) | yes | -,G | none found | none | none |
| grades_rec | 61 | a project's Δ table assembled from grade records | gradekit | grades_rec.py:27 | no | S,no G | tools/verb.bzl:308, bibtex.bzl:146,1235 (mention) | none; engine: grade | none |
| hook_grid | 202 | //:hook member list vs MODULE drift made loud | gatecheck | - | no | S,G | .githooks/pre-commit:110 | none | none |
| hook_index | 86 | worktree≡index precondition for the hook's verdict | gatecheck | - | yes | S,G | .githooks/pre-commit:96; paper/checks/claims.py:704 asserts the spelling | none | none (indexdiverge is its extracted predicate) |
| image_digest | 55 | executor image digests a verdict is keyed on | buildtel | - | yes | -,G | tools/toolchain_status.sh (2 sites) | none | none |
| imports | 129 | enumerate a module's engine-internal imports (the edges) | importdag | imports.py:118 (lazy, imports `durable`) | no | S,G | paperkit/components.bzl:8 mention; boundaries/warrants.bib | <- closure, sites | none |
| indexdiverge | 47 | pure predicate: which paths make worktree != index | gatecheck | - | no | -,no G | none (library) | none | 1 (tests/boundaries_hook_index.py:37) |
| lint_bzl | 50 | .bzl run_shell must invoke tools, not embed program logic | gatecheck | - | no | S,G | tools/BUILD.bazel; boundaries/warrants.bib | none | none |
| logs_push | 176 | push a gate run's structured findings to a log store | buildtel | - | no | -,G | .githooks/pre-commit:321 | none | 1 (tests/boundaries_logs_push.py:26) |
| mem_converge | 147 | has the reservation loop converged | memres | - | no | S,G | none found | none | none |
| mem_db | 126 | observation store (mem.sqlite) behind the reservation ladder | memres | mem_db.py:36 | no | S,G | none found | -> mem_learn; <- mem_project, mem_harvest | none (tests/boundaries_mem_db.py; form UNMEASURED) |
| mem_harvest | 111 | fold cell peaks into a project's manifest | memres | mem_harvest.py:35 | no | S,G | .githooks/pre-commit:315 | -> mem_learn, mem_db | none |
| mem_learn | 108 | project a memory manifest from observed cgroup peaks | memres | - | no | S,G | none found | <- mem_db, mem_harvest | none |
| mem_project | 61 | project mem.sqlite -> mem.json (Starlark-readable) | memres | mem_project.py:25 | no | S,G | .githooks/pre-commit:236; bibtex.bzl:752 mention | -> mem_db | none |
| pathaudit | 154 | every sys.path mutation in the tree, still load-bearing? | importaudit | - (it audits them) | yes | -,G | none found | none | none |
| probe | 107 | invalidation-probe protocol, mechanized | buildtel (cohesion UNMEASURED) | - | yes | S,G | none found | none | none |
| project_endpoints | 117 | project remote endpoints into .bazelrc from the host directory | buildtel | - | yes | -,G | .githooks/pre-commit:46; .bazelrc:411 | none | none |
| pyc | 22 | compile one .py to a .pyc build artifact | pkgbuild | - | no | S,no-needed(G) | tools/calc.bzl:303 | none | none |
| pyinfo | 4 | prints sys.executable | pkgbuild | - | no | -,no G | tools/BUILD.bazel:30 (py_binary) | none | none |
| ratchet | 299 | regex-census paydown gate | RETIRE (see sec. 5) | - | no | S,G | none found | none | none |
| read_grade | 53 | grade as a cheap reading over a calc record | gradekit | read_grade.py:40 | no | S,no G | tools/calc.bzl:761 | none; engine: grade | none |
| report_refresh | 62 | regenerate report/ assets from Bazel-built records | gradekit | - | yes | -,G | report/gen.py:62 (doc: `python3 tools/report_refresh.py`) | none | none |
| rungate | 94 | run a gate target under the repo's resource budget | gatecheck | - | yes | -,G | none found (UNMEASURED beyond .py/.bzl/.sh/.bib/.toml grep) | none | none |
| sens | 60 | aggregate per-(claim,site) flips into a sensitivity set | mutantcell | - | no | S,G | none found | none | none |
| sites | 71 | every perturbation site of the engine as (module, SPEC) | mutantcell | sites.py:36 | no | S,G | none found | -> def_sites, imports; engine: mutate | none |
| sortaudit | 143 | files where an import SORT moved a load-bearing import | importaudit | - (it audits them) | yes | -,G | none found | none | none |
| sweep_budget | 54 | RAM budget for the mutation sweep (--local_ram_resources) | memres | - | no | S,G | .githooks/pre-commit:239 | none | none |
| verdict | 260 | the {verb,verdict} record authority | gradekit | verdict.py:176 (lazy; imports `grade`) | yes | S,G | tools/calc.bzl:700, verb.bzl:13; boundaries/warrants.bib | none; engine: grade | none (tests/boundaries_verdict.py; form UNMEASURED) |
| vfs | 1207 | one read/write seam over working tree and git history | treeio (deferred) | - | yes | S,G | pyproject.toml (ruff per-file note); no script call found | <- bibstruct | none found |
| wheel | 161 | build the engine's wheel the cell installs from | pkgbuild | - | no | -,G | tools/calc.bzl:379 (`-P` is load-bearing there) | none | none (tests/boundaries_wheel.py) |
| witness_reach | 83 | load every witness as the bib spells it (bare python3, project cwd) | gatecheck | witness_reach.py:52 (child code string) | yes | -,G | none found | none | none |
| zswap_probe | 188 | sample cgroup memory + zswap counters in one pass | memres | - | no | S,G | none found | none | none |

Footnote on the shebang column: modules with a shebang but no guard (cellargs, cellcgroup, cellstage, read_grade, grades_rec) are either libraries carrying a stray shebang or body-at-import scripts; this is one finding for the porter, not 5.
Footnote on `invoked by path`: the search covered *.bzl, BUILD.bazel, *.bib, *.toml, *.yml, *.sh, *.bazel, *.json, Makefile, .githooks/pre-commit, .claude/settings.json, .bazelrc and report/gen.py, paper/checks/claims.py, paperkit/grader.py, paperkit/__init__.py. UNMEASURED: .md files (skills, cotype, ledger docs; the shell may not grep .md), `-m tools.x` spellings, `$(location ...)` labels in BUILD files other than those listed, and `cmd:` lines inside per-paper .bib files not named warrants.bib (only boundaries/warrants.bib matched).
Footnote on tests: paperkit's tests of these live in /home/mikemol/github/paperkit/paperkit/tests/boundaries_*.py. Twelve of 18 sampled files mention tools: config, agree, cpuweight, logs_push, check, components, mem_db, closure_census, wheel, verdict, dag_regen, hook_index. UNMEASURED: which of the 51 modules have no test at all (mtools' bar, "every test warranted", does not require a test per module, but a ported module with no witness arrives unprotected; the porter should measure per package).

## 2. Proposed packages (9 distributions + 2 non-ports)

Rule applied: group by measured import edges first, then by shared concern; never one package per module. Per-distribution cost is high (ratchet/ carries BUILD.bazel 200 lines, pyproject.toml 278 lines, uv.lock, two requirements files, rubric.tsv, warrants.bib, paper.toml, ratchet-preview.txt, MODULE.bazel pip.parse hub), which is the argument for few packages.

| dist | import package | modules | n | argument |
|---|---|---|---|---|
| mikemol-mutantcell | mikemol.mutantcell | eval, cellargs, cellcgroup, cellstage, sens, sites, def_sites, decisions | 8 | edges: eval->{cellargs,cellcgroup,cellstage}; sites->def_sites. BUILD.bazel:57 already bundles eval+3 as one py_binary's srcs. sens/decisions have no edges but the same concern (the mutation sweep). Caveat: sites imports engine `mutate`. |
| mikemol-importdag | mikemol.importdag | dagderive, dagnames, dagbzl, imports, closure, closure_census | 6 | edges: dagbzl->dagderive; closure_census->{dagderive,dagnames}; closure->imports. All 5 external python importers of dagderive/dagnames/closure_census sit here. Caveat: dagbzl needs `paperkit.durable`, imports needs `durable`. |
| mikemol-memres | mikemol.memres | mem_learn, mem_db, mem_project, mem_harvest, mem_converge, sweep_budget, cpuweight, zswap_probe | 8 | edges: mem_db->mem_learn; mem_project->mem_db; mem_harvest->{mem_learn,mem_db}. The last 3 have no edges (shared concern only). MERGE CANDIDATE into mikemol-fence (see sec. 5). |
| mikemol-buildtel | mikemol.buildtel | bb_records, buildpulse, logs_push, coord_sample, project_endpoints, image_digest, probe | 7 | zero internal edges, shared concern (build/hook telemetry). Honest weakest cohesion; it is one package only because 7 one-module distributions would cost 7 BUILD/pyproject/lock sets. |
| mikemol-gradekit | mikemol.gradekit | verdict, grades_rec, read_grade, effective, report_refresh | 5 | shared concern (record authority and grade readings). NOT portable as-is: 4 of the 5 import engine `grade`/`bib` (sec. 0). Blocked on a decision. |
| mikemol-gatecheck | mikemol.gatecheck | hook_index, indexdiverge, hook_grid, rungate, absence_audit, lint_bzl, witness_reach | 7 | pre-commit and gate helpers; zero internal edges; indexdiverge is hook_index's extracted pure half (docstring) and has the 1 external importer. |
| mikemol-importaudit | mikemol.importaudit | flatorder, sortaudit, pathaudit | 3 | the sys.path-retirement instruments (W141's own tools). They audit the thing this migration removes; no call site found in paperkit. Port last or retire (open question 4). |
| mikemol-pkgbuild | mikemol.pkgbuild | wheel, pyc, pyinfo | 3 | Bazel packaging actions (calc.bzl:303,379; BUILD.bazel:30). Zero edges. Smallest, so it is the layout pathfinder. |
| mikemol-treeio | mikemol.treeio | edit_snapshot, vfs | 2 | DEFERRED. 3,109 lines; the only importer of both is bibstruct (measured, sec. 0), so they move or stay with bibstruct. vfs looks vendored (pyproject.toml notes "vendored library"; docstring is a ⟡ substrate-origin form); edit_snapshot imports a sibling `scripts/ratchet` at :1043-1045, which is NOT tools/ratchet.py. |
| (not ported) bibstruct | - | bibstruct | 1 | paperkit:W61 ruling (paperkit owns it). |
| (retire) ratchet | - | ratchet | 1 | not drift, a different tool (sec. 5). |

Counts: 8+6+8+7+5+7+3+3+2+1+1 = 51. `tools/__init__.py` (39 lines) is dropped: it is the Ζ·tools·package marker whose purpose (declaring edges importable) is replaced by the dist boundaries.

Layout for each (copy ratchet/, measured): `<dist>/pyproject.toml` (name mikemol-<x>, `[tool.setuptools.packages.find] where=["src"] include=["mikemol.*"]`, py.typed package-data, ruff `select=["ALL"]` preview, strict mypy with `mypy_path="src"` + `explicit_package_bases`, per-file ignores only where a module's one responsibility is a subprocess, as ratchet does for census.py), `src/mikemol/<x>/{__init__.py,py.typed,<module>.py...}` with NO `src/mikemol/__init__.py`, `tests/test_*.py`, `BUILD.bazel` (py_library with `imports=["src"]`, one py_test per test module, ruff/ratchet_gate/mutants/mypy sh_tests, `venv_from_hub`, `dist_checks()`), `requirements*.txt`, `uv.lock`, `rubric.tsv`, `warrants.bib`, `paper.toml`, `ratchet-preview.txt`, `README.md`. Every file carries the two-line SPDX + Copyright header the `flake8-copyright` rule demands (ratchet pyproject.toml:233-234); paperkit's files have none, so the header is part of admission. Third-party runtime deps: UNMEASURED per module (not read for non-stdlib imports); mem_db uses sqlite3 (stdlib).

## 3. Entry points: every call site -> new spelling

Convention (matches existing `mikemol-fence`, `mikemol-membudget`, `mikemol-ratchet`): console script `mikemol-<tool>` mapped to `mikemol.<pkg>.<tool>:main`; every module with a script role also gets `if __name__ == "__main__": raise SystemExit(main())` so `python3 -m mikemol.<pkg>.<tool>` works for Bazel actions. Bazel actions that today spawn `python3 tools/x.py` should become `py_binary` targets in the owning dist (as `//ratchet:ratchet_cli` is), referenced by label, because rules_python resolves by layout with no sys.path. Library-only modules (cellargs, cellcgroup, cellstage, dagderive, indexdiverge, mem_learn, def_sites) ship no script.

| current call site | new spelling | dist |
|---|---|---|
| tools/calc.bzl:433,479 and tools/cell.bzl, tools/BUILD.bazel:56 `python3 tools/eval.py` | `mikemol-eval` / `-m mikemol.mutantcell.eval` / `//mutantcell:eval` py_binary (its srcs are eval + 3 siblings today) | mutantcell |
| (no site) sens, sites, def_sites, decisions | `-m mikemol.mutantcell.<x>` | mutantcell |
| paperkit/dag.bzl:7 `python3 tools/dagbzl.py --write/--check` | `mikemol-dagbzl` | importdag |
| paperkit/BUILD.bazel `tools/dagderive.py` (form unverified) | library `mikemol.importdag.dagderive` (no `__main__` guard today); if the BUILD spawns it, a `main()` is added | importdag |
| paperkit/library/BUILD.bazel `tools/dagnames.py` | `mikemol-dagnames` | importdag |
| paperkit/components.bzl:8, boundaries/warrants.bib `tools/imports.py` | `mikemol-imports` | importdag |
| closure, closure_census (no site found) | `-m` only | importdag |
| .githooks/pre-commit:236 `tools/mem_project.py` (+ bibtex.bzl:752) | `mikemol-mem-project` | memres |
| pre-commit:315 `tools/mem_harvest.py` | `mikemol-mem-harvest` | memres |
| pre-commit:239 `tools/sweep_budget.py` | `mikemol-sweep-budget` | memres |
| pre-commit:294 `tools/cpuweight.py` | `mikemol-cpuweight` | memres |
| mem_converge, mem_db, zswap_probe (no site) | `-m` only | memres |
| pre-commit:279 `tools/coord_sample.py` | `mikemol-coord-sample` | buildtel |
| pre-commit:321 `tools/logs_push.py` | `mikemol-logs-push` | buildtel |
| pre-commit:46 and .bazelrc:411 `tools/project_endpoints.py` | `mikemol-project-endpoints` | buildtel |
| tools/toolchain_status.sh `tools/image_digest.py` (2 sites) | `mikemol-image-digest` | buildtel |
| bb_records, buildpulse, probe (no site) | `-m` only | buildtel |
| calc.bzl:700, verb.bzl:13, warrants.bib `tools/verdict.py` | `mikemol-verdict` (name clash: hooks ships `mikemol.hooks.verdict`, an unrelated module, so the prefix `mikemol-gradekit-verdict` is the safer spelling; operator/integrator picks) | gradekit |
| calc.bzl:761 `tools/read_grade.py` | `mikemol-read-grade` | gradekit |
| verb.bzl, bibtex.bzl `tools/grades_rec.py` | `mikemol-grades-rec` | gradekit |
| report/gen.py:62 `python3 tools/report_refresh.py` | `mikemol-report-refresh` | gradekit |
| .githooks/pre-commit:96 and claims.py:704 `tools/hook_index.py` | `mikemol-hook-index` (NOTE claims.py:704 asserts the literal string "tools/hook_index.py" is in the hook: a paperkit witness that must change in the same paperkit commit) | gatecheck |
| pre-commit:110 `tools/hook_grid.py` | `mikemol-hook-grid` | gatecheck |
| .claude/settings.json:112 `python3 "$CLAUDE_PROJECT_DIR/tools/absence_audit.py"` | `mikemol-absence-audit` (a settings.json hook command: needs the console script on PATH in that environment, or `.venv/bin/` spelling) | gatecheck |
| tools/BUILD.bazel, warrants.bib `tools/lint_bzl.py` | `mikemol-lint-bzl` | gatecheck |
| rungate, witness_reach, indexdiverge | `-m` / library | gatecheck |
| calc.bzl:379 `tools/wheel.py` | `mikemol-wheel` (BUT see risk 5: calc.bzl:379 documents `-P` as load-bearing because python puts the script dir on sys.path; running as an installed script changes that, so the `-P` rationale must be re-measured) | pkgbuild |
| calc.bzl:303 `tools/pyc.py` | `mikemol-pyc` | pkgbuild |
| tools/BUILD.bazel:30 `py_binary(pyinfo)` | `//pkgbuild:pyinfo` py_binary | pkgbuild |
| flatorder, sortaudit, pathaudit | `-m` only | importaudit |

## 4. Port order (leaves first) and waypoint titles

Dependency between dists: none of the 9 imports another (measured: every internal edge is within one cluster above). The only cross-dist coupling is (a) engine modules of paperkit (gradekit, importdag, mutantcell/sites) and (b) bibstruct->treeio. So order is by risk, not by import depth.

| # | dist | needs | waypoint title (one clause, under 150 chars) |
|---|---|---|---|
| 1 | pkgbuild | nothing | `mikemol-pkgbuild: port wheel, pyc and pyinfo from paperkit tools/ as the layout pathfinder for paperkit:W142` |
| 2 | buildtel | 1 | `mikemol-buildtel: port bb_records, buildpulse, logs_push, coord_sample, project_endpoints, image_digest and probe (paperkit:W142)` |
| 3 | gatecheck | 1 | `mikemol-gatecheck: port hook_index, indexdiverge, hook_grid, rungate, absence_audit, lint_bzl and witness_reach (paperkit:W142)` |
| 4 | mutantcell | 1; decide the `mutate` edge for sites | `mikemol-mutantcell: port eval, cellargs, cellcgroup, cellstage, sens, sites, def_sites and decisions (paperkit:W142)` |
| 5 | memres | 1; fence merge decision | `mikemol-memres: port the mem_* store, sweep_budget, cpuweight and zswap_probe, or fold them into fence (paperkit:W142)` |
| 6 | importdag | 1; decide the `durable` edge | `mikemol-importdag: port dagderive, dagnames, dagbzl, imports, closure and closure_census (paperkit:W142)` |
| 7 | importaudit | 6 | `mikemol-importaudit: port flatorder, sortaudit and pathaudit, or retire them with paperkit's sys.path arc (paperkit:W142)` |
| 8 | gradekit | engine decision (Q1) | `mikemol-gradekit: port verdict, grades_rec, read_grade, effective and report_refresh once the paperkit grade/bib edge is cut (paperkit:W142)` |
| 9 | treeio | W61 ruling (Q2) | `mikemol-treeio: decide and port edit_snapshot and vfs with or without bibstruct (paperkit:W142)` |
| r | ratchet | none | `retire paperkit tools/ratchet.py: it has no in-tree consumer and is not mtools' ratchet (paperkit:W142)` |
| ctrl | (paperkit side) | each of 1-9 | not mtools' to mint; tell paperkit the section-3 spellings and the pin sha per package. |

Per package, "port" means: the same behaviour, `main()` extracted where missing, no `sys.path` mutation, at the ruff ALL / strict mypy bar with no waivers (a `# noqa` is forbidden by standing rule), tests moved or written and warranted. Atomize further: the integrator should split any title above whose unit stays top-ready across ticks (per the atomize rule); 7-8 modules per waypoint is likely too coarse, so each row above is a parent and the per-module sub-waypoints are the landable units.

## 5. Risks and open questions

Ratchet drift (measured, answers the letter's guess): NOT drift. paperkit's tools/ratchet.py (299 lines) is a regex-census gate with flags `--pattern`, `--set`, `--grow`, `--replace` over two files (ratchet.py:25-37). mtools' `mikemol-ratchet` takes `dist`, `files...` and `--rev`, censuses ruff findings of a distribution, and compares JSON baselines against a git revision (ratchet/src/mikemol/ratchet/cli.py:53-56,97-106; `grep` for `--pattern` / `--grow` / `--replace` in ratchet/src finds only prose about "growth"). The two share a name and the paydown-only idea, nothing else. A line diff was not run because the two share no structure to diff. tools/ratchet.py has no importer in tools/ and no call site in paperkit (searched .py/.bzl/BUILD/.bib/.sh/pre-commit). edit_snapshot.py:1045 imports `ratchet` from `<dir>/../scripts/` (a different file; best-effort inside `try/except Exception`). So retiring it deletes behaviour that nothing in paperkit calls, but that is a paperkit decision.

Open questions for the operator:
1. **Engine edge.** grades_rec, read_grade, effective, verdict (lazy), sites, dagbzl and imports (lazy) import paperkit's own `grade`, `bib`, `mutate`, `durable`. A pinned mtools dist cannot import paperkit (cycle). Options: cut the edge by moving those engine modules into mtools too, accept the call as data (file-in/file-out CLI, behaviour change), or leave those modules in paperkit. The migration cannot atomize them without one of these; which?
2. **bibstruct/vfs/edit_snapshot.** bibstruct stays per W61. vfs and edit_snapshot are imported only by bibstruct. Recommend they stay with it (treeio deferred) unless W61 is revisited; confirm. Both look vendored (substrate-origin), which would make mtools a second owner of vendored code.
3. **fence overlap.** memres (cellcgroup, cpuweight, zswap_probe, mem_*) and fence (cgroup.py, peaks.py, autosize.py, admit.py, membudget_cli.py) cover the same ground (cgroup v2 reservation and memory budgeting; standing note: fence's membudget is "the one client"). Content overlap was NOT measured (only file names and two docstrings). Recommend a measurement waypoint before memres is minted; the answer may be "fold into fence".
4. **importaudit.** flatorder/sortaudit/pathaudit audit sys.path debt that this migration retires. Port, or retire when W141 closes?
5. **Behaviour changes that cannot be avoided.** (a) wheel's `-P` rationale (calc.bzl:379) assumes a script-dir-on-sys.path regime that an installed console script changes; (b) the 8 no-guard modules get a `main()`; (c) dagnames.py:109-114 and witness_reach.py:52 build child-interpreter code strings that `sys.path.insert` and import `tools.dagnames` by name (dagnames.py:111): those strings must be rewritten to `mikemol.importdag...`, and what they test (a witness run bare, project cwd) is a property of the paperkit tree, so their tests move to paperkit or become fixtures; (d) paperkit's `claims.py:704` witness asserts the string `tools/hook_index.py` appears in the hook.
6. **Naming.** `mikemol-verdict` vs hooks' unrelated `mikemol.hooks.verdict`: prefix the console script? Package names above are proposals (mutantcell, importdag, memres, buildtel, gradekit, gatecheck, importaudit, pkgbuild, treeio); mtools owns naming.
7. **Pins.** paperkit's pin today is one sha for `mikemol-hooks` (pyproject.toml:335, `#subdirectory=hooks`). Nine more pins in a git+url scheme is paperkit's cost; a single umbrella dist would avoid it but defeats the atomization the operator asked for. Operator call.

UNMEASURED summary: per-module test coverage; third-party runtime imports; `.md`/`-m`/label-based invocations; read_grade/grades_rec import-time behaviour; probe's cohesion with buildtel; fence content overlap; whether paperkit's hook spellings can resolve a console script on PATH in the pre-commit and settings.json environments.
