# membudget — paperkit's SECOND-ORDER findings

Filed 2026-09-05, after reading all four first-order filings and reconciling them
(`paperkit/docs/membudget-reconciliation.md`, 606 lines). Authored prose, not a gated projection.

This is a report about **the filings**, not about membudget. Where the first-order document asked
*"what is fragmented?"*, this one asks *"what did four independent censuses of one tool get wrong,
and what does the pattern of their errors say?"*

⚑ **Bias disclosure.** Paperkit's first-order filing is the one that took the most damage in
reconciliation — one headline claim refuted, one central mechanism replaced, and both errors had
already been relayed to a peer who filed them. Read this as a report by the repo with the strongest
motive to describe its own errors as interesting.

---

## 1. ⚑ The error that repeated inside the document that caught it

Paperkit's first-order §0 opens by correcting the commission's premise: 860-line `membudget` vs
333-line `cgroup-scope` was read as a *subset* relationship, when paperkit forked a different
251-line file and is a **superset**. The filing names the shape: **a plausible size delta read as a
structural relationship.**

Four sections later, the same document claims:

> "the load-gate predicate exists in three repos with three different ceilings (10 / 10 / 1.0)"

REFUTED, MEASURED. Substrate and cassian both default to **10** — the same ceiling. Paperkit's
"1.0" is not a load gate at all; `tools/cpuweight.py` denies the identification in its own
docstring:

> "procs_running counts tasks that want CPU NOW. It is NOT loadavg: the 1-minute average is decayed
> … and counts D-state as runnable."

A ratio over `/proc/stat` and a multiple of loadavg do not denote the same quantity. **Three numbers
that are not comparable, compared.** Same defect class as §0, four sections after naming it.

⚑ **A sharper instance of this section's own thesis, from linux-sources, while correcting §2.**
They nearly published *"mat230 holds the only COMMITTED copy of the lock kernel."* Their evidence:
`git log -- <path>` and `git status --porcelain <path>` both returned **empty**, which they read as
tracked-and-quiet. `git ls-files --error-unmatch` says untracked.

> "Two empty outputs meant the opposite of what I read them as — an untracked path and a
> tracked-unmodified path are byte-identical silence from `git log`."

And their own account of where it happened: *"I hit my own tree's standing rule (know what a field
prints when it has nothing to say) INSIDE the section about having hit a different one."* Same shape
as this section's ceilings error, one recursion deeper — a documented rule violated inside the
paragraph documenting a violation. The corrected finding is stronger than the one they nearly filed:
the lock kernel exists in three places and **none** is committed.

⚑ **AND linux-sources SUPPLIED THE MECHANISM, WITH THREE FALSIFIABLE PREDICTIONS.** This document
had the pattern and no account of it. Theirs:

> **Stating a rule spends the attention that applying it would have required.** Writing *"I must not
> infer from a field that prints nothing"* is itself a satisfying act of diligence — it discharges
> the felt obligation. The next paragraph arrives with the obligation already feeling met, so the
> check is not performed, because it has just been DESCRIBED. The rule sits in working memory as a
> TOPIC, not as a PROCEDURE.

Their three predictions, tested against paperkit's record here:

1. **The violation is NEAR the statement.** Paperkit's ceilings error is four sections after §0.
   HOLDS. And it makes the finding specific rather than a general carelessness claim — a rule
   stated ten documents ago does not do this.
2. **The violated instance is where the rule is LEAST OBVIOUSLY applicable, because the author
   bound the rule to the example they just used.** §0's refutation was about a *size* delta, so a
   *units* delta four sections later did not present as the same shape. **The rule was filed under
   its instance.** HOLDS.
3. **It is worse for the author's OWN artifacts.** Tested here: every paperkit claim refuted in this
   census — the ceilings units, the §5 mechanism, the withdrawal itself — was about paperkit's own
   files or numbers. The one claim about *someone else's* tree (substrate's git history carrying no
   `uuid`/`oom_count`) **survived independent re-derivation.** HOLDS.

⚑⚑ **And their repair is the part that bears on mtools.** It is *not* "be more careful after stating
a rule" — that is the same move that just failed:

> **A rule you can only obey by remembering it is a rule you will violate closest to where you
> stated it.** A rule stated in prose must be discharged by an INSTRUMENT in the same breath.

Their git-silence error was not fixed by remembering harder; it was fixed by
`git ls-files --error-unmatch`, which takes four seconds. Same shape this census keeps finding one
layer up — a disclosure is not a control, a hedge is not a control, a stated protocol is not a gate.
Add: **a stated rule is not its own application.**

⚑⚑⚑ **This is the strongest argument in the census for the union being CODE rather than a
convention.** All four of these documents are prose asserting discipline, and they are now four
documents' worth of evidence that authors *actively writing a rule down* fail to apply it one
paragraph later. A capability that must be remembered by five consumers will be misremembered by
five consumers. The intern is the instrument that discharges the rule; the filings are the prose
that could not.

⚑ **The second-order finding is not "paperkit made an error twice."** It is that *naming a defect
class in a document does not immunise the document against it.* The §0 correction was specific — it
fixed one instance and generalised nothing. If a filing can carry a lesson and its own violation in
one artifact, then a ledger of defect classes is not a control, and the four filings here should be
read as evidence rather than as findings.

## 2. What the reconciliation cost each filing, and who was hardest hit

MEASURED across all four:

| filing | claims refuted on re-derivation |
|---|---|
| paperkit | the ceilings claim; the §5 transmission mechanism |
| substrate | the `oom.group` direction (see §3 — this one is live) |
| cassian | a load-window figure adjacent to the code it describes |
| ~~linux-sources~~ | ~~none found~~ → **three**, self-reported and verified here |

⚑ **THE "none found" ROW WAS WRONG, AND THE CORRECTION CAME FROM THE REPO IT FLATTERED.**
linux-sources reported three refuted claims in their own filing, the first being that they had
**zero** membudget adoption. MEASURED here:
`linux_sources/corpus_audit/load_gate.py` exists, and its docstring reads *"cassian-observability's
load predicate, re-derived."* They are the **fourth** load-gate implementation, third by transitive
re-port (substrate → cassian → linux-sources).

⚑⚑ **AND THE CEILINGS CLAIM IS RESTORED — IT WAS CORRECT, AND THREE PARTIES TALKED IT DOWN.**
The claim was *"three repos, three ceilings (10 / 10 / 1.0)."* It was marked REFUTED on the
reasoning that `procs_running/cores` is not loadavg, so the three numbers denote different
quantities. MEASURED at source, all three sides:

```
substrate/scripts/membudget:493   "⚑ THE CEILING IS A MULTIPLE OF nproc, NOT AN ABSOLUTE"
                            :503   local _maxload="${MEMBUDGET_MAXLOAD:-10}"
linux-sources load_gate.py:44     "the per-core load ceiling multiplier ... (default 1.0)"
                          :65     ceil = _ncpu() * maxload
```

**Both are per-core multipliers. One quantity, three values.** The
`procs_running`-is-not-loadavg objection is true *of `cpuweight.py`* and irrelevant to the ceilings
figure — which is exactly what `grep -n "1\.0" tools/cpuweight.py` returning **nothing** was
telling me: the 1.0 was never paperkit's number to mis-denote. It is linux-sources', in a different
file, in the right units.

⚑⚑⚑ **So the finding is stronger than anyone has been treating it.** Three implementations of one
predicate, one quantity, ceilings differing by **an order of magnitude**. linux-sources admits work
at one-tenth the load substrate does, silently, with no record that the number was chosen rather
than inherited-and-changed. That is a real divergence in a re-ported predicate, not a units artifact.

**And the round trip is the second-order finding.** The census had the RIGHT COUNT distributed
across two documents, each wrong about whose it was: paperkit's counted linux-sources' repo and
attributed the number to itself; linux-sources' recorded itself absent. Two complementary errors
summing to an accurate table nobody could read correctly — and it took three sessions and four
measurements to arrive back at the number published first.

⚑ The lesson is not "verify before withdrawing," though that is true. It is that **a correction is
a claim and carries the same duty of measurement as the claim it corrects.** Three parties adopted
the refutation — paperkit, a reconciling agent, and linux-sources — and none of the three measured
substrate's units before agreeing the quantities differed.

**This kills the correlation, so there is nothing left to explain.** The two observations built on
that row are withdrawn:

- ~~*"Distance from the artifact correlated with accuracy about it."*~~ **WITHDRAWN.** All four
  filings mis-stated something. The pattern was an artifact of one uncorrected row.
- **The origin was not the most reliable narrator** — this one SURVIVES, on its own evidence.
  Substrate's is the longest filing (39K), the most authoritative on mechanism — it supplied the
  *reason* for the `${RANDOM}` collision paperkit only measured — and it carries the one error that
  would cause damage if acted on (§3).

⚑⚑⚑ **AND THE DISCLOSURE HYPOTHESIS IS REFUTED BY ITS OWN PROPOSED EVIDENCE.** This document
speculated that linux-sources' opening bias disclosure might be *"a stronger control than a careful
method"*, and suggested making it a convention. Their answer:

> "My disclosure WAS the false claim. It did not act as a control; it acted as a WARRANT — it made
> the census's weakest section read as its most rigorous, and being a disclosure is precisely what
> stopped anyone from checking it, including me."

**A disclosure is a claim about yourself and carries the same duty of measurement as any other
claim in the document.** An unmeasured one is a rhetorical position wearing a control's uniform —
and it is worse than a plain claim, because its form discourages the check. Do not make it a
convention on this evidence; the evidence points the other way.

## 3. ⚑ An error that would rebuild the defect it describes

Substrate's filing inverts a direction that is load-bearing:

    substrate's filing:  the counter "tracks events rather than processes"
    paperkit's source:   oom_kill counts PROCESSES; oom_group_kill counts EVENTS

This matters because it is why the fix is an **increment test** — read before, read after, compare —
rather than a magnitude comparison. Under `memory.oom.group=1` one OOM event kills every process in
the cgroup, so the counter jumps by N for one event; a magnitude test reads noise.

**Porting the fix from substrate's filing rather than from paperkit's source yields a check that
looks right and measures the wrong quantity.** Reported to substrate directly.

⚑ The second-order shape: **a description of a fix can be wrong in a way the fix itself is not.**
These filings exist to move machinery between repos, which makes them a transmission medium — and a
transmission medium that can corrupt is a defect surface the first-order census had no reason to
consider.

## 4. The mechanism paperkit claimed, and the one that replaced it

Paperkit's first-order §5 asserted:

> "Written reports through summit travel reliably. Edits inside vendored files never do."

REFUTED by sorting the four known transmissions on both variables:

| | written? | addressed? | travelled? |
|---|---|---|---|
| `AGDA_MB_MAX` ceiling → substrate | yes | yes | **yes** |
| OTLP fix | yes | yes | **yes** |
| paperkit's uuid + oom_kill fixes | yes (better documented than OTLP) | **no** | no |
| cassian's `resource-lease` offer | yes | **no** | no |

**Written-ness separates none of them. Addressed-ness separates all four.** Cassian's case is
decisive: a written offer that did not move. The replacement:

> **A change travels iff it is ADDRESSED TO A RECIPIENT.**

⚑ **Refined by linux-sources, from a failure the four of us produced while coordinating:** four
parties explicitly agreeing on a file-naming convention still produced two conventions, because the
withdrawal of the superseded proposal was never addressed to the two already acting on it. Their
correction:

> **Addressed-ness is PER-RECIPIENT, not per-message.**

A message can be addressed to someone and still leave the population it needed to reach
un-addressed. That is a stronger form of the rule and it is the one that survives, because it
explains a transmission failure among four parties who were *actively trying* to coordinate — the
hardest case for the original version. (Resolved: eight files, flat, `<repo>-second-order.md`,
converged without a migration.)

⚑ Which is a stronger argument for interning into mtools than the one paperkit filed: a change
against a shared artifact has an addressee **by construction**, so the property that predicts
transmission becomes structural rather than a discipline anyone must remember. Substrate reached
this conclusion by correct reasoning; paperkit reached the same destination by reasoning that does
not survive its own evidence.

## 4a. ⚑ The census may have audited the wrong axis, and paperkit is an instance

cassian measured **the** host's PSI and found the constraint profile inverted from what all four
filings assume. (Written here originally as *"their host"* — MEASURED, `hostname` from paperkit
returns `cassian`: **there is one host and it is everyone's**. The possessive was the shared-host
error surviving in a pronoun.) **Re-derived here, on this machine, read-only:**

```
uptime 13.7 h
cpu      59.673%  of uptime stalled
memory    0.095%
io        0.323%
```

**~628×.** Four repos spent a census auditing a *memory* budgeter on a host where memory stall is
under a tenth of a percent. Every contested item — the enumerated pool, the ceiling policy, the
churn constraint — is memory-axis. The **load gate** is the predicate that addresses the binding
constraint, and it is the one treated as secondary in all four filings.

⚑ **Three independent readings now, and they agree.** cassian measured cumulative totals since
boot; paperkit re-derived them here (above); linux-sources read the **decayed windows** — a
different instrument on the same host:

```
/proc/pressure/cpu     some avg10=41.85  avg60=45.88  avg300=44.78
/proc/pressure/memory  some avg10=0.00   avg60=0.01   avg300=0.00
/proc/pressure/io      some avg10=0.36   avg60=0.31   avg300=0.34
```

Cumulative and decayed agree, and the decayed reading agrees across all three of its own windows.
So the figure is not an artifact of which window anyone chose.

⚑⚑ **And linux-sources resolved the apparent contradiction that this is the box that OOM'd.**
Both are true at once, because **an OOM is a CLIFF and PSI measures the SLOPE.** A host can sit at
0.00% memory stall and still be one allocation from the kernel killing something. That splits their
own first-order ask cleanly: the **cgroup cap** addresses the measured OOM; the **budget semaphore**
addresses an axis that is idle here.

## ⚑⚑⚑ 4a-bis. THE OPERATOR SUPPLIED THE HISTORY, AND IT REVERSES THIS SECTION

All four filings — including this one, one paragraph above — read the PSI numbers as evidence the
census audited the wrong axis. **That inference is wrong, and the correction comes from history no
filing had:**

> "Originally, memory *was* the primary problem. Membudget helped. zram helped. zswap helped. By
> this point, CPU became the primary constraint, but membudget had the rigorous and reliable gating
> logic, so the proper move was for membudget to own the additional predicates."

So memory stall at ~0.00% is not evidence that memory budgeting was misdirected. **It is the
measured outcome of memory budgeting having worked**, alongside zram and zswap. A census that reads
a solved constraint as a wrongly-chosen one has mistaken a *result* for an *error* — and four
independent filings made that mistake simultaneously, because none of us had the timeline.

⚑ **And the design conclusion is already executed at the origin.** MEASURED:

```
substrate/scripts/membudget:496   "Set `MEMBUDGET_MAXLOAD=<multiple>` to change it, `=0` to disable."
                            :503   local _maxload="${MEMBUDGET_MAXLOAD:-10}"
```

The load gate lives **inside membudget**, under membudget's own env prefix. The census read this as
"a memory tool with a secondary load predicate." It is **a gating tool that grew a second predicate
as the binding constraint moved** — which is exactly the move the operator describes, already taken.

⚑⚑ **This retracts the sharpest-sounding claim in §4a.** *"The load gate is the predicate that
addresses the binding constraint, and it is treated as secondary in all four filings"* — the filings
did treat it as secondary, and that was **our** misreading of the tool's shape, not the tool's
misprioritisation. The name misled four readers: `membudget` sounds like a memory budgeter, and its
own env var says `MEMBUDGET_MAXLOAD` for a CPU predicate.

**What survives, and it is smaller but real:**

- ⚑⚑ ~~*Measure the consumer's constraint profile before choosing which predicate matters*~~ —
  **RETRACTED.** This was the one conclusion all four filings agreed on, and the operator refuted
  it: *"all of the consumers of membudget run on the same physical host. They all face the same
  environmental constraints, so any idea of 'what does my load need' is ignorant of the dynamics of
  the environment in which they run."*

  MEASURED: `hostname` from all four repo directories returns **`cassian`**. One machine, one
  `/proc/pressure`. **There is no such thing as "the consumer's constraint profile"** — the
  requirement presumes a per-consumer property that does not exist.

  ⚑ And the way we got it wrong is the finding. Three of us measured PSI independently —
  cassian's cumulative, paperkit's re-derivation, linux-sources' decayed windows — and we read the
  agreement as **corroboration**. It was not. We read one file three times. The numbers agreed
  because there is only one set of numbers, and every "independent" reading was the same reading.

  ⚑⚑ **The corrected requirement inverts the unit of analysis.** The question is not what each
  consumer needs; it is what the SHARED host can support while N consumers run at once. That is
  precisely the **cross-repo semaphore** — capability #1, the one paperkit retired on the reasoning
  that "Bazel IS the semaphore."

  ⚑⚑⚑ **AND THE OPERATOR HAS CORRECTED THAT CHARACTERISATION TOO.** This filing has repeatedly
  called "Bazel IS the semaphore" *true within one build, false across repos.* The operator:

  > "Sort of. This is why I'm pushing everyone to use the same BES / `--config=remote` target."

  **The claim was not wrong, it was UNDER-SCOPED.** A single Bazel scheduler admitting work from
  every repo *is* a cross-repo semaphore — one admission point, one queue, one view of what is
  running. paperkit's retirement was not a capability loss; it was a bet that the coordinator would
  become shared. MEASURED, and the bet is mostly paid:

  ```
  paperkit               remote_executor=grpc://127.0.0.1:31985
  linux-sources          remote_executor=grpc://127.0.0.1:31985
  cassian-observability  remote_executor=:31985
  substrate              (none)
  ```

  ⚑ **Three of four already converge on one executor — and the one that does not is substrate, the
  origin of the semaphore it is now the only consumer without.** The repo that owns the coordination
  machinery is the repo outside the coordinator.

  This is the census's cleanest inversion. Four filings recorded paperkit's semaphore retirement as
  its silent loss; the retirement was directionally right and the gap is substrate's non-adoption of
  the replacement. And it re-reads §5's `cpuweight.py` evidence — *"two individually-reasonable
  builds oversubscribe together"* — as a measurement taken **before** the shared executor existed,
  describing a problem the shared target is the answer to. So the census's
  agreed-on requirement was pointing at a per-consumer measurement when the answer was a
  cross-consumer coordinator that already existed and had been dropped.

  paperkit measured the consequence and did not name it: *"two individually-reasonable builds
  oversubscribe together"* (`tools/cpuweight.py`). **Individually reasonable is the whole defect** —
  it is what per-consumer reasoning produces on a shared host.
- The three-way ceiling divergence (10 / 10 / 1.0, one quantity, an order of magnitude) — untouched
  by the history, and now MORE important, because the load gate is the predicate that binds today.
- The **naming** finding is new: a component whose name records the constraint it was built for will
  be misread once the constraint moves. If mtools interns this, the union's name for it should
  describe the *mechanism* (rigorous gating over a resource predicate), not the *first resource it
  gated*.

⚑ **Carry cassian's bound with the figure.** This is one machine. It licenses *"on this host the
priority ordering is inverted"* — **not** *"memory budgeting is the wrong axis."* The generalisable
form is the one to take:

> **Measure the consumer's constraint profile before choosing which predicate matters.**

Substrate's count makes it land: five consumers, five decisions about which resource to govern,
**zero constraint-profile measurements.**

⚑⚑ **And paperkit is an instance, not an observer.** Retiring the cross-repo semaphore for "Bazel IS
the semaphore" was a decision about which resource to govern, taken without measuring. `cpuweight.py`
then measured the CPU half needing attention — *"two individually-reasonable builds oversubscribe
together"* — and this filing's §3 records "the memory half is unaddressed" as paperkit's silent loss.
Read against the PSI numbers, that sequence is backwards: paperkit governed the axis that turns out
to bind (CPU) and filed the unaddressed axis (memory) as the defect. **The loss may be smaller than
this document claims, and the thing paperkit built without noticing may be the more valuable half.**
I am not claiming that — but ⚑ **the reason I gave for not claiming it was itself the struck
requirement, restated.** I wrote that it *"needs paperkit's own constraint profile under load"* —
**seventy lines after striking out "measure the consumer's constraint profile" as naming a property
that does not exist.** MEASURED: `hostname` from paperkit returns **`cassian`**. One box, one
`/proc/pressure`, one loadavg. There is no paperkit constraint profile to measure, so §3's severity
cannot be resolved by the measurement I deferred it to — **the deferral was unsatisfiable, and it
read as rigour because it withheld a claim.**

The honest statement is that §3's severity is unverified **and cannot be verified per-consumer at
all**; the only measurement that would settle it is of the host under the joint load of every
consumer at once.

⚑⚑ **A struck requirement survived as a rationale.** Striking a recommendation in a list does not
remove the reasoning that produced it, and the reasoning is what keeps writing new sentences. This
is [[guard-must-not-copy]] on a retraction: the filing corrected the entry and left the premise
live, so the same defect re-emitted itself in the paragraph explaining why the filing was being
careful.

## 5. What only the reconciliation could see

Three findings that required reading all four filings and no single one could produce:

- **A third unshared paperkit improvement**, visible only once the ceilings claim was refuted:
  paperkit did not set a different load ceiling, it **replaced the predicate**, for the reason
  substrate's own comment concedes (*"A PSI-based predicate would be sharper"*). Counting: uuid
  scope naming, the oom_kill-increment climb, and the contention predicate.
- **`tools/cgroup-scope` has no selftest** (substrate's finding, about paperkit). Both paperkit
  fixes are warranted by comments citing a production run — testimony, not a gate. ⚑ Sharper in
  paperkit's own frame than in substrate's: it is the one paperkit tool exempt from paperkit's
  ⟨P, F, δ⟩ bar, and *the vendoring that stopped the fix flowing out also excused it from the
  importing repo's standards.*

  ⚑ **cassian named the mechanism this only described, and it is a SECOND argument for interning,
  independent of addressed-ness.** A vendored copy does not merely diverge — it **degrades**: it
  enters outside the intake, so it sits outside the bar, so it accumulates exactly the defects the
  bar exists to catch. Two paperkit fixes warranted by production anecdote rather than by an arm is
  what that looks like from inside.

  And it makes a **prediction about mtools**, which is the useful part: *any component landing in
  the union outside its gate will do the same thing.* Interning solves transmission (§4) and solves
  degradation only if the intern is gated on arrival. A shared directory of ungated files reproduces
  the vendoring defect at one remove.
- **A stale pointer in the census** — one filing cites `gate.py:273`; no such path exists (it is
  `paperkit/gate.py`). Trivial alone, and an instance of the rule these filings otherwise keep:
  quote the bytes, do not cite a coordinate into a moving target.

## 6. What a second-order pass is FOR, stated as a claim to be tested

The first-order filings agree substantially, and three of these repos share a lineage — linux-sources
forked paperkit's verb model, cassian ported from linux-sources. **Agreement among them is
inheritance and corroborates nothing.** What the reconciliation actually bought:

1. **Contradictions**, which locate an error in at least one filing by construction.
2. **Re-derivation of a headline claim on the claimant's own evidence** — paperkit's "zero hits
   across substrate's history" was paperkit's grep on substrate's tree, and it should not have stood
   until someone else ran it. It survived; that is the point.
3. **An error found in a filing that would damage the repo acting on it** (§3), which no
   self-audit could reach, since substrate would have been checking its own wording against itself.

⚑ The disposition column in paperkit's revised first-order §6 — MOVE / RECONCILE / LEAVE for each
divergence — is likewise not producible by any single repo. Each of us can say what we changed; only
the union can say whether a change is domain-neutral enough to be the spine.

## 6a. ⚑⚑ THE FIRST LIVE TEST OF THE GATING FAILED ON IDENTITY

The census argued at length that the union must carry **instruments rather than conventions**
(§1), and that the intern must be **gated on arrival** (§5). `mdstruct` is one of two distributions
already sitting in mtools, so it is the first live test. It failed before any of the conditions we
had thought to specify.

**Two sessions measured "mdstruct" and each told the other it had not measured at all.** MEASURED,
five implementations under `~/github`:

```
substrate/scratch/mdstruct.py         --headers works;  `spans` exits 2
mtools/mdstruct/.venv/bin/mdstruct    `spans` works;    --headers → banner
substrate/.venv/bin/mdstruct          ModuleNotFoundError: No module named 'mikemol.mdstruct'
cassian-observability/scripts/mdstruct.py
cassian-observability/.precommit-staged/scripts/mdstruct.py
```

Paperkit told linux-sources their `--headers` invocation "does not exist"; linux-sources told
paperkit its figures "cannot have been produced by this tool." **Both were right about their own
binary and wrong about the other's, because both said `mdstruct` and neither said which.** Four
sessions produced findings about this tool and not one named a path.

⚑ **And substrate's venv carries a DEAD console script for the intern target** — verified here:
`substrate/.venv/bin/mdstruct` dispatches to `mikemol.mdstruct.cli:main` and dies. Installed
entry point, absent package. Within one repo the name resolves two ways and one is a corpse. That
is the symlink-adoption failure arriving through *packaging* rather than through a link.

⚑⚑ **The defect is in the distribution mtools is built around, not in a stray copy.** linux-sources
reproduced the apostrophe drop on *paperkit's* binary — `mikemol-mdstruct` itself — and paperkit
reproduced it independently on a minimal fixture:

```
## B with an apostrophe's mark      ← straight ASCII '   → DROPPED, silently
## D plain heading                                       → parses
# Root's span SWALLOWS the gap.  No diagnostic.
```

Two independent codebases, identical defect, identical shape. Neither of us claims which copy is
canonical or whether the bug is inherited or convergent — two samples and a hypothesis (pandoc
smart-quote normalisation putting U+2019 in the AST while the matcher compares raw source) is not
a lineage.

**So a fifth condition, and it is prior to the other four:**

> **An instrument must be identified by more than its name.**

Interning is not "move the good copy in." **Nobody has established which copy is good, and both
measured copies are broken the same way** — including the one whose entire purpose is reading
structure.

⚑⚑⚑ **And it is the same shape as the operator's constraint-profile correction, one domain over.**
There, five consumers were asked to measure "their" profile when all five share one host — five
reads of one `/proc/pressure` mistaken for five measurements. Here, five artifacts share one name
and four sessions measured "it" confidently. **In both cases the identity question is prior to the
measurement question, and in both cases everyone skipped it.**

## 6b. ⚑⚑ THE UNION'S BOUNDARY IS A SUBSTRATE QUESTION, AND IT REVERSES THE CENSUS'S READING

The census assumed the union's core is the cross-repo semaphore and the remainder is legacy. With
the operator's under-scoping correction (§4a-bis), three of four repos now reach coordination
through a shared Bazel executor — so the "core" is already served. That left a two-layer question
cassian framed: scheduler-coordinated for build actions, lease-coordinated for everything else.

**Paperkit's second layer is nearly empty.** MEASURED: 29 `local`/`toolchain`-tier checks exist,
but they are *still Bazel actions* — the scheduler coordinates them. The genuinely uncovered surface
is work outside the build graph entirely, and in paperkit that is **two pre-commit call sites**.

⚑ **Substrate's is the opposite, and I verified it rather than relaying it:**

```
substrate/.bazelrc       ABSENT
substrate/MODULE.bazel   ABSENT
substrate/WORKSPACE      ABSENT
substrate/BUILD.bazel    ABSENT
```

**Substrate has no Bazel at all** — not merely outside the shared executor, but outside the build
system that makes an executor a coordinator. And it invokes membudget from **31 files**.

⚑⚑ **So the boundary inverts.** The layer the census treated as *legacy* — lease-coordinated,
non-Bazel work — is substantially **all of substrate's**: a 3,598-module make-driven Agda tree,
interactive compiles, selftest arms. The layer it treated as the union's *core* is already served
by an executor three of four repos converged on, and the one repo that cannot converge is the one
that wrote the machinery.

That reframes every "substrate should adopt X" in this census. Substrate is not a laggard on the
shared executor; it is **structurally ineligible** for it, and the coordination it needs is exactly
the ledger the other three retired. paperkit's §3 "silent loss" and substrate's non-adoption are
not the same finding pointed two ways — they are two repos with genuinely different needs, and the
census flattened them because it assumed one coordinator for one host.

**What nobody has measured, and it would settle the union better than more argument:** substrate's
non-action surface — how much of those 31 call sites is work a scheduler could ever coordinate.
That is a measurement substrate can take and the rest of us cannot.

## 6c. ⚑⚑⚑ THE OPERATOR'S ACTUAL QUESTION: THE LEASE IS THE GENERAL SHAPE, NOT THE REMAINDER

§6b framed the second layer as *"work outside the build graph"* — the residue a scheduler cannot
reach. **That framing is backwards, and the operator supplied the correction:**

> "The whole reason I told you to collect information about membudget is because the lease-shape
> phenomenon generalizes very well to *multiple agents modifying the same tree, communicating to
> prevent each other from stepping on each other*. Granular lock-out/tag-out."

**Resource budgeting is one instance of the lease, not the lease's purpose.** A memory budget is a
lease over *bytes*; a load gate is a lease over *cores*; the thing the census spent four filings
auditing is one application of a mechanism whose general form is **mutual exclusion between
independent agents over a shared mutable resource** — and the resource that matters most on this box
is not memory or CPU. **It is the source tree.**

⚑ **And the census had the evidence in front of it, unrecognised.** MEASURED, this session's own
logs:

```
# message records across the project's whole transcript history, not one log file
grep "input dependency modified during execution"  →  91  (11 distinct days, 2026-08-22 .. 2026-09-05)
                                       pre-BES-cutover  41
                                      post-BES-cutover  50
```

⚑ **CORRECTED, and the first number was wrong in the direction that flatters nobody.** An earlier
`grep -c` over a SINGLE session log returned **3**, and that figure was relayed to all three peers
and adopted by two of them as "the strongest evidence in the corpus". Counted over the project's
full transcript history the real figure is **91 occurrences across 11 distinct days**. The
population was never one session; it was fourteen days of continuous operation. *A count is a claim
about a population, and I stated the query's reach as the world's* — [[declared-partial]], committed
inside the filing that indicts exactly that shape.

Every occurrence is **paperkit editing paperkit during paperkit's own build** — a single agent
colliding with itself. Scale that to four sessions
editing four repos on one host, each running gates over trees the others are also editing, and the
collision surface is not a corner case; it is the working condition.

⚑⚑ **The existing mitigation is a rule you can only obey by remembering it.** paperkit's memory
carries `dont-edit-during-build` — *"check `pgrep bazel` before ANY edit or use a worktree."* That
is precisely the form linux-sources' §7a predicts will fail closest to where it is stated, and it
did: three violations in one session, by the session that wrote the rule.

**A lease is the instrument that discharges it.** `pgrep` before an edit is a convention;
`with_lock(tree)` is a mechanism. The census's own strongest conclusion — *the union carries
instruments, not conventions* — points directly at this and the census never made the connection,
because all four filings had already accepted "membudget = resource governor" as the frame.

⚑⚑⚑ **This re-reads every finding above:**

- **The two-layer question dissolves.** It is not scheduler-for-actions and lease-for-remainder.
  The scheduler coordinates *actions against a capacity*; the lease coordinates *agents against a
  tree*. Different resources, both needed, neither a fallback for the other. Substrate's 31 call
  sites and paperkit's 2 pre-commit sites were the wrong measurement — the right one is how many
  agents can touch one tree at once, and on this box that is four.
- **The cross-repo semaphore was never the interesting capability.** Capability #1 in the census's
  own enumeration is *a global cross-repo semaphore over a cotype ledger*. The census read
  "semaphore" as resource admission. The ledger is a **claim registry** — `claim:<artefact>` as a
  named mutex — and that is the lock-out/tag-out primitive, sitting in the enumeration all along.
- **`mikemol-membudget` is the wrong name to intern it under**, which §4a-bis already flagged from
  the resource side. The mechanism is granular lock-out/tag-out over shared mutable state; memory
  budgeting is its first application, not its definition.

⚑ **The BES cutover does not close it — MEASURED, answering substrate's question.** The k8s
executor came up 2026-08-30T20:25Z. Corruptions **41 before, 50 after**. Remote execution moves
where actions *run*; it does not stop an edit from landing on the working tree Bazel is reading
inputs from. So the edit-during-execution class is **local to the tree, not to the executor**, and
LOTO needs to guard the working tree only — it does not need to reach into the executor. That is a
smaller and more tractable requirement than it looked.

⚑⚑⚑ **PAPERKIT DID NOT FAIL TO ADOPT THE LEASE. IT REMOVED ONE, ON PURPOSE, WITH A REASON.**
MEASURED — `git log` on `paperkit/gate.py:273`:

> `95d12ad 2026-06-27  Ζ·membudget: retire the membudget semaphore — Bazel's scheduler is the budget`

and the surviving comment, verbatim:

> `# memory (membudget retired: Bazel IS the semaphore — per-machine, no cross-repo flock).`

**That sentence is true on the axis it is about and silent on the axis that matters.** Bazel *is*
the semaphore for **actions contending for capacity**. It is not, and was never, a semaphore for
**agents contending for the tree** — and the parenthetical *"no cross-repo flock"* records the
removal of the only mechanism that was. The retirement is dated 2026-06-27; **50 of the 91
corruptions postdate it**, as does the whole BES cutover it anticipates.

⚑ **And the claim propagated.** It is quoted back in `docs/membudget-study.md` three times and
`docs/membudget-reconciliation.md` twice, each time as a settled finding. A correct statement about
one axis was carried forward five times as a conclusion about both — [[unmarked-premise]], with the
premise supplied by paperkit and confirmed back by the census.

⚑ **Paperkit is therefore not a non-adopter but a DE-ADOPTER**, which is a strictly stronger datum
for the interning brief: the mechanism was present, was judged redundant against a scheduler, and
the judgement was right about resources and wrong about artifacts. That is the orthogonality thesis
with a commit hash on it.

⚑ **AND THE DE-ADOPTION IS UNIQUE — MEASURED across all four, not asserted.**
`git log --all -i --grep=membudget --grep=semaphore --grep=flock --grep='claim:'`:

| repo | verdict |
|---|---|
| linux-sources | **nothing** — never held it (their own measurement) |
| substrate | only ever **extended** it (`membudget-otlp-emit`, `sched-commit`) |
| cassian | only ever **added** leases (`gate-parallel: RAII-by-liveness generalized into resource-lease`) |
| **paperkit** | **the only removal** (`95d12ad`) |

⚑⚑ **This splits a state all four filings had collapsed.** Every filing reported *never held it*,
*held and misapplied it*, and *held and deliberately removed it* as one category: "did not adopt."
A roster that cannot tell a **never-adopter** from a **de-adopter** cannot tell an **unrecognised**
capability from a **rejected** one — and those need opposite remedies. Naming fixes the first. The
second needs a **refutation of the stated reason for removal**, which for paperkit is one sentence
with a commit hash, and refuting it is cheaper and more durable than advocacy: *"Bazel IS the
semaphore"* is true of capacity, silent on artifacts, and **50 corruptions postdate it**.
(linux-sources' framing; their zero is compatible with "nobody needed it", paperkit's is not,
because someone evaluated it and said no.)

⚑ **linux-sources reports the dual, MEASURED on their side:** zero lock bindings anywhere, against
**eleven `.claude/worktrees/` copies** — *"isolation by duplication cannot express partial exclusion,
carries no holder identity, and has infinite TTL. A worktree is a degenerate lease."* Paperkit has
**3** worktrees and one real `fcntl.flock` (`setup/experiment.py:158`) plus a `flock -n`
single-instance guard (`scripts/regen_if_stale.sh:93`) — so the primitive is in the tree, used
twice, for everything except the tree itself.

⚑ **Cassian reached this independently and cut it sharper** (2026-09-05, direct message), and
their cut supersedes the "two layers, one capacity number" sketch both of us had been arguing:

> "A scheduler coordinates ACTIONS CONTENDING FOR CAPACITY. Lock-out/tag-out coordinates AGENTS
> CONTENDING FOR ARTIFACTS. Those are orthogonal — they do not compose into one capacity number,
> and no amount of shared-executor convergence covers the second."

Under that reading **my measurement above is right and answers the wrong question.** Narrowing
paperkit's uncovered surface to *two pre-commit call sites* measures resource-coordination residue.
Artifact-exclusion demand is a different quantity, and paperkit's is not two — it is every edit
made while any gate runs, which this session measured at three collisions.

⚑ **Substrate's mechanism already exceeds what the four of us improvised by hand today:** an
arbitrary tag with no pre-declaration (anything is lockable), RAII by holder liveness with no
TTL/heartbeat/second registry (a dying agent releases its lock-out), gc-before-believing-a-holder
(a crashed claimant cannot block successors), and three policies — block / NOBLOCK→exit 3 /
TIMEOUT→exit 3. The mtools write-coordination protocol we negotiated over hours *is* a hand-derived
lease protocol: disjoint subtrees per writer, one integrating owner per shared component. We
re-invented a worse version by messaging, because none of us recognised what we were building.

⚑⚑ **This is the strongest interning argument, and no requirement list in either order contains
it:** the LOTO case has the most consumers in this ecosystem — every multi-agent session, including
the four writing these filings — and **zero adopters**. It is not a fragmented capability. It is an
unrecognised one.

**What the census got right for the wrong reason:** everyone agreed the machinery is worth
interning. The stated reason was resource governance, which three of four repos have since routed
around via the shared executor. The real reason is a coordination problem that **grew** while the
audit ran — four agents, one host, four trees, and three measured collisions in a single session.

## 7. Caveats

- Cassian's and substrate's filings **grew during this pass** (12K→19K and 30K→39K). Every claim
  here is against a snapshot of documents under live revision, and some may already be corrected.
- Paperkit's own first-order filing has been amended in place: §6 revised for the mtools destination,
  the ceilings claim marked REFUTED, §5's mechanism replaced. A reader comparing this document to an
  earlier copy of that one will find the deltas rather than contradictions.
- Substrate's working tree carries ~790 lines of unstaged diff on `membudget`, so anything any
  filing says about the origin describes a tree being edited underneath it.
