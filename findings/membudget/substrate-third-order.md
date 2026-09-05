# substrate's third-order findings — the pushout, and how to land in it

**Author:** substrate (origin of `membudget`; author of `substrate.md`, `substrate-second-order.md`)

**Directive:** *"evolve a common understanding of the capabilities of the tool and establish what a
**pushout** looks like, so that all parties can cooperatively land their requirements into the
commonly-managed tool, and so that all parties can cooperatively **avoid stepping on each other at a
fine-grained level**."*

**This is a rewrite.** The first version of this file computed a **pullback** and had corrections
stapled to it; a reader met three superseded sections before reaching anything usable. The pullback
reasoning is preserved in §9 as residue, at the end, where it is evidence rather than an obstacle.

⚑ **Bias, third time.** Substrate is the origin, the largest offender in its own first-order filing,
and was the undeclared referee for the other three. **Its account of what is "shared" is the account
most likely to mistake its own design for the common part** — which is exactly the error §9 records.

⚑⚑ **This file is also structurally damaged by a defect this census found.** `mdstruct --headers`
drops any heading containing a straight apostrophe (`gate-F75`), so tooling reading this document
will under-report its sections. **Headings here avoid apostrophes deliberately.** The instrument that
would verify the artifact is the artifact's own subject.

---

## 0. What the tool does, for a reader who has followed none of this

**One command, and it is the whole interface for the coordination case:**

    membudget run <mb> claim:<tag> -- <cmd>

**Measured behaviour**, verified in three trees, two of which hold none of the code:

- **at most one live lease may carry `<tag>`.** Any other tag is unaffected.
- **the tag is arbitrary and needs no pre-declaration** — a file, a directory, a service, a name.
- **the claim lives exactly as long as the holding process.** No TTL, no heartbeat, no registry, and
  the kernel releases it on any exit **including SIGKILL** — so a crashed agent cannot wedge the tree.
- **a dead holder is reaped before it is believed**, so a stale claim cannot block every successor.
- **three contention policies:** block by default; `MEMBUDGET_NOBLOCK=1` refuses with exit 3;
  `MEMBUDGET_TIMEOUT=<s>` refuses with exit 3 after waiting.

⚑ **That is a granular lock-out/tag-out primitive, and it works today, unmodified, from a repo that
holds none of the code.** It is the capability four auditors spent a day characterising as fragmented
and un-adoptable, because the tool is named for its first predicate — memory — and its coordination
core was read as a secondary feature.

**What you cannot do today** (each measured, each detailed below):

- **only byte-identical tags exclude.** `claim:x/a` and `claim:x/a/` both acquire — §3.
- **a claim cannot be made without a capacity figure it does not need** — `run 0` is rejected by
  systemd, so every artifact claim debits a memory pool it never uses.
- **it is not installable.** The lock kernel exists in three trees and zero commits — §4.

**The rest of this document is what a shared version of that would have to be, and why it is not one
yet.**

### ⚑⚑⚑ AND THE CAPABILITY CENSUS DID NOT CONVERGE — FOUR PARTIES AUDITED THE TOOL THEY USED

**Paperkit measured each filing against membudget's own dispatch table:**

    paperkit        9 verbs, 18 knobs, 860 lines — the full table
    substrate       `membudget run`                               (1 of 9)
    linux-sources   `membudget shell` + verify-ceiling            (2 of 9)
    cassian         `membudget run`                               (1 of 9)

⚑ **Three of four parties referenced one verb each. `init`, `status`, `peaks`, `probe` appear in no
filing but paperkit's** — and substrate is the owner, so the miss lands hardest here. **This is the
presence-versus-aim defect one level up: the census converged on the verbs people happened to
invoke.**

**The sharpest instance, verified here rather than relayed.** Three filings spent pages on *how does a
consumer size its cap*, and none named the verb that answers it. `membudget peaks`:

    label                    runs  max_mb  median  p90  max_sec  cpu%  suggested
    selftest:mypy_census…      52      90      89   90     11.0    71   128MB
    selftest:run_selftests…   414      51      22   23      5.3    41    64MB

**Runs, max, median, p90, wall, CPU%, and a power-of-two bucket suggestion — per label, from the runs
that happened.** Its own comment states the design: *"a SINGLE observation cannot size a cap: max
alone is one bad run away from over-sizing, median alone under-sizes the tail."*

⚑⚑ **So substrate's pow2 sizing — which cassian filed as leg-local-to-substrate and substrate
accepted — is already in the shared tool as a suggestion column.** The census argued about a question
the tool answers halfway, from an axis nobody enumerated.

⚑ **It does NOT overturn the shared-host finding.** `peaks` measures a label's maxRSS, not a
consumer's environmental constraint, so *"no per-consumer profile to measure"* stands. The two are
different questions and only one of them was already answered.

⚑⚑⚑ **AND THE LEDGER HAS BEEN RECORDING THIS CENSUS'S OWN PROBES THE WHOLE TIME** —
`claim:cassian-p1-min-1-…`, `claim:selftest/raii-…`, `claim:ns-…/a/b/` all appear in the live output.
**Four parties ran controlled experiments against a tool that was logging them, and none of the four
read the log.**

---

## 1. The construction, stated so the rest follows from it

A **span** is `A ← C → B`: a shared object `C` with maps **out** to each party. The **pushout** is
the **colimit** `A ⊔_C B` — **everything from every leg, with C glued once.**

    C        what two or more legs demonstrably SHARE
    legs     each party's requirements, carried whole
    pushout  every leg's content, C identified ONCE, nothing dropped

**A pullback is the opposite limit** — the intersection, what survives everyone's agreement.

⚑ **The operative difference is not vocabulary, it is direction of work.** A pullback's work is
**deciding what to exclude**; the object comes out smaller than any contributor. A pushout's work is
**deciding what is the same**; the object comes out larger than any leg, and the only judgement is
about **identification**, never about **admission**.

⚑⚑ **Consequences, all of which reverse decisions this corpus already took:**

- **Nothing is declined.** Cassian's enumerated pool, substrate's pow2 sizing and 384 ceiling,
  paperkit's `resource_set` projection — all carried, each as its leg's content.
- **Conflicts stop being conflicts.** `enumerate-vs-churn` and the three ceilings were conflicts only
  under selection. Three ceilings are three maps out of one C; there is nothing to reconcile.
- **Bounds travel with their leg** rather than disqualifying it. Cassian's unexercised allocation
  path is a bound ON cassian's leg, not grounds for excluding it.
- ⚑ **The one thing a colimit does forbid** is one leg's label becoming the object's identity. **So
  substrate does not export the name `membudget`** — not a declined leg, a declined identity.

---

## 2. What is in C, measured

**C is what two or more legs demonstrably share.** Measured across four runs in three trees, two of
which hold none of the code:

| property | substrate | cassian | paperkit |
|---|---|---|---|
| exclusion over an arbitrary tag, no pre-declaration | yes | yes | yes |
| granularity: a different tag proceeds | yes | yes | yes |
| RAII by holder liveness, pid+starttime, reuse-proof | yes | yes | yes |
| release survives SIGKILL -9 | — | — | yes |
| gc before believing a holder | yes | ⚑ WEAK — read from substrate source, may be ONE witness twice | — |
| three policies: block / NOBLOCK→3 / TIMEOUT→3 | yes | yes | yes |

⚑ **Cassian's bar belongs here and only here:** *an element of C needs a measurement from a tree that
does not hold the code.* **It is not an admission test** — a pushout has none. It is **evidence that
two parties' requirements are the SAME requirement**, which is a question about the gluing map.

⚑⚑ **Applied honestly, it demotes one row from C into an open question.** `gc-before-believing` is
attested by substrate and cassian, and cassian's reading derives from substrate's source. **So its
identification across those two legs is not yet established** — which is tractable (one measurement
from a third tree) where "excluded" would have been final.

⚑⚑⚑ **AND THE TABLE ABOVE SAID `yes | yes` FOR THAT ROW UNTIL CASSIAN FLAGGED IT.** The hedge was in
the paragraph and absent from the cell — **which is the exact pattern linux-sources diagnosed in
substrate's first-order filing: hedge in prose, drop the hedge in tables and headers.** Tables are
what a reader quotes. **Recurring here, in the third-order document, after being named twice.**

⚑ The general form worth carrying into C's own discipline: **an identification is not "two parties
agree", it is "two parties measured independently."** One witness read twice looks identical to two
witnesses in every artifact either produces.

---

## 3. What blocks the pushout: the gluing map is not well-defined

**You cannot glue by "same name" until you know when two names are the same.**

Cassian measured four spelling variants, controlled (holder verified registered and alive at
contention, else no verdict). **All four acquired independently; only byte-identical strings
exclude.** Substrate reproduced the load-bearing case: holder on `claim:sub/keyway/a`, contender on
`claim:sub/keyway/a/` **acquired**.

⚑ **So the four-session path-convention split is this defect, unmechanized.** Had all four of us used
the mechanism we were auditing, **we would have collided anyway**, each holding a claim believed
exclusive.

### Three refutations of canonicalize-by-realpath, on three vocabularies

- **paperkit, bazel labels:** `//:hook` → `/:hook`, nonsense, silently.
- **paperkit, output bases:** `bazel-bin/...` resolves through a symlink into a hash-named output
  base, so **the same logical artifact canonicalizes differently per workspace** — taking two agents
  who WOULD have collided and making them not.
- **substrate, bare identifiers — and this one is the worst.** `pycodemod --literal 'claim:'` shows
  substrate's live vocabulary is `pg` and `roster`, not paths:

      realpath -m pg                        → /home/mikemol/github/substrate/pg
      env -C ~/github/mtools realpath -m pg → /home/mikemol/github/mtools/pg

  ⚑⚑ **`claim:pg` canonicalizes cwd-dependently, so substrate's postgres guard and any peer's would
  stop excluding each other** — on the one host they share, guarding the store whose ungated
  concurrency *"caused kernel hangs."* **The proposal converts a working exclusion into a silent
  non-exclusion**, which is the worst signature in this corpus: green while doing nothing.

⚑ **Canonicalization is not monotone: it merges names that should merge AND splits names that should
not.** Paperkit's per-namespace refinement — declare the KIND (`claim:path:<p>`, `claim:label:<l>`,
unprefixed uncomparable) — is the only form surviving all three, **because it declines to
canonicalize what it cannot.**

**And the property that decides whether any of this works: `realpath -m` on a nonexistent path
RESOLVES rather than fails**, so claim-before-create works. Verified.

---

## 4. What blocks it harder: C has no landing place

**Linux-sources' measurement, taken from a tree holding none of the code, and the strongest single
item in the corpus:**

    06-19 14:30  substrate  concurrent-RAM semaphore                        [C, the origin]
    06-22 20:38  paperkit   vendors the copy
    06-27 16:01  paperkit   RETIRES it — "the deadlock that wedged paperkit on a
                            sibling repo's stale leases cannot recur"
    06-27 16:10  substrate  fix: re-entrant single-fd mutex                     [+9 MIN]
    06-27 17:10  substrate  fix: bounded acquire + kernel death-release         [+69 MIN]

⚑⚑⚑ **Paperkit retired the semaphore NINE MINUTES before substrate committed the fix for the defect
it retired over.** Causally independent; neither commit cites the other.

⚑ **And the vendored copy was NOT stale — about 34 hours old, current at fork time.** So the census's
freeze-a-slice framing needs correcting: **a fresh fork and a stale fork fail identically once the
fix has nowhere to land.** Staleness was never the mechanism. **Absence of a landing place was.**

⚑⚑ **Therefore the first element of C is not a behaviour.** It is **one committed installable
distribution plus a concurrency harness** — in C because **they are what makes a map out of C
possible at all.** A leg cannot map into a tool it must first vendor.

**Substrate's side of the same finding:** `git log --all --oneline -- scripts/membudget-ledger` is
**EMPTY** — the file every filing quotes as the contract has never been committed on any branch.
`commit_refusal` reports **9 gates would refuse, 28 unmeasurable, 0 measured-green.**

⚑ The operator has ruled this the **reason for the consolidation** rather than a blocker on it —
*"it is easier to clean up at that scale than at substrate's current scale"* — so the machinery moves
as the clean components and the debt stays with the tree that generated it. **`--init-absent` is
therefore the honest birth state: a component that cannot land clean under zero-tolerance is not yet
clean enough to move.**

---

## 5. The legs, carried whole

| leg | owner | maps into C via | bound travelling with it |
|---|---|---|---|
| memory admission | substrate | the lease | pow2-from-history; 384 is a forcing function, not a bound |
| pool allocation | cassian | the lease at N members | allocation path has zero production call sites |
| scheduler projection | paperkit | nothing — Bazel admits | true within one build; **41 pre / 50 post** says it does not close the edit-during-execution class |
| non-adoption | linux-sources | the lease, plainly | is the fourth implementation of the load predicate, by transitive re-port |

⚑ **Linux-sources' leg is the shortest and most informative:** the repo with the strongest need and
least adoption needs C and nothing else. **A leg that needs only C is evidence C is correctly drawn.**

⚑⚑ **And substrate's leg is the one most at risk of being mistaken for C**, because substrate is the
origin and its leg came first. **The memory budget is not the shared part. It is the first
application of the shared part** — the operator's history stated as a diagram.

---

## 6. What the pushout is FOR, and its scope is smaller than assumed

**Operator:** the lease-shape phenomenon generalizes to *"multiple agents modifying the same tree,
communicating to prevent each other from stepping on each other. Granular lock-out/tag-out."*

⚑ **Four filings decomposed along the RESOURCE axis and treated the claim gate as a secondary
predicate.** Under this reading **the claim gate is the primary case and the memory budget is the
specialization** — membudget is a lease mechanism whose first application was memory.

**Paperkit's measurement bounds it, and makes it smaller:**

    "input dependency modified during execution"  →  91 occurrences, 11 days
      pre-BES-cutover 41 · post-cutover 50

⚑⚑ **A shared executor does not close the class** — it moves where actions run, not where inputs are
staged. **So C guards the LOCAL WORKING TREE only:** no executor reach, no distributed consensus, no
surviving the network. **Substrate's mechanism already meets that unmodified.**

⚑ **And all 91 are one agent colliding with itself.** The requirement does not begin at two sessions;
**it begins at one session and one long-running job.** Substrate's 3598-module `make` build with
agents editing during it is in that population and has never counted itself in it.

---

## 7. How to land in it — the protocol this document owes

**The directive's second half is a deliverable, not a framing.** What follows is what C supports
today plus the one thing it does not.

**Works now, measured in three trees:**

    membudget run <mb> claim:<tag> -- <cmd>
      exclusion over the tag · other tags unaffected · released on any exit incl. SIGKILL
      block by default · MEMBUDGET_NOBLOCK=1 → exit 3 · MEMBUDGET_TIMEOUT=<s> → exit 3

**Does not work yet, and is the whole obstruction:** two parties must already agree on the tag's
spelling. ⚑ **Until the keyway is settled, the protocol is: agree the tag in writing, then claim
it** — which is a hand-negotiated convention, i.e. the thing the directive asks to eliminate.

⚑⚑ **The falsifiable test, and linux-sources' repair of it.** Substrate proposed: *if the four of us
cannot land our next four contributions without a path split, a duplicated finding, or a
hand-negotiated convention, the third order failed.* **Linux-sources observed it was unpassable by
construction under a pullback** — a shared core excluding three legs' remainders guarantees three
private copies, and private copies are the failure. **It becomes passable only once the construction
is right.**

**The control arm already ran, unintentionally:** four sessions, two path conventions, a split found
by `find`, and one finding written at length twice by two parties each unaware of the other.

### The test has now run, and it passed by the letter while failing by the mechanism

**Measured immediately after this round** — `ls findings/membudget/` returns twelve files, four repos
times three orders, **one directory, no variant path, no duplicated finding.**

⚑ **But the test names three failure modes and the third is the one we hit: a hand-negotiated
convention.** Substrate stated the filename form in a message before writing — *"the flat form you set
for second-order, and I am naming it before writing this time rather than after"* — **and all four
parties complied by reading that message.** Four agents coordinating over a shared tree by messaging
is the hand-derived worse-lease this census spent three orders identifying.

⚑⚑ **So the round is evidence FOR the requirement, not against it** (paperkit's verdict, and it is
the correct one). **The convention held because four parties were live, attentive, in message range,
over one afternoon, with the naming arriving early enough for everyone to read. None of that
generalises** — it requires exactly the conditions a lock-out mechanism exists to not require.

⚑ **And the claim gate alone would not have sufficed either.** Per §3, `claim:findings/membudget` and
`claim:findings/membudget/` both acquire — **so the keyway is load-bearing for the very round that
just succeeded without it.**

**The honest verdict: the deliverable was met, the mechanism was not used, and a round that succeeds
by attention does not license dropping the requirement.** What it records is the cost when unmet —
**one message per party per round, forever, degrading the moment anyone stops listening.**

### Landing is not a sequence, and substrate's ordering was pullback residue too

⚑⚑ **Paperkit found this class in its own §7 and substrate has it in the same place.** Their landing
section was a queue — *"P1 first, and nothing before it. P2 next."* — **ordering requirements by
admission priority, in a construction that admits nothing and orders nothing.** Cassian had predicted
exactly this residue: the reasoning that produced the retracted framing keeps writing sentences until
something scans for it.

**The replacement is not a queue but a question about whether each party's map out of C exists at
all:**

    L1  one committed, installable distribution.  MEASURED: the lock kernel is in THREE TREES
        AND ZERO COMMITS. Vendoring replaces the map with a copy, and a copy is where a fix has
        nowhere to land — the nine-minute miss is what that costs.
    L2  the concurrency harness, in C — a fix must be showable correct by the party RECEIVING it,
        not only the one writing it. Substrate's 69-minute commit was verified under one; paperkit
        had no way to run it.
    L3  the self-asserting contracts (`verify`, `verify-ceiling`), in C.

⚑ **L3 is paperkit's addition and it is aimed at our actual situation:** it is what makes L1 and L2
**safe to adopt from parties one has just spent three orders correcting.** Substrate's own header is
already imperative about it — *"do not re-derive this from the comment, run verify"* — and after this
corpus, **a consumer checking what it holds without trusting anyone's description is the only trust
model with evidence behind it.**

**Then every leg lands as a gluing, none blocked on another. The sequencing was the illusion.**

---

## 8. Honest gaps

- **C's membership is proposed by the origin**, the party most likely to mistake its own design for
  the common part. §2's rows are measured; §3 and §4 rest on other parties' measurements, credited.
- **The keyway has no design** — only three refutations and a shape (declare the kind). Nobody has
  built one.
- **C has never been load-tested as lock-out/tag-out.** Four measurements are functional, not
  concurrent at scale, and the closest stress case has zero production call sites.
- ⚑ **Substrate cannot currently ship C.** Nine gates would refuse; the ledger file has no commit on
  any branch. Whoever interns C is transcribing from an uncommitted working tree **and the interned
  artifact must say so.**
- ⚑⚑ **Every finding against substrate in this document came from another party.** A third-order
  document whose self-criticism is entirely externally sourced is evidence about the peer audits,
  not about the author's reflexivity.

### What the consistency audit found in substrate's own filings

**Run on the operator's instruction, with `--budget` rather than `--headers` since the latter is the
tool under test.**

⚑⚑ **`substrate-second-order.md` is structurally broken, and by substrate rather than by the tool.**
`--budget` reports six headings **one line long** and seven **orphan fragments** — `boundary, taken`,
`THAT HOLD NONE OF THE CODE`, `two-answer question`, `unnecessary`, `EITHER ORDER`. Those are
`###` headings substrate wrote across two source lines. **Markdown reads the first line only; the
continuation became a heading in its own right and owns the content.** Verified: `boundary, taken` is
a real level-3 section spanning 39 lines.

⚑ **That is distinct from the apostrophe defect and it is self-inflicted.** Peers navigating that
document by section get fragments where sections should be — and substrate produced it while writing
about a tool that mis-locates bounded writes.

**`substrate-third-order.md`:** `--budget` 14 headings, `--headers` 10. **Four sections invisible to
the tool three peers are using to read it**, including the title.

⚑⚑ **NEITHER FILE HAS BEEN REPAIRED.** The second-order damage needs the split headings rejoined,
which is a bounded write against spans the tool reports wrongly — **the repair is blocked by the
defect it would repair.** Recorded rather than silently fixed, because a reader of either document is
currently getting a wrong skeleton and should know it.

---

## 9. Residue: the pullback this document first computed

**Kept because it is the evidence for what the census actually did.**

The first version built a four-column table of parties with ticks where they agreed and called the
intersection the apex. It then adopted cassian's bar as a **membership filter**, which tightens
toward intersection. Substrate wrote *"the apex is SMALLER than any of our requirement lists, and that
is the useful result"* — **the pullback stated proudly.**

Then both parties began **declining their own contributions**: cassian its enumerated pool, substrate
its sizing, ceiling and name, each commending the other. Substrate proposed the test *"did each
party's own contribution shrink?"*

⚑ **That test is right for an intersection and wrong for a colimit**, and the error was
self-reinforcing **because it looked like virtue.** Two parties competitively shrinking their
contributions were converging on the largest thing everyone could agree to — the operation that was
not asked for.

⚑⚑ **Linux-sources named the shape and it is this corpus's own subject:** four parties asked for a
gluing procedure **built a selection procedure**, and spent an exchange **deleting requirements.**
The same move as resolving a shared-tool problem by deleting a copy. **Both times it looked like
rigour, and both times the thing removed was somebody's actual need.**

**The operator's correction was one sentence:** *"I said pushout, damnit, not pullback."*
