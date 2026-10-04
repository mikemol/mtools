# W606: port plan for substrate's `_pycodemod_control.py`

Verdict: PORT, generalized. The 2026-09-26 decline stands only against the module as written. The census is
general; one operand (what counts as a row read) is substrate-specific and becomes an explicit argument.

## 1. What it measures, and for whom it is general

`control_sites(path)` walks every scope (module, def, class) and emits one row per control-flow site:
`(line, construct, kind, sqlform, scope, snippet)`. The roster is 8 groups and 41 constructs (branch, loop, guard,
exit, handler, short-circuit, fold, suspend). Each site gets one of six kinds:

| Kind | Meaning | Decided by |
| --- | --- | --- |
| external | file, process, clock, terminal boundary | name, attribute and root tables; one-hop taint |
| row-iteration | loop over a set read from a data source | row provenance of the iterable |
| row-branch | branch on the content of such a row | row provenance of the test |
| early-exit | `break`, `continue`, return inside a loop | construct and loop stack |
| mode-branch | branch on parameter, ALL-CAPS constant, argv, environ | parameter and constant names |
| unclassified | could not be determined, reported as such | fallthrough |

The `sqlform` column is a table keyed on (construct, kind), never on the site text, and says `unknown` when no
relational form is named. The headline is a ratio: irreducible external share versus work that could move out.

General for any repo that is migrating imperative Python into a declarative engine (SQL, Datalog, Rego, a rules
engine). Everything except row provenance is generic: the construct walker, the external/mode classifier, the
one-hop taint fixpoint, and the scope-local walk. Value for other consumers: the census sees the early-exit class
that a relational-algebra lint structurally cannot, and it reports the unknowns as findings.

## 2. Dependencies that become operands

The module imports four names from `_pycodemod_sql` plus `_pycodemod_core`:

| Import | Role | Fate in the port |
| --- | --- | --- |
| `store_reader_fns(tree)` | names of defs that read the store | operand-driven, see below |
| `has_read(node, rfns)` | expression contains a read, one hop | pure on `is_row_read` |
| `row_names(nodes, rfns)` | names bound from a read | pure on `is_row_read` |
| `derived_names(nodes, rows)` | names one hop from row names | already generic, copy as is |
| `touches(node, names)` | expression mentions a name | already generic, copy as is |
| `_pycodemod_core.py_files`, `ROOT` | corpus walk, relpath root | explicit `paths` and `root` operands |

The only substrate-specific datum is `is_store_read`: attribute in `STORE_READERS` (execute, fetchall, run, rows,
scalar, and so on) on a receiver in `STORE_CONNS` (con, cur, QB, `_schema`), or on any Call or Attribute receiver.
The port takes a `RowSource` operand: a frozen dataclass of `reader_attrs`, `receiver_names` and
`chained_receivers: bool`. The substrate values become the documented default preset, not a module global, and
`mikemol-pycodemod --control --reader-attrs ... --receivers ...` supplies others. With an empty `RowSource` the
census still runs and every site is external, early-exit, mode-branch or unclassified, which is a valid and
honest degenerate case (no row kinds claimed).

Other hidden globals to make explicit: `EXTERNAL_ROOTS`, `EXTERNAL_NAMES`, `EXTERNAL_ATTRS`, `EXTERNAL_EXC` and
`MODE_DOTTED` become fields of a `Boundary` operand with the current values as the default. A duplicated
`import _pycodemod_core` and `sys.path.insert` in the source are dropped, not ported.

## 3. Cut plan

Conventions to meet: no `ROOT` global (relpath base is an operand), skipped files are reported through
`core.Skip` (the source silently returns `[]` on OSError, SyntaxError, ValueError), operands explicit, and one
module per question, as `swallows.py` does. Parser note: sibling `swallows.py` uses stdlib `ast`; libcst is
required for rewriting, and a census does not rewrite, so `ast` stays unless a sibling convention check says
otherwise (verify with `core.py` before commit 1).

One commit per module, in this order. Each commit lands its own tests and passes the gate before the next.

1. `control_roster.py`: `CONSTRUCT_GROUPS`, `CONSTRUCTS`, `CONTROL_KINDS`, the loop and early-exit sets, the
   `SQL_FORM` table with `sql_form()`, and the `Boundary` dataclass. Pure data, no AST. Tests: roster has 8
   groups, 41 constructs, no duplicates; every `SQL_FORM` key names a roster construct; an unclassified kind never
   returns a form other than `unknown`.
2. `control_provenance.py`: `RowSource`, `is_row_read`, `row_reader_fns`, `has_read`, `row_names`, `derived_names`,
   `touches`, `ext_names` (fixpoint, 5 rounds), `external_expr`, `mode_expr`, scope helpers `scopes`,
   `own_walk`, `module_consts`, `params`. Tests: one-hop helper read, derived accumulator, `p = subprocess.run`
   then `p.returncode` is external, module scope does not inherit function-local rows.
3. `control.py`: the `_Census` class and `control_sites(path, source, boundary) -> list[Site] | Skip`. Site becomes
   a frozen dataclass, not a 6-tuple. Tail-return exclusion and the `else` line caveat travel with the code.
4. `control_report.py` and the CLI hook in `cli.py`: corpus census returning `(files, per_file, skipped)`, the
   ratio headline, by-file-by-kind table, early-exit repeat block, `--constructs` roster with zero rows, and the
   skipped list. No `os.path.relpath(..., ROOT)`: take `root`.

Selftest arms to transcribe (all from `_pycodemod_selftest.py`, lines 2366-2549), as a pytest module per commit:

- The planted-construct fixture (`rows_loop`, `guards`, `shell`, `gen`, `pure`), kept verbatim as a test constant.
- Completeness in both directions: roster minus found is empty, found minus roster is empty, 8 groups.
- The kind arms: row loop, row-branch versus mode-branch in one function, comp-if over rows, `with open` external,
  `except OSError` external on the type, one-hop subprocess external, `sys.exit` external, yield row-iteration,
  comprehension over a plain argument unclassified.
- Early exits: exactly break, continue, return-in-loop; break maps to `LIMIT 1 / EXISTS`.
- Mutation arm: delete the break and its guard, count drops by exactly 2.
- The unknown column arm and the kinds-in-roster arm.
- Dropped: the `relalg_sites` blindness arm (needs `--relalg`, not ported) and the receiver-qualified `scan` arms
  after line 2551, which test a different mode. Replace the dropped arm with a differential: run the ported
  census and the substrate original over the same fixture and corpus slice and assert identical site tuples
  (the W36 differential note applies; the original is the reference arm).

Add two new arms the source lacks: a skipped file (syntax error) appears in the skipped list and not as an empty
result; and an empty `RowSource` yields zero row-kinds.

## 4. Risks

- Row provenance is name-based and one hop deep, so unrelated code with `execute`/`run` receivers false-positives.
  Mitigation: operand default is empty for the generic CLI; substrate preset is opt-in. State the limit.
- The 41-construct count and `unknown` ratio are corpus-sensitive; a headline ratio ported without its roster is
  the misreading the source docstring warns about. Keep `--constructs` in commit 4.
- The source's docstring is substrate history (ladder logic, `_unreflected_floor`); do not port it as prose.
  Rewrite to describe the operand, and put history in evidence.
- Python 3.12+ grammar drift: `TryStar` handled by name; `match` needs 3.10. Check the project floor.
- Differential needs the substrate checkout present; make the arm skip with a reported reason when absent.
- Four modules from a 695-line source may leave `control.py` near the size bar; measure before commit 3.

## 5. Recommendation

PORT. First waypoint title (one landable unit, under 150 chars):

`pycodemod: control_roster.py, the control-flow construct roster, SQL_FORM table and Boundary operand, tested`

Follow-ups: provenance module, census class, report plus CLI, each its own waypoint, in that order.
