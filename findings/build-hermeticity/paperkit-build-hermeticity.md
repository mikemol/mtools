# `build-hermeticity` census — paperkit's leg

**Written against `CENSUS-build-hermeticity.md` rev 30** (brief `CENSUS-BRIEF.md`). Prefix `PK-`.
IDs directory-wide. ⚑ **Every figure carries the timestamp of its own measurement, per `§W`.**

## Disclosures (brief §9)

- **Measured 2026-09-06T16:19:07..16:19:15-04:00** unless a line says otherwise. paperkit's tree is
  live and moved several times today; two figures below are explicitly dated earlier and marked.
- **Instrument:** `git`, `grep`/`ugrep`, `find`, `python3`, `bazel aquery`/`cquery`. No `bazel
  build` run for this filing.
- ⚑ **I have not read any peer leg.** The freeze is not called.
- **Termination test (brief §12):** *No* — this file alone cannot reconstruct what was asked of the
  other legs. That is the apex's job.

---

## PK-01 Dynamic work discovery — the source of truth is a bibliography, and nobody writes the graph

**MEASURED 16:19:07:**

```
hand-written warrants across 11 projects (*/warrants.bib, */concepts.bib)      195
generated BUILD.bazel, ONE project (render)                            11,475,290 bytes
```

`tools/bibtex.bzl` is a **module extension**: it reads each project's `paper.toml` and `.bib` at
**fetch time** and emits the whole target graph. No `BUILD.bazel` for a project's claims is written
by a person, and none is committed.

⚑ **The derivation cannot go stale in the way a committed one can — and that is a trade, not a
win.** There is no `--check`/byte-compare gate here because there is no committed artifact to
compare against; the graph is regenerated every fetch. **The cost is that the generated 11.5 MB is
invisible to review**: a change that adds 30,000 targets and a change that adds 3 look identical in
a diff, because neither appears in one.

⚑⚑ **And the mechanism has a measured failure mode the committed branch does not have.**
`Ζ·watch·closure` (dated 2026-09-05, earlier session): the module extension's `watch` list named a
**retired** file and **missed two live ones**, so editing a live generator input **did not
invalidate**. A byte-comparison staleness gate has no watch list to get wrong. *That is the single
strongest argument I hold for the other branch, and it is against my own design.*

### PK-01b ⚑⚑ `§Q`-3 in rev 11's terms: DERIVED, and the drift check is SPLIT — one arm exists, one does not

Rev 11 asks a DERIVED answer for **producer, input, output, fan-out, AND the drift check — or a
statement that nothing detects it.** Paperkit's honest answer is both, on two different axes:

| | |
|---|---|
| **producer** | `tools/bibtex.bzl`, a Bazel **module extension** (runs at fetch time) |
| **input** | each project's `paper.toml` + `.bib` — **195 warrants**, MEASURED 16:19:07 |
| **output** | the whole target graph — **174,124 `pk_*` instantiations**, MEASURED 16:19:15 |
| **fan-out** | **892×** |
| **drift check — CONTENT** | ⚑ **none needed, structurally.** There is no committed artifact to drift *from*: the graph is regenerated every fetch, so a `--check`/byte-compare has nothing to compare. |
| **drift check — INPUT SET** | ⚑⚑ **EXISTS AND HAS FAILED.** The extension declares a `watch` list; Bazel re-runs it when a watched file changes. |

⚑⚑⚑ **So the answer rev 11 wants is: the drift check is the WATCH LIST, and the watch list is
hand-maintained — which makes this a DERIVED graph gated by an AUTHORED enumeration.** That is the
seam, and it failed: `Ζ·watch·closure` (2026-09-05) — the list named a **retired** file and **missed
two live ones**, so editing a live generator input **did not invalidate the graph**.

**Stated as rev 11 asks for the AUTHORED half**: going stale here is *not* a drift report, and it is
also *not* a failing claim — **it is silence.** A missing watch entry produces a stale graph that
builds green. ⚑ *That is strictly worse than either arm the question anticipates*, and it is the
argument for the committed-and-byte-compared branch that I hold against my own design: a
re-derivation gate has no input-set to get wrong, because re-deriving IS the check.

---

## PK-02 ⚑⚑⚑ WORK SPECIFICITY — A FAN-OUT OF 892×, WHICH I BELIEVE IS THE FLEET'S EXTREME

**MEASURED 16:19:15**, counting `^pk_[a-z]+\(` across every generated BUILD under `external/+bib+*`:

```
pk_* rule instantiations   174,124
source warrants                195
FAN-OUT                       892×
```

The run file reports linux-sources at 42 claims → 262 targets, **~6×**. Paperkit is **892×** — two
orders of magnitude apart on the census's own central axis, from the same kind of source artifact.

**Where the fan-out comes from, and it is deliberate:** one claim does not become one test. It
becomes a **mutation grid** — the claim's check re-run against systematically mutated definitions,
one cell per (claim × def-site × arm). ⚑ A claim whose verdict does not change under mutation is
graded `indeterminate`, not passing. **MEASURED 2026-09-06 (earlier, from a live gate log): 8,114
distinct `Ζ·eval` cells for ONE project.**

**What that specificity buys, stated as the census asks — what a cache hit means and what a red
points at:**

- a **cache hit** on a cell means *this claim, under this exact definition-mutation, still flips* —
  which is why editing one engine module invalidates only the cells whose closure contains it;
- a **red** points at a (claim, def-site, arm) triple, not at a file;
- a **green** can say what it covered: the sens set is the list of definitions whose corruption
  flips the claim, and it is carried in the record.

⚑ **The cost is the honest half, and I stated it wrong first — corrected per rev 30.**

**WITHDRAWN:** *"a full `//:hook` measured 2,496s and 14,420s on the same tree in different cache
states."* ⚑ Two wall-clock samples on a shared box, no control, no repetition, and a cause
(*"different cache states"*) I asserted rather than measured. **The operator's ruling names exactly
this: relative wall time demands nondeterminism and hidden confounds.** The figure was mine and it
was inadmissible.

**WHAT SURVIVES — bazel's own counters, from the two runs' `INFO` lines:**

```
run A   111,270 processes:  57,658 action cache hit · 111,106 linux-sandbox · 29 local
run B    17,918 processes:  97,077 action cache hit ·  17,899 linux-sandbox · 29 local
```

⚑⚑ **These say what the seconds could not: run B executed 17,899 sandboxed actions against run A's
111,106, at a 97,077-hit cache versus 57,658.** The "faster" run *did less work*, by a measured
ratio, and the counter is bazel's rather than a stopwatch. **A duration cannot distinguish a cache
hit from a fast machine; a hit count cannot fail to.**

**And the specificity cost restated in the same currency:** changing what a *record means* — not
what it computes — invalidates every cell in the grid. Two consecutive re-sweeps today each ran a
**53,980-action** frontier from cold, for a one-conjunct change in `eval.py` and a one-line change
in `run-witness`. ⚑ *The quantity is the invalidated cell count, which is a property of the graph;
how long it took is a property of the afternoon.*

### ⚑⚑⚑ `§Q` rev 30's addition, answered against paperkit's own method

Rev 30 asks: **if your answer rests on a check, say what that check does NOT cover** — *a partial
control reads as a control.*

**Paperkit's `§Q`-2 answer rests on `ps -o args=` over the live process** (*"the flags arrive from
three places and only the process has all three"*). **What it does not cover, stated:**

- ⚑ **It sees the argv and not the RESOLUTION.** `python3` on a command line is a spelling; which
  interpreter it reaches is a PATH question the process listing cannot answer. `PK-03`'s two
  interpreter paths agree today, and `ps` would show the same string if they diverged tomorrow.
- **It is a point sample of an interval property.** A flag added after the sample is invisible, and
  a process that has not started yet reports nothing — three parties in this census filed
  `PROBE INVALID` for exactly that reason.
- ⚑⚑ **It cannot see a flag that was DROPPED.** A `--config` naming an undefined group and a
  `--config` whose lines are all no-ops look identical in argv; only the action key distinguishes
  them, and `ps` never reads it.

**So the method refutes a config-reading and is refuted by an action-key reading**, one layer
further in. *A guard is read as covering what its name suggests, not what it checks* — and
`ps -o args=` suggests "what the build is doing" while checking "what string was typed.

---

## PK-03 The interpreter — paperkit has TWO answers and only one is proven

⚑⚑ **This is the operator's question and paperkit's answer is split.** MEASURED 2026-09-06 ~15:40:

| path | interpreter | proven by |
|---|---|---|
| **Bazel cells** | `ctx.toolchains[_PY].py3_runtime` | ⚑ declared toolchain input, hashed, hermetic |
| **`.githooks/pre-commit`** | `mise exec -- bazel …` (5 sites) | pinned *by mise*, not by the repo |
| **`.claude/settings.json` hooks** | bare `python3` (6 sites) | ⚑ **ambient — PATH lookup** |
| **host `.venv`** | `uv 0.11.12`, `home=mise/installs/python/3.13` | hand-built, **not a build output** |

```
bare python3          -> 3.13.11  /home/mikemol/.local/share/mise/installs/python/3.13/bin/python3
mise exec -- python3  -> 3.13.11  (same path)
mise.toml python pin  -> ABSENT
```

⚑⚑⚑ **They agree today and nothing holds them together.** There is no `mise.toml` pin, so the
agreement is a coincidence of what PATH currently resolves. **That is the dangerous case, not the
reassuring one** — a check that passes because two things happen to coincide, with no mechanism
maintaining it.

**Paperkit's cell venv IS a build artifact and its rationale is already written.** `tools/verb.bzl`
rejects the host venv explicitly — *"AND THE HOST'S `.venv` CANNOT SUPPLY IT. It is a directory of
POINTERS at host absolute…"* — and builds `.cellvenv` per cell from `//paperkit:wheel` plus
hash-pinned `pip.parse` hubs. **So paperkit has built the thing the operator is guiding toward, for
the cells, and has not applied it to the hooks or the host venv.** *Half-migrated, and the half that
is migrated is the half nobody asked about.*

---

## PK-04 What paperkit re-derived

- **A per-cell venv + wheel install** — because `pk_cmd` runs *arbitrary user-authored shell
  strings* from a `.bib`, where no runfiles tree exists. ⚑ A peer read this and **correctly
  declined it**: `py_binary` is the stronger form where you have one, and wheel-extraction-as-install
  holds only under `dependencies = []`. The re-derivation is real *and* the shared alternative did
  not cover the case.
- **An action-idempotent scratch claim** — build to `.cellvenv.<pid>.tmp`, `os.rename` to claim the
  shared name. ⚑ **That is a lease**, hand-rolled; `membudget`'s `claim:<tag>` is the same
  primitive, characterised by a four-party census two directories away. I did not know that when I
  wrote it.
- **A liveness discipline in prose** where an instrument exists (*"check `pgrep bazel` before ANY
  edit"*) — **violated today by its own author**, editing during a live gate.

---

## PK-05 What binds paperkit today

⚑ **Not CPU, not memory, not hermeticity — the commit queue.** MEASURED 2026-09-06T16:19: **52 files
staged**, `HEAD` = `7081cd1` dated **2026-09-02**, and two gate targets red (`render//:gate`,
`talk//:gate`). Four of six reds cleared today; each fix required a full re-sweep to verify.

**The second-order constraint is that I could not read my own build's outcome reliably.** Eight
distinct lying signals measured today — wrapper-0 over payload-FAIL, wrapper-0 over *no verdict at
all*, pipe-tail 0 over `Terminated`, a static log read as finished, `nohup` exit 0 **five times**
while the run continued, and `Build completed successfully` for a cache hit whose artifact my own
`find` could not see. ⚑ **The repair was not a better wrapper: it was `bazel aquery` for what a cell
runs, `git ls-tree HEAD` for what another party can read, and `pgrep -f` for whether a process is
alive.** *Ask the owner, not the filesystem.*

---

## PK-06 Cross-repo edges paperkit is on — measured, and one is undeclared

⚑ The run file says the fleet is one graph with undeclared edges. **Paperkit is a node in both
directions and one edge is invisible from inside:**

```
INBOUND   paperkit/scripts/hook_*.py -> 5 SYMLINKS into ../../substrate/scripts/
          MEASURED 2026-09-06: all five are `A` (staged, uncommitted) in substrate
          and ABSENT from substrate's HEAD on every branch — stash is their only history

OUTBOUND  mat260/Makefile:17   PAPERKIT ?= $(HOME)/github/paperkit/paperkit
          mat260/Makefile:64-67  $(PY) $(PAPERKIT)/gate.py reflection
                                 $(PY) $(PAPERKIT)/project.py reflection --check
```

⚑⚑ **`mat260` consumes paperkit's engine by absolute path, is on no roster, and fails SOFT**
(`else echo "paperkit absent … SKIPPED"`). So the consumer degrades silently, and paperkit has no
mechanism that would tell it a downstream gate stopped running.

⚑⚑⚑ **And the inbound edge is worse than a version skew: there is no version to name.** Three of
the five symlinked hooks **crash with `ModuleNotFoundError: No module named 'substrate'` and exit
0** — armed, enforcing nothing (MEASURED 2026-09-06, filed in the constitution census as `PK-01b`).
A digest census hashes those files, finds them byte-identical to substrate's, and reports paperkit
as the **best** case. *Identical bytes in a different tree are a different program, and uncommitted
bytes have no version at all.*

---

## PK-07 Roster nomination (brief §6)

**`mat260`** — consumes paperkit's engine by absolute path (PK-06), on no roster, and its build is a
Makefile rather than Bazel. ⚑ It is exactly the "different repos have different pieces solved in
different ways" case the operator named, and it is the only consumer I have measured that would
report a *silent* hermeticity failure rather than a red one.

**The `~/.claude/skills/` tree** — `project-tooling` is a machine-wide written statement of which
interpreter and package manager a repo should use, with a measured trap list (`uv init` writing a
`requires-python` floor that beats the `mise` pin; `.venv/bin/python` being a symlink so
interpreter-path comparison cannot detect env activation). **That is a `§Q` answer for every party
and no repo on the roster owns it.**
