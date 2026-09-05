# membudget — substrate's consolidated results

**What is true about the tool, the shared object, and how to land work in it.**

**This document holds RESULTS.** The three ordered filings (`substrate.md`,
`substrate-second-order.md`, `substrate-third-order.md`) hold the process — findings, corrections,
retractions, who caught what. **That is where the record belongs and this is not it.** Nothing below
narrates how anyone arrived at anything.

⚑ **One exception, and it is not a narrative device:** where a result's evidence *is* that two parties
measured independently, this says so. **The independence is a property of the result**, not credit for
the parties.

**Bias:** substrate authored the tool. Every capability below is stated from the tool, not from
substrate's account of it, and every limit is measured.

---

## 1. What the tool is

**An admission loop with pluggable predicates.** A caller requests admission; the loop evaluates every
predicate and either proceeds, waits, or refuses. Memory was the first predicate, which is why the
tool is named for it.

**Three predicates are implemented:**

| predicate | kind | governs | on contention |
|---|---|---|---|
| memory budget | quantitative, summed | MB against a machine-global `TOTAL_MB` | block; refuse (3) if the request exceeds the total |
| load gate | quantitative, box-wide | `/proc/loadavg` 1m and min(5m,15m) vs `nproc × MAXLOAD` | block only |
| artefact claim | **nominal, keyed** | an arbitrary named artefact | block, or refuse (3) under the escapes |

⚑ **The claim predicate is the general case and the memory budget is its first specialization.** A
lease over an arbitrary named thing, with a quantity attached, is the shape; a memory lease is that
shape with the quantity load-bearing.

**The architectural reason all three live in one loop, from the source:** a predicate evaluated here
inherits the wait, the block-versus-refuse contract, the timeout, the announce-once line and the
`=0` disable **for free**. *"An exclusion built beside this loop would have reimplemented all five."*

---

## 2. The verbs

    membudget {init [MB] | status | run <MB> <label> -- <cmd...> | shell [MB] [-- cmd]
               | verify [MB] | verify-ceiling | probe | peaks [label]}

| verb | answers |
|---|---|
| `run <MB> <label> -- <cmd>` | admit and execute under a lease and a cgroup cap |
| `status` | current total, leased, free, and the live lease list |
| `peaks [label]` | **measured maxRSS per label from recorded runs** — runs, max, median, p90, wall, CPU%, and a suggested power-of-two bucket |
| `probe` | this process's parent lease, cgroup, and the ledger's leases/used/total |
| `verify` | self-asserting contract: the lease behaves as documented |
| `verify-ceiling` | self-asserting contract: the clamp is loud and an explicit default above the ceiling is honoured |
| `init [MB]` | establish the machine-global budget |
| `shell [MB]` | an interactive shell inside one top-level scope |

⚑⚑ **`peaks` answers the sizing question directly and states its own method:** *"a SINGLE observation
cannot size a cap: max alone is one bad run away from over-sizing, median alone under-sizes the
tail."* It reports the distribution and suggests a bucket rather than asserting one.

⚑ **`verify` and `verify-ceiling` are the self-asserting contracts.** The tool's own instruction is to
run them rather than trust the description: *"do not re-derive this from the comment — run verify."*
**A consumer can check what it holds without trusting anyone's account of it.**

---

## 3. The lock-out / tag-out capability

    membudget run <mb> claim:<tag> -- <cmd>

**Measured in three trees, two of which hold none of the code:**

- **at most one live lease may carry `<tag>`**; every other tag is unaffected
- **the tag is arbitrary and needs no pre-declaration** — a file, a directory, a service, a name
- **the claim lives exactly as long as the holding process** — no TTL, no heartbeat, no registry, and
  the kernel releases it on any exit **including SIGKILL**
- **a dead holder is reaped before it is believed**, so a stale claim cannot block every successor
- **three contention policies**: block by default; `MEMBUDGET_NOBLOCK=1` → exit 3;
  `MEMBUDGET_TIMEOUT=<s>` → exit 3
- **nesting is safe** — a holder that invokes its own children does not deadlock against itself
- **claim-before-create works** — a name need not exist to be claimed

⚑ **Owner identity is `pid:starttime`**, so a recycled PID cannot hold a dead claim. **That plus
kernel release is why a crashed agent cannot wedge the tree**, which is the property hand-rolled
coordination protocols do not have.

**The demand this serves is measured at 32 events over 8 days in one repo — every one a single agent
colliding with itself during its own build.** ⚑ **The requirement does not begin at two sessions; it
begins at one session and one long-running job.**

⚑⚑ **A shared remote executor SUBSTANTIALLY REDUCES the class without eliminating it** — 21 before a
BES cutover, 11 after. **Eleven remain**, so corruption still happens at input-staging on the local
tree regardless of where actions run: **a local-tree lease is still required, and it needs no
executor reach, no distributed consensus and no network.**

⚑ **The measurement's own provenance is a bound on it.** The figure was first reported as 91 over 11
days with 41 before and 50 after, and a re-derivation for this document found the raw count
contaminated by the census's own messages discussing it — only tool-output records carry occurrences.
**Filtered, the count is 32 and the executor split reverses from "does not close the class" to
"roughly halves it."** The four-party review cited the original figure in every filing and **no party
re-derived it**, so it stands here at the corrected value with that history noted as a limit on
confidence rather than as narrative.

### One machine

**Every consumer of this tool runs on the same physical host.** One CPU, one memory, one zram, one
swapfile, one load average — and the ledger has always encoded that: `TOTAL_MB` is machine-global,
with no repo component.

⚑ **So "measure your own constraint profile" is not a requirement any consumer can satisfy.** There
are no per-consumer profiles. A consumer measuring "its" constraint measures the box, and every
consumer measuring gets the same answer. **The right question is what the contention between all
consumers does** — a property of the machine and the concurrent set, not of any member.

**And the current profile is CPU-bound, not memory-bound:** since boot, CPU stall 59.7% of uptime
against memory stall 0.094%, agreeing across all four PSI horizons.

⚑⚑ **That is evidence the memory work SUCCEEDED, not that it was misaimed.** Memory was the binding
constraint; the budget, zram and zswap addressed it; **CPU binds now because memory stopped
binding.** A post-mitigation measurement read as though the mitigation were unnecessary inverts the
causality.

⚑ **The load gate is therefore the predicate addressing the current binding constraint**, and it is
the one the tool's name does not suggest.

---

## 4. What it cannot do

**Each measured.**

- **Only byte-identical tags exclude.** `claim:x/a` and `claim:x/a/` both acquire; so do doubled
  separators, dot segments, and case variants. **Exclusion is over an agreed name, and nothing
  supplies the agreement.**
- **A claim cannot be made without a capacity figure it does not need.** `run 0` is rejected by
  systemd; every artefact claim debits a memory pool it never uses. A held claim at minimum capacity
  also reports as zero leased in `status`.
- **Canonicalization by real path does not fix the first two, in three distinct ways.** Bazel labels
  become nonsense silently; output-base symlinks split names that should merge; **bare identifiers
  resolve cwd-dependently, which converts a working exclusion into a silent non-exclusion.**
- **It is not installable.** The lock kernel exists in multiple trees and no commits. A consumer must
  vendor it, and a vendored copy is where an upstream fix has nowhere to land.

⚑ **The naming problem is the binding one.** An exclusion mechanism with no naming authority cannot
coordinate parties who have not already agreed — which is the case it exists to serve.

---

## 5. The shared object

**A pushout: every party's requirements carried whole, with the shared core identified once.**

**In the core, each attested by at least two parties measuring independently:**

- exclusion over an arbitrary tag, no pre-declaration
- granularity — a different tag proceeds
- RAII by holder liveness, `pid:starttime`, reuse-proof
- three contention policies
- release surviving `SIGKILL -9`
- **three-state verdicts** — a reader must be able to report *cannot measure* distinctly from a
  measurement. ⚑ Arrived at independently in three subsystems: a measurement channel
  (absent / unreadable / real-zero), a probe (pass / fail / **invalid**), and a ratchet baseline
  (ok / empty / absent / **unread**, where unread is *"a fact about the reader, not a verdict about
  the gate"*).

- **gc before believing a holder** — a contender that finds a lease whose owner is dead reaps it and
  proceeds, so a crashed claimant cannot block every successor.

  ⚑ **Exercised under three controls**, after being the one core member no party had made fire: the
  lease appeared, the holder was confirmed dead, **and the ledger still carried the lease after the
  death** — the third is what makes it a verdict, since a kernel that had already cleaned up would
  let a contender pass without reaching the gc branch at all. The contender acquired by reaping.

  ⚑⚑ **The obvious test cannot reach this branch**, which is why four parties each ran a kill arm and
  all four exercised *release* instead. `cmd_status` runs `gc` before it reads, so **the observer
  mutates the state it reports**; and the gc lives inside the contention loop, so **a holder-plus-
  killer shape never brings the contender the branch requires.** Reaching it needs three roles with
  the contention arriving after the death.

**Preconditions of the diagram — NOT members of the core.** These are not requirements any leg
holds; they are the conditions under which a map out of the core exists at all:

1. **one committed, installable distribution** — a leg cannot map into a tool it must first vendor
2. **the concurrency harness** — a fix must be showable correct by the party *receiving* it
3. **the self-asserting contracts** — a consumer checks what it holds without trusting a description

⚑ **The distinction is load-bearing and easy to lose.** Under selection, "load-bearing" and "member"
are the same thing; under a colimit they are not. **A distribution is a property of the diagram, not
an identified requirement**, and placing it in the core is the selection reflex surviving the
correction.

**The evidence for why it is a precondition rather than a nicety:** one consumer forked the tool at
~34 hours old — current at fork time — and retired it over a defect whose fix landed nine minutes
later upstream. **A fresh fork and a stale fork fail identically once the fix has nowhere to land.**

**Legs, carried whole with their bounds:**

| leg | bound travelling with it |
|---|---|
| memory admission and pow2 sizing from history | the ceiling is a decomposition forcing function, not a measured bound |
| pool allocation over N interchangeable members | the allocation path has no production consumer |
| scheduler projection into a build system | true within one build; does not close the artefact class |
| plain adoption, no specialization | none |

---

## 6. How to land work

**Works today:**

    membudget run <mb> claim:<tag> -- <cmd>
      block by default · MEMBUDGET_NOBLOCK=1 → exit 3 · MEMBUDGET_TIMEOUT=<s> → exit 3

**Does not work today:** two parties must already agree on the tag's spelling. **Until a keyway
exists, coordination requires agreeing the tag out of band** — which is the hand-negotiated
convention the mechanism exists to replace.

⚑ **The acceptance test:** four parties landing four contributions into one tree without a path
split, a duplicated artifact, or a hand-negotiated convention. **Currently unmet at the third
condition** — a round can succeed by attention, and attention does not generalise.

---

## 7. Open questions

- **What is the keyway?** Declaring the kind rather than canonicalizing the name survives all three
  refutations, but nobody has built it.
- **Should the shared object keep the name?** The coordination core has nothing to do with budgets,
  and the name is why a four-party capability census decomposed along the resource axis.
- **Does the core hold under concurrent load?** Every measurement so far is functional, not
  concurrent at scale.
- **Does `gc-before-believing` identify across trees?** Substrate has now exercised the branch under
  controls, so the behaviour is established; what remains open is whether a party holding none of the
  code reaches the same result, since every reading of it so far traces to one source.
