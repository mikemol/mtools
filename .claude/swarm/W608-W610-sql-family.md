# W608 / W609 / W610: the SQL-inside-Python family of pycodemod

Source: `/home/mikemol/github/substrate/scratch/_pycodemod_sql.py` (1,661 lines) and its arms in
`/home/mikemol/github/substrate/scratch/_pycodemod_selftest.py`. Target package:
`/home/mikemol/github/mtools/pycodemod/src/mikemol/pycodemod/`. Drafted 2026-10-04, read only.

## Verdicts

| Waypoint | Group | Verdict | First landable unit |
| --- | --- | --- | --- |
| W610 | `sql_sites` style grading | PORT | see below |
| W609 | store-read vocabulary and its four consumers | PORT | see below |
| W608 | `portable_sites` and `_pg_*` probes | PORT, behind a protocol | see below |

The 2026-09-26 decline reasons were each a naming problem, not a measuring problem. Every substrate name is
a roster or a path, and each becomes a caller-supplied operand. No group is declined on merit.

First-waypoint titles (150 characters or fewer):

- W610: `pycodemod sql.py: sql_sites reads SQL literals and grades raw vs literal by a caller-supplied executor roster`
- W609: `pycodemod storeflow.py: StoreVocab operand plus is_store_read, store_reader_fns, row_names, derived_names`
- W608: `pycodemod portable.py: portable_sites judges SQL literals via an injected Probe protocol, no database in tests`

## What each group measures

### W610: sql_sites (and its style grade)

Population: every `ast.Constant` string that a SQL engine accepts as a statement. Recognition is two-stage:
first token in a DML/DDL head roster, then `EXPLAIN` on an in-memory sqlite, then (only when sqlite refuses)
a second oracle. Placeholders (`%s`, `%(x)s`, `:name`) are rewritten to `NULL` before the probe.
"no such table/column" counts as parsed.

The style grade is `raw` when the literal sits among the descendants of a call argument whose callee name is in
`execute, executemany, executescript, execute_many, rows, scalar`, else `literal`. Descendants, not the
argument itself, so `"..." % ph()` and `.format` spellings count.

Finding to carry over, stated as residue: the `builder` branch (`elif nm == "run"`) writes `style_of[id(node)]`
keyed on the Call node, but lookups are keyed on Constant nodes, so `builder` can never be emitted. The arm
"a builder call is not counted as a raw SQL literal" passes vacuously. The three-layer split
(`query_defs` / `query_sql` / `query_builders`) is therefore never read by name; only the executor roster is
substrate-shaped. Port it as a real `builder` grade over a caller-supplied builder-callee set, or drop the
word. Do not carry a dead branch.

Known lower-bound defect noted in the source header: a SQL literal that is the left operand of `%` is handled
here (the placeholder normaliser), but the header still calls the census a lower bound. Port the header
claim only if the arm for it still reproduces.

### W609: rawread_sites, snapshot_sites, relalg_sites, store vocabulary

- `rawread_sites`: `for ... in con.execute(...)`, comprehensions over it, and `list/sorted/set/dict/tuple`
  around it. It measures a call-site fact: row shape at the consumer (a dict row iterates as keys under
  psycopg `dict_row`). Valid SQL does not help `--portable` here.
- `snapshot_sites`: one value composed of several store round trips. Kinds `composed` and `iterated` form the
  headline, `sequential` is a signal only. `_read_trips` collapses chained `execute(..).fetchall()` to one trip
  and MAXes an `IfExp`.
- `relalg_sites`: per function that also reads the store, six kinds of relational algebra done in Python on
  rows: join, group-by, filter, sort, set-op, distinct. It leans on `store_reader_fns` for the one-hop helper
  case.
- Shared predicates `is_store_read`, `is_store_read2`, `store_reader_fns`, `row_names`, `derived_names`,
  `has_read`, `touches`. `_pycodemod_control.py` already imports five of them, so these are a shared seam,
  not four private helpers.

### W608: portable_sites and the probes

`portable_sites(path)` lists SQL literals that a real postgres rejects, with a remedy. The verdict comes from
`EXPLAIN` (DML) or from executing the statement in a throwaway tenant (DDL, `PRAGMA`, `VACUUM`, `ATTACH`).
`UndefinedTable`, `DuplicateTable` and `DuplicateObject` count as success. Generated files (a `# GENERATED`
marker in the first 400 bytes) are skipped. A file's `func.<name>` SQLAlchemy Core calls are recorded as
"not judged", set before any early return. With no database it degrades to the `_PORT_REMEDY` regex list and
says `pattern`.

## Substrate-specific names and how each becomes an operand

W609:

- `STORE_READERS` tuple (`execute`, `run`, `rows`, `fetchall`, ...) becomes `StoreVocab.readers: frozenset[str]`.
- `STORE_CONNS` tuple (`con`, `conn`, `c`, `cur`, `db`, `QB`, `_schema`) becomes `StoreVocab.receivers`.
- The `("con","conn","c","connection")` literal in `rawread_sites` becomes `StoreVocab.connections`.
- `("list","sorted","set","dict","tuple")` stays a module constant (Python builtins, not substrate).
- `RELALG_KINDS` stays a constant (the six operator names are the measure).

W610:

- Executor roster `execute ... scalar` and `run` become `SqlConfig.executors` and `SqlConfig.builders`.
- `HEADS` DML/DDL roster stays a constant (SQL, not substrate).
- `_pg_probe_con()` as second oracle inside `_parses` becomes `SqlConfig.oracles`, a tuple of
  `Callable[[str], bool]`, default empty.

W608:

- `sys.path.insert(_c.ROOT/jea/metalanguage)`, `import store`, `store.sandbox_connect()`: a `Probe` factory
  passed by the caller. The import never ports.
- `_PG_CON`, `_PG_TRIED`, `_PG_SANDBOX`, `_PG_SANDBOX_TRIED`, `_PG_SANDBOX_ERR` become fields of a
  `ProbeSession` object. No module globals.
- `psycopg.errors.UndefinedTable/DuplicateTable/DuplicateObject` become SQLSTATE strings `42P01`, `42P07`,
  `42710` read off the exception.
- `_PORT_REMEDY` text (`_schema.upsert()`, `_schema.ph()`, `_schema.relations()`, `_schema.dedup()`) becomes
  `PortConfig.remedies`, a sequence of (regex, text). The sqlite-ism regexes stay default; the remedy strings
  are caller text.
- The `# GENERATED` marker regex becomes `PortConfig.generated_marker`, default the same regex (generic).
- Function attribute `portable_sites.core_built` becomes a returned `PortableReport(blockers, core_built)`;
  the stale-carry-over defect disappears by construction.

All three:

- `_c.ROOT` read through the module object: reuse the `core` corpus-root convention already ported, and never
  `from ... import ROOT`.

Rule for all of them: a module constant may name SQL or Python grammar. Anything that names a store, a tenant, a
helper module or a connection variable is an operand with no default.

## W608: testing a live-postgres probe without a database

The probe uses four calls: `con.transaction()` (context manager), `con.cursor().execute(text)`,
`sb.cursor().execute(text)` for DDL, and exceptions classified by type. Define in the module:

- `Probe` protocol: `explain(text) -> Verdict`, `execute_ddl(text) -> Verdict`, `reason: str` (empty if
  connected).
- `Verdict` = `ok | parsed_absent | error(kind, message)`, where `parsed_absent` is the three SQLSTATE cases.
- A thin real adapter `PsycopgProbe(con)` implements the protocol over a caller-supplied connection. It is the
  only code that touches `transaction()` and `cursor()`, and it classifies by `getattr(e, "sqlstate", None)`
  so no `import psycopg` is needed in the core.

Tests:

- `FakeProbe` with a recorded table `{statement: Verdict}`. Record the answers from the six measured shapes in
  the source docstring: `?` gives syntax error, `INSERT OR IGNORE` syntax error, `PRAGMA` syntax error,
  `GROUP_CONCAT` UndefinedFunction, `rowid` UndefinedColumn, `LIKELIHOOD` UndefinedFunction, plus
  `UndefinedTable` which must be excluded.
- `FakeConnection` (a 20-line class with `transaction()`, `cursor()`, scripted exceptions carrying `.sqlstate`)
  tests `PsycopgProbe` itself: that each EXPLAIN runs in its own transaction block so one error does not poison
  later sites, and that DDL goes to the sandbox handle, never the EXPLAIN handle.
- A degraded-mode arm: `Probe` is None -> pattern verdicts tagged `pattern`; DDL without sandbox -> tagged
  `pattern/ddl`. This is asserted unconditionally, replacing the source's skip-if-unreachable.
- The "positive control" principle (a zero needs a control) survives as `Probe.reason`: an unreachable probe
  carries its cause, and the report prints it. Keep that.

What must stay out:

- `store.sandbox_connect`, the `jea/metalanguage` path insert, and any tenant selection. They are substrate's
  store layer; the mtools caller supplies a factory or none.
- Any live-database arm in the gated suite. If one is wanted, it is a separate opt-in test outside the bazel
  gate, marked skip-with-reason, and it needs its own waypoint.
- The DDL-execution capability by default. Executing caller statements is a hazard (a probe once created a table
  in the live store). `PsycopgProbe.execute_ddl` must require an explicit `sandbox=True` construction argument,
  and the CLI mode must not offer a flag that connects to anything but a caller-named sandbox DSN.
- The `# noqa: BLE001` on `_core_func_sites`: any `# noqa` comment is forbidden here. Narrow the `except` to
  `(OSError, SyntaxError, UnicodeDecodeError)`.

## Cut plan: one commit per module

Dependency order: W610, then W609 (independent of W610, can land in parallel), then W608.
W594 (the pure SQL-string relation reader: `sql_rel_roles`, `sql_relnames`, `sql_kind`, `sql_rw`) has no
dependency on any of these. Its one consumer here, `relname_sites`, imports `sql_sites` from W610 (and
`literal_sites`), so `relname_sites` lands after both W594 and W610 and is not part of this plan.

1. W610, commit 1: `sql.py` with `SqlConfig`, `sql_sites`, `_PLACEHOLDER`, the sqlite oracle and memo. One
   connection per call, closed on exit (the source leaks one per call). Arms transcribed:
   - source 1874: prose label starting with a keyword is not a site
   - 1883: real statement is a site and carries its style
   - 1890: a builder call is not counted as raw (rewrite so it is no longer vacuous)
   - 1906: `%s`-parameterised statement is a site and RAW
   - 1945: postgres-only statement is a site, rewritten to inject a fake `oracles` entry that accepts
     `DELETE FROM evq e`, so it runs unconditionally with no database
   Add one arm for the executor roster being an operand (empty roster -> everything is `literal`).
2. W610, commit 2: `cli` mode `--sql` and `_print_sql` output, with the `n of m` denominator line.
3. W609, commit 1: `storeflow.py` with `StoreVocab`, `is_store_read`, `is_store_read2`, `store_reader_fns`,
   `touches`, `has_read`, `row_names`, `derived_names`. No default vocabulary. Arms: none exist at source for
   these directly, so write arms through the consumers (below).
4. W609, commit 2: `relalg.py` (`relalg_sites`, `RELALG_KINDS`). Arms 2144-2171: JOIN, filter, sort, group-by,
   distinct, set-op between two store-reading helpers, and the pure-helper negative. Source 2528 (the `break`
   kind) belongs to the control mode, not this module; skip.
5. W609, commit 3: `snapshots.py` (`snapshot_sites`, `_read_trips`, `_iterated_read`). Arms 2344-2360: composed,
   chained fetch is one trip, `IfExp` is one trip, comprehension is iterated, loop is fine. Read the rest of
   that block (around 2360-2370) when transcribing.
6. W609, commit 4: `rawreads.py` (`rawread_sites`). Source has no arm for it (only an import); write four
   arms: unpacked loop, iterated loop, comprehension, `list(con.execute(..))`, plus a bare `con.execute("DELETE")`
   negative. This is the one place the port adds arms the source lacked, and the card should say so.
7. W609, commit 5: CLI modes `--rawreads`, `--snapshots`, `--relalg` and the vocabulary option (see below).
8. W608, commit 1: `portable.py` with `Probe`, `Verdict`, `PortConfig`, `ProbeSession`, `PsycopgProbe` (adapter
   only), `portable_sites` returning `PortableReport`, `_core_func_sites`. Arms 3001-3017 become
   "Core-only file has no literal blockers, core_built recorded" and "plain file has empty core_built", now
   against the returned report, which makes the second one structural.
9. W608, commit 2: the fake-probe and fake-connection arms listed above, as their own test module.
10. W608, commit 3: CLI `--portable` and `_print_portable`: grouping by remedy then blocker, the DEGRADED
    banner naming `Probe.reason`, and the NOT JUDGED Core block.

Vocabulary delivery on the CLI (W609, W610, W608 all share it): a TOML or JSON file named by `--store-vocab`,
read through the existing config loader. No flag means the mode refuses with a one-line message naming the
option, rather than guessing the substrate names. A `--rawreads` run with no vocabulary is an error, not a
zero. This is what keeps the "zero needs a positive control" rule intact.

## Per-group recommendation and reason

- W610 PORT. Everything substrate-keyed is a verb roster plus an optional second oracle. The measured defect
  history (prose admitted as SQL, `%` as modulo, `EXPLAIN` over `complete_statement`) is exactly what the arms
  pin, and none of it depends on tenants.
- W609 PORT. The four modes and `_pycodemod_control.py` need one shared predicate, and the source argues
  against copying it. The vocabulary is just names; an AST census over caller-named receivers is neutral. The
  honest cost is a missing default, so the first run on a new repo needs a vocabulary file.
- W608 PORT, gated. The probe is portable once the connection is a protocol; the engine verdict is the
  point of the mode, and a fake with recorded verdicts tests every branch the source tested live. Land it last
  and keep real-database use opt-in and sandbox-only. If the operator judges the sandbox DDL path too risky, the
  only cut allowed is dropping `execute_ddl` (DDL then reports `pattern/ddl`), never defaulting it on.
