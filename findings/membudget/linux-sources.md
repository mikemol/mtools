# membudget — findings from linux-sources

A fleet-wide census, commissioned 2026-09-05. The operator's framing was the starting hypothesis and
the census confirmed it: *"It's more than just memory and CPU. It's genericized. Or it's supposed to
be. I can't tell how many times I've told all of you to improve on and genericize that machinery,
and had you not share the improvements back, or decide you didn't need the whole of the thing. So it
might be fragmented."*

It is fragmented. But the cause is not what it looks like, and that is the finding I most want on
record — see §6.

⚑ **Bias disclosure, stated first because it colours everything below.** linux-sources — the repo
writing this — has **zero** membudget references, runs heavy Bazel gates, and OOM'd this box on
2026-09-04 under precisely the concurrent-heavy-compile scenario membudget exists to prevent. I had
even noted the capability at the time as *"the ecosystem's answer to the concurrent-heavy-compile
OOM; worth adopting if this recurs"* — and it recurred within the hour. This is a report by the
consumer with the **strongest need and the least adoption**, so read every judgement below as coming
from the worst offender, not an auditor.

---

## 1. What membudget IS — eleven dimensions, not two

Origin: `substrate/scripts/membudget` (860 lines) + `membudget-ledger` (169) + `cgroup-scope` (251)
+ `cgroup-scope-selftest` + `sched-batch.rs` + `membudget-shrc` + `agda-shim/agda` +
`substrate/label_lease.py` + `membudget_otlp.py`.

Its own header:

> `# membudget — a recursion-aware concurrent-memory-budget SEMAPHORE over 'systemd-run --scope'.`

That undersells it. The measured capability set:

| # | dimension | mechanism |
|---|---|---|
| 1 | memory **budgeting** | global `TOTAL_MB` (default `min(70% RAM, 8192)`), Σ over live leases |
| 2 | memory **enforcement** | cgroup `memory.max` + `memory.swap.max=0` — two writes that are **one control** |
| 3 | concurrency semaphore | blocking acquire, inotify wake, exponential backoff (×1.6, capped) |
| 4 | recursion / lease tree | `MEMBUDGET_PARENT`, disjoint child allocation, cascade-GC, exit 4 on vanished parent |
| 5 | **load-average gating** | `MEMBUDGET_MAXLOAD` (10× nproc), 1m **AND** min(5m,15m) |
| 6 | **nominal exclusion** | `claim:<artefact>` labels — a mutex, RAII by holder liveness |
| 7 | CPU scheduling | `sched-batch.rs`: SCHED_BATCH + nice-19 + long EEVDF slice; `--cpu-weight` |
| 8 | autobudget / learning | pow2 sizing from measured maxRSS history, per-module *and* per-label |
| 9 | self-correction | retry-on-OOM at the next pow2 bucket |
| 10 | telemetry | `/usr/bin/time -v` wall/user/sys/maxRSS → TSV → `peaks` → OTLP → VictoriaMetrics |
| 11 | process supervision | PID-reuse-proof liveness (`pid:starttime`), dead-owner GC, cgroup reaping |

Dimensions 5 and 6 are the ones that make "memory budget" the wrong name. The load gate exists
because the operator asked for it directly:

> ⚑⚑⚑ *"THE LOAD GATE — the SECOND predicate... 'make' has no '--load-average' (Gentoo's 'emerge'
> does; operator: "I wish I had a tool like membudget which would sleep until load average dropped
> below a target"). membudget is where it belongs: it is already the universal capture point every
> compile routes through, and it already OWNS the block-and-retry loop — this adds a predicate, not
> a mechanism."*

⚑ **And that comment is the thesis of this entire report.** The design's own stated principle is
*one admission point owning a block-and-retry loop, into which predicates plug and inherit the
contract for free*:

> ⚑ *"WHY IT IS HERE AND NOT IN A NEW TOOL. `MEMBUDGET_MAXLOAD` is the precedent: a predicate that
> is neither a lease nor a label, evaluated in this same loop, which inherits the wait,
> block-vs-refuse, `MEMBUDGET_TIMEOUT`, the announce-once line and the '=0' disable FOR FREE rather
> than growing a second, subtly-different version of each. An exclusion built beside this loop would
> have reimplemented all five."*

**Every consumer did the thing that paragraph warns against.**

---

## 2. The interface and the contract

```
membudget init [TOTAL_MB] | status | run <MB|auto> <label> -- <cmd...>
              | shell [MB] | verify [MB] | verify-ceiling | probe | peaks [label]
```

- **Declare:** a size (or `auto`) + a label. A `claim:` prefix makes it exclusive.
- **Receive:** the child's exit code **verbatim**, stderr diagnostics, a TSV row.
- **Unavailable ⇒ BLOCK.** **Impossible ⇒ REFUSE (exit 3).** **Parent gone ⇒ exit 4.** **No cap
  backend ⇒ REFUSE (exit 3)** — it never runs uncapped.

The asymmetry is deliberate and is the contract:

> ⚑ *"IT BLOCKS, IT NEVER REFUSES, AND THE ASYMMETRY IS THE WHOLE DESIGN. A RAM request larger than
> TOTAL is IMPOSSIBLE and is refused, because waiting could not help. Load is never impossible — it
> can always come down — so there is nothing to refuse and the honest behaviour is to wait."*

**Typed API: only a sliver.** `substrate/label_lease.py` exposes a frozen dataclass
`Sizing(label, lease_mb, peak_mb, clamped)`. Everything else is bash over a whitespace TSV ledger:
`LEASE <id> <mb> <pid:starttime> <epoch> <parent|-> <label>`.

---

## 3. The genericization history — it happened, repeatedly, and it is documented

1. **2026-06-19** — a machine-wide OOM. Built as an Agda-compile budgeter.
2. **2026-07-13** — operator: *"Safe until it isn't... **Fix the problem for the general case. Make
   it cheap to do the right thing. I don't want any motivation to route around the preferred
   tooling.**"* → generalized from Agda to any heavy command.
3. **2026-08-05** — disjoint child allocation: *"a lease is not a slice of a caller's allowance, it
   is a statement of how much THIS unit of work may cost"* — a statement about **grade, not size**.
4. Load gate added (memory → box quietness).
5. Claim gate added (quantity → nominal exclusion).
6. File split into `membudget-ledger`: *"split until the unit of repair is the unit of concern."*
7. **2026-09-01** `⟡membudget-wire` — per-label sizing extracted to `label_lease.py`.
8. Summit records it generalizes *"beyond make -j compile budgeting to any shared unbounded resource
   pool across cooperating cgroups."*

The genericization instruction was followed. The *sharing* is what failed.

---

## 4. The fragmentation census

| repo | form | verdict |
|---|---|---|
| **substrate** | **ORIGIN** — 860 + 169 + 251 lines | canonical; all 11 dimensions |
| **mat230** | frozen fork, 41% of a pre-split copy | pre-load-gate, pre-claim, pre-ledger-split; still carries the **superseded** suballocation model and a **stale v2-root cgroup bug substrate already fixed** |
| **mat260** | path-archaeology invoker | uses the real tool; ~4 of 11 dimensions; 3 duplicate detection copies |
| **paperkit** | vendored `cgroup-scope` + independent reimplementation above it; membudget declared "retired" | the retirement is **PARTIAL** — it retired the ledger, not the cgroup |
| **cassian** | 3 predicate re-ports, **zero copied code** | took **2 of 11**; nothing in cassian budgets concurrent memory |
| **linux-sources** | **ABSENT** | ⚑ total non-adoption (see §7) |
| **mtools** | absent, name reserved | the interning target |

**mat230** is the worst state: its vendored `cgroup-scope` still writes to the `/sys/fs/cgroup` root
and still asserts two dated probe lines substrate deleted as *"BOTH HALVES ARE NOW FALSE."* That
copy is **dead unprivileged and does not know it**.

**mat260** is what summit already filed:

> *"discovery is path archaeology rather than an interface: grep the agda library registry for the
> substrate.agda-lib entry, take the grandparent directory, and hope for scripts/membudget, **a
> derivation duplicated in a shell shim, a build script, and a python twin because there is no call
> surface to share**."*

**paperkit** declares (`gate.py:273`): *"membudget retired: Bazel IS the semaphore — per-machine, no
cross-repo flock."* But substrate adjudicated this in its own warrants (`bz-resource-set`,
`ado-resource-set`): *"resource_set is a scheduling hint that bounds nothing — bazel schedules and a
cgroup bounds — so membudget remains substrate's only enforcement layer."* Paperkit still vendors
`cgroup-scope`, which is the concession that the retirement is partial.

**cassian** took the load gate (verbatim algorithm, `MEMBUDGET_*`→`GATE_*`) and the lease/liveness
discipline, generalized to pool allocation. It dropped the other nine, including all memory budgeting.

### ⚑ Improvements made downstream that never flowed back

| improvement | where | status |
|---|---|---|
| ~~**`release()` `grep -v` exit-status bug**~~ | cassian | ⚑ **REFUTED — see §4a. Not a flow-back failure.** |
| **UUID scope naming** — `$$-date-RANDOM` collided; MEASURED at 1 in 24,376 actions, build failed | **paperkit** | not in substrate |
| **OOM climb keyed on `memory.events` `oom_kill` increment** — strictly sharper than `137\|\|143`, which is ambiguous for any SIGKILL and wrong under `oom.group=1` | **paperkit** | not in substrate |
| **sqlite observation store** with provenance + monotone concurrent upsert | **paperkit** | not in substrate (which hand-rolls an insertion sort in awk) |
| **convergence witness** (has the learning loop warmed up?) | **paperkit** | not in substrate — and dead in paperkit too, by its own declaration |
| **three-state peak channel** (`unavailable:absent` / `unavailable:unreadable` vs a real 0) | **paperkit** | not in substrate |
| **CPU-time integral bound** (`cputimeout`) and **multi-resource fence reporting WHICH cap bound** | **cassian** | not in substrate |
| **pool allocation** (allocate-one-of-a-set vs exclude-a-named-one) — its own header calls it *"a candidate to offer back to substrate via summit since membudget is theirs"* | **cassian** | ⚑ **the offer was never made** |

⚑ The channel is not broken — it was used once. Paperkit reported the root-ownership and reap bugs
and the `memory.swap.max=0` measurement, and substrate repaired `cgroup-scope` upstream. It simply
stopped being used after that.

---

## 4a. ⚑ A REFUTED FINDING, KEPT WITH ITS REFUTATION

This section exists because a findings document carrying only **confirmed** defects teaches the next
auditor to trust shape-matching. The next reader will match the same shape; the invariant that saves
it must be findable from here.

**What I reported to substrate:** `membudget-ledger:167` gates its `mv` on grep's exit status —

```sh
if grep -v "^LEASE $1 " "$FILE" > "$FILE.t" 2>/dev/null; then mv "$FILE.t" "$FILE"; fi
```

— and `grep -v` exits 1 when it emits no lines, so the `mv` would be skipped exactly when the ledger
empties, leaking the last lease forever. Cassian had measured that failure in its own tree (*"the
top-level release never took"*) and fixed it. I reported it as a fix that never flowed back, hedged
as a code-shape match I had not reproduced.

**REFUTED by substrate, who ran the probe.** `grep -v` can never emit nothing here. `ensure()` writes
a four-line header the filter always keeps:

```
# membudget cotype — recursion-aware concurrent memory-budget semaphore (scripts/membudget).
# Global free = TOTAL_MB - Σ top-level LEASE mb; a nested lease draws from its PARENT's mb.
# LEASE <id> <mb> <pid:starttime> <epoch> <parent|-> <label>
TOTAL_MB 8192
```

Releasing the last lease still emits ≥4 lines → grep exits 0 → the `mv` runs. **There is no ledger
state in which the filter output is empty.** The defect does not exist in substrate.

Three things worth keeping from this:

1. ⚑ **The code shape matched and the defect did not exist, because the invariant that saves it
   lives in a DIFFERENT FUNCTION.** `release()`'s safety depends on `ensure()`'s header, fifty lines
   away and unmentioned at the call site. That is a real fragility even though the bug is not live:
   it holds *by accident of file format*, and a future ledger written without a header would break it
   silently. Worth a comment at the `release()` call site naming the dependency.

2. ⚑ **A RE-PORT CAN INTRODUCE A DEFECT THE ORIGIN NEVER HAD, by dropping a property that was
   load-bearing without being marked as such.** Cassian's ledger line is
   `LEASE <pool> <member> <pid:starttime> <epoch>` with **no header at all** — so cassian's ledger
   *can* empty, and cassian's fix was **correct for cassian's tree**. This was never a fix that
   failed to flow back. It is a defect the re-port *created* by producing a cleaner, flatter record
   that lost an accidental guard. That is a sharper entry on the fragmentation map than the bug would
   have been, and it is substrate's finding, not mine.

3. ⚑ **My own error, named:** I matched a shape and reported a failure I had not constructed. The
   hedge ("code-shape match, not reproduced") was correct and did not save the claim from being
   wrong, because a hedge travels with the message and only the claim survives the relay. The control
   was one probe, and substrate ran it. *Read one level finer than the shape.*

**And the same probe found a real defect.** The live ledger's header line 2 states *"a nested lease
draws from its PARENT's mb"* — the **pre-2026-08-05 suballocation model, explicitly retired**. The
code does the opposite: *"Child allocation is DISJOINT from parent allocation… parentage governs
cascade-GC, never the pool."* Because `ensure()` **only writes on creation and never migrates an
existing ledger**, the operator's live file has stated the opposite of what the code does since
August. `membudget-shrc` carries the same retired claim. This is a stale-authority defect in the
artefact a reader consults to understand the model — and it is live now.

---

## 5. Usage vs adoption — what was taken vs what is called

| consumer | took | actually uses |
|---|---|---|
| substrate | all 11 | all 11 (`Selftest.mk` 234 `auto` requests, `agda/Makefile`, agda-shim) |
| mat260 | the whole tool | ~4 of 11 |
| mat230 | 41% of a stale copy | its cgroup arm is dead unprivileged |
| paperkit | vendored cgroup-scope; rebuilt sizing | cap + climb heavily; `mem_converge.py` runs **nowhere**; `PAPERKIT_NO_MEMBUDGET` disables a path that no longer exists |
| cassian | 2 of 11 | ⚑ load-gate at **one** call site with its exit-3 escapes swallowed by `\|\| true`; `cputimeout` only in `--meter` mode; `resource-lease` and `resource-fence` at **zero** production call sites (its own docs: the fence *"is built but has never been aimed at anything"*) |
| **linux-sources** | **nothing** | **nothing** |

That table is the operator's complaint, quantified. Four resource-governance tools built in one
consumer, two of them never aimed at anything.

---

## 6. ⚑ THE ROOT CAUSE IS PACKAGING, NOT DISCIPLINE

This is the finding that changes what to do about it.

`substrate_tooling.egg-info/SOURCES.txt` ships **`.py` files only**. Of the entire membudget family,
**only `membudget_otlp.py` is packaged**. The ~1,300-line bash core is **structurally
undistributable**.

So: mat260 greps the Agda library registry for a path because there is no import. paperkit vendored
because there is no dependency. cassian re-ported because there is nothing to depend on. Summit
already named it — *"there is no call surface to share... citing a capability by reconstructing its
filesystem location leaves no token any survey of consumers could match on."*

**The fragmentation is not people ignoring the instruction to share. It is that copying has been the
only available verb.** Every consumer that "decided it didn't need the whole of the thing" was, in
fact, choosing between vendoring 1,300 lines of someone else's bash and reimplementing the 2
predicates it needed. Both choices are rational; neither shares anything back.

---

## 7. The case for interning it as `mikemol-membudget`

**Verdict: the strongest interning candidate in the fleet**, because its fragmentation is
*mechanically caused* and interning removes the cause rather than the symptom. mtools' README defines
the repo as *"hash-consing at the architectural and component level"*; `mdstruct/pyproject.toml`
already names `mikemol-membudget` as a planned namespace sibling. Ownership is unambiguous
(substrate's), and cassian's own migration note already records *"MEMBUDGET IS MISROUTED TO CASSIAN:
membudget is SUBSTRATE's machinery."*

**Union of capability `mikemol-membudget` must expose** (the point of interning is that the canonical
node is the *union*, not any one consumer's subset):

- **Core** — ledger (lock/liveness/gc/release; ⚑ if the interned ledger is written **without**
  substrate's header — and a Python rewrite very likely would be — it acquires cassian's emptiable-
  ledger hazard, so cassian's `release()` fix becomes REQUIRED rather than redundant; see §4a) · lease acquire
  with block/refuse/timeout · cgroup cap backend (`memory.max` + `swap.max=0`, delegating-ancestor
  walk, reaper, **paperkit's UUID naming**) · systemd-run backend · exit-code passthrough.
- **Predicates as plugins** — the design's own intended shape: quantity · load-average · nominal
  claim · **pool allocation** (cassian) · **CPU-time integral** (cassian) · **multi-resource fence
  reporting which cap bound** (cassian).
- **Sizing** — pow2 buckets, per-module/per-label keys, loud clamping, **paperkit's sqlite provenance
  store + convergence witness** replacing the TSV + awk insertion sort.
- **Enforcement** — OOM climb on **paperkit's `oom_kill`-increment discriminator**, not `137||143`.
- **Scheduling** — SCHED_BATCH/nice/slice, `cpu.weight`.
- **Telemetry** — wall/user/sys/maxRSS, `peaks`, OTLP — ⚑ with the hardcoded `127.0.0.1:8428`
  replaced by an ordered candidate list; that literal is the ▣39 defect verbatim, and linux-sources
  has already paid for it once.
- **Integrations** — a Bazel `resource_set` projection **plus** the cgroup cap, since substrate
  measured that these answer different questions and neither is redundant.

**What each consumer gains / gives up:**

| | gains | gives up |
|---|---|---|
| substrate | the `release()` fix, UUID naming, oom_kill discriminator, sqlite provenance, CPU-time + fence dimensions | sole ownership; an installed entry point instead of `$SELFDIR` |
| paperkit | the ledger back (cross-invocation budgeting Bazel cannot do), load gate, claim gate | its in-place `cgroup-scope` edits become upstream patches |
| cassian | the 9 dimensions it dropped, including any memory budgeting at all | three re-ports retire; its pool/CPU-time work becomes canonical |
| mat260 | a real import; deletes 3 detection copies and a stale workaround | — |
| mat230 | escape from a frozen fork with a dead cgroup arm | — |
| linux-sources | memory bounding it does not have | — |

### ⚑ The blocking design question

membudget is ~1,300 lines of **bash**. mtools' bar is a Python-wheel bar (ruff `select=["ALL"]`, mypy
`disallow_any_expr`, pytest witnesses). Interning requires a decision that has not been made:

- **(a) rewrite the ledger + admission loop in Python** — feasible; the ledger is a TSV plus a
  `flock`, and `label_lease.py` is already the model. The cgroup/systemd-run backends stay shell-outs.
- **(b) ship the bash via `[project.scripts]`** and gate it with shellcheck at mtools' shell bar.

Desirability is not in question. **This choice is.** It is a bar-owner decision, not an
implementation detail, because it decides which of mtools' two bars (python vs shell) governs the
fleet's most-copied capability.

---

## 8. Undetermined — stated rather than papered over

- ~~Whether substrate's `release()` bug has ever fired.~~ **RESOLVED — REFUTED, see §4a.** substrate
  ran the probe I had not: the bug does not exist there, saved by `ensure()`'s header. My report was
  a shape-match I failed to construct. The residual open question is narrower and belongs to
  substrate: whether to comment the `release()` call site with the header dependency it silently
  relies on.
- ⚑ **NEW, live, found by substrate's probe:** substrate's ledger header (and `membudget-shrc`)
  states the **retired** suballocation model while the code implements disjoint allocation;
  `ensure()` never migrates an existing ledger, so the live file has contradicted the code since
  2026-08-05. Stale authority in the artefact a reader consults for the model.
- Whether `membudget_peak_mb` series are still being written to VictoriaMetrics.
- Whether cassian ever replied to substrate's 2026-07-23 OTLP report.
- Where paperkit and substrate disagree on the semaphore, **substrate is right and paperkit's own
  measurement settles it**: `resource_set` is a hint, a cgroup is a bound.
- Where cassian and substrate disagree on the load gate's third window, **both are wrong in the same
  direction**: the comment says `min(5m,10m)`, the code reads the **15**-minute field. Linux
  publishes no 10-minute average. The behaviour is safe (more conservative); the documented contract
  is not what runs — in **both** repos.
