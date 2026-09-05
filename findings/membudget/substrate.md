# substrate's membudget findings

**Author:** substrate (owner-of-origin for the `membudget` capability; summit `owner = substrate`)
**Occasion:** the operator's grievance — *"It's more than just memory and CPU. It's genericized. Or
it's supposed to be. I can't tell how many times I've told all of you to improve on and genericize
that machinery, and had you not share the improvements back, or decide you didn't need the whole of
the thing. So it might be fragmented."*

Every figure here names the command that produced it. Where a claim is a reading rather than a
measurement, it says so.

---

## ⚑⚑⚑ BIAS AND BOUNDS — read before anything below

**Substrate is the origin and the largest offender in this audit.** Two counts, both in §0. This
document is written by the party whose stale authority misled the consolidation session, so weight it
accordingly.

⚑⚑⚑ **AND A THIRD ROLE THIS DISCLOSURE ORIGINALLY OMITTED, ADDED AFTER A SECOND-ORDER AUDIT NAMED
IT: SUBSTRATE ACTED AS REFEREE FOR THE OTHER THREE FILINGS.** Every contested claim in this census
was settled by a probe substrate ran, on substrate's tree, and the other filings accepted the result
— linux-sources struck a finding *"REFUTED by substrate, who ran the probe"*; cassian recorded
*"substrate then showed my reproduction is unreachable in its tree."* The audit found substrate was
right each time. **The process shape is the finding anyway:** a reconciliation reading these four
cold would conclude *remarkable convergence*, when the correct conclusion is **convergence through a
hub that is also a party.**

⚑ **Declaring yourself the defendant while acting as the judge is exactly the bias that reads as
humility**, and "largest offender" does not cover it. Agreement between substrate and any other
filing should be treated as weak corroboration by default. ⚑ Only two claims in this document survive
as genuinely decorrelated: cassian's independent re-implementation of the four lease mechanics (§3),
and the swap.max/FAILS-GREEN class (§7) — the latter derived from a local bash measurement here and a
Kubernetes pod-limit encounter there, different substrate and different tooling.

⚑⚑⚑ **AND THE COROLLARY, FOUND INDEPENDENTLY BY BOTH SECOND-ORDER AUDITS: THIS CORPUS'S EVIDENCE
HIERARCHY INVERTS ITS CONFIDENCE.** The claims stated most emphatically across the most filings —
packaging-is-the-root-cause, reports-travel-but-edits-don't, consumer-liveness — are the LEAST
independently supported: one measurement plus relays. The claims with genuine decorrelated witnesses
— the pool/N-member collapse, refuse-never-best-effort, the four concurrency mechanics — are each
stated once, calmly. **Repetition across files tracked MESSAGING TRAFFIC, not evidence. A reader
counting file-agreement would rank this corpus almost exactly backwards.**

⚑ **The discriminator is chronological and it is cheap to apply: the strongest agreements PREDATE the
messaging.** The pool collapse and refuse-not-best-effort converged because both artifacts existed
before the audit began. Everything that converged DURING the audit is one source with relays.

⚑⚑ **AND THE SINGLE MOST LOAD-BEARING CLAIM IN THE CORPUS HAS EXACTLY ONE MEASUREMENT.** The
packaging root cause (§6) — the entire justification for interning, which three of four filings build
on — rests on linux-sources' reading of `SOURCES.txt`. Cassian's agent has since verified it TRUE
(133 entries, all `.py`, `membudget_otlp.py` the sole membudget-family file). **But three sessions
asserted it without checking, and this filing was one of them.**

⚑⚑ **AND THIS DOCUMENT COMMITTED ITS OWN HEADLINE DEFECT.** §1's predicate table originally read
`min(5m,10m)` for the load gate. The code reads **`_l15`** — `membudget:507` binds `_l1 _l5 _l15` and
`:511` takes `min($_l5, $_l15)`. **Linux publishes no 10-minute average**, so the figure was never
implementable; it was transcribed from the source COMMENT rather than the code. **In the document
whose §0 thesis is that substrate's own authority went stale, in a table captioned as measured by
reading the source whole.** Caught by linux-sources, not by substrate. Corrected above.

⚑⚑ **AND THE TREE THE OTHER THREE REPOS AUDITED IS UNCOMMITTED.** Measured, after paperkit raised it:

    git status --short scripts/membudget scripts/membudget-ledger scripts/cgroup-scope
       M scripts/cgroup-scope
       M scripts/membudget
      ?? scripts/membudget-ledger

    git diff --stat scripts/membudget scripts/cgroup-scope
      861 insertions(+), 182 deletions(-)

**`scripts/membudget-ledger` — the file this entire audit quotes as "the ledger format is the
contract" — is UNTRACKED.** It exists only in substrate's working tree. So every finding the other
three repos reported about substrate is a snapshot of a tree that is being actively edited and that
nobody can fetch.

⚑ **That is not a caveat on the findings, it is one of them.** A peer auditing substrate's membudget
today is auditing something with no commit to cite, which is the same discovery failure as the
gitignored inbox (§5) one layer down: the artifact exists, is authoritative, and is unreachable by the
normal channel. **It also means substrate cannot honestly ask anyone to intern this code until it is
committed.**

⚑⚑ **AND THE REASON IT IS UNCOMMITTED IS NOT NEGLECT — IT IS A GATE SURFACE NOBODY HAD SURVEYED
WHOLE.** `python3 -m substrate.commit_refusal`:

    295 path(s) staged
      9 gate(s) WOULD REFUSE this commit
     28 UNMEASURABLE — no verdict, NOT clean
      0 VACUOUS

The nine are real accumulated debt (ban ratchet, claims, rederive, discharge, sumtype, public, mode
contracts, divergence, tool-mode census). **The twenty-eight are NOT a claim those gates are broken.**
`verdict`'s own docstring says it *"asks each authority rather than executing"*, so UNMEASURABLE means
this reader declined to run a gate that writes on a bare invocation, exposes no `census()`, or will
not import under a bare name. **The tool renders it as NO VERDICT, NOT CLEAN — and that is the honest
reading: nine known-red, twenty-eight unknown, zero measured-green.**

⚑ Nobody had assembled this because the question was always asked one gate at a time. It is the
substrate-side answer to "why is nothing committed."

⚑⚑⚑ **AND THE CONCLUSION DRAWN FROM IT HERE WAS WRONG — CORRECTED BY THE OPERATOR.** This section
originally read *"substrate is reporting on machinery it cannot currently ship"*, and a companion
finding held that the nine refusals are substrate's own ratchet family, so **the thing substrate
proposes to contribute is the thing preventing substrate from shipping the contribution.** Cassian
sharpened it further as *"the union's spine cannot be fetched, cannot be committed by its owner, and
the blocker is the spine itself."*

**Both of us read a MOTIVATION as a BLOCKER.** Operator, verbatim:

> *"This is why everything clean is being moved to a common repository; **it's easier to clean up at
> that scale than at substrate's current scale.**"*

**The debt does not have to be paid where it accumulated before the machinery can move.** The nine
refusals are debt measured at SUBSTRATE'S scale — a large tree with years of accumulation, where
paying down the ratchet means cleaning everything the ratchet covers. **Substrate does not need to
ship its whole tree; it needs to ship the clean parts, which is what mtools is for.** The machinery
moves as the clean components; the debt stays with the tree that generated it.

⚑ **So this measurement is evidence FOR the consolidation, not a constraint on it** — it measures the
scale at which cleanup is currently being attempted, and that scale is the wrong one.

⚑⚑ **AND IT SETTLES THE ONE OPEN FORK THIS DOCUMENT FLAGGED** (§9, whether mtools inherits
substrate's baselines or starts at `--init-absent`). **It is `--init-absent`, for a positive reason
rather than a hygienic preference:** mtools starts from a CURATED CLEAN SET, so zero-tolerance is the
honest birth state — there is no legitimate debt to grandfather. Inheriting substrate's baselines
would import the very debt the move exists to escape, and would do it **silently**, since a baseline
is precisely the mechanism that renders existing debt invisible. **If a component cannot land clean
under `--init-absent`, it is not yet clean enough to move — which is the selection criterion,
mechanized.**

⚑ **What survives unchanged:** `git log --all --oneline -- scripts/membudget-ledger` is EMPTY — the
file every filing quotes as the contract has never been committed on any branch. Not a blocker under
this framing either, but a real constraint on the union's PROVENANCE: **whoever interns the ledger
format is transcribing from an uncommitted working tree and should say so in the interned artifact**,
rather than presenting it as a port of a shipped thing.

---

## 0. The headline: substrate is a party to the grievance, twice

Before the fragmentation map, the part that is substrate's own fault, because it is what misled the
consolidation session and this whole audit.

**⚑ Substrate generalised its own machinery twice and never updated its own designated authority.**
`.claude/skills/build-system/SKILL.md` is the gated census that `CLAUDE.md` orders every reader to
consult *instead of* quoting figures: *"Do not quote a cap, a lease default, or a build figure from
this file — ask the oracle."* That skill describes membudget as a **memory lease only**. Neither the
load gate nor the claim gate appears in it. The `build-oracle` agent's own description calls
membudget *"the RAM semaphore and its cgroup leases."*

So a reader who **obeys the repo's own routing rule** gets the memory-only answer. That is exactly
what happened: substrate reported to `mtools-2c` that *"membudget is scalar all the way down, the
label is free text, there is no membership"* — and steered them away from membudget toward the
ratchet, on a question (keyed membership claims) that **membudget's claim gate already answers**.

⚑ **And substrate has the mechanism to prevent this and did not apply it here.** The census-sync gate
family — `build_census.py --check`, `sql_lift.py --check-census`, `toolmodes.py --check` — exists
precisely so a generated authority cannot drift. Three instances of the pattern, and the one that
misled a peer is not covered by any of them.

**Second count:** `suite_claims.py` writes down the pool generalisation as a comment — *"`pg` IS THE
DEGENERATE CASE OF A POOL… a lease over a SET of N slots rather than an exclusive lock — the same
machinery at |members| = N"* — and cassian **built** it independently as `scripts/resource-lease`.
Substrate wrote the design down; a peer built it; neither told the other.

---

## 1. What membudget actually is — three predicates, not one

Measured by reading `scripts/membudget` and `scripts/membudget-ledger` whole.

`cmd_run` evaluates **three admission predicates in one loop**:

| predicate | kind | resource | on contention | disable |
|---|---|---|---|---|
| RAM budget | quantitative, summed | MB vs `TOTAL_MB` | BLOCK; **REFUSE (3)** if request > TOTAL | `MEMBUDGET_NOBLOCK` / `_TIMEOUT` |
| load gate | quantitative, box-wide | `/proc/loadavg` 1m **and** min(5m,**15m**) vs `nproc × MEMBUDGET_MAXLOAD` | BLOCK only | `MEMBUDGET_MAXLOAD=0` |
| **claim gate** | **nominal, KEYED** | **an arbitrary named artefact** | BLOCK on the live holder | `MEMBUDGET_NOCLAIM=1` |

The claim gate keys on the ledger's **label** field (field 7):

    membudget:560
      _held=$(awk -v l="$label" '$1=="LEASE" && $7==l {print $4; exit}' "$FILE")

with an authoritative re-check inside the lock before the append — a real mutex, not check-then-act.

`membudget:541`: *"THE `claim:` PREFIX IS NOT A NAMING CONVENTION, IT IS WHAT THIS PREDICATE MATCHES
ON."*

**In production on a non-memory resource.** `substrate/suite_claims.py` opens: *"Which artefact a
suite must hold exclusively."* `claim:pg` guards the single postgres (several suites open it; enough
concurrency caused kernel hangs); `claim:roster` guards suite-runner recursion.

⚑ **So "it's more than just memory and CPU" is accurate and already partly built.** What is *not*
built: the quantitative axis is hardcoded to MB. There is no resource-type parameter. Adding a second
countable resource means editing `cmd_run`, not configuring it.

### The generic form, stated in the source

`membudget:528-532`, at the claim gate:

> *"WHY IT IS HERE AND NOT IN A NEW TOOL. `MEMBUDGET_MAXLOAD` is the precedent: a predicate that is
> neither a lease nor a label, evaluated in this same loop, which inherits the wait, block-vs-refuse,
> `MEMBUDGET_TIMEOUT`, the announce-once line and the `=0` disable FOR FREE rather than growing a
> second, subtly-different version of each. An exclusion built beside this loop would have
> reimplemented all five."*

**membudget is an admission loop with pluggable predicates.** That is the generic machinery,
understood by whoever wrote that comment, never lifted into a named parameterised interface and never
propagated to the docs.

---

## 2. The ledger contract, and what `<parent>` is not

    membudget-ledger:19
      LEASE <id> <mb> <pid:starttime> <epoch> <parent|-> <label>
      TOTAL_MB <n>

**`<parent>` is a LIFETIME edge, not an allocation edge.** From the header `ensure()` writes into
every new ledger:

> *"Child allocation is DISJOINT from parent allocation: a nested lease draws from the GLOBAL budget,
> not its parent's mb — **parentage governs cascade-GC, never the pool**."*

`gc()` cascade-drops a lease whose parent vanished (`membudget-ledger:113`). That is all parentage
does.

⚑ **This refuted a hypothesis worth recording**: cassian proposed that the genericization might live
in `<parent>` as a sub-allocation edge (the RCS/CVS shape). It does not. Refuted by the artifact's own
header.

**`gc()` DELETES, it does not mark.** `membudget-ledger:104-123` — dead-owner and vanished-parent
lines are `continue`d, never written to `$tmp`, then `mv` replaces the file. No tombstone. So the
`cotype` in the header is **not** cassian's charter sense (monotonic, deletion-forbidden,
supersession-to-Residue). What substrate means by `cotype` here is still unestablished.

---

## 3. COMPLETE / PARTIAL / KNOWN-DEFECTIVE — substrate's honest declaration

Requested by cassian as an alternative to handing over a whole-cloth schema. This is what substrate
believes about its own copy.

**COMPLETE — would stand behind interning as-is.** The lease mechanics:

- the lock is held on an **fd that never crosses a fork**, so the kernel death-releases it on any
  signal — there is no userspace cleanup to be skipped. The comment records the incident: *"a killed
  holder's lock once stayed held by a child's copy → cross-repo deadlock."*
- **liveness is `pid:starttime`** (field 22 of `/proc/pid/stat`), so a recycled PID cannot keep a dead
  lease alive
- **gc-on-death**, so a failed release never leaks budget permanently
- **acquire is bounded** (`flock -w`, default 10s) — and because a dead holder auto-releases, *"a
  timeout can only mean a LIVE, wedged holder"*
- **critical sections are pure file-IO** — never fork/sleep/wait under the lock

⚑ These now have a **second, decorrelated witness**: cassian's `resource-lease` re-implemented all
four independently and credits them (*"the concurrency discipline is membudget's, reproduced here"*).

**PARTIAL.** The resource model. The quantitative axis is MB-only, with no resource-type parameter.
`cgroup-scope` accepts `--cpu-weight` and membudget never passes it — a plumbed dimension with no
caller.

**KNOWN-DEFECTIVE.**

- **The ceiling POLICY.** `AGDA_MB_MAX=384` is marked **UNRESOLVED** in the source: *"a number that
  works for this repo, not a number with a reason."* The mechanism is fixed (see §5); the value is not.
- **The live ledger's header is the retired model.** `ensure()` writes correct text but **only on
  creation**, so an existing ledger is never migrated. The operator's live
  `~/.cache/membudget/budget.cotype` line 2 reads *"a nested lease draws from its PARENT's mb"* — the
  pre-2026-08-05 design, contradicting the code. `membudget-shrc` carries the same retired claim.
- **No call surface.** See §6; independently evidenced from two directions.

---

## 4. The fragmentation map — four shapes, six repos

| repo | relationship | state |
|---|---|---|
| **substrate** | origin, sole implementation | generalised twice, told nobody — including its own authority |
| **paperkit** | vendored the cgroup slice, **improved it** | 2 fixes substrate lacks; lease layer *deliberately* retired ("Bazel IS the semaphore") |
| **mat230** | vendored, **rotted** | 4 files stale; ⚑ **repo is RETIRED** — see §7 |
| **mat260** | consumer, no copy | discovery logic **triplicated**; foreclosed by the ceiling |
| **cassian** | no code; **built the third case** | `resource-lease`; wrote down "offer back to substrate" and never sent it |
| **linux-sources** | **abstained entirely** | zero references; OOM'd this box today under the scenario membudget prevents |

⚑ **Two of these repos — mat230 and mat260 — were unknown to the three sessions coordinating this
audit until the census found them.**

### Improvements stranded downstream (owed to substrate)

- **paperkit's UUID scope naming.** Substrate builds `NAME="${NS_PREFIX}$$-$(date +%s)-${RANDOM}"`;
  bash seeds `$RANDOM` from pid+time, so two cells in the same second with the same pid collide.
  **Measured in paperkit production: a 24,376-action run died on `mkdir … .scope: File exists`.**
  Their fix reads `/proc/sys/kernel/random/uuid` and **preserves the `<pid>-<birth>` fields because
  substrate's reaper parses them by field.** Substrate is still exposed.
- **paperkit's OOM discriminator**, keyed on the cgroup `memory.events` `oom_kill` **increment**
  rather than exit `137||143`, which is ambiguous for any SIGKILL. ⚑ **`oom_kill` counts PROCESSES
  and `oom_group_kill` counts EVENTS** (`paperkit/tools/cgroup-scope:321`) — which is WHY the test
  must be an increment rather than a magnitude: under `memory.oom.group=1` one event raises
  `oom_kill` by the whole tree size. **This bullet stated the counters inverted until paperkit
  caught it; see §5a.**
- **paperkit's climb ladder** — 10 attempts doubling `memory.max` per OOM to `CLIMB_MAX_MB=4096`,
  where **only an OOM climbs** (a payload failing for its own reasons must not be retried).
- **paperkit's REPLACEMENT of the load predicate** — `tools/cpuweight.py` reads
  `(procs_running / cores, procs_blocked)` from `/proc/stat`, explicitly *not* loadavg. A third
  unshared improvement, recorded by no filing until the second-order pass.
- **cassian's pool case** (§8), its CPU-time integral bound, and its which-cap-bound fence reporting.

⚑ **paperkit's diff is ADDITIVE UP TO THREE SUPERSEDED LINES** — 3 dropped, 82 added, and the three
dropped are superseded rather than lost. ⚑⚑ **This bullet read "PURELY ADDITIVE — substrate has zero
features paperkit's copy lacks" until linux-sources' audit caught the pattern: this document hedges
in prose and drops the hedge in tables and headers, which are what a reader quotes.** The unhedged
form is the one that travels.

INFERRED (flagged by the reporting session): paperkit did not vendor substrate's `cgroup-scope`
selftest family, so their improvements are validated only by production measurements cited in
comments. **If substrate takes them, take them with tests.**

---

## 5. The mat260 letter — a consumer foreclosed, and the fix that flowed while the adoption did not

`scratch/inbox/2026-08-14-mat260-membudget-correction-landed.md`, ⚑ **in the GITIGNORED inbox**
(`scratch/inbox/` is the registered `listens` path and is gitignored per summit's own ruling). A peer
followed the registry and delivered where git cannot see; the letter sat for three weeks.

mat260's corrected filing:

> *"`cap` clamps unconditionally and 384 < 600, so **no successful climb can ever reach this
> consumer**. A failed climb is a condition you can retry into; **a ceiling below the requirement
> forecloses the class**."*

And: *"the ceiling has now been justified from a **stale premise twice** — the first time it
misdescribed itself, the second it locked out a downstream consumer."*

Their second filing, kept rather than withdrawn because the shape is the useful part:

> *"`AGDA_MB_DEFAULT=1024` is returned early, before the ledger lookup, so it covers run 1 and is
> silently defeated the moment history exists. **A knob consulted only on the path where it is not
> needed reads as a fix for exactly as long as nobody measures the second run.**"*

⚑ **They declined to propose a number**, and the reasoning is the discipline the ceiling still needs:
*"I am one consumer with one corpus, and a ceiling picked to fit mat260 would be the same defect with
a different constant."* What they asked for instead: **observability** — *"the current failure is
silent in both directions: the seed stops mattering without saying so, and the clamp does not report
that it clamped."*

**Substrate DID absorb the mechanism fix** — an explicit `AGDA_MB_DEFAULT` above the ceiling is now
honoured rather than clamped, any clamp is LOUD and names `AGDA_MB_MAX`, and `cmd_verify_ceiling`
asserts both arms as an executable contract. **The fix flowed; the adoption did not** — mat260 still
holds three divergent copies of its discovery logic.

**And `summit capability membudget` shows `question-owner-cap-is-a-consumer-bound` filed BY
SUBSTRATE.** Substrate raised the question, received the correction, fixed the mechanism, and left the
policy unresolved.

---

## 5a. ⚑⚑ THE MECHANISM: reportable travels, vendored does not

Paperkit's framing, and substrate CONFIRMS it — it is the best explanation anyone produced for why
the fragmentation has the shape it does:

> **Written reports through summit travel reliably; edits inside vendored files never do.**

**The counter-example proves it rather than weakening it.** The `AGDA_MB_MAX=384` ceiling that locked
out mat260's 600MB modules **did** flow back and became `cmd_verify_ceiling`, a permanent selftest.
It travelled *because it was reportABLE* — mat260 wrote it as a floor entry with a claim and a
witness. **A vendored edit has no moment at which sharing becomes the obvious next action.**

⚑ Substrate can add the confirming pair from its own side: the OTLP `vm_rows_inserted_total`
correction travelled to cassian within the hour and was credited, because it was a REPORT. Paperkit's
uuid fix and oom_kill discriminator, made the same month, are still only in paperkit — because they
were EDITS.

**So the packaging root cause (§6) and this are one mechanism seen twice.** No call surface forces
vendoring; vendoring produces edits; edits have no reporting moment. **Interning does not merely
deduplicate the code — it converts every future improvement from an edit into a change against a
shared artifact, which is the only form that travels.**

### Two paperkit fixes substrate has never had — verified against substrate's whole history

    git log --oneline -S 'uuid' -- scripts/cgroup-scope   → (empty)

- **Scope-name collision.** Substrate still builds `${NS_PREFIX}$$-$(date +%s)-${RANDOM}`. Paperkit
  measured `mkdir … File exists` at ~1 in 24,000 actions and moved to a uuid, **preserving the
  `<pid>-<birth>` fields because substrate's reaper parses them by field.** Substrate is exposed
  today.
- **The OOM discriminator keys on `memory.events`' `oom_kill` counter, not the exit code.** ⚑ **This
  is strictly better than substrate's own reasoning, and substrate's comment CONCEDES the weakness** —
  `rc=137` alone is ambiguous for any SIGKILL. **The origin holds the weaker form of a decision the
  fork already got right.**

  ⚑⚑ **AND THIS ENTRY ORIGINALLY INVERTED THE COUNTER SEMANTICS, WHICH WOULD HAVE CORRUPTED THE PORT.**
  It read *"the counter tracks events rather than processes."* Paperkit's source says the opposite, at
  `tools/cgroup-scope:321`: *"⚑ INCREMENT, never a delta SIZE: **`oom_kill` counts PROCESSES,
  `oom_group_kill` counts EVENTS**, so a group OOM (kubelet sets `memory.oom.group=1`) raises
  `oom_kill` by the whole tree size."*

  **That direction is why the fix is an INCREMENT test** — read before, read after, compare — rather
  than a magnitude comparison. Under `oom.group=1` one event raises `oom_kill` by N processes, so a
  magnitude test reads noise and only the delta means anything. ⚑ **Porting from this filing's
  original wording would have produced a check that looks right and measures the wrong quantity.**
  Take the code, not anyone's prose about the code. Caught by paperkit.

- ⚑ **A THIRD unshared paperkit improvement, recorded by no filing until now: paperkit REPLACED the
  load predicate.** `tools/cpuweight.py` reads `(procs_running / cores, procs_blocked)` from
  `/proc/stat` — its docstring: *"`procs_running` counts tasks that want CPU NOW. It is NOT loadavg:
  the 1-minute average is decayed … and counts D-state as runnable."* **That is the sharper predicate
  substrate's own comment concedes it lacks** (*"A PSI-based predicate would be sharper"*). So the
  count of unshared paperkit improvements is **three**, not two: uuid naming, the oom_kill-increment
  climb, and the contention predicate.

### And a correction to a premise, which is the ecosystem's problem in miniature

Paperkit briefed their own study saying their `cgroup-scope` (333 lines) was a SUBSET of `membudget`
(860) and asked what the missing 527 lines cost. **Their study refuted it:** paperkit forked
`scripts/cgroup-scope` (251 lines) and is a **SUPERSET** — 3 lines dropped, 82 added. `membudget` was
never adopted at all, and that non-adoption is recorded in `paperkit/gate.py` rather than silent.

⚑ **A plausible size delta was read as a subset relationship.** Two files, two line counts, one
inferred containment — and the inference was backwards. Substrate committed the identical shape in
§10 and in the mat230 chain (§7). **Comparing artifacts by magnitude instead of by content is the
audit-level form of the count-is-a-fact-about-the-query defect.**

### Three more from the fleet census, recorded not yet verified here

⚑ **Flagged as UNVERIFIED by substrate** — reported by paperkit and linux-sources, not re-measured
here, and a peer's verdict is a hypothesis:

- **The load-gate predicate exists in three repos with three different ceilings** (10 / 10 / 1.0).
  One predicate, three policies, no shared authority.
- **linux-sources fixed a measured 33-minute livelock** whose shape substrate's unbounded `sleep 5`
  loop still has. A liveness floor exists in exactly one tree.
- **cassian's `resource-lease` offers itself back to substrate IN WRITING** — its own header says
  *"a candidate to offer back to substrate via summit since membudget is theirs"* — and the offer was
  never sent. Cassian surfaced this against themselves before anyone else found it.

---

## 6. The root cause is PACKAGING, not discipline

The strongest framing produced in this audit, from linux-sources' census:

`substrate_tooling.egg-info/SOURCES.txt` ships **`.py` only**. Of the whole membudget family, only
`membudget_otlp.py` is packaged. **The ~1,300-line bash core is structurally undistributable.**

That single fact explains all three consumption shapes as one cause rather than three lapses:

- **mat260** does path archaeology to locate a live `membudget` and shells out → triplicated
  discovery logic in `tools/agda-safe`, `tools/jea_gate.py`, `build.sh`
- **paperkit** could only vendor the cgroup slice
- **cassian** re-ported rather than importing

mat260 said it to paperkit directly: *"membudget has **NO CALL SURFACE** — the fix belongs upstream
with you, not in a fourth copy."*

⚑ **So `mikemol-membudget` removes the CAUSE rather than the symptom, and mtools already reserves the
name** (`mdstruct/pyproject.toml` names it as a planned sibling distribution in a dependency-isolation
rationale). This is the strongest interning candidate in the fleet.

---

## 7. A defect chain that held at three links and was still wrong

⚑ **Recorded because the miss is worth more than the finding was.**

Substrate escalated mat230's vendored `cgroup-scope` as the audit's highest-priority item: it does
`echo 0 > memory.swap.max 2>/dev/null || true` where substrate `_die`s, and substrate's own header
carries the measurement — `swap.max=max → rc=0, oom_kill=0` versus `swap.max=0 → rc=137, oom_kill=1`
on identical bytes. So a scope can be handed back that **looks capped and cannot kill**, and any OOM
ladder keying on 137 reads success.

Three links, all sound:

1. substrate **measured the mechanism**
2. substrate **verified the code divergence**
3. cassian **verified the host precondition** — 32G swapfile + 9.2G zram at 9.0G used, and the
   operator confirms *"this host is DESIGNED to swap. It uses zram and zswap"*

**Nobody checked whether the consumer was in service. mat230 is retired.**

⚑ **The honest audit chain is FOUR links, and the fourth is CONSUMER LIVENESS.** "The code is wrong +
the host qualifies" does not establish a live failure. A vendored copy in a repo nobody runs is a
hygiene item; the same copy under load is an incident; **the diff looks identical.**

What survives regardless: **the canonical form must REFUSE when `swap.max` cannot be written, never
tolerate.** Cassian reached that independently from their own k8s encounter (*"a pod's memory limit is
a HARD ceiling only with swap.max=0 … cgroup-scope FAILS GREEN"*) — two repos, no shared derivation,
so the class is structural.

And mat230's copy does not merely fail: its v1 arm carries `# swap off => cap is RSS` — **a stale
premise stated as a fact, inside the file whose job is to make the cap real.**

---

## 8. Two cases, not three — and substrate's is the under-specified one

Cassian mapped the design space as three allocation shapes; testing substrate's claim gate against it
collapses two of them.

1. **divisible scalar** from a global total — membudget `<mb>`
2. **exclusive named** resource — membudget `claim:<artefact>`
3. **one interchangeable member** of a finite set — cassian `resource-lease` (ports 18000-19999)

**Case 2 IS case 3 at N=1.** `membudget:560` matches `$7==l` on the exact label and acquires when no
holder exists; nothing requires the name to be pre-declared or to belong to a set. **The artefact name
IS the member, and the pool is `{that one name}`, discovered at use.**

⚑ **And the asymmetry runs against substrate.** `resource-lease` has an **enumerated** pool, so
"no member free" is decidable and gets its own exit code, distinct from usage and unknown-pool errors.
Substrate's claim pool is **implicit** — the member set is whatever callers happen to name — so:

- **a typo'd `claim:pgg` silently acquires a fresh single-member pool and excludes nothing.** There is
  no unknown-pool error and there cannot be: an implicit pool cannot distinguish a new member from a
  misspelt one.
- exhaustion is not distinguishable from contention (they coincide at N=1; the gap becomes real at N>1)

**So the union should take the ENUMERATED pool as the general form**, with substrate's implicit-name
claim as the special case that trades declarability for convenience — and the trade costs the typo
check. That is the opposite of what substrate's copy suggests in isolation, where accepting any name
reads as the more general behaviour.

⚑ Substrate's own `suite_claims.py` names the collapse from the other side: *"`pg` IS THE DEGENERATE
CASE OF A POOL … the same machinery at |members| = N."*

---

## 9. Constraints the union must answer

**The churn constraint — "make it a cotype" is not a free improvement.** From
`membudget-ledger:120-122`:

> *"Rewrite ONLY when this pass actually dropped a lease. Rewriting unconditionally turned every gc
> into a ledger-change event → woke every blocked waiter → each ran gc → rewrote again: a self-feeding
> churn storm that **saturated the GLOBAL lock and starved other repos**."*

An append-only ledger over a machine-global lock trades a GC pass for a wake-storm **unless the notify
path is decoupled from the write path**, because every append IS a change event. And an enumerated
pool of N members has N times the append rate of a single claim — so the problem gets harder exactly
as the general form is adopted.

**The ledger is machine-global with NO repo component.** `$HOME/.cache/membudget/budget.cotype`, one
file, one `TOTAL_MB` across every repo. That is by design and it works — commit `7c61738f4` records
the cross-repo starvation incident and its architectural fix, verified under a concurrency harness at
*"100/100 cross-repo lock-free, 0 ledger churn."*

⚑ **But the label namespace is machine-global too.** A `claim:pg` from substrate and a `claim:pg` from
another repo mutually exclude — correctly or catastrophically depending on whether they mean the same
postgres. **Nothing namespaces a claim by repo**, and the design has not faced this because substrate
is the only claimer. **For a multi-writer intake this is the first thing a convention must settle.**

**One observability criterion, not several.** Substrate and cassian converged on: *every divergence
between what the caller SPECIFIED and what the mechanism DELIVERED must be reportable at the call
site — **adjusted, refused, or substituted**.* The three known faces are a clamp that did not say it
clamped, a seed silently defeated by history, and a lease admitted at a size nobody asked for;
cassian's `resource-lease` adds substitution (a pool handing back a different member).

---

## 10. A refuted report, kept with its refutation

⚑ **Included deliberately.** A findings document carrying only confirmed defects teaches the next
auditor to trust shape-matching.

linux-sources reported `membudget-ledger:167` as a live bug:

    if grep -v "^LEASE $1 " "$FILE" > "$FILE.t" 2>/dev/null; then mv "$FILE.t" "$FILE"; fi

`grep -v` exits 1 when it emits nothing, so the `mv` would be skipped exactly when the ledger empties
— leaking the last lease. **Cassian measured this shape in their own re-port and fixed it there.**

**It cannot bite in substrate.** The live ledger always carries three comment lines and `TOTAL_MB`,
which `grep -v "^LEASE <id> "` keeps unconditionally, so the filter output is never empty and grep
never exits 1.

⚑ **But it holds by an invariant in a DIFFERENT FUNCTION.** `release`'s safety depends on `ensure`'s
header fifty lines away, unmentioned at the call site. **Cassian's re-port dropped the header — their
record is `LEASE <pool> <member> <pid:starttime> <epoch>` with no comments — so their ledger CAN empty
and their fix was correct for their tree.**

**So this is not an improvement that failed to flow back. It is a defect a re-port INTRODUCED by
dropping a property that was load-bearing without being marked as such.** Their flatter record is
cleaner *and* lost an accidental guard. That is a distinct fragmentation shape worth naming.

⚑⚑ **AND CASSIAN THEN REPRODUCED IT, WHICH LOOKED LIKE A CONTRADICTION AND IS NOT.** They ran two
cases and measured the single-lease path stranding its lease. Their fixture was
`LEASE alpha 100 1:2 999` — **header-less**, i.e. their own record shape. Substrate's live ledger
carries three comment lines plus `TOTAL_MB`, and `ensure()` runs under the lock before every lease
path (`membudget:241`, `:467`, `:831`) with `cmd_init` recreating it, so substrate's ledger can never
lack them. **Both results are correct; we tested different artifacts.** Neither reading was sloppy —
the disagreement itself is the evidence that the guard is a property of the FILE FORMAT rather than
of the function, which is precisely why it does not survive a port.

⚑ **THE INTERNING CONSEQUENCE, which linux-sources drew and is the actionable part:** a Python
rewrite of the ledger would very likely produce a headerless record and thereby ACQUIRE cassian's
hazard. **So in `mikemol-membudget`, cassian's fix stops being redundant and becomes REQUIRED.** The
accidental guard does not survive the port that interning implies. That is a hard constraint on the
rewrite.

**And the class is one substrate already holds:** exit-code-as-verdict. `grep`'s exit status answers
*"did I match anything"*, not *"did the write succeed"* — the same shape as `|| true` on
`memory.swap.max`, where a status is treated as a verdict it does not carry. ⚑ Substrate's own
comment at `:158-160` reads as coverage and is not: it says a failed release *"never leaks budget
permanently"* because gc reaps it — **true for the wedged-lock path, false here, because gc reaps on
OWNER DEATH and this strands a lease whose owner is alive and released correctly.** A correct
statement about a different failure mode, sitting next to this one.

---

## 11. What substrate owes, ranked

1. **Gate the build-system skill's membudget section** against the source, using the census-sync
   pattern substrate already runs three instances of. This is the artifact the repo orders readers to
   trust, and it is currently the false authority that misled this audit.
2. **Take paperkit's UUID naming and OOM-increment discriminator** — with tests, which paperkit's copy
   lacks.
3. **Migrate the live ledger header**, or have `cmd_status` warn when a ledger states the retired
   suballocation model. Same for `membudget-shrc`.
4. **Resolve the ceiling POLICY** — derived from the live `MEM_CAP` rather than asserted. mat260
   correctly declined to name a number; paperkit's climb-with-high-ceiling is a third answer.
5. **A call surface** — the absence that caused mat260's triplication and limited paperkit to a
   partial take. `mikemol-membudget` is the form.

6. ⚑⚑ **NAMESPACE THE CLAIM LABEL SPACE BY REPO — added after two second-order audits found it
   missing from every requirement list INCLUDING THIS ONE.** §9 calls it *"the first thing a
   convention must settle"* for a multi-writer intake and then the corpus dropped it: it appears in
   no other filing, no requirement list, and until now not in this document's own owed-list. **The
   central recommendation (intern it) is gated on a question raised once and abandoned.** The ledger
   is `$HOME/.cache/membudget/budget.cotype` with no repo component, so `claim:pg` from two repos
   mutually exclude with no way to tell whether that is correct — and interning exists precisely to
   produce more independent writers into that namespace.

7. ⚑⚑ **RESOLVE THE ENUMERATE-VS-CHURN CONFLICT, WHICH IS A COST OF THIS DOCUMENT'S OWN
   RECOMMENDATION.** §8 recommends the enumerated pool as the general form; §9 records that an
   enumerated pool of N members has N times the append rate against the machine-global lock **whose
   churn already caused a measured cross-repo starvation.** Both cassian's filing and this one state
   the amplification, and **neither states that it is the price of the recommendation it just made.**
   Aggravating: the enumerated pool's ALLOCATION path has never run in production (cassian's
   correction — `cputimeout` consumes only its reclamation verb), so the union would adopt as its
   general form an untested design that provably worsens a measured failure mode.

⚑ **Not proposed here:** whether membudget lands as `mikemol-membudget`, what the intake schema is,
and whether the union adopts the enumerated pool. Those are the operators' and mtools-2c's calls.
