# W36 — the pycodemod differential

## W105 (locate) — 2026-09-27

**The 407/408 is not a count over a tree. It is the origin's SELFTEST score.**

Source, verbatim (`inbox/2026-09-25-substrate-pycodemod-port-letter.md:72`, §4 "Suites and
scores"):

> `scratch/pycodemod.py --selftest` | **407/408, exit 1** | FAIL `a live hand-rolled memo
> classifies as a cache` (got None, want 'cache'); plus one SKIP (postgres-dialect case, sandbox
> store unreachable, reported UNMEASURED, not passed). The origin is not green today, so the
> differential baseline starts at 407 and the failing case is either a defect to carry or a case
> to fix …

Corroborated in `.claude/queue.md:293` (DIFFERENTIAL BASELINE 407/408) and `.claude/queue.md:712`
("NOT A MODE: --selftest; its 408 cases ARE the differential baseline").

- **Command:** `cd ../substrate && .venv/bin/python scratch/pycodemod.py --selftest`
- **Tree:** none. The 408 cases are embedded fixtures inside the origin's own driver and modules.
- **Baseline:** 407 pass, 1 fail (memo-as-cache), 1 skip (postgres dialect, UNMEASURED).
  408 + 1 skip, or 407 + 1 fail = 408 with the skip outside the count — the letter does not
  say which; W106 must re-run it and read the origin's own tally line.

## Consequence for W106 — the title was wrong

W106 as minted said "run both tools over the W36.1 tree, per shared mode". There is no tree.
The differential is **case correspondence**: each of the origin's 408 selftest cases is either

1. **ported** — a named pytest case in `pycodemod/tests/` pins the same claim (possibly
   inverted, where the port fixed a measured origin defect);
2. **DO-NOT-PORT** — its mode is on the DO-NOT-PORT or DEFERRED list (queue.md:708-716), so the
   case stays in substrate;
3. **dropped** — neither, which is a gap to close or a decision to record.

The count sent to substrate and summit (W107) is `ported / (408 − DO-NOT-PORT)`, with the
dropped list, and the memo-as-cache case's fate named explicitly.

## Residue

- Rejected reading: "run both over substrate's tree and diff the rows." It rhymes with a
  differential but measures a different thing (agreement on one corpus, where the port
  deliberately diverges on every measured origin defect), and no figure in any letter is on
  that axis. Not dropped entirely: a row diff on one real tree is a useful *second* witness
  once the case map exists, but it is not what 407/408 names.

## W106 (enumerate) — in progress 2026-09-27

- The re-run reproduces the letter exactly: `pycodemod selftest: 407/408`, exit 1. The one FAIL
  is `a live hand-rolled memo classifies as a cache` (got None want 'cache'). The postgres case is
  SKIPped outside the 408 (UNMEASURED: 127.0.0.1:5432 refused).
- The cases are `check(n, got, want)` calls into a closure at
  `substrate/scratch/_pycodemod_selftest.py:96`.
- STATIC count, measured with our own port (`mikemol-pycodemod values check 0
  _pycodemod_selftest.py`): **378 call sites, 1 with a computed name (line 160)**.
- 378 ≠ 408, so about 30 cases come from checks inside loops. A static read cannot give the
  population; only a traced run can.
- Tracer: scratchpad `w106_trace.py` (sys.setprofile on each `check` return), writing
  `w106_cases.tsv`. The profiler makes the run slow: it was still running after 600 s.

- **LANDED 2026-09-27 (traced run, exit 0 under the tracer, tally line 407/408 unchanged).**
  `.claude/design/W36-origin-cases.tsv` holds one row per case: index, PASS/FAIL, caller line,
  name. The tracer is at `.claude/design/W36-trace.py`.
  - **408 rows, 1 FAIL:** row 225, caller line 1844, `a live hand-rolled memo classifies as a
    cache`. This matches the origin's own tally.
  - **408 distinct names:** no name repeats. The loop cases compute distinct names, so a case
    name IS a usable key (requirement 3 holds without renaming).
  - **399 distinct caller lines at runtime, against 378 static `check(` sites** in
    `_pycodemod_selftest.py`. Nine lines run more than once (the loops), so at least 21 caller
    lines are ones the one-file static read did not count: either `check` reached under another
    spelling, or a caller outside that file. This is UNEXPLAINED, and W108 must resolve it before
    it trusts the static file as the fixture source.
- **Not captured:** fixtures and query operands. The tracer sees (n, got, want) only (open
  question (c)).

## W108 step 1 — the 399-vs-378 gap, EXPLAINED (2026-09-27)

This was measured with the scratchpad script `w108_gap.py`: runtime caller lines, against static
`check(` sites, against the file's own `ast` calls to the bare name `check`.

- figure: static sites (`mikemol-pycodemod values check 0`); value: 378; why: includes 4 `seen_a.check(...)` /
  `seen_c.check(...)` at `_pycodemod_selftest.py:856-865`: a DIFFERENT function (`KwIndex.check`), matched because a
  bare query matches a method name
- figure: `ast` bare-name `check(...)` calls; value: 374; why: 378 − those 4
- figure: runtime caller lines; value: 399; why: see below
- figure: runtime lines not a static start line; value: 27; why: 5 are continuation lines of multi-line `check(` calls
  (CPython reports the call's later line); **22 are in ANOTHER FILE**

**The 22 are `_pycodemod_fingerprint.py` cases.** `_pycodemod_selftest.py:2775` calls
`_fp_cases(check)`, handing the closure to `_pycodemod_fingerprint._cases`, which has **36**
`check(` sites of its own (lines 713-897). The tracer recorded only the caller's LINE, not its
FILE, so the fingerprint lines that happen to coincide with selftest lines were silently merged.
Only 22 of the 36 showed up as "extra". ⚑ This is requirement 3 (case identity) biting the
instrument itself: a line number is not a case key. The tracer must record `(caller file, line)`.

**Static sites that never ran:**

- `:160` — `for _msg in _pycodemod_placement._cases(): check(f"placement: {_msg}", False, True)`.
  ⚑⚑ **`_cases()` yields only FAILURE messages**, so every PASSING placement case is outside the
  408. The origin's denominator OMITS placement's population entirely; only its failures would
  ever be counted. Whatever `_pycodemod_placement` checks internally is a hidden population. That
  population must be enumerated separately, or it goes unaccounted for in the differential.
- `:856, :858, :860, :865` — the `KwIndex.check` method calls above; they are not cases.
- `:1945` — the postgres case, SKIPped (UNMEASURED).

**What this means for the 408:**

- **fingerprint's 36 cases are DO-NOT-PORT.** Fingerprint is on the DO-NOT-PORT list
  (queue.md:708-716; its algebra is gabion's). So they are `do-not-port` spec records, pending
  confirmation that all 36 ran; the TSV must be re-cut by caller file to confirm that.
- **The placement population is missing from the denominator.** This is not a port question; it
  is a defect in the ORIGIN'S count, to be reported to substrate in W107.
- The static count is only usable per file, and only after the `KwIndex.check` false sites are
  removed.

**Open, not a defect claim:** the port's `values check` matched `seen_a.check(...)` for a bare
`check`. The port's help says "a bare or dotted callee name". Whether a bare name should match
attribute calls is a design question for pycodemod's `values`/`sites` (the origin does the same;
not checked here).

## Operator direction (2026-09-27): pytest FROM compliance specs run against a REFERENCE

Inferred from the cross-repo OPA/Rego survey, where the same shape already exists three times:

- OPA/Rego (el-openglo, luthen, cassian): policy = pure function, input → verdict sets (deny / withheld / admitted; exit
  0/1/3); this differential: query = pure function, fixture source → rows
- OPA/Rego (el-openglo, luthen, cassian): `_test.rego` pins the policy on hand-written inputs; this differential: the
  origin's 408 `check` cases pin the origin on inline fixtures
- OPA/Rego (el-openglo, luthen, cassian): the gate runs the policy on a MEASURED input (tofu plan JSON, check_*.py
  --json); this differential: the port runs on the same fixture
- OPA/Rego (el-openglo, luthen, cassian): luthen binds the verdict to the input's sha256; this differential: a case's
  verdict is bound to its fixture text

**The defects found there become requirements here.**

1. el-openglo's `opa test` never exercises the real measurement: it is unit-only
   (`opa_gate.py:136-141`). → The spec must drive BOTH implementations through the same input, not
   pin each one alone.
2. When the tool is missing, el-openglo exits 0, cassian's gate stays green, and luthen WITHHOLDS.
   → **A missing reference is UNMEASURED, never PASS.** UNMEASURED fails the gate unless it is
   declared; the origin's own postgres SKIP is the right shape (counted outside, and named).
3. cassian's `package main` silently unions rules that share a name. → **Case identity is a
   declared key, never positional and never a display name that can collide.** The origin's cases
   have names, and about 30 of them repeat through loops.

**The pytest shape.** A compliance SPEC is DATA, not code: one record per case, with the fields
`key, mode, fixture (source text), query operands, expected, disposition`. The disposition is one
of:

- `agree`: the reference and the port must both produce `expected`.
- `port-fixes`: the reference is measured wrong. The record carries the reason and the reference's
  actual output, so the divergence is pinned from both sides.
- `do-not-port`: the case stays in substrate. The spec keeps the row, but the test is not
  collected for the port.
- `unmeasured`: declared and counted outside, like the postgres case.

pytest parametrizes over the spec, with the keys as ids. A second, opt-in arm runs the same records
against the REFERENCE. If a substrate checkout is present, it runs; if not, the result is
UNMEASURED and fails, never a green skip.

The W36 count is then not a hand tally but the spec's own summary: the passing `agree` +
`port-fixes` records over (all − `do-not-port` − `unmeasured`).

**Consequence for W108:** the mapping becomes extracting the spec (one record per traced case), not
writing a prose table. The memo-as-cache FAIL is the first `port-fixes`-or-`agree` decision.

## W110 — placement's hidden population, COUNTED (2026-09-27)

- **6 cases.** The `_cases()` function in `substrate/scratch/_pycodemod_placement.py:436-469` makes exactly six
  `case(name, src, want)` calls:
  - entry-at-module-scope
  - first-write-helper
  - dispatched-under-mode
  - entry-one-hop
  - no-main-block-module-scope
  - hop-under-condition
- `_cases()` returns only failure strings, and `_pycodemod_selftest.py:160` turns each one into a failing `check`.
  Run directly, placement prints its OWN tally, `placement selftest: N/6` (:475-478). So the six passing cases are
  counted there, but NOT in the aggregate 407/408.
- **The honest aggregate denominator is 408 + 6 = 414.** Fingerprint's 36 are still inside it, as do-not-port.
- Every case carries its fixture source and expected verdict inline. That means W108 can capture them without
  tracing, so open question (c) is easy for placement.
- The letter (W107) reports this as an origin denominator defect: a sub-suite whose cases reach the aggregate only
  when they fail.

## DECIDED (operator, 2026-09-27): the spec language is REGO

Open question (a), TOML or JSON, was the wrong question. The survey had already answered it: the
ecosystem's compliance-spec language is Rego, in three repos, with an opa pin already in one
MODULE.bazel. A new data format would be a fourth dialect beside it.

**The shape, restated in Rego:**

- **A spec is a Rego package per mode.** Its rules read `input` =
  `{case, fixture, operands, result}`, where `result` is what the implementation under test
  produced. The rules emit the ecosystem's existing verdict sets, `deny` / `withheld` /
  `admitted`, with el-openglo's and luthen's convention (exit 0 admitted / 1 denied /
  3 withheld). A spec therefore says what COMPLIANT output is, not one exact expected value.
- **This dissolves open question (b), exact vs normalised comparison.** Normalisation is the
  policy's own business: Rego's set semantics make row order irrelevant by default, and a policy
  that needs exact order says so. So (b) is not a runner flag.
- **The pytest plugin is the runner, not the spec.**
  - `pytest_collect_file` claims the spec packages (and a case list per package).
  - Each item runs the SELECTED implementation (the subject port, or the reference origin,
    through the adapter hook) on the case fixture.
  - It hands `{case, fixture, operands, result}` to `opa eval data.<pkg>`, and maps the verdict
    sets onto pytest outcomes: `deny` → fail, `withheld` → fail as UNMEASURED (never skip-green),
    `admitted` → pass.
- **Dispositions become Rego data, not pytest markers.**
  - `do-not-port` and `unmeasured` are declared per case in the package's data.
  - `port-fixes` is a rule that ADMITS the port's output and DENIES the reference's recorded
    wrong output. The divergence is therefore pinned from both sides, in one policy, readable
    by anyone who reads Rego.
- **opa comes from the pinned toolchain,** the way luthen already pins it (`@opa` v1.20.2,
  `opa_linux_amd64_static`). opa on PATH is a fallback that must match the pin. An absent opa is
  a FAILED item, never exit 0: el-openglo's defect 1 and cassian's defect 2 are refused by
  construction.
- **The Rego specs themselves are tested with `opa test`** (their own `_test.rego`), AND
  exercised against real implementation output by the plugin. That closes el-openglo's defect 7,
  where opa test never meets a real measurement.

**Consequences:**

- The plugin is the fail-closed opa runner that el-openglo, luthen and cassian each hand-rolled.
  One distribution replaces three runners, so it meets the membership criterion (reuse beyond
  the origin repo) on day one.
- W108's spec extraction now produces Rego: one package per origin mode, cases as data, and
  expectations as rules. Open (c), fixture capture, still stands: the fixtures must be captured
  as `input.fixture` text.

## Operator direction, sharpened: exploit pytest's PLUGGABLE architecture

The spec is data, so pytest should COLLECT it rather than a test module parametrizing over it.
This is pytest's documented non-Python-test-files pattern (the "YAML test file" example), and it
turns the differential into a reusable plugin instead of one repo's conftest.

- pytest hook / type: `pytest_collect_file(file_path, parent)`; role here: claims `*.spec.toml` (or similar) files and
  returns a `SpecFile` collector
- pytest hook / type: `SpecFile(pytest.File).collect()`; role here: yields one `SpecItem` per record. `name` = the
  record's declared KEY (requirement 3: identity is declared, so a key collision is a collection ERROR)
- pytest hook / type: `SpecItem(pytest.Item).runtest()`; role here: runs the record's mode on its fixture through the
  SELECTED implementation and compares the result to `expected`
- pytest hook / type: `SpecItem.repr_failure` / `reportinfo`; role here: got/want and the spec's path:line, instead of a
  Python traceback into the plugin
- pytest hook / type: `pytest_addoption`; role here: `--impl=subject|reference` (repeatable) and `--reference-root PATH`
- pytest hook / type: an implementation ADAPTER registry (a plugin-owned hookspec, `pytest_spec_implementations`); role
  here: each implementation registers a callable `(mode, fixture, operands) -> result`. mtools registers the port; a
  substrate-side conftest, or an adapter that shells out to `scratch/pycodemod.py`, registers the reference. The plugin
  never imports either one
- pytest hook / type: markers from `disposition` (`spec_agree`, `spec_port_fixes`, `spec_do_not_port`,
  `spec_unmeasured`); role here: `-m` selection for free. `--strict-markers` (already in every mtools pyproject) refuses
  a misspelt disposition
- pytest hook / type: `pytest_collection_modifyitems`; role here: deselects `do-not-port` records for the subject (they
  are still COUNTED, as deselected, not dropped)
- pytest hook / type: an adapter or reference that is absent; role here: the item FAILS as UNMEASURED; it is never
  `pytest.skip` (requirement 2). A declared `unmeasured` record is `xfail(strict=True)`, so if it starts passing, that
  is news
- pytest hook / type: `pytest_terminal_summary`; role here: prints the differential line itself (agree / port-fixes /
  do-not-port / unmeasured / dropped), so the W36 figure is the run's own output and not a hand tally
- pytest hook / type: `port-fixes` with `--impl=reference`; role here: asserts the reference STILL produces its recorded
  wrong output, so an origin fix surfaces as a changed row

**Why a plugin and not a conftest.** The same machinery serves every "implementation vs spec"
pair in the ecosystem that the survey found:

- Rego policy vs spec, with opa as one adapter. It would replace el-openglo's unit-only
  `opa test` and give luthen and cassian one fail-closed runner.
- The pycodemod port vs its origin.
- Any future mtools cleanroom port vs its origin.

That makes it non-repo-local reuse, the membership criterion for its own distribution
(`mikemol-pytest-spec` or similar, registered through the `pytest11` entry point).

**Open questions, recorded and not decided here:**

- (a) The spec format: TOML (every mtools gate already reads it) or JSON (what OPA's inputs
  already are).
- (b) Whether `expected` is compared exactly or by a per-mode normaliser (row order, paths).
- (c) Whether the origin's 408 cases can be extracted mechanically. Their fixtures are inline
  source strings built in Python, so a traced run can capture (n, got, want) but not the
  fixture. The fixture and operands must come from the call site, or from wrapping the mode entry
  points during the trace.

## W109 — re-trace by caller file (2026-09-27)

`W36-trace.py` now records the CALLER's file with each check, since a line number alone does not
say which case module made it. `W36-origin-cases.tsv` was replaced; columns are now
`index, verdict, file, line, name`.

Run: `env -C ~/github/substrate .venv/bin/python ~/github/mtools/.claude/design/W36-trace.py OUT`
(exit 0; the origin's own tally line: `pycodemod selftest: 407/408`).

| caller file | checks |
|---|---|
| `_pycodemod_selftest.py` | 372 |
| `_pycodemod_fingerprint.py` | 36 |
| **total** | **408** |

- 407 PASS, 1 FAIL: row 225, `_pycodemod_selftest.py:1844`, "a live hand-rolled memo classifies
  as a cache". This is the origin's one known failure, and it is the 1 in 407/408.
- ⚑ All 36 fingerprint cases ran. They are one contiguous block at trace rows 335–370, with
  selftest rows on both sides (334 before, 38 after), so a line-only trace could not tell them
  apart from selftest checks at the same line numbers.
- The trace total equals the origin's denominator (408), so the traced population is the one the
  407/408 figure is taken over. Placement's passing cases are outside it (W110).

## W126 — mode map: origin cases by mode section (2026-09-27)

Each traced case (`W36-origin-cases.tsv`, 408 rows) is assigned to the `# ── <mode>` section
header that precedes its caller line in `substrate/scratch/_pycodemod_selftest.py` (35 headers).
Rows from `_pycodemod_fingerprint.py` are their own mode. Placement's 6 cases (W110) are outside
the 408 and get their own row. The per-row map is `.claude/design/W36-origin-modes.tsv`
(index, mode, verdict, file, line), made by `.claude/design/W36-modemap.py` (its OUT path points at
the scratchpad; the copy beside this file is the record).

| mode section | cases | FAIL |
|---|---|---|
| losslessness (roundtrip, scan; lines 110–121, before the first header) | 4 | 0 |
| `--guarded` | 4 | 0 |
| `--swallows` | 6 | 0 |
| `--check-contracts` | 3 | 0 |
| `⟡mode-opt-key-collision` | 6 | 0 |
| `Mode.writes` | 7 | 0 |
| `--rivals` | 35 | 0 |
| `asserted()` | 8 | 0 |
| `values()` | 33 | 0 |
| `py_files()` | 4 | 0 |
| `--projects` | 7 | 0 |
| `--source` | 4 | 0 |
| `--key` | 5 | 0 |
| `--artifacts` | 6 | 0 |
| F5 (`n of m` denominator) | 1 | 0 |
| `--importers` | 4 | 0 |
| `--aliases` | 7 | 0 |
| `--size` | 7 | 0 |
| commentary census | 38 | 0 |
| `--shape` | 9 | 0 |
| `--binding` | 21 | 0 |
| `--state` | 7 | 1 |
| `--sql` | 4 | 0 |
| `--literal` | 7 | 0 |
| `--crossings` | 5 | 0 |
| `--relalg` | 7 | 0 |
| `--relname` (both headers, incl. the `sql_rw` read/write split) | 29 | 0 |
| `--snapshots` | 5 | 0 |
| `--control` | 23 | 0 |
| `--split` | 28 | 0 |
| `--reifies` | 13 | 0 |
| `--resorts` | 7 | 0 |
| `--funcnames` | 8 | 0 |
| `--ambient` | 10 | 0 |
| `--fingerprint` (own module, `_pycodemod_fingerprint.py`) | 36 | 0 |
| **traced total** | **408** | **1** |
| placement (`_pycodemod_placement._cases`, W110; outside the 408) | 6 | — |
| **all origin cases** | **414** | |

- The one FAIL is under `--state` (row 225, selftest.py:1844, "a live hand-rolled memo
  classifies as a cache"). That matches W109.
- ⚑ The selftest's own `--fingerprint` header (line 2768) has 0 traced cases. All 36 fingerprint
  checks come from the separate module, so they are counted once, in the fingerprint row.
- ⚑ The map uses the nearest preceding header, which is a structural reading. A case that
  tests one mode from inside another mode's section would be counted under that section. W127's
  disposition cut works at this grain, so that is acceptable here; it is not a per-case audit.

## W127 — disposition cut and the W36 denominator (2026-09-27)

This applies the port's own disposition lists (`.claude/queue.md:688-712`, the DRIVER MODE MAP; the
W37 letter sent the same lists to substrate) to the W126 mode map. Each section gets one
disposition. A case takes the disposition of the section it sits in, at the W126 grain.

- disposition: **do-not-port**; mode sections (cases): `--control` 23 · `--fingerprint` 36 · `--artifacts` 6 ·
  `--projects` 7 · `--relalg` 7 · `--snapshots` 5 · `--sql` 4; cases: **88**
- disposition: **deferred** (stays in substrate until a second repo asks); mode sections (cases): `--relname` 29 (the
  SQL relation reader, incl. `sql_rw`) · `--split` 28; cases: **57**
- disposition: **driver concern** (the origin describing its own mode table; queue.md:705-707); mode sections (cases):
  `--check-contracts` 3 · `⟡mode-opt-key-collision` 6 · `Mode.writes` 7; cases: **16**
- disposition: **in scope for the port**; mode sections (cases): every other section (losslessness 4, `--guarded` 4,
  `--swallows` 6, `--rivals` 35, `asserted()` 8, `values()` 33, `py_files()` 4, `--source` 4, `--key` 5, F5 1,
  `--importers` 4, `--aliases` 7, `--size` 7, commentary 38, `--shape` 9, `--binding` 21, `--state` 7, `--literal` 7,
  `--crossings` 5, `--reifies` 13, `--resorts` 7, `--funcnames` 8, `--ambient` 10) + placement 6; cases: **253**
- disposition: **total**; cases: **414**

- **unmeasured: 0 inside the 414.** The origin's postgres case is SKIPped and is already outside
  the 408 (W106). It is recorded as +1 outside, not subtracted.
- **The W36 denominator is 253** = 414 − 88 do-not-port − 57 deferred − 16 driver concern.
  Intermediate figures, so W107 can state each cut separately: 414 − 88 = **326**, and
  326 − 57 = **269**, before the driver-concern cut.
- The one origin FAIL (memo-as-cache, `--state`) is **inside** the 253. It is the first
  agree-or-port-fixes decision W108 must make.
- ⚑ **Two of the dispositions are judgments, not list lookups.** Both are recorded so W107 can
  name them:
  - `⟡mode-opt-key-collision` and `Mode.writes` were classed as driver concerns because they test
    the origin's `Mode` table. The queue lists `--check-contracts`, `--declare-modes` and the
    like, but it does not name these two sections. If either tests a general property the port
    also owes, it moves into scope (+13 at most, giving 266).
  - `--importers` is counted in scope: it was RETIRED as a flag spelling but ported as
    `imports.importers` (queue.md:689).
- The residual risk is the W126 caveat: a case can sit under one header and test another mode.
  W108's per-case pass is where that gets checked.

## W128/W186: fixture capture over the origin's 408 checks (2026-09-27)

Instrument: `.claude/design/W128-capture.py`, a profiler on calls from the selftest body into
pycodemod modules. Output: `W128-captured.jsonl`. Counts: `W128-count.py`. The origin
selftest reported 407/408 under the profiler, the same as unprofiled.

| class | checks | meaning |
|---|---|---|
| fresh | 183 | at least one mode call since the previous check |
| sticky | 224 | reuses the last call's result; attribution is the last call, **unverified** |
| none | 1 | #1, the libcst round-trip, which calls libcst directly and no mode |

288 of the 408 checks carry fixture file text. The remaining 120 fall mainly in these
sections:

- `--fingerprint`: 36 of 36. ⚑ Its checks run inside `_pycodemod_fingerprint.py`, not the
  selftest body, so the caller filter cannot see its mode calls. These 36 are instrument
  blind, not fixture-free.
- `--relname`: 27 of 29.
- commentary census: 12 of 38.
- `--rivals`: 8 of 35.
- `Mode.writes`: 7. `--projects`: 7. `⟡mode-opt-key-collision`: 6. `py_files()`: 4.

The last four sections most likely pass inline strings rather than paths, and the capture
reads only existing-file arguments. The inline strings are recorded in `operands`, but only
truncated to 300 chars.

Next: widen the filter to the fingerprint module and keep full inline string operands. Then
the 120 split into truly-uncapturable and instrument gaps.

## W187: widened capture (2026-09-28)

Changes to `W128-capture.py`:

- Calls made from any pycodemod module's `_cases(check)` are now in scope.
- String arguments are kept whole instead of cut at 300 chars.

Rerun output: `W187-captured.jsonl`. Selftest still 407/408.

**Counts** (`W187-count.py`):

- By class: fresh 213 (up from 183), sticky 194, none 1.
- By input: file 290, inline multi-line 6, "uncaptured" 112.

**The 112 split** (`W187-sample.py`, three rows per mode, read by hand):

- bucket: captured, counter too strict; modes (count): `--fingerprint` 31, `--relname` 27; what it is: the whole input
  is a one-line str operand (a SQL string, a registry key); the counter wanted `\n`
- bucket: instrument gap: directory fixture; modes (count): `--projects` 7, `py_files()` 4; what it is: the operand is a
  tempdir path; the capture reads only files, so the tree is lost
- bucket: no text fixture exists; modes (count): `Mode.writes` 7, `⟡mode-opt-key-collision` 6; what it is: pure-data
  checks on `Mode` objects; the operand repr IS the fixture; sticky attribution is to an unrelated earlier call
- bucket: unsampled; modes (count): commentary 10, `--rivals` 8, `--binding` 4, `values()` 3, 5 singletons; what it is:
  not yet read

The distinction that matters is not about text. Sorted by whether the input can be rebuilt:

- **Rebuildable from the operand repr:** the fingerprint, relname and Mode-data checks, 71 in
  all.
- **Need a directory snapshot:** 11.
- **Still to be read:** 30.

## W189: the 30 unsampled fixture-less checks, bucketed (2026-09-28)

Read by hand with `W187-sample.py`, all 30 rows:

- bucket: rebuildable from operands; checks: 13; modes: `--rivals` 8, `values()` 3, `--split` 1, `--source` 1; porting
  consequence: the operands are the fixture (argv, names, a call graph dict, a def table). ⚑ But non-str operands are
  still `repr(v)[:300]`, and `values()`'s call graph and `--split`'s `by_i` ARE cut. That is an instrument gap.
- bucket: reads the live origin tree; checks: 16; modes: commentary census 10, `--binding` 4, `--check-contracts` 1,
  `--funcnames` 1; porting consequence: `path=None` means pycodemod's own source; `_roots()` is substrate's layout;
  `_generic_func_names()` is SQLAlchemy's registry. These check the ORIGIN, not a fixture. Each is either DO-NOT-PORT or
  needs a pinned snapshot.
- bucket: pure library; checks: 1; modes: #1, libcst round-trip; porting consequence: no mode; ports as a libcst
  property test, or not at all

**All 112 fixture-less checks, combined with the W187 split:**

- **84 rebuildable from their operands:** fingerprint 31, relname 27, `Mode` data 13, and
  these 13.
- **16 read the live origin tree.**
- **11 need a directory snapshot:** `--projects` 7, `py_files()` 4.
- **1 pure library.**

Instrument work still owed, before those counts can be called a capture:

- non-str operands kept whole, not cut at 300 chars;
- directory operands walked into a tree snapshot.

## W191 (W189a): bucketing the unsampled fixture-less groups

Instrument: `.claude/design/W191-bucket.py` over `W187-captured.jsonl`. Operands that name a temp
path count as dir-snapshot, operands that name `/home/mikemol/github/` count as live-tree, and the
rest count as rebuildable.

| group | W187 said | fixture-less here | bucket |
|---|---|---|---|
| the ⚑ COMMENTARY census | 10 | 12 | rebuildable 12 |
| --rivals | 8 | 8 | rebuildable 8 |
| --binding | 4 | 4 | rebuildable 4 |
| values() | 3 | 3 | rebuildable 3 |

**The grouped checks: 27 of 27 are rebuildable from their operands.**

⚑ **This is a lower bound on tree dependence, not a proof that none exists.** The instrument only
sees paths that appear *in operands*. A check that reads the origin tree implicitly (through a
module-level root or cwd) shows as rebuildable here. Evidence that it misses these: py_files()
buckets as rebuildable 4, but W187 found it needs a directory snapshot. So the 16 live-tree checks
and 11 dir-snapshot checks counted in W187 still stand. This pass only positively identifies
--projects 7 and --source 1 as dir-snapshot.

Divergence, carried rather than resolved: COMMENTARY counts 12 fixture-less here against W187's 10.
The fixture test differs: this script counts a row as fixture-less when none of its calls has
fixtures, whereas W187 counted per call. Totals are 118 here against 112.

Next: W192's capture change (directory snapshots and whole non-str operands) is the step that lets
implicit tree reads become visible.

## W192 (W189b): capture with directory snapshots

Instrument: `W128-capture.py` v2. It walks temp-directory operands into `<dir>//<rel>` fixtures (at
most 200 files each), reads PathLike operands, and keeps non-str operands whole. Output is
`W192-captured.jsonl`, compared by `W192-count.py`.

```text
checks 408  classes {none 1, fresh 213, sticky 194}  with_fixture_text 297 (W187: 290)
pycodemod selftest 407/408 (postgres case SKIP-unmeasured; memo-as-cache FAIL: both unchanged)
gained fixtures:       --projects 7
carry a dir snapshot:  --projects 7
still fixture-less:    111
```

**7 of W187's 11 dir-snapshot checks now carry their tree.** The other 4 are `py_files()`. It still
captures no fixture, because its tree never reaches a mode call as an operand: the case builds the
tree and passes something that is not a temp-dir path. Carried, not resolved.

⚑ Correction to the W192 ledger line of 02:32. That line blamed the unbounded walk for v1's
slowness. v2 bounds the walk and still took about 30 minutes, the same time at which v1 was
killed, so v1 was probably nearly finished. The diagnosis was wrong. The bound stays because it is
correct on its own terms, but it made no measured difference to runtime.

The COMMENTARY count of 12 against W187's 10 is still carried from W191.

## W189: capture v3 (varargs operands, temp-rebound ROOT)

Defect found. v1 and v2 read `co_varnames[:co_argcount]`, which counts positional parameters only,
so every `*args`, keyword-only and `**kwargs` operand was dropped. `py_files(*roots)` recorded `{}`.
v3 reads all four kinds, and records `<global ROOT>` when a case rebinds the module global to a temp
tree. Output is `W189-captured.jsonl`; `W189-count.py` compares it with v2 and `W189-pyfiles.py`
inspects the py_files rows.

```text
with_fixture_text 303 (v2 297, W187 290)
gained fixtures:      py_files() 4, COMMENTARY 2
carry a dir snapshot: --projects 7, py_files() 4   = 11 of 11
still fixture-less:   105
```

- **All 11 dir-snapshot checks now carry their tree.** #107 and #108 carry it via `roots`, #109 and
  #110 via `<global ROOT>`.
- **The W191 divergence is resolved.** COMMENTARY's 12-vs-10 was 2 checks whose operands the
  varargs defect dropped. With them captured, 10 remain fixture-less, which matches W187.
- ⚑ **Residue: #110 cannot be rebuilt from its snapshot.** Its subject is a `bazel-proj` symlink.
  `os.walk` does not report a symlinked directory as a file, so the snapshot holds the 6 files but
  not the link. A rebuild would pass vacuously. Minted as W193.

Final buckets for the 112/105 fixture-less denominator: rebuildable from operands, with 11 checks
that need a directory snapshot (10 now rebuildable from the capture, 1 needing the symlink).
The 16 live-origin-tree readers remain as W187 measured them.

## W196: first Rego spec, `--guarded`

Spec: `.claude/design/W196-spec/guarded.rego` (+ `guarded_test.rego`), `opa test` PASS 6/6.
The origin fixture's expected rows are admitted; each single-row mutation is denied.

Port run (`.claude/design/W196-port.py`, `guarded --target g`), exit 0, no incomplete banner:

    under g.py:4:8 if apply
    under g.py:7:12 if a / b
    under g.py:11:8 if not (c)
    top g.py:2:4

Three of the four cases agree. **else-body diverges:** the origin reports the call under `c`,
while the port reports `not (c)`. The spec as written denies the port's row. The port's docstring
(`pycodemod/src/mikemol/pycodemod/arguments.py:99`) says the negation is intended. Arguably the
port is the more precise of the two, because the call runs exactly when `c` is false. This is not
adjudicated here; W197 decides whether it is a port-fix (amend the spec) or a port defect.

## W200: the guarded spec, run by the runner

`mikemol-pytestspec` (installed, `plugins: mikemol-pytestspec-0.1.0`) over W196's
`guarded.rego`, with cases built from the port's W196 output, and pinned opa 1.20.2:

    guarded.rego ...FF
    else-body: DENIED: else-body: line 11 is not reported under [c]
    mystery: UNMEASURED (withheld, not passed): no rule for case mystery
    2 failed, 3 passed

This matches W196's hand reading. The else-body divergence (W197) is now reported by the
runner, not by eye.

## W197: else-body is a port-fix

Decided as a **port-fix**, and the spec was amended. An else body runs exactly when `c` is false.
The origin's row `c` therefore names a condition that is false wherever the call runs. A gate
reading it would conclude that a call in the `else` of `if apply:` runs under `apply`. That is the
gate-hiding axis that `arguments.py:102` exists to close.

W196's own rule comment ("NEVER negated: a negated test ... is FALSE where it runs") had the
logic backwards: it is the origin's un-negated test that is false there.

`guarded.rego` #8 now requires `[not (c)]`. `guarded_test.rego` pins both sides:

- the port's result is admitted for all four cases;
- the origin's result is admitted for the three cases where the two sides agree;
- the origin's else-body row is pinned as a DENIAL.

`opa test` PASS 7/7. This divergence is a finding to report upstream to substrate, whose
pycodemod carries the origin behaviour.

### W197 residue: the origin's contract is deliberate

The origin's check (`_pycodemod_selftest.py:146-150`) documents its choice. The else body is
reported under its `if` "DELIBERATELY", as an **over-report, never an inversion**: `conds` means
"the tests of the enclosing `if` statements", a structural answer. It is not a statement about
truth where the call runs. So the divergence is two deliberate contracts, not one side's
mistake. The port-fix decision stands, because the port's contract is the one a gate needs, but
the upstream report (W204) must frame it that way.

The origin's fear is a real test for the port: an `elif` chain. A correct negation of the else
body of `if a: … elif b: … else: g()` is `not (a)`, `not (b)`. A naive negation of only the
nearest test would be the inverted answer the origin warns about. Probe minted as W210.

## W205: both implementations, live, through --impl

`W196-spec/conftest.py` offers `reference`, substrate's `_pycodemod_query.guarded`, and
`subject`, the mtools port's CLI. `guarded.cases.json` carries the fixture and operands, not a
result. It runs from the pycodemod venv with
`PYTHONPATH=pytestspec/src:substrate/scratch` and `-p no:pytestspec -p mikemol.pytestspec.plugin`.
The venv's installed pytestspec is stale and has no `--impl`.

```text
pytestspec: .claude/design/W196-spec/guarded.rego impl=subject admitted=4 denied=0 unmeasured=0 do-not-port=0 port-fix=0
pytestspec: .claude/design/W196-spec/guarded.rego impl=reference admitted=3 denied=1 unmeasured=0 do-not-port=0 port-fix=0
else-body: DENIED: else-body: line 11 is not reported under [not (c)]
```

This is W197's port-fix, now measured against both live implementations rather than a frozen
row.

## W210: the elif chain, probed and pinned

Probe: `.claude/design/W210-elif.py`, one call in each branch of `if a / elif b / else`:

    port    under 3 [a] · 5 [not (a), b] · 7 [not (a), not (b)]
    origin  under 3 [a] · 5 [a, b]       · 7 [a, b]

The port negates **every** earlier test, so there is no nearest-test inversion. The origin
over-reports the same way it does for the else body. Pinned as case `elif` in `guarded.rego`
(two rules). `guarded_test.rego` admits the port's chain, denies the origin's twice, and denies
a nearest-only negation. `opa test` PASS 10/10.

```text
pytestspec: .claude/design/W196-spec/guarded.rego impl=subject admitted=5 denied=0 unmeasured=0 do-not-port=0 port-fix=0
pytestspec: .claude/design/W196-spec/guarded.rego impl=reference admitted=3 denied=2 unmeasured=0 do-not-port=0 port-fix=0
```

## W206: per-mode case data, all 35 modes

`.claude/design/W206-gen.py` joins `W187-captured.jsonl` to `W36-origin-modes.tsv` on the case
index and writes `W206-cases/<mode>.cases.json`. Each case keeps what the origin called
(`calls`: fn and operands), the fixtures it read, and its origin check name and line. It never
keeps a result. The script refuses (exit 1) unless every mode's count equals the map's.

Result: 35 of 35 modes match, **408 cases vs map 408**. One case declares `unmeasured` (#1,
"libcst round-trips comments and blank lines", capture class `none`, no call). The largest
modes, which W207 takes first:

- the-commentary-census 38
- fingerprint-own-module 36
- rivals 35
- values 33
- relname 29
- split 28

## W207 step 1: a generic reference adapter, smoke-run

The generator's keys are now `fixture` ({original path: source}) and `operands`
([{fn, args}]), the W202 `--impl` shape. It still reports 408/408 over 35 modes.
`W206-cases/conftest.py` holds one generic `reference` adapter:

- recreate the fixture files under a fresh root;
- rewrite the original root inside each repr'd arg, then `ast.literal_eval` it;
- call `<module>:<fn>` from substrate/scratch;
- normalize the return value to JSON.

Smoke (`W207-smoke.py`, unbuffered, 120 s cap) over the first 23 modes: **186 ran, 37 raised,
1 empty**. The raises:

- fingerprint-own-module 29 of 36
- mode-writes 5 of 7
- mode-opt-key-collision 3 of 6

It **hangs at `resorts`**, and the modes after it were not reached. A buffered 600 s run printed
nothing, which is how the hang showed. The raise messages were not yet printed, because the
tally prints at the end.

## W211: the smoke covers every mode

`W207-smoke.py` now runs each case in a forked child with a 10 s timeout and prints each error
as it happens. The full run finishes: **346 ran, 54 raised, 7 timed out, 1 empty (408)**.
28 of 35 modes run clean. The `raised=` and `timeout=` columns below count cases:

- mode: fingerprint-own-module; raised: 29 of 36; apparent shape (for W212 to confirm): the operand is a repr'd object
  (`'str' has no attribute get_or_assign/primes/_fields`), or it calls a nested or method callee (`get_or_assign`,
  `prime_for`, `<genexpr>`) that isn't a module-level function
- mode: split; raised: 7 of 28; apparent shape (for W212 to confirm): an arg that was a dict or object was captured as a
  repr string
- mode: resorts; timeout: 7 of 7; apparent shape (for W212 to confirm): every case hangs; the origin call itself doesn't
  return within 10 s
- mode: swallows; raised: 5 of 6; apparent shape (for W212 to confirm): a callee named `case` isn't a module attribute
  (a local helper)
- mode: values; raised: 5 of 33; apparent shape (for W212 to confirm): the `module()`/`check` callee name refers to a
  selftest-local function, not a module function
- mode: mode-writes; raised: 5 of 7; apparent shape (for W212 to confirm): a dict arg arrived as a string (`.items`)
- mode: mode-opt-key-collision; raised: 3 of 6; apparent shape (for W212 to confirm): same as mode-writes

Main cause: the W187 capture recorded non-literal args as `repr` strings, and recorded calls
to selftest-local callables by their bare names. Those are gaps on the capture/adapter side.
None of these errors shows a port or origin disagreement. `the-commentary-census` runs 38/38,
so W213 can start now.

## W213 step 0: the census "mode" is nine subjects, and the adapter can't be edited yet

The 38 `the-commentary-census` cases (origin lines 1342–1597) call nine different callees:

- `commentary_census`, `commentary_kinds`, `commentary_lost` (commentary module);
- `modes`, `_modes_ast`, `cst_modes`, `argopt_flags`, `declared_operand_flags` (`pycodemod.py`);
- `py_files` (core);
- `collision_apex` and `shape_sites` (query module).

The origin's section heading groups them together; the subject doesn't. A spec per **callee**
is the unit, so W213 has to be split. Three measured obstacles:

1. **The fixture root leaks into results.** Paths come back under the fresh `/var/tmp/tmpXXXX`,
   or as `../../../../var/tmp/...` relative paths in `collision_apex`. A rule can't name a file
   until the adapter maps the fresh root back to `<root>`.
2. **`py_files` (165–167) walks the live repos.** The results list real files under
   `~/github/mtools` and `substrate`, so they depend on the machine and the date. They need a
   disposition (unmeasured, with that reason) or a fixture-scoped cwd.
3. **`shape_sites` (186–189) returns `[[]]`** for all four cases. Those cases are about the
   origin's *own* defect patterns, so an empty result probably means the capture lost the
   target and the result isn't really empty. W212 should check this before any rule admits `[]`.

Also: the pycheck Edit hook refuses any edit to `W206-cases/conftest.py`. It was written
untyped, and now has about 46 mypy findings (strict, no Any). The adapter needs one clean,
typed rewrite before root-mapping (1) can go in.

## W214: the adapter is typed and root-mapped

`W206-cases/conftest.py` was rewritten in one pass, and pycheck (strict mypy, no Any) accepted
it:

- captured data is narrowed through `str_map`/`calls` (raising `CaseDataError`);
- origin callees go through an `OriginCall` Protocol with `**kwargs`, not `Callable[..., object]`,
  which counts as explicit Any;
- `normal(value, root)` writes the fresh fixture root as `<root>`.

The smoke is unchanged at **346 ran / 54 raised / 7 timeout / 1 empty**. Census results now read
`<root>/kinds.py`.

Residue: `collision_apex` returns paths relative to the **cwd**, so they come back as
`../../../..<root>/apexcase.py`. The `../` prefix depends on how deep the run starts. Its spec
(within W213) has to either strip everything up to `<root>` or run from a fixed cwd. It can't
state the prefix.

## W213: the first per-callee rules — commentary_kinds

`W206-cases/the-commentary-census.rego` judges `commentary_kinds` (#161–#164). Each case has
one deny rule, taken from the origin check at `_pycodemod_selftest.py:1430-1443`:

- executable rows are exactly one `check(` and one `print(`;
- exactly one comment row;
- exactly one docstring row;
- the untokenizable file is the one unparsed row.

Every other case in the section is `withheld`. `opa test` over both files (spec and
`_test.rego`) gives **6/6**: the reference output is admitted, one mutation per case is
denied, and an unjudged case is withheld. Under the plugin:

```text
pytestspec: .claude/design/W206-cases/the-commentary-census.rego impl=reference admitted=4 denied=0 unmeasured=34 do-not-port=0 port-fix=0
```

The remaining 34 cases are split one callee per waypoint (W215–W220), in the order they
appear in the section.

## W218: commentary_lost (#183–#185)

Three deny rules, taken from the origin at `_pycodemod_selftest.py:1568-1576` ("an unresolvable
baseline must be VISIBLE, not a pass"). The result is `[lost, new, before, after]`:

- `lost == []`;
- `before == 0`, where a nonzero value would be an invented baseline;
- `after == 4`.

`opa test` gives **10/10**. The new arms deny a phantom loss, an invented baseline, and an
uncounted present. Under the plugin:

```text
pytestspec: .claude/design/W206-cases/the-commentary-census.rego impl=reference admitted=7 denied=0 unmeasured=31 do-not-port=0 port-fix=0
```

## W217: collision_apex (#171–#174)

Four deny rules, from the origin at `_pycodemod_selftest.py:1511-1531`. Rows are keyed by name,
as the origin keys them:

- the dedent: `handler` carries exactly 2 deep-skeleton labels;
- identical, not undecidable: its holes are `0`, not `null`;
- absent, not zero-scored: there is no `solo` row;
- the row is seven-wide.

⚑ **The cwd-relative path residue from W214 doesn't bite here.** The origin only counts labels
and never states a path, so the spec doesn't either. A later callee whose check does name a
path will still need the strip-to-`<root>` helper.

`opa test` gives **15/15**. The new arms deny a dropped dedent, `null` holes, a zero-scored
`solo` row, and a six-wide row. Under the plugin:

```text
pytestspec: .claude/design/W206-cases/the-commentary-census.rego impl=reference admitted=4 denied=0 unmeasured=0 do-not-port=0 port-fix=0   (-k 171..174)
```

The whole file gives 11 passed and 27 failed (all withheld), so admitted=11 and unmeasured=27.

## W220: shape_sites (#186–#189): two admitted, two misattributed

**The capture is faithful for 186 and 187.** The fixture carries the scanned file
(`pycodemod.py`), the operands are `shape_sites(pattern, [that file], in_code_only=True)`, and
a live scan of the *current* file also finds 0 rows for both patterns (`W220-peek.py`). The
origin expects `[]` after its `_in_dispatch` filter, so `[[]]` really is the compliant answer.
W213's concern that an empty result was hiding a lost target is **refuted** for these two.

**188 and 189 are misattributed.** Their origin checks (`_pycodemod_selftest.py:1593-1599`) run
`re.search` on a literal string: that is the regex's self-test, and it calls no callee. The
capture recorded the previous check's `shape_sites` call against them, so the "result" doesn't
measure the check. They stay **withheld**, which is accurate. Disposing them needs a declared
`MISATTRIBUTED` table in `W206-gen.py`. pycheck refused that edit because the generator is
untyped (the same class as the W214 adapter). The fix is W221, a typed rewrite.

`opa test` gives **18/18**. The new arms deny a row-derived count and an `or None` widening row.
Under the plugin:

```text
pytestspec: .claude/design/W206-cases/the-commentary-census.rego impl=reference admitted=2 denied=0 unmeasured=2 do-not-port=0 port-fix=0   (-k 186..189)
```

## W221: the generator is typed, and misattribution is declared

`W206-gen.py` was rewritten in one pass, and pycheck (strict mypy, no Any) accepted it:

- capture records are narrowed into frozen `Record`/`Call` dataclasses (raising `CaptureError`);
- a `MISATTRIBUTED = {i: reason}` table declares `unmeasured` for checks whose captured call
  isn't what they judge, so a regeneration keeps the disposition and no generated case is ever
  edited by hand.

Regeneration: **408/408, unmeasured 3**: #1 has no call captured, and #188 and #189 are
misattributed (W220). Under the plugin, 188 and 189 move from FAIL (withheld) to **XFAIL**
with their reason:

```text
pytestspec: .claude/design/W206-cases/the-commentary-census.rego impl=reference admitted=2 denied=0 unmeasured=2 do-not-port=0 port-fix=0   (-k 186..189)
```

W212's remaining raises (capture repr-strings and selftest-local callees) will need entries
of the same kind, and this table is where they go.

## W219: py_files (#165–#167): the capture drops *varargs

All three checks call `py_files(*roots)`, and the capture recorded `operands: {}` for each. It
keeps named parameters and **drops `*args`**, so a replay calls `py_files()` and walks the
whole default corpus (real files under `~/github/mtools` and `substrate`). The machine- and
date-dependent result that W213 step 0 saw was this: a capture gap, not a fact about the
origin. Two more obstacles to replaying:

- 165 runs with the fixture dir as cwd (`os.chdir(_d)`);
- 166 is judged by whether the call **raises** `PopulationError`, and the adapter reports a
  raise as an error, not as a value.

All three are declared `unmeasured` in `W206-gen.py`'s `MISATTRIBUTED`, each with its reason.
Regeneration: **408/408, unmeasured 6**.

⚑ **This is a capture class, and it goes to W212.** 26 captured calls have empty operands:

- `py_files` ×7 and `_roots` ×4: `*roots` callees, likely dropped varargs;
- `_pycodemod_placement._cases` ×5 and `_generic_func_names` ×1: to classify;
- `pg_probe_status` ×7 and `declared_operand_flags` ×2: plausibly zero-argument, to confirm
  against their signatures.

A capture fix (record `*args` under a reserved key) would make the `*roots` group replayable.
Until then each one is a `MISATTRIBUTED` entry.

## W216: the modes family (#157–#160, #175–#179)

These cases judge the origin's **own CLI table** (`pycodemod.py`). Eight rules, taken from the
origin at `_pycodemod_selftest.py:1386-1415, 1540-1551`:

- 157: every flag the derivers find is declared, minus the named over-fires;
- 158: those over-fires still over-fire, so the exemption can't outlive its cause;
- 159: `modes()` is a stated census;
- 175: the stdlib road and the CST road agree;
- 176: more than 20 modes;
- 177–179: the CST precondition is per-mode (`--roundtrip` needs a CST; `--size` and
  `--commentary` don't).

**160 is declared `unmeasured`**: it compares `modes()` against the module constant `MODES`,
which no call returns, so the capture holds only one side.

`opa test` gives **27/27**. The new arms deny:

- an undeclared operand flag;
- a stale exemption;
- a missing census;
- roads that disagree;
- an empty road;
- a blanket CST requirement.

Regeneration gives 408/408 with 7 unmeasured. Under the plugin:

```text
pytestspec: .claude/design/W206-cases/the-commentary-census.rego impl=reference admitted=8 denied=0 unmeasured=1 do-not-port=0 port-fix=0   (-k modes family)
```

⚑ For the port, these rules are **directly portable**. They judge a CLI table's
self-consistency, not the origin's spelling, so `--impl subject` should satisfy them over the
port's own table. A port-side adapter for these callees is the natural subject arm.

## W215 — commentary_census (closes W213)

The 7 measurable commentary_census checks got rules: 152 (4 marked lines), 153 (group total 3), 168 (NB is not a
substring), 169 (NB as a token), 170 (glyph), 181 (re-indent keeps total 4) and 182 (duplicate at 2 sites). Each rule
has a two-armed test. `opa test` gives 35/35 PASS. The withheld-arm test moved from 152 to an unjudged name, because 152
is now judged.

Checks 154, 155, 156 and 180 are declared unmeasured in W206-gen MISATTRIBUTED. The capture keeps only a check's latest
call, and these checks judge the earlier whole-file census _t0. That gap is handed to W212.

`--impl reference` over the-commentary-census.rego:

    admitted=28 denied=0 unmeasured=10 do-not-port=0 port-fix=0   (28 passed, 10 xfailed)

W213's section is fully accounted for. Every case is admitted or declared unmeasured with a reason, and nothing is
withheld.

## W212 — bucket the W211 raises and timeouts

Smoke re-run on 2026-09-28: `TOTAL ran=346 raised=54 timeout=7 empty=1`. This matches the W211 baseline. Every raise was
bucketed by its message:

- bucket: repr-string operand; n: 26; cases: split 318-322,330,331 · mode-writes 024-028 · mode-opt-key-collision
  021-023 · fingerprint 339,345,347-349,353-357,359; cause: the capture stored a non-literal arg (an AST node, a
  registry, a dict of modes) as its repr, so the replay hands the callee a `str`
- bucket: callee resolves to `module()`; n: 10; cases: fingerprint 338,340,341,346,350,351,363,369 · values 098,102;
  cause: the recorded fn name resolves to the `module` type itself (a constructor or class recorded as a function)
- bucket: callee not in module; n: 16; cases: fingerprint 336,337,342,364-368 · swallows 009-013 · values 099-101;
  cause: a method, a selftest-local helper or a `<genexpr>` was recorded as a module-level function
- bucket: other; n: 2; cases: fingerprint 335 (`'str' object is not callable`), 344 (strict-mode ValueError, the
  downstream effect of a repr'd registry); cause: consequences of the repr bucket
- bucket: timeout (10s); n: 7; cases: resorts 384-390; cause: not yet diagnosed

**Adapter-gap bucket: 0.** No raise is fixable in conftest.py. Every one is a W187 capture defect: repr'd operands,
misresolved callees, and (from W215/W219) latest-call-only and dropped *varargs. The fix belongs to the capture, and
until the capture is fixed these cases are declared unmeasured with the reasons in the table above.

## W222 — the 54 raising cases declared

W206-gen maps each case in the W212 buckets to a `disposition: unmeasured` with that bucket's reason (repr 26, module()
10, absent 16, knock-on 2). The map is `_BUCKETS`, merged into `MISATTRIBUTED`. Regeneration gives
`total 408 vs map 408; unmeasured 65`, which is the 11 declared before plus these 54. The 7 resorts timeouts are not
declared yet (W223).

## W223 — the 7 resorts timeouts are a slow walk, not a hang

`_pycodemod_query.resorts(paths)` (substrate scratch :1807) always joins against `reifies()` over the UNION of the
default corpus and the walked paths (:1854-1866). That is a full-corpus CST walk, memoised because "the unmemoised
version did not finish in two minutes" (:1867). The origin selftest pays for it once and runs 384-390 against the warm
memo. W207-smoke forks per case with TIMEOUT=10, so each fork pays for the whole cold walk. The cause is the harness
(origin-needs-state: a warm memo), not an adapter gap and not a hang.

Not yet measured: the cold walk's wall time, and whether one pytestspec process (no fork) amortizes it the way the
origin does.

## W224 — one process does not amortize: the adapter's fresh root defeats the memo

Ran `pytestspec --impl reference resorts.rego` in one process under `timeout 580`. Only 3 of 7 cases finished (exit 124,
`FFF` = withheld, as intended), so each case costs about 190s cold even without a fork. Cause: `_PRODUCER_CACHE` is
keyed by the resolved population `tuple(py_files() + files)` (substrate `_pycodemod_query.py:1874-1876`). conftest
`rehome()` makes a fresh `mkdtemp()` per case, so the fixture path, and therefore the key, differs every time, and every
case misses the memo.

This is an adapter gap after all: the first one found (W212 had 0). The fix is a deterministic root per fixture content.
It would take the cost from about 7 × 190s to 1 × 190s for this mode, but even the first case exceeds any per-case smoke
timeout. `resorts.rego` (withheld-only) is kept as the timing harness.

## W225 — content-addressed fixture root: the memo now survives across cases

conftest `rehome()` writes each fixture under `BASE/<sha256(fixture)[:16]>` (one `BASE` per session) instead of a fresh
`mkdtemp()`. `-k "384 or 385"` measures `384 290.65s` (cold walk) then `385 0.12s` (memo hit, same fixture). Resorts has
2 distinct fixtures (384-389 share `resort_case.py`; 390 is `clean.py`), so the mode costs 2 cold walks ≈ 580s. The
earlier full-mode run (6/7 inside `timeout 580`) is that arithmetic, not a miss. Resorts is measurable under a spec run
with a budget of about 10 min; it is not measurable under the forked 10s smoke.

## W226 — resorts judged

`resorts.rego` rules for 384-387 (redundant row, re-keyed separate, reverse is a re-key, non-sorting callee absent),
each with a two-armed test. `opa test` gives 6/6. 388-390 are declared unmeasured in W206-gen (`_FN_ATTRS`): they read
`resorts.population`, `.skipped` and `.producer_population`, attributes the function stamps on itself, which the capture
never keeps.

    admitted=4 denied=0 unmeasured=3   (4 passed, 3 xfailed in 585.33s)

Durations: 384 296.25s (cold), 385-387 0.11s (warm), 390 288.47s (the second fixture's cold walk). Finding: pytestspec
still RUNS the implementation for an `unmeasured` case, so 390 costs about 290s for a verdict fixed in advance. Skipping
the impl for a declared disposition would halve this mode.

## W227 — skipping --impl for a declared case conflicts with stale-declaration detection (NOT landed)

Short-circuiting `SpecItem.runtest` for `disposition: unmeasured` would save resorts 390's ~290s. It would also silently
retire `test_declared_unmeasured_that_passes_fails` (pytestspec/tests/test_plugin.py:149). Strict xfail over a REAL
evaluation is the only thing that notices a declaration gone stale (the capture repaired, the case now admitted). Under
a short-circuit, a declaration can never be refuted.

Two defensible shapes, both preserving the other side as an explicit mode:

- (a) default evaluates (today's behavior, refutable); an opt-in `--skip-declared` makes a fast run that says so in the
  differential line (`declared-skipped=N`).
- (b) default skips (cheap read by default, per plan §8b); an opt-in `--recheck-declared` runs them strictly.

The invariant under both: a skipped declaration must be COUNTED as unchecked, never folded into `unmeasured` as though
it had been evaluated. This is the operator's call; nothing changed in pytestspec.

## W228 step 1 — what the reference callees read beyond their operands

`.claude/design/W228-reads.py` lists every distinct callee in the W206 case files and which ambient inputs its OWN body
names (it does not follow helpers, so `-` means "none in the body", never "reads nothing"). 92 callees:

- ambient input: default corpus (`py_files`/`_roots`/…); callees: 33; note: values, scan, reifies, shape_sites,
  commentary_census, ambient, resorts, rivals, … the whole query/census family
- ambient input: subprocess; callees: 1; note: `commentary_lost` (git): reads repository history, so no file digest
  covers it
- ambient input: UNRESOLVED; callees: 11; note: the W212 misresolved callees (`__init__`, `<genexpr>`, `check`,
  `get_or_assign`, …); already declared unmeasured
- ambient input: none named in own body; callees: 47; note: may still reach the corpus through a helper

Missed signal, recorded rather than patched: `resorts`' `_PRODUCER_CACHE` is not matched by the `cache` signal
(exact-name match). The body scan under-reports.

What this means for the key: a third of the callees read the default corpus, which is substrate's scratch tree. A sound
key is `fixture + operands + origin module sources + corpus digest`, and `commentary_lost` is uncacheable (git state).
The corpus sits outside this workspace, so a Bazel action cannot declare it as an input without a `local_path`
repository over a live tree, which is exactly the unhermetic input `.bazelrc` refuses. Recommendation: a
content-addressed result cache on the pytestspec side first, keyed as above, with every stored result naming its key.
Bazel actions can come later, if the corpus becomes a declared, digested input.

## W392 — rivals judged (W393–W395)

`W206-cases/rivals.rego` judges 34 of the 35 rivals/scan/dead/sqlname/argv cases
(`_pycodemod_selftest.py:400-622`), in three batches. Each rule restates the origin's own check
against the captured rows, which are real only with libcst present (W347, W348):

- **A (W393):** the rivals verdicts (031), dead `g` (034), eleven defs kept alive by a value use
  (041–044, 046–048, 051–054), and three anti-silencing guards that a dead def must still read
  dead (045, 049, 055);
- **B (W394):** no scan row is a `call` for a comment, a string-invoked query or a value use (033,
  035, 064, one rule); the sqlname def and ref rows (036, 037); both spellings agree (038); the
  kinds are `{def, ref}` (039); an unreferenced query has `[def]` alone (040); the registrar is
  reached exactly once (050); the value use is a `ref` at line 13 (065);
- **C (W395):** a bare prefix is not a framework contract (056); the exemption names `libcst` (057);
  `--` ends the flags, delivers its tail, and keeps the mode before it; with no `--` every token
  stays flag-visible; `--` at argv[0] is not the marker (058–063).

**032 stays withheld, by reason:** its origin check computes distinct SIGNATURES with its own
`ast` walk, and the captured `rivals()` result does not carry them.

`opa test` gives **11/11** (an admitted arm and a denied arm per batch, plus the withheld arm).
F-arms: 065 planted to `[12]` gave 7/9; 058 inverted gave 9/11; each restored to green. Run in
`scratchpad/w348-venv` with `PYTHONPATH=substrate/scratch`:

```text
pytestspec: rivals.rego impl=reference admitted=34 denied=0 refused=0 withheld-expected=0 unmeasured=1 do-not-port=0 port-fix=0 declared-skipped=0 cached=0
```

## W416 — every in-scope mode specced: the reference tally (2026-10-02)

Each W127 in-scope mode now has a Rego spec in `W206-cases/` (`<mode>.rego` + a two-armed
`<mode>_test.rego`). One run of the 21 fast specs, `--impl reference`, in the durable reference
venv `W206-cases/.venv` (`reference-requirements.txt`: libcst 1.9.0 and sqlalchemy 2.0.51, both
pinned to substrate's own venv), with `PYTHONPATH=substrate/scratch`:

    25 failed, 190 passed, 21 xfailed in 29.05s
    (the 25 failures are 24 withheld-with-reason + 1 denied; none is an unexplained red)

| mode | spec waypoint | admitted | denied | unmeasured | note |
|---|---|---|---|---|---|
| rivals | W390-W395 | 34 | 0 | 1 | 032 withheld: origin checks its own signature walk |
| values | W396 | 27 | 0 | 6 | 5 declared (W222); 084 sticky |
| the-commentary-census | W213-W220 | 28 | 0 | 10 | declared (W215/W219/W220) |
| binding | W397 | 13 | 0 | 8 | 212-215 `_DERIVER` constant; 216-219 live tree |
| reifies | W398 | 11 | 0 | 2 | 382/383 fn attrs (W399) |
| ambient | W400 | 8 | 0 | 2 | 407 constant, 408 fn attr (W399) |
| shape | W401 | 9 | 0 | 0 | |
| asserted | W402 | 7 | 0 | 1 | 073 judges two calls, capture keeps one |
| funcnames | W403 | 6 | 0 | 2 | 397/398 fn attr (W399) |
| aliases | W404 | 5 | 0 | 2 | 141 sibling fixture lost (W405); 144 sticky |
| size | W406 | 7 | 0 | 0 | |
| state | W407 | 6 | **1** | 0 | 225 = the origin's own FAIL, reproduced |
| literal | W409 | 7 | 0 | 0 | |
| swallows | W410 | 1 | 0 | 5 | declared (W222) |
| crossings | W411 | 5 | 0 | 0 | needed the adapter to materialize iterators |
| key | W412 | 5 | 0 | 0 | |
| source | W414 | 4 | 0 | 0 | |
| importers | W415 | 4 | 0 | 0 | |
| py-files | W417 | 0 | 0 | 4 | replay walks the live corpus (W418) |
| preamble (losslessness) | W419 | 3 | 0 | 1 | 001 declared (no mode call) |
| f5 | W420 | 0 | 0 | 1 | no mode call; driver concern |
| **21 fast specs** | | **190** | **1** | **45** | 236 cases |
| resorts (slow, W226) | | 4 | 0 | 3 | ~10 min; measured once |
| **all ruled modes** | | **194** | **1** | **48** | **243 cases** |

The `guarded` spec lives in `W196-spec/` and runs both implementations (W205/W210); it is not
in this tally.

### Findings about the origin (for W107's letter)

- **225, the memo case, is the origin's one known FAIL and the reference reproduces it.** The
  spec states the origin's check truthfully and the reference is DENIED on it: `_DAG` moved to
  an import site when `split_pipeline` was decomposed, and `module_state` declines to classify
  an import. A spec that admitted it would hide the origin's own red. W408 declares it
  `expect.deny`.
- **121's name and assertion disagree.** "--source finds a class as well as a function" asserts
  only that a name in a nonexistent file yields nothing; no class is in the fixture. The class
  claim is untested in the origin. The spec rules what the assertion measures.
- **The capture, not the origin, explains every other unmeasured row**: latest-call-only
  (sticky: 073, 084, 144, 154-156), dropped `*args` and temp trees (py-files; W189 has them,
  W418 regenerates), lost sibling fixtures (141, W405), and attributes or module constants no
  call returns (212-215, 382/383, 397/398, 407/408; W399 declares them).

### Instrument repairs this arc forced

- `conftest.normal` now materializes iterators (W411): `crossings` returns a generator, and its
  repr (`<generator object ... at 0x...>`) had been serialized as the result. All prior specs
  re-run unchanged.
- The reference venv moved out of the session scratchpad to `W206-cases/.venv` (git-ignored by
  `.venv/`): luthen's reaper evicted the scratch venv's `pyvenv.cfg` and editable `.pth` finders,
  after which pytest ran from the system site-packages and never saw `--impl`.


## W208 — the per-mode differential table and the ported count (2026-10-02)

Both implementations over the 20 fast specs, the same command, from the tracked home
`pycodemod/differential/` (after a70989c's declared outcome map; per-spec lines unchanged by it).
`ref` is `--impl reference` (the origin), `sub` is `--impl subject` (the port). `dnp` is declared
do-not-port: deselected under the port, still run under the origin (03fac34). `unm` is unmeasured
(withheld by the spec, or declared).

| spec | ref admitted | sub admitted | dnp | ref unm | sub unm | note |
|---|---|---|---|---|---|---|
| aliases | 6 | 6 | 0 | 1 | 1 | 144 withheld under both |
| ambient | 8 | 8 | 0 | 2 | 2 | 407, 408 withheld |
| asserted | 7 | 7 | 0 | 1 | 1 | 073 withheld |
| binding | 13 | 10 | 0 | 8 | 11 | 209-211 wait on `_cached_defs` (W480); 212-219 withheld under both |
| crossings | 5 | 5 | 0 | 0 | 0 | |
| f5 | 0 | 0 | 0 | 1 | 1 | 133 withheld by design |
| funcnames | 6 | 5 | 1 | 2 | 2 | 396 do-not-port (`portable`) |
| importers | 4 | 4 | 0 | 0 | 0 | |
| key | 5 | 5 | 0 | 0 | 0 | |
| literal | 7 | 7 | 0 | 0 | 0 | |
| preamble | 3 | 3 | 0 | 1 | 1 | 001 has no call |
| py-files | 4 | 0 | 4 | 0 | 0 | 107-110 do-not-port (no corpus enumerator) |
| reifies | 11 | 11 | 0 | 2 | 2 | 382, 383 withheld |
| rivals | 34 | 29 | 5 | 1 | 1 | 036-040 do-not-port (`sqlname`); 032 withheld |
| shape | 9 | 9 | 0 | 0 | 0 | |
| size | 7 | 7 | 0 | 0 | 0 | |
| source | 4 | 4 | 0 | 0 | 0 | |
| state | 6 | 6 | 0 | 0 | 0 | +225 refused under both: the origin's own known red |
| swallows | 1 | 1 | 0 | 5 | 5 | 009-013 declared unmeasured (W212) |
| values | 27 | 27 | 0 | 6 | 6 | 084 withheld |
| **total** | **167 (+1 refused = 168 passed)** | **154 (+1 refused = 155 passed)** | **10** | | | |

### The ported count

Of the 168 cases the origin passes, the port passes **155**, and the other 13 are accounted
for case by case, none unexplained:

- **10 declared do-not-port**, each with a reason the port itself records (cli.py
  `_DO_NOT_PORT_NAMES`): rivals 036-040 (`sqlname`), funcnames 396 (`portable`), py-files
  107-110 (no corpus enumerator; every port mode takes explicit paths).
- **3 pending**: binding 209-211, waiting on a port counterpart or a declaration for
  `_cached_defs` (W480).

No case is DENIED under either implementation: on every judged case the port agrees with the
origin. 155 + 10 + 3 = 168.

### Scope, stated so the count is not read wider than it is

- The 3 slow specs (resorts, fingerprint-own-module, the-commentary-census) are specced and
  run under the reference but were not run under the subject in this table.
- 12 modes have case data and no spec yet (artifacts, check-contracts, control, guarded,
  mode-opt-key-collision, mode-writes, projects, relalg, relname, snapshots, split, sql);
  several back do-not-port modes. They are outside both counts.

### Where it came from

The subject side was built by the swarm's five translator batches, each card's F-arm re-run
here before landing: de1d4fd (tq3), 710d043 (tq2), 5447a09 (tq1), 0102a4e (tq4), 6b394dc (tq5).
The harness became tracked in bebafd7..33a17aa (W465) and gate-reached in 6e7fd2c and 5cf82d5.
