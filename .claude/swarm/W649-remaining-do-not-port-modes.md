# W649: the four remaining DO-NOT-PORT driver modes, re-read at source

Sources: `/home/mikemol/github/substrate/scratch/pycodemod.py` (MODES table lines 969-1205, dispatch 2214-2250,
2630-2682, 2828-2891), `scratch/_pycodemod_query.py` (`sqlnames` 373-440, `collision_apex` 2348-2480),
`scratch/_pycodemod_core.py` (`py_files` 281-340, `DISCARD_LEDGER` 53) and `scratch/_pycodemod_selftest.py`
(`sqlnames` arms 431-466, `collision_apex` arms 1497-1530). Operator ruling 2026-10-04: "substrate-only" is not a
reason to decline; each mode is judged on its merit and its operands. The origin has NO selftest arm for `--last`.

| Mode | What it is | Recommendation |
| --- | --- | --- |
| `--sqlname` | joins `def q_NAME` to the string `"NAME"` that invokes it | PORT, as an operand-prefixed reader |
| `--last` | replays a persisted `--discards` census, says when stale | DECLINE ON MERIT |
| `--collision-apex` | collisions ranked by body skeleton, via substrate's jea | DECLINE ON MERIT, blocked on jea |
| `py-files` | the origin's corpus enumerator, not a mode | DECLINE ON MERIT, covered by pathwalk |

## --sqlname

What it does: `sqlnames(name, paths)` returns `(path, line, qname, kind)` rows, kind `def` for a `def q_NAME` and
`ref` for a string literal equal to the bare name passed as an argument (`QB.run(con, "obs_core")`). Either spelling
resolves. For whom: anyone deciding what to delete from a corpus where a function is invoked by a string. `--calls
q_x` reports 1 def, 0 calls, dead, on a query run every fold; the origin's `--dead` printed that false verdict for
every registered query (measured 2026-08-18) and `--calls` now points at `--sqlname` for a `q_` name.

Substrate-specific names and how each becomes an operand:

| Origin name | Where | Becomes |
| --- | --- | --- |
| `q_` prefix | `name[2:]`, `startswith("q_")` | required operand `prefix` (no default; empty refused) |
| `QB.run(con, "x")` call shape | implicit: any string argument | none; any string-literal argument is a ref |
| `_pycodemod_core.py_files()` | default population | required `paths` operand, as every mtools mode |
| `_WRAPPER_CACHE`, `MetadataWrapper` | parse cache | dropped; mtools parses with `ast` |
| `sqlnames.skipped` function attribute | skip accounting | a returned `Skip` list, never silent |
| `q_thing` accepted as the operand | either spelling | kept: strip `prefix` when present |

What already exists in mtools: `literals TEXT paths` (every string literal containing a text, with its role) finds
the ref side; `bindings NAME paths` finds the def side; `relname` matches an exact string as a relation. Nothing
joins them. `dead.py` `_excuse` excuses a def only when its own name is a string constant (`name in constants`), so
`def q_x` with `"x"` invoked is NOT excused: the false-dead verdict the origin closed is still open here, whenever a
repo registers by prefix. So the join is unserved, not merely unported.

Cut plan: `pycodemod/src/mikemol/pycodemod/registered.py` with `registered_refs(paths, name, prefix) -> Registered`
(rows of path, line, kind; `skipped`), frozen slotted dataclasses like `Size`. Reuse `strings._parse` for the parse
and its `Skip`. Count a ref only when the literal is a call argument (not a docstring, not a dict key), as the
origin's visitor does. CLI wiring (`registered NAME --prefix PREFIX paths`) is a second unit; extending `dead`
with a `--registered-prefix` excuse is a third, only after the reader lands.

Arms to transcribe (selftest 437-466), vocabulary passed in:

1. the `q_`-prefixed def is found as `def` at its line
2. the string reference `--calls` cannot see is found as `ref`
3. the defined spelling and the invoked spelling return identical rows
4. a string reference is `ref`, never `call`
5. a query defined and never referenced has only its `def` row
6. new: an unparseable file lands in `skipped`; an empty prefix is refused; a docstring mentioning the name is no ref

Recommendation: PORT. First waypoint title (under 150 chars): "pycodemod: registered.py, a prefixed def joined to
the string literal that invokes it, prefix supplied by the caller, skipped files reported".

## --last

What it does: reads `DISCARD_LEDGER` (a file beside the origin script), prints it, and compares the stamped
`predicate=` (sha1 of `inspect.getsource` of `verdict_returners` and `_bare_calls`) with the current one, ending in
`VERDICT: STALE` or `CURRENT`. `--discards` writes the ledger only on a full, unscoped sweep. For whom: a reader who
would otherwise re-run a multi-minute sweep or redirect it to a scratch file the tool does not know about.

Substrate-specific names and how each becomes an operand:

| Origin name | Where | Becomes |
| --- | --- | --- |
| `DISCARD_LEDGER` | path beside the script | required operand `--ledger PATH` |
| `verdict_returners`, `_bare_calls` | the hashed predicate | the stamp is a caller-named version string, not source |
| "full sweep only" (no `args`) | write gate | explicit `--record` flag; never implicit |
| `ROOT` relpath in ledger rows | row format | rows carry the path as given |

What already exists in mtools: `discards.py` returns `Discards` for a named callee and paths; nothing persists, and
the port persists nothing by design. A shell redirect to an operand path gives the same record, and a durable file
under the fence's no-hidden-writes rule must be an explicit operand. The staleness stamp is the only novel part, and
`inspect.getsource` hashing ties it to the interpreter-readable source of an installed package, which a wheel cannot
promise. The origin's `--discards` takes a callee operand in mtools, so a "full sweep" has no counterpart to key the
write on.

Recommendation: DECLINE ON MERIT. Reason: the ledger exists to avoid a re-run, and a bare mtools `discards` takes a
callee name and paths, so the multi-minute full sweep it replays has no mtools shape; a recorded run is a redirected
file with an explicit path. Evidence that would reverse it: a measured `discards` wall time over about a minute on
a real mtools corpus (record it with the telemetry skill), or a second census that wants the same stale-predicate
stamp, at which point a generic `--record LEDGER --stamp VERSION` belongs to the driver, not to `discards`.

## --collision-apex

What it does: for each name `collisions()` returns, takes the sites' sources (dedented), calls
`jea_extrude_ir.templatize` for hole counts and `jea_pyalg.head_spine` for a coarser key, then bands names as
universal, broad or pairwise by site count, with `IDENTICAL`, `deep-key-no-match` and `N hole(s)` verdicts. For whom:
someone ranking name collisions by how liftable they are: 14 sites collapsing to 2 skeletons is a lift, to 11 is a
convention.

Substrate-specific names and how each becomes an operand:

| Origin name | Where | Becomes |
| --- | --- | --- |
| `jea/metalanguage` on `sys.path` | `jea_extrude_ir`, `jea_pyalg` imports | NOT an operand: a missing dependency |
| `templatize`, `full_skeleton` | hole count and deep key | needs a body-skeleton function mtools lacks |
| `Intern`, `PyDivStr`, `lower_source`, `head_spine` | spine rung | same; depends on the jea trace algebra |
| `synth_apex` bands, `max(3, n // 2)` | breadth bands | named constants, kept |
| `source_of`, `collisions` | inputs | already `source-of` and `collisions` |
| `_pycodemod_core.ROOT` | label relpath | operand `relative_to` |

What already exists in mtools: `collisions`, `source-of`, `rivals` (delegates or reimplements) and
`rivals.collision_kinds`-style location grading cover the name side and the location partition. Nothing in
`pycodemod/src/mikemol/pycodemod/*.py` computes a body skeleton or hole count, and no `jea` exists in mtools. The
mode is a thin wrapper (about 100 lines) over a discriminator that does not live in pycodemod, so porting the
driver alone ships a mode that raises on import.

Recommendation: DECLINE ON MERIT as a pycodemod mode today. Reason: its content is the jea skeleton discriminator;
the wrapper has nothing to wrap in mtools. Evidence that would reverse it: the jea templatize and head-spine
pieces landing in mtools (the wholesale drain reaches `jea/metalanguage`), or a cleanroom body-skeleton function
(identifiers and constants abstracted, hole count over a cluster) in some mtools distribution. Then it is one unit:
`apex.py` taking the skeleton function as a parameter, with the three origin arms (identical methods share a deep
skeleton after dedent; a single-def name yields no row; rows carry both rungs) plus a `templatize`-failure row with
`holes=None`.

## py-files

Where it appears: summit's letter (`inbox/archive/2026-10-04-summit-pycodemod-moved-and-pins-at-03749d5.md`) lists
it as DO-NOT-PORT. It is not a flag in the origin MODES table: it is `_pycodemod_core.py_files(*roots)`, the
enumerator every origin mode calls (62 call sites), defaulting to the discovered corpus when no root is given.

Substrate-specific names and how each becomes an operand:

| Origin name | Where | Becomes |
| --- | --- | --- |
| `_roots()` | default corpus when no operand | none: mtools requires `paths` (nargs `+`) on purpose |
| `ROOT` | relative resolution of a root | the caller's working directory |
| `_GENERATED_DIRS`, `bazel-*` | generated trees skipped | not an operand yet; see the gap below |
| `.venv`, `site-packages` substring skip | vendored code | `pathwalk.expand` prunes by `pyvenv.cfg` instead |
| `PopulationError` | unresolvable root | a missing operand is refused by the walker |

What already exists: `mikemol.pathwalk.walk.expand` (used by `cli.main` for every directory operand) skips
registered worktrees and virtualenvs, refuses symlinks, prunes `.git`, and prints each skip count, which is stricter
than the origin. Gap, stated as residue: pathwalk prunes no generated trees (`bazel-bin`, `bazel-*`, `dist`,
`build`, `.tox`, `.mypy_cache`), where the origin did, after a mutant-copy census inflated results (origin comment at
`_pycodemod_core.py` 311-326). That is a pathwalk operand (`--exclude NAME`), not a pycodemod mode.

Recommendation: DECLINE ON MERIT. Reason: it is an enumerator already replaced, and a no-operand default corpus is
per-repo configuration the caller should name. Evidence that would reverse it: a measured census inflated by
generated trees in an mtools or summit corpus; that evidence points at a pathwalk `--exclude` waypoint, which is
the one follow-up worth minting from this item.

## Which of the 13 uncovered cases the origin has

Method: the origin MODES table has 63 flags. cli `MODES` wires 34 of them under their mtools names (commentary,
blocks, calls, guarded, placement, ambient, swallows, exits, binding, attr, literal, forwards, asserted, values,
reaches, importers, aliases, collisions, rivals, discards, reifies, resorts, funcnames, size, layout, dead,
crossings, escapes, state, source, key, shape, relname, and fix-owes-callers as `owes`, retired under a new name).
`DO_NOT_PORT` names 15 more (types, artifacts, touches, projects, discriminates, control, fingerprint, portable,
rawreads, relalg, snapshots, sql, collision-apex, sqlname, last), which this ruling re-reads; `split` is ported
(`split.py`, commit e0549f7). The remainder, with no CLI mode and no recorded decision, is 13:

| Flag | What it is | Likely class |
| --- | --- | --- |
| `--declare-modes` | emits `Mode(...)` roster skeletons | driver self-description |
| `--check-contracts` | dispatch against the MODES roster | driver self-description |
| `--banner` | renders the mode roster | driver self-description |
| `--selftest` | runs the origin's arms | origin-only; mtools has pytest |
| `--unbound-snapshot` | snapshot guard with no bound operand | needs a read at source |
| `--roundtrip` | does parse then emit reproduce the file | generic, small |
| `--imports` | every import in the corpus | overlaps `aliases` and `importers` |
| `--available` | which modules import here | environment probe |
| `--diagnose` | why one file failed to parse | generic, small |
| `--kinds` | the kind roster including zeroes | modifier of a census |
| `--lines` | line-granular commentary rows | overlaps `commentary-kinds` |
| `--package` | where an installed module's source lives | generic, small |
| `--sites` | per-site detail for a census | a modifier, not a mode |

The 13 is a count by name, and it matches summit's figure. Caveats: the classes are from the MODES `why` strings,
not from a read of each dispatch branch; `--imports` may already be served by `imports.py` and `aliases`. Several
`DO_NOT_PORT` names (control, fingerprint, sql, portable, relalg, snapshots, artifacts, touches as `reads.py`) have
ported libraries (`control_census.py`, `fingerprint.py`, `sql.py`, `portable.py`, `relalg.py`, `snapshots.py`,
`artifacts.py`, `reads.py`) while `cli.py` `_DO_NOT_PORT_NAMES` still refuses their spellings: a wiring gap to
reconcile, not a decision.

Answer for summit's question 2: its three named items are `sqlname` (PORT, above), `portable` (ported as
`portable.py`, not wired to a CLI mode) and `py-files` (not a mode; `mikemol-pycodemod MODE DIR` already expands
directories). Whether summit uses any of the 13 is a fact in summit's own scripts, which this note cannot read.
