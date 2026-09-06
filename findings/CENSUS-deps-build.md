# CENSUS: `deps-build` — run file

**Brief:** `findings/CENSUS-BRIEF.md` rev 1. Read it first. This file overrides it where they conflict.

**Subject:** dependency management, dependency discovery, build design, build management, test design,
test management — **as your repo actually does them**, not as they ought to be done.

---

## §R Roster, prefixes, paths

| surveyor | prefix | file |
|---|---|---|
| `paperkit` | `PK-` | `findings/deps-build/paperkit-deps-build.md` |
| `substrate` | `SB-` | `findings/deps-build/substrate-deps-build.md` |
| `cassian-observability` | `CO-` | `findings/deps-build/cassian-observability-deps-build.md` |
| `mtools` | `MT-` | `findings/deps-build/mtools-deps-build.md` |
| `linux-sources` | `LS-` | `findings/deps-build/linux-sources-deps-build.md` |
| `rosettapkg` | `RP-` | `findings/deps-build/rosettapkg-deps-build.md` |
| **apex** — a fresh session holding **no leg** | `AX-` | `findings/deps-build/deps-build-apex.md` |

**Conventions, fixed here so nobody negotiates them peer-to-peer:**

- Filenames exactly as above. ⚑ Not `DEPS.md`, not `<party>-consolidated.md`, not one file per round.
- **One file per surveyor.** Draft privately, revise freely, file once.
- IDs are `<PREFIX><n>` — `PK-01`, `SB-14`. ⚑ **Directory-wide, not file-local.** Never renumber
  another party's IDs into your own scheme.
- Quote style: verbatim in blockquotes, typos preserved, provenance class tagged per brief §7.
- Everything lands under `findings/deps-build/`.

⚑ **Answer the roster question in your filing:** name any party you believe should be on this roster
and is not, and what you think they hold. The roster is the index the span is computed over; the last
run of this machinery omitted a party that held directives no other party could cite, and nothing in
that survey could have discovered it.

## §Q The question

⚑ **Survey yourself.** Report how *your repo* does these things. Do not survey the others — `§R`
tells you who else is reporting and that is all you need to know about them.

**I do not know what the union looks like; that is why I am asking all of you.** That is the honest
statement of the target, and per `§C` it is a complete question.

Cover, for your own repo, whatever of this you actually have — **absence is a finding, reported per
brief §5**:

1. **Dependency declaration** — where a dependency is named, in what file, in what language. Pinned
   or floating, and what pins it. Lockfiles: which, generated how, verified by what.
2. **Dependency discovery** — how you find out what you depend on. Import scanning, manifest reading,
   a tool, a person, nothing. ⚑ Include **implicit** dependencies: a binary on `PATH`, a service on a
   port, a file at a fixed path, an env var, a network endpoint. Those are dependencies that no
   manifest names.
3. **Dependency acquisition** — vendoring, fetching, a registry, a wheel, a corpus fetch, a symlink,
   a copy. What happens on a cold machine.
4. **Hermeticity** — what your build can reach that it does not declare, and how you know. A gate that
   passes by *not running* is the specific case to look for.
5. **Build design** — the graph, the units, the tiers. What is cached, what is not, and **why not**.
   Remote vs local execution. What invalidates what.
6. **Test design** — what a test is in your repo, what a claim is, how one binds to the other. Is a
   test proven *falsifiable*, or only observed to pass?
7. **Gate design** — what refuses, when, and what it reads to decide. Pre-commit, CI, a hook, a
   selftest. ⚑ **Has it ever fired?** A gate that has never refused anything is a configuration, not
   a gate.
8. **What you re-derived** — machinery you built because a shared thing did not offer it, or you did
   not know it did. ⚑ **This is the highest-value item in the whole census** and it is the one nobody
   records. A re-derivation is a defect report about the shared object whether or not you fix it.
9. **What you declined** — a shared mechanism you looked at and did not take, **and why**. A decline
   with a reason is a design constraint; a decline without one is fragmentation.
10. **What binds you** — the constraint that actually limits your build today. Not the one you would
    fix first; the one that decides your throughput.

## §C The construction — two phases, and phase 1 is not the deliverable

**Phase 1 — the span.** Build `A`: what every leg holds, as a correspondence table with a **witness
per identification**. State non-identifications explicitly, with reasons. Publishable, verifiable,
and **not the answer** — it is the surface the glue is taken over.

**Phase 2 — the glue.** Glue the legs along the published `A`. It **grows**: every leg's contribution
is carried, including the ones only one leg holds. No admission bar. ⚑ **If the output is smaller
than the largest leg, phase 2 did not run.**

⚑ **Carry-uncheckable-testimony.** A claim held by one leg that the apex cannot verify is carried,
tagged with its witness and its leg, and **not adjudicated**. Unverifiable ≠ false. Where two legs
disagree about one item, both stand in the divergence register with their denominators and
instruments. **An identification with no witness is over-gluing; a missed one is duplication. Both are
recorded, neither is guessed.**

## §W Window, and why

⚑ **UNBOUNDED. No date bound.**

**Justification:** the previous run of this machinery bounded every leg to a single day by nobody's
instruction, and the directive that *created the artifact under study* sat seven days outside it,
quoted in none of four filings. A window is a property of the query; findings inside one are not facts
about the subject. Build and dependency machinery here has antecedents going back months, and the
origin of a given tool is exactly the thing a bounded sweep destroys.

**The antecedent probe is still required** (brief §6): for each artifact you cite, search unbounded
for its *origin*, and report it. Unbounded window does not excuse skipping the probe — it makes it
cheap.

## §X Context you would not otherwise have

Facts no leg can infer from its own corpus:

- **One physical host.** Every party runs on the same machine — one CPU, one memory, one zram, one
  swapfile, one load average. A per-repo answer to *"what does my build need"* is a measurement of the
  box, not of the repo.
- **The current binding constraint is CPU, not memory.** Since boot: CPU stall ~59.7% of uptime
  against memory stall ~0.094%. ⚑ That is evidence the memory work **succeeded**, not that it was
  misaimed.
- **A shared remote executor exists** — BuildBuddy on k3s, reachable at `grpc://127.0.0.1:31985`,
  BES at the same, results UI on `:31080`, metrics on `:31464`. ⚑ **`--remote_local_fallback` is
  ruled out**: it evades the scheduler and consumes resources on the machine the scheduler protects.
  Some parties are on this config and some are not; that difference is a finding, not an error to
  hide.
- **The executor is currently degraded** — a ghost scheduler shard from a retired quadlet persists in
  Valkey, so a fraction of `EnqueueTaskReservation` calls return `Unavailable`. ⚑ If your remote
  builds are failing, that is a known environmental fact and **not evidence about your configuration**.
- **`mtools` is the intern table** — the repo where clean, granular, canonically-packaged tools live
  so that consumers reference rather than copy. That is the destination this census informs.
- **`membudget` exists and is shared** — an admission loop with pluggable predicates (memory, load
  average, named-artefact claim). It is **not installable**; consumers vendor it. If you vendored it,
  that is a `§Q`-3 and `§Q`-8 answer.
- **Retired, do not report as live:** the host `buildbuddy` quadlet (superseded by the k8s
  deployment); `mat230` and `mat260`.
- ⚑ **A prior four-party census over `membudget` is filed in `findings/membudget/`.** It is
  **testimony, not citation**, for this survey. Do not treat its conclusions as settled input — and
  do not read peers' legs from *this* survey until the freeze.

## §V Revision log — ⚑ corrections land here, not in messages

| rev | when | what changed | affects |
|---|---|---|---|
| 1 | 2026-09-06 | initial | — |
| 2 | 2026-09-06 | `rosettapkg` dispatched later than the other five — no session existed at rev 1. **Byte-identical message, no substitution.** Recorded as a dispatch-time asymmetry, not a content one. | apex §accounting; `rosettapkg`'s brief §9 disclosure |

⚑ **rev 2 is an accounting entry, not an instruction.** No leg needs to re-read anything. It exists
so the apex can distinguish *"filed late"* from *"had less notice"* — and so `rosettapkg`'s own §9
disclosure can state the input asymmetry rather than the apex inferring it. **All six parties
received the same bytes; only the clock differed.**

| 3 | 2026-09-06 | ⚑ **ORIGIN IS NOT ATTRIBUTABLE FROM GIT LOG IN A CONSOLIDATION REPO.** See `§Y`. | apex phase 1; every leg's antecedent probe |
| 4 | 2026-09-06 | ⚑ **A leg may mis-grade itself in EITHER direction; verify self-reported weaknesses on the same terms as strengths.** See `§Z`. | apex weighting |
| 5 | 2026-09-06 | ⚑ **Filing status is MEASURED at freeze time, never carried in the dispatcher's head.** See `§F`. | the freeze; apex accounting |

---

## §F ⚑ THE FREEZE ROSTER IS MEASURED, NOT REMEMBERED

**Logged at rev 5 after this dispatcher's own outstanding-list went stale by two legs.**

At rev 4 this dispatcher stated four legs outstanding — `paperkit`, `substrate`,
`cassian-observability`, `rosettapkg`. **`paperkit` (23:04) and `substrate` (23:06) had already
filed.** The list was a recollection of who had *messaged*, not a measurement of what was *on disk*,
and no leg announces its filing by obligation.

⚑ **Had the freeze been called on it, `A` would have been computed over the wrong `N`** — the exact
`census-kit` §6 failure, in the run that produced `§Z`.

**Binding rule:**

> **Before calling the freeze, list the directory.** The roster's `filed` / `declined` /
> `no response` marks are read off the filesystem at that moment, not accumulated from messages
> during the run.

⚑ **A filing is an artifact, not an event.** A leg that files silently is filed; a leg that messages
without filing is not. Tracking the messages tracks the wrong thing — and the messages are the part
that reaches the dispatcher, which is why the error is the default rather than an oversight.

**Same shape as `§Y`.** There, a `git log` date was mistaken for an origin witness. Here, a message
was mistaken for a filing witness. **In both, an artifact-of-record was replaced by a
convenient-adjacent signal.**

⚑ **The correction arrived from `mtools`, by directory listing, explicitly without opening either
file** — filename, size, mtime only. That is the accounting/findings boundary held under pressure:
the information a coordinator needs to avoid a stale freeze is exactly the information available
without reading a single peer finding. **Coordination traffic and findings traffic are separable in
practice, not only in the brief.** Independently re-measured by this dispatcher before logging;
sizes and mtimes match.

⚑ **rev 3 adds `§Y` below. It is an instruction to the APEX, not a re-read for surveyors** — no leg's
own survey changes. It is logged rather than messaged because a fact that reaches the apex only
through one party's disclosure is testimony; in `§V` it is part of the run.

## §Y ⚑ Origin attribution — a trap the antecedent probe walks into

**Reported by `mtools` in its filing message, 2026-09-06, before the freeze. Class: testimony
(unverified by this dispatcher at rev 3).**

`mtools` is **8 hours old** — 123 files, 52 commits, first commit 13:40 today — and is a
**consolidation point**. Its files are new *by construction* while their content is inherited from
older trees. Its own report of the spread:

> every artifact I cite originates *today*, while `substrate` (2026-05-15), `paperkit` (06-22),
> `cassian` (07-20) and yours (08-17) are 3–16 weeks older.

⚑ **So: `git log` in a consolidation repo dates the CONSOLIDATION, not the DESIGN.** An apex computing
origin from commit dates will attribute four trees' designs to the repo that most recently copied
them — over-gluing at its purest, with a machine-looking warrant.

**Consequences, binding on phase 1:**

- ⚑ **A commit date is not an origin witness** when the repo is a consolidation target. Per
  `references/apex.md`, an identification needs byte-identity, matching timestamps in a plausible
  pass, shared third-party prose, or an explicit cross-reference. **A `git log` date alone is none of
  those.**
- `mtools`' mitigation is **prose in evidence-comments naming the origin party** — its own assessment
  is that this is *"not machine-readable and no gate checks it."* Read those comments; do not rely on
  them being complete.
- ⚑ **This generalizes past `mtools`.** Any leg that vendored, copied, or adopted machinery has the
  same defect at smaller scale. **The antecedent probe (brief §6) must find an artifact's origin in
  the tree that AUTHORED it, not the tree that currently holds it.**

⚑ **The party most exposed to being credited flagged the risk against itself.** That is a
disclosure, and it is the reason this section exists rather than being discovered at the apex.

⚑ **`mtools` sharpens the finding against its own version of it:** its 8-hour-old repo made the
defect *maximally visible*, and **a vendored file in a months-old tree hides the same defect under a
plausible date** — which is strictly worse, because nothing about the date looks wrong.

---

## §Z ⚑ A LEG MAY MIS-GRADE ITSELF IN EITHER DIRECTION

**Raised by `mtools`, 2026-09-06, after withdrawing a self-assessment at this dispatcher's
correction. Logged at rev 4. Binding on the apex; no re-read required of surveyors.**

Brief §9 requires a leg to disclose its asymmetries, and the skill's whole posture assumes the risk
runs one way: a leg overstating its independence, its coverage, or its warrant. **`mtools` filed a
disclosure claiming a brief §2 violation that had not occurred** — its peer contact predated the
census, so no independence existed to lose and no rule was in force over the conduct. It withdrew the
claim and **left the withdrawal visible in its file** rather than editing it away.

Its formulation, kept because it is the contribution:

> **A leg that overstates its own weakness corrupts the span exactly as much as one that overstates
> its strength** — the apex weighs legs, and a leg lying about itself in the modest direction is
> still lying about itself.

⚑ **Consequence for the apex:** an unearned self-deprecation costs a real carry — the apex would have
held, discounted, and reasoned around a defect that did not exist. **Verify a leg's self-reported
weaknesses on the same terms as its self-reported strengths.** A disclosure is a claim about the
world and carries the same burden as any other.

⚑ **Why it is hard to catch from inside**, in `mtools`' words: *"self-criticism that reads as
discipline is the hardest kind to catch from inside."* A leg auditing its own filing has every
incentive to let a modest error stand — it looks like rigor, and correcting it looks like
self-defence.

**What `mtools` did NOT withdraw, correctly:** that it owns and authored its entire subject, and that
`mtools` is the census's own destination (`§X`). Those are real asymmetries and they stand.

**Every filing cites the revision it was written against, in its first line.**

⚑ **An instruction that reaches you outside this file is not in force until it is appended here and
you cite the new revision. Echo it, then act on it.**
