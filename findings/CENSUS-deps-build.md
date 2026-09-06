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
| 6 | 2026-09-06 | ⚑ **SIX ROSTER NOMINATIONS RECEIVED — the index may be short. NOT dispatched.** See `§N`. | apex §A4; roster accounting |
| 7 | 2026-09-06 | ⚑ **`summit` independently corroborated by a second leg, different reason.** See `§N` end. | apex §A4 |
| 8 | 2026-09-06 | ⚑ **TWO REPOS HOLD OPPOSITE FAIL-OPEN POLICIES ON ONE SHARED EXECUTOR.** See `§P`. | apex divergence register |
| 9 | 2026-09-06 | ⚑⚑ **`§Q`-10 ANSWERS ARE TYPED, NOT RANKED — do not sum or average them.** See `§T`. | apex phase 2; `§Q`-10 handling |
| 10 | 2026-09-06 | ⚑⚑ **THE FREEZE IS AN ARTIFACT IN `§V`, NOT A MESSAGE. Poll this table.** See `§G`. | every leg's embargo; the freeze |
| 11 | 2026-09-06 | ⚑⚑ **`mdstruct --headers` SILENTLY DROPS SECTIONS — cross-check with `--budget`.** See `§M`. | apex phase 1; every leg read |

---

## §G ⚑⚑ THE FREEZE IS AN ARTIFACT, NOT A MESSAGE — poll `§V`

**Raised by `substrate-b0`, 2026-09-06, and adopted verbatim as the mechanism.**

The dispatch said *"do not read peers' filings until I call the freeze."* ⚑ **No leg can observe that
call.** It arrives as a peer message that may not arrive, or may land mid-turn and be missed — so a
leg holding the embargo cannot distinguish:

> *"nobody has called the freeze"* from *"the call did not reach me"*

⚑ **That is this brief's own absence-versus-unavailable class, applied to the survey's control
flow** — and the dispatcher built it in without noticing. A leg could hold an embargo indefinitely
against an event it has no instrument for.

**THE RULE, effective now:**

> ⚑ **THE FREEZE IS A ROW IN `§V`.** It is called when, and only when, a revision appears in the
> table above reading **`FREEZE CALLED`** and `§S` below carries the roster accounting. **Poll this
> file. Do not wait for a message.** A message may also be sent as a courtesy; it is not the event.

⚑ **This is `I1` applied to the freeze itself** — *corrections land in the revision log, not in
messages* — and substrate's reason for preferring it over a locally-evaluable condition is the one
that decides it: **a condition like "all six files present" produces no accounting artifact**, while
`§6` requires every party marked `filed` / `declined` / `no response` *before* the apex begins. The
revision produces the artifact the brief already demands.

⚑ **Until `FREEZE CALLED` appears in `§V`, the embargo holds and legs are not blocked on anything.**
Answering substrate's direct question: **nothing is owed by a filed leg.** File once, then the
obligation is discharged; the next event is the freeze, and it is now observable.

## §S Freeze roster — ⚑ NOT YET CALLED

| party | status | evidence |
|---|---|---|
| `paperkit` | **filed** | `paperkit-deps-build.md` |
| `substrate` | **filed** | `substrate-deps-build.md`, `SB-01`–`SB-10`, against rev 1 |
| `mtools` | **filed** | `mtools-deps-build.md`, `MT-01`–`MT-13`, against rev 1 |
| `rosettapkg` | **filed** | `rosettapkg-deps-build.md` |
| `linux-sources` | **filed** | `linux-sources-deps-build.md`, `LS-01`–`LS-30` |
| `cassian-observability` | ⚑ **in progress — held** | leg complete at `cassian:docs/census-deps-build-leg.md`; blocked on **its operator's hold against writing to mtools**. Not a decline; the dispatch was usable. |

⚑ **This table is provisional and is re-measured at freeze time, never carried forward** (`§F`).

---

## §M ⚑⚑ THE READER THE ROUTING HOOK MANDATES DROPS SECTIONS SILENTLY

**Reported by `substrate-b0`; REPRODUCED by `linux-sources` on its own file within the hour.**

    mdstruct --headers NEXT.md   ->  31 headings
    mdstruct --budget  NEXT.md   ->  73 headings      ⚑ 42 sections invisible

**Mechanism** (`testimony`, substrate): a heading containing an **apostrophe** reads as unmatched,
the cursor does not advance, and **the preceding section's span extends over the missing one.**
⚑ **No error, no gap — the predecessor just reads longer.** `--budget` does not use the anchoring
path, which is why the two disagree.

⚑⚑ **BINDING ON THE APEX, AND THIS IS THE SHARPEST OPERATIONAL ITEM IN THE RUN FILE.** Substrate
reports the drop swallowed **`SB-08` — its `§Q`-8 re-derivation section**, which `§Q` names as *the
highest-value item in the census*. It renamed the heading to work around it, **so its leg is safe and
no other leg is known to be.**

> **An apex reading legs with `--headers` will silently miss `§Q`-8 sections in any leg whose
> heading contains an apostrophe, and will see no gap.**

**Required of the apex:** cross-check every leg's heading count with `--budget`, and treat a
mismatch as a **stop**, not a note. ⚑ A single reader cannot detect this class — **the disagreement
between two readers is the only signal.**

⚑ **Two correct guards compose into an unfixable defect.** `hook_structural_query` refuses
`grep`/`sed`/`cat` on `.md` and names `mdstruct` as the owning tool, so the gate **compels** the
defective reader and forbids the fallback that would expose it. A clean replacement exists
(`substrate/md_hkey.py`, 18/18, folding all seven of pandoc's smart-typography rewrites) and is
**unwired**, behind an all-or-nothing per-file gate that refuses every edit to `mdstruct`. **The
per-file gate protects the tool; the routing hook mandates the tool; the fix sits outside both.**

⚑ **It has already cost this dispatcher a symbol collision** — a ledger census taken with
`--headers` missed an existing symbol and a new item was filed onto it. **A guard that routes every
consumer to one instrument inherits that instrument's blind spot fleet-wide**, and the guard's own
correctness is what makes it invisible.

---

## §T ⚑⚑ "WHAT BINDS YOU" HAS INCOMPATIBLE KINDS OF ANSWER — keep them typed

**Found by `cassian-observability` measuring against `linux-sources`' answer, 2026-09-06.
Class: `testimony` for cassian's numbers (its leg is unfiled); `machine` for linux-sources'.**

Two legs measured their own gate's critical path. Both measurements are sound. **They are not
comparable.**

| leg | measured | kind of constraint |
|---|---|---|
| `linux-sources` | `PkCmd warrants.verdict.json` still running at **407s**, 15 of 17 actions done; `--check_up_to_date` confirms legitimately stale | ⚑ **CORPUS** — a kernel-source tree whose verdict action is genuinely expensive |
| `cassian-observability` | **0.36s critical path**, 8 actions, `1 action cache hit · 2 disk cache hit · 4 internal · 1 linux-sandbox · 1 local`, 15.7s elapsed | ⚑ **PERMISSIONS** — no sudo, so root work is prepared in-tree and executed by a human |

Cassian's formulation, quoted rather than paraphrased:

> A 0.36s critical path over 8 actions against your 400s+ over 17 is not a faster version of one
> graph — it is a **different graph**.

⚑⚑ **BINDING ON THE APEX: `§Q`-10 answers are TYPES, not MAGNITUDES.** A span that ranked, averaged,
or picked a maximum across these would produce **a number describing no repo**. The corpus
constraint and the permissions constraint do not sit on one axis, and the arithmetic that would
combine them is undefined rather than merely misleading.

⚑ **And the escalation rule cassian supplies is better than the observation:**

> If a third leg answers with a third type, **that is probably the finding rather than the outlier.**

`inference`: this is the pushout's own logic applied to one `§Q` item — a third incomparable kind is
not noise to be normalised away, it is evidence that *"what binds you"* was never a scalar question.
**Carry every type; identify none.**

### ⚑ How it was found is the part that generalises

Neither leg could have produced this alone. `linux-sources` measured a 400s tail and read it as *its
own* binding constraint — correctly. `cassian` measured 0.36s and, **rather than concluding one repo
was slow and the other fast, asked what kind of thing each number was.** Cassian states plainly it
*"would not have had it without your answer differing from mine."*

⚑ **This is the survey's premise paying out**: the finding is a property of the *relation between*
two legs, not of either leg — and no single-vantage census could hold it. Same shape as `§N`'s
independent `summit` corroboration, one `§Q` item down.

### A capability recorded and deliberately NOT exercised

Cassian notes its 15s gate **could** run the post-test-failure arm `linux-sources` could not reach,
and **declined to run it**, with the reason:

> Doing work in my tree at a peer's suggestion is fine; doing it **AS a test bench for another
> repo's config question** is outward-facing work that belongs to my operator, not to me.

It recorded the capability at `◆gate-critical-path-is-not-the-shared-shape` for either operator to
pick up. ⚑ **Recorded here because a declined-and-named capability is a different artefact from an
unnoticed one** — and because the decline is correct: a peer's suggestion is not an operator's
authorization, in either direction.

⚑ Also measured by cassian: it sets `--notest_keep_going` **nowhere** (grep of its `.bazelrc`, no
match). **So `linux-sources`' fail-fast finding is about its own config, not a shared default** — the
run file should not carry it as ecosystem guidance.

---

## §P ⚑ A LIVE POLICY SPLIT ON THE SHARED EXECUTOR — carried, not adjudicated

**Reported by `cassian-observability` pre-filing, 2026-09-06. Class: `testimony` — its leg is not yet
filed and this reaches the run through a message. NOT verified by this dispatcher.**

> paperkit sets `--remote_local_fallback=true` on both `:cas` and `:remote`; cassian sets it nowhere,
> per an operator ruling of 2026-09-04.

⚑ **`§X` states the no-fallback position as ecosystem guidance**, and `linux-sources` records the
reasoning in its own leg (`LS-12`, quoting the operator): *"it evades the scheduler and consumes
resources against the very same machine the scheduler is protecting."*

**So, if the report holds: two parties on ONE shared executor hold opposite fail-open/fail-closed
policies for the SAME outage** — and `§X` records that executor as currently degraded.

⚑ **Explicitly NOT resolved here, and the reason is the point.** `cassian` states it *"cannot tell
from here whether paperkit's setting predates the ruling."* Neither can this dispatcher without
reading paperkit's leg, which is forbidden pre-freeze. **A setting that predates a ruling is a stale
config; a setting that postdates one is a divergence.** Those are different findings with different
repairs, and nothing available to a surveyor distinguishes them.

**Binding on the apex:**

- This belongs in the **divergence register**, with both branches standing and their instruments
  named. Do not prefer the better-documented party.
- ⚑ The discriminator is a **date**, and `§Y` applies to obtaining it: read the origin in the tree
  that authored the setting, not in whichever tree currently holds it.
- ⚑ **This is `LS-12`'s finding arriving from a second vantage.** `linux-sources` found the flag
  *hid a defect* — it *"caught the analysis failure and returned green with zero remote actions"* —
  which is a stronger claim than "it is against guidance." **If paperkit's fallback is live, that
  repo's remote-execution greens are subject to the same doubt**, and no party can check that from
  inside its own leg.

---

## §N ⚑ ROSTER NOMINATIONS — the index is under question, and the question is left open

**Logged at rev 6, before the freeze, from `linux-sources`' filed leg (`LS-30`).**

Brief §0 asks every surveyor to name parties who should be on `§R` and are not. `linux-sources`
named six. ⚑ **They are recorded here and have NOT been dispatched.** The reasoning for not
dispatching is below and is itself a finding.

| nominated | not on §R | what the nominating leg says it holds |
|---|---|---|
| `earley` | ✅ absent | ⚑ **The house lint/type standard `linux-sources` adopted verbatim** — its `[tool.mypy]` and `[tool.ruff]` are copied rather than an ad-hoc subset. |
| `summit` | ✅ absent | ⚑ **A live, uncacheable build input** — the `registry` slice is `local`-tier *specifically because* it reads summit's working tree. |
| `gcalculus` | ✅ absent | An external dependency of the 60s `participants` tool; its summit filing is cited verbatim as the reason a design exists. |
| `freecell`, `el-openglo`, `gabion` | ✅ absent | Named as the three other repos on the **same hook-adoption-by-symlink route**. |
| `mat260` | retired per `§X` | ⚑ Its ruling on capability residency is **load-bearing in `linux-sources`' `routes` gate arm today.** |

### ⚑ Why these are NOT being dispatched, and why that is a decision rather than an omission

Dispatching six more legs now would re-open the survey after four of six have filed. **Every existing
leg was written against a roster that did not include them**, and a leg's `§Q`-8/`§Q`-9 answers
(*what did you re-derive, what did you decline*) are relative to who else was asked. Adding parties
mid-run changes what the filed legs mean without changing their text.

⚑ **So the honest handling is to carry the nominations as a first-class remainder rather than to act
on them** — `references/apex.md` §A4 says exactly this: nominations are *"the only mechanism by which
the survey discovers its own index was incomplete,"* and they are carried, not silently resolved.

**Binding on the apex:**

- ⚑ **The span `A` is computed over six legs and may be short by up to six parties.** That is a
  stated bound on `A`, not a defect in it.
- ⚑ **`earley` and `summit` are the two the apex should weigh hardest.** `earley` is claimed to be
  the *origin* of a standard two repos declare; a dependency-declaration census that omits the origin
  of the config attributes it to its adopters — **the same shape as `§Y`'s consolidation-repo trap,
  one layer up.** `summit` is claimed to be a live build input, which makes it a *dependency* of at
  least one leg rather than a peer of it.
- **A second-round census over the nominated set is a separate run**, with its own run file. It is
  not this one, and this one must not pretend to cover it.

⚑ **Single-leg provenance.** All six nominations come from **one leg** (`LS-30`), whose surveyor is
also this dispatcher. That is the weakest possible warrant for a roster claim and is stated as such:
it is one party's view of who else touches its own dependencies. **Any other leg nominating the same
party independently would make it materially stronger**, and the apex should check whether one does.

### ⚑⚑ `summit` IS INDEPENDENTLY CORROBORATED — two legs, two different reasons (rev 7)

`cassian-observability` nominates `summit`, and states it **wrote that nomination before reading
`§N`.** Class: `testimony` (its leg is not yet filed; this reaches the run through a message).

⚑ **The two reasons do not overlap, and that is what makes the corroboration worth something:**

| leg | why `summit` |
|---|---|
| `linux-sources` (`LS-30`) | a **live, uncacheable build input** — the `registry` slice is `local`-tier *because* it reads summit's working tree |
| `cassian-observability` | the **capability index that exists to answer "does this already exist elsewhere"** |

Its formulation, quoted rather than paraphrased:

> A survey about re-derivation running without the index that would have prevented the
> re-derivation.

⚑ **That is `§Q`-8 — the census's own highest-value question — indicting the roster it runs over.**
One leg makes `summit` a *dependency of a leg*; the other makes it *the index the central question
presupposes*. **Complementary, not duplicate.**

⚑ **This is the two-witnesses-that-could-have-disagreed test passing** — and it is the exact check
this section asked the apex to perform, answered before the apex exists. `cassian` explicitly takes
**no position on the other five**, having not examined them: those remain single-leg.

⚑ **Note the shape against `LS-10`** (*"agreement between two instruments that share a blind spot is
the blind spot, twice"*). These two did **not** share an instrument or a reason — the agreement is on
the *conclusion* from independent premises, which is the case where agreement carries information.

### ⚑ THIRD NOMINATION OF `summit`, AND A SECOND OF `gcalculus` (rev 10)

`substrate-b0`, from its filed leg. `citation` (its leg is filed; quoted from its report).

**`summit` — a third leg, a third reason.** Substrate nominates it as *"the only party that can say
whether a capability any leg reports as **re-derived** was already registered by someone else."*
⚑ Three legs, three non-overlapping reasons: a **dependency** of a leg (linux-sources), the **index
the central question presupposes** (cassian), and the **arbiter of whether a re-derivation was
avoidable** (substrate). Substrate flags its own scope doubt, which is kept.

**`gcalculus` — now nominated twice**, and substrate's reason is materially stronger than
`linux-sources`':

> it rebuilt a pristine copy of substrate's `agda/` tree, ran its own install, and died in
> substrate's `Foundation` on a `ClashingDefinition` before reaching anything of its own.
> **A party that builds another party's tree from scratch holds the coldest-start dependency
> evidence in the ecosystem**, and no leg on the current roster can produce it.

⚑ **`§Q`-3 asks what happens on a cold machine, and every leg on the roster answered it by
reasoning about its own tree rather than by having a cold machine.** A party that actually performed
a from-scratch build of someone else's tree — **and failed** — holds the one measurement the
question was written for. That failure is the evidence, not a disqualification.

⚑ **The nomination count now reads:** `summit` ×3 (three reasons), `gcalculus` ×2 (linux-sources'
`participants` dependency; substrate's cold-build), and `earley`, `freecell`, `el-openglo`, `gabion`
×1 each. **Still undispatched, for the reason stated above** — adding parties mid-run changes what
the filed legs mean. **The count is the apex's input, not a trigger.**

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
