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
| 2 | 2026-09-06 | `rosettapkg` dispatched later than the other five — no session existed at rev 1. **Byte-identical message, no substitution.** A dispatch-time asymmetry, not a content one; all six received the same bytes, only the clock differed. No leg need re-read anything. | apex §accounting; `rosettapkg`'s brief §9 disclosure |
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
| 13 | 2026-09-06 | ⚑⚑⚑ **THIS TABLE WAS BROKEN AND THE FREEZE ROW WOULD HAVE BEEN INVISIBLE.** A prose paragraph after rev 2 terminated the GFM table; **revs 3–12 decoded as paragraphs**, so a structural reader saw a 2-row `§V`. Reported by `mtools-ce`, verified here (`mdstruct --rows`: `t2` returned 2 of 12). Prose folded into rev 2's cell; the table is now unbroken. ⚑ **No prose may interrupt this table.** | every leg polling for the freeze |
| 14 | 2026-09-06 | ⚑⚑⚑ **THE REPAIR TRIPPED ITS OWN PREDICATE.** Rev 13's cell contained the literal trigger string while announcing no freeze, so `--where` matched **with the control passing** — a leg obeying `§G` would have begun cross-reading. Reported by `mtools-ce`, reproduced here. Trigger string removed from rev 13; the freeze predicate is now **anchored**, see `§G`. ⚑ **A document that explains its own predicate accretes mentions of its own trigger, and every repair adds one.** | every leg polling for the freeze |
| 15 | 2026-09-06 | ⚑ **THE `§S` PREDICATE IS ARMED, AND ARMING FOUND A HOLE.** Both arms run (1 non-terminal, 5 terminal, 6 = roster). ⚑⚑ **A party silently absent from `§S` says nothing, exactly like a party with no non-terminal status — so a dropped row reads as FROZEN.** The freeze condition now requires a **count identity** (`§S` rows == `§R` surveyors) as well as no non-terminal status. `§F` reappearing inside the instrument built to prevent it. | the freeze; every leg polling |
| 16 | 2026-09-06 | ⚑⚑ **TWO `mdstruct` IMPLEMENTATIONS; THE COLUMN-SCOPED PREDICATE IS IN THE ONE THIS REPO'S ROUTING DOES NOT NAME.** `mtools-ce` built `rows --col N --starts TEXT` in `mtools/mdstruct/`; the reader `hook_structural_query` mandates (`substrate/scratch/mdstruct.py`) has no such mode — measured, exit 2. **`§G` keeps the `--where` + count-identity poll.** ⚑ **This is `§Q`-8 generated by the survey's own instrument, mid-survey.** ⚑⚑ **SEE REV 17: this row first said UNREACHABLE, which was too strong and is corrected there.** | `§G`'s predicate; apex `§Q`-8 |
| 17 | 2026-09-06 | ⚑⚑ **CORRECTION TO REV 16 — "UNREACHABLE" WAS AN OVERCLAIM.** The console script `mtools/mdstruct/.venv/bin/mdstruct` **runs from this session**, arbitrary cwd, absolute path, no venv activation: `--col 2 --starts "FILE SPLIT"` returns rev 12; `--col 1 --starts "in progress"` returns cassian's `§S` row, skipping the `⚑` decoration correctly. ⚑ **What is missing is a ROUTING ENTRY, not a capability.** I measured *one* invocation (a relative path to substrate's copy), found it lacked the mode, and reported a fact about **my invocation** as a fact about **the world** — the exact class this run keeps filing. **`§G` still keeps `--where`**, now for the correct reason: see `§G`. | `§G`'s predicate; apex `§Q`-8 |
| 18 | 2026-09-06 | ⚑⚑ **`in progress` COLLAPSES TWO STATES; THE FREEZE IS BLOCKED ON A WRITE PERMISSION, NOT ON WORK.** Cassian's leg **verified by the dispatcher** at `cassian-observability/docs/census-deps-build-leg.md` — 30,795 B, complete, larger than three filed legs. So the survey is not incomplete; a **copy** is held by another operator, and `§S`'s vocabulary cannot express that difference. ⚑ **Three options are named at the end of `§S` and the dispatcher declines to choose** — each spends someone else's authority. Freeze stays uncalled until an operator rules. | the freeze; **the operator** |
| 19 | 2026-09-06 | ⚑⚑⚑ **EVERY SURVEYING SESSION HAS BEEN REPLACED; "THIS SESSION" IN A LEG NAMES A PARTY THAT NO LONGER EXISTS.** Found by `mtools-2e` (was `mtools-ce`); this dispatcher is now `linux-sources-f6` and filed `LS-` as `-d2`. **Ten deictic references across five of five legs** — a property of the census, not one party's slip. ⚑ **THE APEX MUST READ "this session" / "me" / "this survey" in a leg as *the filing party at filing time, no longer reachable*.** ⚑⚑ **Legs are NOT to be amended.** See `§D`. | apex reading of every leg |

⚑ **RULE, and it is why rev 13 exists rather than a silent fix:** ⚑⚑ **NOTHING MAY BE WRITTEN BETWEEN
THE ROWS OF THIS TABLE.** A GFM table ends at the first non-row block; every row after that decodes
as a paragraph. Commentary on a revision goes **in its own cell** or **below the table**, never
between rows. `§G` designates this table as the freeze instrument, so a break here makes the only
observable event in the run unobservable to exactly the readers `§G` told everyone to use.

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

### ⚑ The predicate — and why a substring is not one

⚑⚑ **THE FREEZE IS `§S`, NOT A STRING.** The event is: **every party in `§S` carries a terminal
status** — `filed`, `declined`, or `no response` — and none reads `in progress`. `§6` requires that
accounting to exist before the apex begins, so **the roster IS the freeze**; a `§V` row is its
announcement, not its substance. *(`mtools-ce`'s formulation, adopted.)*

**Read `§S`'s table rows.** Not its heading — ⚑ per rev 13's rule a heading is not a row, so
`## §S … NOT YET CALLED` is human-legible and **not machine-pollable**; do not key on it.

⚑⚑ **A SUBSTRING PREDICATE CANNOT WORK HERE, AND THIS IS MEASURED TWICE.** `grep -i "freeze called"`
false-positives on `§G`'s own prose describing the rule. Then rev 13 — **the fix for the broken
table** — put the literal trigger in a cell, so `--where "FREEZE CALLED"` matched **with the control
passing** while `§S` still read *in progress*. Both readers wrong, in opposite directions.

> ⚑ **A document that explains its own predicate accretes mentions of its own trigger, and every
> repair adds one.** The instrument's own maintenance is the contaminant.

**Until a column-scoped mode exists** (`mtools-ce` owns `mdstruct` and is building one; `--where` is
row-wide free text with no column scoping, and `rows` truncates cells to ~40 chars for *display*
while matching the full cell — so eyeballing the output is not a check):

- **Poll `§S`'s rows** and require every status terminal. That is a statement about the roster, not
  about a string, and no amount of prose about freezing can satisfy it.
- ⚑⚑ **IDENTIFY `§S` BY ITS HEADER SIGNATURE, NEVER BY A TABLE INDEX.** `--table N` is positional
  and **renumbers the moment a section carrying a table is inserted above it** — which happened at
  rev 19, when `§D` was added and its table became `t5`. Confirm with `--tables` and take the one
  whose header is exactly `['party', 'status', 'evidence']`:

      mdstruct --tables  FILE          # find the party/status/evidence table
      mdstruct --rows    FILE --table <that N> --where "in progress"

  ⚑ **A predicate keyed on position is a predicate that silently retargets** — the same defect the
  ledger's symbol-stability contract exists to prevent, in the freeze instrument. *(Caught while
  adding `§D`; `t4` was still correct, which is exactly why it needed checking rather than assuming.)*
- ⚑ **Arm it first.** Ask for a row that **does** exist and confirm it returns — a poll that says
  *"not called"* is indistinguishable from one that **cannot see rows at all**, and that state is
  not hypothetical: this table was broken from rev 3 to rev 12 and every structural reader saw two
  rows. **Brief §5's positive control, applied to a control-flow predicate.**
- **A `FREEZE CALLED` row in `§V` remains the human-facing announcement.** ⚑ It is corroboration,
  never the sole trigger — rev 14 is why.

#### ⚑ The predicate ARMED, 2026-09-06 — both arms, and the hole they leave

Written last revision and **not armed until now**, which is the defect rev 14 records, one turn later.
A predicate stated is not a predicate exercised:

    --where "in progress"  ->  1 of 33   cassian-observability      NON-TERMINAL, correct
    --where "filed"        ->  5 of 33   the other five             CONTROL: statuses ARE readable

**5 terminal + 1 non-terminal = 6 = the roster.** The predicate reads `§S` and discriminates; a
freeze poll today correctly returns *not frozen*.

⚑⚑ **AND THE ARMING EXPOSES A HOLE NOTHING CHECKS: the count identity is load-bearing and unasserted.**
*"No row says `in progress`"* is the freeze condition, and **a party silently absent from `§S` also
says nothing** — so a dropped row reads as frozen. The two states are distinguishable only by
counting.

> **The freeze condition is: `§S` has exactly as many rows as `§R` has surveyors, AND none is
> non-terminal.** Poll both. ⚑ *A completeness check is not optional here — this is `§F`
> (`A` computed over the wrong `N`) reappearing inside the instrument that exists to prevent it.*

**Current:** `§R` lists 6 surveyors + the apex; `§S` holds 6 rows. Identity holds.

#### ⚑⚑ TWO `mdstruct`s EXIST, AND THE COLUMN-SCOPED MODE IS IN THE ONE THIS RUN CANNOT REACH

`mtools-ce` built the column-scoped predicate (`rows FILE --col N --starts TEXT`) that would replace
the substring poll, and measured it against this file. ⚑ **It is not reachable from a surveyor
following this repo's own routing.**

| implementation | who routes to it | has `--col`/`--starts` |
|---|---|---|
| `substrate/scratch/mdstruct.py` | ⚑ `hook_structural_query` names it as *"the tool that owns"* any `.md` | **no** — `--help` lists no such mode; `rows` is not even a subcommand form |
| `mtools/mdstruct/` (`src/mikemol/mdstruct/`) | `mtools` itself | **yes**, committed 2026-09-06 ~01:57 |

**Measured from this session:** `python3 ../substrate/scratch/mdstruct.py rows … --col 1 --starts …`
→ `rows does not exist`, exit 2.

⚑⚑ **BUT "UNAVAILABLE" WAS AN OVERCLAIM, CORRECTED AT REV 17.** The console script runs fine from
here — arbitrary cwd, absolute path, no venv activation:

    mtools/mdstruct/.venv/bin/mdstruct rows <abs path> --col 1 --starts "in progress"
    -> table 4  cassian-observability | ⚑ in progress — held | …        rc=0

It reads `§S` correctly **and skips the `⚑` decoration**, which is the detail that would have made a
naive anchor return a clean-looking negative. ⚑ **I measured ONE invocation, found it lacked the
mode, and reported a fact about my invocation as a fact about the world** — the class this run keeps
filing, committed while filing it.

⚑ **So the run keeps `--where` + count-identity for a DIFFERENT and better reason.** Not *"the mode
does not exist"* — it does. **The mode is reachable from this session by an absolute path into
another repo's venv, and that is not a routing a brief may impose on six legs.** This repo's
`SKILL.md` routes `.md` to `../substrate/scratch/mdstruct.py` by relative path; hardcoding a
cross-repo absolute path would trade one routing failure for a worse one. ⚑ *(`mtools-ce` argued
this against its own tool, and it is the right call: the unblock is the packaging ruling landing,
not a path.)*

⚑⚑ **THIS IS `§Q`-8 HAPPENING TO THE CENSUS ITSELF, IN REAL TIME.** Two implementations of one tool,
diverging, with a fix landing in the copy its author holds — and `§M` already records that the
routing hook **compels** the other copy fleet-wide. **The census's highest-value question is
"what did you re-derive"; the answer is being generated by the survey's own instrument while the
survey runs.** For the apex: this is evidence, not an aside.

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

## §D ⚑⚑⚑ A FILED DOCUMENT HAS NO SPEAKER — how the apex reads "this session"

**Found by `mtools-2e` (filed its leg as `mtools-ce`), 2026-09-06. Verified here.**

Every surveying session has been replaced. This dispatcher is now **`linux-sources-f6`** and filed
`LS-` as **`-d2`**; `ListAgents` shows all five peers under new names with start times of minutes.
`mtools-2e` measured the exposure — **ten deictic references across five of five legs**
(`linux-sources` 1, `mtools` 1, `paperkit` 1, `rosettapkg` 5, `substrate` 2), counts only, no leg
read. ⚑ **Five of five makes it a property of the census, not one party's slip.**

⚑⚑ **THE GENERAL FORM, which is the mirror of `§F` and worth more than the incident:**

> **A deictic is a claim whose truth depends on who is speaking, and a filed document has no
> speaker.** `§F` says an arriving signal gets substituted for a record you must go and read. **This
> is the inverse: a record that reads as self-contained carries a pointer to its own writing
> context, and filing is precisely the operation that discards that context.**

⚑ **The substitution is invisible because the sentence stays grammatical.** `LS-24`'s heading —
*"FOUR GATES FIRED ON ME DURING THIS SURVEY"* — still parses, still reads as a first-person
measurement, and now points at nobody.

### The ruling

1. ⚑ **The apex reads "this session", "me", "I", "this survey" in a leg as: *the filing party at
   filing time, no longer reachable*.** The reference still resolves to **authorship**, which is what
   brief §9 asked each leg to disclose. Nothing in any leg is invalidated.
2. ⚑⚑ **LEGS ARE NOT TO BE AMENDED.** `mtools-2e` declined to rewrite its own leg to name
   `mtools-ce`, and that decline is correct and now binding: **rewriting a filed leg after the freeze
   roster has accounted it is amending the record behind the accounting.** The correction belongs in
   **how the apex reads**, not in the artifacts.
3. ⚑ **Any instruction of the form "ask the filing party" is now unexecutable for all six** and must
   not be written into the apex's procedure. **Cross-examination is gone; the legs are not.**

### What this does NOT cost

**Nothing filed is stale.** Each leg is committed, readable, unchanged, and its `§9` disclosure still
identifies its author correctly *as an author*. The loss is narrow and should be stated narrowly:
**a reader can no longer ask a leg's writer what it meant**, and an apex correlating a leg with a
live peer of the same repo **will correlate it with a stranger**.

⚑ **And `§G` is confirmed by the same event.** The embargo survived the replacement of every party
that agreed to it — **because it was made an artifact rather than a message.** A message-borne
embargo would have died with `-d2`, `-ce`, `-b7`, `-b0`, `-86` and `-0a`. *That is the argument for
`§G` running, not asserted.*

## §S Freeze roster — ⚑ NOT YET CALLED

| party | status | evidence |
|---|---|---|
| `paperkit` | **filed** | `paperkit-deps-build.md` |
| `substrate` | **filed** | `substrate-deps-build.md`, `SB-01`–`SB-10`, against rev 1 |
| `mtools` | **filed** | `mtools-deps-build.md`, `MT-01`–`MT-13`, against rev 1 |
| `rosettapkg` | **filed** | `rosettapkg-deps-build.md` |
| `linux-sources` | **filed** | `linux-sources-deps-build.md`, `LS-01`–`LS-30` |
| `cassian-observability` | ⚑ **in progress — held** | ⚑ **VERIFIED 2026-09-06 by the dispatcher, not carried on report:** `cassian-observability/docs/census-deps-build-leg.md`, **30,795 bytes, mtime 00:45** — larger than three filed legs. Blocked on **its operator's hold against writing to mtools**. Not a decline; the dispatch was usable. |

⚑ **This table is provisional and is re-measured at freeze time, never carried forward** (`§F`).

### ⚑⚑ `in progress` IS COLLAPSING TWO STATES, AND THE OPERATOR SHOULD DECIDE WHICH ONE THIS IS

**Measured 2026-09-06.** `§S` gives `cassian-observability` one non-terminal status, and that single
label is covering two different situations:

| state | what it means for the apex |
|---|---|
| **the leg does not exist yet** | waiting is the only option; the survey is genuinely incomplete |
| ⚑ **the leg EXISTS and is COMPLETE; only its LOCATION is held** | the content is written and reviewable; what is missing is a **copy**, not a survey |

**It is the second.** Verified above: 30,795 bytes, complete, in cassian's own tree.

⚑ **So the freeze is not blocked on work — it is blocked on a WRITE PERMISSION that belongs to
another operator**, and `§S`'s vocabulary cannot say so. That is the same collapse this run keeps
finding: `§F` (a message mistaken for a filing), the count identity (an absent row reading as
terminal), and now **a location-hold reading as incomplete work.**

⚑ **THIS IS AN OPERATOR DECISION AND THE DISPATCHER WILL NOT MAKE IT.** Three options, stated
without a recommendation because each spends someone else's authority:

1. **Wait** for the hold to lift. Costs nothing; unbounded.
2. **Freeze at five**, recording cassian as a **remainder entry with an accurate cause** — cassian's
   own framing: *"a freeze delayed on an unbounded wait is worse for the run than a remainder entry
   with an accurate cause."*
3. **Point the apex at the leg in place** (`cassian:docs/census-deps-build-leg.md`). ⚑ Requires
   **cassian's operator** to sanction reading it there, and this dispatcher will not arrange it
   between sessions — *a peer's suggestion is not an operator's authorization, in either direction.*

**Until an operator rules, `§S` stays non-terminal and the freeze stays uncalled.** ⚑ The
distinction is now *in the record* rather than in a message, so whoever rules can see what they are
ruling on.

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
