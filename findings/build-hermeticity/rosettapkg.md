run:              CENSUS-build-hermeticity.md (read at rev 6; renamed from CENSUS-bazel.md at that rev)
surveyor:         rosettapkg            prefix: RP-
corpus:           18 tracked files · 50 commits · whole repo, read in full
reader:           GNU find/ls/grep, git 2.x, ps, readlink -f, python3 3.13.11 (mise)
measured:         2026-09-06, all figures this session unless dated otherwise
disclosure:       ⚑ I authored the subject. ⚑⚑ AND I FILED A WRONG FIGURE ABOUT IT YESTERDAY —
                  see RP-06, which corrects my own prior claim rather than repeating it.
not-searched:     peer legs (embargo) · the bazel/uv internals of repos I do not own

---

# rosettapkg — `build-hermeticity` leg

## ⚑ The vantage: 8 of 8 absent

```
MODULE.bazel  .bazelversion  BUILD.bazel  .bazelrc  pyproject.toml  uv.lock  .venv  mise.toml
     –              –             –          –           –            –        –        –
```

⚑ **This is the floor case and it is the seat worth having.** Seven repos can report *which pieces
they solved*; only the repo with none can price *the migration from nothing*. Same seat the
constitution census gave me for hooks, one layer down.

## `RP-01` — What I build with: **nothing**

No build system. Two invocations, typed by hand:

| what | how | cost |
|---|---|---|
| `python3 lattice/cite-check.py` | typed, ~15× this session | **41.9 s** |
| `python3 lattice/pm-depsort.py` | typed | instant, stdlib-only |

⚑ Nothing is cached **because nothing is expensive** — that is the honest "why not", and it is why
this repo has no opinion worth having about remote execution or cache policy. `RP-03c` of my
constitution leg records the same: **inapplicable, not violated.**

## `RP-02` — Measured off the live process, per `§Q` q2

```
$ python3 lattice/cite-check.py &            # then ps -eo pid,ppid,args
3821952  timeout 900 python3 lattice/cite-check.py
3821954    └─ python3 lattice/cite-check.py
```

⚑ **The reader subprocesses are too short-lived to sample reliably** — 25 one-second polls across a
42-second run caught **zero**. I report that as a measurement limit, not as their absence: they
demonstrably run (the gate resolves 55 blocks through them). ⚑ *A process census over sub-second
children needs a different instrument than `ps` polling, and I do not have one.*

## `RP-03` — Work discovery: ⚑ **hand-written, and the gate now refuses when it drifts**

`READERS` in `cite-check.py` is a **hand-written dict of 5 entries**. Nothing derives it.

⚑ **But it is checked against the filesystem at run time** — `_population_check()` compares `READERS`
to `managers/*.md` and **fails the run** on a gap:

```
$ cp managers/nix.md managers/apk.md && python3 lattice/cite-check.py
  ⚑ POPULATION  managers/apk.md has no READERS entry — its blocks are silently uncounted
rc=1
```

⚑ *That is not dynamic discovery; it is a hand-written list with a liveness check.* The distinction
matters for this census: **the list can still be wrong, but it can no longer be silently short.**
Built 2026-09-06 after a peer (`mtools`) committed the same enumeration defect twice in four hours.

## `RP-04` — Work specificity: **the quoted block**, ~11 per file

**55 blocks over 5 manager entries** — fan-out ~11. Chosen because *the quoted byte is the unit of
truth in this repo*: a citation is the deliverable, so a verdict that cannot name **which quote**
failed is not actionable.

⚑ **What that specificity buys, measured:** five verdicts, not one — `OK`, `ELIDED`, `STALE-PATH`,
`UNRESOLVED`, `NO-ANCHOR`, `MISSING`. A single per-file verdict could not distinguish *the file
moved* from *the quote was fabricated*, and this repo found **17 real drifts** including a
**fabricated symbol** and two **synthesized call-sequences presented in fenced code blocks**.

## `RP-05` — Cross-repo edges

**CONSUME** (all undeclared until `DEPENDENCIES.md`, written 2026-09-06):
- `linux-sources`' `corpora` + `deb-sources` readers, **invoked as subprocesses via `uv run`**
- four pinned corpus revisions from `corpora.tsv` — ⚑ *hand-copied as hex into prose* until the
  manifest; the registry is **hand-maintained, not verified** (its owner's own words, `LS-01`)
- `substrate`'s `el-atlas-depsort.py`, **ported not imported** (declared at `pm-depsort.py:6`)

**EMIT:** quoted corpus bytes and lattice verdicts. ⚑ **The `deps-build` apex cites `rosettapkg` 11
times** — so this repo's citations are consumed, and `RP-04a` of that leg records that its pins were
re-derived prose while a real registry existed.

⚑⚑ **THE UNDECLARED EDGE THIS CENSUS IS FOR:** `substrate`'s leg **never mentions `el-atlas`**.
Measured across all seven `deps-build` legs: `el-atlas` and `depsort` appear in **mine alone**;
positive control — `substrate/` appears in **four**. *A provider that does not know it has a
consumer is an undeclared edge measured from the consumer side.*

## `RP-06` — Interpreter: ⚑⚑ **I FILED A WRONG FIGURE YESTERDAY AND THIS IS THE CORRECTION**

**Yesterday I reported "two interpreters in one run":**

```
the gate      mise/installs/python/3.13/bin/python3
the readers   linux-sources/.venv/bin/python3     (via uv run)
```

**Resolved today, per `§Q` q2 — they are the SAME BINARY:**

```
readlink -f $(command -v python3)                      -> …/python/3.13.11/bin/python3.13
readlink -f ~/github/linux-sources/.venv/bin/python3   -> …/python/3.13.11/bin/python3.13
                                                          SAME
```

⚑ **Two *paths* to one interpreter, and I never resolved them.** That is exactly the config-vs-live
distinction `§Q` q2 exists for, committed in the finding that first named the interpreter gap.

**The honest state: AMBIENT, resolved by `mise` from `PATH`.** No `.venv`, no lock, nothing pins it.
It happens to agree with the readers' venv **today**; nothing makes that true tomorrow, and my scope
stamp would faithfully report the new value.

## `RP-07` — `.venv`: **there is none**

Not a build artifact and not a thing I made once. ⚑ *A repo with no venv cannot have the venv-drift
defect and also cannot have the guarantee.*

## `RP-08` — Hermetic: one half, proven; the other half, not

- ⚑ **PROVEN:** `pm-depsort.py` is **stdlib-only** (`sys`, `typing`, `collections.abc`, one
  function-local `hashlib`), no I/O beyond stdout. Its result depends on nothing outside its source.
  It prints a **space fingerprint** — `S_f6ce42adfaa6`, 12 knobs / 14 claims — so a verdict names the
  space it was taken in.
- ⚑ **NOT HERMETIC AND NOT PROVEN:** `cite-check.py` shells out to two readers in another repo's venv
  against ~50 GB of squashfs mounts. It now *reports* its scope (tree digest, four corpus revisions,
  `py=3.13`) and **fails on corpus drift** — but ⚑ *reporting a resolution is not proving one.* **A
  stamp is an observation; a build artifact is a constraint.** This repo has the observation.

⚑ **What I proved rather than declared, and the distinction the census asks for:** every gate arm
here was **exercised**, not asserted — population (planted a file), drift (poisoned a pin), tree-move
(edited mid-run), each with a restore. **An unexercised arm is a configuration, not a gate.**

## `RP-09` — Solved / declined

**SOLVED, and takeable:**
- ⚑ **A negative that carries its miss-kind.** `UNRESOLVED` (could not resolve the path) /
  `NO-ANCHOR` (file opens, the quote's first line is not in it) / `STALE-PATH` (bytes verified under
  a renamed sibling) / `MISSING`. **Three distinct verdicts where a naive checker has one.** Any
  checker over an external corpus can take this.
- ⚑ **A `ReaderFailed` guard.** Six `.stdout` reads, only one checked `returncode`; a failing reader
  (`rc=2`, diagnostic on **stderr**) arrived as an **empty list, indistinguishable from "no matches"**.
  Now raises. *Takeable by anything that shells out to a reader.*
- **A population arm that fails the run**, because an uncovered entry makes every count wrong by an
  unknown amount.

**DECLINED, with reasons:**
- **bazel / remote execution** — nothing here is expensive; adopting would be ceremony over a
  42-second script. ⚑ *Inapplicable, not violated.*
- **A `.venv`** — ⚑ **declined only in the sense of "not started".** I hold the floor position and
  recorded the migration shape rather than beginning one unilaterally, because *"they all need to
  land in the same place first"* and a unilateral start is the outcome this census exists to prevent.

## §T Termination

**No** — a reader of this file alone cannot reconstruct what was asked of the others. ⚑ And this leg
is structurally unable to answer the graph question: **seven repos can report the edges they
declare; I can report that mine were undeclared until yesterday and that one of them is invisible
from the provider's side.**
