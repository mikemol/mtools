# `linux-sources` — deps/build census, leg `LS-`

**Written against:** `CENSUS-deps-build.md` **rev 5**, `CENSUS-BRIEF.md` rev 1.

```
brief:            CENSUS-BRIEF.md rev 1
run:              CENSUS-deps-build.md rev 5
surveyor:         linux-sources                              prefix: LS-
corpus:           ~/github/linux-sources @ 3d81161 · 248 first-party .py (4 are symlinks into
                  ../substrate/scripts) · BUILD.bazel 456,436 B (GENERATED, 261 pk_cmd targets)
                  · MODULE.bazel.lock 212,667 B · uv.lock 547,777 B · warrants.bib 24,417 B
                  (42 @misc) · 35 corpus_facts modules · 231 commits (e9b11f5 2026-08-17 →
                  3d81161 2026-09-05)
reader:           harness Read; git; python3 3.13 (venv); bash; tools/import_closure.py
                  --selftest; tools/gen_gate_build.py --check; tools/check_status.sh
reader-blind:     .sqfs corpus images (binary, unread) · MODULE.bazel.lock / uv.lock /
                  mypy-tool.lock (pin-line sample only, not parsed) · ~/.cache/bazel-disk
                  contents · BuildBuddy server-side state · bazel action logs (no bazel
                  invocation run during this survey)
                  ⚑ THREE PreToolUse HOOKS SHAPED THIS SURVEY'S INSTRUMENT — see LS-24/25/26
                  and the coverage note. This is a measured instrument asymmetry, not a
                  disclosure of intent.
positive-control: exhibited per negative, in-corpus (see LS-27)
unreadable:       0 unrecovered
disclosure:       I am this repo's own delegate surveying itself. CLAUDE.md (77,524 B) and
                  NEXT.md (133,764 B) are this repo's claims ABOUT itself — citations of the
                  repo, NEVER independent verification. Where I re-ran a tool live I say so
                  and class it `machine`. ⚑ I am also this census's DISPATCHER; I authored
                  the run file including §X. That is an input asymmetry no peer has: I know
                  what every leg was told. I did not use it to shape this leg, and per §R
                  the apex is a session holding no leg — not me.
window:           UNBOUNDED per §W. Antecedent probe run — LS-01.
roster-nomination: LS-30 — six parties, five of them not on §R.
not-searched:     peer repos · findings/deps-build/ (forbidden pre-freeze; not opened) ·
                  the kernel corpus itself (not the subject)
```

**Provenance classes** per brief §7 — `citation` (this repo's own bytes, verbatim) · `machine`
(a tool I ran live) · `testimony` (second-hand, appearing in this repo's bytes) · `inference` (mine).

---

## LS-01 — Antecedent probe: the gate is 17 days older than the build system

`machine` — `git log --diff-filter=A`, run live.

| artifact | created | commit |
|---|---|---|
| `.claude/settings.json`, `.githooks/pre-commit` | **2026-08-17** | `e9b11f5` |
| `warrants.bib`, `paper.toml`, `checks/corpus.py` | **2026-08-17** | `89f266e` |
| `pyproject.toml`, `uv.lock`, `mise.toml` | **2026-08-17** | `3ffd794` |
| `.bazelrc`, `MODULE.bazel`, `tools/verb.bzl`, `tools/verdict.py`, `tools/gen_gate_build.py`, `tools/import_closure.py`, `tools/check_status.sh` | **2026-09-03** | `2315c2c` |
| `tools/mypy-tool.{in,lock}`, `tools/substrate_ext.bzl`, `tools/substrate_wheel.bzl` | **2026-09-05** | `21ee11d` |

⚑ **The test design predates the build design by two and a half weeks; the hermetic/RBE layer is two
days old at survey time.** Any window shorter than 20 days severs the two. This is `§W`'s
justification confirmed from inside one leg.

---

## §Q-1 — Dependency declaration: five surfaces, three pinning strengths

`citation` throughout.

- **`mise.toml`** — the interpreter: `python = "3.13"`.
- **`pyproject.toml`** — six runtime deps, all **floors (`>=`), not pins**; the pin lives in
  `uv.lock`. Dev group adds `substrate-tooling = { path = "../substrate" }`.
- **`MODULE.bazel`** — `rules_python 1.0.0`, `platforms 0.0.11`, plus a `pip.parse` hub
  `gate_pip` reading `//tools:mypy-tool.lock`.
- **`tools/mypy-tool.lock`** — a **second, hand-transcribed lock** with `--generate-hashes`.
- **`.bazelversion`** — `8.7.0`.
- **`corpora.tsv`** — a hand-maintained pin table for **28 source corpora**.

### LS-02 ⚑ Two locks that must agree by hand

`uv.lock` governs the host venv; `tools/mypy-tool.lock` governs the hermetic sandbox mypy.
**Nothing mechanically proves they agree.** The binding is prose in `mypy-tool.in` (`citation`):

> ⚑ Every version here is transcribed from uv.lock; a bare `mypy==2.3.1` re-resolves ast-serialize
> to a NEWER version than uv.lock pins (measured: 0.9.0 vs 0.8.0), which would skew the sandbox mypy
> off the host one. Pin the whole closure explicitly.

`inference`: this is a real un-gated dependency edge in a repo that gates almost everything else.

### LS-02b — `ref` is what was asked for; `revision` is what was received

`corpora.tsv` header (`citation`):

> ⚑ A tag is a NAME and can move (measured: a repo whose only "release" tag pointed at a
> three-year-old tree). A commit is a RECORD. Where they differ the revision governs, and a ref of
> `master` is a SNAPSHOT honestly labelled — **not a pin, and it must not be quoted as one.**

⚑ **Vantage-local:** this repo pins **bazel's own source** (`8.7.0 @ a6d8d66`) as a readable corpus,
and read the action-key algorithm out of it. See LS-09.

---

## §Q-2 — Dependency discovery: mechanized in three layers

⚑ **This is the strongest item in this repo, and each layer was built after a measured stale-green.**

### LS-03 — `tools/import_closure.py`: closure as a correctness requirement, not an optimization

`citation`:

> A per-file check caches correctly only if its cache key covers everything the result depends on.
> For mypy that is the file PLUS its transitive first-party import closure … Running mypy on A
> alone, with B stubbed to `Any`, silently SUPPRESSES that error. **So the closure is not an
> optimization; it is what makes per-file caching correct rather than fast-but-wrong.**

The return type is **three-state, deliberately** (`citation`):

```python
class ImportScan(NamedTuple):
    first_party: set[str]
    unresolvable: set[str]
    dynamic: set[str]
```

> ⚑ THE UNDER-COVER IS A TYPED, VISIBLE STATE -- NOT A SWALLOWED ONE. The trap for a closure tool
> is not "the closure is wrong"; it is "the closure dropped an unresolvable import and returned
> success", so the caller reads absence-of-error as coverage.

`machine` — I ran `--selftest` live: **nine adversarial arms, all PASS.**

⚑ **The hermetic reader found what the host reader hid** (`citation`):

> Measured: the hermetic sandbox mypy reported `Module "linux_sources" has no attribute
> "corpus_census"` because the submodule was unstaged -- the toolchain-tier host mypy hid it (the
> whole tree was present). **A closure that misses a submodule import is a false-complete closure,
> and only a hermetic reader surfaces it.**

### LS-04 ⚑ `gen_gate_build.py`: discovery of IMPLICIT deps, fail-closed — the most transferable artifact here

1,905 lines enumerating **seventeen numbered adversaries**, each a class of missed dependency.
Samples (`citation`):

- **Stub files** — *"the stubs are the typed boundary for UNTYPED external packages … reached by
  runtime `sys.path` insertion -- so they are in no first-party import closure and were in no
  slice's `data`. A `.pyi` edit flipped the stubs verdict while invalidating no key: a stale-green."*
- **Roster tool contents** — *"**the set-vs-content gap** -- the roster tracks WHICH tools carry a
  selftest, never WHAT the selftest does."*
- **Second artefact of one generator** — *"**the drift-detector cache-hit green over the very file
  it exists to check.**"*

⚑ **It refuses to emit a graph it cannot prove complete** — three exception classes, three exit
codes (`citation`): `_STALE = 3`, `_UNDERCOVER = 4`, `_OPAQUE = 5`.

> `UnderCoverError`: Raised, never papered over. A whole-tree fallback would cache-bust the world on
> any edit … and hide that the closure was indeterminate. The honest response is a HARD FAIL naming
> the file and its gap -- **fix the import, not the key.**

The subprocess net is **fail-closed over a bounded set** (`citation`):

> a third adversary showed the net was fail-OPEN … Unlike argv SHAPES (unbounded), the spawner
> FUNCTIONS are a finite, stable set -- so enumerating them is bounded and **ends the treadmill.**

`machine` — `gen_gate_build.py --check` → **exit 0**. The generated graph is currently honest.

### Implicit deps this repo names explicitly

`citation` — a binary on PATH (`bazel`, `shellcheck`, `uv`, `mksquashfs`); a file at a fixed path
(`~/.cache/linux-sources/*.sqfs`, `/usr/src`); **a sibling repo at a fixed relative path**
(`../substrate` as a hard build edge, `../summit` as a live read); a service on a port
(`grpc://127.0.0.1:31985`); five `*_HOOK_BLOCK` env vars; two forge endpoints.

---

## §Q-3 — Acquisition: six routes, deliberately not unified

| route | pinned by | cold behaviour |
|---|---|---|
| interpreter | `mise.toml` | mise installs |
| runtime/dev deps | `uv.lock` | uv resolves + a **git fetch for paperkit** |
| `substrate-tooling` | **the sibling working tree** | requires `../substrate` to exist |
| bazel modules | `MODULE.bazel.lock` | bazel fetches |
| hermetic mypy | `mypy-tool.lock` + hashes | bazel fetches, hash-verified |
| substrate wheel | ⚑ **nothing — tracks the sibling's HEAD** | `uv build --wheel` at fetch time |
| kernel corpus | `dpkg-query` at read time | **UNAVAILABLE, not a failure** |
| 28 source corpora | `corpora.tsv` revision | absent = UNAVAILABLE |

### LS-05 ⚑ A hermeticity trade recorded as a trade

`citation`, `substrate_wheel.bzl`:

> ⚑ NOTHING IS COMMITTED AND NOTHING IS STALE. The wheel is built from ../substrate's CURRENT
> sources every fetch … **no vendored binary in this librarian's ledger** (which would merge the
> ledger with its subject, the distinction this repo is organized around) … The cost is the honest
> one: ../substrate must be present beside this repo, and this build reaches into it -- **a real
> cross-repo build edge, chosen deliberately over a committed artifact.**

`inference`: the build is hermetic **given `../substrate`**, and not otherwise. Neither vendoring nor
a registry — a third thing, **and it has no pin.**

### LS-06 ⚑ A measured failure of the symlink-adoption pattern

Four hooks are symlinks into `../substrate/scripts/`. `citation`:

> measured: substrate moved arg_after behind `substrate.ratchet_flags`, `_ROOT` through the symlink
> resolved to THIS repo (not substrate), the import raised ModuleNotFoundError, and **the hook
> exited 0 = ALLOW — a gate that had silently stopped gating.**

Fixed by installing `substrate-tooling` into the venv **without un-symlinking**.

### LS-06b — the corpus fetcher refuses to overwrite

`citation`: *"An existing name REFUSES unless --replace is passed, and even then the old image is
kept"* — because *"apt destroyed its own history by overwriting a tarball in place, leaving this
delegate's image the only surviving copy of 7.0.0-29.29."*

---

## §Q-4 — Hermeticity

### The tier model — `_tier_exec` (`citation`, verbatim)

```python
sandbox   — hermetic, cached. (Default; no special execution_requirements.)
local     — host-coupled and UNCACHED. The check reads unpinned live state that Bazel cannot
            hash, so a cached verdict would bank a host-dependent die-roll.
toolchain — host-coupled but CACHED, stamped with the corpus fingerprint (ctx.info_file).
```

`machine` — counted live in the generated `BUILD.bazel`: **261 `pk_cmd` targets — 246 sandbox,
9 toolchain, 6 local.** 94% of the graph is hermetic.

⚑ **The `local` tier IS the declared undeclared-reach**, and it is uncached *because of that*
(`citation`): *"if it reads live state, a cache banks a reading of a world that has changed."*
`_LIVE_STATE_SLICES = {"topology", "debsrc", "registry"}`.

### LS-07 ⚑⚑ A VERSION BANNER IS NOT THE BYTES — a toolchain verdict survived a changed linter

**This is `§Q`-4's marquee item — "a gate that passes by not running" — measured here two days ago**
(`citation`, `check_status.sh`, HEAD commit):

```
  before  STABLE_TOOL_RUFF ruff 0.16.5   sha256 024cdfbb…
  after   STABLE_TOOL_RUFF ruff 0.16.5   sha256 94fde127…      <- payload changed
          bazel build //:lint  ->  1 ACTION CACHE HIT
```

> ⚑ **A TOOLCHAIN-TIER VERDICT SURVIVED A CHANGED LINTER BINARY.** `--version` is a banner a
> rebuilt, patched or substituted binary keeps … So the version key detects an UPGRADE and is blind
> to a **REPLACEMENT** — which is the case a pinned environment actually produces.
>
> ⚑ AND THE ARM THAT FOUND IT IS THE POINT: this file's stamping was already proven to invalidate,
> on `STABLE_CORPUS_ROSTER` — a CONTENT HASH. **That green certified the MECHANISM and said nothing
> about the keys beside it. Run the arm PER KEY, not per mechanism.**

⚑ `testimony` **appearing in this repo's bytes**: the arm was run here *after paperkit ran it in
theirs*. **A cross-repo defect propagation with a witness** — apex material for §Q-8.

### LS-08 — the same defect one layer up, on the corpus label

`citation`: *"apt overwrites its tarball in place on upgrade, so a same-version security respin can
serve NEW bytes under an UNCHANGED `7.0.0-30.30` label … a stale-green."*

### LS-09 ⚑ The action key, read from bazel's own pinned source — vantage-local

`citation`, `.bazelrc`:

> ⚑⚑⚑ AND THE ACTION KEY IS NOT A MYSTERY — IT IS READ FROM SOURCE, bazel 8.7.0 (a6d8d66737d5), in
> the pinned corpus the whole time. **Two repos ran probes for weeks and neither opened the file.**

```
  ActionEnvironment.java:128-131
    f.addStringMap(getFixedEnv());       <- names AND values
    f.addStrings(getInheritedEnv());     <- ⚑ NAMES ONLY
```

> ⚑ SO execution_requirements IS KEY MATERIAL, fingerprinted TWICE. **A local-tier and a
> sandbox-tier action with identical argv and inputs are DIFFERENT ACTIONS and cannot collide in a
> shared CAS.**

⚑ **And it retracted its own alarm** (`citation`): *"THE `toolchain` TIER IS SOUND ON THIS AXIS …
Recorded because the first read of the key made it look like one, and **an unretracted alarm is its
own defect** — a reader would have added a no-cache that costs the tier its whole purpose."*

### LS-10 ⚑⚑ Agreement between two instruments that share a blind spot

`citation`: *"BOTH REPOS' EMPIRICAL NOT-IN-KEY LISTS AGREED AND WERE BOTH WRONG HERE. A probe shows
only what varies when you vary it, and neither party varied PATH under an inherited-env action.
**AGREEMENT BETWEEN TWO INSTRUMENTS THAT SHARE A BLIND SPOT IS THE BLIND SPOT, TWICE** — the same
shape as the bare platform, which was one habit propagated by copying rather than two independent
bugs."*

⚑ `inference`: **this is a direct warning to the apex about its own span.** Two legs agreeing is not
corroboration when both inherited the same habit.

### The `.venv` is deliberately NOT wired into Bazel

`citation`: *"A .venv is a directory of pointers at host-absolute paths; staged into a sandbox it
would resolve OUT of the sandbox to the live working tree, and every check would read unstaged
sources and report green — **a sandbox escape that passes.**"*

---

## §Q-5 — Build design

`BUILD.bazel` is **456,436 bytes and GENERATED**; one `pk_cmd(verb="mypy")` per first-party file
(~246), 13 slice targets, 3 staleness checks, one `pk_gate_test`. The verdict is a **parsed record,
never a grepped string** (`citation`): *"Bazel is the proof structure; the record is the artifact a
downstream gate depends on."*

### LS-11 ⚑⚑⚑ Remote execution witnessed for the first time — and it had never worked

`citation`, three-armed on a clean tree:

```
  P  --config=remote                          -> 11 processes: 9 internal, 2 REMOTE
     (re-run)                                 -> 3 processes: 2 REMOTE CACHE HIT
  F  --config=remote --remote_executor=:39999 -> Connection refused, exit 34
  C  no --config=remote                       -> 1 linux-sandbox
```

> ⚑ THE F-ARM IS WHAT MAKES THE P-ARM MEAN ANYTHING, and it took three attempts to make honest: at
> a dead endpoint bazel first reported `12 action cache hit` and then `1 internal` — **GREEN both
> times, having never contacted the executor.**

### LS-12 ⚑⚑ The removed guard was the instrument

`citation`: *"`--remote_local_fallback` IS WHY NOBODY SAW IT. It caught the analysis failure and
returned green with zero remote actions … **A guard removed because it was WRONG also removed the
thing that was HIDING a defect.**"*

And the decline itself (`citation`, quoting the operator): *"it evades the scheduler and consumes
resources against the very same machine the scheduler is protecting" … **That is a budget breach
wearing the costume of graceful degradation: the control is present, plausible, and inert exactly
under load, which is the only time it matters.**"*

### LS-13 — `--remote_instance_name` partitions the cache; four-armed with a control

`citation`: arm 4 is a control proving the probe *can* detect a hit under the same foreign name —
*"Without a control … 're-executed' and 'my probe is broken' are indistinguishable."*

⚑ `testimony`: *"MTOOLS MEASURED THE OPPOSITE AND HAS SINCE REVERSED IT … **NEITHER OF US CAUGHT OUR
OWN** — which is the argument for publishing a rule where a DIFFERENT party reads it."*

### LS-14 ⚑⚑ A null result from a well-run probe

`citation`: *"I built an instrument to detect a distinction that does not exist, then reported the
null result as a bound on my ACCESS rather than on the QUESTION … **a null result from a well-run
probe is evidence the QUESTION is wrong at least as often as it is evidence the ACCESS is short.
Ask what would DIFFER before building the arm.**"*

### LS-15 — fail-fast, and the load-bearing clause

`citation`: the operator asked four times; `--[no]keep_going` defaults **false** but
`--[no]test_keep_going` defaults **true**, so *"INCLUDING TESTS"* was the whole gap. ⚑ *"A PRIOR
SESSION OBSERVED THE ABSENCE AND DID NOT CONNECT IT TO THE RULING … **The push was absorbed as an
observation and the change did not happen.**"*

⚑ **VERIFIED, then BOUNDED — two corrections to this item, post-filing (2026-09-06).**

**(a) The defaults table is a citation, re-read live** (`machine`, `bazel help test`, 8.7.0 on this
box): `--[no]keep_going [-k] (default: "false")` / `--[no]test_keep_going (default: "true")`.
Confirmed, not recalled.

**(b) ⚑ THE BEHAVIOURAL ARM COULD NOT BE REACHED, and this item does not claim it.** Attempted:
`//:gate`'s critical path is a single toolchain-tier action (`PkCmd warrants.verdict.json`) still
running at **407s** with 15 of 17 actions complete. `--check_up_to_date` confirms the action is
**legitimately stale**, so that is the cache behaving correctly and not a tier defect — the
non-result is a real bound, not a broken instrument. **A flag governing what happens AFTER a test
fails cannot be observed until a test RUNS.** State: *correct by citation, unexercised by
measurement.*

**(c) ⚑ SCOPE CORRECTION — this is a finding about THIS REPO'S config, not an ecosystem default.**
The `.bazelrc` comment's framing *"the operator asked for this FOUR TIMES and no repo had it"* is
about the ruling's reception, and a reader may take it as a claim about the fleet. `testimony`
(`cassian-observability`, 2026-09-06): cassian sets `--notest_keep_going` **nowhere** — grep of its
`.bazelrc`, no match. **So the absence is real elsewhere and this leg makes no claim about whether
that is a defect there.** Per `§T`, a constraint measured in one repo is not automatically the same
kind of thing in another.

---

## §Q-6 — Test design

**A test here is three different things**: a **warrant** (42 `@misc`, each `check = {corpus:…}` or
`{gate:…}` → one of 35 fact modules); a **gate slice** (13); a **tool selftest**.

Evidence is a **field, not prose** (`citation`): *"in prose a measurement is testimony, in a field it
is a record."* Argument and measurement are **fused deliberately**: *"A partition into 'shape-claim'
plus 'evidence' keeps the magnitude and destroys the orientation."*

### LS-16 ⚑ Falsifiability is PROVEN, by mutation — not merely observed

`citation`, `corpus_audit`: *"`--mutate` re-runs each predicate where its claim is FALSE and reports
any mutant that SURVIVED — **a predicate no mutant breaks is decoration.**"* Two mutation kinds:
corpus bytes **and this repo's own tool source**.

⚑ **A no-op mutant reads as detected, and the audit catches it** (`citation`):

> ⚑ A MUTANT WHOSE `old` IS ABSENT IS A SILENT NO-OP, and it reads as DETECTED … Either way the line
> claims a discrimination never exercised. **Cheap to decide here and impossible to notice from the
> output.**

Verdict vocabulary is five-valued: `HOLE`, `INVALID`, `SKIP`, `UNAVAIL`, `ok`. And an uninterpretable
arm is refused: *"SKIP — fails unmutated, so mutants are uninterpretable."*

### LS-16b — every slice refuses an empty population

`citation`: *"**a search that found nothing is BROKEN, not clean.** Each slice states `n of m` and
fails when m is zero."*

### LS-16c — the build system's own documentation is gated by the build system

`gate-architecture/` binds each architectural claim to the source line recording it via
`traces:<path>#<needle>`, and declares its own honesty tier (`citation`): *"a `traces:` check proves
the claim is RECORDED where it says, **NOT that the mechanism is globally proven**."*

---

## §Q-7 — Gate design, and HAS IT FIRED?

### LS-24 ⚑⚑ FOUR GATES FIRED ON ME DURING THIS SURVEY — `machine`, not `citation`

I did not set out to test the gates. **They refused my survey commands.** 12 refusals:
`hook_no_chaining` ×4, `hook_structural_query` ×5, `hook_shellcheck` ×3.

⚑ **This is the strongest possible answer to "has it ever fired": the instrument surveying the repo
was constrained by the repo's own gates, in this session, without either being arranged.**

### LS-25 ⚑ Two measured FALSE POSITIVES in `hook_no_chaining`

A `|` inside a **quoted string argument** — not a shell pipe — triggered refusal twice:
`git log --format='%h|%ad|%s'` and `grep -rn 'a\|b'`. **The predicate reads shell metacharacters
lexically, not syntactically.** `inference`: fail-*closed*, so the failure direction is correct — it
costs a round-trip and admits nothing unchecked — but it is real and I hit it twice in one survey.

### LS-26 ⚑ A measured coverage boundary in `hook_structural_query`

`grep` over `.py`/`.md` → **refused**. `grep -c` over `.bazel` → **allowed**. Per SKILL.md's own
note, *"a suffix claimed by no row is a suffix the hook will not guard"* — so `.bazel`, `.bzl`,
`.bib`, `.tsv`, `.sh` are **unguarded**. That is a coverage statement about the routing table.

### LS-17 ⚑ The F-arm's own environment was contaminated

`citation`: *"`.claude/settings.json` sets both arming variables in `env`, so a Claude session
inherits them … **A guard verified only under the environment that arms it cannot distinguish
'denies because armed' from 'denies always.'**"* The fix is a **predicate over the population**
(`k.endswith("_HOOK_BLOCK")`), not a literal list — *"EVERY ARMING VARIABLE MUST BE SCRUBBED, NOT THE
TWO THAT EXISTED WHEN THIS WAS WRITTEN."*

### LS-18 ⚑⚑ The config was correct and the gate was not using it

`citation`, 2 days old: *"until now **every commit this hook gated ran LOCALLY SANDBOXED with no BES
record: measured, the runs reported `246 linux-sandbox` and zero remote actions** … **THE CONFIG
BEING CORRECT AND THE GATE USING IT ARE TWO DIFFERENT FACTS** … A configuration nothing invokes is a
claim, not a control."*

### LS-18b — three of five PreToolUse hooks fail OPEN, each saying so once

`citation` — deliberate, with a per-hook reason: *"the cost prevented is a WASTED GATE RUN, not
corruption, and a guard that refuses everything whenever it cannot tell is worse than the problem."*

⚑ **The unarmed-clone hole is named, not hidden** (`citation`): *"NOTHING ENFORCES THAT ARMING STEP,
AND ITS ABSENCE IS INDISTINGUISHABLE FROM A GREEN BOARD"* — citing gcalculus' summit filing
`friction-a-guards-silence-is-indistinguishable-from-its-approval`.

---

## §Q-8 — What this repo RE-DERIVED ⚑ (highest value per §Q)

| # | artifact | status |
|---|---|---|
| **LS-19** | `tools/verb.bzl` | **Adopted from paperkit, reduced** — `pk_file`/`pk_result`/`pk_agree` declined by scope. ⚑ **But `_tier_exec`'s three tiers are this repo's own.** Apex: does any peer have a tier model, and is it these three? |
| **LS-20** | `tools/import_closure.py` | **Re-derived**, rejecting an in-repo alternative as unsound for a cache key. ⚑ It **credits substrate for the measurement that justifies it** (`type_scope.py`: 3 findings → 231). **substrate held the number; the closure computer did not exist.** That is a defect report about substrate. |
| **LS-21** | `tools/gen_gate_build.py` | **Re-derived from substrate's makefile-generator pattern, emitting a bazel DAG.** ⚑ The **1,905-line completeness net is entirely local** — 17 adversary rounds, no adoption claim. **If any peer has a subprocess-completeness net, that is ~1,900 duplicated lines.** |
| **LS-22** | `check_status.sh` bytes-stamping | ⚑ **The ARM propagated from paperkit; the FIX was re-implemented here.** Transferable half is the rule: *"Run the arm PER KEY, not per mechanism."* |
| **LS-23** | `mdstruct.py` / `pycodemod.py` | **Not re-derived — borrowed by path.** ⚑ A hard cross-repo path dependency **inside a hook's routing table**, unpinned. A peer moving `scratch/` makes this repo's guard name a tool that does not exist. |
| **LS-28** | the four hooks | **Not re-derived — adopted by symlink.** `citation`: *"the established adoption route (freecell, el-openglo and gabion took the same one), not a copy."* ⚑ **Three repos on that route are not on §R.** |
| **LS-29** | `hook_gate_running`, `hook_pycheck` | **Held as CODE deliberately** — `citation`: *"mat260's ruling is that residency of a capability whose tree may be erased means holding the CODE."* ⚑ **`mat260` is RETIRED per §X, and its ruling is currently load-bearing in this repo's gate.** |

---

## §Q-9 — What this repo DECLINED, with reasons

`citation` throughout. Selected; the full set is 17.

| declined | reason |
|---|---|
| ⚑ **`membudget`** | **Superseded by the remote executor's queue** — *"A queue with N executor slots IS a cap of N … **That is membudget's own block-don't-refuse contract implemented by a scheduler instead of a semaphore.**"* |
| `--remote_local_fallback` | budget breach (LS-12) |
| `--jobs` / `--local_resources` | *"bazel's own per-action concurrency budget is not second-guessed"* |
| substrate's `resource_set`-is-a-hint critique | ⚑ **a declined critique with a self-correction**: *"does NOT transfer here **and I over-extended it once**"* |
| wiring the uv `.venv` into Bazel | *"a sandbox escape that passes"* |
| editable install of substrate-tooling | *"invisible to mypy by construction"* — 13 red errors measured |
| `[[tool.mypy.overrides]]` | *"one module gets exempted, the exemption outlives the reason … that is a **FINDING ABOUT THE DESIGN**"* |
| a curated ruff subset | *"a selection silently omits whole families, and the omission is invisible afterwards"* |
| pylint | ⚑ **adopted `earley`'s config verbatim instead** |
| full vendoring of the 4 hooks | cost enumerated, *"**Not worth it.**"* |
| an over-cover closure fallback | *"it hides that the closure was indeterminate"* |
| committing the corpus image / the substrate wheel | *"would merge the ledger with its subject"* |
| `.agda` in the routing table | ⚑ **a decline to over-claim coverage** |

### LS-27 ⚑ The `membudget` negative, per brief §5

```
claim:             no vendored copy of membudget, and no membudget import, exists in
                   linux-sources
spelling searched: `membudget` (case-insensitive)
denominator:       248 first-party .py + .bazelrc + .bzl + .toml + CLAUDE.md + NEXT.md
shapes read:       .py .bzl .bazelrc .toml .md
shapes empty from my reader: .sqfs (binary corpus images — not read)
reader:            GNU grep -rn / -rln; harness Read
positive control:  `grep -rn 'membudget' .bazelrc` returns .bazelrc:62 — the same
                   spelling IS found by the same reader in this corpus.
```

**Conclusion: this repo read membudget's contract and declined it with a mechanism argument.** A
decline with a reason is a design constraint, not fragmentation.

---

## §Q-10 — What BINDS this repo today

⚑ **The six `local`-tier targets: the uncacheable, unremotable, always-run serial tail.**

`inference`, grounded: 246 sandbox targets are elastic (remotable, witnessed); 9 toolchain targets
cache on the stamp; **6 local targets carry `no-cache` + `no-remote` and run on this box every
commit** — `debsrc`, `topology`, `registry`, `routes`, `instruments`, `arch`. This repo measured its
own tail and named the worst two (`citation`): `gate_differential.py` at **122s**, `participants` at
**60s**, *"the instruments slice is TAIL-BOUND by them."* Mitigation is conditional deferral, not
parallelization.

⚑ **What binds is not "the gate is slow" — it is that six verdicts are definitionally host-coupled,
and this repo has correctly refused to cache or remote them.** The constraint is a consequence of a
correctness decision.

⚑ **Secondary, and possibly dominant right now:** the pre-commit runs `--config=remote` with **no
local fallback**, so an executor outage makes every commit **refuse**. Per §X the executor is
degraded (ghost Valkey shard). `inference`: **this repo is fail-closed onto a known-degraded shared
service, by deliberate design** — and per §X that is environmental, not evidence about this
configuration.

---

## LS-30 ⚑ Roster nomination — six parties, five not on §R

1. **`substrate`** — on §R ✅, but the **direction** matters: four load-bearing symlinks into
   `../substrate/scripts/`, two routing-table entries into `../substrate/scratch/`, and a build-time
   `uv build --wheel` against it. **If substrate's leg does not report being a *consumed*
   dependency, the span will under-count.**
2. ⚑ **`earley` — NOT on §R.** Holds the **house lint/type standard this repo adopted verbatim**. A
   census of dependency declaration that omits the party whose config is copied into two repos'
   `pyproject.toml` is missing the origin.
3. ⚑ **`summit` — NOT on §R.** A **live, uncacheable build input**: the `registry` slice is
   `local`-tier *specifically because* it reads summit's working tree.
4. ⚑ **`gcalculus` — NOT on §R.** An external dependency of the 60s `participants` tool, and its
   summit filing is cited verbatim as the reason a design here exists.
5. ⚑ **`freecell`, `el-openglo`, `gabion` — NOT on §R.** Named as the three other repos on the **same
   hook-adoption-by-symlink route.** If the census wants adopted-vs-re-derived counts, three
   adopters are missing from the index.
6. ⚑ **`mat230`/`mat260`** — §X says retired and I comply. **But `mat260`'s ruling is load-bearing in
   this repo's `routes` gate arm today.** A retired party's directive is still in force here.

---

## Coverage — stated as inclusions (brief §3, §10)

```
A  root config/manifest files read in full                      -> 11
B  tools/ build engine read in full                             ->  5
C  tools/gen_gate_build.py — 1,522 of 1,905 lines (80%)         ->  1
D  test-design artifacts read                                   ->  6
E  corpus_fetch.py head (110 of ~600L)                          ->  1
F  git history: 231 commits; antecedent probe over 14 groups    -> 231
G  LIVE tool runs (machine, not file reads)                     ->  4
H  measured gate firings against my own commands                -> 12
                                                    TOTAL       -> 28 files + 231 commits

EXCLUSIONS, counted separately:
  CLAUDE.md (77,524 B), NEXT.md (133,764 B) — NOT read in full. This repo's claims
      ABOUT itself; citations-of-the-repo, never verification.
  BUILD.bazel (456,436 B) — grep -c only. Generated; a function of the generator I read.
  MODULE.bazel.lock, uv.lock, mypy-tool.lock — pin-line sample only, not parsed.
  ~383 lines of gen_gate_build.py; ~490 of corpus_fetch.py — unread.
  28 .sqfs images and /usr/src — binary / not the subject.
  findings/deps-build/ — FORBIDDEN pre-freeze. Not opened.
UNREADABLE / UNPARSEABLE: 0.
```

### ⚑ Reader-blind: my instrument was shaped by the subject's own gates

`grep`/`cat`/`wc` over `.py` and `.md` were **refused**; `.bazel`, `.bzl`, `.bib`, `.tsv`, `.sh`,
`.json`, `.toml` were **unguarded** and read textually. So my coverage is **systematically deeper on
unguarded suffixes** and **forced through whole-file `Read` on guarded ones** — biasing me toward
reading guarded files *completely* and unguarded ones *by pattern*.

⚑ **This is a real, measured instrument asymmetry that I could not have predicted before starting**,
and it is the inverse of a normal reader-blind declaration: the shapes my reader could not see are
the shapes it was *forced to see whole*.

---

## Termination line (brief §12)

**No.** A reader of this file alone could not reconstruct what was asked of the other legs. This file
answers §Q 1–10 for one repo, nominates six parties, and carries three cross-party items (paperkit's
stamp arm reaching here, mtools' reversed instance-name measurement, gcalculus' filed friction) as
**testimony appearing in this repo's own bytes** — not as adjudicated fact.

⚑ **Computing the span, identifying LS-19/20/21 against peers' equivalents, and deciding whether the
`_tier_exec` tier model or the 1,900-line completeness net is duplicated work, is the apex's job —
and per §R the apex is not me.**
