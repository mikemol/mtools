# Operator directives — the membudget census, as PAPERKIT received them

⚑ **ID namespace: `PK-D<n>`** (paperkit directives). Renamed from a bare `P<n>`, which **collided
with `paperkit-third-order.md`'s `P1..P5` REQUIREMENT ids** — same prefix, two meanings, both in
this directory, both written by paperkit. Caught by `census-kit`'s postmortem, which recorded the
collision as *"one ID prefix meaning two different things across two documents … nobody has caught
the second."* Now caught, by its author. Directive ids here are `PK-D<n>`; requirement ids in the
third-order filing remain `P<n>`.

**What this is.** The companion to `OPERATOR-DIRECTIVES.md`. That file is linux-sources' compilation
from *their* transcript; this is the same census swept from **paperkit's** transcript
(`4ce41847-…jsonl`, `cwd=/home/mikemol/github/paperkit`). Verbatim, chronological, no paraphrase.

⚑⚑ **Why a second file rather than a merge, and it is a finding rather than a courtesy.** The two
sweeps do not agree, and *cannot*: **the timestamps are per-delegate receipt times, not send times.**

| directive | linux-sources received | paperkit received | Δ |
|---|---|---|---|
| kickoff | 15:38:11 | 15:39:10 | 59s |
| first-order order | 15:47:00 | 15:49:18 | 2m18s |
| second-order order | 16:08:48 | 16:08:59 | 11s |
| the shared-host constraint | 16:21:59 | 16:22:04 | 5s |
| the construction correction | 16:54:08 | 16:54:11 | 3s |
| consolidation | 17:13:34 | 17:16:41 | 3m07s |

**Neither column is the time the operator typed.** A merged file would have to pick one and would
silently assert a send-order the corpus does not contain. ⚑ *A broadcast to four delegates leaves
four different records of one event, and no delegate holds the original.*

**Counts differ too:** linux-sources lists 18 items (A0–A17); paperkit's window holds **15**.
Theirs includes an origin six days prior and two after paperkit's arc closed. **Neither is wrong.**

---

## The census-shaped defect in compiling this file

⚑⚑⚑ **A paperkit dispatch produced a 12-item account and reported it as complete.** Its exclusion
predicate was sound — `toolUseResult`, `isMeta`, `isCompactSummary`, cross-session, task-notification
— and **not one exclusion is retracted.** The *inclusion source* was wrong: it read only
`type: "user"` records.

```
attachment.type == "queued_command", attachment.origin.kind:   human 118 · null 167 · peer 54
```

**118 human turns invisible to it**, including the **first-order filing directive** — the instruction
that created a third of the files in this directory. It also reported two messages as NOT EXISTING
(the shared-host constraint and the shared-BES remedy) and closed with *"if a filing attributes
either to the operator, that attribution is not sourced from this session"* — inviting readers to
distrust correctly-sourced filings on the strength of an incomplete query.

⚑ **linux-sources hit the identical shape and says so** (their five `queued_command` items, *"a
prior dispatch missed them for exactly this reason"*). **Two independent sweeps, same blind spot,
same record type.** The correction generalises:

> **A negative finding counts only what the query could see. Before asserting an absence, enumerate
> the record types you did not read.**

The honest claim is *"no such message appears among `type: user` records"* — a statement about the
query. What was written instead was a statement about the operator.

**Two further traps, measured:** `origin` is nested **inside** `attachment`, not at top level (a
top-level probe returns zero and reads as confirmation); and `attachment.prompt` is a **list of
content blocks**, so a naive `str()` yields a dict repr that matches keyword searches on *field
names*.

---

## Predicate and coverage

**Three sources, stated as inclusions rather than as one-minus-exclusions:**

```
A  type=="user" AND no toolUseResult AND NOT isMeta AND NOT isCompactSummary
     AND no <cross-session-message> / <system-reminder> / <task-notification>     ->  842
B  type=="attachment" AND attachment.type=="queued_command"
     AND attachment.origin.kind=="human"                                          ->  118
C  none — the other 23 attachment subtypes were checked and carry no human turns
                                                                       TOTAL      ->  960
```

Of those, **15 fall in the census window** (2026-09-05 15:39–17:20). `isMeta` captures every
self-scheduled cron prompt machine-side, so no heuristic guessing was needed.

**Not searched:** other sessions' transcripts (the per-party files cover those); anything the
operator said outside a Claude session.

### ⚑⚑⚑ Window justification, and the antecedent probe that indicts it

**The window `2026-09-05 15:39–17:20` was set for convenience** — it is the dispatch-day arc — and
`census-kit` names that failure: *"a date bound chosen for convenience gets reported as a fact about
the subject."* Stating it, and running the antecedent probe the skill requires regardless:

```
human turns mentioning "membudget" BEFORE the window, same reader, same corpus:   11
                                                     spanning 2026-08-22 .. 08-25
```

⚑ **Fourteen days of prior operator statements about membudget, quoted in NONE of the sixteen
filings.** The postmortem records the origin directive as sitting *seven* days outside a window
nobody set; from paperkit's vantage the antecedents run to **fourteen days and eleven turns**.

Several are substantive design statements the census then argued about without them:

> `2026-08-24T23:34:32Z` — *"this is what membudget is **for**. It **constructs** the cgroup. Are we
> not running cell contents inside their own membudgets?"*
>
> `2026-08-24T23:36:25Z` — *"membudget is **supposed** to construct a cgroup for the thing it
> **wraps**, which makes that cgroup last precisely as long as the thing it wraps."*
>
> `2026-08-24T23:32:16Z` — *"bazel doesn't support memory **limiting**, though, which is what
> membudget guarantees."*
>
> `2026-08-24T15:06:48Z` — *"membudget now supports a 'wait until load average' flag. If you're not
> leveraging that, you ought to."*
>
> `2026-08-22T21:55:39Z` — *"See membudget."* (the earliest antecedent in this corpus)

⚑⚑ **The RAII-by-liveness property the census "discovered" and filed as `C`'s load-bearing element
is stated in the 23:36 turn, twelve days before the kickoff** — *"that cgroup lasts precisely as long
as the thing it wraps."* Four parties measured it independently, wrote it up as a finding, and none
quoted the operator saying it first. **The census re-derived its own premise and did not know it.**

⚑ And `23:32` answers the retirement argument directly: *bazel doesn't support memory limiting,
which is what membudget guarantees* — the exact axis-gap that `95d12ad`'s *"Bazel IS the semaphore"*
missed. The refutation the third-order filing built from commit archaeology was available in plain
prose, two days after the retirement, from the operator.

**These are ANTECEDENTS, not directives** — they are listed here as evidence about the window, not
appended to the directive list.

---

## The directives, verbatim

### PK-D1 — 15:39:10Z · `user message` · KICKOFF

> Dispatch a research agent to study membudget _in depth_. It's more than just memory and CPU. Also see how substrate, paperkit, linux-sources and cassian-observability is using the machinery. It's genericized. Or it's supposed to be. Ic an't tell how many times I've told all of you to improve on and genericize that machinery, and had you _not share the improvements back, or decide you didn't need the whole of the thing_. So it might be fragmented.

**DIRECTIVE.** Ordered the depth study; named fragmentation as expected and the cause as delegates not sharing improvements back.

### PK-D2 — 15:49:18Z · `queued_command` · FIRST-ORDER ORDER

> I want you, linux-sources, substrate, and cassian-observability to write your exhaustive findings re membudget into the mtools repo.

**DIRECTIVE.** Created the four base `<repo>.md` filings. ⚑ Arrived as a queued_command — a paperkit dispatch missed it entirely and reported a complete 12-message account without it.

### PK-D3 — 16:00:08Z · `user message` · SECOND-ORDER ORDER

> Time for a second-order report. Dispatch a research agent to read through all of the findings in /home/mikemol/github/mtools/findings/membudget and reconcile with your own.

**DIRECTIVE.** Ordered reconciliation against all filings in the directory.

### PK-D4 — 16:05:18Z · `user message` · interjection

> `The nine refusals are its own ratchet family — the same machinery offered as the union's domain-neutral spine.` This is why everything clean is being moved to a common repository; it's easier to clean up at that scale than at substrate's current scale.

**CONTEXT.** Answered the delegate's ratchet-family observation: cleanup is easier at the common repo's scale than at substrate's.

### PK-D5 — 16:08:59Z · `user message` · SECOND-ORDER, ALL FOUR

> I want cassian-observability, linux-sources, substrate and paperkit to all write their _second-order_ findings into the mtools repository, as files distinct from their first-order findings.

**DIRECTIVE.** Extended the second-order pass to every repo, as files distinct from the first-order ones.

### PK-D6 — 16:19:58Z · `user message` · SUBSTANTIVE — the axis history

> Some history on membudget and CPU vs memory PSI: Originally, memory _was_ the primary problem. Membudget helped. zram helped. zswap helped. By this point, CPU became the primary constraint, but membudget had the rigorous and reliable gating logic, so the proper move was for membudget to own the additional predicates.

**CONTEXT.** Memory was the original constraint; CPU became primary; membudget kept the gating logic, so membudget owns the added predicates.

### PK-D7 — 16:22:04Z · `queued_command` · SUBSTANTIVE — the shared host

> It's also worth pointing out that, to date, _all of the consumers of membudget run on the same physical host_. They all face the same environmental constraints, so any idea of "what does my load need" is ignorant of the dynamics of the environment in which they run.

**CONTEXT.** ⚑ THE CENSUS'S CENTRAL PREMISE. All consumers run on one physical host, so per-consumer load reasoning is ignorant of the environment. A paperkit dispatch reported this message as NOT EXISTING.

### PK-D8 — 16:25:19Z · `queued_command` · interjection — the shared target

> `"Bazel IS the semaphore" is true within one build and false across repos` Sortof. this is why I'm pushing evveryone to use the same BES/--config=remote target.

**CONTEXT.** Qualified the delegate's semaphore claim and named the remedy: one shared BES/--config=remote target. ⚑ Also reported as not existing.

### PK-D9 — 16:33:07Z · `user message` · THE REFRAMING

> `What stays irreducibly lease-shaped is work outside the build graph ` Actually, the whole reason I told to collect information about membudget is because the lease-shape phenomenon generalizes very well to "multiple agents modifying the same tree, communicating to prevent each other from stepping on each other". Granular lock-out/tag-out.

**CORRECTION.** ⚑ Reset the census. The lease-shape generalises to multiple agents modifying one tree — granular lock-out/tag-out. Retroactively made the resource axis one instance rather than the subject.

### PK-D10 — 16:50:00Z · `user message` · THIRD-ORDER ORDER

> Ok, I want you, cassian-observability, linux-sources and paperkit to file your third-order findings in /home/mikemol/github/mtools/findings/membudget. We're looking to evolve a common understanding of the capabilities of the tool and establish what a pushout looks like, so that all parties can cooperatively land their requirements into the commonly-managed tool, and so that all parties can cooperatively avoid stepping on each other at a fine-grained level.

**DIRECTIVE.** Ordered third-order filings and named the object: establish what a PUSHOUT looks like, so parties land requirements cooperatively and avoid stepping on each other.

### PK-D11 — 16:54:11Z · `user message` · THE CONSTRUCTION CORRECTION

> I said pushout, damnit, not pullback.

**CORRECTION.** ⚑⚑ Four delegates had computed a LIMIT and called it a colimit. Inverted the arrows: a pushout GLUES and grows, carries every leg's remainder, and admits nothing.

### PK-D12 — 17:00:10Z · `user message` · THIRD-ORDER RE-ISSUE

> Ok, I want you, cassian-observability, linux-sources and paperkit to file your third-order findings in /home/mikemol/github/mtools/findings/membudget. We're looking to evolve a common understanding of the capabilities of the tool and establish what a pushout looks like, so that all parties can cooperatively land their requirements into the commonly-managed tool, and so that all parties can cooperatively avoid stepping on each other at a fine-grained level.

**DIRECTIVE.** Byte-identical to 16:50, ten minutes later, after the correction. Preserved rather than deduplicated: the re-issue is what makes the correction legible.

### PK-D13 — 17:05:49Z · `user message` · AUDIT

> Audit your rewrites and finding documents for consistency, correctness and convergence.

**DIRECTIVE.** Ordered an audit of the rewrites and findings for consistency, correctness and convergence.

### PK-D14 — 17:09:02Z · `user message` · CONSOLIDATION

> `That gap is real but correct as-is — the second-order document predates the pushout directive entirely. It shouldn't carry a correction to a construction it never attempted; that would be backfilling history. The right fix is a forward pointer, not a retrofit.`

The fix is a fourth document _consolidating; we don't want to hold the retractions, we want to hold the results.

**CORRECTION.** ⚑ A REVERSAL. The delegate had argued for a forward pointer and against backfilling history; overridden — a fourth document holding RESULTS, not retractions.

### PK-D15 — 17:16:41Z · `user message` · NAMING

> I think your CONSOLIDATED.md needs to be paperkit-consolidated.md; everyone else's is <repo>-consolidated.md.

**CORRECTION.** Corrected `CONSOLIDATED.md` to `<repo>-consolidated.md`, matching the three peers. ⚑ The convention failure the third-order test predicted.

---

## What the record shows that the filings do not

⚑ **The entire census is 15 operator turns in 97 minutes** — roughly 2,700 characters producing
sixteen findings files across four repos. **The asks are thin and the outputs are thick**, which is
exactly the ratio that makes this file necessary: a reader of the consolidations cannot recover
which sections answer the original question and which answer its replacement.

⚑⚑ **Three of the fifteen are corrections that changed what the work WAS**, not refinements of it:

1. **16:33 — the reframing.** Before it, the census was auditing a resource governor. After it, the
   resource axis was one instance of a lock-out/tag-out mechanism. Every first- and second-order
   filing was written under the superseded reading.
2. **16:54 — the construction.** Four delegates had computed a limit (selection, admission bars,
   shrinking to an intersection) and called it a colimit. The correction inverted every arrow.
3. **17:09 — the consolidation.** The delegate argued for a forward pointer and against backfilling
   history. Overridden: hold the results, not the retractions. **The `-consolidated.md` files exist
   because that argument was rejected.**

⚑⚑⚑ **And 17:16 is the third-order test failing in the way it was designed to detect.** The test —
*if the four cannot land four contributions without a path split, a duplicated finding, or a
hand-negotiated convention, the third order failed* — was met by a naming divergence
(`CONSOLIDATED.md` vs `<repo>-consolidated.md`) that **the operator caught, not the mechanism.**
Two names for one intended slot, in the directory whose census argues that shared trees need
mechanised naming. `PK-D2` is confirmed load-bearing by the failure.
