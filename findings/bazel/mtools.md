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

⚑ **And a probe needs a control arm that must PASS.** "Both arms were green" is not a result unless
one of them was designed to be. `1 internal`, `N action cache hit`, and a real remote landing are
three different things that print as success.

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

## Bounds

⚑ **THREE STATES ARE DISTINGUISHED HERE AND THEY ARE NOT INTERCHANGEABLE**, because this file
briefly conflated the second and third and a peer had to separate them:

- **Measured** — an arm was run, with a control, and the result is stated with its numbers.
- **An open measurement** — a real proposition with a real answer that nobody has arrived at yet.
- **Not a testable proposition** — a question the substrate cannot express a difference for. This
  is not a gap to be filled later; it is a question to be withdrawn.

The bounds:

- Rules 2–5 are grounded in measurement, not in a read of Bazel's `ActionKeyComputer`. The
  not-in-the-key list is empirical. **That is an OPEN MEASUREMENT** — a real question about what
  enters the key, with a real answer in the source, that nobody in this ecosystem has read. Two
  empirical derivations agreeing is corroboration only where they *could* have disagreed, and on
  `--remote_instance_name` they did.
- Rule 6 states a defect mtools has **not** repaired. `mypy` here still runs outside the graph,
  keyed on nothing. Whether per-file granularity earns a generator at 26 modules, or one action per
  distribution declaring that distribution's closure suffices, is an **open measurement**.
- Whether the CAS partitions by instance name is **not a testable proposition** and has been
  withdrawn from Rule 5 rather than left open. Content addressing makes sharing definitional.
