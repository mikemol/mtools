# `LS-` — linux-sources' leg, build-hermeticity census

**Filed against `CENSUS-build-hermeticity.md` rev 21** (read from `git show HEAD:…` at mtools
`cd0a742`, **not** from a working tree — see `§V` rev 15 for why that distinction is load-bearing).
Prefix `LS-`, assigned in `§R`. **Measurement window `2026-09-06T16:30`–`17:00-0400`**; every
figure below carries its own stamp per `§W`.

## `§9` Disclosures, first — and this leg has the worst set

- ⚑⚑⚑ **I AM THE DISPATCHER.** I wrote `§Q`, `§R`, `§W`, `§X` and every revision through 21. **A
  fit between my answers and these questions is partly a fit between my answers and my own
  questions**, and it is worth less than any other leg's fit. *(`gabion-e5` stated this form first,
  about their own smaller version of it; it applies to me with no discount.)*
- ⚑⚑ **I have read six peer legs' EXISTENCE and none of their CONTENT.** `§2` binds until the
  freeze. What I have read is peers' **messages** — which is not the same restriction and is not
  covered by `§2`. **Several findings below were prompted by a peer's message**, and each says so.
- ⚑ **I filed LAST**, after every other live party. **Independence on `§Q`-2, `§Q`-5b and `§Q`-6 is
  compromised and not claimed** — three peers had already reported measurements on those axes and
  I knew what they found before I measured mine.
- **The operator corrected my framing four times** during this run (revs 2, 5, 6/7, 8) and once
  more on permission (rev 18). **`§Q`'s current shape is not mine alone.**

## `LS-01` · `§Q`-1 — what linux-sources builds with

| | |
|---|---|
| build system | **bazel 8.7.0**, plus a `.githooks/pre-commit` shell gate |
| invoked by | `core.hooksPath .githooks` on commit; and by hand |
| python | **uv-managed `.venv`**, `mise` for the interpreter |
| second surface | **`linux_sources/check.py`**, 13 slices, run independently of bazel |

⚑ **TWO GATES, ONE TREE, AND THEY DO NOT COVER THE SAME THING** *(measured 16:30)*. `check.py`
runs 13 slices unsandboxed; `//:gate` runs the bazel graph sandboxed. **Today `//:gate` refused a
commit that `check.py`'s `registry`, `mypy` and `lint` slices had just passed green** — an
undeclared input (`corpus_store/{paths,version}.py`) that is *present on disk* in the unsandboxed
run and *absent* in the sandbox. ⚑⚑ ***A green from the unsandboxed path is not evidence about the
sandboxed one; they are different populations.***

## `LS-02` · `§Q`-2 — measured off the live process

⚑⚑⚑ **PROBE INVALID FOR THE PROCESS ROUTE, AND I WILL NOT SUBSTITUTE A CONFIG READING.**

    pgrep -a -f 'hook_structural_query|hook_no_chaining|hook_pycheck'   (16:44)
      -> ONE match, and it was my own pgrep

**This delegate's hooks exit too fast for a point sample to catch.** Manufacturing a long-running
hook would measure a case that does not occur. ⚑ *`cassian` reported `PROBE INVALID` for a
different reason — their bazel gate is invoked by no hook, so no live process exists during a
commit — and `substrate` bounded theirs to a direct invocation because their standing rule is
stage-never-commit. **Three parties, three different reasons the question cannot be answered as
asked, and none of us faked it.*** **That is a defect in `§Q`-2, which I wrote.**

**What I measured instead, with the substitution declared** *(`scratchpad/interp_probe.py`, 16:47)*:

    which python3     /home/mikemol/github/linux-sources/.venv/bin/python3
    resolves to       ~/.local/share/mise/installs/python/3.13.11/bin/python3.13
    version           Python 3.13.11 (main, Dec 17 2025) [Clang 21.1.4]
    mise.toml         python = "3.13"

⚑ **BOUND: that is the resolution under MY shell. A hook spawned by the harness may inherit a
different PATH and that is NOT answered.** *`substrate` measured exactly this gap on their own
tree and found the venv resolves first while `/usr/bin/python3` runs — so the gap is real,
measured elsewhere, and unmeasured here.*

## `LS-03` · `§Q`-3 — work discovery: DERIVED, with a drift check that fires

**DERIVED.** `tools/gen_gate_build.py` reads two `warrants.bib` files and writes a **checked-in**
`BUILD.bazel`.

| | measured 16:52 |
|---|---|
| producer | `tools/gen_gate_build.py` |
| input | `warrants.bib` (42 claims) + `gate-architecture/warrants.bib` (35) = **77** |
| output | `BUILD.bazel`, **263 `pk_*` targets**, ~9600 lines, written by nobody |
| fan-out | **≈ 3.4** |
| drift check | ⚑ **`stale_gate_build`, and it FIRED TODAY** |

⚑⚑ **THE DRIFT CHECK IS NOT DECORATIVE — IT REFUSED MY OWN COMMIT.** `slice_registry` gained an
import of `corpus_store.version`; the generator traced it and added **two new declared inputs**;
`//:gate` refused until `BUILD.bazel` was regenerated. **A generated work list nothing re-derives
is a hand-written one with extra steps** — mine re-derives, and the proof is a refusal I could not
talk my way past.

⚑ **AND `substrate`'s CONTRAST IS THE FINDING, NOT MINE.** Their Makefile generator's input is the
**filesystem layout**, so it is *structurally incapable* of noticing that a warrant's inputs moved
— **`DERIVED, drift check ABSENT AND UNBUILDABLE AT THIS INPUT`.** *A drift check requires a
producer whose input can DISAGREE with reality; a glob's input IS reality.* **Same role, opposite
detectability, and neither of us could have seen it alone.**

## `LS-04` · `§Q`-4 — specificity, and what it costs

**Grain: per (claim × tier).** 77 claims → 263 targets *(16:52)*.

⚑ **WHAT IT COSTS, measured today rather than argued:** `//:gate` took **1831s** on a cold graph
and **117s** on the re-run, **264 action-cache hits**. *The fine grain is what makes the re-run
cheap; it is also what makes the cold graph expensive.* ⚑⚑ **And I nearly recorded that pair as
*the gate got faster*.** `rosettapkg`'s formulation is the one to keep: ***a cache effect looks
like a property of the CODE when read once and a property of the QUEUE when read twice.***

**One level coarser** — per-claim without tiers — would collapse 263 to 77 and **destroy the
distinction between a sandboxed and an unsandboxed run of the same claim**, which `LS-01` shows is
exactly the distinction that catches undeclared inputs. **The grain is load-bearing, not
aesthetic.**

## `LS-05` · `§Q`-5 — cross-repo edges, both directions

**CONSUMES:**

| edge | DECLARED or AMBIENT |
|---|---|
| `substrate` hook bodies — **4 of 7 hooks are SYMLINKS** into `../../substrate/scripts/` | ⚑ **AMBIENT** as a path; ⚑⚑ **DECLARED as a package** — `substrate_tooling-0.1.0` is a **copied wheel** in `.venv` |
| `substrate/scratch/pycodemod.py`, `mdstruct` | ⚑ **AMBIENT** — named in `.claude/skills/struct-tools/SKILL.md`, read at call time, in **no manifest** |
| `mtools/mdstruct/.venv/bin/mdstruct` | ⚑ **AMBIENT** — absolute path in prose |
| `summit/registries/` — a **sibling checkout** | ⚑ **AMBIENT**, and it *used to fail the gate* until today |
| `/usr/src` kernel source, `apt` | ⚑ **AMBIENT and UNVENDORABLE** — 206MB, deliberately untracked |

**EMITS:** ⚑⚑⚑ **quoted corpus bytes that peers cite in their own warrants — and `summit anchored
linux-sources` reports 0 records requiring this tree.** *That is TRUE and is exactly why nobody
would notice.* **A census of declared dependencies structurally cannot see what a tree EMITS that
someone else cites.**

⚑ **`▣39`, filed in my own ledger today:** my `hook_cmdparse.py` **is a symlink**, so
`Path(__file__).absolute()` derives *my* root and the `sys.path.insert` points at the wrong tree.
**It works only because the wheel is installed** — *the insert is dead code in my tree and
load-bearing in `gabion`'s, where the same two hooks crash, and nothing in either file says
which.*

## `LS-05b` · `§Q`-5b — invoked executables, and a correction to my own `§X`

⚑⚑ **MY `§X` SAYS "`shellcheck` AT 20 SITES" AND THAT FIGURE IS WRONG.** Structural count
*(`pycodemod --literal`, 16:55)*: **37 literal sites across 8 files** — and **most are messages,
docstrings and test names, not invocations.** *I counted string occurrences and reported them as
invocation sites: a population error in the dispatcher's own context section.*

**The honest answer** *(`_shellcheck_bin`, read 16:56)*: `shellcheck` is located by **PATH search,
then a `~/.local/share/mise/shims/shellcheck` fallback**, declared in **no manifest** — and the
hook **reports UNKNOWN rather than clean when it is absent**:

> *"⚑ AN ABSENT LINTER IS AN UNKNOWN, not a clean bill."*

⚑ **CORRECT BEHAVIOUR AND AN UNDECLARED DEPENDENCY ARE COMPATIBLE** *(`mtools`' formulation)* —
and mine adds a **hardcoded fallback path to another tool's shim**, which is worse than
undeclared: *it is declared in the wrong place, to a location no resolver reads.*

**Also invoked and undeclared:** `dpkg-query`, `apt-cache`, `git`, `bazel`, `pandoc` *(via
mdstruct)*.

## `LS-06` · `§Q`-6 — interpreter: AMBIENT, and pinned to a MINOR version

⚑⚑⚑ **ALL NINE HOOK REGISTRATIONS USE BARE `python3`** *(`.claude/settings.json`, 16:45)* — not
`.venv/bin/python`. **They resolve only because the harness's PATH puts my venv first.**

⚑ **AND THAT IS THE SAME PATH ORDERING THAT MADE ME FILE A FALSE REPORT AGAINST `summit` TODAY.**
`summit/scripts/summit` is `#!/usr/bin/env python3`; my PATH gave it **my** venv, which has no
`library` package, and I reported their ask-floor broken. *One accident, one wrong answer and one
right one, and nothing distinguishes them from inside.*

**The version pin is one level too coarse** *(16:47)*: `mise.toml` says `python = "3.13"`; the
running binary is **3.13.11**. **The patch level floats with whatever mise installed.**

⚑⚑ **AND NO GATE OF MINE CAN CATCH ANY OF THIS.** `check.py --only routes` passes **34 of 34**
with T- and F-arms on every hook — **while spawning them the way the harness does, so it inherits
the same PATH and cannot fail for this reason.** `checks/hookcensus.py` surveys 62 repos and
reports *which* hooks are wired and **not which interpreter runs them.** *A green produced by the
defect it would need to detect.*

## `LS-07` · `§Q`-7 — the `.venv` and the lock axis

**The `.venv` is a thing made once**, not a build artifact. `uv`-managed, gitignored, regenerable
in principle and **never actually regenerated**.

| property | measured 16:35 |
|---|---|
| set pinned | `uv.lock`, 547777 bytes |
| **content** pinned | ⚑ **YES — 1622 `sha256` hashes** |
| lock is **build key material** | ⚑⚑ **YES — a declared input to 12 bazel actions** |
| lock **freshness gated** | ⚑⚑⚑ **NO** — `grep uv .githooks/pre-commit` → **0** *(control: `bazel` → 11, so the zero is real)* |

⚑ **BEING A DECLARED BAZEL INPUT IS STRONGER THAN A CI CHECK AND STILL NOT THE MISSING PIECE.** A
lock change re-runs twelve actions **by construction** — enforcement nobody can skip. **What
nothing catches is a `pyproject.toml` edit that SHOULD have changed the lock and did not.** *Being
an input proves the lock is USED; it says nothing about whether it is CURRENT.*

## `LS-08` · `§Q`-8 — what is hermetic, and what fired

⚑⚑⚑ **PROVEN, NOT DECLARED, AND IT FIRED TODAY** — the strongest thing in this leg.

`//:gate` **refused a commit** on `stale_gate_build` because `slice_registry` gained an import and
`BUILD.bazel` had not been regenerated to declare it. ⚑ **`registry`, `mypy` and `lint` had all
just passed GREEN on the same tree**, because they run **outside** the sandbox where the
undeclared input is simply present on disk.

**That is a hermeticity check that would go red if hermeticity broke, and it did.**

⚑ **THE BOUND:** hermeticity is proven for the **sandbox-tier** actions. The `local` and
`toolchain` tiers are host-coupled **by design** and are not hermetic; `check.py`'s 13 slices are
not sandboxed at all. **The claim is scoped to the tier, not to the tree.**

## `LS-09` · `§Q`-9 — solved, and declined

**SOLVED, offered as takeable:**

1. ⚑ **A tree stamp on the gate verdict** (`◆62`, shipped today). `check: 13 of 13 slice(s) clean
   [tree 9afc93175cbf dirty]` — **three states**, `UNKNOWN` never rendered as a sha. **And `git
   write-tree` is the seductive wrong instrument**: it hashes the *index* and returns the
   byte-identical hash of a clean tree when a file is modified-but-unstaged. *Measured, both arms
   witnessed on real runs.*
2. **`gen_gate_build.py` + `stale_gate_build`** — a generator whose drift check can actually fire,
   because its input is a bib rather than a glob.
3. **A waiter that refuses to classify a lock.** Three discriminators for `.git/index.lock` were
   written and all three were wrong; the fourth artifact **waits on the condition and, at its
   ceiling, refuses to remove the lock and prints the discriminator instead.** *A commit that
   acquires the lock and then spends minutes in its gate writes NOTHING to the file, so mtime, size
   and age are silent for exactly the interval that matters.*

**DECLINED — HELD:**

- ⚑ **`--remote_local_fallback`.** Operator: *"it evades the scheduler and consumes resources
  against the very same machine the scheduler is protecting."* **The executor is colocated**, so a
  fallback action runs on the identical cores outside the executor's accounting. ⚑⚑ **And removing
  it is what made remote execution MEASURABLE** — it had been catching an analysis failure and
  returning green with zero remote actions.
- **`--stamp` beyond workspace status, and an `-Xmx` rung** — no measurement yet demands them.

**DECLINED — UNEXAMINED:** ⚑ **every binary in `LS-05b`.** *I never compared until `§Q`-5b made me
count, and then I miscounted.*

## `LS-10` · Roster nomination

**`memory-concepts`** — `cassian` nominated it from the consuming side and the reason is stronger
than the nomination: **`MEMORY.md` is projected from its `warrants.bib` with a byte-compare
freshness gate**, a `§Q`-3 **DERIVED** mechanism with a real drift check, **in a repo not
registered with summit at all.**

## `LS-11` · Coverage, as a population

**Answered from measurement:** `§Q`-1, 3, 4, 5, 5b, 6, 7, 8, 9 — **nine of nine**.
**PROBE INVALID:** `§Q`-2's process route, with the reason and the substitution declared.
**UNMEASURED:** whether a harness-spawned hook inherits a different PATH than my shell.

⚑ **Absences with controls:** the `uv`-in-pre-commit zero carries `bazel → 11` as its control.
**The `shellcheck` figure in `§X` had NO control and was wrong** — corrected in `LS-05b`.

## `LS-12` · Termination

⚑ **The dispatcher will not build the apex.** `§R` lists *a session with no leg* first and
**that is the preferred builder**; the constitution census's `AX-06a` — *an article's author is the
worst-placed party to find its violations at home* — applies to a run file's author with no
discount. **This leg is the eighth and last of the live-session tier.**
