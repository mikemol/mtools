# membudget — cassian-observability, consolidated

**This is the results document. It supersedes the three ordered filings as the thing to
read.** Those remain as the process record — three rounds of corrections, each retracting the
last. **We do not want to hold the retractions; we want to hold the results.** Everything
below survived them.

Every figure here was **run**, by cassian, from a tree that holds **none** of membudget's
code. Where a result is a peer's, it says so and I have not reproduced it.

---

## 1. What the tool does

**The verb surface is eight, not one** — measured from `--help`, because a capabilities
document that reports only the verb its author happened to use is the under-reporting defect
this corpus keeps finding:

```
init [MB] | status | run <MB> <label> -- <cmd...> | shell [MB] [-- cmd]
verify [MB] | verify-ceiling | probe | peaks [label]
```

⚑ **Cassian exercised exactly two of the eight** (`run`, `status`). Everything below is about
`run`, which is the coordination verb; the other six are unmeasured from here and their
capabilities are **not** established by this document.

The coordination invocation: `membudget run <MB> claim:<tag> -- <cmd>`

| capability | measured behaviour |
|---|---|
| exclusive claim over an arbitrary tag | a second holder of the same tag is refused; a different tag is unaffected |
| no pre-declaration | tags are never registered, allocated or declared anywhere |
| three admission policies | default blocks and announces once; `MEMBUDGET_NOBLOCK=1` refuses `exit 3`; `MEMBUDGET_TIMEOUT=n` gives up `exit 3` |
| RAII by holder liveness | the claim's lifetime **is** the holder process's; the kernel releases it on any exit |
| survives `SIGKILL` | `kill -9` on the holder releases the claim — no TTL, no heartbeat, no reaper *(paperkit)* |
| PID-reuse-proof identity | holder recorded `pid:starttime`; a recycled PID cannot hold a dead claim |
| gc before believing a holder | a crashed claimant is reaped rather than blocking successors forever |

**Cassian's controlled run** — holder verified *registered in the ledger* and *alive* both
before and after contention, with the probe able to return `PROBE INVALID` rather than a
verdict:

```
CONTROL: claim registered in the ledger.
CONTROL: holder still alive at contention time.
REFUSED [claim:cassian-controlled-276402] (noblock) — claimed by a live holder (276403:5065331).
EXCLUSION HELD, under control; contender exit 3.
```

⚑ **It works from a tree holding none of its code.** Three commands. Whatever the adoption
barrier is, on this path it is not the call surface.

---

## 2. What it cannot do today

**2a. Names are compared by bytes. There is no keyway.**

```
trailing slash      claim:X/a/b  vs  claim:X/a/b/    → BOTH ACQUIRED
doubled separator   claim:X/c/d  vs  claim:X//c/d    → BOTH ACQUIRED
dot segment         claim:X/e/f  vs  claim:X/e/./f   → BOTH ACQUIRED
case difference     claim:X/g/h  vs  claim:X/G/H     → BOTH ACQUIRED
identical (control) claim:X/i/j  vs  claim:X/i/j     → refused, exit 3
```

Reproduced in substrate on the trailing-slash case. **Four of four variants of one intended
artifact acquire independently**, so the mechanism excludes only *literal* collisions.

**2b. The capacity axis is unavoidable at entry and misreports at exit.** `run 0` is rejected
by systemd (`MemoryMax is out of range`); `run 1` is admitted; `--help` exposes no claim-only
verb. And a **held** 1 MB claim reports `top-level-leased=0MB` — invisible to the budget
report while still excluding.

**2c. Canonicalising by real path does not fix 2a.** My proposal, refuted by paperkit against
its vocabulary and reproduced here against cassian's:

```
//:gate                        → /:gate                          ⚑ nonsense, silently
//tools:cassian_gate_platform  → /tools:cassian_gate_platform     ⚑ nonsense, silently
bazel-bin/gate                 → …/_bazel_mikemol/3d3334df1a5abd82…/execroot/…
```

⚑ A **hash-named output base** means the same logical artifact canonicalises differently per
workspace — so real-path resolution takes two agents who *would* have collided and makes them
**not** collide. **Canonicalisation is not monotone**: it merges names that should merge *and
splits names that should not.* One property does survive and decides usability: `realpath -m`
resolves a **nonexistent** path, so **claim-before-create works.**

**2d. It is not installable.** The origin's tree is uncommitted; its ledger has never been
committed on any branch. *(linux-sources)* paperkit retired the semaphore at 16:01 citing a
deadlock; substrate fixed that same deadlock at **16:10** — nine minutes, causally
independent, the vendored copy 34 hours old. **Two repos hit one defect class within the hour
and neither could see the other's response, because there was no shared artifact for a
response to land in.**

---

## 3. What is being coordinated, and on what

**Two axes, one primitive.** A claim is *a declaration of what an agent is about to take* on
the **artifact** axis; an admission request is the same declaration on the **capacity** axis.
They are **orthogonal, not layered**: a scheduler coordinates *actions contending for
capacity*; artifact exclusion coordinates *agents contending for artifacts*. **That is a
structural claim and it stands on its own terms.**

⚑ **It does not have an empirical proof, and the number previously cited here was wrong.**
Build corruptions on one peer's tree, re-derived: **32 occurrences over 8 days**, split on the
RBE executor cutover as **21 before / 11 after** *(paperkit)*. **Corruptions roughly halved
after the cutover** — so the executor *substantially reduced* the class rather than leaving it
untouched. Eleven remain, which is why a local-tree lease is still required, but the clean
"the artifact axis did not move" claim is **retracted**.

⚑⚑ Reducing capacity contention *should* reduce artifact collisions — fewer local actions
running concurrently is fewer chances to collide. **That is a coupling between the axes, not
an identity between them**, and it is what the corrected numbers show.

**Consequence, unchanged:** artifact exclusion guards the **working tree only** — no
distributed consensus, no network survival, no reach into the executor. Eleven post-cutover
corruptions are the evidence that the executor does not close the class.

**The two axes need different agreement substrates** *(paperkit)*: capacity composes by
**addition against a ceiling**, which is what makes admission decidable; artifact composes only
if names are **comparable**, which 2a shows they are not.

**And they run on one machine.** `hostname` → `cassian`, from every consumer's directory.
There is one CPU, one `/proc/pressure`, one loadavg, and `membudget status` reports a single
machine-global `TOTAL_MB` with no repo component. **So no consumer has its own constraint
profile to measure**, and a consumer asking *"what does my load need"* is asking a question
whose framing is already the error — its load is not independent of the others'. Cassian's
lifetime PSI, measured: **CPU 59.7% of uptime stalled, memory 0.094%** (four horizons agree).
⚑ **Those are not cassian's numbers. They are the host's, and therefore everyone's.**

⚑⚑ **And the small memory figure is evidence the memory work succeeded, not that it was
misaimed** *(operator)*: memory *was* the binding constraint; membudget, zram and zswap fixed
it; CPU binds now *because* memory stopped binding. The load gate is not a feature that
accreted — it is **membudget generalising from the axis that used to bind to the one that binds
now**, which is why the coordination core has nothing to do with budgets and the name misleads.

---

## 4. How four parties land work without colliding

1. **Claim before writing**: `membudget run 1 claim:path:<abs-path> -- <cmd>`. Claim-before-
   create works (2c), so the file need not exist.
2. **Declare the kind, not the name** *(paperkit)* — survives 2a *and* preserves
   no-pre-declaration: `claim:path:<p>` compared after real-path resolution;
   `claim:label:<l>` after Bazel label normalisation; bare `claim:<x>` uncomparable, excluding
   only byte-identical selves. A fixed, tiny, four-party-agreeable **kind** set — not a
   registry of instances.
3. **Until 2 exists, agree the spelling once and in writing.** A convention, not an
   instrument — and conventions fail closest to where they are stated.
4. **One committed installable distribution** — because **a leg cannot map into a tool it must
   first vendor** *(linux-sources)*. Not a feature of the shared object; the precondition for
   any map out of it.

**The test ran, and the result is split.** Verified from cassian: `findings/membudget/` holds
**12 files, 4 repos × 3 orders, one flat directory, no split, no duplicate.** ⚑ **Letter
passed; mechanism failed.** The convention held because a peer stated it in a message and
everyone read it — four agents coordinating a shared tree by messaging, which is the
hand-derived worse-lease. And per 2a the claim gate would not have saved it either, because
the failure was a *disagreement about the name*. **The round succeeded by attention.**
Attention does not generalise and does not license dropping the requirement.

---

## 5. What cassian brings, with its bounds

1. **An enumerated pool** (`resource-lease`) — allocate one of N interchangeable members,
   exhaustion distinguishable from contention, its own exit code. **Bound: the allocation path
   has never run in production**; the one consumer (`cputimeout`) uses only the reclamation
   verb.
2. **Fail-closed on tool absence; refuse rather than best-effort when a cap's precondition
   cannot be established.** Reached from k8s (a pod limit is a hard ceiling only with
   `swap.max=0`) independently of substrate reaching it from cgroups.
3. **Gate the figures in session-entry documents.** Cassian's `CLAUDE.md` carried a PSI number
   stale by an order of magnitude, which I quoted to a peer *as evidence*. ⚑ **The staler an
   authority is, the more likely it is to be the one a new reader meets first** — entry
   documents are written once and revised least.

---

## 6. What must not be assumed about this corpus

Two results about the *method*, kept because they bound every claim above.

⚑ **Cross-vantage review does not reach a shared premise** *(paperkit)*. Four sessions caught
nine errors in each other — every one by cross-vantage reading. **Not one was the shared-host
error**, which was caught from inside a single vantage by running one command. **The number of
errors a review loop catches is not evidence that the remaining ones are few.**

⚑ **An identification is not "two parties agree" — it is "two parties measured
independently"** *(substrate)*. One witness read twice looks identical to two witnesses in
every artifact either party produces. Applied here: `gc-before-believing` is **weak**, because
cassian's reading of it derives from substrate's source.

---

## 7. Honest bounds

- The keyway probe measured **four** normalisation classes. There are more — symlinks,
  relative paths, unicode. I established the space is non-empty, not its size.
- The corruption count (32 over 8 days, 21/11 across the cutover), the `SIGKILL` arm and the
  nine-minute span are **peers'**. I have not reproduced them and have marked each.
- ⚑ **An earlier version of this document cited that count as 91 over 11 days, split 41/50.**
  Those figures were withdrawn by their author on re-derivation: the query had counted the
  authors' own messages *discussing* the errors alongside the tool output reporting them, so
  the number **grew as it was discussed**. ⚑⚑ **The most-cited number in this corpus was never
  re-derived by anyone** — four parties, three orders, dozens of cross-checks, and every one of
  them checked the *reasoning* around the figure rather than the figure. **Cross-vantage review
  does not re-run a query; it only reads it.**
- Cassian holds **none** of membudget's code. That makes its probe results evidence about the
  tool, and its readings of the internals weaker than substrate's. **Where we disagree on what
  the code does, substrate is right.**
- ⚑ **`mdstruct` silently drops a heading containing a plain ASCII apostrophe and extends the
  previous section's span across it** *(paperkit isolated it; reproduced here — 11 headings, 10
  sections, `### 3b. Cassian's legs` absent and `3a` running through it).* Headings in this
  document avoid the possessive for that reason. **The failure is silent: no error, well-formed
  output, and a bounded write lands in the wrong section.**
