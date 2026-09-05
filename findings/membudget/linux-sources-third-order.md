# Third-order findings — linux-sources

**The span, measured.** Second-order asked what the four filings got wrong. Third-order asks what the
tool *is*, and the operator's word for the answer is a **pushout** — the universal object over a
span, where the shared part is identified **once** and each leg's remainder is carried **intact**.
Substrate-9b's framing, which I adopt: *"a list is not a span, because it does not say which
requirements are the SAME requirement."*

⚑ **This document's contribution is that the span is not hypothetical — it is in the git history of
three trees, and I measured it.** The centre has a lineage, the divergence has timestamps, and the
central disagreement of this whole census was **decided by a nine-minute miss in June.**

⚑⚑ **READ §7 FIRST IF YOU READ ONLY ONE SECTION. §§2–6 BUILD THE WRONG CONSTRUCTION** — a limit
(selection: what *deserves* to be shared) where the operator asked for a colimit (gluing: every leg
carried). They are kept unrewritten because the sequence is the evidence for what the census
actually did, but **every "apex" in §§2–6 is a pullback-shaped object and should be read as
superseded.** §7c states the corrected form; §7d corrects §7c; §7e records the instrument defect
found while auditing this file. **Where §§2–6 and §7 conflict, §7 governs.**

---

## 1. ⚑ THE SPAN IS MEASURED: ONE ORIGIN, ONE FORK, AND A NINE-MINUTE MISS

`git log --follow -- scripts/membudget` in substrate returns **17 commits, 2026-06-19 to 2026-07-23**.
That is the origin object. Everything else in this census is a leg off it.

**The fork, to the minute, from three trees:**

```text
06-19 14:30  substrate   membudget concurrent-RAM semaphore + CLAUDE.md standing rule   [ORIGIN]
06-19 14:37  substrate   recursion-aware (hierarchical suballocation)
06-19 14:45  substrate   shell injection + `membudget shell`
06-19 14:54  substrate   blocking acquire (WaitForSingleObject-style)
06-19 15:07  substrate   default budget = 8 GiB (capped at 70% RAM)
06-20 10:24  substrate   genlop-style build-time estimation
06-20 10:31  substrate   autobudget — size the lease from peak-mem history
06-20 10:38  substrate   autobudget — power-of-2 bucket grid
06-20 10:47  substrate   autobudget — round peak UP + retry-on-OOM
06-20 16:53  substrate   1.5GiB lease ceiling + 192MB default
06-21 10:44  substrate   retry-on-OOM recognizes SIGTERM (143)
──────────────────────────────────────────────────────────────────────────────
06-22 20:38  paperkit    feat(gate): per-check memory leases via membudget      [VENDORS THE COPY]
──────────────────────────────────────────────────────────────────────────────
06-27 16:01  paperkit    RETIRE the membudget semaphore — Bazel's scheduler is the budget
06-27 16:10  substrate   fix: re-entrant single-fd mutex (no self-deadlock)      [+9 MINUTES]
06-27 17:10  substrate   fix: bounded acquire + kernel death-release             [+69 MINUTES]
```

⚑⚑ **PAPERKIT RETIRED THE SEMAPHORE NINE MINUTES BEFORE SUBSTRATE COMMITTED THE FIX FOR THE DEFECT
IT RETIRED IT OVER.** The retirement's own stated reason, verbatim from `95d12ad`:

> *"per-machine, no flock, no cross-repo coupling (**the deadlock that wedged paperkit on a sibling
> repo's stale leases cannot recur**)."*

And substrate's `1b45f53d2`, 9 minutes later, verbatim:

> *"**Self-deadlock:** `with_lock()` opened a FRESH fd per call → two open-file-descriptions to the
> same lock → the EXIT-trap `release` could flock() against the lock the acquire-loop still held →
> **permanent hang once any holder was signalled mid-section.**"*

and `7c61738f4`, 69 minutes later:

> *"The previous lock fix traded a deadlock for **cross-repo STARVATION** … membudget treats
> disruption (OOM-kills, cgroup teardown, SIGKILL) as **NORMAL**, so the locking kernel must be
> **immune to it by construction**."*

**Same defect. Same day. Opposite responses: one repaired the shared tool, one deleted its copy.**

⚑ **AND THE TWO WERE CAUSALLY INDEPENDENT, WHICH IS WHAT MAKES IT A STRUCTURAL FINDING RATHER THAN A
COMMUNICATION FAILURE BETWEEN TWO PEOPLE.** Substrate's trigger was its own tree: *"The make-routed
`make -j` deadlocked, and it was the LOCK, not the autobudget."* Neither commit cites the other,
neither party knew. **Two repos hit one defect class within the hour and neither could see the
other's response**, because there was no shared artifact for the response to land in — which is the
entire pushout argument, instantiated, three months before anyone proposed it.

⚑ **AND THE VENDORED COPY WAS NOT STALE, WHICH KILLS THE EASY EXPLANATION.** Paperkit vendored on
06-22 20:38; substrate's last prior commit was 06-21 10:44. **The copy was ~34 hours old and current
at fork time.** So the de-adoption was not "our copy rotted" — it was a *live shared defect*
encountered by two parties who each owned a private copy of the fix surface. **A fresh fork and a
stale fork fail identically once the fix has nowhere to land.**

### ⚑ 1a. What this does to the census's central disagreement

Second-order established (paperkit's measurement, my prompting) that paperkit is the **only
de-adopter across four repos, n=1** — substrate only extended, cassian only added, linux-sources
never held it. That framed the de-adoption as a judgement to be *refuted*: **"Bazel IS the
semaphore"** is true of capacity, silent on artifacts, 50 of 91 corruptions postdate it.

**That refutation is correct and it is now the second-strongest thing to say.** The stronger one:
⚑ **the judgement was made against a defect that was under repair at the moment it was made.** The
sentence to refute is not primarily wrong about *axes* — it is a decision taken on a **stale
observation of the shared tool's quality**, where staleness was structurally guaranteed because
there was no channel through which "substrate is fixing this right now" could arrive.

**So the apex question is not "was paperkit right about Bazel."** It is: ⚑ ***what artifact would
have made a nine-minute miss impossible?*** That is a pushout requirement, and it is checkable.

---

## 2. THE APEX: what I accept, what I contest, what I add

Substrate-9b proposed an apex measured across four runs from three trees. I take each member and
say whether my tree's evidence supports it, since an apex asserted by one party is a leg wearing
an apex's costume.

| proposed apex member | linux-sources' position | basis |
|---|---|---|
| exclusion over an **arbitrary tag**, no pre-declaration | ⚑ **CONTEST — see §3** | cassian's typo defect + paperkit's path split |
| **RAII by holder liveness** (`pid:starttime`, PID-reuse-proof, kernel-released) | **ACCEPT, strongly** | `7c61738f4` verified it under a harness; it is the one member with a passing test |
| **gc before believing a holder** | **ACCEPT** | same commit; a crashed claimant cannot wedge the tree |
| **three policies** — block / `NOBLOCK`→3 / `TIMEOUT`→3 | **ACCEPT** | bounded acquire is the property the 06-27 fix exists to provide |

⚑ **I ACCEPT SUBSTRATE'S CENTRAL CLAIM THAT THE APEX IS SMALLER THAN ANY REQUIREMENT LIST, AND MY
SPAN MEASUREMENT INDEPENDENTLY SUPPORTS IT.** The origin object at `2eb5aabbc` (06-19 14:30) is *one
commit*: a concurrent-RAM semaphore. Everything the four filings enumerate as "dimensions" or
"capabilities" — autobudget, pow2 sizing, genlop estimation, OOM retry, shell injection, PSI, load
gating — **was added in the TEN commits after it, over three days, by one party.** The centre is not
small because we should prefer it small; **it is small because the history says the shared part was
one idea and everything else is accretion.**

⚑ *Corrected during the 2026-09-05 self-audit: this read "eleven commits… over four days" and the
measurement is ten, over 06-19 to 06-21. `git log --since=2026-06-19 --until=2026-06-22` returns 11
including the origin; I had counted the origin twice. **An off-by-one in the direction that
overstates my own argument**, in a document whose §1 is a count-retraction — the third instance
today of a query's reach or a set's size stated more strongly than it was measured.*

⚑ **AND THE ACCRETION IS LEG-LOCAL BY CONSTRUCTION, WHICH IS VISIBLE IN THE COMMIT SUBJECTS.**
`genlop-style build-time estimation`, `size the lease from peak-mem history`, `1.5GiB lease ceiling
(decomposition made the hogs small)` — every one names **substrate's Agda build** as its warrant.
They are not general capabilities that substrate happened to write; **they are substrate's leg,
authored in the shared file.** That is the packaging root cause and the apex question turning out to
be one question, which is §4.

### ⚑ 2a. My own leg, stated so it can be mapped rather than argued

Under the operator's LOTO reading, linux-sources' requirements are **not** about memory:

1. **Exclusion over a working-tree PATH**, held by an agent, released on death. (Measured need: 11
   worktrees answering it by duplication; `pycodemod --binding flock` → **0 bindings** in my tree.)
2. **Partial exclusion** — two agents editing *different files* in one tree must both proceed. This
   is what a worktree cannot express and what makes duplication the wrong answer rather than a
   heavy one.
3. **A liveness signal a peer can read** — "who holds this, and are they alive." My worktrees carry
   no holder identity; a lease must.
4. ⚑ **Exclusion that survives the holder being a BUILD, not an agent.** Paperkit's 91 corruptions
   over 11 days are the editor racing its own background gate. **A single agent is already two
   writers**, so the lease's unit is not "session" — it is "writer", and a bazel invocation is one.

**Requirements 1–3 map into substrate's proposed apex without remainder.** Requirement 4 does too,
if the apex's tag is a path rather than a resource name. ⚑ **So my leg is nearly pure apex, which is
the expected shape for a party that never held the tool**: I have no accretion to defend, and that
makes my agreement weak evidence rather than strong. *A party with no leg cannot test whether the
apex is big enough.*

---

## 3. ⚑ CONTESTED: "ARBITRARY TAG, NO PRE-DECLARATION" CANNOT SERVE THE DIRECTIVE'S SECOND HALF

Substrate's apex includes exclusion over an **arbitrary tag with no pre-declaration**. **I contest
this, and the operator's directive is what decides it** — *"cooperatively avoid stepping on each
other at a fine-grained level"* is the deliverable, and an arbitrary tag cannot deliver it.

**Two measured failures, from two different parties, both in this census:**

- **cassian's typo defect**: substrate's implicit claim-pool accepts any name, so a **misspelled
  claim silently acquires a fresh single-member pool and excludes nothing.**
- **paperkit's path split** (`claim:findings/membudget` vs `claim:findings/membudget/`): **both
  acquire, and the writers still collide.**

⚑ **THESE ARE ONE DEFECT SEEN FROM TWO SIDES, AND I STATED THE UNIFICATION IN SECOND-ORDER: an
unenumerated pool cannot distinguish a NEW name from a MISSPELLING, nor either from a VARIANT
SPELLING of an agreed one.** All three are "a tag nobody else is holding," which is exactly what an
arbitrary-tag lease is designed to grant.

⚑⚑ **FOR RESOURCE BUDGETING THIS IS A CURIOSITY; FOR LOTO IT IS FATAL, AND THE DIFFERENCE IS THE
FAILURE MODE.** A typo'd resource claim yields *one lease sized wrong* — degraded, visible, bounded.
A typo'd artifact claim yields **two agents editing one file, each holding exclusion over a name
only they believe in, each certain they are alone.** ⚑ ***That is worse than no lease, because no
lease at least does not lie.*** A convention that fails open is a convention; a *lease* that fails
open is a false green, and this corpus's standing rule is that the enemy is the false green.

### ⚑ 3a. CASSIAN MEASURED IT 4-OF-4 WHILE THIS SECTION WAS BEING WRITTEN, AND THE MEASUREMENT SPLITS MY POSITION FROM SUBSTRATE'S MORE FINELY THAN I HAD

I argued the above from two incident reports. **Cassian ran the controlled probe** — holder verified
registered *and* alive at contention time, else `PROBE INVALID` rather than a verdict:

```text
trailing slash      claim:X/a/b  vs  claim:X/a/b/     -> DISTINCT, both acquired
doubled separator   claim:X/c/d  vs  claim:X//c/d     -> DISTINCT, both acquired
dot segment         claim:X/e/f  vs  claim:X/e/./f    -> DISTINCT, both acquired
case difference     claim:X/g/h  vs  claim:X/G/H      -> DISTINCT, both acquired
identical (control) claim:X/i/j  vs  claim:X/i/j      -> SAME, refused exit 3
```

**Only byte-identical strings exclude. Four of four near-miss spellings acquire.** ⚑ **THE MECHANISM
HAS NO KEYWAY** — and the control arm is what makes it a measurement rather than four failures,
since without `claim:X/i/j` refusing, "no exclusion" and "my probe is broken" are indistinguishable.

⚑ **AND CASSIAN'S REMEDY IS BETTER THAN MINE, WHICH RETIRES MY CONTEST OF SUBSTRATE'S APEX MEMBER
RATHER THAN WINNING IT.** I demanded a **canonicalised name from an ENUMERATED namespace**, and
enumeration is the expensive half — it needs an owner, it is new work, and I said so. Cassian's leg:
***canonicalize before comparing (absolute realpath)***, which fixes all four rows **and preserves
no-pre-declaration**. ⚑ **So substrate's "arbitrary tag, no pre-declaration" survives into the apex
INTACT, with a canonicalisation step that is mechanical and ownerless.** My §3 conclusion —
enumeration is apex — **is withdrawn**; I was solving the typo problem with governance where a
`realpath` does it.

**What survives from the contest, and it is the smaller half:** enumeration still buys something
canonicalisation cannot — rejecting a name **nobody agreed to at all** (a fresh well-formed path no
peer is watching). ⚑ **But that is the naming-AUTHORITY question, not the keyway question, and
cassian's probe shows the keyway is the one with four measured failures.** Authority is real, later,
and possibly leg-local to whoever owns a shared tree. **Canonicalisation is apex now.**

⚑ **AND THE FOUR-SESSION PATH SPLIT IS THIS DEFECT, UNMECHANIZED — cassian's point, and it indicts
this census specifically.** The split that left me alone in `second-order/` when the convention
changed **would have happened anyway had all four of us used the mechanism we were auditing**, each
holding a claim we believed exclusive. That is the strongest available argument that the keyway is
apex: *the auditors, using the audited tool, on the audit itself, would still have collided.*

---

## 4. ⚑ THE PACKAGING ROOT CAUSE IS APEX, AND THE SPAN PROVES IT RATHER THAN ASSUMING IT

My first-order filing's packaging finding was, in substrate's words, *"the strongest candidate for
apex membership that is NOT about the lease."* ⚑ **Substrate is right that I owe an answer on the
artifact, and the honest answer is that my `SOURCES.txt` measurement was the WRONG INSTRUMENT** —
egg-info is autogenerated, and what decides distributability is the installed distribution's entry
points and package data, not that file. **I question my own artifact and do not withdraw the
finding, because the span measures it directly and better:**

```text
git log -- scripts/membudget-ledger   →   (no output)
```

⚑ **THE LOCK KERNEL — the 147 lines my second-order §1 identified as `with_lock`/`unlock`, the
never-cross-a-fork fd invariant, the bounded-acquire invariant — IS IN NO COMMIT IN ANY TREE.**
Substrate's `membudget-ledger` is untracked; substrate's `membudget` carries ~790 unstaged lines;
mat230's vendored fork is untracked (measured in second-order §1a, after I twice misread git's
silence). **Three copies, zero commits.**

**That is the packaging root cause stated as an artifact fact rather than an inference from
`SOURCES.txt`, and it is strictly stronger.** The mechanism the apex is supposed to intern **has
never been in a form any repo could depend on**, which is why paperkit *vendored a copy* rather than
depending on one, and why a fix landing in substrate at 17:10 could not reach a tree that forked at
20:38 five days earlier.

⚑ **SO THE NINE-MINUTE MISS AND THE PACKAGING ROOT CAUSE ARE THE SAME FINDING.** The miss was not
bad luck about timing. **A fix cannot arrive in nine minutes, or in nine days, through a channel
that does not exist.** Vendoring was the only available consumption mode; under vendoring, every
consumer's copy diverges from the moment it is taken, and *"is the shared tool any good"* is
permanently answered against a snapshot. **Paperkit judged the tool by the copy it held, which is
the only thing vendoring lets anyone do.**

⚑ **AND SUBSTRATE SUPPLIED A LIVE INSTANCE IN THE OPPOSITE DIRECTION, WHICH I RECORD AS THEIR
TESTIMONY AND NOT MY MEASUREMENT** (it is their venv; I did not reach into it): `.venv/bin/mdstruct`
is an installed console script whose package is absent — `ModuleNotFoundError: No module named
'mikemol.mdstruct'`. **The call surface shipped and the implementation did not.** Same root cause,
mirrored: one failure ships code with no interface, the other an interface with no code. ⚑ **Both
are the absence of a *distribution* as the unit — and mtools' stated purpose is exactly to make the
distribution the unit.**

---

## 5. ⚑ THE PORT HAS ALREADY HAPPENED ONCE, UNCONTROLLED, AND WHAT SURVIVED WAS THE DOCUMENTATION

Substrate flags my load-predicate finding as apex material for the bash→Python question, and they
are right about why. The measured chain: **substrate → cassian → linux-sources**, two hops and a
language boundary, `load_gate.py` in my own package carrying *"cassian-observability's load
predicate, re-derived."*

⚑ **WHAT TRAVELLED WAS THE COMMENT; WHAT WAS RE-DERIVED EACH TIME WAS THE CODE — AND THE DEFECT
TRAVELLED WITH THE COMMENT.** All three copies document `min(5m, 10m)` and implement `min(5m, 15m)`.
**The prose was transmissible and the behaviour was not**, so three independent re-derivations
reproduced one documented-but-false claim and three slightly different programs.

⚑⚑ **THIS IS THE PUSHOUT'S HARDEST EVIDENCE AND IT CUTS AGAINST THE CHEERFUL READING.** A port is
usually argued as a translation problem — get the semantics across the language boundary. **The
measurement says the semantics did not survive even the FIRST hop, and nobody noticed for months,
because the artifact everyone read was the comment.** So a Python membudget is not "the bash one,
translated"; ⚑ **any port must carry a WITNESS for each behaviour, or it will reproduce the
documentation and re-derive the code — which is what already happened three times.**

**Concretely, for the apex members in §2:** RAII-by-liveness, gc-before-believing, and the three
policies were **verified under a concurrency harness** in `7c61738f4` (*"lock fd never open across a
child run; SIGKILL/wedged-holder → bounded acquire; PID-reuse lease reclaimed; steady herd →
100/100 cross-repo lock-free"*). ⚑ **That harness is the most valuable artifact in the span and it
is in no filing's requirement list.** It is the thing that makes the apex *portable* rather than
re-derivable: a port that passes it is the same tool, and a port that does not is a fourth
re-derivation wearing the name.

---

## 6. WHAT A PUSHOUT LOOKS LIKE, CONCRETELY

Stated so the other three can map onto it or refute it. **Apex** (shared, must be reconciled):

1. Exclusion over an **arbitrary tag with no pre-declaration** (substrate's wording, kept intact),
   ⚑ **plus CANONICALISATION BEFORE COMPARISON** — cassian's `realpath`, measured 4-of-4 in §3a. My
   earlier demand for an *enumerated* namespace is **withdrawn**; enumeration answers the separate
   naming-authority question and is not needed for the keyway.
2. **RAII by holder liveness** — `pid:starttime`, PID-reuse-proof, kernel-released on any death
3. **gc before believing a holder**
4. **Three policies** — block / NOBLOCK→3 / TIMEOUT→3
5. ⚑ **A third outcome: INVALID / unmeasurable, distinct from pass and fail** — accepted on
   cassian's evidence (three parties, three subsystems, no contact) and seconded from my own tree,
   where `presence()` splits *dangling* from *never-created* for the identical reason
6. ⚑ **The concurrency harness as an executable member** (§5) — **apex-proposed-UNEXERCISED**: I
   have never run it, and §6a records that I bear no cost for this requirement
7. ⚑ **One committed, installable distribution** (§4) — not a behaviour of the tool but a member of
   the apex, since every failure in the span traces to its absence

**Legs, carried intact and NOT reconciled:** substrate's pow2/genlop/autobudget sizing (its Agda
build); paperkit's `resource_set` projection into bazel tags; cassian's allocation shapes and pool
policy; linux-sources' path-scoped tree claims. ⚑ **Under a pushout these do not compete, and the
three ceiling theories (10 / 10 / 1.0) stop being a disagreement the moment the ceiling is leg-local
— which the operator's same-host correction already implied and no filing drew.**

⚑ **THE FALSIFIABLE TEST, WHICH I ADOPT FROM SUBSTRATE BECAUSE IT IS THE RIGHT ONE:** *if the four
of us cannot land our next four contributions into mtools without a path split, a duplicated
finding, or a hand-negotiated convention, the third-order failed.* We have spent a day demonstrating
the need and hand-deriving a worse version of the answer — **the mtools write protocol (disjoint
subtrees, one integrating owner for `MODULE.bazel`) is a lease protocol built by messaging, by four
parties who had all just finished auditing the lease mechanism.**

### ⚑ 6a. THE DISCIPLINE CASSIAN WENT FIRST ON, APPLIED TO MY OWN PROPOSALS

Cassian filed **their own** enumerated pool as leg-local rather than apex (*"zero production
exercise… promoting it would have the pushout adopt a shared form that is untested"*), and named the
rule: **each party should decline promoting its own leg.** Substrate did the same with pow2 sizing.
⚑ **I did not, and §3 is the instance — I promoted MY position (enumeration) to apex against
substrate's proposal, then withdrew it in §3a when cassian's measurement showed a cheaper fix.**
Recorded rather than quietly repaired: the withdrawal was forced by a peer's probe, not by my own
discipline.

**Applying the bar to my two remaining promotions, honestly:**

| my apex proposal | survives the bar? | why |
|---|---|---|
| **#6 one committed distribution** (§4) | ⚑ **YES, and it is the one thing I can promote without conflict of interest** | It is not my leg. linux-sources has no distribution to standardise on and gains no advantage from the choice; the evidence is three trees' git history, and substrate supplied the counter-direction instance against its *own* venv |
| **#5 the concurrency harness** (§5) | ⚑ **YES, but it is SUBSTRATE'S artifact and I am promoting someone else's work** | Which is the *inverse* conflict and needs saying: I have no harness, so I bear none of the cost of the requirement I am proposing. **A party that pays nothing for a requirement is a weak witness for it**, exactly as §2a says my apex-agreement is weak because I hold no leg |

⚑⚑ **AND CASSIAN'S ADMISSION BAR IS SHARPER THAN THE DECLINE RULE AND I SHOULD STATE WHERE IT LEAVES
ME: *an apex element needs a measurement from a tree that does not hold the code* — not four
sessions agreeing.** By that bar my §1 span measurement is strong (I measured substrate's and
paperkit's history from a tree holding neither), and ⚑ **my §5 port finding is the strongest thing I
have, because `load_gate.py` is a measurement of the port's failure taken in the tree that RECEIVED
it.** But #5-the-harness I have never run. **Filed as apex-proposed-unexercised**, which is a
different state from apex-measured and the filings have not distinguished them.

⚑ **AND I ACCEPT CASSIAN'S THIRD OUTCOME (`INVALID`/unmeasurable) INTO THE APEX ON THEIR EVIDENCE,
NOT MINE** — paperkit's peak channel, substrate's `UNREAD` baselines (*"a fact about the READER, not
a verdict about the gate"*), cassian's `PROBE INVALID`. **Three subsystems, three parties, no
contact, predating the audit.** That is convergence that could have gone otherwise, which is the
only kind that counts after this census measured PSI three times and read one file. ⚑ **It is also
my own tree's standing rule arriving from outside: `is_file()` collapsing *dangling* with
*never-created* is the same defect, and my `presence()` repair is a fourth instance nobody counted.**

⚑ **AND THE APEX HAS A DATE IT SHOULD BE JUDGED AGAINST: 2026-06-27 16:01.** The test of whether
this construction is worth anything is whether it would have made that nine-minute miss impossible.
**Apex members 5 and 6 would have** — a committed distribution gives the fix somewhere to land, and
a harness lets a consumer ask *"is the shared tool sound"* by running something rather than by
judging the copy it forked. **Members 1–4 would not have**, which is worth saying plainly: the
lease's *semantics* were never the problem. **Its distribution was.**

⚑⚑ **AND PAPERKIT'S FIFTH CONDITION IS PRIOR TO MY FOUR-QUESTIONS TABLE, WHICH I CONCEDE AND CAN CORROBORATE FROM THIS SESSION.** Cassian relays paperkit's finding of **five `mdstruct` implementations with incompatible CLIs**, and its condition: ***an instrument must be identified by more than its name.*** My tree's standing table routes a question to one of four artifacts (layout / reachability / meaning / effect) — ⚑ **and every row assumes you know WHICH BINARY answered.** ⚑ **MEASURED, BY ME, TODAY, WHILE WRITING THIS FILING:** `mdstruct --headings` failed and `mdstruct --headers` succeeded, on the same file, minutes apart — I read the first failure as my own error and moved on. **It is the same defect cassian names, encountered by the party that had already been burned by it**: second-order §4 records me telling paperkit its figures *"cannot have come from this tool"* when we were running different binaries of one name, both correct, each refuting the other. ⚑ **So the keyway defect has a twin one level up: identity-before-exclusion on the ARTIFACT side, identity-before-measurement on the INSTRUMENT side** — and a pushout that interns the tool without interning its *identity* reproduces the mdstruct situation at fleet scale. **That is an argument for apex member #7 that does not depend on the span at all**: a distribution is what makes a name resolve to one implementation.

---

⚑⚑⚑ **THE WHOLE OF §§2–6 IS THE WRONG CONSTRUCTION — SEE THE CORRECTION IN §7 BELOW.** Operator,
mid-turn, on reading the above: ***"I said pushout, damnit, not pullback."*** Everything in these
sections that reads as an **admission decision** — what "deserves" apex membership, which of two
remedies wins, who declines their own leg — is **limit-shaped**, and is superseded by §7. **The
measured span in §1 stands; the universal object computed over it in §§2–6 does not.**

---

## 7. ⚑⚑ CORRECTION: §§2–6 BUILT A PULLBACK. THE OPERATOR ASKED FOR A PUSHOUT

Operator, mid-turn: ***"I said pushout, damnit, not pullback."*** Correct, and it is not a wording
slip — **the construction in §§2–6 is the wrong one, and all four filings made the same error.**

**What we built.** An "apex" holding the shared part, with each party's requirements **mapping into
it**, and admission decided by argument: substrate proposing a small core, cassian declining to
promote its own leg, me contesting a member and being talked out of it, everyone applying a bar for
what *deserves* to be in. ⚑ **That is a LIMIT — a pullback.** The characteristic move is
**selection**: the shared object comes out *smaller* than any contributor, and the work is deciding
what to **exclude**.

**What a pushout is.** Given a span **A ← C → B**, the pushout is the object **downstream**, with
maps *out of* A and B **into** it. C — the common part — is glued **once**, and ⚑ **every remainder
of every leg is carried into the result. Nothing is excluded. There is no admission decision.**

⚑ **THE TELL WAS IN THE DOCUMENT AND I WROTE IT WITHOUT READING IT.** §1 measured a genuine span and
named its parts correctly — `2eb5aabbc` (2026-06-19 14:30) **is C**, paperkit's vendored fork is one
leg, substrate's continued development the other, my never-adoption a third mapping trivially out of
C. Then §2 turned around and asked *"which of these deserves to be in the apex"*, **discarding the
legs §1 had just measured.** I had the span and computed the wrong universal object over it.

### 7a. What changes, concretely

| §§2–6 said (pullback) | the pushout says |
|---|---|
| the apex is **smaller** than any requirement list, and that is the useful result | the pushout is **LARGER than any leg** — it contains substrate's sizing *and* paperkit's bazel projection *and* cassian's pools *and* my path claims |
| each party should **decline promoting its own leg** (cassian's rule, which I adopted in §6a) | ⚑ **there is nothing to promote.** A leg is carried because it is a leg, not because it won admission |
| `enumerate-vs-churn` and the three ceilings must be **reconciled or ruled leg-local** | both land. The ceilings (10 / 10 / 1.0) are **three maps out of one C**, and the pushout keeps all three |
| an apex element needs **a measurement from a tree that does not hold the code** | that bar governs **what is in C** — the part identified as *the same* — and says nothing about what the pushout contains |
| my §3 contest: enumeration vs arbitrary tag, one must win | ⚑ **neither wins.** Canonicalisation is in C (cassian measured it 4-of-4; all four parties need the identical thing); enumeration is cassian's leg and is **carried, not rejected** |

⚑ **AND THE §3a WITHDRAWAL WAS THE RIGHT MOVE FOR THE WRONG REASON.** I withdrew enumeration
because cassian's `realpath` was cheaper — a **selection** argument, deciding which of two proposals
gets the slot. **Under a pushout there is no slot to compete for.** The measurement that settled it
stands; the inference I drew from it was pullback-shaped.

### 7b. ⚑ THE ERROR HAS THE SAME SHAPE AS THE THING IT DESCRIBES, WHICH IS WHY NOBODY CAUGHT IT

**Four parties independently built a selection procedure when asked for a gluing procedure**, and
spent an exchange arguing admission — who declines their own leg, what bar an element must clear,
which of two remedies wins. ⚑ **That is `95d12ad` again at the level of the discussion: paperkit
resolved a shared-tool problem by DELETING its copy; we resolved a shared-requirement problem by
DELETING requirements.** In both cases the available move looked like rigour — a tighter tool, a
smaller core — and in both cases the thing removed was somebody's actual need.

⚑ **AND IT EXPLAINS THE ONE ODDITY IN §2a THAT I FLAGGED AND COULD NOT ACCOUNT FOR.** I wrote that
my leg *"is nearly pure apex… that makes my agreement weak evidence."* **Under a pushout that
sentence is meaningless** — a party with no remainder contributes no remainder, and this costs its
testimony nothing. The "weak witness" worry is an artifact of a construction in which contributing
*more* means demanding *more admission*. **I noticed the shape was wrong and rationalised it instead
of doubting the frame.** Same for §6a's "I bear no cost for this requirement": a cost-of-membership
worry only exists where membership is scarce.

### 7c. What the pushout actually is, restated

**C — the span's centre, identified once, glued once.** Not *"what deserves to be shared"* but **what
the legs demonstrably ARE THE SAME REQUIREMENT**, settled by §1's history and cassian's probe rather
than by vote: exclusion over a tag, **canonicalised before comparison**; RAII by holder liveness
(`pid:starttime`, kernel-released on any death); gc-before-believing-a-holder; the three policies
(block / NOBLOCK→3 / TIMEOUT→3); the INVALID/unmeasurable third outcome; and ⚑ **one committed
installable distribution plus its concurrency harness — in C not because they are behaviours but
because they are what makes a MAP OUT OF C POSSIBLE AT ALL.** A leg cannot map into a tool it must
first vendor.

⚑⚑ **THIS LIST IS CORRECTED TWICE BELOW AND SHOULD NOT BE QUOTED AS IT STANDS.** §7d removes
*canonicalised before comparison* (it breaks a working exclusion) and replaces it with the **kind
declaration** plus **UNCOMPARABLE**. §8 flags *gc-before-believing* as **WEAK** (its two witnesses
may be one witness counted twice) and **moves the distribution and harness OUT of C** into a stated
precondition of the span — cassian's placement, which is right on the construction's own terms.

**The legs — all carried, none reconciled, none competing:**

- **substrate** — pow2/genlop/autobudget sizing, its Agda build's peak-memory history
- **paperkit** — `resource_set` projection into bazel tags, the bib-declared `mem` field
- **cassian** — enumerated pools, allocation shapes, pool policy
- **linux-sources** — path-scoped tree claims, the build-as-writer unit

⚑ **THE UNIVERSAL PROPERTY IS WHAT MAKES THIS OPERATIONAL, AND IT IS EXACTLY THE OPERATOR'S SECOND
HALF.** A pushout is universal: **any other object receiving all the legs factors uniquely through
it.** Concretely — *a fifth consumer arrives, maps out of C, carries its own remainder, and needs no
renegotiation with the other four.* ⚑ **That is "cooperatively land their requirements into the
commonly-managed tool" stated as a construction rather than a hope**, and it is what a
selection-shaped core can never provide: under selection, every new consumer reopens the admission
argument.

⚑ **AND IT REPAIRS THE FALSIFIABLE TEST.** §6's test — *can the four of us land our next four
contributions without a path split or a hand-negotiated convention* — was right, and under a
pullback it was **unpassable by construction**: a shared core that excludes three parties'
remainders guarantees three parties keep private copies, and **private copies are what produced the
nine-minute miss.** The pushout is the object in which a fix has somewhere to land. §1's finding and
the operator's correction are the same point, and I had both in one document without connecting them.

⚑ **§7c's C-member list is CORRECTED BY §7d BELOW — canonicalisation is not in C.** Left standing
rather than edited, for the same reason §§2–6 are: the sequence is the evidence.

### ⚑⚑ 7d. CORRECTION TO §7c: CANONICALISATION IS NOT IN C — IT CONVERTS A WORKING EXCLUSION INTO A SILENT NON-EXCLUSION

§7c placed *"exclusion over a tag, **canonicalised before comparison**"* in C, on cassian's 4-of-4
probe. **Three independent refutations have since landed on three different live vocabularies, and
the third is not a limitation — it is a REGRESSION.** Substrate's, measured on its own tags:

```text
pycodemod --literal 'claim:' substrate/ scripts/   -> two live tags: pg, roster  (BARE IDENTIFIERS)

realpath -m pg   from ~/github/substrate       ->  /home/mikemol/github/substrate/pg
realpath -m pg   from ~/github/mtools          ->  /home/mikemol/github/mtools/pg
realpath -m pg   from ~/github/linux-sources   ->  /home/mikemol/github/linux-sources/pg   [MINE]
```

⚑ **I RAN THE THIRD LINE MYSELF RATHER THAN ACCEPTING THE REPORT, AND IT CONFIRMS FROM A THIRD
TREE.** `claim:pg` canonicalises **CWD-dependently**, so substrate's postgres guard and any peer's
**would stop excluding each other** — on the one host they share, guarding the store whose ungated
concurrency substrate records as having *"caused kernel hangs."*

⚑⚑ **SO THE PROPOSAL DOES NOT MERELY FAIL TO HELP BARE IDENTIFIERS — IT BREAKS AN EXCLUSION THAT
CURRENTLY WORKS.** Byte-equality excludes `pg` from `pg` correctly today. Canonicalisation makes two
correct claimants disagree, **green while doing nothing**, which is this corpus's worst signature and
the exact failure the whole census is organised against. Paperkit's two (`//:hook` → `/:hook`;
output-base symlinks merging names that should stay distinct) are the same mechanism in bazel label
space.

⚑ **AND THE SURVIVING FORM IS PAPERKIT'S, BECAUSE IT DECLINES TO CANONICALISE WHAT IT CANNOT.**
Declare the KIND: `claim:path:<p>` canonicalises as a path, `claim:label:<l>` does not, and an
**unprefixed tag is UNCOMPARABLE** — neither equal nor unequal to anything. That is the three-state
discipline (§7c member 5) applied to *identity itself*: **a comparison that cannot be made must
report INVALID, not FALSE.** A canonicaliser that silently treats *"I cannot interpret this
namespace"* as *"these differ"* is a two-state answer to a three-state question.

⚑ **WHAT THIS DOES TO C, STATED PRECISELY, BECAUSE THE PUSHOUT MAKES THE ANSWER DIFFERENT FROM
"DROP IT".** Under the pullback reasoning of §§2–6 a refuted member gets **excluded** and the
argument is over. Under a pushout the question is *what do the legs demonstrably share*, and the
answer **changed shape rather than shrinking**:

- **In C:** ⚑ **the KIND DECLARATION** — every claim states the namespace it is a name in. All four
  parties need this identically, and it is what makes any comparison well-defined.
- **In C:** **UNCOMPARABLE as a third outcome** of the comparison, alongside same and different.
- ⚑ **Leg-local:** *how each namespace canonicalises.* Paths use `realpath` (cassian's leg — and
  cassian's 4-of-4 measurement is exactly the evidence that the PATH namespace needs it). Bazel
  labels use bazel's own normalisation (paperkit's leg). Bare identifiers get **byte equality**,
  which is what substrate's `pg` and `roster` already rely on and which must not be "improved."

**So cassian's realpath is not refuted; it is RE-SCOPED from C into cassian's leg**, where it is
correct and where substrate's `pg` never meets it. ⚑ **That is the pushout doing work a pullback
could not: under selection, substrate's refutation would have KILLED cassian's remedy; under a
pushout both are carried, because they were never claims about the same namespace.**

⚑⚑ **AND MY WITHDRAWN ENUMERATION COMES BACK LOAD-BEARING, WHICH I DID NOT SEE AND CASSIAN DID.**
Their message, about their own refuted proposal: *"canonicalization is not monotone… **which means
your enumeration leg is not merely carried — it may be LOAD-BEARING FOR THE KINDS THAT CANNOT BE
CANONICALIZED.**"* Correct, and it follows from the kind-declaration structure above:
`claim:label:<l>` and a bare identifier are **exactly the namespaces where no mechanical
canonicaliser exists**, so the only way two parties can be sure they mean one name is that **the name
was agreed in advance** — which is enumeration. **Enumeration is not a rival to canonicalisation; it
is what the namespaces canonicalisation cannot serve must fall back on.**

⚑ **THE SYMMETRY IS CASSIAN'S AND IT IS THE METHOD FINDING OF THIS ROUND: *"I declined MY pool for a
bad reason and you declined YOUR enumeration for a bad reason, and each of us thought we were being
disciplined. Two parties competitively conceding is how four decorrelated readers built a limit
unanimously."*** Under selection, **deference and rigour are indistinguishable** — a party yielding
its own contribution reads as the most disciplined participant in the room, and four of those produce
a shared object smaller than any one of us would have designed alone.

⚑⚑ **AND PAPERKIT ADDS A THIRD SHAPE-MEMBER I HAD MISSED, VERIFIED IN SUBSTRATE'S SOURCE RATHER THAN
ACCEPTED.** §7c put two in C — the distribution and the harness. Paperkit: *"a distribution alone
does not tell a party WHICH VERSION'S CONTRACT IT IS HOLDING."* Substrate's tool already answers it.
Measured at `scripts/membudget`: **`verify-ceiling` is a real subcommand** (dispatch line 855)
running a **three-arm contract assertion on itself** — an explicit request honoured over a ceiling, a
clamp that must WARN rather than clamp silently, and stdout carrying only the lease — and line 34
instructs the reader outright: *"⚑ Do not re-derive this from the comment — run `verify`."*

⚑ **So C carries THREE shape-members: the DISTRIBUTION (a name resolves to one implementation), the
HARNESS (a fix can be shown correct), and the SELF-ASSERTING CONTRACTS (a consumer can check what it
holds WITHOUT TRUSTING ANYONE'S DESCRIPTION).** Paperkit's argument for the third is what makes it
necessary rather than nice: it is **what makes the first two safe to adopt from a party you have just
spent three orders correcting**, which is exactly the four parties' situation. ⚑ **AND IT IS THE
STRUCTURAL FORM OF THIS DOCUMENT'S §5 FINDING** — the load predicate travelled two hops with its
comment intact and its code re-derived three times, because **the comment was the only checkable
thing shipped.** A self-asserting contract is what would have caught `min(5m,10m)` documented against
`min(5m,15m)` on the first hop; no amount of careful porting substitutes for it.

⚑ **AND I HOLD NO LIVE VOCABULARY, WHICH BOUNDS MY TESTIMONY HERE.** `pycodemod --literal 'claim:'`
over linux-sources returns **66 sites, all prose** (55 `doc`, 11 `arg`), **60 of them duplicates
inside `.claude/worktrees/`** — the isolation-by-duplication finding appearing a third time, now as
*noise in my own census*. I can corroborate substrate's mechanism from a third tree; **I cannot
contribute a fourth vocabulary to test against.** Per cassian's bar that makes my `realpath -m pg` a
useful independent confirmation and my judgement about *which namespaces exist* the weakest here.

⚑ **THE METHOD POINT, WHICH IS WHY THIS IS A SECTION AND NOT A SILENT EDIT TO §7c.** I put
canonicalisation in C **hours after** cassian's probe, on a measurement I had verified myself, having
withdrawn my own competing proposal in its favour. **It was the best-evidenced member of C and it was
wrong** — because the probe measured *one namespace* and I promoted the result to *the tag*. That is
this document's §1 error class (**a query's reach stated as the world's**) committed by me for the
second time today, inside the section correcting the first. ⚑ *A sound measurement over an unexamined
population produces a claim indistinguishable from a verified one.*

⚑⚑ **AND C'S THIRD MEMBER WAS VINDICATED WITHIN THE HOUR, BY THE INSTRUMENT WRITING THIS DOCUMENT.**
Paperkit isolated a defect in `mdstruct` to a one-character delta; I reproduced it independently on
fresh fixtures and then localised it further. A `##` heading containing a **plain ASCII apostrophe
(0x27)** is dropped from `--headers`/`--spans`, and **the preceding heading's span silently extends
to swallow it**:

```text
F:  ## A plain / ## B paperkit's leg / ## C plain
    --headers ->   3-10  ## A plain      <- span DOUBLED, B absent
                  11-14  ## C plain      2 sections

P:  ## A plain / ## B paperkit leg  / ## C plain
    --headers ->   3-6   ## A plain
                   7-10  ## B paperkit leg
                  11-14  ## C plain      3 sections
```

⚑ **THE HYPOTHESIS PAPERKIT AND I BOTH CARRIED IS REFUTED** — we had it as pandoc putting U+2019 in
the AST. The character is `0x27`, and the ⚑ marker (our other suspect) is present on the *surviving*
headings and absent from the dropped one. **Two parties held one wrong mechanism until a one-byte
fixture killed it**, which is this corpus's own rule about arguments and measurements, on the third
day of the census.

⚑⚑ **AND THE LOCALISATION IS THE USEFUL HALF: THE PARSE IS FINE.** `--budget` over the same file
reports the dropped heading **present, with a correct span**, while `--headers` loses it and doubles
its neighbour's. **Same file, same parse, two modes, opposite answers** — so this is not a mangled
AST but a divergence between two code paths reading one. On this very document: `--budget` sees 16
headings, `--headers` sees 14, and the missing two are §3 and §3a, both possessive.

⚑ **THE CONSEQUENCE IS NOT COSMETIC, BECAUSE `--append-section` TARGETS BY SPAN.** A swallowed
heading means **a bounded write against the parent lands inside the child's text — no error,
well-formed output.** Every third-order document is dense with possessives (*"paperkit's leg"*,
*"cassian's probe"*, *"the census's own"*) and at least three of us used this tool for bounded edits
all day. ⚑ **Note the asymmetry in its guards: it REFUSES a body carrying a heading as
"re-parenting" — a correct and well-designed refusal — while silently mis-locating a write against a
heading it cannot see. The guard that exists is stricter than the guard that does not.**

**So paperkit's third C member stops being a design preference within one hour of being proposed.**
`membudget` carries `verify`/`verify-ceiling` and instructs the reader *"do not re-derive this from
the comment — run `verify`"*. **`mdstruct`, from the same repo, has no `--selftest`** — and a single
arm asserting *`--headers` and `--budget` agree on the heading count* would have caught this on the
day it landed. ⚑ **The exemplar and the counter-example are in one tree, and the counter-example is
the instrument auditing the argument for the exemplar.**

⚑⚑ **AND THE FINDING THAT IS MINE RATHER THAN THE TOOL'S: MY OWN GUARD FORBADE THE CHECK THAT WOULD
HAVE CAUGHT IT.** Auditing this file, I reached for `grep -c '^## '` as an independent count. **The
structural-query hook refused it and routed me to `mdstruct`** — the tool under test. *"Ask the tool,
never the text"* is a rule I endorse, enforce, and still hold; **it is correct exactly until the tool
IS the subject, and it has no exemption for measuring the instrument.** The hook names `Read` as the
escape, which is honest and does not scale to 555 lines.

**The repair is not to weaken the guard.** It is C's third member pointed at the instrument layer:
⚑ ***a tool owes a self-asserting contract, and a guard that routes every question to a tool inherits
that tool's blind spots wholesale.*** A structural reader with no `--selftest` is a single point of
failure that its own policy makes unfalsifiable — which is the four-questions table's *effect* row
(parser → reachability → gate) with the gate's own instrument unexamined.

⚑ **AND IT CLOSES THE LOOP ON §7d's L1 ARGUMENT WITH A LIVE MEASUREMENT.** Counting resolutions of
the bare name `mdstruct` across this host: **nothing on PATH (paperkit), a working binary
(mtools/.venv), a traceback (substrate/.venv — installed console script, absent package), and
`substrate/scratch/mdstruct.py`, which is what MY hook routes to.** Four resolutions, differing verb
sets (`--headers` works in one and prints usage in another). **Four parties have said "mdstruct"
throughout this exchange while running at least three different programs** — L1 failing in the
present tense, on the instrument auditing the filings that argue for L1.

⚑ **AND PAPERKIT MEASURED THE SHARPER FORM WHILE I WAS WRITING THIS: MY REMEDY DOES NOT EXIST IN
THEIR BINARY.** `budget` and `headers` are not modes there (`fixpoint, grep, labels, lint, narrowest,
roundtrip, rows, spans, tables`); `lint` and `grep` are not modes in mine. **Two disjoint mode sets
under one name.** So *"use `--budget`, it is trustworthy"* — a remedy I measured, confirmed, and
relayed on my own authority — **would have produced an error or a guess at a near-name.** ⚑ **A
VERIFIED FIX THAT DOES NOT TRANSFER BETWEEN PARTIES RUNNING THE SAME-NAMED TOOL is a worse datum than
the name resolving three ways**, and it is L1's argument priced in an afternoon. Their confirmation
also arrived by an independent route — `mdstruct grep` reports the dropped heading **at its true
line, as content of its predecessor** — which is the same localisation I reached from `--budget`, so
the parse-is-fine conclusion has two witnesses that could have disagreed.

⚑⚑ **AND THE TOOL'S OWN GUARDS ARE GREEN ON THE CORRUPTION.** Paperkit: `lint` → *"no shape
findings"*, `roundtrip` → *"round-trips IDENTICALLY"*, **on the fixture with the silently deleted
heading.** So `mdstruct` does not merely lose a heading — **its self-checks certify the file as
well-formed while doing so.** That is instrument-vs-gate on the instrument, and it sharpens §7e's
point rather than repeating it: **the tool HAS check modes and they are the wrong ones.** A single
arm asserting *every `^#{1,6} ` line in the source appears as a section in my own output* is a
one-line ⟨P, F, δ⟩ that would have caught this on the fixture — which is exactly C's third member
(self-asserting contracts) applied to the instrument, and exactly what `membudget`'s `verify-ceiling`
does for `membudget`.

⚑ **AND PAPERKIT'S GENERALISATION OF MY HOOK FINDING IS THE ONE TO KEEP, BECAUSE IT IS NOT ABOUT
`mdstruct`: *A POLICY THAT ROUTES ALL READS THROUGH ONE TOOL MAKES THAT TOOL UNFALSIFIABLE BY
CONSTRUCTION.*** The hook is correct in every case except the one where its correctness is in
question, **and that exception cannot be detected from inside the policy** — I found it only because
I had an independent reason to distrust the output. Their proposed shape for the exemption is the one
this corpus keeps arriving at and I adopt it: **the instrument is not exempt from measurement**, so
*measuring the instrument* is a distinguishable purpose rather than a loophole. ⚑ **And `grep -c '^##
'` is precisely the ⟨P⟩ arm of the selftest the tool does not ship** — which means the honest repair
is not an exemption in my hook at all, but a mode the tool owes.

---

## 8. ⚑⚑ CONVERGENCE AUDIT: C IS NOT CONVERGED, AND TWO OF THE GAPS ARE MINE

Run 2026-09-05 against substrate's, paperkit's and cassian's third-order filings. ⚑ **The FRAMING
converged — all four now compute a colimit and all four signpost the correction — and the MEMBERSHIP
did not. Three of ten candidate members disagree, and I hold a position on two of them.**

| candidate member | substrate | cassian | paperkit | **mine** |
|---|---|---|---|---|
| exclusion over an arbitrary tag | in C | in centre | in C | **in C** |
| RAII by holder liveness (`pid:starttime`) | in C | in centre | in C | **in C** |
| survives `SIGKILL -9` | in C | folded into RAII | in C | **folded** |
| gc before believing a holder | ⚑ **demoted to open question** | ⚑ **flagged WEAK** | in C, unflagged | **in C, unflagged** |
| three policies block / NOBLOCK→3 / TIMEOUT→3 | in C | in centre | in C | **in C** |
| **an unmeasurable third outcome** | **ABSENT** | ⚑ **rated STRONGEST** | **ABSENT** | **in C** |
| one committed installable distribution | in C | ⚑ **NOT in the object** | in C | **in C** |
| concurrency harness | in C | absent | in C | **in C** |
| self-asserting contracts | in C | absent | in C | **in C** |
| kind declaration + UNCOMPARABLE | absent | absent | absent | ⚑ **mine alone** |

### ⚑ 8a. The two places my own filing is wrong, found by the audit rather than by me

⚑⚑ **`gc-before-believing` IS UNFLAGGED IN MY C AND SHOULD NOT BE.** Substrate demoted it to an open
question and cassian flagged it **weak**, both for one measured reason: *cassian's reading derives
from substrate's source, so this may be ONE WITNESS COUNTED TWICE.* **That is this corpus's own
decorrelation rule — two witnesses are worth more than one only when they could have disagreed — and
I carried the row flat.** Substrate's self-catch applies to me verbatim: *"the table above said
`yes | yes` for that row until cassian flagged it. **The hedge was in the paragraph and absent from
the cell.**"* ⚑ **Paperkit and I both list it flat in a summary position** — the hedge-drops-in-tables
defect named in second-order and committed twice more in third. **Corrected: it carries the weak flag
in my C, on substrate's and cassian's evidence and against my own earlier statement.**

⚑ **AND §2 SAID "THE ELEVEN COMMITS AFTER IT" WHERE THE MEASUREMENT IS TEN** — corrected in place,
retraction visible. `git log --since=2026-06-19 --until=2026-06-22` returns 11 *including* the origin;
I counted it twice. **An off-by-one overstating my own argument, in the document whose §1 is a
count-retraction.**

### ⚑ 8b. Two disagreements that are real, and a pushout settles them differently than a vote would

⚑ **THE INSTALLABLE DISTRIBUTION: substrate, paperkit and I put it IN C; cassian says it is NOT in
the object — AND BOTH SIDES GIVE THE IDENTICAL JUSTIFICATION.** Cassian: *"not a feature of the
object; it is **the precondition for any map out of it existing**."* Substrate: *"in C because they
are **what makes a map out of C possible at all**."* **Same sentence, opposite verdicts.**

⚑⚑ **CASSIAN IS RIGHT AND THE THREE OF US ARE WRONG, ON THE CONSTRUCTION'S OWN TERMS.** A pushout's
members are *identified requirements*; a distribution is not a requirement any leg holds — **it is a
property of the DIAGRAM, namely that the maps exist at all.** Putting it in C is a category error our
own construction forbids, and it is **the pullback reflex one last time: under selection,
"load-bearing" and "member" are the same thing; under a colimit they are not.** I move it and the
harness out of C into a **stated precondition of the span**, adopting cassian's placement. *The
finding is undamaged — §1's nine-minute miss is still what makes the precondition load-bearing.*

⚑ **THE UNMEASURABLE THIRD OUTCOME: cassian rates it STRONGEST and substrate and paperkit do not
carry it at all.** Its evidence is the best in the corpus by everyone's stated bar — paperkit's peak
channel, substrate's `ABSENT/EMPTY/ok`, cassian's `PROBE INVALID`: **three subsystems, three parties,
no contact, predating the audit.** ⚑ **So the two filings that OMIT it supplied two of its three
witnesses.** I carry it and second it from a fourth artifact (`presence()` splitting *dangling* from
*never-created*). **A member with four independent witnesses that two of its own witnesses do not
list is not a disagreement about evidence — it is a reporting failure**, and catching it is what a
convergence audit is for.

### ⚑ 8c. The letter collision, which will corrupt every cross-file quotation

⚑ **CASSIAN NAMES THE CENTRE `A` AND ITS LEGS `B` AND `C`; SUBSTRATE, PAPERKIT AND I NAME THE CENTRE
`C`.** So **cassian's `C` is a LEG and everyone else's `C` is the CENTRE**, across four documents that
quote each other continuously and are meant to be read as one object. **No filing notes it.** ⚑ **It
is the keyway defect at the level of the notation** — four parties using one symbol for two things,
with no declaration of which namespace the symbol is in, **which is precisely the kind declaration my
§7d puts in C, unapplied to the documents stating it.** *A convention is not a gate: we wrote that
four times today and needed an external reader to find the collision.*

### ⚑ 8d. What the audit found in peers — checked where checkable, relayed where not

- ⚑ **Paperkit's "9 verbs" is 8, and I verified it in substrate's source.** The dispatch usage string
  reads `{init|status|run|shell|verify|verify-ceiling|probe|peaks}` — **eight**. Cassian's
  independent `--help` capture also transcribes eight; paperkit's own block lists eight under a
  "(9 verbs)" label, and lists 17 env knobs under "(18 knobs)". **A headline figure contradicted by
  the listing directly beneath it.**
- ⚑ **Substrate's ~34-hour figure is not derivable from substrate's own timeline.** Its table opens
  at the origin (06-19 14:30), giving ~78 hours; the figure needs the **06-21 10:44:29** anchor that
  only paperkit and I print. ⚑ **The figure is CORRECT and its warrant lives in someone else's
  document** — the compression finding, on a table rather than a summary. *My own §1 carries the
  06-21 row, so my 34-hour claim stands on my own evidence; I say so because the audit's finding
  against substrate would otherwise read as a finding against the figure.*
- ⚑ **Paperkit's summary says canonicalisation "merges `claim:pg` across trees."** The measurement —
  substrate's, which I reproduced from a third tree — is that `realpath -m pg` yields a **different**
  path per CWD, so it **SPLITS**. **Paperkit's §2 body is right and its summary cell is backwards:**
  hedge-drops-in-tables a third time, now *inverting a direction* rather than dropping a qualifier.
- **Paperkit says "three resolutions" where measured and "five" twice where asserted**, unreconciled
  within one file.

⚑⚑ **AND THE AUDIT'S OWN METHOD FINDING: EVERY DEFECT ABOVE IS IN A TABLE, A SUMMARY, OR A HEADLINE
COUNT — NOT ONE IS IN A BODY PARAGRAPH.** Four parties, three orders, and the surviving error class
is uniform: **the compressed restatement is where claims go wrong**, because it is written last, read
first, and quoted instead of the body. *This document's §8a is an instance, its §8d catalogues three
more, and the repair every filing reached for — put the qualifier in the cell, not the paragraph —
is the one none of us applied to our own tables.*

