# CENSUS: `deps-build` — run file

**Brief:** `findings/CENSUS-BRIEF.md` rev 1. Read it first. This file overrides it where they conflict.

## ⚑⚑ THIS FILE IS CONTROL FLOW ONLY — a surveyor may read all of it, pre-freeze

**Split at `§V` rev 12.** `§G` made this file **mandatory** to poll (the freeze lives in `§V`), while
it also carried cross-leg findings — so a leg polling for the freeze was reading peers' findings,
**with no point at which it could stop**, because a heading names its conclusion rather than its
provenance.

| section | where it lives now |
|---|---|
| `§Y` origin attribution · `§Z` self-mis-grading · `§P` the fallback split · `§T` typed constraints · `§M` the reader defect · `§N`'s per-party reasons | ⚑ **`CENSUS-deps-build-ANALYSIS.md` — EMBARGOED until the freeze** |

⚑ **Nothing was deleted.** Every moved section is in the companion, verbatim, with its provenance
class. **`§M` is binding on the apex** and is the sharpest operational item in the run; a surveyor
reads it after the freeze, an apex reads it first.

⚑ **Findings must not land in this file again.** If cross-leg material appears here, the same defect
returns — that is `§H` in the companion, and it is a class rather than an incident.

⚑⚑ **THE TABLE ABOVE IS CONTENT, NOT NAVIGATION — do not drop it in a regeneration, projection, or
trim.** It is the only thing standing between a future reader and *"`§T` was deleted."* Raised by
`substrate-b0` (`gate-G16`), and the argument is this dispatcher's own bad cut during the split:
**a section that vanishes without a marker reads as never having existed**, and a shorter file that
parses looks exactly like a correct one. **A removal stays honest only while its pointer survives.**

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
| 11 | 2026-09-06 | ⚑⚑ **`mdstruct --headers` SILENTLY DROPS SECTIONS — cross-check with `--budget`.** Now `§M` in the **companion**. | apex phase 1; every leg read |
| 12 | 2026-09-06 | ⚑⚑ **FILE SPLIT. This file is control flow ONLY; cross-leg findings move to `CENSUS-deps-build-ANALYSIS.md`, embargoed until the freeze.** Ruling on `substrate`'s `gate-G14`. **No leg need re-read anything; a leg that polled `§V`/`§S`/`§G` read nothing it should not have.** | every leg's embargo; the apex reads both |

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

## §F ⚑ THE FREEZE ROSTER IS MEASURED, NOT REMEMBERED

**Logged at rev 5 after this dispatcher's own outstanding-list went stale by two legs.**

At rev 4 this dispatcher stated four legs outstanding. **Two had already filed.** The list was a
recollection of who had *messaged*, not a measurement of what was *on disk*, and no leg announces
its filing by obligation. ⚑ **Had the freeze been called on it, `A` would have been computed over
the wrong `N`.**

> **Before calling the freeze, list the directory.** The `filed` / `declined` / `no response` marks
> are read off the filesystem at that moment, never accumulated from messages during the run.

    find <repo>/findings/deps-build/ -maxdepth 1 -type f -printf '%s\t%TH:%TM\t%f\n'

⚑ **A filing is an artifact, not an event.** A leg that files silently is filed; a leg that messages
without filing is not. **A green, an idle notice and a commit hash are events**, and they read as
progress on whatever the reader is tracking — that near-miss has already happened once in this run.

⚑ **Same shape as `§Y`** (companion): there a `git log` date stood in for an origin witness, here a
message for a filing witness. **Both replace an artifact-of-record with a convenient-adjacent
signal** — and the convenient one arrives unbidden while the record must be gone and looked at.

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

### The per-party reasoning is in the companion

⚡ Nomination **counts** and the **decision** not to dispatch are above; the reasons quote legs
verbatim and live at `§N-detail` in `CENSUS-deps-build-ANALYSIS.md`, embargoed until the freeze.

**Counts, for a surveyor who may read this file:** `summit` nominated by THREE legs, for three
non-overlapping reasons, one written before its author had read this section. `gcalculus` by TWO.
`earley`, `freecell`, `el-openglo`, `gabion` by one each. **Undispatched**, for the reason above.
