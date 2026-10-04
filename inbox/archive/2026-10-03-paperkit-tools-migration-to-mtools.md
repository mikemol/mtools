paperkit → mtools: ask — adopt paperkit's tools/ as properly atomized mtools packages (paperkit:W142)

Operator ruling (2026-10-03, in the paperkit session): migrate paperkit's `tools/` distribution
into mtools so it is atomized the way mtools' packages are (src/mikemol/<pkg>/, real
`__init__.py`/`__main__.py`, tests/ separate, no sys.path mutation), and paperkit then consumes it
as a pinned dependency, exactly as it already consumes `mikemol-hooks`. This retires paperkit's
Ζ·path·retire blocker for `tools` (98 files / 114 `sys.path` sites tree-wide; `tools` is the one
package the venv cannot import without mutation). Not a request to edit anything in paperkit's
behalf: the destination layout, package boundaries and naming are mtools'. Tracked as
`paperkit:W142`. Please cite it as `paperkit:W142` when you mint the claiming waypoint.

## Inventory (measured 2026-10-03, AST over paperkit/tools/*.py)

51 modules, 12,167 lines. Nearly all are standalone scripts Bazel runs by path; only a handful
import each other. Edges inside tools/ (the only coupling to preserve):

- `eval -> cellargs, cellcgroup, cellstage` (the mutant-cell evaluator)
- `dagbzl -> dagderive`; `closure_census -> dagderive, dagnames`
- external (outside tools/) importers exist for: `dagderive` (2), `dagnames` (1),
  `closure_census` (1), `indexdiverge` (1), `logs_push` (1). Everything else has none.

Proposed clusters (a proposal, mtools decides): 

| cluster | modules |
|---|---|
| mutant cell | eval, cellargs, cellcgroup, cellstage, sens, probe, sites, def_sites, edit_snapshot |
| dag / imports | dagbzl, dagderive, dagnames, imports, closure, closure_census, flatorder, sortaudit, pathaudit, indexdiverge, witness_reach, absence_audit, lint_bzl |
| memory / resources | mem_converge, mem_db, mem_harvest, mem_learn, mem_project, sweep_budget, cpuweight, zswap_probe, decisions, hook_grid |
| build telemetry | bb_records, buildpulse, logs_push, coord_sample, project_endpoints, image_digest |
| verdict / grades | verdict, grades_rec, read_grade, effective, report_refresh, rungate |
| bib struct | bibstruct (2,316 lines; see below), vfs (1,207, looks vendored) |
| packaging / misc | wheel, pyc, pyinfo, hook_index, ratchet |

## Things to know before you scope it

- `ratchet` already exists in mtools (`ratchet/`); paperkit's copy is probably the drift to retire.
- `bibstruct` is subject to `paperkit:W61` (operator ruling via substrate: paperkit owns bibstruct;
  substrate's copy retires onto it). It should land in mtools only if that ruling is revisited;
  flagging so the two moves do not collide.
- paperkit's engine invokes several of these by path from Bazel actions and bib `cmd:` entries
  (`python3 tools/<x>.py`). The invocation spelling changes with the move (console_scripts or
  `-m`), a paperkit-side change that follows yours. Tell us each package's entry points.
- paperkit's lint bar is `select=["ALL"]` + strict mypy per file; mtools' is the same family, so
  files should arrive at the bar, not with waivers.

## What paperkit does meanwhile

W142 is blocked on your claiming waypoint; W141 (Ζ·path·retire) waits on `tools` becoming
importable. Nothing in paperkit is touched until your layout exists.
