# Bazel declaration rules — measured in mtools

**Why this file exists.** Cache poisoning requires a *collision*, and a collision requires the
**same improper key on both sides**. A consumer receives a bad entry only by computing the same
narrow key — which means making the same omission. So a correct declaration is self-protecting,
and the shared risk is not under-declaration in general but **the omissions two parties make
identically**: the conventional ones. That makes writing measured rules down a fleet obligation
rather than documentation, and one rule below had already gone unnoticed in **two repositories at
once**.

Every claim here was measured in `~/github/mtools` on 2026-09-05, not recalled. Where a rule is
bounded, the bound is stated.

## Rule 0 — what is actually in the action key (read from source, Bazel 8.7.0)

**Two empirical derivations agreed and were both wrong in the same place.** A peer read
`ActionKeyComputer.java`, `SpawnAction.java` and `ActionEnvironment.java` and reported the
enumeration below; the parts marked **verified here** were then re-measured independently in this
repository. **Provenance is marked per line, because a relayed quote is not a read.**

**In the key:**

| | |
|---|---|
| argv / command lines | `commandLines.addToFingerprint(...)` |
| input file digests | content, not path strings |
| the mnemonic | `fp.addString(mnemonic)` |
| **`execution_requirements` / `exec_properties`** | fingerprinted **twice** — `getExecutionInfo()` and `getExecProperties()` |
| **the exec platform** | `executionPlatform.addTo(fp)` **directly**, with a boolean for null-vs-present |
| explicitly-set env | `getFixedEnv()` — by name **and value** |
| inherited env **names** | `getInheritedEnv()` — `addStrings`, **names only** |

**Not in the key:** spawn strategy and all sandbox flags · `--remote_local_fallback` ·
`--remote_instance_name` · **inherited env VALUES.**

### ⚑⚑ The correction that matters: `use_default_shell_env` keys names, not values

Both parties had believed the flag was a coarse declaration — "the flag is keyed, the env is not."
The truth is worse, because it *looks* like tracking: inherited variables enter the key **by name
only**. `PATH` changes value, the key does not move, the cached verdict is served.

**Verified here, independently of the source read.** A passing target with `env_inherit =
["PROBEVAR"]`:

```
PROBEVAR=alpha   Executed 0 out of 1 test: 1 test passes.
PROBEVAR=beta    Executed 0 out of 1 test: 1 test passes.   <- cache HIT, value differed
PROBEVAR=alpha   Executed 0 out of 1 test: 1 test passes.   <- control, identical
```

⚑ **The test never re-ran while its environment changed.** This is the mechanism behind a tier
carrying `no-cache` for host-coupled checks — and the reason to carry it is sharper than "the
machine is unpinned": the key is *actively misleading*, listing the names it does not track.

### ⚑⚑ `execution_requirements` is key material, which strengthens the collision argument

`no-cache`, `no-remote`, `no-sandbox`, `local` are all fingerprinted. **A `local`-tier and a
`sandbox`-tier action with identical argv and inputs are different actions** and cannot collide in
a shared CAS. So two repositories must share their declared inputs *and* their execution
requirements to collide at all — the safety property is stronger than stated below.

### ⚑ The method finding, which is why the read was worth the fifteen minutes it cost

Two empirical lists, from two clients against one executor, **agreed and were both wrong about
env** — because a probe shows only what varies when you vary it, and neither party had varied an
inherited variable's *value*. **Agreement between two instruments that share a blind spot is not
corroboration; it is the blind spot, twice.**

That is the shared-habit finding one level up: the bare platforms were one habit propagated by
copying, and the NOT-IN-KEY lists were one *method* propagated by both parties probing instead of
reading. The source was in the corpus the whole time, ranked as "nobody's blocker" — a claim about
who is *waiting* rather than about what *rests* on it, and Rule 3, a peer's `.bazelrc`, and the
shared-CAS safety argument all rested on it.

⚑ **Bound on this rule:** the Java source is not present on this machine. The quotes are a peer's
read of a pinned Bazel 8.7.0 corpus, relayed; the env behaviour was re-measured here and the
sandbox-flag and exec-platform lines match probes run here. **A relayed quote is corroborated, not
verified.**

## Rule 0b — audit your own actions against Rule 0, because publishing one is not following one

Rule 8 says a rule in your own file is one you already believe you are following. So this
repository was audited against Rule 0 immediately after publishing it. **Clean on the env axis,
and not clean on a larger one.**

**Env — clean, and by construction rather than by luck:**

```
env_inherit / use_default_shell_env   none    <- no action depends on an UNKEYED value
env = {...}                           2       <- explicit: keyed by name AND value
os.environ reads in src/ and tests/   PANDOC_BIN, RUFF_BIN — exactly the two declared
```

⚑ **And both of those name a binary that is itself declared `data`**, so the file's *content digest*
is in the key, not merely its path. An env var naming an undeclared file would be the misleading
case: a keyed name pointing at unkeyed bytes.

**⚑⚑ NOT CLEAN: THREE CHECKS RUN OUTSIDE THE GRAPH ENTIRELY.** `.githooks/pre-commit` invokes
`ruff`, `mypy` and the ratchet directly. Those are not actions, so they have no key, no
invalidation and no cache — they re-run in full on every commit and reuse nothing.

| check | in the graph? | keyed on |
|---|---|---|
| 25 pytest targets | yes | declared inputs |
| stubtest | yes (inside a target) | declared inputs |
| **ruff** | **no** | **nothing** |
| **mypy** | **no** | **nothing** |
| **ratchet** | **no** | **nothing** |

⚑ **This is not the same defect as an under-declared action, and it is worth keeping distinct.** An
under-declared action has a key that is *wrong*; a check outside the graph has **no key at all**.
The first serves a stale green; the second can never serve anything, which is safe but is also why
it costs full re-execution forever. The repair is the same — make it an action and declare its
domain — but the failure it currently exhibits is cost, not incorrectness.

### ⚑⚑ And the three do not have the same domain, which decides how each is repaired

The same one-line experiment separates them. Break a return type in `ast.py`, which `spans.py`
imports, and ask each checker about **`spans.py`**, the file that was not edited:

```
mypy   spans.py   Found 1 error       <- verdict CHANGED; domain is f + closure(f)
ruff   spans.py   All checks passed   <- verdict UNCHANGED; domain is f alone
```

| check | domain | hand-writable? | repair |
|---|---|---|---|
| ruff | the file, its config, the binary | **yes** | an ordinary action per file or per distribution |
| ratchet | the census output + its baseline | **yes** | an ordinary action |
| **mypy** | **`f` + transitive import closure** | **no** | needs the closure computed — Rule 6 |

⚑ **That is the discriminator, made concrete rather than argued.** Two checkers over the same
tree, one whose domain a human can write down and one whose cannot — and the second is the one
that needs a generator. A repository decides whether to build custom rules by running this
experiment per checker, not by counting targets.

## The frame: every action must be Π-typed

An action's output type *depends on* its inputs, so the declared inputs must be the full domain
the verdict ranges over. **The cache cannot be improper if the cache keys are proper.** A wrong
verdict is never a cache that misbehaved — it is an improper key, the cache faithfully serving a
function nobody meant.

Four defects found here in one session were one shape, differing only in what escaped the domain:

| action | declared | actual domain |
|---|---|---|
| a lint-arm test | staged sources | + the author's host `.venv`, via `resolve()` |
| pandoc-marked cases | the test module | + a host binary, else a silent skip |
| `mypy(f)` | one file | + its transitive import closure |
| any action | its inputs | + the whole source tree, pre-hermetic |

The two repairs are not alternatives. **Widening the declaration** makes the domain match the
function; **narrowing what is reachable** makes the function unable to exceed its domain. An
undeclared dependency that cannot be reached is one that cannot be forgotten.

## Rule 1 — a dropped bin is not a wall; measure before reaching for http_archive

`rules_python` stages only `site-packages` and drops a wheel's `bin/`. The general fix is
`@rules_python//python/entry_points:py_console_script_binary.bzl`, which **regenerates** the
console script from the wheel's own `entry_points.txt`. The discriminator is one command:

```python
importlib.metadata.distribution(X).entry_points   # -> console_scripts group
```

Measured here:

```
ruff     []                                            + bin/ruff is an ELF executable
mypy     ['dmypy','mypy','mypyc','stubgen','stubtest']
pytest   ['py.test','pytest']
```

⚑ **So `http_archive` was correct for ruff and wrong as a habit.** There is no entry point to
regenerate. For any tool that declares one, the launcher is the instrument — and it must be
consumed through `ctx.actions.run_shell(tools = ...)`, never `inputs = ...`, or the launcher
cannot find its `.runfiles/` tree.

⚑ **And a launcher is not automatically an improvement.** `stubtest` was evaluated against this
rule and *declined*: running the console script directly still writes `.mypy_cache` relative to
cwd, so the writable-cwd workaround is a property of the tool rather than of how it is invoked,
and `mypy` was already a declared dependency. The rule says when a launcher is *necessary*, not
when it is available.

## Rule 2 — sandbox flags are not in the action key, so hermeticity cannot be a config

Measured, both directions:

```
run WITHOUT the hermetic flags   -> caches a green verdict
same target WITH them            -> "Executed 0 out of 1 test: 1 test passes"
```

The verdict **crossed the boundary unexecuted**. The key is a checksum over declared input bytes,
and a sandbox flag changes what an action can *reach* rather than what it *declares*.

⚑ **An opt-in hermeticity flag is therefore not hermeticity** — it is a regime a cache hit
silently bypasses. These must be `build` lines, never `build:<config>`.

What they buy, probed in both arms: without them a "hermetic" action reads
`…/hooks/.venv/bin/ruff` and the whole source tree; with them neither exists.

⚑ **The predicted breakage is workload-specific and must be measured, not inherited.** A peer
measured this same flag as *broken*; the discriminator is whether a check needs writable scratch
at a **host path outside the execroot**. Eight of 25 modules here touch temp paths — 90 references
— but through pytest's `tmp_path`, which lives *inside* the sandbox. 25 of 25 pass. Adopting on
the peer's verdict would have been wrong; **so would declining on it**, which is the half easier
to miss.

## Rule 3 — a bare platform resolves no toolchain, unconditionally

Two repositories carried `platform(name = ...)` with empty `exec_properties` and no
`constraint_values`, each believing it worked. Measured here:

```
Error in fail: Unable to find a CC toolchain using toolchain resolution.
Target: @@rules_cc+//cc:current_cc_toolchain, Platform: @@//rbe:mtools_gate_platform
```

…and independently in linux-sources, on a *python* toolchain. **Same defect, different gate
announcing it.** A platform declaring nothing satisfies no toolchain's constraints; only *which*
toolchain complains first is graph-dependent.

Both halves are required:

```python
bazel_dep(name = "platforms", version = "0.0.10")   # transitive is NOT visible under bzlmod
constraint_values = ["@platforms//os:linux", "@platforms//cpu:x86_64"]
```

⚑ **And `--remote_local_fallback` is why it went unseen.** In the peer's repo it caught the
analysis failure and returned **green with zero remote actions**, for weeks. Removing it was not
hygiene — it was the instrument that made the defect measurable. A guard removed for being wrong
also removed the thing hiding a defect.

## Rule 4 — arm a remote claim against a dead port, with caches disabled

A stale action cache produces a pass byte-identical to a real remote landing. The first attempt at
this arm here reported `3 action cache hit`; the peer's reported `12 action cache hit` at a dead
port — **green twice, having never contacted the executor**.

```
dead port, --disk_cache= --noremote_accept_cached
  -> Failed to query remote execution capabilities: Connection refused
real port, same conditions
  -> 3 of 3 tests pass
```

## Rule 5 — an instance-name probe needs a never-used name and a control arm

⚑⚑ **AN EARLIER REVISION OF THIS RULE SAID THE INSTANCE NAME DOES NOT PARTITION. THAT WAS WRONG,
AND IT WAS WRONG BY EXACTLY THE FAILURE RULE 4 DESCRIBES.** Two arms, no `bazel clean` between
them, and the `OTHER` arm hit on entries it had populated itself in an earlier run of the same
session. A peer challenged it with a control, and re-measured here it reverses.

The honest form is four arms, `bazel clean` before **every** one, `--disk_cache=`, and a name that
has **never been used**:

```
1  default name,      clean first   -> 2 remote cache hit
2  FRESH name,        clean first   -> 2 remote          (RE-EXECUTED)
3  same fresh name,   clean first   -> 2 remote cache hit   <- CONTROL
```

Arm 3 is what makes arms 1–2 evidence: it proves the probe **can** detect a hit, and it did not
detect one across the namespace boundary. **`--remote_instance_name` partitions.**

⚑ **A reused "other" name measures nothing** — it hits on its own history. And an arm run without
a clean can report `1 internal`, which is green and is not a measurement at all. Both parties
produced one of these while writing this rule.

**Two layers, and only one of them was ever a question.**

- **The action cache** maps `action key -> result`. That mapping is what `--remote_instance_name`
  partitions, and the arms above measured it.
- **The CAS is content-addressed, so sharing is DEFINITIONAL.** A blob lives at the hash of its own
  content; a namespace cannot change what `sha256(x)` is. There is nothing there to partition.

⚑⚑⚑ **AN EARLIER REVISION CARRIED THIS AS AN OPEN "AC-vs-CAS SPLIT". IT WAS NOT OPEN — IT WAS
MALFORMED, AND THE FAILED PROBE THAT TRIED TO SETTLE IT WAS THE EVIDENCE.** A peer ran two clean
arms with fresh instance names, captured execution logs (10.087s vs 8.605s; a 27-byte delta that is
invocation IDs), went looking for server-side CAS byte counters, hit a `404`, and reported the null
as a bound on **access**. It was a bound on the **question**. "Re-uploaded" and "deduplicated" are
not two states of a content-addressed store — the entry at `sha256:abc…` is the same bytes either
way. Whether one client put those bytes on the wire again is a fact about **one connection's
traffic**, not about the cache.

⚑⚑ **AND "BOTH TRUE OF DIFFERENT LAYERS" WAS TOO GENEROUS TO BOTH OF US.** It sounded like two
findings meeting in the middle. It is one finding and one definition: the action-cache measurement
was right, the content-addressing argument was right, and they were never in conflict.

⚑⚑⚑ **POSTSCRIPT: THE COUNTERS WERE REACHABLE ALL ALONG — THREE SESSIONS PROBED THE WRONG PORT.**
`:31080/metrics` returns `404`, reproduced independently by three parties, and all three inferred
the surface did not exist. **It is on `:31464`.** The service carries three NodePorts — `1985:31985`
gRPC, `8080:31080` app/UI, `9464:31464` prometheus — and nobody checked the third. Measured here:
**9,537 metric lines**, including

```
buildbuddy_remote_cache_disk_cache_duplicate_writes
  # HELP  Number of writes for digests that already exist.
buildbuddy_remote_cache_upload_size_bytes_{bucket,count,sum}
buildbuddy_remote_cache_download_size_bytes_*
```

⚑ **A 404 LOOKS LIKE A MEASUREMENT AND FUNCTIONS AS A FACT ABOUT THE WORLD.** It is a real HTTP
response, so it reads as evidence of absence rather than as evidence about *one address*. The
earlier framing — *"a fact about access, not about the CAS"* — was the right instinct and still
landed wrong: it was a fact about **the port**. This is Rule 9 with a status code standing in for
a figure, and *the same reading taken by three vantages is still one reading*.

The withdrawal stands on its own terms — content addressing makes sharing definitional — but
`disk_cache_duplicate_writes` is exactly the counter that would have settled the original question,
and it was available the whole time.

⚑ **THE TRANSFERABLE RULE: a null result from a well-run probe is evidence the QUESTION is wrong at
least as often as it is evidence the ACCESS is short.** Rule 7 protects against a *contaminated*
arm. It does nothing against measuring a distinction the substrate cannot express — those arms were
clean, the control was sound, and the apparatus was pointed at a non-difference. **Ask what would
DIFFER before building the arm.** If the answer is "the same bytes at the same address," there is
no arm to build.

⚑ Neither party caught this; both were inside the question. It came from outside the pair.

**The exec platform *does* participate** — through toolchain resolution rather than as a string.
It selects *which* toolchain, and the resolved toolchain's files are inputs.

## Rule 6 — mypy reacts to transitive dependencies, so per-file keys must carry the closure

Measured with one edit:

```
spans.py alone                                Success: no issues found
break a return type in ast.py (imported by spans.py):
  ast.py                                      Found 1 error
  spans.py  (NOT EDITED)                      Found 1 error
```

The unchanged file's verdict flipped. A per-file action keyed on only its own file serves a
**stale green** the moment a dependency's signature changes.

⚑ **And this is why the peer repositories carry so much custom Bazel and Bazel-generation code.**
A stock rule cannot express a *computed domain*: `py_test` takes a `srcs` list a human wrote, while
`mypy(f)` ranges over `f + closure(f)`, derived from the source. No hand-written list can state it,
and any that tries under-covers the moment an import is added. **The trigger for building a rule is
a computed domain, not a target count** — a repository whose every check has a hand-writable domain
is not one that needs no custom rule; it is one that has not yet met a computed one.

⚑⚑ **THE CLOSURE MUST BE COMPUTED, NOT GLOBBED, AND THE FALSE-COMPLETE CASE IS THE DANGEROUS ONE.**
A peer shipped and fixed exactly this: `from pkg import submodule` staged only `__init__.py`, so a
per-file action was keyed on a closure that *looked* complete. It surfaced as
`Module "linux_sources" has no attribute "corpus_census"` only once a sandbox tier arrived — the
host-tier reader had the whole tree present and hid it for weeks. **A closure that is wrong in the
direction of too-small is a stale green; the sandbox is what converts it into an error.**

**Calibration, measured by that peer — and stated precisely, because the figure already in
circulation is wrong and imprecision is how it got that way.** Two distinct measurements of two
distinct things:

```
gen_gate_build.py --check   5.60s, 40MB maxrss, cold   <- computing the DOMAIN
bazel query kind(pk_cmd)    2,254 targets
full gate, cold on executor 267 processes, 317s        <- BUILDING them
```

They are jointly meaningful only as **"computing the domain for 2,254 targets costs 5.6s."** Two
other repositories' records cite *"430 fine targets"* — five times low — and built cost arguments
on it.

⚑ **Provenance, per Rule 9:** these three numbers are that peer's own measurements of its own tree,
run at the time of writing. **This repository has not re-derived them**, and they are load-bearing
only for the claim that a generator is cheap — not for anything in mtools' own configuration.

⚑ **The number that answers "does a computed domain earn a generator" is the 5.6s, not the 317s.**
The build cost is what the checks cost; the generator cost is what *knowing their domains* costs.
Conflating them is how a cheap generator gets declined on the price of the work it enables.

## Rule 7 — an RBE arm is not a measurement until the output base is cleaned

**Three independent instances in one day, by two parties:**

- a peer's dead-port probe reported `12 action cache hit` — green, never contacted the executor
- that peer's *own* instance-name arm reported `1 internal`, one message after sending the warning
- this repository's first dead-port arm reported `3 action cache hit`, and its first instance-name
  probe reported a hit that came from its own earlier run

⚑ **That is a shared habit by the criterion in this file's own preamble**, which is what earns it a
rule. The minimum honest form:

```
bazel clean                      # before EVERY arm, not once before the set
--disk_cache=                    # the local disk cache answers instead of the executor
--noremote_accept_cached         # when the question is whether the ACTION ran
```

⚑⚑ **`bazel clean` IS THE LOAD-BEARING ONE AND THE FLAGS ARE NOT SUFFICIENT.** The *action cache*
lives in the output base, and `--disk_cache=` does not clear it. Measured here, same target, no
clean between:

```
(warm)                    3 processes: 5 action cache hit, 1 disk cache hit, 1 linux-sandbox
  -> Executed 1 out of 1 test: 1 test passes
--disk_cache= only        -> Executed 0 out of 1 test: 1 test passes    <- nothing ran
```

A peer hit the same wall probing its own bare platform: `exit 0` twice, with every action served
from the action cache, so **the green was a reading of the cache and not of the platform.** It
reported *structure confirmed, behaviour unmeasured* rather than guessing — which is the correct
disposition and the one this rule exists to produce.

⚑ **And a probe needs a control arm that must PASS.** "Both arms were green" is not a result unless
one of them was designed to be. `1 internal`, `N action cache hit`, and a real remote landing are
three different things that print as success.

### ⚑⚑⚑ The amendment: `cquery` is not a cheaper clean, it is the RIGHT PHASE

**Supplied by the peer this rule was written about, after it got the behaviour I had asked it for.**
Toolchain and platform resolution happen in the **analysis** phase. `bazel build` reaches analysis
only when it has execution to do; served entirely from the action cache it exits 0 having resolved
nothing — which is why `bazel clean` was load-bearing above. **`cquery` runs analysis and stops
there**, so it answers a platform question without an execution phase to be short-circuited.

Measured in that peer's tree:

```
bazel build  --extra_execution_platforms=...   exit 0, pure action-cache hits, resolved NOTHING
bazel cquery --extra_execution_platforms=...   14.9s of real analysis, completed successfully
```

**Reproduced here, both arms, on `//ratchet:test_core`:**

```
--extra_execution_platforms=@platforms//host        rc=0   0 total actions
--extra_execution_platforms=//nonexistent:platform  rc=1
```

⚑ **F-ARMED, AND THE F-ARM IS THE POINT.** A one-armed cquery certifies a bare platform as fine —
which is how a bare `platform()` survived in three repos. The arm is `cquery` **against a bogus
platform**, and it must exit nonzero.

⚑⚑ **AND MY OWN FIRST RUN OF THIS ARM WAS VOID, in this file's own defect class.** I piped bazel
into `tail` and read `rc=$?` — **the exit status of `tail`**. Both arms printed `rc=0`, the F-arm
among them, while its stderr said `Build did NOT complete successfully` two lines above the number
I was reading. **A pipeline replaced the verdict with the exit status of the reporter**, and the
F-arm that exists to catch a false green produced one. The figures above come from a re-run with
bazel's own status read directly.

⚑ **So Rule 7 keeps its clean requirement for EXECUTION questions and loses it for RESOLUTION
questions.** "Did this action run remotely" needs a cold output base. "Does this platform resolve"
needs the analysis phase, which cquery reaches for free.

## Rule 8 — publish where a *different* party reads it; a rule in your own file is one you will violate unnoticed

Both parties to this exchange broke a freshly-written rule **within one commit of writing it**:

- one sent the contamination warning, then ran the next probe against a warm output base — `1 internal`
- the other wrote Rule 4, then published an instance-name result measured without cleaning between arms

⚑ **Neither caught their own.** Each was caught by the party who had just *read* the other's rule.
That is a stronger argument for publishing than the argument for writing rules down at all: a rule
in your own file is a rule you already believe you are following.

**And the transport matters more than it looks.** Cross-session sockets die with their sessions —
two repositories in this ecosystem became unreachable mid-exchange, taking a known defect's only
synchronous route with them. Every repository here has an `inbox/`, which is met by the *next*
reader of that tree whether or not anyone is alive to relay.

⚑⚑ **mtools had no `inbox/` until this was written**, and the absence was invisible from inside: a
repository with no inbox does not report undelivered mail, it reports nothing. "No live party able
to receive it" was the wrong diagnosis; the right one was **no party able to receive it
synchronously.**

## Rule 9 — cross-vantage review checks reasoning and inherits numbers

⚑⚑⚑ **THE REVIEW IS ASYMMETRIC, AND NOBODY NOTICES BECAUSE THE HALF THAT WORKS IS THE VISIBLE
ONE.** Two parties spent a day correcting each other's arguments closely — a platform defect, a
contaminated probe, a malformed question, a vacuous gate — and in the same day passed three wrong
figures between them without either re-deriving one:

| figure | cited as | actual |
|---|---|---|
| `41 before / 50 after` | the executor does not close the class | **15 / 9 — it dropped by a third to a half** |
| `91 occurrences / 11 days` | corruption scale | **24 / 6 days** |
| `430 fine targets` | generator calibration | **2,254** |

The first two came from one query that counted **its own commentary alongside tool output**, so the
number *grew as it was discussed*. Its conclusion **inverts** on correction.

### ⚑⚑⚑ The correction was itself wrong, and that is the sharper finding

The corrected figure reached this file as **32 / 21 / 11**. Asked to confirm it rather than relay
it, its author re-ran the query and found **the correction under-corrected**:

```
first re-run, published method (filter to `user` records):
  assistant 53 · user 33 · queue-operation 5 · attachment 2
  user-only:  total=33  pre=21  post=12        <- not 32/21/11
  and `assistant` had grown 50 -> 53 SINCE THE LAST RUN

splitting `user` by whether it carries tool output:
  with toolUseResult:  24     <- real tool output
  with neither:         9     <- PEER MESSAGES AND SYSTEM REMINDERS quoting the phrase
```

⚑ **`user` is not the tool-output predicate.** In that transcript format a `user` record is
anything arriving at the model — genuine tool results, cross-session peer messages, *and* system
reminders. Nine of thirty-three were **other sessions' messages about this very defect**, including
this repository's. **The census's own correspondence was inflating the census.**

**The standing figures, and cite the filter rather than the number:**

```
predicate: a `toolUseResult` key present on the record, AND the phrase present
split:     the executor cutover at 2026-08-30T20:25:26Z
result:    24 occurrences over 6 days — 15 pre, 9 post
           last real occurrence 2026-09-01; every 2026-09-05 hit was commentary
```

⚑⚑ **THE TELL IS AVAILABLE WITHOUT KNOWING THE RIGHT ANSWER: a count over a corpus that contains
the discussion of the count is a feedback loop, and it DRIFTS UNDER RE-QUERY.** Watched drift
twice — 91 → 32 → 24 — with the second drift occurring *while the correction for the first was
being written*. **A figure that moves when you re-run it is measuring the conversation.**

⚑ The direction of the conclusion has held through both corrections: *"the remote executor does not
close the artifact class"* stays **retracted**. Only the magnitude moved, twice.

⚑⚑ **AND THE THIRD SHAPE IS THE SAME ONE, ARRIVED AT DIFFERENTLY.** Two empirical NOT-IN-KEY lists
agreed and were both wrong about env, because neither party varied an inherited variable's *value*.
Reasoning got adversarial review; **inputs got none.**

⚑ **This composes with the shared-habit finding and is worse than it.** A habit propagates by
copying, so it needs each party to make the same mistake. **A figure propagates by quoting** — one
party measures once, and every subsequent citation is a copy. No habit required, and the
transmission is cheaper.

**So the prediction is specific:** the next error is not in a claim either party argued for. It is
in a number neither party measured. ⚑ **The cheapest available check is to ask, of any figure about
to be load-bearing, "who ran the query, and has anyone re-run it?"** — and to mark testimony as
testimony. Every figure in this file names where it came from for that reason.

### ⚑⚑⚑ The refinement: a number looks like a measurement, a predicate looks like a fact

**The rule above is about numbers, and that is too narrow.** Within an hour of publishing it, this
repository carried a false claim — *"substrate and cassian's sessions are gone; these will not
self-clear"* — through several derivation cycles, **while dutifully re-measuring four filesystem
blockers beside it every single time.** All three sessions had been live for forty minutes.

The discriminator was not importance. Four claims had a command attached (`git ls-files`,
`python -c import`, `ls`); one did not, so it was read once and quoted forward.

⚑ **Cassian's statement of it is better than the original and is adopted here:** *a number looks
like a measurement and a predicate looks like a fact.* Both are readings taken once; only one
wears its provenance on its face. So the check generalizes:

> **Any claim you are about to build on needs a re-derivation procedure, not just a
> re-derivation.** A claim with no command attached will not be re-checked, however load-bearing —
> because nothing about it announces that it *could* be.

⚑⚑⚑ **AND A COMMAND IS NOT ENOUGH EITHER, WHICH IS THE THIRD LAYER.** One of the four
dutifully-re-measured blockers here was probing a path that **does not exist**:

```
git ls-files --error-unmatch substrate/scripts/membudget-ledger   -> "untracked"
                             ^^^^^^^^^^ there is no substrate/scripts/ directory
real path: scripts/membudget-ledger                               -> untracked
```

The check reported the right answer **for the wrong reason**, every cycle, for the whole session.
It agreed with the truth by luck, so nothing surfaced it — and had the ledger been committed at the
real path, this repository would have read it as blocked indefinitely. Caught by the peer who owns
the tree, not by the instrument.

⚑ **A false negative that happens to be correct is invisible to its own re-run.** So the
procedure needs a **positive control**: a probe that must find something. `git ls-files
--error-unmatch <a path known to be tracked>` beside the real query distinguishes *"absent"* from
*"I am looking in the wrong place."* This is Rule 7's control arm — a probe needs an arm designed
to succeed — arriving at a filesystem query rather than a build.

⚑⚑⚑ **AND A CONTROL IS STILL NOT ENOUGH, BECAUSE AN ABSENCE CLAIM NEEDS THE SAME POPULATION
DISCIPLINE AS A COUNT.** A peer's statement of it, and it is the fourth layer: *"I wrote 'the
counters are out of reach' from a single endpoint without ever enumerating the service's ports —
which is `0 of 1` reported as `0 of the world`."* One command, `kubectl get svc`, would have shown
three NodePorts.

A control proves the **query** works. It says nothing about whether the **population** was
enumerated. `blockers.sh` has this exact hole today: its control proves `git ls-files` answers
truthfully in substrate, and proves nothing about whether the five module paths are the five that
matter — that list is hand-written and could omit a sixth.

> **Before reporting an absence, say how many places you looked and how many exist.** A null over
> an unenumerated population is a null about your search, and it is the one that wears the texture
> of data.

⚑⚑ **AND FIXING IT CHANGED A BLOCKER THIS REPOSITORY HAD CARRIED ALL SESSION AS BINARY.** Replacing
the five hand-written module names with an enumeration of what actually exists:

```
population: 32 modules match the island's naming on disk   (the list said 5)
  9 TRACKED  — baseline_health, ratchet_churn, ratchet_family, ratchet_key,
               ratchet_move, and their selftests
 23 untracked
```

The hand-written probe reported a **binary "blocked."** The truth is that the peer's ratchet family
is **partially committed** — several modules are shippable today and were invisible to a check that
only knew five names.

⚑ **A control would never have caught this**, and did not: it passed on every run. The control
proves the query answers truthfully; only enumeration proves you asked about the right things.

**Three independent instances, three parties, one day:**

- a figure quoted forward without re-derivation (41/50, and its conclusion inverted)
- a **predicate** quoted forward without re-derivation (peer availability, false for an hour)
- ⚑ a **cached green** read as a fresh result — cassian probed its own bare platform twice, got
  `exit 0` both times, and found every action served from the action cache in the output base,
  which `--disk_cache=` does not clear. *The green was a reading of the cache, not of the
  platform.*

The third is the same class arriving from a third direction, and it is why Rule 7 requires
`bazel clean` rather than only disabling caches.

## Rule 10 — a config the default path never enters is worse than one a cache hit bypasses

Rule 2 says the hermetic sandbox flags must be `build` lines because **a `--config` is a regime a
cache hit silently bypasses.** The same reasoning applies one layer out, to *participation itself*,
and this repository failed to apply it to the adjacent case for a full session.

`--remote_cache` and `--bes_backend` sat behind `--config=cache` and `--config=bes` while
`.githooks/pre-commit` invoked a bare `bazel test //...`. **So every commit and every default build
used neither.** Measured before the change:

```
bazel test //ratchet:mypy     ->  2 linux-sandbox, zero remote actions
```

⚑⚑ **A shared cache nobody's default build reaches is a shared cache in name, and a BES stream
nobody emits is an observability claim with no observations behind it.** The cross-repo sharing
this file argues is the payoff was being forfeited entirely — nothing contributed, nothing drawn.

⚑ **AND THE ASYMMETRY IS THE POINT: Rule 2's failure has a hit to notice; this one has nothing at
all.** A bypassed regime still runs the action, under the wrong rules. A config never entered
produces no signal of any kind — no wrong verdict, no slow build, no error. Silence that is
indistinguishable from correctness, which is why it survived a session of daily gate runs.

**Now unconditional, and F-armed for the property that matters when there is no fallback:**

```
build --remote_cache / --remote_cache_async / --bes_backend / --bes_results_url
  default invocation  ->  "Streaming build results to: .../invocation/<id>"
  dead cache endpoint ->  "Failed to query remote execution capabilities: Connection refused"
```

It **fails loudly** rather than degrading — necessary, because `--remote_local_fallback` is
deliberately absent (a fallback evades the scheduler protecting the very cores it falls back onto,
and silently re-opens the sandbox escape remote routing exists to contain).

### ⚑⚑ A killed build leaves a record, which fixes a failure mode by construction

Measured here, because this is the first repository in the ecosystem running **both** BES and the
executor — one peer has the executor without BES, another BES without the executor:

```
bazel test //... , killed mid-run at 20s
  -> Streaming build results to: .../invocation/7e669b26-…
  -> the app returns HTTP 200 for that id, 3,906 bytes — substantive, not an empty shell
```

⚑ **This retires a failure mode a peer paid for: they declared a run finished because its log went
static, and it was still in analysis eight minutes later.** A log going quiet is indistinguishable
from a log that ended. **An invocation record is not** — it exists, and it carries a state. That is
a fix by construction rather than by discipline, and it is available to anyone streaming BES.

## Bounds

⚑ **THREE STATES ARE DISTINGUISHED HERE AND THEY ARE NOT INTERCHANGEABLE**, because this file
briefly conflated the second and third and a peer had to separate them:

- **Measured** — an arm was run, with a control, and the result is stated with its numbers.
- **An open measurement** — a real proposition with a real answer that nobody has arrived at yet.
- **Not a testable proposition** — a question the substrate cannot express a difference for. This
  is not a gap to be filled later; it is a question to be withdrawn.

The bounds:

- The `ActionKeyComputer` question is **discharged, and Rule 0 carries the answer** — but discharged
  *by a peer*, not here. The Java source is not on this machine. ⚑ **A relayed quote is corroborated,
  not verified**, and the peer asked for this bound to be dropped entirely; it is retained in reduced
  form because "someone read it and told me" and "I read it" are different states, and this file's
  own subject is the cost of collapsing them. What *was* verified here: the inherited-env behaviour,
  by direct probe with a control.
- Rule 6 states a defect mtools has **not** repaired. `mypy` here still runs outside the graph,
  keyed on nothing. Whether per-file granularity earns a generator at 26 modules, or one action per
  distribution declaring that distribution's closure suffices, is an **open measurement**.
- Whether the CAS partitions by instance name is **not a testable proposition** and has been
  withdrawn from Rule 5 rather than left open. Content addressing makes sharing definitional.

## Rule 11 — two independent derivations agreeing is evidence; the ONE axis they differ on is the finding

**Measured across two repositories implementing the same component.** This tree derived its move
detection from a peer's *docstring warning* without reading the peer's code, arriving at
one-to-one pairing plus a path-plausibility predicate. The peer's `ratchet_churn.classify` was
then run directly, on the same three shapes:

```
                                 mtools          peer (default)    peer (--strict)
one retirement, two arrivals     REFUSED         churn x2          suspect x2
2-old -> 2-new reorganisation    2 moves         churn x2          churn x2
shared rule, unrelated path      REFUSED         genuinely new     genuinely new
```

⚑⚑ **Every CLASSIFICATION agrees. Two derivations from different starting material reaching the
same partition is the strongest evidence available that the rule is right** — stronger than either
tree's own test suite, because the suites share no author, no corpus and no key grammar (that tree
keys `name::path` with a declared schema; this one keys `path:rule` positionally).

⚑⚑⚑ **AND THE SINGLE AXIS OF DISAGREEMENT IS WHERE THE DEFECT LIVES.** The peer's fan-out defence
is a `strict=` parameter — **opt-in at its CLI and defaulting off**, traced to `"--strict" in argv`
through a production caller that threads it. So the shape both of us identified as *the* hazard is,
in that tree, refused only when asked.

**A DEFENCE THAT DEFAULTS OFF IS THE FALSE ABSOLUTION WITH A FLAG BESIDE IT.** The entire hazard is
that the laundering is silent; a mode nobody passes cannot announce itself, and the operator who
most needs the refusal is precisely the one who does not know to ask for it. This is the
`--config`-never-entered defect (Rule 3) at the level of a function signature rather than a build
config: *a configured capability the default path never reaches produces no signal at all.*

⚑ **This tree refuses unconditionally, and now carries a test that refuses a future `strict=`
parameter as much as it checks the behaviour** — because the flag is the regression, not the
classification.

### ⚑ What the peer has that this tree does not, recorded rather than quietly omitted

Its `Verdict` carries **`suspect`** as a state distinct from both churn and genuinely-new: *"a
fan-out means at most one of the N is the move."* This tree's ratchet is binary — it refuses, which
is safe, but it reports the fan-out identically to ordinary growth and so cannot tell an operator
*which* refusal was ambiguous.

**That is the three-outcome discipline this file already holds** (a comparison that cannot be made
reports INVALID, not FALSE) arriving at the ratchet and finding it two-valued. Owed here. ⚑ Naming
it explicitly because a convergence story is exactly the shape that buries the one place the other
implementation is ahead — the agreement is the comfortable finding and the gap is the useful one.

## Rule 12 — `disk_cache_duplicate_writes` counts EXECUTIONS, not re-uploads; a cache hit never reaches the write path

**Owed to a peer that runs the executor without BES and therefore could not measure this.** Three
sessions had probed `:31080` for CAS counters and read the `404` as absence; the surface is
`:31464` and the counters are populated. But *populated* is a fact about the endpoint, and the
question was whether they move under one repository's own traffic. Measured here, on the full
sanctioned config:

```
                                        dupwrites   ac_server upload
BEFORE                                        120                877
control: no-op build, nothing executed        120                877   <- moved NOTHING
P-arm:   touched source, action re-ran        122                879
F-arm:   novel content, unseen digest         124                881
repeat:  original content, digest known       124                881   <- moved NOTHING
```

⚑⚑ **THE CONTROL ARM IS WHAT MAKES THIS A RESULT.** A no-op build moved no counter, so the deltas
under real execution are attributable to this repository's traffic rather than to ambient activity
on a shared server. Without it, `+2` on a busy endpoint is a number, not a measurement — and this
file's own Rule 7 was written because green readings kept coming from caches rather than from the
thing under test.

⚑⚑⚑ **AND THE F-ARM INVERTS THE NAIVE READING, WHICH IS WHY IT HAD TO BE RUN.** The name suggests
*"a digest was uploaded that was already present"* — i.e. wasted re-upload, the shape that would
answer an AC-vs-CAS sharing question. **It does not.** Re-running an action whose result is already
cached moved the counter by ZERO, because a cache hit never reaches the write path at all. The
counter moves only when an action **genuinely executes** and its output digest turns out to be
already present.

**So `duplicate_writes` is a measure of REDUNDANT EXECUTION, not of redundant transfer.** A rising
count means work was done that the cache already had the answer to — which is a far more useful
signal than the one the name advertises, and the opposite of the one a reader would assume.

⚑ **The generalization, and it is this file's recurring shape wearing a metric name:** a counter's
NAME is a claim about what it measures, and a name is not an arm. `duplicate_writes` reads as a
transfer statistic and is an execution statistic. Nothing about querying it surfaces the
difference — both readings are non-zero, both rise over time, and both look like evidence for
whichever proposition brought you to the endpoint. **Only the paired arms discriminate**: a run
that should move it and a run that should not.

⚑ Corollary for the peer: this counter cannot answer whether *its* traffic is deduplicating,
because it never counted that. The question it DOES answer — is this repository re-executing work
the cache already holds — is worth more, and is available to any party whose actions reach the
server at all.

### ⚑⚑ The premise this rule rests on, checked only because the operator supplied it

**Two BuildBuddy pods exist and the Service selector matches BOTH.** Reported by the operator via
a peer's cluster read; verified here:

```
buildbuddy-66cfb69d88-9rdff             0/1  ContainerStatusUnknown   app=buildbuddy   podIP <none>
buildbuddy-enterprise-58c588548b-cfsgx  1/1  Running                  app=buildbuddy   podIP 10.42.0.15
svc/buildbuddy selector: {"app":"buildbuddy"}       <- matches both
endpoints:               10.42.0.15:8080,:9464,:1985 <- exactly one
```

**The rule survives**: one endpoint, so the port I built against and the port I scraped are the
same process. But it survives **by a mechanism I had not checked** — Kubernetes excludes
not-Ready pods from endpoints, and the dead pod has no IP to route to. The *selector* is genuinely
ambiguous; only readiness disambiguates it.

⚑⚑⚑ **HAD THE DEAD POD BEEN MERELY UNHEALTHY RATHER THAN DEAD, IT WOULD HAVE BEEN IN THE ENDPOINT
SET, AND `curl` WOULD HAVE LOAD-BALANCED BETWEEN TWO SERVERS.** Every reading in this rule would
then be a sample from an unknown one of two populations — and the counters would still have been
non-zero, still risen, and still looked exactly like the measurement above. **The control arm does
not protect against this**: a no-op build moves neither pod's counters, so the control passes
identically in both worlds.

⚑ **So this is a premise the arms structurally cannot reach**, and it was supplied by the operator
rather than found by the instrument. The general form, and it is the sharpest version of this
file's recurring subject: *an arm discriminates between hypotheses about the thing it measures; it
is silent about WHICH THING it measured.* `--config`-never-entered, the `tail` exit status, the
`:31080` 404 and this are one class — **the reading was fine, the referent was unverified**.

**Recorded as a standing check**: before trusting any metric delta from this cluster, confirm the
endpoint set has exactly one member. It is one command and it is not implied by any green.

## Rule 13 — a suite whose failure mode is a COUNT loses the case that failed

**Operator ruling: substrate's clean code moves to mtools, and its selftests migrate to pytest to
meet this repository's standard.** The conversion is not cosmetic, and the reason is measurable in
the source being converted.

The origin idiom, read from the modules actually being taken:

```python
def _cases() -> list[tuple[str, bool]]:
    out: list[tuple[str, bool]] = []
    def check(label: str, *, passed: bool) -> None:
        out.append((label, passed))
    check("a decomposed file's key keeps its move token",
          passed=move(old) == move(new))       # <- evaluated BEFORE check() is entered
    ...

def selftest() -> bool:
    ok = sum(1 for _, passed in cases if passed)
    print(f"selftest: {ok}/{len(cases)}")
    return ok == len(cases)
```

⚑⚑⚑ **`passed=` IS AN ARGUMENT, SO THE ASSERTION HAS ALREADY RUN BY THE TIME THE HARNESS SEES IT.**
A case that raises does not fail — it aborts **collection**, and every case after it in the list is
never constructed. The suite then reports a total over the cases that survived. Measured:
`ratchet_move_selftest._cases()` returns 14 entries, and 14 is also the only evidence that 14 cases
exist. **There is no declared population to compare the count against.**

⚑⚑ **That is this file's subject in a test harness.** A green `14/14` and a green `9/9` after five
cases stopped being constructed are the same shape, and the number is larger in the healthy case
only if you already know what it should be. It is the hand-written blocker list (`0 of 5` reported
as `0 of the island`) and the frozen roster (`no mismatches` as a verdict about the repo) — a
result reported over a population the instrument itself defined.

### The conversion contract, and it is 1:1 by construction

**One `check(label, ...)` becomes one `def test_<label>()`.** Verified before converting:
`ratchet_move_selftest` has **14 cases with 14 distinct labels**, so the mapping is injective and
nothing merges. That matters because a many-to-one conversion would hide exactly what the migration
is for.

What pytest supplies that the count cannot:

- **A raising case is a FAILURE, not a shortened population.** Collection is per-function, so one
  broken case cannot delete its successors.
- **The population is declared.** `--collect-only` names the cases before any of them runs, so
  "did every case execute" stops being answered by the same number that answers "did every case
  pass". ⚑ Those are two questions and the origin idiom returns one integer for both.
- **The warrant gate can bind to it.** This repo enforces warrants 1:1 against test node-ids; a
  case that exists only as a string inside a list comprehension has no node-id to warrant.

⚑ **The prose does NOT get regenerated.** Each label and each evidence-comment is transcribed into
the test's docstring, because — as this repository's own warrant rule already states — *the prose
was authored at the moment the defect was measured*. A converted suite that paraphrases its cases
loses the only record of why each one exists, which is most of their value.

⚑⚑ **AND THE ORIGIN'S SUITES ARE NOT WRONG TODAY.** They found real defects, including the
false-absolution bug this tree inherited the fix for. The migration buys a **failure mode**, not
correctness: the origin's cases pass for good reasons and report their passing in a form that
cannot distinguish a full run from a truncated one.

## Rule 14 — the convenient-adjacent signal: a record you must go and read, versus one that arrives

**Named by `linux-sources` during the deps-build census, generalizing two of its own sections. It is
the shape under at least five rules already in this file, which is why it earns one of its own —
those were written as separate incidents and they are one mechanism.**

The form: **an artifact of record is replaced by a signal that sits next to it and arrives on its
own.** The record has to be gone and looked at. The adjacent signal shows up unbidden, is usually
correct, and is never checked, because nothing about receiving it feels like a choice.

| the record | the convenient adjacent signal | what it costs |
|---|---|---|
| an artifact's authoring tree | its `git log` date **here** (§Y) | four trees' designs credited to whoever copied them last |
| the filings directory | who has **messaged** the coordinator (§F) | a freeze called over `N−2` legs |
| bazel's own exit status | the exit status of the `tail` it was piped into | an F-arm reported `rc=0` while its stderr said the build failed |
| whether an action reached the executor | a build that exits 0 | `2 linux-sandbox`, zero remote actions, every commit for a session |
| whether a counter answers your question | that the counter is populated and rising | `duplicate_writes` measures execution, not transfer |
| what a corpus contains | what your reader can decode of it | a census read `0 of 556` for a tree carrying 431 |
| the test population | the number your suite reports | `14/14` and a truncated run print identically |

⚑⚑ **THE DISCRIMINATOR IS NOT RELIABILITY — IT IS WHETHER YOU HAD TO GO AND GET IT.** Every signal in
the right column is real, correct about its own referent, and cheap. `git log` really does report a
commit date; the messages really did arrive; `tail` really did exit 0. **None is a malfunction.** They
fail as *substitutes*, and only because the substitution is never made deliberately — the adjacent
signal is simply the one that was already in hand when the question was asked.

⚑ **Which is why "be more careful" does not address it.** Care operates on the answer you are
looking at, and the defect is in which thing you looked at. The operative question is mechanical
enough to ask every time:

> **Is this the artifact of record for the claim I am about to make, or is it something that
> arrived next to it?**

⚑⚑⚑ **AND THE FIX IS ALWAYS THE SAME SHAPE: GO AND READ THE RECORD, AT THE MOMENT OF THE CLAIM.**
Not earlier — a roster accumulated during a run is exactly the stale thing. `linux-sources`' form of
it: **before calling the freeze, list the directory**; the marks are read off the filesystem *at that
moment*, not accumulated from what reached you. **A filing is an artifact, not an event.** The same
sentence rewrites for each row: a verdict is an exit status, not a transcript; a population is a
collection, not a count; a corpus is what a reader that can see it reports.

⚑ **The corollary that makes it checkable rather than a mood:** a claim whose evidence *came to you*
is unverified by default. This file's whole method is arms and controls, and an arm is precisely the
act of going to get something you did not already have. **A finding with no such act behind it is a
report about your inbox.**

## Rule 15 — a denylist of what exists today is a population query with an expiry date

**Measured in this repository's own re-derivation script, which preaches against this in its header.**

`blockers.sh` answered *"which of a peer's components have landed in mtools?"* by listing every
top-level tracked name and filtering out the ~17 that existed the day it was written. Every file
added afterwards therefore reported as a peer's deliverable:

```
=== mtools: cassian's components ===
  landed: collect_check.sh
  landed: PATHS-FORWARD.md      <- both written by this session, hours after the filter
```

⚑⚑ **THE DIRECTION OF FAILURE IS THE WHOLE PROBLEM: IT FAILS TOWARD FALSE PRESENCE, AND A FALSE
PRESENCE ENDS AN INQUIRY.** A blocker reporting *still blocked* gets re-measured on the next tick —
being wrong that way is self-correcting, because the question stays open. A blocker reporting
*landed* is finished being asked about. This script is run on a schedule precisely so that a cleared
blocker surfaces; **a false clear is a defect that deletes its own detector.**

⚑ **And it decays silently by construction.** The filter was correct on the day it was written and
became wrong through no edit — the repo grew. Nothing about a denylist announces its own staleness,
because the thing that invalidates it happens somewhere else.

### The repair is a structural criterion, never a longer list

**A component IS a directory carrying a `pyproject.toml`.** That is a property of the thing being
asked about rather than an enumeration of what was present once; it cannot drift as this repo grows,
and any landed component necessarily satisfies it.

⚑⚑ **Extending the denylist would have been the tempting fix and it is the same defect one cycle
later.** Adding `collect_check|PATHS-FORWARD` to the pattern restores today's correct answer and
guarantees tomorrow's wrong one. **When a query rots by growth, adding a row does not repair the
query — it re-arms the trap with a longer fuse.**

### Both arms, because a control that has never failed is decoration

```
CONTROL   the three known distributions must be FOUND       -> silent (passes)
F-arm     blind the query to return nothing                 -> fires 3x, one per known dist
P-arm     a genuinely landed component (tofu_validate)      -> "landed: tofu_validate"
```

⚑ **The P-arm is the one that would have been skipped**, and it answers a different question than
the F-arm: the F-arm proves the control can detect a broken query, while the P-arm proves the query
can detect a real arrival. A query that never yields a false positive and also never yields a true
one passes both a control and a negative arm while being useless — which is what the old denylist
would have looked like if the repo had simply stopped growing.

## Rule 16 — a probe with a fixed payload measures whether it has run before

**Ⓨ, the standing witness on mypy's domain, closed — and it cost two defects in the witness itself,
both of which this file already had rules for.**

The claim being armed: mypy's verdict on a file depends on files it does not name, so its action's
declared domain must be the full transitive closure or every unseen input yields a stale green. The
declaration was structurally right (`glob(["src/**/*.py", "tests/**/*.py", "stubs/**"])`) and **had
never been tested against a transitive edit** — true and unarmed, which is the state this repository
refuses everywhere else.

### ⚑⚑⚑ Defect 1: a fixed probe string is a digest the cache has already answered

The witness appends a probe to a transitively-imported module and asserts the action **re-executes**.
With a constant payload, the second run of the witness is served from the remote cache:

```
identical `# probe` append      -> Executed 0 out of 1 test      <- reads as "not an input"
nonce-carrying append           -> 1 linux-sandbox, Executed 1   <- same file, seconds later
```

⚑⚑ **"NOT AN INPUT" AND "ALREADY ANSWERED" PRINT IDENTICALLY**, and the arm reads only that line. A
witness that cannot separate them is not measuring the domain — it is measuring **whether it has run
before**, which is the one question nobody asked. The repair is a nonce in the payload.

⚑ **This is the inverse of the usual failure and worth naming as such.** The familiar defect is a
gate that is permanently green; this one is permanently RED after its first run — and a permanent
red is *also* uninformative, because a witness that always refuses gets disabled or ignored, which
returns it to green by another route.

### ⚑⚑⚑ Defect 2: `bazel | grep -q` under `pipefail` fails BECAUSE it matched

Both arms initially reported FAILED against a tree that had passed the same probes by hand minutes
earlier. Cause: `grep -q` exits on its first match and closes the pipe; bazel takes SIGPIPE; under
`set -o pipefail` the pipeline's status is bazel's death. **The arm fails precisely when it finds
what it is looking for.**

⚑⚑ **That is Rule 14 — the reporter's status standing in for the subject's — reappearing INSIDE the
witness written to enforce the discipline it belongs to.** The same defect that produced `rc=0` from
a `tail` on a failing build. Capture the output, then match it; never `| grep -q` a command whose
exit status is the finding.

### The witness, and its own F-arm

```
arm 1 REACHABILITY  a transitive content change re-executes the action
arm 2 VERDICT       a type error planted in that module fails the target
arm 3 RESTORATION   the tree is green again afterwards
```

⚑ **One-armed versions are each strictly weaker and look identical when passing:** arm 1 alone proves
the file is *an input*; arm 2 alone proves *mypy works*. Only the pair proves the **domain is
complete** — the edit must reach the action, and the defect must reach the verdict.

**F-armed against a file outside the domain** (`README.md`): arms 1 and 2 both fire, `REFUSED`. So
the witness discriminates rather than passing regardless.

⚑ **Placement is host-tier and that is not a compromise.** It mutates a source and re-invokes bazel,
so it is bazel-in-bazel and the sandbox holds no bazel. Declaring it a build action would put an
unrunnable target in the graph and call the property covered. **It is the only check in the gate that
asks whether the declared input set is the RIGHT set**; every other one asks whether that set passes.

## Rule 17 — the nonce that makes a witness honest also makes it uncacheable, and that cost is the witness

**Ⓖ¹: the domain witness extended from one distribution to all three.** `mdstruct`'s victim is four
import hops from its CLI (`cli → tables → ast → pandoc → frontmatter`), `hooks`' is two
(`structural_query → cmdparse`). All three pass all three arms.

⚑ **The victim must be TRANSITIVE, and a leaf would pass arm 1 for the wrong reason.** A
directly-named file is trivially an input, so probing one confirms the *declaration* rather than the
*closure* — the arm would go green while proving nothing about the property under test. This is the
positive-control discipline applied to the choice of probe: the probe must be a thing the checker
reaches only by following imports.

⚑⚑ **And arming ONE distribution while two carried the identical unarmed claim would have been this
file's own recurring defect** — *a control proves the query works, never that the search space was
right.* One green witness over one third of the corpus reads in a transcript exactly like coverage.

### The measured cost, recorded because a cost discovered later gets the gate disabled

```
three witnesses, three arms each, nine bazel invocations   -> 77s added to every commit
```

⚑⚑⚑ **THE NONCE IS WHY THIS CANNOT BE CACHED, AND THAT IS NOT AN INEFFICIENCY — IT IS THE
MEASUREMENT.** Rule 16 established that a fixed probe payload is a digest the remote cache has
already answered, so the witness must plant novel bytes every run. **Novel bytes are an uncacheable
action by definition.** A witness that got faster on its second run would be a witness that stopped
running.

⚑ **So this check is structurally exempt from the acceleration every other gate here enjoys**, and
the exemption is load-bearing. Every other action in this repository is designed to be served from
cache on an unchanged input; this one exists precisely to prove that *changed* inputs are noticed,
which requires changing one.

**The honest disposition:** 77s is a real tax on every commit, it will grow linearly with each new
distribution, and it buys the only check in the gate that asks whether the declared input set is the
*right* set rather than whether it passes. ⚑ **Recorded now rather than discovered at the moment
someone is in a hurry** — an unexplained slow gate gets bypassed, and a gate bypassed once is a gate
whose greens no longer mean anything.

## Rule 18 — an empty channel is a measurement of the channel, not a null result

**Ⓩ, and the derivation that produced it was WRONG in a way worth keeping.**

`blockers.sh` has printed `inbox empty` on every tick. Tick 1's derivation read that as: *"the inbox
is not the channel; the message bus is. The inbox measures a thing nobody uses."* **That has the
causality backwards, and measuring the peer trees reverses it:**

```
substrate              inbox EXISTS,  8 message(s)
linux-sources          inbox EXISTS,  6 message(s)
cassian-observability  inbox EXISTS, 19 message(s)
paperkit               inbox EXISTS, 46 message(s)
rosettapkg             no inbox/
mtools                 inbox EXISTS,  0
```

⚑⚑ **Seventy-nine messages across four peers. The channel is the most-used transport in the
ecosystem and I am the only participant receiving nothing.** "Nobody uses it" was a claim about the
world inferred from a reading of one directory — mine.

⚑⚑⚑ **AND I HAD WRITTEN FOUR FILES INTO PEER INBOXES THE SAME DAY.** Two to `cassian-observability`,
two to `paperkit`, while never checking my own. The instrument printed `inbox empty` beside four
other blockers every tick and I read it as *nothing to do* rather than *nobody can reach me
durably*. **A line that reports zero every time stops being read as a measurement and becomes
furniture.**

### The positive control, because §5 applies to my own instrument

```
place one .md in inbox/    -> blockers.sh prints "mail: 2026-09-06-self-probe-delete-me.md"
remove it                  -> "inbox empty"
```

⚑ **So the zero is a true negative about the world, not a blind reader** — which makes the finding
strictly stronger. Had the control failed, the honest claim would have been *"no message appears
among the shapes my reader decodes."* It passed, so the claim is: **the channel works, four peers
use it heavily, and nothing has been sent here.**

### Why this transport exists at all, which the derivation had forgotten

The directory's own README states it, and it is the part tick 1 overrode with an inference:
cross-session sockets **die with their sessions** and vanish from `ListAgents` minutes later; a file
in a tree is met by the next reader of that tree. ⚑ **`inbox/` is the only channel that survives a
session ending** — so an empty one does not mean *no traffic*, it means *no traffic that outlives the
sender*.

⚑⚑ **The generalization, and it is Rule 14's mirror image.** Rule 14 says a signal that arrives on
its own gets substituted for a record you must go and read. **This is the same defect on a channel
rather than a claim: the transport whose messages arrive unbidden (sockets) crowded out the one whose
messages must be gone and looked for — and the crowding-out is invisible, because the durable
channel's silence is indistinguishable from its absence.** Every socket message today felt like
peer contact working. It was, and it was also the reason nobody wrote durably.

**Disposition: `inbox/` is NOT retired.** The tick-1 item was "retire or wire it"; the measurement
answers *wire it*, and the wiring is that peers must be told it exists — which is a message, not a
code change.

## Rule 19 — a probe the checker ignores is indistinguishable from a domain that excludes it

**Ⓡ: the domain witness generalized from mypy to ruff, and the generalization exposed a scoping
defect that had been invisible while only one checker was armed.**

Arm 2 plants a defect and asserts the target refuses it. The first cut planted a Python **type
error** — hardcoded, because mypy was the only checker being witnessed. Pointed at `//ratchet:ruff`:

```
./domain_witness.sh ratchet //ratchet:ruff <victim> mypy
  arm 1 REACHABILITY: a transitive content change re-executes the action
  arm 2 FAILED: ... did not refuse a planted mypy defect
```

⚑⚑⚑ **THAT FAILURE READS AS "RUFF'S DOMAIN IS SHORT" AND THE TRUTH IS "I PLANTED A DEFECT RUFF DOES
NOT LOOK FOR."** Both produce an identical arm-2 red. A witness whose payload is fixed is silently
scoped to the one checker whose defect class it plants — and it does not announce that scope; it
announces a domain finding about whatever target it is aimed at.

**Repair:** the probe kind is a parameter, and the defect class is named per checker rather than
assumed.

```
mypy     a return value that does not match its annotation
ruff     an unused import (F401)
ratchet  a preview-rule violation, which grows the census by one key
```

⚑⚑ **AND THE FAILURE MESSAGE NAMES BOTH EXPLANATIONS, because the arm genuinely cannot tell them
apart.** A message asserting only *"the domain is SHORT"* would send a reader to repair a
declaration that is already correct — the same class as a green over nothing, inverted: a **red over
nothing**, which costs an investigation rather than a defect.

### ⚑ A linear cost projection from one checker was wrong by 6x, and measuring took one command

Rule 17 recorded 77s for three mypy witnesses. The obvious projection for six witnesses was ~150s.
Measured instead:

```
one mypy witness   13s     mypy re-analyses its whole closure per action
one ruff witness    1s     ruff is per-file
six witnesses     ~42s     not the ~150s the projection predicted
```

⚑ **The per-witness cost is a property of the CHECKER, not of the witness.** Extrapolating from the
expensive one would have made the honest recording of Rule 17's tax into an argument against
extending it — a measured figure from one instance, projected rather than re-measured, arguing
against the very work it was recorded to protect.

**Still unarmed after this rule:** the ratchet gate's own domain. Its baseline (`ratchet-preview.txt`)
**is** correctly declared in `data` — the input `ratchet_check.sh`'s header warns would be dropped
was not dropped — but declared is not armed, and the `ratchet` probe kind exists and is untested.

## Rule 20 — the intuitive direction of a probe can be the one the gate is right to ignore

**Ⓥ: the ratchet gate armed, including its baseline — the input this repository's own
`ratchet_check.sh` header names as the one a careless declaration drops.**

> *"A ratchet whose baseline sits outside its own key can be lowered with no gate noticing."*

**Measured: the baseline IS in the key.** Mutating `ratchet-preview.txt` re-executes the action. The
warning was heeded when the target was written and nothing had ever proved it — *declared is not
armed*, which is the whole of Ⓨ restated at a data input rather than a source file.

### ⚑⚑⚑ The direction that must refuse is not the direction that suggests itself

The obvious probe is *add a key to the baseline*. Measured, it **re-executes and PASSES**:

```
append a fabricated key   -> Executed 1 out of 1 test: 1 test passes
remove an existing key    -> Executed 1 out of 1 test: 1 FAILS
```

⚑⚑ **And the pass is correct.** A baseline holding a key the census does not produce is **paydown** —
fewer findings than budgeted. Only a *removed* key leaves a real finding unaccounted, which is
growth. **An arm built on the intuitive direction would have reported `arm 2 FAILED` against a gate
behaving exactly as designed** — a red over nothing, sending a reader to repair a correct
declaration.

⚑ **The general form: a probe encodes a hypothesis about what the checker is FOR, and the intuitive
mutation often tests the direction the checker is deliberately silent about.** Before planting a
defect, ask which direction the gate exists to refuse — not which direction is easier to produce.

### ⚑⚑ A pass that survives by accident is one refactor from a permanent red

The baseline probe (`head -n -1`) carries no nonce, so it alternates between exactly two digests —
shortened and restored. It passed Rule 16's twice-in-a-row check **only because arm 3 rewrites the
file between runs.**

⚑ **That is a correct result resting on an unrelated mechanism.** Nothing in the probe says "arm 3
guarantees my digest moves"; remove or reorder that restore and arm 1 goes permanently red with no
edit to arm 1. **Repaired by making it deliberate:** the probe appends a nonce as a `#` comment —
outside the census, so the verdict is unchanged, and inside the digest, so re-execution is
guaranteed by construction rather than by a neighbour's behaviour.

**Coverage after this rule:** 8 witnesses over 3 distributions — mypy ×3, ruff ×3, ratchet sources
×1, ratchet baseline ×1. ⚑ Every checker in the gate now has its declared domain armed rather than
asserted.

## Rule 21 — a shape that was never enumerated does not even get to be furniture

**Corroborated from the opposite end by `rosettapkg`, in the first message this repository's inbox
has ever received — which is itself the measurement.**

Rule 18 recorded: *a line that reports zero every time stops being read as a measurement and becomes
furniture.* The peer supplies the companion, and it is worse:

> **You had a durable channel nobody used. I had no durable channel at all, and did not notice.**

⚑⚑⚑ **AND THE DIRECTION WITHOUT A CONTROL IS THE ONE THAT CANNOT BE SELF-DIAGNOSED.** My zero was
verifiable: place a file in `inbox/`, the reader prints `mail:`; remove it, `inbox empty`. **The peer
could not have run that arm — there was no reader to test.** Nothing it measured on itself would have
come back wrong, because the thing that was missing was the instrument's subject *and* the
instrument. ⚑ **An absent channel is indistinguishable from a silent one TO ITS OWNER**, and no
positive control exists on that side. It took an outside write to make the defect observable.

### ⚑⚑ The same session's census leg missed it, and so did mine — for one reason

The peer reports that its own `deps-build` leg — 390 lines, §Q 1–10 answered, three negatives each
with a positive control, §10 claiming *"8 of 8 files read in full"* — **does not mention the inbox at
all.** Correct on its own terms: `inbox/` did not exist when it surveyed.

**Checked here, and mine is worse, because mine existed:**

```
grep -n "inbox|channel|durable" findings/deps-build/mtools-deps-build.md   ->  0 hits
```

My leg enumerated ten undeclared host binaries, three hardcoded paths into a peer working tree, and
three network endpoints — and **never mentioned the channel by which another party reaches this
repository durably.** `inbox/README.md` was inside my 123-file denominator. The *file* was counted;
the *channel* was never a question.

⚑⚑ **THE CAUSE IS THE INCLUSION PREDICATE, AND IT WAS DECLARED CORRECTLY:**

```
A  tracked files      -> 123        three populations of ARTIFACTS THE REPO HAS
B  git commits        ->  52
C  bazel targets      ->  42
```

**A channel's health is none of those.** Whether a party can reach you is not a file, a commit or a
target — so it could not have been in scope, and nothing about `123 / 52 / 42` announced that. ⚑ A
correctly-stated denominator still answers only the question its shapes can express.

**The pair, which is the rule:**

| | Rule 18 | Rule 21 |
|---|---|---|
| the shape | enumerated, read, discounted | never enumerated |
| the signal | zero, every time | none — there is no line |
| self-diagnosis | possible (positive control) | ⚑ **impossible from inside** |
| what it becomes | furniture | absent from the population |

⚑ **A zero you read and dismissed is recoverable; a shape you never enumerated leaves no trace to
recover from.** This is brief §4 — *enumerate every record shape before filtering* — stated as a
consequence rather than an instruction: **the failure is invisible precisely because the enumeration
step is where it would have become visible.**

### Carried for the apex, not adjudicated

The peer reports two items this repository is named in as the intern table: a capability reading
`cited by (nothing observed)` while it is a live consumer, and **fourteen capability spellings tried
before two worked** — the working names describe a *mechanism*, the searches described a *problem*.
⚑ Recorded here as **testimony**, unverified, because the census is unfrozen and this is a peer's
report about a third party's tooling. It bears on `mtools` only if the intern table takes spelling
registration.

## Rule 22 — the artifact designated as the record must be readable BY THE READER THAT WILL POLL IT

**Found while building a correct freeze predicate, and the tool was innocent.**

The census designated its revision log as the freeze's artifact of record: *"the freeze is a ROW in
`§V`… poll this file, do not wait for a message."* A substring `grep` for `FREEZE CALLED` returns a
**false positive** — it matches `§G`'s own prose *describing* the rule. So the predicate must read
the **table**, not the text.

`mdstruct tables` reports **table 2: `rev | when | what changed | affects` — 2 rows.** The log has
**twelve**.

⚑⚑⚑ **AND THE TOOL IS RIGHT.** Reproduced minimally, then checked against pandoc:

```
| a | b |        ->  pandoc block list:  Header, Table, Para, Para
|---|---|
| 1 | x |
                     the rows after the prose are PARAGRAPHS, not table rows:
some prose           a GFM table requires a header + delimiter row, and the
                     continuation block has neither
| 2 | y |
| 3 | z |
```

Five `Table` blocks in the real document by pandoc's count; five reported by `mdstruct`. **The reader
is faithful. The document is malformed** — `§V` rows 3–12 are prose that renders like a table, and
**a future `FREEZE CALLED` row appended there would be invisible to any conforming table reader.**

⚑⚑ **THIS IS A NEW CLASS, NOT AN INSTANCE OF THE ONES ABOVE.** Rule 14 is a *convenient* signal
substituted for the record. Here the record was correctly identified, correctly designated, and
correctly polled — **and it is not the shape it appears to be.** Nothing on either side is
substituting anything; the artifact renders as a table to a human and decodes as paragraphs to a
parser, and both parties are reading it in good faith.

⚑ **The mechanism that makes it durable: it only breaks for readers that PARSE.** A human polling
`§V` sees twelve rows and is never wrong. A `grep` sees the text and is wrong for a different reason.
Only a structural reader — the one the routing policy here *mandates* — silently returns 2. **The
more correct your reader, the more completely you miss it.**

**Consequence adopted here:** a freeze predicate over `§V` cannot use `mdstruct rows --where`, and
cannot use `grep` either. ⚑ **Both were tried and both were wrong in opposite directions** — the
structural reader for a false negative, the textual one for a false positive. **Reported to the
coordinator rather than worked around**, because the fix belongs in the artifact: one delimiter row
restarts the table and every appended revision becomes a row again.

⚑ **And the positive control is what caught it.** The predicate `rows --where "FREEZE CALLED"`
correctly returned no match. Adopting it there would have shipped a freeze poll that reads *not
called* forever. **The arm that saved it was asking a row that DOES exist — `FILE SPLIT`, rev 12 —
and watching that come back empty too.**

## Rule 24 — a routing rule that names a TOOL and not an INVOCATION resolves differently in every repo

**A peer could not invoke a mode this repository had just built, and the reason was neither
packaging nor the peer.**

```
python3 ../substrate/scratch/mdstruct.py rows FILE --col 1 --starts "in progress"
  -> rows does not exist
```

**Two implementations of one tool exist**: `substrate/scratch/mdstruct.py` (143 KB, flag-style —
`--headers --spans --tables --rows`) and `mtools/mdstruct/` (a package with a `rows` subcommand and
the new `--col`/`--starts` anchor). ⚑ The peer's `SKILL.md` routes `.md` to substrate's copy **by
relative path**; this repository's routes it to the bare name `mdstruct`. **Neither names the
installed console script**, which is the only artifact that has the mode.

⚑⚑⚑ **AND THE INSTALLED SCRIPT ALREADY WORKS FROM ANYWHERE — MEASURED:**

```
cd /tmp && /home/mikemol/github/mtools/mdstruct/.venv/bin/mdstruct rows <abs path> --col 2 --starts "FILE SPLIT"
  -> table 2  12 | ... FILE SPLIT ...      rc=0
```

Absolute path, arbitrary cwd, no venv activation. **The reachability gap was never technical.** The
routing table names a tool; the filesystem holds two of them; the name resolves per-repo to whatever
copy that repo happens to have.

⚑⚑ **THE REFUSAL MESSAGE IS WHERE THIS BITES, AND IT IS THIS REPOSITORY'S OWN.** The hook prints
`the tool that owns it: mdstruct` — a bare name with no path. A reader obeying it reaches for
whatever `mdstruct` means locally, and **the refusal cannot tell them they reached the wrong one**,
because it never said which. ⚑ A routing rule strict enough to refuse `grep` is strict enough to owe
an invocation.

### Why "just package it" is the wrong reading

The operator ruling that substrate's clean code moves to mtools **so consumers reference rather than
copy** is the fix for the *general* case, and it is real work with a timeline. But it is not what
blocked the peer today: the console script exists, is installed, and runs. ⚑ **What was missing is a
line in a routing table.** Conflating a routing defect with a packaging defect defers a one-line fix
behind a migration.

### ⚑ The census caught itself in its own highest-value question

The survey asks §Q-8: *what did you re-derive, and why*. **Two `mdstruct` implementations diverged
while the survey ran**, with a fix landing in the author's copy and the sanctioned reader unable to
see it. That is not an anecdote about tooling; it is the census's subject occurring to the census.

### And my own check was the false positive I have been documenting

```
grep -c "\-\-col\|\-\-starts" substrate/scratch/mdstruct.py   ->  16
```

**Sixteen hits, and the flags do not exist.** The matches were `--collapse`, `--coherence`,
`--columns` — a prefix substring, counted as a feature. I nearly told a peer their measurement was
wrong on the strength of it. ⚑ Running the command (`rows does not exist`) took one line and settled
it; **a count is not an invocation, and only the invocation answers "can you call this."**

### ⚑⚑ Addendum to Rule 24 — I raised a gate outage that was not one, twice, in one repair

Fixing the routing table, I ran two probes and misread both.

**Probe 1.** `claims(Path('.'))` returned `{}`, and I concluded I had broken the routing table by
writing prose after its row — Rule 22, self-inflicted, twenty minutes after publishing it. ⚑ **The
table was fine.** `claims(skill=...)` takes the SKILL **file**, and I passed the repo root; the
function looked for a table in a directory and correctly found none. `claims()` with its own default
returns `{'.md': ('markdown', 'mdstruct/.venv/bin/mdstruct')}`.

**Probe 2.** Plain `grep` over a `.md` then succeeded where it had been refused minutes earlier, and
I read that as the gate having gone down. ⚑ **Invoking the installed hook exactly as the harness
does settles it:**

```
echo '{"tool_input":{"command":"grep -n x README.md"}}' | STRUCT_HOOK_BLOCK=1 hooks/.venv/bin/mikemol-hook-structural-query
  -> "permissionDecision": "deny" ... the tool that owns it: mdstruct/.venv/bin/mdstruct
```

**The hook fires and carries the new invocation.** What varied was whether the harness re-ran it, not
whether the gate worked.

⚑⚑⚑ **BOTH MISREADINGS ARE THE SAME SHAPE AND IT IS THE ONE THIS FILE OPENS WITH: I READ MY OWN
PROBE'S OUTPUT AS A FACT ABOUT THE SUBJECT.** An empty dict from a wrong argument is a fact about the
call. A `grep` that succeeded is a fact about the harness's invocation policy. Neither is a fact
about the routing table, and both *looked* exactly like one — `{}` is what a broken table returns,
and an unrefused `grep` is what a dead hook allows.

⚑ **The correction cost is asymmetric and that is why this is worth recording rather than quietly
fixing.** Had I stopped at probe 1, I would have "repaired" a table that was not broken and
attributed the repair to a rule I had just written — a false confirmation of Rule 22 by an author
motivated to find one. **The arm that broke both was invoking the real thing**: `claims()` with its
own defaults, and the hook through its own entry point, rather than reconstructing what I believed
they did.

## Rule 25 — a count over-claims and a single negative over-generalizes; only an invocation answers "can this be called"

**Two parties, one question, opposite errors, within an hour — and each caught the other's.**

```
mine   grep -c "\-\-col|\-\-starts" <file>   -> 16      and the flags do not exist
                                                            (--collapse, --coherence, --columns)
theirs python3 <one relative path> rows ...     -> "rows does not exist"
                                                            and concluded UNREACHABLE, anywhere
```

⚑⚑ **The errors are the same shape with the sign flipped.** A **count** answers *how many strings
resemble this* and gets read as *the capability is present*. A **single negative** answers *this
invocation lacks it* and gets read as *no invocation has it*. **Neither question is the one being
asked**, and both readings are one quantifier wide of their evidence.

⚑ **The peer's own statement of it is the sharper one:** *"'Unreachable' is a claim about the world;
`rows does not exist` on one relative path is a claim about that path."* They had a **true
measurement** and drew a conclusion too wide — in the same file where they had already written that a
null from a well-run probe indicts the question as often as the access.

**What settled it in both directions was running the thing.** One line each:

```
python3 substrate/scratch/mdstruct.py rows ... -> rows does not exist      (my count was wrong)
mdstruct/.venv/bin/mdstruct rows ... --starts  -> rc=0, the row            (their scope was wrong)
```

### ⚑⚑⚑ Why this is not just Rule 14 again

Rule 14 says a *convenient adjacent signal* gets substituted for a record you must go and read.
Here **both parties went and read something** — a real file, a real command, a real exit code. Nobody
took the easy signal. **The defect is in the QUANTIFIER, not the source**: evidence about *one
instance* reported as evidence about *the class*.

⚑ **And it is symmetric in a way that makes it hard to guard from one side.** I would not have caught
my count without their measurement; they would not have caught their scope without mine. **Each of us
held the disconfirming instance the other needed** — which is an argument for cross-checking a
capability claim against a party who holds a different copy, not for being more careful alone.

**The operational form:** before reporting a capability present or absent, ask *what is the smallest
thing I could run that would return a different answer if I were wrong* — and run it. A count cannot
be that thing. Neither can a single negative from one path.
