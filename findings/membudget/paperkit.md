# membudget — findings from paperkit

Filed 2026-09-05, from a 682-line study (`paperkit/docs/membudget-study.md`, authored prose, not
a gated projection). The operator's framing was the commission:

> "It's more than just memory and CPU. It's genericized. Or it's supposed to be. I can't tell how
> many times I've told all of you to improve on and genericize that machinery, and had you not
> share the improvements back, or decide you didn't need the whole of the thing. So it might be
> fragmented."

⚑ **Bias disclosure, first.** paperkit is the repo that **believes it retired membudget**. That
belief is recorded in `paperkit/gate.py` — *"membudget retired: Bazel IS the semaphore —
per-machine, no cross-repo flock"* — and it is the reason paperkit's improvements never flowed
back: you do not upstream to a tool you think you have replaced. Read every judgement below as
coming from the repo with the most unshared work and the strongest reason not to notice it.

---

## 0. A correction to the commission's own premise

The brief that produced this study said paperkit's `cgroup-scope` (333 lines) was a **subset** of
substrate's `membudget` (860 lines), and asked what the missing 527 lines cost. **That framing was
wrong and the study refuted it.** MEASURED:

```
wc -l  substrate/scripts/cgroup-scope   251
       paperkit/tools/cgroup-scope      333
diff … | grep -c '^<'                     3
```

paperkit forked a **different substrate file** — `scripts/cgroup-scope`, not `membudget` — and is
a **superset** of it: 3 lines dropped (all superseded, not lost), **82 added**. The 860-line
`membudget` was never adopted at all, and that non-adoption is *recorded*, not silent.

Recording this because the shape of the error is the ecosystem's problem in miniature: **a
plausible size delta read as a subset relationship.** 860 vs 333 invites "they took a third"; the
artifact says "they forked a sibling and extended it."

## 1. What paperkit actually took, and what it added

| | |
|---|---|
| **Forked** | `substrate/scripts/cgroup-scope` (251 lines) |
| **Never adopted** | `membudget` (860 lines) — deliberately, with the reason recorded |
| **Added** | 82 lines, including two bug fixes substrate still lacks |

## 2. ⚑ Two fixes paperkit made and never shared

MEASURED: zero hits for `uuid`, `_climb`, `CLIMB_MAX`, `oom_count` in substrate's `cgroup-scope`
**and across substrate's entire git history**. Both are tagged "(paperkit, 2026-08-25)".

**(a) The scope-name collision.** substrate still names scopes with `${RANDOM}`. paperkit measured
a real build failure — `mkdir … File exists`, roughly 1 action in 24,000 — and moved to a uuid.
At substrate's action volumes this is a **latent build-breaker substrate is exposed to today**.

**(b) The OOM climb keyed on the right signal.** paperkit's ladder reads `memory.events`'
`oom_kill` counter rather than the exit code. ⚑ This is **strictly better reasoning than
membudget's own**, whose comment concedes `rc=137` alone is ambiguous. The origin has the weaker
form of a decision the fork already got right.

⚑ And paperkit's own file header asserts a protocol it violates: *"Upstream fixes flow substrate →
here by re-copying; this file is not edited in place."* Both fixes are edits in place. A stated
one-way flow, with traffic going the other way and nobody watching.

## 3. What paperkit silently lost

**The cross-repo semaphore** (capability #1 of the 16 the study enumerates). paperkit's claim was
"Bazel IS the semaphore" — true *within* one build, false *across* repos.

⚑ paperkit has already measured the consequence and did not name it as this loss.
`tools/cpuweight.py` records: *"two individually-reasonable builds oversubscribe together… while
substrate ran its selftests alongside paperkit's grid."* paperkit answered with `cpu.weight`.
**The memory half is unaddressed** — there is no cross-repo memory admission control, and the
failure mode is the one linux-sources hit on 2026-09-04.

## 4. What paperkit did NOT lose — it rebuilt better

`mem.sqlite` versus membudget's autobudget. paperkit's keeps **provenance** (`mem.json` "stores the
CONCLUSION and discards the evidence"), merges **raise-never-lower**, and supports concurrent
writes. That is precisely the defect class behind the mat260 `AGDA_MB_MAX=384` clamp.

**Largest unshared improvement in the study, and invisible for a structural reason:** paperkit
believes it retired membudget, so it has no frame in which "share this back" is a thought that
occurs.

For the record, one thing that is **not** a reimplementation: paperkit's `.bazelrc` four-rung
`-Xmx` ladder. A JVM heap bound never reaches the kernel; it reuses only the doubling *discipline*.
I had flagged it as a suspected duplicate in the brief and the study refuted that too.

## 5. The pattern, stated as a mechanism rather than a complaint

> **Written reports through summit travel reliably. Edits inside vendored files never do.**

There is no moment at which sharing a vendored edit becomes the obvious next action. The fix lands,
the gate goes green, the session moves on. Contrast the counter-example that proves backflow works
when it is *reportable*: the `AGDA_MB_MAX=384` ceiling that locked out mat260's 600MB modules **did**
flow back, and became `cmd_verify_ceiling`, a permanent selftest.

⚑ **AND THE MECHANISM ABOVE DOES NOT SURVIVE RECONCILIATION.** Sorting the four known
transmissions by *written* versus *addressed*: written-ness separates **none** of them —
paperkit's uuid fix is better documented than the OTLP fix that did travel — and addressed-ness
separates **all four**. cassian's `resource-lease` is decisive against my version: a written offer
that did not move. The replacement, which is stronger:

> **A change travels iff it is ADDRESSED TO A RECIPIENT.**

Which is precisely the argument for interning into mtools: a change against a shared artifact has
an addressee **by construction**. My §6 revision reached the right destination by the wrong
reasoning, and substrate reached it by the right one.

⚑ **A claim in an earlier version of this filing was REFUTED, and I had relayed it to substrate.**
It read: *"the load-gate predicate exists in three repos with three different ceilings
(10 / 10 / 1.0)."* MEASURED: substrate and cassian both default to **10** — the same ceiling — and
paperkit's "1.0" is not a load gate at all. `tools/cpuweight.py` denies the identification in its
own docstring: *"procs_running counts tasks that want CPU NOW. It is NOT loadavg."* A ratio over
`/proc/stat` and a multiple of loadavg do not denote the same quantity, so "three ceilings"
compared three numbers that are not comparable.

**This is the same defect class §0 above congratulates itself for catching** — a plausible numeric
similarity read as shared structure, exactly as 860-vs-333 lines was read as a subset. Caught once
and committed again in the same document.

The correct finding underneath is better: paperkit did not set a different ceiling, it **replaced
the predicate**, for the reason substrate's own comment concedes (*"A PSI-based predicate would be
sharper"*). That is a **third** unshared improvement — uuid scope naming, the oom_kill-increment
climb, and the contention predicate.

What survives from the census: the liveness floor exists in **one** repo — linux-sources fixed a
measured 33-minute livelock that substrate's unbounded `sleep 5` loop still has.

## 6. Smallest high-value action — REVISED, after the operator named why this repo exists

The first version of this section said: *"port paperkit's ~30 lines of `cgroup-scope` fixes
upstream"* — meaning into substrate. ⚑ **That is the wrong destination**, and the operator's
framing for mtools is why:

> "This is why everything clean is being moved to a common repository; it's easier to clean up at
> that scale than at substrate's current scale."

Upstreaming a good fix into a tree carrying ~790 lines of unstaged diff moves clean code into the
hardest place to clean it. The fixes should land **here**, in mtools, as the union's spine — and
substrate should consume them from here rather than receive them as a patch.

That also reframes what these four filings ARE. They are not an audit for its own sake; they are a
**census of what is clean enough to move**, and the fragmentation ledger is the migration's input.
Every divergence resolves to one of three dispositions:

| | disposition |
|---|---|
| paperkit's uuid scope naming | **MOVE** — strictly better than the origin's `${RANDOM}`, no domain coupling |
| paperkit's `oom_kill`-counter climb | **MOVE** — better reasoning than `membudget`'s own, which concedes `rc=137` is ambiguous |
| paperkit's `mem.sqlite` provenance layer | **MOVE** — raise-never-lower, concurrent-safe, keeps the evidence `mem.json` discards |
| the cross-repo semaphore (capability #1) | **RECONCILE FIRST** — three repos have measured its absence and none has adopted it; it is the one capability whose value depends on all four using the same instance |
| `AGDA_MB_MAX=384` | **LEAVE** — a generic path bounded by an Agda-named constant is substrate's domain coupling, not the union's |
| paperkit's `.bazelrc` `-Xmx` ladder | **LEAVE** — a JVM heap bound never reaches the kernel; it shares only the doubling discipline |

⚑ And the disposition column is the thing no single filing could produce. Each of us can say what
we changed; only the union can say whether a change is domain-neutral enough to be the spine.

## 7. Caveats on this filing

- **substrate's machinery is almost entirely uncommitted** — 790 lines of unstaged diff on
  `membudget`, and `membudget-ledger` untracked. Everything above is a snapshot of a working tree
  being edited by a live session.
- The study corrected one of its own claims mid-draft: a first pass reported "20 executable sites"
  for `AGDA_MB` from a `grep -o` token count; re-deriving by opening the lines gave **14 lines, 8
  non-comment, 3 on the live control path**. Recorded in the document rather than silently fixed,
  because a count from a token grep is the same error class as §0's size-delta inference.
- Claims are marked MEASURED or INFERRED throughout the full study. A tier says what kind of
  evidence was offered, not that it was correct — two claims marked MEASURED elsewhere in
  paperkit's docs were later found unearned by peer review.
