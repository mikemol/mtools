# CENSUS: build-hermeticity — the dependency graph, work discovery, and work specificity

⚑ **This file was `CENSUS-bazel.md` through rev 4 and is renamed at rev 6.** The subject is not
bazel: **three of eight parties do not use it, and two of those hold substantial work-discovery
tooling anyway.** A run file named after one party's mechanism would have told five parties they
had nothing to report. *`§V` revs 2, 5 and 6 record the two scope corrections that produced this
name; the dispatcher got it wrong twice and was corrected both times.*

**Brief:** `CENSUS-BRIEF.md`. Read it first. This file overrides it where they conflict.

**Written against:** rev 1, 2026-09-06, by `linux-sources` as dispatcher. ⚑ **The dispatcher is
also a surveyed party**, which `§X` records as a known defect in this run's construction rather
than leaving for the apex to discover.

## §R Roster, prefixes, paths

| surveyor | prefix | file |
|---|---|---|
| `linux-sources` | `LS-` | `findings/build-hermeticity/linux-sources.md` |
| `paperkit` | `PK-` | `findings/build-hermeticity/paperkit.md` ⚑ **EXISTS, unconvened — see `§X`** |
| `mtools` | `MT-` | `findings/build-hermeticity/mtools.md` ⚑ **EXISTS, unconvened — see `§X`** |
| `cassian-observability` | `CO-` | `findings/build-hermeticity/cassian-observability.md` |
| `substrate` | `SB-` | `findings/build-hermeticity/substrate.md` |
| `summit` | `SM-` | `findings/build-hermeticity/summit.md` |
| `rosettapkg` | `RP-` | `findings/build-hermeticity/rosettapkg.md` |
| `gabion` | `GBB-` | `findings/build-hermeticity/gabion-build.md` ⚑ **PRE-FILED — see `§V` rev 2** |
| **apex** — a session with no leg, **or** a named party whose leg is filed and frozen first | `AX-` | `findings/build-hermeticity/build-hermeticity-apex.md` |

⚑⚑⚑ **AND THE ROSTER HAS THREE KINDS OF PARTY, NOT ONE — rev 9.** The eight above **have live
sessions** and can be dispatched. The twelve below hold warranted work-planning artifacts and
**do not**, so a leg from them requires **someone dispatching a subagent to read the tree**.
⚑ **And at least a couple are RETIRED, for which a leg is NOT OWED** — a state no prior census
of this dispatcher's has had, because every earlier roster was live sessions only.

| kind | parties | how a leg arrives |
|---|---|---|
| **live session** | the eight in the table above | dispatched; the party measures itself |
| **no session, active** | `gcalculus`, `memory-concepts`, `gkr-bugs`, `resumes`, `mat230`, `mat260`, `vm-manual`, `sre-troubleshooting`, `el-openglo`, `mikemol.github.io`, `cassian-obs`, `memmesh` | ⚑ **a SUBAGENT reads the tree** — third-party measurement, marked as such |
| **retired** | ⚑ **operator-held knowledge; see below** | ⚑ **no leg owed** — a remainder entry that is *not* an omission |

⚑⚑ **RETIREMENT IS NOT RECORDED IN ANY ARTIFACT, WHICH IS ITSELF A `§X` FACT.** Measured
2026-09-06, both directions:

    find <12 repos> -maxdepth 1 \( -iname 'estate*' -o -iname 'retired*' -o -iname 'archive*' \)
      -> 1 hit, and it is `mat230/archive` — a SUBDIRECTORY, not a marker
    summit delegate --all
      -> 20 delegates, EVERY ONE showing `listens=inbox/` or `-`; NO retirement state exists

**So "which of these is retired" is knowledge the operator holds and no instrument can answer.**
⚑ *A census that inferred activity from a tree would count a retired repo as a silent party —
the `no response` state — which is exactly the misattribution `§G`'s vocabulary exists to
prevent.* **The dispatcher will not guess it.**

⚑ **AND THREE OF THE TWELVE ARE NOT REGISTERED WITH summit AT ALL** — `memory-concepts`,
`gkr-bugs`, `vm-manual` hold warranted artifacts and appear in no delegate record. *A registry
miss is a fact about the index, never a claim about the world*, and here the index and the
population genuinely differ.

⚑⚑ **A THIRD-PARTY LEG IS NOT A SELF-SURVEY AND MUST SAY SO.** `§Q` opens *"survey yourself"*;
a subagent reading someone else's tree is doing something else. **Such a leg is tagged
`third-party measurement` in its first line**, and its claims are `machine`/`citation` provenance
only — ⚑ **it may not answer `§Q`-7 or `§Q`-9 at all**, because *what did you DECLINE and why* and
*what did you SOLVE* are questions only the author can answer. **A subagent reporting a decline
as UNEXAMINED when the absent author held a reason is a fabrication wearing a measurement's
provenance.**

**Conventions fixed here rather than negotiated:** filename pattern as above; ID prefixes as
above; all files land in `findings/build-hermeticity/` in **mtools**; quote the byte, cite file and line.

⚑⚑⚑ **THE ROSTER ABOVE IS EIGHT REPOS AND THE SUBJECT SPANS AT LEAST SIXTEEN — MEASURED AT
rev 8, AFTER THE ROSTER WAS WRITTEN.** Operator: *"you should look around for `.bib` files all
over, because a lot of them are actually cotype files."* Measured across `~/github`, excluding
`.git`, `.tmp`, agent worktrees, `.precommit-staged` and scratch mirrors:

    find ~/github -name 'paper.toml' …    ->  ⚑ 70 paperkit PROJECTS in 16 repos
    find ~/github -name '*.bib' …         ->  cotype/warrant bibs in the same 16

**Repos holding warranted work-planning artifacts that are NOT on `§R`:** `gcalculus`,
`memory-concepts`, `gkr-bugs`, `resumes`, `mat230`, `mat260`, `vm-manual`,
`sre-troubleshooting`, `el-openglo`, `mikemol.github.io`, `cassian-obs`, `memmesh`.

⚑⚑ **AND TWO OF THEM HOLD MECHANISMS `§Q`-3 CALLS RARE.** `el-openglo` has
`catalog/worklist/warrants.bib` **and** `catalog/cotype/warrants.bib` — *the same worklist shape
this file records as substrate's, which rev 7 nearly called unique.* And
`substrate/.claude/agents/paper.toml` makes **the agents themselves a gated paperkit project**
(`gate-oracle.bib`, **424525 bytes**). **Work planning is warranted at the agent level in at
least one tree.**

⚑ **THE ROSTER IS THEREFORE PROVISIONAL AND `§D` ADMITS LATE ARRIVALS BY DESIGN.** A repo absent
from `§R` is **not** excluded — it is one this dispatcher had not measured when writing rev 1.
*A roster built from "who do I talk to" and a subject that spans "who holds a warranted work
list" are different populations, and the first is the one that produced `§R`.*

⚑ **FOUR OF THE EIGHT ORIGINAL PARTIES HAVE BAZEL TODAY.** Measured 2026-09-06 from mtools:

    find ~/github -maxdepth 2 \( -name MODULE.bazel -o -name WORKSPACE -o -name .bazelrc \) -printf '%p\n'
      linux-sources, paperkit, mtools, cassian-observability     <- 4 repos, 8 files

⚑⚑ **THE OTHER FOUR ARE ON THE ROSTER DELIBERATELY AND THEIR LEGS ARE THE POINT, NOT A
COURTESY.** `substrate`, `summit`, `rosettapkg` and `gabion` build with `pyproject.toml` and/or
`Makefile`. **A party with no bazel is the only one who can say what adopting it from zero
actually costs**, which no already-migrated repo can measure — the lesson `rosettapkg`'s leg
taught the constitution census, where *"I hold zero hooks, so every article is a re-opening for
me"* was the finding no conformant repo could have produced.

⚑ **AND THE GROUPING MATTERS IN THAT `find`, WHICH I GOT WRONG WHILE WRITING THIS FILE.** Without
`\( … \)` the `-printf` binds to the **last** `-o` branch only and returns a *plausible partial* —
4 files instead of 8, the same repo set, no error. That is `▣36` in this tree's ledger, committed
live in the census that asks about build tooling. **Anyone measuring their own build files: group
the alternation.**

## §Q The question

⚑ **Survey yourself.** Report what *you* build with, what you solved, what you declined, what you
re-derived. Do not survey the others; `§R` tells you who else is reporting and that is all you
need to know about them. **Do not read peer legs until the freeze.**

**The operator's framing, quoted verbatim because the paraphrase loses the load-bearing half:**

> *"This is why I'm guiding everyone toward maintaining their .venv as a **build artifact** in
> their build process (which I'm guiding everyone toward migrating **that** to bazel), so that
> when we do a build in an enforced-hermetic environment, **the interpreter is specified and
> proven**."*

> *"This is why I want a census-kit over everyone's bazel (and other build systems)
> implementation details and capabilities; **solving this properly is complicated, and different
> repos have different pieces solved in different ways, and they all need to land in the same
> place first**."*

⚑⚑⚑ **AND THE SUBJECT IS BIGGER THAN EITHER QUOTE, WHICH THE DISPATCHER GOT WRONG TWICE BEFORE
BEING TOLD — SEE `§V` revs 2, 5 AND 6.** Rev 1 scoped this to *bazel*; rev 2 to *hermeticity and
a proven interpreter*. **Both are symptoms.** The operator's correction, and it is the subject:

> *"The problem is bigger than that."* … *"The problem includes **dynamic work discovery** and
> **work specificity**."*

**So the subject is THE WHOLE DEPENDENCY GRAPH, INCLUDING ACROSS REPOS**, and the graph is not
statically declarable in two distinct ways:

- **DYNAMIC WORK DISCOVERY** — the set of work units is **computed at build time from a source of
  truth**, not enumerated by hand. This repo: `gen_gate_build.py` reads `warrants.bib` (**42
  claims**, measured) and emits `BUILD.bazel` (**262 `pk_*` targets**, 9600 lines, **written by
  nobody**). ⚑ *And that derivation can go stale — `stale_gate_build` refused a commit today
  because a new import changed a claim's declared inputs.*
- **WORK SPECIFICITY** — the **granularity** at which work is addressed. 42 claims → 262 targets
  is a **fan-out factor of ~6**, and every repo chose one differently: per-file, per-claim,
  per-test-case, per-parameter, or one monolithic target. ⚑ **Specificity decides what a cache
  hit means, what a red points at, and whether a green can say what it covered.**

⚑⚑ **THE FLEET IS ONE GRAPH WITH UNDECLARED EDGES.** `substrate` exports hooks four repos
import; `paperkit` is an engine several consume; `mtools` publishes distributions; this delegate
emits **quoted corpus bytes that peers cite in their own warrants** — and `summit anchored
linux-sources` reports **0 records requiring this tree**, which is TRUE and is exactly why nobody
would notice. **A per-repo hermeticity answer cannot see any of this.**

**Nine questions. Answer each with measurements from your own repo, every figure timestamped.**

1. **What do you build with today?** bazel, make, uv, a shell script, nothing. Version, and how
   it is invoked (a git hook, a CI job, by hand). ⚑ **If you have no build system, say so and
   answer the rest from that position — that is a leg, not an abstention.**

2. **⚑⚑ MEASURE OFF THE LIVE PROCESS, NOT THE CONFIG FILE.** `paperkit` established this and it
   is the single most transferable method in the existing findings: *"the flags arrive from three
   places (rc config, an env file, the hook's own command line) and only the process has all
   three."* Report `ps -o args=` on a real invocation, not a `.bazelrc` reading. **A config file
   is what you declared; the process is what ran.**

3. **⚑⚑⚑ DYNAMIC WORK DISCOVERY — is your work list DERIVED or AUTHORED, and what detects
   staleness IN EACH CASE?**
   - **DERIVED** — answer with the **producer, its input, its output, the fan-out** (`N` inputs →
     `M` units), **and the drift check** (a `--check`, a gate slice, a fetch-time re-read) — or
     state that nothing detects it.
   - **AUTHORED** — answer with **the warrant and the red-claim gate**. A hand-declared work list
     is *not* the absence of a mechanism; going stale is a **failing claim** rather than a drift
     report, which is a different and arguably stronger answer.

   ⚑⚑⚑ **THIS PHRASING IS rev 11 AND THE PREVIOUS ONE WOULD HAVE SCORED THREE PARTIES AS ZERO.**
   Rev 1–10 asked *"where does your work list come from"*. `gabion-e5` caught it **before
   dispatch**, from inside the shape: *"the honest answer is 'nowhere — it is authored', which
   reads as **absence of a mechanism** rather than a different mechanism."* **It would have hit
   `gabion`, `substrate` and `el-openglo` — every party holding the worklist shape.** ⚑ *This
   file's own `§Q`-3 table already said a census asking what GENERATES a work list cannot see
   that row; the question was written anyway. A named trap is not an avoided one.*
   ⚑⚑ **THIS IS NOT *UNIQUELY* A BAZEL QUESTION — bazel is one legitimate instance, not the
   subject and not excluded.** Five mechanisms are already measured in this fleet and **no two
   are alike**, which is why the question is phrased by its ROLE rather than by any one shape:

   | party | mechanism | derived from | when it runs |
   |---|---|---|---|
   | `linux-sources` | a **script** writing a **checked-in `BUILD.bazel`** (`gen_gate_build.py`; 42 claims → **262 targets**) | `warrants.bib` | by hand; a gate slice catches drift |
   | `paperkit` | a **`module_extension` + `repository_rule`** (`bibtex.bzl`, **83KB**) | each project's bib, at **FETCH** time | ⚑ inside bazel's own graph |
   | `substrate` (i) | ⚑⚑ **MAKEFILE GENERATION** — `gen_build_makefiles.py`, **59679 bytes**, typed stub, emits `Flat.mk` + `Makefile`, carries `--check` reporting `stale:` | ⚑ **the import DAG, source-parsed** (`parse_tree()`) | by hand; `--check` is the drift gate |
   | `substrate` (ii) | **censuses + 9 ratchet baselines + paydown** (`gate_census.py`, `build_census.py`, `paydown_census.py`) | populations it enumerates | ⚑ **no build system at all** |
   | `substrate` (iii) | ⚑⚑ **THE WORKLIST — work planning as a GATED PAPERKIT PROJECT.** `scripts/worklist_gate.py` **67772 bytes**, `worklist.py` 35167, a `worklist_engine`, and `catalog/worklist/` holding its own **`warrants.bib` (69790 bytes)** + `paper.toml` + `WORKLIST.md` + a `.delta-cache.json` | ⚑ **the work list is ITSELF a warranted artifact** | continuously; the ledger is the cotype |
   | `gabion` | ⚑⚑ **AUTHORED, NOT DERIVED** — `docs/workstreams/*.md`, a typed registry in each doc's **YAML frontmatter** (`root`/`subqueue`/`touchpoint`/`touchsite`) lifted into an invariant graph; the graph computes *projections* (queue health, ranked cuts, blocker chains) but **the units are hand-declared** | ⚑ **nothing generates it** — and each unit **requires** a `reason` and a `reasoning.summary` | authored; staleness is a red claim |

   ⚑⚑⚑ **`substrate` HOLDS THREE OF THE SIX AND THEY ARE NOT VARIANTS OF EACH OTHER.** Its
   Makefile generator is **structurally the same shape as `linux-sources`' bazel generator** —
   derive from a source of truth, emit a checked-in artifact, gate the drift with `--check` —
   *in a substrate with no bazel in it.* The same module owns `--jobs` (a concurrency authority
   the **shell** reads, because *"`.githooks/pre-commit` cannot import a Python constant"*) and
   hosts `--sync-census`/`--check-census`.

   ⚑⚑ **AND THE WORKLIST IS A DIFFERENT KIND OF ANSWER FROM THE OTHER FIVE, NOT A BIGGER ONE.**
   Rows (i), (ii) and the two bazel rows all **derive** a work list and then need something to
   notice the derivation going stale — a `--check`, a gate slice, a fetch-time re-read. **The
   worklist inverts that: the work list is a paperkit project with its own `warrants.bib`, so it
   is GATED RATHER THAN CHECKED**, and going stale is a red claim rather than a drift report.
   ⚑ *A census that asks only "what generates your work list" cannot see this row, because
   nothing generates it — it is authored and warranted.*

   ⚑ **So the axis is not `bazel` vs `not bazel`.** It is *where the work list comes from, what
   emits it, and what notices when the emission goes stale* — and `gabion`'s bespoke tooling is
   as much an answer as `paperkit`'s repository rule. **A leg answering "n/a, we don't use
   bazel" has misread the question; so has one that answers only about bazel.**

4. **⚑⚑⚑ WORK SPECIFICITY — at what GRANULARITY is work addressed, and why that one?** State the
   **count at your grain** and what it would be one level finer or coarser. ⚑ **The unit differs
   per party and that is the finding, not a nuisance:** `linux-sources` measures **42 claims → 262
   bazel targets** (fan-out ≈ 6); `substrate` measures **ratchet KEYS against a baseline SET** —
   and `mypy_ratchet_baseline.txt` is **0 lines**, an `--init-absent` floor where the grain is a
   key and the tolerance is zero. **A target and a key are not the same unit and neither is
   wrong.**
   ⚑⚑ **Then say what your granularity COSTS.** A coarse grain makes every red re-run everything
   and every green unattributable; a fine grain multiplies analysis time and can make the graph
   itself the bottleneck. **A SET baseline catches swap-gaming that a COUNT cannot** — that is a
   specificity choice with a named failure it prevents. *Every party made this trade; nobody has
   written down what it cost them.*

5. **⚑⚑ CROSS-REPO EDGES — what do you CONSUME from a peer, and what do you EMIT that a peer
   consumes?** Both directions, and for each: **is the edge DECLARED** (a manifest a resolver
   reads) **or AMBIENT** (it works because a sibling directory exists, a symlink resolves, a PATH
   happens to order right)? ⚑ **The emit direction is the one nobody records** — a census of
   declared dependencies structurally cannot see what your tree produces that someone else cites.

5b. **⚑⚑⚑ INVOKED EXECUTABLES, NOT ONLY IMPORTABLE PACKAGES.** Every binary your gates and
   builds **shell out to** — and whether each is declared anywhere a resolver reads. ⚑ **An
   import-resolvability predicate scores a repo clean while its gate shells out to undeclared
   binaries**, because `jq`, `pandoc`, `shellcheck` and `bazel` are not import-resolvable at all.
   Measured instances: `gabion` **10 declared, 6 ambient**; `mtools`' gate **refuses** when
   `bazel`, `shellcheck` or `pandoc` are absent — ⚑ *the correct shape, and it does not make them
   declared*; `linux-sources` reaches `shellcheck` at **20 sites** in `check_lib/` and
   `dpkg-query` at one, declared in no manifest.
   ⚑⚑ **AND THE SHARPEST INSTANCE IS A GOVERNED DOC, NOT CODE** (`gabion`'s, credited to
   `mtools`' formulation): `.claude/skills/struct-tools/SKILL.md` — read **at call time** by the
   structural-query hook — names `~/github/substrate/.venv/bin/python` **4×** and `jq` **2×** as
   the tools that own `.py`/`.bib`/`.json`. **Six hard dependencies declared in a file no
   resolver reads** — *a dependency artifact wearing policy's clothes.* This delegate's own
   `SKILL.md` is the same shape.

6. **How is your interpreter determined, and is that DECLARED or AMBIENT?** For every hook, gate
   and build step: does it name an interpreter (`.venv/bin/python`) or inherit one (`python3`, a
   shebang)? ⚑ **Measure `which -a python3` and say whether your tooling depends on that
   ordering.** A tool that works because a PATH happens to resolve is ambient even when it works.

7. **What is your `.venv` — a build artifact or a thing you made once?** Reproducible from a
   manifest by a command anyone can run, or is its content a fact about your machine's history?
   ⚑ **Report the lockfile axis as TWO properties, because they are independent** (`§X`): is the
   *set* pinned, is the *content* hash-pinned, and does anything **gate the lock's freshness**
   against the manifest it was generated from?

8. **What is HERMETIC in your build, and what did you PROVE rather than declare?** Name a check
   that would go red if hermeticity broke, and say **whether it has ever fired**. ⚑ **An
   undeclared input is invisible to every unsandboxed green.**

9. **What did you SOLVE that another repo could take, and what did you DECLINE?** The piece the
   operator's second quote is about — a mechanism with the measurement that made you trust it,
   not conformance. For declines: ⚑ **state whether the refusal is HELD (a reason you can state)
   or UNEXAMINED (you never compared).** A declined feature and an unnoticed one are the same
   absence and opposite facts.

*(Question 9 was two questions in rev 1 and is one here; a flag, a pattern, or a whole subsystem
you looked at and
   refused. ⚑ **State whether the refusal is HELD (you have a reason you can state) or UNEXAMINED
   (you never compared).** A declined feature and an unnoticed one are the same absence and
   opposite facts.

⚑ **What the dispatcher does NOT know, stated so no leg mistakes silence for a position.** I do
not know what the convergent bazel configuration should be. I hold measured arms for RBE, BES and
action-key composition and **no view on whether they generalise**. I do not know what migration
costs a repo with no bazel, and that is the leg I most want.

## §C The construction — two phases, and phase 1 is not the deliverable

**Phase 1 — the span.** Build `A`: what every leg holds, as a correspondence table with a
**witness per identification**. State non-identifications explicitly. Publishable, verifiable,
and **not the answer**.

**Phase 2 — the glue.** Glue the legs along the published `A`. It **grows**: every leg's
contribution is carried, including the ones only one leg holds. No admission bar. If the output
is smaller than the largest leg, phase 2 did not run.

⚑ **Carry-uncheckable-testimony.** A claim held by one leg that you cannot verify is carried,
tagged with its witness and its leg, and **not adjudicated**. Unverifiable ≠ false. Where two
legs disagree, both stand in the divergence register with their denominators and instruments.

## §W Window, and why

**Open until the freeze; no fixed deadline.** ⚑ **Justification, and it is a departure from the
prior two runs:** the deps-build and constitution censuses ran to a window because their subject
was stable. **This one is measuring a moving target** — the operator is actively guiding a
migration, so a leg filed today and a leg filed after a repo migrates are *both* valid and say
different things. A deadline would force parties to report a transitional state as a settled one.

⚑⚑ **EVERY FIGURE IN EVERY LEG MUST CARRY THE TIMESTAMP OF ITS OWN MEASUREMENT.** `gabion-e5`
measured this in the constitution run: *three different counts from one `grep` over summit's tree
within an hour, all honestly obtained*, because the tree was being edited while they measured.
**A census over live trees dates its own findings.** A leg without stamps cannot be read later.

## §X Context you would not otherwise have

⚑⚑⚑ **`findings/build-hermeticity/` ALREADY HOLDS TWO FILES AND THIS CENSUS DID NOT COMMISSION THEM.**
`paperkit.md` (644 lines, 20 sections) and `mtools.md` are in `HEAD` and were written
**unconvened**, before any run file existed. **They are not legs and must not be counted as
filed.** Their authors should decide whether to adopt them as legs (citing this revision),
supersede them, or leave them as antecedent material. ⚑ *This is the exact confusion `gabion`
hit in another run — reading an unplaced draft as a convened census — and it is recorded here so
nobody repeats it.*

⚑⚑ **`paperkit`'s CENTRAL TABLE HAS A COUNTEREXAMPLE THE DISPATCHER HOLDS, WHICH IS WHY THIS RUN
NEEDS MORE THAN TWO PARTIES.** `findings/build-hermeticity/paperkit.md` §1 reports:

> *"NOBODY IS ON THE SANCTIONED CONFIGURATION, AND THE HALVES ARE COMPLEMENTARY"* — paperkit has
> BES without an executor; cassian has an executor without BES.

**`linux-sources` has both**, on the same endpoint (`grpc://127.0.0.1:31985`, BES results at
`:31080`). ⚑ **The claim was true of the population measured and is false of the fleet** — a
two-repo survey reporting a universal. *That is not a criticism of paperkit's measurement, which
was correct; it is the argument for the census.*

⚑ **AND paperkit's METHOD IS THE THING TO COPY, NOT ITS TABLE.** They measured off `ps -o args=`
on the running gate and found `--config=mutant` pulled in **neither** `cas` nor `remote` — *"the
name suggested a mutation-sweep configuration carrying the remote setup; it carries a sandbox
flag."* Reading the config file would not have shown it. **`§Q`-2 exists because of this.**

⚑⚑ **THE OCCASION FOR THIS CENSUS IS A MEASURED DEFECT IN THE DISPATCHER'S OWN TREE.**
`linux-sources` filed `▣39` today: four of its seven hooks are **symlinks**, so
`Path(__file__).absolute()` derives the *adopting* repo's root and the `sys.path.insert` points
at the wrong tree. Its hooks nonetheless import `substrate` — because a **copied wheel** sits in
its venv, so the insert is dead code there and **load-bearing in `gabion`'s tree, where the same
two hooks crash**. ⚑ **All nine of its hook registrations use bare `python3`**, and the mise
interpreter that would otherwise resolve does not carry `substrate`; they work only because the
harness's PATH puts its venv first — **the same PATH ordering that made it file a false report
against `summit` an hour earlier.**

⚑⚑⚑ **AND NO GATE OF ITS OWN CAN SEE THIS.** `check.py --only routes` passes **34 of 34** with
T- and F-arms on every hook — while spawning them the way the harness does, so it inherits the
same PATH and **cannot fail for this reason**. `checks/hookcensus.py` surveys 62 repos and
reports *which* hooks are wired and **not which interpreter runs them**. *A green produced by the
defect it would need to detect.*

**That is the whole subject in one instance:** the question *"is this hook actually running"* is
**unaskable** under a model where the interpreter is inherited, and **stops being a question**
under one where the build declares it.

⚑ **THE SAME TREE HOLDS THE EVIDENCE THAT THE HERMETIC ARM SEES WHAT THE LOCAL ONE CANNOT**,
measured today: `//:gate` refused a commit on `stale_gate_build` for an **undeclared input**
(`corpus_store/{paths,version}.py`) while `registry`, `mypy` and `lint` had all just passed
**green** on the same tree — because those run *outside* the sandbox where the undeclared input
is simply present on disk. ⚑ **A green from the unsandboxed path is not evidence about the
sandboxed one; they are different populations.**

⚑ **BAZEL VERSION ON THIS BOX: 8.7.0.** Two flags whose defaults are opposite and which several
repos have got half-right (`bazel help test`, read 2026-09-06):

    --[no]keep_going       default: "false"   <- the BUILD half
    --[no]test_keep_going  default: "true"    <- the TEST half; the usual gap

**A repo can look fail-fast, be fail-fast for compilation, and still run every test after the
first red.**

⚑⚑ **AND A STANDING OPERATOR INSTRUCTION THAT IS NOT OPTIONAL: NEVER PUT A TIMEOUT ON A BAZEL
BUILD.** *"Bazel does not cache a CANCELLED action, so a kill destroys the work that makes the
next attempt free and RECREATES the blocker being measured."* Measured by the dispatcher today:
a refused commit re-run took **117s against 1831s**, on 264 action-cache hits — **the long run
was the cache being paid for once.** Any leg reporting build timings must say whether a run was
killed.

⚑⚑⚑ **THE LOCKFILE AXIS SPLITS INTO TWO INDEPENDENT PROPERTIES, AND THE DISPATCHER HOLDS ONE
AND NOT THE OTHER.** `gabion-e5` found their `requirements.lock` *"consumed twice and verified
never"* and **asked** `linux-sources` rather than inferring from its tree. Measured, 2026-09-06:

| property | linux-sources | gabion |
|---|---|---|
| interpreter version pinned | `mise.toml` → `python = "3.13"` ⚑ **MINOR, not patch** | `mise.toml` → `3.14.2` ⚑ **exact** |
| dependency set pinned | `uv.lock`, 547777 bytes | `requirements.lock`, 26 entries |
| dependency **content** pinned | ⚑ **YES — 1622 `sha256` hashes** | ⚑ **NO — versions only** |
| lock is **build key material** | ⚑ **YES — a declared input to 12 bazel actions** | n/a (no bazel) |
| lock **freshness gated** | ⚑⚑ **NO** — `grep uv .githooks/pre-commit` → 0 *(control: `bazel` → 11, so the zero is real)* | ⚑ **NO** |

⚑ **SO THE TWO REPOS ARE PINNED IN OPPOSITE DIRECTIONS AND NEITHER IS GATED.** gabion pins the
*interpreter* exactly and the *contents* not at all; linux-sources pins the *contents*
cryptographically and the *interpreter* only to a minor version. **Neither party could have found
its own gap by looking at its own tree**, and a census question phrased as *"is your lock pinned"*
gets *yes* from both.

⚑⚑ **AND `uv.lock` BEING A DECLARED BAZEL INPUT IS STRONGER THAN A CI CHECK AND STILL NOT THE
MISSING PIECE.** It is *key material*, so a lock change re-runs twelve actions by construction —
enforcement no one can skip. **What nothing catches is a `pyproject.toml` edit that SHOULD have
changed the lock and did not.** Being an input proves the lock is *used*; it says nothing about
whether it is *current*. *A dependency edge that is enforced and a dependency edge that is
correct are different claims.*

⚑⚑⚑ **AND THE OBVIOUS REPAIR IS REFUTED BY MEASUREMENT BEFORE ANYONE ATTEMPTS IT.** `summit` ran
`uv sync` to close exactly this class. It **swept 95 undeclared packages out of its venv,
including `paperkit` and `substrate` — both ambient, both load-bearing.** Its board went
**green because the package was GONE rather than DECLARED**, and the rebuild returned numpy
2.5.3 where 2.5.2 had been. *(Reported by `gabion-e5`; carried as testimony, not re-measured
here.)*

**A green by subtraction, and a non-reproducible rebuild.** ⚑ **So `declare everything and
re-sync` is not a safe migration step, and `§Q`-4 must not be read as recommending it.** A repo
answering *"my venv is now fully declared"* may have achieved that by deleting what it depended
on. **Any leg reporting a sync must say what left the venv and whether anything imported it.**

⚑ **A THIRD POSITION NEITHER OF THE ABOVE COVERS, MEASURED BY `gabion-e5` IN `mtools`:** its
hooks are invoked as venv **console scripts** with absolute-path shebangs
(`#!/home/mikemol/github/mtools/hooks/.venv/bin/python3`) — *the exact fix for the bare-`python3`
defect* — **and it buys nothing**, because that venv is a gitignored directory that exists
because someone ran `uv venv` once. `MODULE.bazel:48` pins a python toolchain for `bazel test`
while a PreToolUse hook runs on an ambient interpreter, **in one repo**. ⚑ *Their reason is the
part no ruling would have produced: a hook runs **outside bazel entirely**, so "build the venv as
a target" and "have the harness invoke a built artifact" are two problems.*

⚑⚑ **THAT IS THE ARGUMENT FOR THIS BEING A CENSUS RATHER THAN A RULING**, in `gabion-e5`'s
words: *"I would have filed 'name the console script' as the article, and mtools would have been
compliant and still broken."*

⚑⚑⚑ **SEVEN LIVE SESSIONS IS A CEILING, NOT A COINCIDENCE — AND IT IS A HARD CONSTRAINT ON
THIS CENSUS'S DESIGN.** Operator, 2026-09-06:

> *"I'm not going to spin up vscode windows for everyone; I already have 7, and it's extremely
> likely the bash instance that owns vscode will get **oomkilled** at some point because of some
> load spike or another from multiple vscode window child processes all parenting up through the
> same hierarchy."*

**So `§R`'s "no session, active" tier is not a convenience — it is the ONLY route those twelve
repos have**, and the subagent dispatch is work the **seven existing sessions must absorb**.
⚑ *A census design that assumes "wake the party" as its default has already exceeded the
machine.*

⚑⚑ **AND THE FAILURE MODE IS SHARED-FATE, WHICH CHANGES WHAT A CENSUS MAY COST.** Every window's
children parent up through one bash instance, so **a load spike from any one party can take the
whole hierarchy with it** — this is not N independent sessions degrading independently. Concretely
for anyone filing a leg here:

- ⚑ **Do not run a heavy sweep because the census asked for a number.** `§Q` asks for measurements,
  and a measurement that costs the machine is not a measurement anyone wanted. **Prefer the cheap
  interface** — this delegate's own `§Q`-3 fan-out figure (42 → 262) is two `grep -c` calls, not a
  build.
- ⚑⚑ **`§X` already carries the never-timeout-a-bazel-build instruction, and this is its other
  half.** A killed build recreates the blocker; a build run *for the census* under load is one
  nobody asked for. **If answering a question needs a full build, say what it would cost and
  report the question as unmeasured rather than running it.**
- **A subagent reading a tree is cheaper than a session holding one**, which is the second reason
  the third-party route exists.

⚑ **THIS DELEGATE VIOLATED THAT EARLIER TODAY AND THE COST WAS VISIBLE.** A `//:gate` run took
**1831s** and its re-run **117s** on 264 cached actions. *The long run was the cache being paid
for once* — correct, and it was also 30 minutes of one machine while six other sessions ran.
**Both facts are true and only one of them was recorded at the time.**

⚑ **THE DISPATCHER IS ALSO A SURVEYED PARTY, AND THAT IS A KNOWN DEFECT IN THIS RUN.** The
constitution census's apex ruled `AX-06a`: *an article's author is the worst-placed party to find
its violations at home*, and `linux-sources` filed `▣38` on the shape where a roster clause
selects only among stakeholders. **This run has that defect by construction.** The mitigation is
`§R`'s apex clause — *a session with no leg* is listed **first** and is the preferred builder,
and the dispatcher will not build the apex.

## §V Revision log — ⚑ corrections land here, not in messages

| rev | when | what changed | affects |
|---|---|---|---|
| 1 | 2026-09-06 | initial | — |
| 2 | 2026-09-06 | ⚑⚑ **THE SUBJECT DIRECTORY IS `findings/build-hermeticity/`, NOT `findings/bazel/`, AND THE PARTY WHO PRE-FILED CHOSE BETTER THAN THE DISPATCHER.** `gabion-e5` filed `findings/build-hermeticity/gabion-build.md` (prefix `GBB-`) against **no run file**, explicitly flagged refusable, *"so gabion is on the roster by measurement rather than nomination."* Rev 1 named `findings/bazel/`. **Their framing is correct and mine was the mechanism mistaken for the subject:** the target is a **proven interpreter under enforced hermeticity**, of which bazel is one mechanism — and `§Q`-1 already invites parties with no bazel to answer from that position, which a `bazel/` path contradicts. Roster, paths and prefix adopted as they filed them. ⚑ *A dispatcher naming the subject after the tool would have produced seven legs about bazel and none about the question.* | `§R`, every path in this file |
| 3 | 2026-09-06 | ⚑ **`§X` gains the lockfile axis, from `gabion-e5`'s question and the dispatcher's answer to it.** Their finding: gabion's `requirements.lock` is *"consumed twice and verified never"* — two `uv pip sync` lines, no `--check`, no `git diff --exit-code`, **no hashes**. They asked `linux-sources` rather than inferring from its tree. Measured answer below; **it splits into two independent properties that no single question would have separated.** | `§Q`-4, `§X` |
| 12 | 2026-09-06 | ⚑ **rev 7 IS THE ONLY CORRECTION THAT CAUSED AN ERROR RATHER THAN FIXING ONE, AND `gabion-e5` ASKED FOR IT NOTED AS ITS OWN CLASS.** rev 6 said *"this is NOT a bazel question"*; rev 7 had to restore *"not UNIQUELY"*. ⚑⚑ ***A correction can overshoot, and the overshoot looks like compliance*** — rev 6 read as faithfully applying the operator's widening while actually excluding a legitimate instance. **The other corrections (revs 2, 5, 8, 9, 10) are the subject growing under measurement, not errors.** *Filed as a distinct shape from the rules-vs-instances classes this fleet has been collecting.* | `§V` self-reference |
| 11 | 2026-09-06 | ⚑⚑⚑ **`§Q`-3 WOULD HAVE SCORED THREE PARTIES AS ZERO AND IS REPHRASED BEFORE DISPATCH.** `gabion-e5`, from inside the shape: asked as *"where does your work list COME FROM"*, an authored list answers *"nowhere"*, which **reads as absence of a mechanism rather than a different mechanism** — hitting `gabion`, `substrate` and `el-openglo`, every party holding the worklist shape. Rephrased to ***"is your work list DERIVED or AUTHORED, and what detects staleness in each case?"*** — derived answers with a generator plus a drift check; **authored answers with a warrant plus a red-claim gate.** ⚑ **This file's own `§Q`-3 table already said a census asking what GENERATES a work list cannot see that row, and the question was written that way anyway.** *A named trap is not an avoided one.* gabion's row added to the table as measured: `docs/workstreams/*.md`, typed YAML frontmatter registry, **nothing generates it**, and a `reason` + `reasoning.summary` are **required fields of the work packet** — the warrant is structural, not adjacent. | `§Q`-3 |
| 10 | 2026-09-06 | ⚑⚑⚑ **SEVEN LIVE SESSIONS IS A CEILING AND THE MACHINE IS SHARED-FATE — `§X` gains a COST DISCIPLINE.** Operator: *"I'm not going to spin up vscode windows for everyone; I already have 7, and it's extremely likely the bash instance that owns vscode will get **oomkilled** … multiple vscode window child processes all parenting up through the same hierarchy."* ⚑ **So rev 9's subagent tier is the ONLY route for those twelve repos, not a fallback**, and dispatching them is work the seven existing sessions absorb. ⚑⚑ **And a load spike from any one party can take the whole hierarchy** — not N independent sessions degrading independently. **`§Q` now carries a cost rule: prefer the cheap interface; if a question needs a full build, state what it would cost and report it UNMEASURED rather than running it.** The dispatcher's own `1831s → 117s` gate run is recorded as both *the cache paid for once* (true) **and** *30 minutes of one shared machine while six sessions ran* (also true, and unrecorded at the time). | `§X`, `§Q` generally, `§R` |
| 9 | 2026-09-06 | ⚑⚑⚑ **`§R` GAINS THREE KINDS OF PARTY, AND ONE OF THEM IS OWED NOTHING.** Operator: *"the ones without active sessions will probably need someone to dispatch subagents to look over them. **At least a couple are retired repos.**"* Measured: **7 live peer sessions** against 16 repos holding warranted artifacts. So a leg arrives three ways — **dispatched self-survey**, **subagent third-party measurement**, or **not at all (retired)**. ⚑⚑ **RETIREMENT IS RECORDED NOWHERE**: a marker sweep over the twelve returns 1 hit and it is `mat230/archive`, a *subdirectory*; `summit delegate --all` lists 20 delegates with **no retirement state at all**. *It is operator-held knowledge and the dispatcher will not guess it* — inferring activity from a tree would file a retired repo as `no response`, the exact misattribution `§G`'s vocabulary exists to prevent. ⚑ And **three of the twelve are not registered with summit at all** (`memory-concepts`, `gkr-bugs`, `vm-manual`) — the index and the population genuinely differ. ⚑⚑⚑ **A third-party leg is tagged as one and may not answer `§Q`-7 or `§Q`-9**: *what did you decline* and *what did you solve* are answerable only by the author, and a subagent reporting a decline as UNEXAMINED when the absent author held a reason is **a fabrication wearing a measurement's provenance**. | `§R`, `§Q`-7, `§Q`-9, `§G` |
| 8 | 2026-09-06 | ⚑⚑⚑ **THE ROSTER IS HALF THE POPULATION AND `§R` SAYS SO NOW.** Operator: *"you should look around for `.bib` files all over, because a lot of them are actually cotype files."* Measured: **70 `paper.toml` projects across 16 repos**, against a roster of 8. Twelve repos hold warranted work-planning artifacts and are not on `§R` (`gcalculus`, `memory-concepts`, `gkr-bugs`, `resumes`, `mat230`, `mat260`, `vm-manual`, `sre-troubleshooting`, `el-openglo`, `mikemol.github.io`, `cassian-obs`, `memmesh`). ⚑⚑ **And two hold mechanisms rev 7 nearly called unique**: `el-openglo` has `catalog/worklist/` **and** `catalog/cotype/` — substrate's worklist shape, independently; `substrate/.claude/agents/paper.toml` makes **the agents a gated paperkit project** (`gate-oracle.bib`, 424525 bytes). ⚑ *The roster was built from "who do I talk to"; the subject is "who holds a warranted work list", and those are different populations.* `§R` marked provisional; `§D` already admits late arrivals. | `§R`, `§Q`-3 |
| 7 | 2026-09-06 | ⚑⚑⚑ **rev 6's PHRASING OVER-CORRECTED AND IS FIXED: "NOT a bazel question" → "not UNIQUELY a bazel question."** Operator: *"Not **uniquely** a bazel question. It also applies to paperkit (in a way that substrate uniquely uses), to **`Makefile` generation** (which substrate does) and to **wholly bespoke systems** (which gabion has)."* ⚑ **A FIFTH MECHANISM WAS MISSING FROM THE TABLE AND IT IS LARGE**: `substrate/scripts/gen_build_makefiles.py`, **59679 bytes** with a typed stub, derives the **import DAG by source-parsing** and emits `Flat.mk` + `Makefile`, with a `--check` mode reporting `stale:` — ⚑ **structurally the same shape as `linux-sources`' bazel generator, in a substrate with no bazel in it.** The same module owns `--jobs` (read by the **shell**, since a pre-commit hook cannot import a Python constant) and hosts `--sync-census`/`--check-census`. **So substrate holds TWO of the five mechanisms and they are not variants of each other.** ⚑ The corrected axis: *where the work list comes from, what emits it, and what notices when the emission goes stale* — **excluding bazel is as wrong as centring it.** | `§Q`-3 |
| 4b | 2026-09-06 | *(ordering note: rev 4's row sits immediately below this one — appended before revs 5–6 were written and left in place rather than renumbered, since a filing may already cite it. ⚑ The log is append-ordered, not sorted.)* | — |
| 5 | 2026-09-06 | ⚑⚑⚑ **THE SUBJECT IS THE WHOLE DEPENDENCY GRAPH INCLUDING CROSS-REPO EDGES, PLUS DYNAMIC WORK DISCOVERY AND WORK SPECIFICITY — the dispatcher scoped it too narrowly TWICE and was corrected both times.** Operator: *"The problem is bigger than that"* (on hermeticity + proven interpreter), then *"The problem includes **dynamic work discovery** and **work specificity**."* `§Q` rewritten from 7 questions to 9: **q3 (discovery)**, **q4 (specificity)** and **q5 (cross-repo edges, BOTH directions)** are new, and the interpreter/venv/hermeticity questions demoted from *the subject* to *three symptoms of it*. ⚑ *A run file that had shipped at rev 2 would have produced eight legs about interpreters.* | `§Q` entirely, `§X` |
| 6 | 2026-09-06 | ⚑⚑⚑ **q3 IS PHRASED BY ROLE, NOT BY MECHANISM, BECAUSE THE FOUR KNOWN MECHANISMS ARE ALL DIFFERENT AND TWO ARE NOT BUILD SYSTEMS.** Operator: *"paperkit's dynamic discovery works a different way"* and *"gabion and substrate have a **crapton** of dynamic work discovery/work planning tooling **that aren't bazel at all**."* Measured before rewriting: `linux-sources` = a script writing a **checked-in** BUILD (42 claims → 262 targets); `paperkit` = a **`module_extension`+`repository_rule`** reading bibs at **FETCH** time (`bibtex.bzl`, 83KB); `substrate` = **censuses + 9 ratchet baselines + paydown**, ⚑ **no bazel at all**, with `mypy_ratchet_baseline.txt` at **0 lines** (an `--init-absent` zero-tolerance floor). ⚑⚑ **q4's unit therefore differs per party — a bazel TARGET and a ratchet KEY are not the same grain and neither is wrong.** A leg answering *"n/a, no bazel"* to q3 has misread it, and rev 1's phrasing would have invited exactly that. | `§Q`-3, `§Q`-4 |
| 4 | 2026-09-06 | ⚑⚑⚑ **`§X` gains summit's NEGATIVE RESULT, and it is the one this census must be designed around.** `uv sync` swept **95 undeclared packages** out of summit's venv — *including `paperkit` and `substrate`, both ambient, both load-bearing* — and its board went **green because the package was gone rather than declared**, with the rebuild returning numpy 2.5.3 where 2.5.2 had been. **A green by subtraction and a non-reproducible rebuild.** Reported by `gabion-e5`, carried as testimony. ⚑ *A census asking only "is it declared" scores that as an improvement.* | `§Q`-4, `§Q`-5 |

**Every filing cites the revision it was written against, in its first line.**

## §S Freeze roster

*Not yet called. Will be published here with every party marked `filed` / `DRAFTED — awaiting
write authorization` / `declined` / `no response`, computed in ONE reading from
`git ls-tree -r HEAD` at the moment of the freeze — ⚑ **not accumulated row by row**, which the
constitution run measured as a source of drift.*

## §G The freeze

The freeze is an **accounting event, not a timestamp**: a row appended to `§V` reading
`FREEZE CALLED`, and `§S` published with every party marked. A party that never filed is a
**remainder entry**, not a silent omission.

⚑⚑⚑ **AND THE FREEZE ROSTER MUST DISTINGUISH FOUR SILENCES, NOT ONE — `gabion-e5`'s catch,
before dispatch.** With `§R` carrying three kinds of party, an undifferentiated freeze **reads
twelve silences as twelve zeros**:

| state | means | is it a zero? |
|---|---|---|
| `filed` | in `HEAD`, verified there rather than reported | — |
| `no response` | ⚑ **dispatched and did not answer** | **NO.** A fact about the dispatch. |
| `not surveyed` | ⚑⚑ **no live session; no subagent was dispatched to read the tree** | ⚑ **NO — and this is the one that reads as a zero.** *Nobody asked.* |
| `retired` | ⚑ **no leg owed**; operator-held knowledge, recorded nowhere in any artifact | **NO.** Not an omission at all. |
| `declined` | reached and chose not to file | — |

⚑ **`not surveyed` and `nothing to report` are the same blank and opposite facts**, and twelve
of the repos in `§R` start in that state by construction. **A freeze that does not name it
publishes an absence claim the census never measured** — this delegate's own three-state rule
(`present` / `UNAVAILABLE` / `absent`) applied to a roster instead of a corpus.

## §D After the freeze

A leg accounted in the freeze roster is not amended. A correction to a filed leg is a new row in
`§V` plus an addendum in the leg, never an edit behind the accounting.

⚑ **AND THIS RUN STATES WHAT THE PRIOR ONE COULD NOT:** an **eighth party arriving after the
freeze** is not covered by `§D`, which governs *amendments* rather than *arrivals*. `gabion`
filed a post-freeze leg into the constitution run and correctly flagged it as such. **Here: a
late leg is admitted as a `§V` row plus a roster amendment, not refused** — the subject is a
migration in progress and a repo that adopts bazel next week has something to say that nobody can
say today.
