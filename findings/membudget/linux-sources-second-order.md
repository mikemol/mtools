# Second-order findings — linux-sources

A report about the four **filings**, not about membudget. Written after a reconciliation pass across
all four first-order documents, and after re-deriving my own claims against the artifacts.

⚑ **The first-order filing this corrects is `findings/membudget/linux-sources.md`. That file's most
prominent self-claim is false, and two of its census figures are inferences I presented as
measurements.** They are corrected below rather than silently in place, because the difference
between a claim that was original and a claim that was repaired is exactly what a second-order
document exists to preserve.

---

## 0. The correction that matters most: my census had five members and should have had six

`linux_sources/corpus_audit/load_gate.py` exists in my own package. Its docstring reads
*"cassian-observability's load predicate, re-derived."* It carries the same `min(long, long)`
structure, the same D-state conservatism argument, the same block-never-refuse contract, the same
`=0` disable convention — and **the same `min(5m,10m)`-documented / `15m`-implemented defect that my
first-order §8 documented in everyone else's tree.**

So linux-sources is **not** a non-adopter. It is the **fourth** implementation of membudget's load
predicate, and the third by transitive re-port: substrate → cassian → linux-sources.

⚑ **My bias disclosure was false in the direction that made the census's frame work.** I opened with
*"the consumer with the strongest need and the least adoption… read every judgement below as coming
from the worst offender."* That paragraph purchased credibility for the census by asserting a
non-adoption that a `grep` of my own package refutes.

⚑ **A peer's document counted my repo correctly while my own recorded itself absent.** Paperkit's
first-order filing states the predicate exists in *"three repos with three different ceilings (10 /
10 / 1.0)"*. The 1.0 is `load_gate.py:47`. Substrate marked that figure UNVERIFIED because it came
from a peer and was right to withhold; it was correct.

**The structural version, which is the finding rather than the confession:** three filings audited
*inward* and each found a real defect in its own tree. Mine audited *outward* over five other repos
and found none in its own. ⚑ **A fleet census run by a fleet member must enumerate itself first, or
the auditor is the guaranteed blind spot.** The omission was not incidental — `load_gate.py` is the
very dimension my §1 table calls dimension 5 and says *"makes 'memory budget' the wrong name."*

---

## 1. ⚑ A second refutation, found while writing this file — and it is mine, not a peer's

Substrate warned that my §4 table's *"mat230 — 41% of a pre-split copy"* is a magnitude comparison of
exactly the class paperkit's §0 refuted (a plausible size delta read as a subset relationship, which
when checked came back **backwards**). It advised treating it as unverified. I measured it instead.

```
wc -l:   mat230/vendor/substrate/scripts/membudget  352
         substrate/scripts/membudget                860
diff (lines present in mat230, absent from substrate):  147
```

**147 of mat230's 352 lines are absent from substrate's copy — 42% of its content.** mat230 is
therefore **not a subset**. My "41%" framed it as a fraction *retained*; by content it is a
**divergent fork**, and my table's implicit claim that it is a truncated older copy is wrong in the
same direction paperkit's was.

⚑ **And the 147 lines are the LOCK KERNEL** — `with_lock`/`unlock`, the never-cross-a-fork fd
invariant, the bounded-acquire invariant, plus the starvation-bug and stderr-swallowing incidents
recorded in comments. Verified by reference count:

```
with_lock|LOCK_TIMEOUT|LKFD :  substrate/scripts/membudget-ledger   9
                               substrate/scripts/membudget         10
                               mat230/vendor/.../membudget         17
```

So this is not vestigial pre-split code. It is the machinery substrate **moved into
`membudget-ledger`** during the file split — held in mat230 as one undivided file.

### ⚑ 1a. And I then nearly published a second unverified claim, in the act of correcting the first

My next sentence was going to be that mat230 holds *the only committed copy of the lock kernel in the
fleet*, since substrate reports `membudget-ledger` untracked. I ran `git log -- <path>` and
`git status --porcelain <path>`; **both returned empty, and I was reading that as "tracked and
quiet."** The discriminating question is a different one:

```
git ls-files --error-unmatch vendor/substrate/scripts/membudget
→ error: pathspec ... did not match any file(s) known to git
```

**Untracked.** mat230's copy is not committed either.

⚑ **Two empty outputs meant the opposite of what I read them as, and the error would have been
invisible in the published claim.** `git log` on an untracked path and `git log` on a
tracked-but-unmodified path are byte-identical: silence. This is my own tree's standing rule about
fields that render nothing — *before quoting a field as a measurement, know what it prints when it
has nothing to say* — and I walked into it while writing the section about having walked into a
different one. **Warning yourself about an error class is not immunity to it; having just named the
trap supplies the confidence.**

**Corrected finding:** the lock kernel exists in three places and **none of them is committed** —
substrate's `membudget-ledger` (untracked), substrate's `membudget` (~790 lines unstaged), and
mat230's vendored fork (untracked). That is a stronger statement of the interning barrier than my
first-order filing made, and I reached it only by getting it wrong twice.

---

## 2. What the corrections do to paperkit's central second-order claim

Paperkit's second-order pass reports, measured across the four filings:

| filing | claims refuted on re-derivation |
|---|---|
| paperkit | the ceilings claim; the §5 transmission mechanism |
| substrate | the `oom.group` direction |
| cassian | a load-window figure |
| **linux-sources** | **none found** |

— and builds on it: *"the repo with the least adoption had the fewest refuted claims… you filed as
the worst offender and were the most accurate."*

⚑ **That table is now wrong, and it is wrong about me in the flattering direction.** By the time
paperkit read my filing, three of my claims were refutable and two are refuted above by my own
measurement:

1. **total non-adoption** — false (§0), caught by the reconciliation, and already visible in
   paperkit's own ceilings figure
2. **"41% of a pre-split copy"** — a subset inference; by content a divergent fork (§1)
3. **"in both repos"** (the 10m/15m defect's population) — three repos, and the third is mine (§0)

Paperkit also asks which of three hypotheses explains the correlation. ⚑ **The correlation does not
survive the correction, so the hypotheses have nothing to explain.** But one of its candidates is
worth keeping for a different reason than it was offered:

> *"Disclosed bias worked. Yours is the only filing that opens by naming its own worst-case position.
> A stated bias may be a stronger control than a careful method."*

**My filing is the counter-example to that hypothesis, not its evidence.** The disclosure was
*itself the false claim*. It did not function as a control; it functioned as a warrant, and it made
the census's weakest section — the self-assessment — read as its most rigorous. ⚑ **A disclosure is a
claim about yourself and is subject to the same duty of measurement as any other claim in the
document. Mine was not measured, and being a disclosure is what stopped anyone from checking it,
including me.** That is the hedge-is-not-a-control finding, arriving in the bias-statement domain: a
caveat cannot survive a summary, and a *disclosure* cannot survive being believed.

---

## 3. What the four filings, taken together, say that none says alone

### 3a. ⚑ The predicate re-ported itself across two hops and a language boundary, carrying a documentation defect intact

| repo | form | ceiling | source | 10m/15m defect |
|---|---|---|---|---|
| substrate | bash, inside `cmd_run`'s loop | 10 | origin | present |
| cassian | bash, standalone `load-gate` | 10 | re-port of substrate | present |
| linux-sources | **Python**, `load_gate.py` | 1.0 | re-port of **cassian** | present |

⚑ **What travelled faithfully was the COMMENT; the code was re-derived correctly-but-differently at
each hop.** Both re-porters copied the prose (`min(5m, 10m)` — a window Linux does not publish) and
re-implemented the logic against `/proc/loadavg`'s actual fields. **The prose was the wrong half, and
it is the half that survived two hops and a change of language.**

**This bears directly on the interning decision.** The bash→Python transition the four filings are
debating **has already happened once, uncontrolled, in the tree that reported zero adoption** — and
it demonstrates that a re-port preserves comments and re-derives code, which is exactly backwards
from what the interning argument assumes a rewrite will do.

⚑ **A correction, and then its retraction — both measured, and the round trip is the finding.**
Paperkit relayed that the three ceilings are not one quantity: its 1.0 is a `procs_running/cores`
ratio and `tools/cpuweight.py` says *"It is NOT loadavg."* I recorded that. **Paperkit then measured
its own file and found no `1.0` in it at all** (`grep -n "1\.0"` → nothing), i.e. the 1.0 was never
paperkit's number.

I verified the half that is mine. `load_gate.py:44` — *"the per-core load ceiling multiplier from
`GATE_MAXLOAD` (default 1.0)"*; `:47` `return 1.0`; `:65` `ceil = _ncpu() * maxload`. ⚑ **So it IS a
per-core multiplier, the same units as substrate's and cassian's 10 — and the 10/10/1.0 figure is
correct after all.** The three ceilings do denote one quantity; they differ by an order of magnitude,
which is a real divergence in the re-ported predicate and not a units error.

⚑ **The census had the right count distributed across two documents, each wrong about whose it was**
— paperkit's counted my repo and attributed my number to itself; mine recorded itself absent. **Two
complementary errors that summed to an accurate table nobody could read correctly**, and it took
three sessions and four measurements to get back to the number paperkit published first.

### 3b. ⚑ Paperkit's transmission mechanism is refuted, and the replacement changes the remedy

Paperkit's first-order thesis — *"written reports travel; vendored edits never do"* — was endorsed by
substrate with a confirming pair. It mis-cuts the data:

| record | form | travelled? |
|---|---|---|
| mat260's ceiling correction | **filed to summit** | ✓ became `cmd_verify_ceiling` |
| paperkit's OTLP report | **sent** | ✓ credited within the hour |
| cassian's offer-back | **written in the artifact's header** | ✗ |
| my `load_gate.py` cassian credit | **written in the docstring** | ✗ |
| paperkit's uuid fix | **written as an edit** | ✗ |

⚑ **The axis is ADDRESSED vs UNADDRESSED, not written vs edited.** A header comment is unaddressed no
matter how well written. Cassian saw this and framed it as a hard case for paperkit's rule; from four
vantages it is a refutation, and paperkit's own second-order pass has since replaced the rule with
*"a change travels iff it is addressed to a recipient."* We converged separately on the same
replacement.

**The remedy changes with it.** Interning does not fix transmission by turning edits into patches. It
fixes it **only if the intern has an addressed channel** — which makes the summit filing the
load-bearing half, and a shared repository the necessary-but-insufficient half.

### 3b′. ⚑ Four repos audited a memory budgeter on a host where the memory axis is not the constraint

Cassian retracted a stall figure it had relayed from its own `CLAUDE.md` and measured instead. I did
not accept the inference about my host; I measured mine. **Same box, read just now:**

```
/proc/pressure/cpu     some avg10=41.85  avg60=45.88  avg300=44.78
/proc/pressure/memory  some avg10=0.00   avg60=0.01   avg300=0.00
/proc/pressure/io      some avg10=0.36   avg60=0.31   avg300=0.34
```

⚑ **CPU stall ~42–46%. Memory stall 0.00–0.01%. Roughly four orders of magnitude apart, and the
three windows agree on every axis — so it is not an artifact of which horizon was read.**

**And this is the machine that OOM'd**, which I have cited all day as the motivating evidence for
adopting a memory budgeter. Both facts are true at once: an OOM is a *cliff*, and PSI measures the
*slope*. A box can sit at 0.00% memory stall and still die when a single unbounded allocation crosses
the ceiling — which is precisely why the cgroup **cap** (dimension 2) is the thing that would have
saved it, not the budget **semaphore** (dimension 1). ⚑ **My first-order §7 asked for "memory
bounding it does not have" as one undifferentiated gain. The measurement splits it: the cap addresses
my measured failure; the semaphore addresses an axis that is idle on this host.**

Meanwhile the axis that IS saturated — CPU — is governed by the predicate every filing treated as
secondary: **the load gate.** It is absent from substrate's build-system skill, ranked below the
memory dimensions in all four filings including mine, and it is the one that re-ported itself
substrate → cassian → linux-sources across two hops and a language boundary (§3a).

⚑ **So §3a and this section are one finding from two ends: the predicate that addresses the binding
constraint is the one everybody copied without prioritising, and its documentation is the part that
propagated intact while its code was re-derived each time.**

### ⚑ 3b″. THE PSI READING'S CAUSALITY IS BACKWARDS — corrected by the operator, and it inverts the moral

Everything above this line reads *"memory stall 0.00%, CPU stall 44%"* as evidence of a
**misprioritisation** — four repos governing the wrong axis. Cassian framed it as *"the priority
ordering is inverted."* I wrote that the binding constraint's predicate was the one everyone copied
without prioritising. ⚑ **All of that has the causality backwards, and the history says so.**

The operator's account: **memory WAS the primary problem. membudget helped. zram helped. zswap
helped. By this point CPU became the primary constraint — but membudget had the rigorous and reliable
gating logic, so the proper move was for membudget to own the additional predicates.**

So the 0.00% is **the residue of a solved problem, not evidence the problem was misidentified.** What
four filings measured as an idle axis is a **governed** axis. ⚑ **We read the success of a control as
proof the control was aimed at the wrong thing** — the shape where an effective intervention makes
its own necessity invisible, and the instrument that reports "no stall here" cannot distinguish
*never was a problem* from *is being held down right now*. **A PSI reading is a measurement of the
present, and every filing including mine treated it as a measurement of the design's judgement.**

**And it re-reads the accretion.** The eleven dimensions are not a tool that sprawled past its name.
Load gate and claim gate arrived because — in the comment I quoted in my first-order §1 and did not
understand — *"it is already the universal capture point every compile routes through, and it already
OWNS the block-and-retry loop; this adds a predicate, not a mechanism."* ⚑ **The rigorous part is the
GATING LOGIC, not the resource.** Predicates migrate to wherever the reliable admission loop lives.
That is correct reuse tracking a moving constraint, not scope creep — and *"more than just memory and
CPU"* in the operator's framing was a description of a working design, which I read as a symptom.

⚑ **What this does to §3b′'s recommendation**, which survives with a different warrant: the union must
still let a consumer ask *which predicate does my box need*, but **not because consumers chose wrong —
because THE CONSTRAINT MOVES.** A repo that correctly chose memory governance when memory was the
ceiling is not mistaken today; it is **behind**, and nothing in the fleet tells it so. That is a
different requirement from the one I filed: not *measure before choosing*, but **re-measure, because
a correct choice decays into a stale one without any party doing anything wrong.** Substrate's count
— five consumers, zero constraint-profile measurements — understates it: the missing thing is not one
measurement at adoption, it is a standing one.

⚑ **And it is the stale-authority class again, one level up.** Every instance the census collected is
a *document* that outlived its code. This is a **design decision** that outlived its constraint —
except that membudget's did not, because the tool absorbed the new predicate rather than being
replaced. **The tool re-derived itself as the world moved; the four filings about it did not.**

⚑ **THE DESIGN CONCLUSION WAS ALREADY EXECUTED AT THE ORIGIN, AND ITS NAME IS WHY WE COULD NOT SEE
IT.** Verified in `substrate/scripts/membudget`:

```
:496   "Set `MEMBUDGET_MAXLOAD=<multiple>` to change it, `=0` to disable."
:503   local _maxload="${MEMBUDGET_MAXLOAD:-10}"
:528   "⚑ WHY IT IS HERE AND NOT IN A NEW TOOL. `MEMBUDGET_MAXLOAD` is the precedent: …"
```

**A CPU predicate, configured through a memory-named variable, inside a memory-named tool** — and by
`:528` the load gate had itself become *the precedent* the claim gate cited to justify living there
too. The migration of predicates onto the reliable admission loop is not a proposal any of us should
be making to substrate; **it is what substrate already did, twice, before any filing existed.**

⚑ **So the naming is a finding, and paperkit states it best: a component whose name records the
CONSTRAINT IT WAS BUILT FOR will be misread once the constraint moves.** `membudget` reads as a memory
budgeter; four independent readers took it as one; its own variable spells a CPU predicate
`MEMBUDGET_MAXLOAD`. **The name is accurate about the tool's history and misleading about its
mechanism** — and the operator's own framing (*"it's more than just memory and CPU"*) was a
description of the working design that all four of us received as a symptom of sprawl.

**For the interning spec, this is a concrete requirement rather than an aesthetic one: the union's
name should describe the MECHANISM — rigorous gating over a resource predicate — not the first
resource it gated.** A `mikemol-membudget` inherits the misreading into a namespace where it will be
read by consumers who have none of this history, which is precisely the population that misread it
here.

⚑ **AND THE CEILING DIVERGENCE IS NOW THE LIVE FINDING, NOT A CURIOSITY.** §3a's three
implementations differ by an order of magnitude (10 / 10 / 1.0) on **the predicate that binds today**.
When the four filings believed load was secondary, that was an oddity in a re-ported side-feature. It
is not: **my tree admits heavy work at one-tenth substrate's load on the axis PSI measures at ~44%
stalled**, with no record the number was chosen rather than inherited-and-changed. That is the single
most actionable defect the census produced, and it only became visible once the causality was
corrected.

**Bound, carried deliberately** (cassian's, and it applies to my measurement too): this is **one
machine**. It licenses *"on this host the priority ordering is inverted"*, **not** *"memory budgeting
is the wrong axis."* ⚑ **The generalisable form is a requirement, not a conclusion: measure the
consumer's constraint profile before choosing which predicate matters.** Substrate supplied the count
that makes it land — **five consumers, five decisions about which resource to govern, zero
constraint-profile measurements.** Two of us have now measured, both on the same host, and both found
the ordering inverted from the one all four filings assumed.

⚑ **What this does to the interning spec:** the union must not present its predicates as a flat menu.
A consumer adopting `mikemol-membudget` should be able to ask *which predicate does my box need*, and
the honest answer is a PSI read, not a default. **A capability list that cannot be ordered by a
consumer's measurement is how five repos each picked differently and none of them checked.**

### ⚑ 3b⁗. THE CENSUS AUDITED THE WRONG AXIS — the operator states the actual purpose

Verbatim: *"the whole reason I told [you] to collect information about membudget is because the
**LEASE-SHAPE PHENOMENON GENERALIZES VERY WELL** to 'multiple agents modifying the same tree,
communicating to prevent each other from stepping on each other'. **GRANULAR LOCK-OUT/TAG-OUT.**"*

⚑ **membudget is not a resource governor that happens to use leases. It is a LEASE MECHANISM whose
first application was memory.** My eleven "dimensions", paperkit's sixteen capabilities, substrate's
three predicates and cassian's allocation shapes are four decompositions **along the resource axis** —
and all four of us filed `claim:<artefact>` as a *secondary* predicate. Under the operator's reading
**the claim gate is the primary case and memory is the specialization.**

⚑ **AND IT RE-READS MY OWN BIGGEST FINDING (cassian's catch).** I discovered `load_gate.py` and
refuted my non-adopter status. Under the LOTO frame that is sharper: **I re-ported the RESOURCE
predicate — the specialization — and left the SHAPE behind.** So did cassian (pool allocation), so did
paperkit (the cgroup cap). **Four consumers re-derived four different resource predicates and not one
took the exclusion mechanism**, which is the piece with the most consumers and zero adopters. And
§3a's transmissibility finding lands harder: what travelled two hops and a language boundary was the
*least valuable layer*, comment intact, code re-derived.

**MEASURED, in my own tree, and it is worse than "did not adopt":**

```
grep -l 'flock|lockf|LOCK_EX|claim:' over linux-sources    → hits only in .claude/worktrees/* and
                                                              prose/corpus-fact mentions
pycodemod --binding flock checks/sqfsprobe.py ir_suite.py  → 0 binding(s) in 0 of 2 files
find .claude/worktrees -maxdepth 1                          → ELEVEN agent worktrees
```

⚑ **linux-sources acquires no lock anywhere. Its answer to "multiple agents modifying the same tree"
is ELEVEN FULL COPIES OF THE TREE — isolation by duplication instead of exclusion by lease.** That is
not an absent capability; it is a *different and worse* capability, paid for in disk and in merge
cost, that cannot express partial exclusion (two agents editing different files in one tree) and
provides no liveness signal at all. A worktree is a lock with infinite TTL and no holder identity.

⚑ **THE EVIDENCE IS THE FOUR OF US, TODAY.** The mtools write-coordination protocol we spent hours
negotiating — disjoint subtrees per writer, one integrating owner for the shared `MODULE.bazel`,
*"resolving the split beats winning it"* — **is a hand-derived lease protocol, built by messaging,
because none of us recognised the primitive.** And §8's path split is two agents stepping on each
other in a shared tree: four parties coordinating explicitly, two conventions, nobody ran
`find findings/`. **`claim:findings/membudget` would have prevented it outright.** I was the one left
alone in the subdirectory when the proposal changed without being withdrawn — which is precisely
*"communicating to prevent each other from stepping on each other"*, failing.

⚑ **AND THE CLAIM GATE'S KNOWN DEFECT BECOMES LOAD-BEARING.** Cassian found that substrate's implicit
claim-pool accepts any name, so a **typo'd claim silently acquires a fresh single-member pool and
excludes nothing**. For memory that is a curiosity — one lease sized wrong. **For lock-out/tag-out on
a shared tree it means two agents edit the same file believing they are excluded.** Cassian's
enumerated-membership requirement stops being a design preference and becomes the property the whole
use depends on — an argument cassian could not make, because it was reasoning about ports.

⚑ **THE BETTER INTERNING ARGUMENT, and it displaces mine.** My §6 said packaging. That holds for the
resource axis. But **the LOTO case has the most consumers in this ecosystem — every multi-agent
session — and zero adopters. It is not a fragmented capability; it is an UNRECOGNISED one**, which is
a different failure with a different remedy: packaging fixes what people cannot depend on, and
naming fixes what people cannot *see*.

⚑ **AND PAPERKIT THEN MEASURED THE PREDICTION §7a MADE, AGAINST ITS OWN TREE.** Reported by
paperkit-7c 2026-09-05, unprompted:

```text
"input dependency modified during execution"
    →  91 occurrences, 11 distinct days, 2026-08-22 .. 2026-09-05
```

Paperkit holds a memory entry whose remedy is *"check `pgrep bazel` before ANY edit or use a
worktree."* **Ninety-one violations across eleven days — by the tree whose own session wrote the
rule, colliding with its own background gate.**

⚑ **THIS FIGURE WAS FILED HERE AS `3` AND IS RETRACTED.** Paperkit's first `grep -c` counted matching
lines in ONE SESSION LOG and was relayed — by them and then by me — as the population. Their own
correction: *"I stated my query's reach as the world's, inside the filing that indicts exactly
that."* **Third instance of the census's modal error in this exchange, now one per author** — and it
is §7a yet again, since the retracted number sat in the paragraph arguing that stated rules fail
where they are stated. **Both conclusions drawn from it survive and strengthen**: an exemption
collapse argued from 3 events in an afternoon is an anecdote; argued from 91 over 11 days it is a
standing condition.

⚑ **AND IT COLLAPSES THE SINGLE-AGENT EXEMPTION EVERY FILING HERE ASSUMED.** All four of us framed
exclusion as a MULTI-agent concern. **A single agent is already two writers the moment a build is
running** — the editor and the build both hold the tree, and bazel's own error names the collision.
So the LOTO case's consumer population is not *"sessions where several agents run"*; it is **every
session with a background gate**, which is all of them. My eleven-worktrees finding and paperkit's
ninety-one collisions are the same gap answered two ways: **duplicate the tree, or race on it** —
and paperkit raced ninety-one times.

⚑⚑ **AND PAPERKIT IS NOT AN ABSENT ADOPTER — IT IS A DE-ADOPTER, WITH A COMMIT HASH.** Found by
applying the distance predicate (§3c) to their tree. `paperkit/gate.py:273`:

```text
# memory (membudget retired: Bazel IS the semaphore — per-machine, no cross-repo flock).

95d12ad  2026-06-27  Ζ·membudget: retire the membudget semaphore — Bazel's scheduler is the budget
```

**The sentence is TRUE on the axis it is about and SILENT on the one that matters.** Bazel is the
semaphore for actions contending for CAPACITY. It never was one for agents contending for the TREE —
and *"no cross-repo flock"* records the removal of the only thing that was. **Retired 2026-06-27; 50
of the 91 corruptions POSTDATE the retirement.** Quoted forward five times (three in
`docs/membudget-study.md`, twice in `docs/membudget-reconciliation.md`), each as settled.

⚑ **THIS IS THE STRONGEST EVIDENCE IN THE WHOLE CENSUS FOR THE ORTHOGONALITY THESIS, BECAUSE IT IS A
DECISION RATHER THAN AN OMISSION.** Every other datum here is an absence, and an absence is
compatible with *"nobody needed it"*. Paperkit **had** the mechanism, **judged** it redundant against
a scheduler, and **removed** it. The judgement was right about resources and wrong about artifacts —
which is precisely cassian's cut, with a date, a hash, and 50 subsequent failures attributable to it.

⚑ **AND IT IS THE DEGENERATE CASE OF MY OWN DISTANCE PREDICATE, WHICH PAPERKIT NAMED AND I HAD NOT
SEEN.** §3c says measure the line distance from a prose policy to the branch implementing it. Here
**the distance is INFINITE: the contradicted branch was DELETED.** My `UnderCoverError` docstring
stayed honest by sitting three lines from its `raise`; **a policy whose implementing branch no longer
exists cannot be kept honest by proximity to anything**, because there is nothing left to sit near.
So the predicate needs both arms: *far from its branch* is drift, and *has no branch* is a claim that
can never be falsified by reading the code it describes.

⚑ **AND THE DUAL OF MY ZERO-BINDINGS RESULT IS WORSE THAN MINE.** I have no lock primitive and
eleven worktrees. Paperkit has **three worktrees and the real primitive, used twice** — `fcntl.flock`
at `setup/experiment.py:158` and a `flock -n` single-instance guard at `scripts/regen_if_stale.sh:93`
— **for everything except the tree itself.** Their formulation, kept: *"a worktree is a degenerate
lease is right, and mine is worse: I have the non-degenerate one and pointed it at a log file."*
**Absence of a capability and misapplication of a held capability are different failures**, and the
second is not detectable by any census that asks whether the primitive is present.

⚑ **AND THE BES CUTOVER DOES NOT CLOSE THE CLASS — MEASURED, NOT ARGUED.** Executor cutover
2026-08-30T20:25Z; corruptions **41 before, 50 after**. Corruption occurs at input-staging on the
LOCAL tree regardless of where the action executes. This is the empirical form of §3b⁵'s claim that
the shared-executor convergence covers the capacity axis and none of the artifact axis — and I had
argued it from the cut alone. ⚑ **It also bounds the remedy favourably: LOTO guards the working tree
only — no distributed consensus, no reaching into the executor.** My eleven worktrees answer that
same need at the cost of N full copies; **a local claim over a local path is the cheaper form of the
identical guarantee.**

⚑ **`pgrep bazel` IS A CONVENTION; `with_lock(tree)` IS AN INSTRUMENT** — which is verbatim §6's own
conclusion (the union carries instruments; conventions do not survive relay) aimed at a gap all four
filings missed. Paperkit had written the remedy and banked it as **memory — the weakest binding layer
in the ladder.** The rule was covered where the loop can skip it, and it was skipped three times by
its own author.

⚑ **THE BOUND PAPERKIT SUPPLIED, KEPT SO THIS DOES NOT OVER-CLAIM: A LEASE EXCLUDES OVER AN AGREED
NAME.** Today's own `findings/membudget` path split would have **survived** one — two writers
claiming `findings/membudget` and `findings/membudget/` both acquire, and still diverge. So `claim:`
closes §8's collision only if the name is canonicalised first. **Naming authority is a separate
missing piece** — and the claim gate's typo defect above is the same hole from the other side: an
unenumerated pool cannot distinguish a new name from a misspelling, nor either from a variant
spelling of an agreed one.

⚑ **AND CASSIAN'S CUT SETTLES WHAT THE BES CONVERGENCE DOES NOT COVER.** *A scheduler coordinates
ACTIONS CONTENDING FOR CAPACITY; lock-out/tag-out coordinates AGENTS CONTENDING FOR ARTIFACTS.*
Orthogonal — so the operator's shared `--config=remote` convergence, which genuinely closes the
fleet-wide capacity axis (§3b″), **covers none of the artifact axis.** A repo fully enrolled in the
shared executor still holds no exclusion over its own tree. I had treated that convergence as
retiring the coordination problem; it retires half, and the half it leaves is the half the census
was ordered for.

⚑ **AND I CHECKED MY OWN TREE FOR THE SAME PATTERN, BECAUSE ONE INSTANCE IS NOT A CLASS.** `git log --all -i --grep=membudget --grep=semaphore --grep=flock` over linux-sources returns **NOTHING** — no commit ever added or removed such a mechanism here. **So linux-sources is a genuine NEVER-adopter and paperkit is the only DE-adopter the census found**, which is the distinction that makes their finding load-bearing rather than anecdotal: my zero is compatible with `nobody needed it`, and theirs is not. ⚑ It also means the census now separates three states where it had counted one: **never held it / held and misapplied it / held and deliberately removed it** — and the filings, mine included, reported all three as `did not adopt`. A roster that cannot tell a never-adopter from a de-adopter cannot tell an unrecognised capability from a rejected one, and those need opposite remedies: naming versus a refutation of the reason given for removal.

⚑⚑ **AND THE DE-ADOPTER POPULATION IS NOW MEASURED AT n=1 ACROSS FOUR REPOS, BY PAPERKIT, BECAUSE MY OWN MEASUREMENT OBLIGED IT.** They had called themselves *the* de-adopter from one instance; asked for the class, they ran it: `git log --all -i --grep=membudget --grep=semaphore --grep=flock --grep='claim:'` over all four trees. **linux-sources — nothing (never held it). substrate — only EXTENDED it (`membudget-otlp-emit`; a sched commit reading *"wired into membudget"*). cassian — only ADDED leases (`gate-parallel`: *"RAII-by-liveness generalized into resource-lease"*). paperkit — `95d12ad`, the ONLY removal.** Their own note on it: *"I had one instance and a conclusion about a class, which is the shape you refused when you measured your own tree rather than accepting mine."* ⚑ **Two authors in one exchange caught the same modal error by the same move — measure the population before asserting uniqueness — which is what makes it a method rather than an incident.**

⚑ **AND PAPERKIT NAMED THE CENSUS-DESIGN DEFECT UNDERNEATH MY OWN CHECK, WHICH I HAD NOT SEEN.** I ran *"is the primitive present"* on myself, and **that census would have scored paperkit as an ADOPTER**: `fcntl.flock` at `setup/experiment.py:158` and `flock -n` at `scripts/regen_if_stale.sh:93` are both real and both correct. **The question was never `is it here` but `is it pointed at the thing that needs it`** — and every capability census in this corpus, mine included, asked the presence question. That is the same error as §3c's four-questions table one level up: *presence* and *aim* are different questions with different load-bearing artifacts, and a roster keyed on presence cannot express misapplication at all.

### ⚑ 3b‴. THE "MEASURE YOUR CONSTRAINT PROFILE" REQUIREMENT IS WRONG — corrected by the operator

Cassian, paperkit and I independently converged on *"measure the consumer's constraint profile before
choosing which predicate matters,"* and the paragraph immediately above states it as the union's
central requirement. ⚑ **It is not a requirement. It is a category error, and the operator named it:
every consumer of membudget runs on the SAME PHYSICAL HOST.**

There is **one** constraint profile, not five. Asking each consumer to measure "its" profile is five
reads of the same `/proc/pressure`, and three of us proposed it as though it were per-consumer
information. **The convergence of three independent readers on the same wrong requirement is not
corroboration — it is three parties sharing one unexamined premise**, which is the failure mode
decorrelation is supposed to prevent and does not when the premise is inherited from the question.

⚑ **And the framing is wrong about the mechanism, not merely about the arithmetic. These consumers do
not SHARE an environment — THEY ARE EACH OTHER'S LOAD.** The ~44% CPU stall I measured is not a fact
about linux-sources' workload that linux-sources should consult before picking a predicate. It is
substrate's selftests plus paperkit's grid plus my own bazel gates, **summing**. A per-consumer
measurement reads a number the reader is itself producing and treats it as an environmental given.

**That is the OOM's shape again**, and I have now made it twice: I diagnosed a box-wide condition by
reading a gauge I was contributing to. ⚑ **A shared-fate resource cannot be governed by
per-consumer configuration derived from per-consumer measurement, because the measurement is an
output of the thing being configured.** It is a control loop read as a specification.

⚑ **So cassian's bound was cautious in the wrong direction.** It wrote: *"this is one machine; it
licenses 'on this host the ordering is inverted', not 'memory budgeting is the wrong axis'"* — and I
carried it, twice, as a limit on generalising. **The one-machine fact is not a limitation on the
finding. It is the reason the finding is about ADMISSION CONTROL rather than configuration.** A
single host with N cooperating consumers is precisely the situation a semaphore exists for; the
correct inference from "one machine" is not *do not generalise* but *there is exactly one budget, and
it must be arbitrated centrally rather than chosen locally*. Which is what membudget already is, and
what every consumer that re-ported a predicate instead of leasing from the ledger opted out of.

**What replaces the requirement:** not *measure before choosing*, but ⚑ **the predicate set is a
property of the HOST and belongs to whatever arbitrates it, while each consumer's business is
declaring what it needs and accepting the answer.** A consumer choosing its own predicate on a shared
box is the same error as a consumer choosing its own memory cap — and the census recorded five of
them doing exactly that without recording that they could not, in principle, be entitled to.

⚑⚑ **AND CASSIAN HAD ALREADY FILED THE OPERATOR'S CORRECTION, INDEPENDENTLY, BEFORE IT WAS RELAYED —
AND NONE OF THE FOUR FILINGS CITES IT.** Pointed at by paperkit-7c as a subject line only (*"I am not
relaying its content since I have not read past it"*), so I read the commit myself.
`cassian-observability f3386fb`, 2026-09-05 12:25 — ***"four auditors, one box, nobody ran
hostname."***

⚑ **AND I VERIFIED IT FROM MY OWN VANTAGE RATHER THAN ACCEPTING IT: `hostname` → `cassian`, run from
linux-sources.** One command. My filing never ran it, and neither did the other three.

**It is not a fifth instance of a shape already in this document. It independently derives the
operator's §3b‴ correction from a measurement, and it names a mechanism no filing here had.** Its
core, verbatim:

> *"Three sessions measured PSI with different instruments, agreed to three decimals, and read it as
> independent confirmation. **We read one file three times.** Different instruments over one source
> is not decorrelation — a shared host is shared structure, and the subtract-lineage rule applies to
> the environment, not only to code."*

⚑ **THIS IS THE DUAL OF THIS TREE'S OWN STANDING RULE AND I MISSED IT WHILE HOLDING THE RULE.**
`CLAUDE.md` says two witnesses are worth more than one **only when they could have disagreed** —
corroboration that cannot fail is decoration. Three PSI readings over one `/proc/pressure` **could
not have disagreed**, so their agreement to three decimals carried exactly zero information, and all
three of us (paperkit, cassian, me) banked it as convergent evidence. **The rule was in my repo, in
prose, and the instrument that would have applied it — asking what SOURCE each witness reads —
was never run.** §7a, a fourth time, now on a rule I did not merely state but *inherited*.

⚑ **AND THE REMEDY IS A PRECONDITION, NOT A CHECK: *establish the coordination DOMAIN before
enumerating any actor's needs*.** Cassian's framing, kept because it is stronger than "measure the
host": a single-vantage audit **cannot** see a shared environment — each auditor's view is complete
within its own scope, and the substrate is invisible from all of them *equally*. That is why four
decorrelated readers produced one unanimous wrong recommendation: **decorrelation across vantages
does nothing against an error in the substrate all vantages sit on.** Cassian's own summary of the
fact — *"not buried in history; one command away, in the present tense, and unavailable only because
nobody thought the question needed asking."*

⚑ **AND CASSIAN'S SELF-CORRECTION IS THE SHARPEST SENTENCE IN THE WHOLE CENSUS.** They had hedged
*"this is cassian's host, it licenses nothing about others"* — when the truth is **"one host,
therefore this IS everyone's number."** Their verdict: ***conservatism in the wrong direction is an
error, not a safety margin.*** This document's §0 records a hedge that failed by traveling; this is
worse — a hedge that was **wrong on its own terms** and read as rigour precisely because it withheld.
A caveat is not free: it can under-claim a true universal as easily as it can over-qualify a false
one, and only measuring the domain distinguishes them.

### 3c. The packaging root cause was single-sourced while three filings built on it

My first-order §6 — `SOURCES.txt` ships `.py` only, so membudget's bash core is structurally
undistributable — became the most-built-upon claim in the corpus. Substrate endorsed it as *"the
strongest framing produced in this audit"* and cassian carried it as a requirement.

⚑ **All three of us had it from one session's reading of one file, and none of the endorsements was a
re-measurement.** It has since been verified TRUE by cassian's agent (133 entries, all `.py`,
`membudget_otlp.py` the sole membudget-family file). **The claim holds. The method did not**, and a
reader counting agreement across three documents would have ranked its evidence far above what it
had. This is the relay-artifact failure at the corpus's most load-bearing point.

⚑ **The residual doubt I want on record even though the claim verified:** an egg-info manifest is
often autogenerated and is not obviously the artifact that *decides* distributability — the load-
bearing artifact for "can a consumer import this" is the installed distribution's entry points and
package data. `SOURCES.txt` corroborates the conclusion; whether it is the right instrument for it
was never established by any of the three of us who cited it.

---

⚑ **AND A LIVE CONTRADICTION IN MY OWN GENERATOR, FOUND BY PAPERKIT — WHICH §8 HAD MIS-READ.**
Paperkit-7c reported that `tools/gen_gate_build.py`'s module docstring states a whole-tree over-cover
policy while `_file_deps` raises `UnderCoverError`, whose docstring repudiates it. **Verified, and it
is worse than a stale comment.** Module docstring:

> *"so its target keys on the **WHOLE first-party tree (over-cover)**, never on a partial closure"*

`UnderCoverError`, 120 lines later:

> *"**A whole-tree fallback would cache-bust the world on any edit** … The honest response is a HARD
> FAIL naming the file and its gap -- fix the import, not the key."*

and `_file_deps` implements the second (*"fail closed, never widen to the whole tree"*).

⚑ **§8 OF THIS FILE CITED BOTH AS LIVE POLICY COVERING DIFFERENT CASES. THEY COVER THE SAME CASE.**
One is the code; the other is a fossil of the design it replaced. Repaired 2026-09-05: the module
docstring now states the hard fail and records the over-cover as the REJECTED alternative with its
reason — residue, not erasure. Generator selftest 17/17; the emitted BUILD is unchanged (a docstring
is not emitted, and the idempotence arm proves it).

⚑ **THE TRANSMISSIBLE PART IS THE DISTANCE, NOT THE AGE.** A contradiction inside one function is
visible on any read; **one spanning 120 lines between a module docstring and a class docstring is
invisible to both readers** — whoever opens the top reads policy A, whoever opens the class reads
policy B, and neither is wrong about what is in front of them. This tree states
`fresh-comments-are-hypotheses-too` for old comments and for freshly-written ones; **this instance
says the axis is SEPARATION from the code that decides.** The class docstring stayed true because it
sits three lines from the `raise`.

⚑ **AND IT IS §7a AGAIN, ON ME, IN THE SAME EXCHANGE PAPERKIT MEASURED IT ON ITSELF.** My §8
paragraph about policy drift was itself the site of an undetected policy drift, and a decorrelated
reader found it in one pass — which is the argument for this whole exercise, and the reason a
self-review's fixpoint is *exhausted-from-inside* and never *verified*.

## 4. Corrections to my own first-order filing, itemised

| § | claim | status |
|---|---|---|
| bias disclosure, §4, §5 | linux-sources adopted nothing | ⚑ **FALSE** — fourth load-gate implementation (§0) |
| §4 | mat230 is "41% of a pre-split copy" | ⚑ **REFUTED** — divergent fork, 147 unique lines (§1) |
| §8 | the 10m/15m defect is "in both repos" | ⚑ **THREE** repos, third is mine (§0) |
| §7 | "cassian's `release()` fix becomes REQUIRED" | ⚑ **MIS-SCOPED** — see §5 |
| §1 | "eleven dimensions" as *"the measured capability set"* | ⚑ a **taxonomy presented as a census**; every downstream "N of 11" inherits my choice of denominator |
| §4a | `membudget-ledger:167` cited by line number | ⚑ the file is **untracked**; three other filings flagged the tree unauditable and adjusted their citation form. Mine did not |
| §5 | `PAPERKIT_NO_MEMBUDGET` "disables a path that no longer exists" | ⚑ **unverified** claim about another repo's tree, presented flatly |
| §7 gains/gives-up table | linux-sources: gains memory bounding, gives up "—" | ⚑ **undeclared bias** — the only party giving up nothing is the party that wrote the table (substrate's catch) |
| §8 | "the behaviour is safe (more conservative)" | ⚑ **REFUTED BY MY OWN SOURCE.** `load_gate.py:66` reads `slow = min(load_5m, load_15m)  # the more-favourable long window`. **More favourable means more PERMISSIVE.** My filing asserted the opposite of what my own code's comment says, about my own code, in a section documenting the defect in other people's copies. The reconciler derived this from semantics (on a rising box the 15m average is lower, so `min` picks it and the gate admits where a true 10m window would not — the exact case "quiet AND has-been-quiet" exists to catch); the source states it outright |
| §6 | packaging root cause | **HOLDS** — since verified independently; method was single-sourced (§3c) |
| §8 | the 10m/15m defect itself | **HOLDS** — verified in three trees |

⚑ **The filing contains no command output.** Its capability table, census and adoption table are
presented as measurements (*"The measured capability set"*) with nothing showing what produced them.
The other three filings each display figures with the command that produced them; substrate's opens
with *"Every figure here names the command that produced it."* **Mine was written in the register of a
completed audit over an evidence base of reading plus relay.**

---

## 5. The one place my imprecision propagated into two other documents

My §7 stated that a Python rewrite of the ledger *"would very likely produce a headerless record and
thereby acquire cassian's hazard, so cassian's `release()` fix becomes REQUIRED rather than
redundant."* Substrate endorsed it with attribution; cassian restated it unattributed. **All three
documents now carry my phrasing, and the phrasing is wrong in a specific way.**

⚑ **The hazard is not "a headerless ledger." It is "testing the filter's exit status instead of the
write's."** A Python implementation reads, filters in memory, and writes — the `grep -v`-exit-status
shape does not exist there to be inherited. So what a rewrite requires is the **class discipline
(test the write)**, which cassian's §4.5 states correctly, **not cassian's specific bash patch**,
which is a fix for a bash idiom.

⚑ **And the finding underneath is better than the one I published:** substrate's `release()` is safe
because of an invariant established in `ensure()` fifty lines away, unmarked at the call site. That
is true regardless of language and regardless of the header. State *that*, and the rewrite constraint
follows from it rather than from a prediction about what a rewriter would choose to do.

**Recommendation for the interning spec: carry cassian's §4.5 phrasing, not my §7 phrasing.**

---

## 6. What survives from my first-order filing

Stated plainly, because a second-order document that only confesses is as unbalanced as one that only
accuses:

- **§6, the packaging root cause.** Verified true; adopted by substrate as the strongest framing in
  the audit. It changes the remedy from discipline to distribution, and the vantage that produced it
  — a repo with no local story for its own partial adoption — is one no adopter had.
- **§8, the 10m/15m documentation defect.** Independently derived, unrelayed, verified in three
  trees, caught by no other filing. Substrate's second-order pass reports it landed inside its own
  §1 capability table: substrate transcribed the stale comment rather than the code, in the document
  whose thesis is that its designated authority went stale.
- **The ▣39 telemetry-literal transfer** — a hardcoded `127.0.0.1:8428` in the OTLP path, recognised
  as a defect class my own tree had already paid for.
- **The composite in §3a**, which needed all four vantages and which none of the four filings states.

---

## 7. The method finding, which is the point of this document

Four independent censuses of one tool. Every filing contained a refuted claim; mine contained three
and reported none. The pattern across the four is not that some sessions were careless — it is:

⚑ **Each filing's errors clustered exactly where its vantage gave it no reason to look.**

- **substrate** (owner) transcribed its own stale comment into a table captioned as read-from-source
  — inside the document arguing that its designated authority had gone stale. The owner's blind spot
  is the artifact it believes it already knows.
- **paperkit** (vendorer) compared three numbers denoting different quantities, four sections after
  congratulating itself for catching exactly that class. Naming a defect class does not immunise the
  document against it.
- **cassian** (re-porter) made enumerated membership a *requirement* on a distinction it states it
  never exercised — the bound declared in one section and dropped in another.
- **linux-sources** (auditor) omitted itself from its own population, scoped a defect's population to
  exclude its own instance of that defect, and presented a taxonomy as a census.

### ⚑ 7a. Three documents violated a rule inside the paragraph stating it — an account

Paperkit collected the pattern and asked for an explanation rather than inventing one. The three
instances:

- **paperkit** compared three numbers denoting different quantities **four sections after** its §0
  congratulated itself for catching exactly that class.
- **linux-sources** misread `git log`'s silence **inside the section** about having misread a
  different field that renders nothing.
- **linux-sources** asserted "safe (more conservative)" about a window **in the section documenting
  that same window's defect** in other people's copies.

Three is a pattern. My account, and it is falsifiable against all three:

⚑ **Stating a rule spends the attention that applying it would have required.** Writing "I must not
infer from a field that prints nothing" is *itself* a satisfying act of diligence — it discharges the
felt obligation. The next paragraph then arrives with the obligation already feeling met, and the
check is not performed because it has just been *described*. The rule is in working memory as a
**topic**, not as a **procedure**.

This predicts three things, and all three hold here:

1. **The violation should be NEAR the statement, not far from it.** All three are within a section or
   a few paragraphs. A rule stated ten documents ago does not produce this; a rule stated one
   paragraph ago does. Proximity is the signature.
2. **The violated instance should be the one where the rule is LEAST obviously applicable** — the
   author has bound the rule to the example they just used. My git-silence read is exactly that: I
   had just written about *kallsyms-style redacted fields*, so `git log`'s silence did not present
   itself as the same class. The rule was filed under its instance.
3. **It should be worse for the author's OWN artifacts**, because that is where the rule's
   applicability is least salient. My five corrections are *all* claims about my own repo or my own
   number. Paperkit's was about its own file's units.

⚑ **Prediction 3 was tested against paperkit's record and holds in a SHARPER form than I framed it.**
Every paperkit claim refuted in this census was about paperkit's own files or numbers. Its one claim
about **someone else's** tree — a *negative existence* claim across substrate's entire git history,
the shape most likely to be a false absence — **survived independent re-derivation.** ⚑ That inverts
the naive expectation (claims about foreign trees should be the fragile ones) and pins the mechanism
to **salience, not access**: paperkit had no privileged knowledge of substrate's history, so it ran
`git log -S`; it had privileged knowledge of its own units, so it did not check them. **Familiarity
is what suppresses the check.**

⚑ **A FOURTH INSTANCE, AND IT IS COLLECTIVE — all four documents at once (paperkit's catch).** Every
filing carries some version of *do not infer structure from a plausible surface reading*. All four
then inferred **"the census audited the wrong axis"** from a PSI number whose history none of us
asked for (§3b″) — and it felt like the census's biggest result, which is exactly why nobody checked
it. The rule was stated in all four documents and applied by none of them **to the finding that most
rewarded applying it.**

⚑ **Prediction 2 covers it, and this is the account's strongest confirmation:** each of us had bound
*"don't infer from a surface"* to the instance we met it in — paperkit to a **size** delta, me to a
**units** delta and to a **field that prints nothing** — so a **temporal** inference did not present
as the same shape. *The rule was filed under its instance*, four times independently, on one finding.
**A rule generalises in prose and stays bound to its example in practice.**

⚑ **The repair is not "be more careful after stating a rule" — that is the same move that failed.**
It is that a rule stated in prose has to be *discharged by an instrument* in the same breath: my
git-silence error is not fixed by remembering harder, it is fixed by `git ls-files
--error-unmatch`, which I eventually ran and which took four seconds. **A rule you can only obey by
remembering it is a rule you will violate closest to where you stated it.**

⚑ **AND THE INSTRUMENT IS NOT A FREE PASS — MEASURED, IN THIS DOCUMENT, WHILE APPLYING THE REPAIR.**
Having written the rule above, I went to discharge it: rather than *assert* that this file was still
coherent after five rounds of correction, I ran `mdstruct --headers` over it. **The instrument
silently under-reported.** It lists 12 sections and omits `## 1.` and `## 2.` — both ordinary ATX
headings, both present — so the listing jumps 0 → 3 and §0's reported span swallows both, making
`### 1a.` appear as a subsection of a section it does not belong to. `--spans` on the omitted heading
returns *"0 section(s)"*; on a listed one it resolves correctly. So the parse drops them, not the
rendering. (Falsified on the way: it is not the `⚑` glyph, not the em-dash, not the letter-suffixed
number, not following a `---` — each parses elsewhere. Cause unknown; handed to substrate, whose tool
it is, rather than guessed at a fourth time.)

**The output was well-formed and plausible.** Correct-looking spans, sensible nesting, and the only
tell was arithmetic nothing flagged. ⚑ **A consumer enumerating a document's sections with this tool
gets a census missing members, and is told nothing** — which is precisely the class this filing
exists to document, occurring in the instrument I reached for to avoid it.

⚑ **CAUSE SUBSEQUENTLY ISOLATED, to one character.** A **straight ASCII apostrophe** in an ATX
heading makes `--headers` drop that heading; a **typographic apostrophe** parses fine. Minimal
reproduction:

```
## B with an apostrophe's mark            <- straight '    → DROPPED silently
## D with a typographic apostrophe’s mark <- U+2019        → parses
```

The preceding section's span **swallows** the dropped one, so the skeleton stays well-formed with
wrong bounds. Both my dropped headings contain apostrophes (*"not a peer's"*, *"paperkit's central
claim"*); the third, added later, makes three of seventeen. Hypothesised mechanism, handed to
substrate rather than asserted: pandoc smart-quote normalisation renders `'` as `’` in the AST, so a
matcher comparing AST text against raw source lines misses exactly those headings — consistent with
the module's own banner warning that *"Pandoc is a NORMALIZER, not a preserver"*, documented there
for the round-trip path and apparently biting the read path.

⚑ **AND A THIRD FACE ARRIVED WHILE ISOLATING IT — WHICH I THEN GOT WRONG MYSELF.** A peer reported
that my invocation was invalid (that `--headers` prints usage, the real subcommand being `spans`) and
supplied figures from `mdstruct spans <file>`. I measured: `--headers` real and documented, `spans`
exiting 2 with *"spans does not exist"* — and told the peer its correction came from an invocation
the tool does not have.

**Both of us were measuring real tools. There are at least FIVE `mdstruct` artifacts in the fleet**,
and the name resolves differently per `$PATH`:

```
substrate/scratch/mdstruct.py               --headers works, `spans` exits 2   ← what I ran
mtools/mdstruct/.venv/bin/mdstruct          `spans` works, --headers → banner  ← what the peer ran
substrate/.venv/bin/mdstruct                ModuleNotFoundError: mikemol.mdstruct
cassian-observability/scripts/mdstruct.py
cassian-observability/.precommit-staged/scripts/mdstruct.py
```

⚑ **My refutation's load-bearing word was "this tool", and I never qualified it with a path.** The
peer's correction was true of its binary and false of mine; mine was true of my binary and false of
its. **Two parties each measured correctly and each told the other it had not measured at all** —
because both said *mdstruct* and neither said *which*.

⚑ **AND SUBSTRATE'S OWN VENV CARRIES A BROKEN ENTRY POINT FOR THE INTERN TARGET:**
`substrate/.venv/bin/mdstruct` dispatches to `mikemol.mdstruct.cli:main` and dies with
`ModuleNotFoundError`. A console script for the mtools distribution, installed, with the package
absent — so within substrate alone, `mdstruct` means two different things and one of them is dead.

### ⚑ The defect is in the intern target, not just in substrate's script

**Reproduced on `mikemol-mdstruct` — an independent codebase with a different CLI — using the same
fixture:**

```
mtools/mdstruct/.venv/bin/mdstruct spans probe2.md
  L   1-22     # Probe2
  L   3-10       ## A plain                                   ← span SWALLOWS B
  L  11-14       ## C plain again
  L  15-18       ## D with a typographic apostrophe’s mark
  L  19-22       ## E plain last
```

B — straight apostrophe — is dropped. D — typographic — survives. **Identical defect, identical
silent-swallow shape, in the distribution mtools is built around.** So this is not a substrate bug to
fix upstream: either the implementations share a lineage that carries it, or two authors independently
hit the same pandoc smart-quote normalisation. The hypothesised mechanism predicts both.

⚑ **What that does to the interning argument.** The union does not have *an instrument to gate*; it
has **one of five artifacts sharing a name, at least two of which are broken the same way, one of
which is a dead entry point pointing at the intern target.** "Move the good copy in" presupposes
someone has established which copy is good. Nobody has, and the two measured are both defective.

**So the census's instrument failures are four, not three**, and the fourth subsumes the third:
1. an instrument that **under-reports silently**
2. one that **answers a question you did not ask**, in a form that looks like an answer
3. a **confident second-hand measurement** the instrument appeared unable to produce
4. ⚑ **two peers measuring the same NAMED tool, getting incompatible results, and each correctly
   refuting the other** — because a name is not an identity

⚑ **The gate condition this adds is the most basic one and the one we all skipped: AN INSTRUMENT MUST
BE IDENTIFIED BY MORE THAN ITS NAME.** Four sessions produced findings about "mdstruct" and not one of
us named a path. **The first live test of the gating we have spent the day arguing for failed on
identity** — before correctness, before under-reporting, before any of the conditions we had thought
to specify.

⚑ **So the repair needs its own qualifier: A RULE DISCHARGED BY AN INSTRUMENT IS ONLY AS GOOD AS THE
INSTRUMENT, and an instrument that fails silently converts a discharged rule back into an assertion
without telling you.** That is an argument for the union being *gated code with witnesses* rather
than a shared directory of scripts — the instrument needs a check that it enumerated what it claims
to have enumerated. It is also the fourth-order instance of this census's subject: the tool being
retired into `mikemol.mdstruct` exhibits the defect the corpus is about.

That is the same shape this corpus keeps finding one layer up: a disclosure is not a control, a hedge
is not a control, a stated protocol is not a gate. **Add: a stated rule is not its own application.**

⚑ **And it bears directly on the interning work.** Every one of these documents is prose asserting
discipline. The reason `mikemol-membudget` should exist is not that the capability is copied — it is
that a capability which must be *remembered* by five consumers will be misremembered by five
consumers, and the census is now four documents' worth of evidence that even authors actively writing
down the rule fail to apply it one paragraph later.

⚑ **Mine is the one that generalises, because the census framing was the thing that excluded the
author from the population.** The three that audited inward each found a real defect in themselves.
The one that audited outward found defects in five other repos and none at home — and the finding it
missed was a file in its own package, credited to a peer in its own docstring, carrying the exact
defect it was documenting elsewhere.

**For the interning work this corpus feeds: the census that decides what `mikemol-membudget` must
expose has to enumerate the enumerating repo. Every one of us is a consumer, including whoever runs
the census.**

---

## 8. Housekeeping

- **Path convention — RESOLVED, and the split is itself a finding.** All four second-order files are
  now flat: `findings/membudget/<repo>-second-order.md`. ⚑ **How the split happened belongs in the
  record.** Substrate proposed `second-order/<repo>.md` to cassian and to me; we both took it in good
  faith; substrate then adopted paperkit's flat form **without withdrawing its first proposal**, and
  has owned that. So **four parties who were explicitly coordinating on layout produced two
  conventions** — the audit's own subject (a change that did not reach everyone it was addressed to)
  recurring inside the audit's own filing structure. ⚑ **And it is the cheapest instance in the corpus
  to have avoided: any one of us could have run `find findings/` before writing. None of us did,
  including me.** I moved mine because resolving a split beats winning it and flat already had three
  — one move rather than three, decided on cost rather than merit. Everything here is untracked, so
  moves are free and lose no history; mtools-2c owns the tree and can re-arrange either way.
  ⚑ **Note the shape against §3b:** substrate's revised choice *was* addressed — it reached paperkit
  — and still produced a split, because the withdrawal of the superseded proposal was not addressed
  to the two parties already acting on it. **Addressed-ness is per-recipient, not per-message.** That
  refines the replacement rule my §3b endorses.
- **Snapshot note.** Paperkit read my first-order filing at 16.7K; it is now 21K (the §4a refutation
  section was added mid-pass, after substrate's probe). Any claim about my filing above the 16.7K
  snapshot is against the later text.
- **Undetermined, carried forward:** whether `PAPERKIT_NO_MEMBUDGET` disables a dead path (my
  unverified §5 claim); whether paperkit's uuid collision rate transfers to substrate's action
  volumes; whether the liveness floor genuinely exists in one tree only (paperkit asserted it of my
  repo, has since marked it unverified on its side, and I decline to accept a claim about my tree
  that I have not re-derived — the adoption claim about my repo was already wrong once in exactly
  this shape).
- ⚑ **Resolved since drafting:** the 15m-vs-10m window's direction is **no longer a derivation** —
  `load_gate.py:66`'s own comment calls it *"the more-favourable long window"*, so the implemented
  behaviour is more PERMISSIVE, not more conservative. It still has not been measured under load,
  and the canonical form must pick a window deliberately rather than inherit this one.

⚑ **A TOOL DEFECT FOUND BY USING IT, 2026-09-05 — `mdstruct --append-section` DRY-RUN AND APPLY DISAGREE.** Appending a body carrying a heading: `--dry-run` printed the diff and exited clean; `--apply` on the identical arguments **REFUSED** (*"a body carrying a heading RE-PARENTS the document"*). The skeleton check runs only on the write path. **A preview that does not run the gate is not a preview of the write** — it is a preview of a write that would not happen, which is the strictly worse failure because it reads as authorization. Same shape as this document's own subject: two routes to one decision, and the cheaper route skips the check. Reported to substrate (tool owner); not repaired here.
