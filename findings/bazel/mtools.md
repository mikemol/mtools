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

⚑⚑ **AND THE SPLIT MAY BE REAL RATHER THAN AN ERROR ON ONE SIDE.** The action cache and the CAS
are separate layers with separate keying. `2 remote` says the *action* re-ran; it does not say the
CAS blobs were re-uploaded rather than deduplicated. If the action cache keys the instance name
while the CAS does not, then **"partitioned" and "shared" are both true of different layers** —
and the argument that content addressing does not know what a repository is applies to the CAS,
not to the action cache. Neither party has tested that, and it is stated here as an open split
rather than resolved by preference.

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

**Calibration, measured by that peer and worth stating because the circulating figure is wrong:**
its generator runs `--check` in **5.60s / 40MB** over **2,254** `pk_cmd` targets. Two other
repositories' records cite "430 fine targets" and built cost arguments on it — five times low. A
generator is cheap at that scale, so *cost* is not the reason to defer one; the reason is whether a
domain here is computed.

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

## Bounds

- Rules 2–5 are grounded in measurement, not in a read of Bazel's `ActionKeyComputer`. The
  not-in-the-key list is empirical. That source read is the remaining step and nobody in this
  ecosystem has done it.
- Rule 6 states the defect; mtools has **not** repaired it. `mypy` here still runs outside the
  graph, keyed on nothing. Whether per-file granularity earns a generator at 26 modules, or one
  action per distribution declaring that distribution's closure suffices, is an open measurement.
