# W655 - control census and fingerprint walk: port against origin, one real slice

## How it was compared

RUN, not reading-only. substrate's venv (`/home/mikemol/github/substrate/.venv/bin/python`) imports the origin
directly: `_pycodemod_control.control_sites(path)` and `_pycodemod_fingerprint.site_referents(path)` both run, and the
origin's `Census` runs over the same sites. The port ran in `pycodemod/.venv` through `control_census.control_sites`,
`fp_sites.fp_sites` and `census_fp.Census`, with `PYTHON_BOUNDARY`. Scratch scripts are in the session scratchpad
(`origin_run.py`, `port_run.py`, `diff.py`, `census_*.py`, `tables_*.py`); no source file was edited.

Slice, 6 real files, 1376 sites each side (every file parsed, `skipped == []`):

- `pycodemod/src/mikemol/pycodemod/exit.py` (144 sites; loops, comprehensions, `except OSError`)
- `pycodemod/src/mikemol/pycodemod/cli.py` (197; `sys.exit`, `.get`, `or` defaults)
- `pycodemod/src/mikemol/pycodemod/split.py` (231; branches, early exits)
- `substrate/scratch/_pycodemod_sql.py` (430; `con.execute`, `fetchall`, row loops)
- `substrate/scratch/_pycodemod_placement.py` (125; `with`, `try`, early returns)
- `substrate/scratch/_pycodemod_control.py` (249; `yield`, `while`, mode branches)

Plus one probe file (`probe_ctl.py`, 38 sites) for constructs the slice lacks: `for-else`, `while-else`, `try-else`,
`finally`, `assert`, `match`/`case`, `yield from`, `filter`, `all`, `quit`, `async for`, `async with`, `executemany`,
`QB.run`.

The origin has no path column: rows were matched by position inside one file, which holds because both sort by
`(line, construct)`. The port ran twice, with the requested StoreVocab (readers `execute`, `fetchall`, `fetchone`;
receivers `con`, `cur`) and with a "wide" vocab equal to the origin's `STORE_READERS` and `STORE_CONNS`. The two gave
identical output on the 6-file slice; they differ only on the probe (D3 below).

## Table: slice, control census (columns compared: line, construct, kind, sqlform, scope, snippet)

- file: exit.py; construct: (all other groups); kind: all; origin: 117; port: 117; status: same
- file: exit.py; construct: and, comp-if, get-default, get-none, if, return-guard, ternary; kind: mode-branch; origin:
  27; port: 27; status: declared D1 (sqlform dash)
- file: cli.py; construct: (all other groups); kind: all; origin: 169; port: 169; status: same
- file: cli.py; construct: if, or, return-guard, ternary, try; kind: mode-branch; origin: 28; port: 28; status: declared
  D1
- file: split.py; construct: (all other groups); kind: all; origin: 176; port: 176; status: same
- file: split.py; construct: and, comp-if, get-*, if, next-default, or, raise-in-cond, return-guard, ternary, try; kind:
  mode-branch; origin: 55; port: 55; status: declared D1
- file: _pycodemod_sql.py; construct: (all other groups); kind: all; origin: 352; port: 352; status: same
- file: _pycodemod_sql.py; construct: and, any, elif, else, if, or, or-default, return-guard, ternary, try; kind:
  mode-branch; origin: 78 (with the next two); port: 78; status: declared D1
- file: _pycodemod_sql.py; construct: for; kind: row-iteration; origin: 6; port: 6; status: declared D1 (dash in "the
  SELECT itself - ...")
- file: _pycodemod_sql.py; construct: or; kind: row-branch; origin: 1; port: 1; status: declared D1 (`WHERE ... OR ...`)
- file: _pycodemod_sql.py; construct: continue; kind: early-exit; origin: 6; port: 6; status: declared D1 (`WHERE NOT
  (...)`)
- file: _pycodemod_placement.py; construct: (all other groups); kind: all; origin: 116; port: 116; status: same
- file: _pycodemod_placement.py; construct: comp-if, if, or, return-guard; kind: mode-branch; origin: 9; port: 9;
  status: declared D1
- file: _pycodemod_control.py; construct: (all other groups); kind: all; origin: 140; port: 140; status: same
- file: _pycodemod_control.py; construct: and, any, elif, else, get-default, if, or, or-default, return-guard, ternary,
  try; kind: mode-branch; origin: 109; port: 109; status: declared D1

Every (construct, kind) pair of the corpus appears with the same count on both sides: no site was added, dropped,
reclassified, moved to another line or given another scope or snippet. The only column that differs is `sqlform`, and
only where the form string held the origin's unicode ellipsis or dash.

## Table: slice, fingerprint site walk (columns: line, construct, kind, scope, snippet, referent set)

- file: exit.py; construct: `except` (UnicodeDecodeError, OSError); kind: external; origin: refs `{open}`; port: refs
  `{UnicodeDecodeError}`, `{OSError}`; status: declared D2 (2 sites)
- file: _pycodemod_sql.py; construct: `except OSError` (lines 83, 726); kind: external; origin: `{open}`; port:
  `{OSError}`; status: declared D2 (2 sites)
- file: _pycodemod_placement.py; construct: `except OSError` (lines 198, 254); kind: external; origin: `{open}`;
  port: `{OSError}`; status: declared D2 (2 sites)
- file: cli.py, split.py, _pycodemod_control.py; construct: all; kind: all; origin: 677; port: 677; status: same
- file: exit.py, _pycodemod_sql.py, _pycodemod_placement.py; construct: every other site; kind: all; origin: 693; port:
  693; status: same

## Table: probe file (38 sites), constructs the slice lacks

- construct: for-else, `else of for ... in X`; kind: row-iteration; origin: snippet with `…`; port: snippet with
  `...`; status: UNDECLARED U1 (control row and fp row)
- construct: case (2 sites), snippet `case …`; kind: mode-branch; origin: `…`; port: `...`; status: UNDECLARED U1
  (control rows and fp rows)
- construct: for-else, case, match; kind: mode-branch / row-iteration; origin: sqlform with em dash; port: ASCII;
  status: declared D1 (8 sites)
- construct: except OSError; kind: external; origin: refs `{open}`; port: `{OSError}`; status: declared D2 (1 site)
- construct: for over `con.executemany(...)`, yield from `QB.run(...)`; kind: row-iteration (origin) and unclassified
  (port, narrow vocab only); origin: row-iteration; port: unclassified; status: declared D3 (2 control, 2 fp)
- construct: while-else, try-else, finally, assert, filter, all, yield, yield from, async for, async with, quit, raise;
  kind: all; origin: 27 sites; port: 27 sites; status: same (or D1 dash)

## Table: census arithmetic (`Census`, run on the origin's own 1376 site tuples through both)

- quantity: per-site fingerprint, known keys, remainder, Omega (1376 rows); origin: computed; port: computed; status:
  same
- quantity: total Omega 1344, total bits 13810, explained sites 637, incidences, max fingerprint; status: same
- quantity: residual order (15), explaining keys (15), 10 gcd classes with members, 139 candidate divisors; status: same
- quantity: `modelled_keys` over `_pycodemod_sql.py`: 370 keys each side; status: same

## Table: static tables (imported from both and diffed)

- table: CONTROL_KINDS, CONSTRUCT_GROUPS (36 constructs), LOOP and EARLY_EXIT sets, ALWAYS_EXTERNAL; status: same
- table: external roots (30), names (8), attrs (19), exceptions (12), mode dotted and mode names; status: same
- table: SQL_FORM (24 keys) and SQL_FORM_EXIT_ROW (3 keys): keys identical; 5 values differ, all the dash or ellipsis
  (`for/row-iteration`, `and/row-branch`, `or/row-branch`, `yield/row-iteration`, exit `continue`); status: declared D1
- table: MODE_FORM; status: declared D1 (dash)

## Differences, named

DECLARED (read in the module docstrings and the ports' commit messages):

- D1 form strings ASCII-ised: commit 8462515 (W606), "the origin's unicode ellipsis and dash in the form strings became
  `...` and `-`". 306 slice sites, 8 probe sites, 6 table values.
- D2 an `except` naming a boundary exception is external by a `forced_external` flag, and `governing` keeps the real
  type node: commit c3ca6d2 (W638) and the `control_census.py` docstring ("the VERDICT is external on the TYPE, but
  `governing` still holds the handler's real type node"). The origin swapped in a fake `Name("open")`. ⚑ The consequence
  for the fingerprint is not named in `fp_sites.py`: refs change from `{open}` to `{OSError}`, which changes a prime's
  frequency count and so the prime assignment. The effect is declared at its source, not at its fingerprint reader.
  6 slice sites, 1 probe site.
- D3 StoreVocab and Boundary are required operands, no default (`storeflow.py` docstring, commit 7774791 W609). The
  requested narrow vocab lacks `executemany`, `run`, `rows`, `scalar`, `scalars` and the receivers `conn`, `c`,
  `connection`, `cursor`, `db`, `QB`, `_schema`; it gave a different answer from the origin only on the probe, where
  `executemany` and `QB.run` appear.
- D4 unreadable, undecodable and unparseable files return a `Skip` beside the sites instead of `[]`: not exercised, as
  every file in the slice parsed.
- D5 no desync `AssertionError` (the walk is a map over `Site.governing`): not exercised.
- D6 the origin's dead `isinstance(n, (ast.Raise, ast.Try))` branch in `external_expr` is dropped (commit ad85c24,
  W637): behaviour-neutral, the branch only `continue`d.
- D7 `modelled_keys` takes explicit paths, returns `Modelled` with `Skip`s, no default seed (`census_fp.py`
  docstring): not exercised for an unreadable seed.

UNDECLARED:

- U1 MEASURED. The snippet text of `for-else` (`else of \`for ... in X\``) and of `case` (`case ...`) uses ASCII `...`
  where the origin used `…`. The W606 commit names "form strings" only, and `control_census.py` does not mention the
  snippets. Probe: 3 control rows and 3 fp rows, all of two constructs; the slice has no `for-else` or `match`.
  Likely the same intent as D1, but undeclared; it also changes a fingerprint row's `snippet` column.
- U2 reading-only. `fingerprint.py` drops the origin's public `omega(n)` (origin line 262, a count of prime
  factors); only `omega_against` is ported, and the docstring does not say so. The origin's `Census` never calls it.
- U3 reading-only. `census_fp.Census` drops the origin's `known_primes`, `files` and `seed` attributes; its docstring
  names the explicit `modelled` argument, not the dropped attributes. Nothing else in the origin's walk reads them.
- U4 reading-only. `referents(None)` returns `set()` in the origin (`_ctl._as_list(None)` is `[]`) and raises
  `TypeError` in the port (`list(None)`); `fp_sites` passes the empty tuple, so no port path reaches it.
- U5 reading-only. The origin's `getattr(c.pattern, "lineno", None) or c.body[0].lineno` (case line),
  `getattr(gen.iter, "lineno", n.lineno)` / `getattr(cond, "lineno", ...)` (comprehension lines) and the `_u`
  unparse fallback are plain attribute reads in the port. Equal on any parsed tree (the probe's `case` and
  comprehension lines match); not declared.

## Totals

- control census sites compared: 1376 on the slice, 38 on the probe (1414)
  - same: 1070 slice, 27 probe
  - declared difference: 306 slice (D1), 8 + 2 probe (D1, D3)
  - UNDECLARED: 0 slice, 3 probe (U1)
- fingerprint site walk rows compared: 1376 slice, 38 probe
  - same: 1370 slice, 34 probe (wide vocab)
  - declared: 6 slice (D2), 1 probe (D2), 2 probe on the narrow vocab (D3)
  - UNDECLARED: 0 slice, 3 probe (U1)
- census arithmetic and static tables: every value same except D1 strings
- UNDECLARED differences: 6 in all (U1 measured, U2 to U5 reading-only); the one that changes output is U1
- DECLARED differences: 7 (D1 to D7), of which D1, D2 and D3 were measured and D4 to D7 are reading-only
- not covered: Skip behaviour (D4), the printers and the CLI (`_print_control`, `collect`, `local_closure`), which are
  not ported by these modules; and a corpus whose store vocabulary differs from substrate's
