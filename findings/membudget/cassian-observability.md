# membudget findings — cassian-observability

## Bias disclosure

**Cassian holds no membudget code and never has.** Its position in this census is
citation-plus-independent-reimplementation, so every claim below about substrate's
internals is a reading of substrate's tree, not of something cassian maintains. Two
consequences a reader should discount for:

1. **Cassian's contributed generalization (`scripts/resource-lease`) has one production
   consumer, and its pool path is unexercised.**

   ⚑ **CORRECTION, 2026-09-05, after filing.** This bullet originally read "**zero
   production call sites**, measured." **That is false**, and a second-order reconciliation
   caught it. `scripts/cputimeout:367` calls `resource-lease --reap-orphans` on the live
   path, under an operator ruling recorded in its own docstring: *"operator ruling
   2026-08-29: cputimeout was re-deriving pid-liveness + orphan-gc that resource-lease
   already generalizes — the reclamation lives there, cputimeout is a consumer."*

   **What I did wrong is the domain-drift class**: I measured the *acquire/pool* path's
   call sites and stated the result at the *all-call-sites* domain. The narrow measurement
   was sound; the sentence was not. And it propagated — a peer's filing repeated it as
   measured fact. **A false claim made against my own interest is still a false claim, and
   its self-deprecating direction is exactly why nobody checked it.**

   The **surviving, narrower** bound — which is the one that matters to the union — is that
   the **allocate-from-pool path has never run in production**. `cputimeout` consumes only
   the reclamation verb. So the enumerated-pool form is a real design with a real consumer
   for its RAII half and **no load-testing of its allocation half**, and the union must
   carry that bound rather than the stronger one I originally claimed.

2. **Cassian's non-adoption of the memory budget was an explicit operator ruling.**

   ⚑ **RETRACTING THE FRAMING, same review.** This bullet originally continued: "That makes
   cassian the control case in this census — the one repo whose absence is a decision."
   **That is not a bias disclosure; it is a defence.** It converts a deficit into a
   credential — the other three filings' disclosures make their authors *worse* witnesses,
   and mine made cassian a *better* one. A disclosure that improves your standing is not a
   disclosure. It was also **asserted bare**, with no ruling quoted or dated, in a filing
   whose whole method is quotes-over-assertion; and it does not survive a peer's reading of
   cassian as *"four resource-governance tools built in one consumer, two of them never
   aimed at anything"* — which is not a control case but the most tool-fragmented consumer
   in the census. I have not engaged that characterization and should have.

   What remains true and useful: cassian never felt the pressures that produced the other
   repos' local forks, so **I have measured the failure modes I describe in substrate's
   copy, not experienced them.** That is a real limit on this filing's weight. The "control
   case" claim is withdrawn.

Everything below is MEASURED (I ran it or read it) unless marked INFERRED. Where a peer
supplied a claim I re-derived it rather than relaying, and I say which.

---

## 1. The generalization cassian built, and the case it names

`scripts/resource-lease` (cassian label A216) is an independent re-port of membudget's
concurrency discipline onto a different allocation shape. Its own header states the
relationship:

> "GENERALIZES substrate membudget's lease. membudget leases a divisible BYTE BUDGET and,
> via its `claim:<artefact>` gate, an EXCLUSIVE NAMED resource. This is the third case
> between them: a finite SET of interchangeable members (ports 18000-19999), where
> `acquire` hands out a member NOT currently held by a live process — allocate-from-pool,
> not exclude-a-named-one."

So the design space, as cassian mapped it:

1. a divisible scalar quantity drawn from a global total — membudget's `mb`
2. an exclusive named resource — membudget's `claim:<artefact>`
3. one interchangeable member from a finite set — `resource-lease`

**This answers "more than memory and CPU" along an axis nobody was searching.** substrate
looked for a parameterised *dimension* on the quantity and correctly refuted the `<parent>`
field as an allocation edge (it governs cascade-GC, i.e. lifetime, not division). The
generalization is not a richer quantity at all — it is a different **allocation shape**. A
pool of interchangeable members has no meaningful scalar: you do not want three units of
port, you want *a* port, distinct from everyone else's.

### 1a. The two-case collapse

substrate then tested the collapse I proposed, against the claim gate's *implementation*
rather than its comment, and found that acquisition is "find it unheld" with no requirement
that the name be pre-declared or belong to a set. **So case 2 is case 3 at N=1**, and the
canonical form is two cases: a divisible scalar, and a pool of |N| members with
exclusive-named as the degenerate N=1.

⚑ **And substrate had written case 3 down without building it.** Its `suite_claims.py`
says pg "IS THE DEGENERATE CASE OF A POOL … a lease over a SET of N slots rather than an
exclusive lock — the same machinery at |members| = N." Two independent arrivals at the same
missing case, neither party told the other. That is the fragmentation with both names on it,
and it is better evidence than either repo's self-accusation because neither was looking
for it.

### 1b. The enumerated pool is the more general form, and this direction surprised us

substrate's implicit claim-pool accepts any name, which *reads* as the more general thing.
It is not. Because the member set is whatever callers happen to name:

- **There is no unknown-member error.** A typo'd claim silently acquires a fresh
  single-member pool and excludes nothing. An implicit pool cannot distinguish a new member
  from a misspelt one.
- **Exhaustion is not distinguishable from contention.** At N=1 they coincide, so the gap
  is invisible today and becomes real the moment N>1.

`resource-lease` declares its pool, so "no member free" is decidable and gets its own exit
code, distinct from usage-error and unknown-pool. **The union should take the enumerated
pool as the general form and treat the implicit-name claim as the special case that trades
declarability for convenience — noting explicitly that the trade costs the typo check.**

### 1c. What cassian confirms about substrate's mechanics

`resource-lease` re-implements substrate's concurrency discipline and credits it: the lock
fd never crosses a fork (a dead holder's fd is closed by the kernel, so the lock
auto-releases); liveness is pid-plus-start-time, PID-reuse-proof; gc drops dead leases;
lifetime is the holder process's lifetime, so the kernel runs the destructor
unconditionally. These are exactly the four mechanics substrate declared complete. **An
independent re-implementation reaching the same four is a decorrelated witness**, and it is
the reassuring half of this census.

---

## 2. Cassian's own three failures, measured

I would rather record these against cassian than have them found.

**2a. An offer-back written down and never sent.** `resource-lease` says in its header that
it is "a candidate to offer back to substrate via summit since membudget is theirs." The
offer was never made. This is the operator's grievance running in cassian's direction, and
it is the hard case for the pattern paperkit proposed ("written reports travel; edits inside
vendored files do not") — because this *was* written down, in the artifact itself, and still
did not move. ⚑ **If a written intent only travels when someone is already looking for it,
that is a sharper and worse finding than the vendored-edit one.**

⚑ **RESOLVED, after filing, by the two second-order passes — and the repair is load-bearing
for the union.** The discriminator is not report-vs-edit. **It is whether the artifact has an
ADDRESSEE.** A summit floor entry has a recipient and a failing check; a comment in one's own
source, a header note, and a letter dropped in a gitignored directory all have *zero*
addressees — and all three failed to travel. Substrate supplied the second counter-instance
against itself: its `suite_claims.py` wrote the pool design down and it never travelled,
one section above substrate endorsing the mechanism that instance falsifies.

**Consequence the union must carry: interning fixes the vendored-edit half and does nothing
for the written-intent-with-no-addressee half.** Three of this audit's own named
fragmentation instances — cassian's pool offer, substrate's pool comment, and mat260's letter
— live in the half interning does not reach. No requirement in any filing covers it. **A
canonical package does not give a finding a recipient; only a channel with an intake does.**

**2b. A defect found in substrate and apparently never reported.** substrate's ledger
release tests the *filter's* exit status rather than the *write's*:

> `if grep -v "^LEASE $1 " "$FILE" > "$FILE.t"; then mv "$FILE.t" "$FILE"; fi`

`grep -v` exits 1 when it selects no lines, so filtering out the last remaining lease
produces empty output, exits 1, and the `mv` is skipped. I reproduced this against
substrate's exact shape: with two leases, releasing one works; with one lease, releasing it
leaves the ledger still holding it.

⚑ **substrate then showed my reproduction is unreachable in its tree, and the resolution is
better than either verdict.** Substrate's live ledger carries a header written by `ensure()`
under the lock before every lease path, so the filter output is never empty and grep never
exits 1. My fixture was header-less — *cassian's* record shape. **So the guard is a property
of the artifact, not of the code, and nothing at the call site says so.** The consequence
for interning: a Python rewrite of the ledger would very likely produce a headerless record
and thereby **acquire** the hazard. The fix is not redundant in `mikemol-membudget`; it is
**required**.

⚑ Separately, substrate's comment beside that code says a failed release "never leaks
budget permanently" because gc reaps it. That is true for the wedged-lock path and false for
this one: gc reaps on *owner death*, and this strands a lease whose owner is alive and
released correctly. A correct statement about a different failure mode, sitting next to this
one and reading as coverage.

**Class:** both this and the best-effort swap-cap are *exit-code-as-verdict* — a status
treated as a verdict it does not carry. `grep`'s status answers "did I match anything," not
"did the write succeed."

**2c. The generalization has no consumer.** `resource-lease` exists to fix four selftest
arms that bind fixed localhost ports and collide under concurrency; its header names the
literals that "become LEASED rather than hardcoded once migrated." **Measured: all four arms
still hardcode all four literals.** The migration never happened, and the tool's only two
references are its own behavioural test and a provenance comment. By cassian's own rule that
a capability nobody can find is functionally absent, cassian shipped a capability with no
consumer. This does not refute the design — the two-case collapse stands on the design, not
on adoption — but it means **the enumerated-pool form has never been load-tested, and the
union must carry that as a bound.**

---

## 3. The liveness lesson — the most transferable thing in this filing

substrate and I jointly escalated a defect in a vendored copy elsewhere in the fleet as a
live silent failure. The chain had three links and every one was sound:

- substrate **measured the mechanism**: with swap reachable, a memory cap only throttles and
  never kills; with swap denied, the same bytes produce a kill.
- substrate **verified the code divergence**: the vendored copy best-efforts the swap denial
  where the origin refuses outright.
- cassian **verified the host precondition**: this host has a 32G swapfile plus 9.2G of zram
  actively in use, and — more than that — *is designed to swap*; compression-then-swap is its
  memory architecture, not a configuration accident.

So a scope could be handed back that looks capped and cannot kill, and any retry ladder
keying on the kill signal would read success.

**The conclusion was still overstated, because nobody checked whether the consumer was in
service. That repo is retired.**

⚑ **We validated the mechanism, the code, and the environment — and not whether anything
runs it.** A defect in a retired repo is a stale artifact, not an exploitable failure. The
audit chain needs a fourth link, **consumer liveness**, and "the code is wrong and the host
qualifies" does not establish one. The diff between a hygiene item and an incident is
invisible in the code; it lives in whether anything calls it.

This is the same family as extending a sound measurement past the domain it covers: three
correct measurements, generalized to a domain (an in-service consumer) that none of them
sampled.

---

## 4. What cassian asks of the canonical form

Stated as requirements rather than as a schema, since the schema is exactly what is
unsettled.

1. **Parameterise on allocation shape, not on quantity.** Divisible-scalar and pool-of-N
   (with exclusive-named as N=1). Three built witnesses across the fleet support this; it is
   not a hypothesis.
2. **Enumerated membership**, so a typo is distinguishable from a new member and exhaustion
   from contention.
3. **A real call surface.** Its absence is the measured cause of triplicated discovery logic
   in one consumer and of another repo taking only the cgroup slice. This is a
   missing-capability finding, not a defect.
4. **Every divergence between what the caller specified and what the mechanism delivered
   must be reportable at the call site — adjusted, refused, or substituted.** A clamp that
   does not say it clamped, a seed silently defeated by history, a lease admitted at a size
   nobody asked for, and a pool handing back a different member than last time are four
   faces of one requirement.
5. **Test the write, not the filter.** See 2b. Required under interning even though it is
   unreachable in the origin today.
6. **Refuse, never best-effort, when a cap's precondition cannot be established.** A cap
   that silently degrades to a throttle is indistinguishable from one that works.
7. **Carry the churn constraint as a named bound.** Making the ledger append-only is not a
   free improvement: over a machine-global lock, every append is a change event, and the
   measured consequence of rewriting unconditionally was "a self-feeding churn storm that
   saturated the global lock and starved other repos." An enumerated pool of N members has N
   times the append rate of a single claim, so this gets *harder* exactly as the general form
   is adopted.
8. **Consumer liveness in the audit chain.** See §3.

## 4a. How to weight this corpus — findings from two decorrelated second-order passes

Added after filing. Cassian and substrate each ran an independent second-order agent over
all four files with *different* briefs. Both reached the same structural conclusion by
different routes, which is the strongest signal produced in this exercise.

⚑ **The corpus's evidence hierarchy inverts its confidence.** The claims stated most
emphatically across the most files — packaging-is-the-root-cause, reports-travel-but-edits-
don't, consumer-liveness — are the *least* independently supported: one measurement plus
relays. The claims with genuine decorrelated witnesses — the pool/N-member collapse,
refuse-never-best-effort, substrate's four concurrency mechanics — are each stated once,
calmly. **Repetition across files tracked messaging traffic, not evidence.** A reader
counting file-agreement would rank this corpus almost exactly backwards.

⚑⚑ **And substrate was an undeclared referee, not merely one input.** Three of the four
filings were edited to incorporate substrate's rebuttals — this one included (§2b exists
because substrate refuted cassian's reproduction). Substrate's own agent found this and
substrate has added the declaration; its formulation is the right one: *"a party that is
simultaneously the subject, the largest offender, and the referee should declare the third
role."* **A reader taking these four files cold would conclude "remarkable convergence"; the
correct conclusion is convergence through a hub that is also a party.**

The corollary is the practical one: **the strongest agreements are the ones that predate the
messaging** — the pool collapse and refuse-never-best-effort converged because both artifacts
existed before the audit began. Everything that converged *during* it is one source with
relays.

### Two conflicts inside the assembled requirement set that no filing resolved

1. **Enumerate-vs-churn.** Cassian and substrate both wrote "take the enumerated pool as the
   general form" *and* "an enumerated pool has N times the append rate, so the churn hazard
   worsens." Neither resolved the tension between its own two bullets. Aggravated by the
   correction in §BIAS: the pool's *allocation* path has never run in production. **So the
   union is being offered, as its general form, an untested design that provably worsens a
   measured failure mode — and it reads settled because two filings agree.** This needs a
   decision, not a synthesis.
2. **The machine-global label namespace.** Substrate named repo-namespacing of the claim
   label space "the first thing a convention must settle" for a multi-writer intake, then
   omitted it from its own owed-list and from every requirement list including this one.
   Interning's *purpose* is to produce multiple writers into exactly that namespace.

### One class with four members, no filing holding more than two

`exit-code-as-verdict` has four instances across the corpus: cassian's `grep -v` (status of
the filter, not the write), the best-effort swap cap, paperkit's `rc=137` discriminator
(nobody classed it), and the silent clamp — which cassian and substrate both filed under
*observability* instead. ⚑ **A clamp returning success while delivering something else is a
status standing in for a verdict.** So requirement 5 ("test the write, not the filter") and
requirement 4 ("report every divergence") are **one invariant**, held as two because each
party derived it from a different instance. That is the fragmentation of the analysis
reproducing the fragmentation of the code, visible inside a single requirement list.

## 5. Honest gaps

- Cassian cannot speak to whether the ledger budgets across repos or per-repo; I have not
  read that path.
- Cassian's exit-code taxonomy is asserted from `resource-lease`'s own documentation; I have
  not exercised the exhaustion path under real contention (see 2c — no production consumer).
- Everything in this filing about substrate's tree is a **working-tree snapshot**; peers
  report substrate's membudget files are substantially uncommitted, so line-level claims may
  not survive their next commit. I have used quotes rather than line numbers for that reason.
