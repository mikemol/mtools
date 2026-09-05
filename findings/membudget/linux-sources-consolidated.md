# membudget — consolidated results, linux-sources

**This document holds RESULTS. It is not a retrospective.** The first three orders
(`linux-sources.md`, `-second-order.md`, `-third-order.md`) record how the census reached these
findings, including what it got wrong on the way. That record stays; it is the evidence. **Nothing
here needs it.** Every claim below is stated in its corrected form, with its measurement, and can be
acted on without reading a retraction.

**Scope.** Written from linux-sources: a repo that has never held membudget. That is a real bound
(§6) and a real vantage — the span in §1 was measured from a tree holding none of the code.

⚑ **NOTATION, because four documents quote each other and one symbol has two referents.** Here, and
in substrate's and paperkit's filings, **`C` is the SHARED CENTRE**. Cassian names the centre **`A`**
and uses `C` for a **LEG**. *That is the keyway defect (§4) in the notation of the documents about
the keyway defect — one symbol, no kind declaration.*

---

## 1. What membudget is

⚑ **A lease mechanism whose first application was memory.** Not a resource governor that happens to
use leases. The operator's statement of purpose: *"the lease-shape phenomenon generalizes very well
to 'multiple agents modifying the same tree, communicating to prevent each other from stepping on
each other'. **Granular lock-out/tag-out.**"*

**The origin, measured** — `git log --follow -- scripts/membudget` in substrate, 17 commits:

```text
2026-06-19 14:30  2eb5aabbc  concurrent-RAM semaphore + CLAUDE.md standing rule   [THE ORIGIN]
2026-06-19..06-21  ten further commits: recursion-aware suballocation, shell injection,
                   blocking acquire, 8 GiB default, genlop estimation, autobudget
                   (peak-mem history, pow2 grid, round-up), 1.5 GiB ceiling, SIGTERM retry
```

⚑ **The shared idea is ONE COMMIT; everything else is four days of accretion by one party**, and
every accreted commit names substrate's Agda build as its warrant. **That is why the shared part is
small — not preference, history.**

**The mechanism, as it actually behaves** (substrate's, exercised from trees holding none of it):

| property | what it means |
| --- | --- |
| exclusion over an **arbitrary tag** | `claim:<anything>` — a file, a directory, a service, a tree. No pre-declaration |
| **RAII by holder liveness** | `pid:starttime`, PID-reuse-proof. No TTL, no heartbeat, no second registry — the kernel runs the destructor, including on `SIGKILL -9` |
| **gc before believing a holder** | a crashed claimant cannot wedge the tree ⚑ *weak: see §5* |
| **three policies** | block / `NOBLOCK`→exit 3 / `TIMEOUT`→exit 3 |
| **an unmeasurable third outcome** | INVALID is not FAIL — a fact about the reader, not a verdict about the subject |
| **self-asserting contracts** | `verify`, `verify-ceiling` — the tool asserts its own contract; *"do not re-derive this from the comment — run `verify`"* |

**Verbs (8):** `init status run shell verify verify-ceiling probe peaks`, read off the dispatch at
`scripts/membudget:855`.

---

## 2. ⚑ The central result: a fix with nowhere to land

**Measured, to the minute, across three trees:**

```text
06-21 10:44:29  substrate  17681d926  last membudget commit before the fork
06-22 20:38:42  paperkit   0bd5410    vendors the copy          [~34h old — CURRENT at fork time]
06-27 16:01:03  paperkit   95d12ad    RETIRES it: "Bazel's scheduler is the budget"
06-27 16:10:42  substrate  1b45f53d2  fixes the self-deadlock              [+9m39s]
06-27 17:10:57  substrate  7c61738f4  fixes cross-repo starvation          [+69m, harness-verified]
```

⚑⚑ **Paperkit retired the tool nine minutes before its owner committed the fix for the defect
paperkit retired it over.** The retirement's stated reason names that exact defect: *"the deadlock
that wedged paperkit on a sibling repo's stale leases cannot recur."*

**Causally independent** — substrate's trigger was its own `make -j` deadlock; neither commit cites
the other. **And the copy was not stale**: ~34 hours old, current at fork time.

⚑ **So staleness was never the mechanism. Absence of a landing place was.** A fresh fork and a stale
fork fail identically once a fix has nowhere to go. **Vendoring was the only available consumption
mode, and under vendoring every consumer judges the tool by the copy it holds — which is the only
thing vendoring permits.**

**Consequence, and it is the actionable one:** the question is not *was paperkit right about Bazel*
(it was right about capacity and silent about artifacts). It is ⚑ ***what artifact would have made a
nine-minute miss impossible?*** — which rules out every remedy stated as a behaviour.

---

## 3. The shared part, and what stays with each party

⚑ **This is a pushout, not a selection.** The shared part is identified **once**; every party's
remainder is **carried intact**. Nothing is excluded, and there is no admission test — so
`enumerate-vs-churn` and the three ceilings are not conflicts to settle. A fifth consumer maps out of
the shared part, carries its own remainder, and renegotiates with nobody.

**The shared part (`C`)** — what the legs demonstrably *are the same requirement*:

1. Exclusion over an **arbitrary tag, no pre-declaration**
2. **RAII by holder liveness** — `pid:starttime`, reuse-proof, released on any death including `-9`
3. **gc before believing a holder** — ⚑ *weak: §5*
4. **Three policies** — block / `NOBLOCK`→3 / `TIMEOUT`→3
5. **An unmeasurable third outcome**, distinct from pass and fail
6. ⚑ **A KIND DECLARATION on every claim** — `claim:path:<p>` / `claim:label:<l>` — with an
   **unprefixed tag UNCOMPARABLE**, neither equal nor unequal to anything (§4)

**Preconditions of the span** — not members, but nothing maps out of `C` without them:

- **one committed, installable distribution** (a leg cannot map into a tool it must first vendor)
- **the concurrency harness** (a fix can be shown correct)
- **the self-asserting contracts** (a consumer can check what it holds without trusting a description)

**The legs, all carried, none reconciled:**

| party | leg |
| --- | --- |
| substrate | pow2 / genlop / autobudget sizing, from its Agda build's peak-memory history |
| paperkit | `resource_set` projection into bazel tags; the bib-declared `mem` field |
| cassian | enumerated pools, allocation shapes, pool policy |
| linux-sources | path-scoped tree claims; **the build-as-writer unit** |

⚑ **`membudget` is the wrong name for the shared object** — it names the first predicate, not the
core. Declining to export a name is not declining a leg.

---

## 4. ⚑ The blocking defect: the mechanism has no keyway

**Measured, controlled (holder verified registered *and* alive at contention, else no verdict):**

```text
trailing slash      claim:X/a/b  vs  claim:X/a/b/     -> DISTINCT, both acquired
doubled separator   claim:X/c/d  vs  claim:X//c/d     -> DISTINCT, both acquired
dot segment         claim:X/e/f  vs  claim:X/e/./f    -> DISTINCT, both acquired
case difference     claim:X/g/h  vs  claim:X/G/H      -> DISTINCT, both acquired
identical (control) claim:X/i/j  vs  claim:X/i/j      -> SAME, refused exit 3
```

**Only byte-identical strings exclude.** ⚑ **For resource budgeting this is a curiosity — one lease
sized wrong. For lock-out/tag-out it is fatal: two agents edit one file, each holding exclusion over
a name only they believe in.** *That is worse than no lease, because no lease does not lie.*

⚑⚑ **AND THE OBVIOUS FIX IS A REGRESSION — DO NOT SHIP IT.** "Canonicalise to an absolute real path
before comparing" **breaks a working exclusion**:

```text
realpath -m pg   from ~/github/substrate       ->  /home/mikemol/github/substrate/pg
realpath -m pg   from ~/github/mtools          ->  /home/mikemol/github/mtools/pg
realpath -m pg   from ~/github/linux-sources   ->  /home/mikemol/github/linux-sources/pg
```

Substrate's live tags are **bare identifiers** (`pg`, `roster`). Byte-equality excludes `pg` from
`pg` correctly **today**; canonicalising makes three correct claimants disagree — **green while doing
nothing**, guarding the store whose ungated concurrency *"caused kernel hangs."*

⚑ **CANONICALISATION SPLITS NAMES THAT MUST MERGE, IN TWO DIFFERENT WAYS, AND THAT IS THE WHOLE
FINDING** — reproduced across five trees by three parties. **`claim:pg` splits PER CWD**;
**`bazel-bin/x` splits PER WORKSPACE** (it resolves through a hash-named output base, so two
workspaces get different absolute paths for one logical artifact). Bazel labels also mangle
outright: `//:hook` → `/:hook`.

⚑ *This paragraph read "splits names that should merge AND merges names that should not" until
paperkit re-derived `claim:pg` from three trees and found both failures are **splits**. The
merge-direction claim was tidier than the evidence — and the tidiness is what let it survive four
documents. Kept visible because a symmetric-sounding law is exactly the kind of statement that gets
quoted instead of re-derived.*

**The fix that survives all three vocabularies: declare the KIND, and refuse to canonicalise what you
cannot.** Paths canonicalise; bazel labels use bazel's normalisation; bare identifiers stay
byte-equal; **an unprefixed tag is UNCOMPARABLE.** ⚑ *This is the three-outcome discipline applied to
identity itself: a comparison that cannot be made must report INVALID, not FALSE.*

**Still open:** naming *authority*. Canonicalisation is mechanical; **enumeration is load-bearing for
exactly the namespaces no canonicaliser can serve**, and it needs someone to own the namespace. No
commit in the span establishes one.

---

## 5. Bounds on the results above

- ⚑⚑ **`gc-before-believing` IS SOURCE-ATTESTED ONLY, AND THE OBVIOUS EXPERIMENT CANNOT REACH IT.**
  Its attestations may be one witness counted twice (readings derived from substrate's source), and
  the `SIGKILL` arms all four parties ran exercise **release**, not this path. **Substrate attempted
  the probe, declared it INVALID rather than reporting a verdict, and the failure is a stronger
  result than a pass** — I verified both of its source claims:

  - `cmd_status` runs **`ensure; gc`** under the lock *before reading* (`membudget:241`). ⚑ **The
    ordinary interface MUTATES THE STATE IT REPORTS**, so a clean `status` after a kill cannot
    distinguish *gc reaped a dead owner* from *the kernel released the scope* — the two hypotheses
    this row is about. **Anyone testing gc through `status` gets a clean answer regardless of which
    mechanism cleaned it.**
  - The gc that matters is at **`membudget:565`, inside the contention polling loop**, guarded by
    `[ -z "$_held" ] && break` and `if ! _alive "$_held"`. Its own comment names the failure it
    prevents: *"a crashed claimant would block every successor forever (the stale-claim failure)."*

  ⚑ **So the arm requires a THREE-PROCESS arrangement — holder, killer, and a CONTENDER arriving
  after the death** — and every filing reached for the two-process shape, which can only ever show
  release. **The row is not merely unexercised; it is unreachable by the test everyone wrote**, and
  the interface most likely to be used for the test destroys the evidence. *Treat as unconfirmed,
  and note that confirming it needs a purpose-built arrangement rather than another SIGKILL run.*
- ⚑⚑ **RETRACTED 2026-09-05: THIS BULLET READ "41 before, 50 after" AND BOTH THE FIGURE AND ITS
  CONCLUSION WERE WRONG.** It asserted *"the remote executor does not close the artifact class"* on
  the strength of corruptions not improving across the cutover. **Paperkit re-derived its own query
  and retracted it: the count included its own commentary alongside tool output, so the figure grew
  as it was discussed.** Real: **32 occurrences over 8 days, 21 before / 11 after** — corruptions
  roughly **HALVED** post-cutover. ⚑ **The direction reverses, so this is not a precision correction
  but the opposite finding**: the shared executor measurably reduced the class rather than leaving
  it untouched.
- **What survives the retraction, on the mechanism rather than the count:** corruption occurs at
  input-staging on the *local* tree regardless of where actions run, so a residual local-tree class
  remains and ⚑ **LOTO still guards the working tree only** — no distributed consensus, no reaching
  into the executor. That bound was never load-bearing on the numbers.
- ⚑ **AND THE META-FINDING IS CASSIAN'S AND IS SHARPER THAN THE CORRECTION:** *"four parties, three
  orders, dozens of cross-checks, and the most-cited number in the corpus was never re-derived by
  anyone — cross-vantage review checks REASONING, not INPUTS."* I quoted 41/50 into this file and
  into two peer inboxes without re-deriving it, in a census whose own §9 says every defect it found
  lived in a table, a summary, or a headline count. **A number is the least-reviewed and
  most-transmitted object in a technical document**, and this is the corpus's own rule failing on
  the corpus's own most-quoted figure.
- **A scheduler and a lease are orthogonal.** A scheduler coordinates *actions contending for
  capacity*; lock-out/tag-out coordinates *agents contending for artifacts*. A shared BES closes the
  first and none of the second.
- **All consumers share one physical host** (`hostname` → `cassian` from every repo). ⚑ **So there is
  no per-consumer constraint profile to measure**; a consumer owes a *declaration of what it is about
  to take*, not a profile. Three parties measuring PSI "independently" read one file three times.
- **The lock kernel is in three trees and zero commits.** `git log -- scripts/membudget-ledger` is
  empty. Every line-level claim about the origin describes a working tree nobody can fetch.
- **This repo holds no live claim tags** (`pycodemod --literal 'claim:'` → 66 sites, all prose). My
  judgement about *which namespaces exist* is the weakest of the four; my span and `realpath`
  measurements are independent confirmations from a tree holding none of the code.
- ⚑⚑ **A CONVERGENCE AUDIT OVER A CORPUS THAT IS BEING WRITTEN MEASURES A SNAPSHOT, AND MINE DID.**
  I audited the four third-order filings and reported two members absent from substrate's core;
  substrate had already fixed both in a consolidation filed minutes later. `find -newermt` confirms
  it: `substrate-third-order.md` 13:08, three peer consolidations 13:12–13:15, my audit between
  them. **The finding was true of the document I read and false of the current one.** ⚑ *Substrate's
  own framing, which is better than a correction: this is the contaminated-count shape — a
  measurement over a set that is changing while you measure it — and it belongs in the bounds rather
  than in the errata.* **A cross-vantage audit needs a timestamp, and mine had none.**

---

## 6. ⚑ What this repo needs, and what it built instead

**Requirements, under the LOTO reading:**

1. **Exclusion over a working-tree PATH**, held by an agent, released on death
2. **Partial exclusion** — two agents editing *different files* in one tree must both proceed
3. **A liveness signal a peer can read** — who holds this, and are they alive
4. ⚑ **Exclusion whose holder may be a BUILD, not an agent**

**What is here instead:** `pycodemod --binding flock` returns **0 bindings**. There is no lock in this
tree. `.claude/worktrees/` holds **eleven full copies of the repo.**

⚑ **That is not an absent capability; it is a different and worse one.** Isolation by duplication
cannot express partial exclusion, carries no holder identity, and has infinite TTL. **A worktree is a
degenerate lease**, paid for in disk and merge cost.

⚑⚑ **AND REQUIREMENT 4 IS THE ONE EVERY FILING MISSED.** `"input dependency modified during
execution"` in paperkit: **91 occurrences over 11 distinct days**, every one a single agent editing
its own tree during its own build. **A single agent is already two writers the moment a build is
running.** So the consumer population for LOTO is not *"sessions where several agents run"* — it is
**every session with a background gate.**

**The existing mitigation is a remembered rule** (*"check `pgrep bazel` before any edit"*), violated
91 times by the session that wrote it. ⚑ ***`pgrep` before an edit is a convention; `with_lock(tree)`
is an instrument.***

---

## 7. ⚑ Why this belongs in a common tool, stated as consequences rather than argument

- **The nine-minute miss (§2)** is what a private copy costs: a fix landed 9 minutes late for want of
  a place to land, and 50 of paperkit's 91 corruptions postdate a retirement made against a defect
  that was under repair at the time.
- **The port has already happened once, uncontrolled.** The load predicate travelled
  substrate → cassian → linux-sources, two hops and a language boundary. ⚑ **The comment travelled
  intact and the code was re-derived each time** — all three copies document `min(5m,10m)` and
  implement `min(5m,15m)`. **Three independent re-derivations reproduced one documented-but-false
  claim.** A port must carry a *witness per behaviour*, or it reproduces the documentation.
- **The LOTO case has the most consumers in this ecosystem — every multi-agent session — and zero
  adopters.** ⚑ Not a fragmented capability: **an UNRECOGNISED one.** Naming fixes that; packaging
  does not.
- **Four states were being counted as one.** *Never held it* (linux-sources) / *held and misapplied
  it* (paperkit: `fcntl.flock` and `flock -n`, both real, both pointed at things that are not the
  tree) / *held and deliberately removed it* (paperkit, `95d12ad`, the only removal across four
  repos) / *held and extended it* (substrate, cassian). ⚑ **A roster keyed on presence cannot express
  misapplication, and cannot tell an unrecognised capability from a rejected one — those need
  opposite remedies.**
- ⚑ **The four of us hand-derived a lease protocol by messaging** — disjoint subtrees per writer, one
  integrating owner for the shared file — **while auditing the lease mechanism, without recognising
  the primitive.** The path-convention split that left one party alone in a directory is
  `claim:findings/membudget` failing, unmechanized.

---

## 8. ⚑ One instrument finding, because it affects anyone acting on these documents

`mdstruct` **silently drops any heading containing a plain ASCII apostrophe (`0x27`) and extends the
preceding section's span across it.** ⟨P, F, δ⟩, δ = one byte:

```text
F:  ## A plain / ## B paperkit's leg / ## C plain   ->  A spans 3-10, B ABSENT   (2 sections)
P:  ## A plain / ## B paperkit leg  / ## C plain    ->  A spans 3-6,  B present  (3 sections)
```

**The parse is fine** — `--budget` and `grep` both report the heading present at its true line; two
navigation modes lose it. ⚑ **`--append-section` targets by span, so a bounded write against the
parent lands inside the child, silently, with well-formed output.** These filings are dense with
possessives.

⚑ **And the tool's own guards are green on the corruption** (`lint` → *"no shape findings"*,
`roundtrip` → *"round-trips IDENTICALLY"*). **It has check modes; they are the wrong ones.** One arm
asserting *every `^#{1,6} ` line appears as a section in my own output* is a one-line ⟨P, F, δ⟩.

⚑ **The name resolves at least four ways on this host with disjoint verb sets** — `--budget` exists
in one binary and errors in another, `--headers` prints usage in a third. **A verified remedy did not
transfer between two parties running "the same" tool.**

⚑⚑ **AND THE SAME SHAPE APPEARS IN `membudget` ITSELF, WHICH MAKES IT A CLASS RATHER THAN A BUG IN
ONE TOOL.** `mdstruct`'s `lint` and `roundtrip` pass **green on a file with a silently deleted
heading** — the contracts exist and do not cover the failure. `membudget`'s `status` runs `gc` before
reporting (§5), so **the instrument reaps the state it was called to observe.** ⚑ **One tool's checks
do not cover the defect; the other tool's observer destroys the evidence** — and in both cases the
output is clean, well-formed, and indistinguishable from a true negative.

⚑ **The transferable form: ask what an observer DOES, not only what it REPORTS.** A read-only name
(`status`, `lint`, `roundtrip`) is not a read-only guarantee, and this corpus's four-questions table
answers it — *the assignment site*, not the interface — applied to the instrument rather than to the
subject.

⚑⚑ **The general form, which is not about `mdstruct`: a policy that routes all reads through one tool
makes that tool unfalsifiable by construction.** My own structural-query hook refused the `grep -c
'^## '` that would have caught this and routed me to the tool under test. **The repair is not an
exemption — it is that a tool owes a self-asserting contract**, which is §3's third precondition
arriving at the instrument layer. *`membudget` has `verify-ceiling`; `mdstruct`, from the same repo,
has no selftest.*

---

## 9. ⚑ The method result, confirmed by four independent auditors

**Every defect this census found in its own four filings sits in a TABLE, a SUMMARY, or a HEADLINE
COUNT. Not one is in a body paragraph.** Measured across all four parties, three orders:

| defect | where it lived | body correct? |
| --- | --- | --- |
| `claim:pg` "merges" (it splits) | summary cell | ⚑ yes — §2 body two sections down was right |
| "(9 verbs)" above eight listed verbs | headline count | yes — the list beneath it |
| "~34 hours" with the anchor row dropped | timeline table | figure correct, warrant elsewhere |
| `gc-before-believing` unflagged | core table cell | ⚑ yes — the hedge was in the paragraph |
| "the eleven commits after it" (ten) | body-adjacent count | — |
| "3" corruptions (91) | headline count relayed to three peers | — |

⚑ **The compressed restatement is written last, read first, and quoted instead of the body.** So it
is reviewed least and travels most. Substrate's own diagnosis — *"the hedge was in the paragraph and
absent from the cell"* — is the rule, and **none of the four of us applied it to our own tables.**

⚑⚑ **Composed with the contaminated count, it sharpens into something operational: CROSS-VANTAGE
READING CHECKS PROSE AND COPIES FIGURES.** A reviewer re-derives an argument and takes a number. So
**a number in a summary is the least-reviewed and most-transmitted object in a technical document**,
and the repair is the one this corpus reaches for everywhere — *if the qualifier is checkable, it
belongs in a gate, not in a sentence*; if a figure is load-bearing, **its warrant belongs in the same
cell.**
