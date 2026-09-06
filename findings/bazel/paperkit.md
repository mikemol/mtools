# Bazel findings — paperkit

**Repo:** paperkit · **Date:** 2026-09-05 · Companion to `mtools.md`.
Every figure re-derived here; where one came from another repo it is marked and attributed.

---

## 1. ⚑⚑⚑ NOBODY IS ON THE SANCTIONED CONFIGURATION, AND THE HALVES ARE COMPLEMENTARY

The sanctioned configuration is **remote BES + cache, no local fallback**. MEASURED across two
repos today:

| repo | BES | executor / cache | on sanctioned config? |
|---|---|---|---|
| **paperkit** | `--bes_backend=grpc://127.0.0.1:31985` | **none** | ✗ — BES without executor |
| **cassian** | **none** (grep over `.bazelrc` + `.githooks/pre-commit`: zero hits) | `--remote_executor=…:31985` | ✗ — executor without BES |

⚑ **Two repos hold complementary halves of one configuration and each believed it was configured.**
Neither could have discovered this alone: paperkit's flags look right in isolation, and so do
cassian's. It surfaced only when a third party asked one repo to send the other its docs.

**Measured off the LIVE PROCESS, not the config file** — `ps -o args=` on the running `//:hook`:

```
--config=mutant --bes_backend=grpc://127.0.0.1:31985 --bes_upload_mode=fully_async
build:mutant --experimental_use_hermetic_linux_sandbox      <- ONE LINE. That is the whole config.
```

⚑ **`--config=mutant` pulls in neither `cas` nor `remote`.** The name suggested a mutation-sweep
configuration carrying the remote setup; it carries a sandbox flag. *Reading the config file would
not have shown this — the flags arrive from three places (rc config, `PAPERKIT_BES` in
`.githooks/local.env`, the hook's own command line) and only the process has all three.*

## 2. ⚑⚑ THE DOCS DO NOT EXIST — a capability nobody can find is absent

The operator directed paperkit to cassian for RBE/BES documentation. Cassian looked rather than
answering from memory: `find docs/ -iname '*rbe*' -o -iname '*buildbuddy*' -o -iname '*bes*' -o
-iname '*remote*'` returns **two plans and no how-to**. The configuration lives in `.bazelrc`
comments and in cross-session messages.

**Consequence, measured rather than argued:** cassian **cannot answer** what the invocation-record
interface gives, because they have never run BES. The one question that most needed an experienced
answer had no one to answer it, and neither party knew that until asked.

## 3. THE FLAG SET (cassian's, read from their `.bazelrc`; attribution caveat below)

```
build:remote --remote_executor=grpc://127.0.0.1:31985
build:remote --remote_instance_name=cassian-gate
build:remote --extra_execution_platforms=//tools:cassian_gate_platform
#            NO --remote_local_fallback  — absent entirely, not set false
```

- **Executor only**, no separate `--remote_cache`; the executor's CAS is what it gets.
- **`--remote_local_fallback` is ABSENT, not false.** Their comment: *"an action routed to RBE runs
  ON the executor or FAILS LOUDLY, never degrades to a local escape"*, with the cost stated —
  `--config=remote` hard-depends on the executor being up.
- **`--remote_instance_name` differs per repo** (`cassian-gate` vs paperkit's `paperkit`), so the
  CAS partitions differ. Consistent with linux-sources' finding that it partitions at the server's
  **storage layer** while **not** being in the action key — both true, and mtools and linux-sources
  initially got this wrong in opposite directions.

⚑ **ATTRIBUTION CAVEAT, carried because it was volunteered against interest.** That line's comment
cites an *"(operator ruling 2026-09-04)"*. linux-sources swept 399 files / 173,842 envelopes and
found **zero** operator statements behind it — the input said *"the operator picks the fix from your
per-arm data"*, the output said *"must be removed under the ruling"*. **The input said the operator
WILL decide; the output said they HAD.** The decision is right on its merits and three repos'
independent reasoning corroborates it; **the attribution is unwitnessed.** *(Checked here: paperkit's
`.bazelrc` makes no operator attributions — `grep -nE "operator (ruling|said|decided|asked)"`
returns nothing.)*

## 3b. ⚑⚑ COPYING THE FLAG SET IS NOT ONE CHANGE — paperkit declares ZERO execution platforms

MEASURED before queueing `Ζ·config·remote`: `grep -rn "extra_execution_platforms\|platform("` over
`.bazelrc`, `BUILD.bazel` and `tools/BUILD.bazel` returns **nothing**. Cassian's third line is
`--extra_execution_platforms=//tools:cassian_gate_platform`; paperkit has no analogue.

```
build:remote --config=cas
build:remote --remote_executor=grpc://127.0.0.1:31985
build:remote --remote_local_fallback=true            <- to be removed
build:remote --remote_instance_name=paperkit
                                                     <- NO platform line
```

⚑ **So paperkit's `--config=remote` resolves against the DEFAULT host platform**, and removing the
fallback exposes whatever that resolves to rather than a declared one. This is the same dependency
that killed linux-sources' remote config at analysis for weeks — *their* platform existed and was
**bare** (no `constraint_values`, satisfying no toolchain); paperkit's does not exist at all. Two
different failure modes, one prerequisite.

⚑⚑ **The lesson is about the copy, not the flags: `--remote_local_fallback` is what makes the other
three lines' correctness UNOBSERVABLE, so it must come off last, not first.** Removing it before a
platform is declared converts a silent degradation into a hard analysis failure — which is the
*point*, but it is a different change than "adopt the sanctioned config", and sequencing it as one
step would have produced a red gate attributed to the wrong cause.

## 3c. ⚑ THE RBE BLOCK INDEPENDENTLY DOCUMENTS THE EXECROOT ESCAPE

`.bazelrc`'s remote-execution rationale, verbatim, on why a copied rootfs is worth switching to:

> *"unlike Bazel's local sandbox, which symlinks first-party packages straight back to the working
> tree (measured this session: `$EXECROOT/paperkit` is a symlink to the live checkout, which is how
> a check could read UNSTAGED sources and pass)."*

**Two independent routes to the same defect** — the sandbox measurement that motivated the staged
wheel work, and the RBE rationale written for a different purpose. The containment property is the
reason RBE was adopted; the wheel is the reason the *local* tier stops needing it. ⚑ **They are the
same finding reached from opposite ends, and neither cites the other.**

## 4. ⚑⚑ `--remote_local_fallback` IS THE THING THAT HIDES A MISCONFIGURATION

paperkit sets it on **both** remote configs (`.bazelrc:247`, `:283`), justified as *"a cache/executor
that is DOWN must not fail the build."*

**MEASURED by linux-sources:** `--config=remote` died at **analysis** for weeks — a bare
`platform()` with no `constraint_values` satisfies no toolchain — and returned **GREEN with zero
remote actions** the entire time. *The fallback was not a safety net; it was the thing hiding a total
failure.*

> **A flag that degrades silently converts a configuration error into a passing build.**

⚑ And the class is self-applying: the fallback is precisely what would have kept paperkit from
noticing it was not on the sanctioned config. *(paperkit has no `platform()` targets at all, so the
bare-platform instance cannot bite here — but the class is about the fallback, not the platform.)*

## 5. ⚑⚑⚑ EXIT-CODE-AS-VERDICT — four faces, all measured in one session

Reading a build's outcome from a wrapper's status rather than the payload's own verdict:

| face | measured |
|---|---|
| wrapper 0 over payload FAIL | notification said `exit code 0`; log line said `[pre-commit] FAIL: hook-index` |
| wrapper 0 over **no verdict line at all** | run ended with neither `ok:` nor `FAIL:` emitted |
| pipe-tail | `timeout 300 … \| tail -5` → `Terminated`, exit **0** from `tail`, no artifact built |
| **static log read as finished** | log quiescent → declared complete; run was mid-analysis and ran **8 more minutes** |

⚑ **The fourth is the dangerous one and it is unfixable by better tailing:** *a log going quiet is
indistinguishable from a log that ended.* Acting on it, paperkit **edited `tools/wheel.py` 70
seconds into a live `//:hook`** — the input-dependency-modified corruption class, self-inflicted,
by the session that had spent the day measuring that class.

**The correct liveness test is not the log and not `pgrep -c`** (which returned 0 at the top of the
tick, correctly, before the build was launched) — it is `ps` on the **pid holding the Bazel server
lock**, which the server names in its own "Another command is running" message. ⚑ **A queryable
invocation record with a TERMINAL STATE fixes this by construction rather than by discipline**,
which is the argument for the sanctioned config that has nothing to do with speed.

## 5b. ⚑⚑⚑ THREE REPOS, THREE DIFFERENT PARTICIPATION FAILURES — and paperkit's is the quietest

mtools reported theirs and asked whether paperkit had it. **Paperkit has a third variant, verified
here.** All three share a shape: *the flags are present somewhere, and the path actually taken does
not use them.*

| repo | how participation was lost | signal available |
|---|---|---|
| mtools | cache + BES behind `--config=cache` / `--config=bes`; hook invoked a bare `bazel test //...` | none — measured `2 linux-sandbox`, zero remote actions |
| cassian | no BES configured at all | absence, discoverable by grep |
| **paperkit** | BES flag **reaches the command line and works**; the *results URL* is scoped to a config the gate never uses | ⚑ **none — and the events ARE arriving** |

**MEASURED, on the running `//:hook`:**

```
ps -o args=  ->  --bes_backend=grpc://127.0.0.1:31985 --bes_upload_mode=fully_async   ← present
grep "Streaming build results to:" hook2.log  ->  NOTHING, at 26 minutes elapsed
grep -iE "bes|buildbuddy|invocation" hook2.log ->  NOTHING
.bazelrc:251  build:cas --bes_results_url=http://127.0.0.1:31080/invocation/    ← ONLY under `cas`
                                                            the gate runs --config=mutant
```

⚑⚑ **Then asked the SERVER instead of the log** — `:31464/metrics`:

```
buildbuddy_build_event_handler_duration_usec_bucket{status="0",…}  1950 events, status 0
```

**BES was working the entire time.** Bazel prints the `Streaming build results to:` line *from
`--bes_results_url`*; with the URL scoped to another config, **no line is printed even though every
event streams**. So paperkit has been producing a complete, retrievable invocation record for every
gate run **and had no way to find it** — the record exists, the pointer to it does not.

⚑⚑⚑ **That is worse than mtools' variant in one specific way: theirs failed to participate and could
be caught by looking for remote actions; paperkit PARTICIPATES CORRECTLY and looks identical to a
build that does not.** There is no local evidence either way. The only instrument that distinguishes
them is the server's own counters — the ones three sessions believed unreachable (§5c).

**Fix (queued as `Ζ·bes·url`, not applied — tree frozen under a live gate):** move
`--bes_results_url` out of `build:cas` to an unconditional `build` line, so the pointer travels with
the events rather than with a config. *The arm: run the gate and confirm a `Streaming build results
to:` line appears whose invocation id resolves at `:31080`.*

⚑⚑⚑ **AND THE OBVIOUS FIX IS THE WRONG ONE — settled by reading, before editing.** The first
instinct was *"move `--bes_results_url` to an unconditional `build` line"*, symmetrical with how the
hermetic-sandbox flags were made unconditional. **That is wrong here, and the reason is this
corpus's own stale-pointer class:**

```
.bazelrc:251            build:cas --bes_results_url=…:31080/invocation/    <- config-scoped
.githooks/pre-commit:201 [ -n "${PAPERKIT_BES:-}" ] && PK_BES="--bes_backend=… --bes_upload_mode=…"
```

`--bes_results_url` only prints a URL **when a backend is actually streaming**. Unconditional, it
would ride on every invocation *including ones with no BES configured* — emitting a pointer to a
record that was never written. ⚑ **The mechanism that decides whether BES participates is line 201,
and it is already the sole owner of that decision** (`PAPERKIT_BES` is its only gate). The URL
belongs **with** that decision, not beside it.

**So the fix is one line, at the owner:**

```
[ -n "${PAPERKIT_BES:-}" ] && PK_BES="--bes_backend=${PAPERKIT_BES} --bes_upload_mode=fully_async \
                                      --bes_results_url=http://127.0.0.1:31080/invocation/"
```

⚑ **And it drags a comment with it.** Lines 222–223 justify an unquoted expansion by saying
`$PK_BES` is *"EITHER empty OR two flags"*. Adding a third makes that comment false — the
comment-that-outlived-its-code class, which this same file catalogues twice (§6, §7b). *A fix that
leaves a now-false comment behind has traded one defect for another.*

**Arm:** run the gate and confirm a `Streaming build results to:` line appears whose invocation id
resolves at `:31080`; and run a build with `PAPERKIT_BES` unset and confirm **no** URL is printed —
the F-arm for the unconditional variant that was rejected.

⚑⚑ **AND THE POINTER IS THE ONLY ROUTE — MEASURED, the API cannot substitute for it.** Probed
`:31080/api/v1/GetInvocation` while the gate ran, to retrieve the in-flight record without the URL:

```
{"query":{…}}                  -> proto: unknown field "query"          (API is LIVE, schema wrong)
{"lookup":{…}}                 -> proto: unknown field "lookup"
{"selector":{"invocationId":…}} -> rpc error: Unauthenticated desc = Auth not implemented
{}                              -> rpc error: Unauthenticated desc = Auth not implemented
```

`selector` is the correct field — the schema errors stop and an **auth** error begins. But **auth is
not implemented on this deployment**, so the programmatic route is closed. ⚑ **The record is
reachable only through the UI, which requires the invocation id that `--bes_results_url` would have
printed.** So `Ζ·bes·url` is not cosmetic: with the URL scoped to an unused config, a complete
invocation record is written for every gate run and there is **no route to it at all** — the id
exists only in a line Bazel declines to print.

## 5c. ⚑⚑ A 404 IS A MEASUREMENT ABOUT ONE ADDRESS, NOT ABOUT THE WORLD

Three sessions probed `:31080/metrics`, got **404**, and concluded the CAS counters were
unreachable. paperkit reported it; linux-sources reported it; mtools repeated it in their own file.
**Cassian checked the third NodePort. VERIFIED HERE:**

```
curl -o /dev/null -w "%{http_code}" http://127.0.0.1:31464/metrics   ->  200
grep -c "^buildbuddy_"                                                ->  9,625 metric lines
buildbuddy_remote_cache_disk_cache_duplicate_writes{cache_name="disk_cache"} 16
  # HELP Number of writes for digests that already exist.
```

The service carries **three** NodePorts — `1985:31985` (gRPC), `8080:31080` (app/UI), `9464:31464`
(prometheus). **Nobody checked the third.**

⚑ **A 404 IS A REAL HTTP RESPONSE, SO IT READS AS EVIDENCE OF ABSENCE RATHER THAN AS EVIDENCE ABOUT
ONE ADDRESS.** It looks like a measurement and functions as a fact about the world. Three vantages
took the same reading — *and the same reading taken by three vantages is still one reading.* This is
§8's count-drift finding with a status code standing in for a figure. *(mtools' framing, from
paperkit's own rule.)*

⚑ `duplicate_writes` is exactly the counter that would have settled the AC-vs-CAS question paperkit
built two clean arms for and then withdrew as bounded by access. **The instrument existed the whole
time.**

## 5d. ⚑⚑ THE GRAPH SHRANK 17% AND THE COMMENT THAT ASKED TO BE RE-DERIVED WAS NOT

`.bazelrc`'s JVM-heap ladder sizes the Bazel server's heap against the action-graph size, and its
own rung-3 note (2026-08-31) ends by naming the defect it expects:

> *"this is not '8G was wrong'; it is that the ceiling tracks GRAPH SIZE and **nobody re-derived it
> when the graph moved**. The next arc that adds modules moves it again."*

**MEASURED from a live `//:hook` (2026-09-05), which is the re-derivation that note asked for:**

```
rung 2, 2026-08-27   125,471 actions        (8G rung, measured by the author)
rung 3, 2026-08-31   152,367 configured     (12G rung; +21%, "the grid grew")
LIVE,   2026-09-05   126,657 configured     <- MEASURED HERE
```

⚑ **The graph SHRANK ~17% and the comment's prediction pointed the other way.** It anticipated
monotone growth (*"the next arc that adds modules moves it again"*), so the heap ladder is now sized
against a graph 25,710 actions larger than the one that exists. **A ratchet that only clicks upward
records a high-water mark, not a size** — and the comment is honest about the mechanism while being
wrong about the direction, which is why it survived: it reads as self-aware.

⚑⚑ **And `docs/bazel-report.md` propagates it correctly-but-unverifiably.** Its line marks the pair
*"(MEASURED-by-the-author, INFERRED-by-me from the comment)"* — an exemplary provenance tag, and
still a citation rather than a measurement. **The tag was accurate and the number was stale**, which
is the harder case: honest provenance does not make a figure current. *Cite the instrument, not the
reading — the reading has a date.*

**What this does not claim:** the shrink's cause is unmeasured. The `--local_resources=memory=6248`
budget and the sandbox tier could partition the graph differently than the runs that produced the
earlier figures. The measurement is the configured count on this invocation; attributing the delta
to an arc would be the same inference this entry is correcting.

## 5e. ⚑⚑ THE `Ζ·stamp·bytes` FIX IS SMALLER AND MORE WRONG THAN QUEUED — measured before editing

Four ticks of notes carried the repair as *"add `sha256sum $(readlink -f "$bin")` with an
absent/unhashable sentinel."* **Reading the file first changed both halves.**

⚑ **The sentinel already exists, and so does the whole pattern.** `emit()` already yields `absent`
(no such command) and `present-unversioned` (command with no banner). And the veraPDF **jar** branch
is a fully worked-out content-hash with every edge closed — **CITATION**:

> *"A shell glob needs no subprocess at all: it expands to the matches, or to the UNEXPANDED PATTERN
> when there are none — which `-f` then rejects, so **absence is tested rather than inferred from a
> swallowed error**."*

It globs rather than parsing `ls`, tests `-f`, checks `sha256sum` is available, and emits `absent`
otherwise. **So the repair is to GENERALIZE AN EXISTING LOCAL PATTERN, not to design one** — the
correct mechanism is already in the file, applied to exactly one of four tools.

⚑⚑ **And `readlink -f` is not sufficient for all three — MEASURED:**

```
pandoc     /home/mikemol/bin/pandoc  -> ELF 64-bit executable        163,589,968 B   ✓ hashable
lualatex   /usr/bin/lualatex         -> /usr/bin/luahbtex, ELF         7,142,032 B   ✓ hashable
soffice    /usr/bin/soffice          -> …/program/soffice, SHELL SCRIPT    6,621 B   ⚑ WRAPPER
```

`soffice` resolves to a **shell script that execs `soffice.bin`**. Hashing it keys on a launcher
that changes rarely while the suite underneath changes often — **the banner defect in a new costume:
a stable proxy standing in for the thing that decides the verdict.** The fix covers 2 of 3; the
third needs its own target (`…/program/soffice.bin`) or an explicit, recorded limit.

⚑ **A correction inside this measurement, worth keeping because it nearly shipped.** A first pass
read `stat -c%s` as 8 and 34 bytes for `lualatex`/`soffice` and concluded both were stubs. Those are
**symlink** sizes — `stat` measured the link, not the target. *An instrument pointed at a pointer
reports on the pointer*, which is this file's §6 defect with `stat` in place of a comment.

## 5f. ⚑⚑ THE STAGED WORK IS RED — four failures, and the corruption alibi does not cover them

The `//:hook` run gating 46 staged files reached `23 / 24 tests` after **3h55m** with **4 failed**:

```
FAIL @@+bib+paperkit_render//:gate      RED  rnd-pdf: {"verb":"cmd","verdict":"fail"}
FAIL @@+bib+paperkit_library//:adequacy RED  concept-shareable__grade: {"grade": "broken"}
                                        RED  concept-views__grade:     {"grade": "broken"}
FAIL @@+bib+paperkit_talk//:adequacy
FAIL @@+bib+paperkit_paper//:adequacy
```

⚑ **`grade: "broken"` is −1 on the ladder — CANNOT-RUN, not refuted.** A claim graded `broken`
reports that its check could not execute; it is the signature of a resolution failure, not of a
false claim.

⚑⚑ **And it is NOT the `.cellvenv` race that this same run found earlier.** MEASURED: `grep -rl
cellvenv` over every failing test log returns **0**. Two distinct causes, and the race fix does not
address either. *The convenient explanation was available and is refuted.*

**What the evidence supports and where it stops.** The staged change **relocates the library**
(`library/` → `paperkit/library/`, 8 files including `concepts.bib` and `run-witness`), and the
failing claims are declared in that moved tree with a **project-declared verb whose command is
root-relative**:

```
[checks.claim]  cmd = "sh ./run-witness {target}"
```

The script exists and is `-rwxrwxr-x` in the checkout, so the failure is not the exec-bit case the
file's own comment already documents:

> **CITATION:** *"`sh`, NOT `./` — THE WHEEL DOES NOT CARRY THE EXEC BIT. Measured: package-data
> files install as `-rw-rw-r--`, so `./run-witness` from an INSTALLED paperkit fails with Permission
> denied while working perfectly in a checkout."*

⚑ **The cause is not established, and the adequacy log does not carry it** — it records the verdict
(`{"grade": "broken"}`) and not the underlying error. Naming the relocation as the cause would be
inference; what is measured is that the failing claims live in the relocated tree, use a
root-relative command, and grade `broken` rather than `fail`.

**Consequence for the queue:** `Ζ·venv·build` cannot land as staged. `Ζ·hook·green` must re-run
regardless (the tree changed 70 minutes into this run, voiding its verdict), but the re-run now has
a **known red** to fix first rather than a hoped-for green. ⚑ *The four-hour run was not wasted: a
voided verdict still produced four real defect reports and banked ~168,000 actions of cache.*

## 5g. ⚑⚑⚑ THE BUILD FINISHED AND THE GATE DID NOT — a BES stream that never drains

MEASURED. Bazel's own final lines, in the log:

```
INFO: Elapsed time: 14420.169s, Critical Path: 149.04s
INFO: 111270 processes: 57658 action cache hit, 135 internal, 111106 linux-sandbox, 29 local.
INFO: Build completed, 4 tests FAILED, 111270 total actions
```

**The build is over.** Five-plus minutes later the gate had still not returned a verdict, and the
log had gained **0 bytes in 32 seconds of sampling**. Diagnosed by process rather than by log:

```
2183961  /bin/sh .githooks/pre-commit   S   WCHAN=do_wait      <- waiting on a child
2184518  bazel test //:hook             Sl  WCHAN=ep_poll  0%  <- blocked on the network
         children of 2184518:           NONE
         open sockets:                  1
         /proc/net/tcp6 peer 0x8743 (34627), state 01 = ESTABLISHED
```

⚑ **And the server confirms the stream is dead, not slow:**

```
buildbuddy_build_event_handler_duration_usec_count{status="0"}   2212 -> 2212   (8s apart)
```

**The connection is open, ESTABLISHED, and consuming nothing.** The only network flag on this
invocation is `--bes_backend`; `:31985` answers a fresh TCP connect. So a **completed** build is held
open by a BES stream that will not drain, and `--bes_upload_mode=fully_async` — chosen so telemetry
would not block the critical path — does not cover the *shutdown* path.

⚑⚑ **This is the run-file's `§X` executor-degradation note arriving as a gate that cannot
terminate.** That note says a degraded scheduler is *"a known environmental fact and not evidence
about your configuration"* — true, and the consequence for paperkit is sharper than the note
implies: **an environmental fault in a TELEMETRY sideline blocks a verdict the build already
computed.** The failure mode is not a lost record; it is a gate that never finishes.

⚑ **And it is the fifth face of the exit-code class**, distinct from the four already catalogued
(§5). Those were *wrong* verdicts read from the wrong layer. This is **no verdict at all, with the
answer already sitting in the log four lines above** — `4 tests FAILED` was knowable at
`t+14420s` and the wrapper was still silent at `t+14760s`.

**Immediate consequence:** the tree stayed frozen ~6 minutes longer than the work required, on a
telemetry path that is explicitly best-effort. `PAPERKIT_BES` gates participation, so unsetting it
is the available mitigation — but the correct fix is a **bounded** shutdown
(`--bes_timeout`), since a best-effort sideline must not be able to hold a verdict hostage.

## 5h. ⚑⚑ THE FOUR REDS DIAGNOSED — and the relocation hypothesis is REFUTED

§5f recorded four failures and named the library relocation as *plausible, not established*. Chased
to a discriminator; **the relocation is not the cause.**

**Two records exist per claim, and they disagree:**

```
                     __calc.calc.json    __dcalc.sens.json
concept-shareable    baseline=True       baseline=False     -> grade "broken"
concept-views        baseline=True       baseline=False     -> grade "broken"
adequacy-gap         baseline=True       baseline=True      -> grade "behavioral"   (passes)
```

⚑ `_grade_from_sens` emits `broken` on `not baseline`, and the grade cell reads the **dcalc**. So
the **file-level** sweep establishes a baseline for all three while the **definition-level** sweep
fails for exactly the two that grade broken. *One claim, two instruments, opposite answers.*

**What the relocation hypothesis predicted and what refutes it:**

- all three claims use the **same** verb (`check = {claim:<id>}`) and the same root-relative
  command `sh ./run-witness {target}` — so a path-resolution failure would break all three, not two;
- run directly in the checkout, **both** a failing and a passing claim return `rc=0`;
- `concept-shareable.verdict.json` says **`verdict: pass`** — ⚑ **the check itself passes.** The
  defect is in *grading*, not in the check.

**So `broken` here is not "the check could not run" in the ordinary sense** — it is the
definition-mutation sandbox failing to establish a baseline for two specific claims whose checks
pass everywhere else.

⚑ **And the engine already owns the distinction the artifact then discards.** `grade.py`'s
`Ζ·broken·offaxis` branch emits `baseline: "unreachable"` vs `"refuted"` plus a `why`:

> **CITATION:** *"passing `reachable=False` says WHICH, so the record stops asserting 'repo is not
> green' about a repo whose check merely could not run."*

But the published grade artifact carries **two fields**:

```
{"claim": "concept-shareable", "grade": "broken"}      <- broken
{"claim": "adequacy-gap", "grade": "behavioral"}       <- healthy, same shape
```

**`baseline` and `why` are computed and dropped at the projection.** ⚑⚑ *A distinction the engine
went to trouble to make is unavailable to the reader of the record it makes it for* — which is why
§5f could not tell cannot-run from refuted, and why the relocation hypothesis survived a tick longer
than the evidence supported. New symbol `Ζ·grade·why`: project `baseline` and `why` into the grade
record, so the discriminator survives to the artifact.

**Frontier, stated rather than inferred:** *why* the definition-level baseline fails for these two
and not the third is not established. What is established is that it is not the relocation, not the
verb, not the witness script, and not the check's own verdict.

## 5j. ⚑⚑ THE `Ζ·calc·reachable` FIX IS CORRECT AND DID NOT CLEAR THE RED — the chain had a gap

The `_run` fix (§5i) is proven at unit level — `cannot_run → flipped=False`, `refuted → flipped=True`
unchanged — and a full 47,279-action re-sweep left `library//:adequacy` **RED**, with the ∅ cell
still `flipped: true`. **The fix was necessary and aimed one hop short.**

⚑ **The ∅ record's `why` is the assertion message, not a cannot-run line**, which is the evidence
that settles it: the witness RAN and its assertion genuinely failed. So `rc` was never 3 at that
layer, and no amount of sentinel-honoring in `_run` could have changed it.

⚑⚑ **AND THE ROOT-CAUSE CHAIN IN §5i NAMED A PATH THE CELL DOES NOT TAKE.** MEASURED with
`bazel aquery`, which is the instrument that should have been used first:

```
--check paperkit/library/concepts.py      <- the eval cell runs concepts.py DIRECTLY
```

Not `run-witness`. §5i reproduced a `uv sync` failure from an extracted wheel and presented it as
the cause; **the outer invocation never touches that script.** *A reproduction is not a diagnosis
unless the path reproduced is the path taken.*

**What is actually true, re-derived:** `concepts.py` asserts a disclaimed key falls through to the
engine's library, and *that* resolve spawns `_library_cmd` → `['sh', './run-witness',
'label-carrier']` with **`cwd=_LIBRARY`**. So `run-witness` is on the path — one level deeper than
claimed, reached by the nested spawn rather than the cell.

⚑⚑⚑ **And the discriminator is `cwd`, measured:**

```
repo root : python3 -c 'import paperkit'  -> OK   (cwd is on sys.path)
/tmp      : python3 -c 'import paperkit'  -> ModuleNotFoundError
```

`run-witness`'s fast path is `if python3 -c 'import paperkit'; then exec python3 "$HERE/concepts.py"`.
From `cwd=_LIBRARY` that import **fails**, so the script falls through to the `uv sync` arm — which
fails because `ROOT=$HERE/../..` is the execroot, with no `pyproject.toml`. The script's own comment
predicts the shape: *"a path relative to a directory that moved is the same defect `_LIBRARY` had
one level up."*

**So the defect is an implicit dependency on cwd-as-import-root** — the check passes in a checkout
because the developer happens to run from the repo root, and fails wherever cwd differs. It is the
`§Q`-2 implicit-dependency class from this repo's own census leg, firing on the engine's own library.

**Kept, not reverted:** the `_run` sentinel fix stays staged. It is independently correct — a
payload's cannot-run must not read as a refutation — and it is the mechanism that will carry this
verdict *once the layer below emits the sentinel at all*. What it does not do is manufacture a
sentinel that was never raised.

## 5k. ⚑⚑⚑ Ζ·witness·cwd — CLOSED. `library//:adequacy` RED → GREEN

```
GATE GREEN: {"verb":"adequacy","verdict":"pass"}
INFO: Build completed successfully, 49473 total actions
```

**The defect, in one line:** `run-witness`'s fast path is `if python3 -c 'import paperkit'`, and a
bare import succeeds only because **CWD is on `sys.path`**. The engine's own nested resolve spawns
that script with `cwd=_LIBRARY` (`resolver._library_cmd` → `['sh', './run-witness', …]`, `cwd=lib`),
so the import failed, the script fell through to its `uv sync` arm, and *that* failed because
`ROOT=$HERE/../..` inside a sandbox is the execroot with no `pyproject.toml`.

**Fix — use the root the script already computes**, correct in a checkout *and* a sandbox:

```sh
_PK_PP="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
if PYTHONPATH="$_PK_PP" python3 -c 'import paperkit' 2>/dev/null; then
    PYTHONPATH="$_PK_PP" exec python3 "$HERE/concepts.py" "$@"
fi
```

**⟨P, F, δ⟩, run from the nested spawn's own cwd** — not from the repo root, which is what hid it:

| arm | result |
|---|---|
| F — pre-fix script, `cwd=library` | `CANNOT RUN — uv sync failed; cannot establish the witness environment` |
| P — fixed script, same cwd | `concept label-carrier: OK` |
| the failing claim, foreign cwd | `concept concept-shareable: OK` |
| gate | `GATE GREEN`, 49,473 actions |

⚑⚑ **THE COST OF THE TWO WRONG HYPOTHESES IS THE FINDING.** This took four ticks and ~3.5 hours of
sweeps, and the two dead ends were not random:

1. **§5f — "the library relocation broke a path."** Plausible, and refuted by measurement: all three
   claims share the same verb and root-relative command, and two of the three passed.
2. **§5i — "`run-witness` fails from an installed wheel because `uv sync` has no `pyproject.toml`
   ancestor."** ⚑ **The reproduction was real and the path was wrong.** `bazel aquery` shows the
   eval cell runs `--check paperkit/library/concepts.py` **directly** — it never invokes
   `run-witness`. The script *is* on the path, but one level deeper, reached by the nested resolve.
   *A reproduction is not a diagnosis unless the path reproduced is the path taken*, and `aquery`
   is the instrument that settles which path that is. It should have been the first tool, not the
   fourth.

⚑ **And the tell was in the artifact from the start.** The ∅ eval record's `why` carried the
**assertion message**, not a cannot-run line — so the witness had RUN and its assertion had failed.
That single field ruled out §5i three ticks before `aquery` did. The record was already honest; I was
reading around it.

**What stays, and why it is not a wasted fix:** `Ζ·calc·reachable`'s `_run` change (§5i) remains
staged. It is independently correct — a payload's `CANNOT_RUN` must never read as a refutation — and
its unit arm holds (`cannot_run → flipped=False`, `refuted → flipped=True` unchanged). It could not
have fixed *this* red, because the sentinel was never raised on this path. **A correct fix aimed at
the wrong layer is still a correct fix; it just is not this one's.**

## 5l. ⚑⚑ Ζ·render·gate — EIGHT REDS, TWO KINDS, AND `talk` IS ENTIRELY DOWNSTREAM

MEASURED 2026-09-06T~17:00. `render//:gate` carries **eight** reds, not the three earlier notes
recorded — six `fail` and two `cannot-run`:

```
rnd-a11y  rnd-latex  rnd-pdf  rnd-wcag  rnd-wcag-entail  rnd-widen   -> verdict "fail"
rnd-link-alt  rnd-math-alt                                            -> verdict "cannot-run"
```

⚑ **`talk//:gate` is not an independent red.** Its two claims delegate by `result:`:

```
t-a11y-claim  check = {result:render#rnd-wcag-entail}      <- cites a render claim that is RED
```

So `talk` fails *because* render does. **One fix clears two targets**, the same delegation structure
that let `Ζ·witness·cwd` clear three at once — and the dependency was established by reading the
warrant rather than by inferring from the shared subject.

### ⚑⚑⚑ THE TWO `cannot-run` HAVE DIFFERENT CAUSES, AND `aquery` NAMED THE DISCRIMINATOR

`bazel aquery` on the cell shows the verdict mapping explicitly — *this is the instrument that
should be reached for first, and this time was*:

```
( cd 'render' && sh -c 'python3 checks/linkalt.py --selftest' ) >/dev/null; rc=$?
if [ "$rc" = 0 ]; then V=pass; elif [ "$rc" = 3 ]; then V=cannot-run; else V=fail; fi
```

**So `cannot-run` IS exit 3 — the engine's declared CANNOT_RUN sentinel — and both checks are
raising it deliberately.** Neither is a crash; both are refusing to skip-green, which is the
behaviour the constitution census settled as binding (*a gate must REFUSE when its tool is absent,
never skip*). ⚑ **The reds are the engine working.**

The two causes are **not the same**, which a shared verdict conceals:

| claim | mechanism | measured |
|---|---|---|
| `rnd-math-alt` | `try: import pikepdf / except ImportError: → exit 3` (`mathalt.py:26-28`) | ⚑ `pikepdf` IS declared in `render/paper.toml` `pydeps` and IS staged into the cell venv per aquery — **host import succeeds, 10.10.0** |
| `rnd-link-alt` | `subprocess.run(["pdftotext", "-bbox", …])` (`linkalt.py:45`) | ⚑⚑ `pdftotext` is a **PATH binary**, present on the host at `/usr/bin/pdftotext`, **staged as no input and absent from the toolchain stamp** (`grep -c '^emit .*pdftotext' tools/toolchain_status.sh` → **0**) |

**Both selftests pass on the host** (`rc=0` each), so neither is a broken check.

⚑ **`rnd-link-alt` is an undeclared implicit dependency** — exactly the `§Q`-2 class paperkit filed
in its own deps-build leg (*"paperkit runs arbitrary PATH programs"*), arriving as a red. The four
stamped tools are pandoc/verapdf/lualatex/soffice; **poppler is a fifth the stamp does not know
about**, so a machine without it produces `cannot-run` and a machine with it produces a verdict
keyed on nothing.

**FRONTIER, stated rather than inferred:** *why* the cell venv fails to supply `pikepdf` when aquery
shows it staged is **not established**. Candidates not yet distinguished: the `_pydeps.pth` roots not
reaching the interpreter, the venv build racing, or the import failing for a reason other than
absence. ⚑ *The last diagnosis I shipped on this file was wrong because I reproduced a failure on a
path the cell does not take; I am not repeating that by naming a cause I have not isolated.*

## 6. A STALE CLAIM CARRYING ITS OWN VERIFICATION

`.githooks/local.env` held:

> `# indirection is right and held a dead value. BES (:1985) did NOT move; verified open.`

MEASURED: **`:1985` closed, `:31985` open, `:31080` open.** The endpoints moved with the k3s
migration and the comment did not.

⚑ **This is the worst variant of the comment-that-outlived-its-code class yet catalogued: the other
instances were assertions; this one ASSERTED ITS OWN CHECK.** A reader applying *"verify, don't
trust"* sees the word **verified** and stops. *(cassian's framing.)* Corrected in place, with the
correction visible rather than swapped.

## 7. ⚑ `Ζ·cellvenv·race` — a concurrency defect the gate found in the gate's own new code

Four `FileNotFoundError` tracebacks from four different cells:

```
FileNotFoundError: '.../execroot/_main/.cellvenv/lib'
  venv/__init__.py  clear_directory -> shutil.rmtree -> os.rmdir
  tools/wheel.py:96  venv.EnvBuilder(..., clear=True).create(vd)
```

Every cell is handed the same `"$PWD/.cellvenv"` and **sandboxed actions share an execroot**, so
concurrent cells race and `clear=True` clears a tree another is walking.

**⟨P, F, δ⟩ — both arms, same δ (6 concurrent `install` calls at one path):**

```
F  pre-fix code   ->  2/6 fail   (also surfaced a second face: PermissionError on bin/Activate.ps1,
                                  a concurrent write into a tree another process is clearing)
P  fixed code     ->  0/6 fail, marker present, zero leftover tmp dirs
```

**Fix:** build to `.cellvenv.<pid>.tmp`, write a `.pk-complete` marker, `os.rename` to claim the
shared name; the loser of the race discards its own copy rather than clobbering a venv in use.
`install` is content-determined (same wheel + deps → same tree), so reuse is sound — *action
idempotency applied to the action's own scratch space.*

## 8. FIGURES — and a filter that matters more than the figures

`"input dependency modified during execution"` over paperkit's transcript corpus:

```
91  -> 32 -> 24        (each correction itself under-corrected)
CURRENT: 24 occurrences, 6 distinct days, 15 pre-executor-cutover / 9 post
```

⚑⚑ **The filter is the finding.** Filtering on record **type** `user` still admits **peer messages
and system reminders quoting the phrase** — so the census's own correspondence about the number
inflated the number, **twice**. The correct predicate is **`toolUseResult` present on the record**.

> **A count over a corpus that includes the discussion of the count is a feedback loop — and the tell
> needs no knowledge of the right answer: the number DRIFTS UNDER RE-QUERY.**

⚑ Cite the filter, not the number. Four repos quoted 91 and then 32 without re-deriving either;
this is `mtools.md`'s Rule 9 (*cross-vantage review checks REASONING, not INPUTS*) with a third and
fourth instance.
