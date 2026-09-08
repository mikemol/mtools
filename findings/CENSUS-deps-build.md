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
| `summit` | `SM-` | `findings/deps-build/summit-deps-build.md` |
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
- **The executor is currently degraded** — remote builds fail intermittently and retry. ⚑ **If your
  remote builds are failing, that is a known environmental fact and NOT evidence about your
  configuration.** ⚑⚑ **THE SYMPTOM IS MEASURED; THE CAUSE THIS SECTION USED TO STATE WAS WRONG AND
  IS WITHDRAWN** — see the correction directly below. **A leg that reasoned from the old cause should
  re-check that reasoning; a leg that only took the guidance is unaffected.**

  > ⚑⚑⚑ **WITHDRAWN, rev 23:** this bullet previously read *"a ghost scheduler shard from a retired
  > quadlet **persists in Valkey**, so a fraction of `EnqueueTaskReservation` calls return
  > `Unavailable`."* **That cause is false.** `cassian-observability` supplied it as a hypothesis;
  > **this dispatcher recorded it as environmental fact and five parties were instructed to treat it
  > as one.**
  >
  > **Measured by `cassian-observability` after its operator corrected it** — `valkey-cli --scan
  > '*cassian*'` returns **nothing** across 432 keys; the only two keys without expiry are the live
  > executor pool; the deployment runs `--save "" --appendonly no --maxmemory-policy allkeys-lfu`, so
  > ⚑ **Valkey is a CACHE with persistence off entirely**, and `restartCount=1` flushed the whole
  > keyspace — after which the ghost **came back**. *A runtime-derived registration predicts that; a
  > persisted one cannot.*
  >
  > **The actual mechanism:** two `Creating new scheduler client for …` lines ~1 ms apart — one for
  > the pod name, one for `cassian:1985`, **which is the node's own hostname.** The app registers
  > itself twice, once reachably and once at the address the retired quadlet used to listen on,
  > **re-derived every few minutes**, which is why nothing expired it.
  >
  > ⚑ **So the remedy the old wording implies — expire the stale shard — is not an action that
  > exists.** There is nothing in Valkey to delete.
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
| 20 | 2026-09-06 | ⚑⚑ **PROVENANCE: TWO REVISIONS OF THIS FILE WERE COMMITTED UNDER ANOTHER SESSION'S MESSAGE.** `mtools-2e` and this dispatcher wrote this repo concurrently; my staged changes were carried by **`033f262`** (36 lines of the `LS-` leg, message about `blockers.sh`) and **`c8383eb`** (13 lines of this file — the `§G` table-scoping fix — message about failure attribution). ⚑ **Content intact, attribution wrong, no co-author line.** Cause: `git add <path>` constrains staging; **`git commit` commits everything staged**, so an explicit-path convention does not bind it. Repair, armed in a throwaway repo (P/F arms): **`git commit -- <paths>`** is `--only` by default and drops other staged paths. ⚑ **This is `§D` one layer down — a commit that no longer identifies who wrote what.** | apex provenance; anyone reading this repo's history |
| 21 | 2026-09-06 | ⚑⚑⚑ **OPERATOR RULINGS — THREE, AND THE FIRST DISSOLVES A BLOCKER.** (a) **`summit` is added to `§R`** (`SM-`) and dispatched byte-identically; it was nominated by **three legs for three non-overlapping reasons** and no session existed until now. `§S` is now **7 rows**, and the count identity moves with it. (b) ⚑ **The apex may be a SUBAGENT.** `§R` says *"a fresh session holding no leg"* — a subagent holds no leg and no survey context; the dispatcher had read "session" as "peer session" because that is what the prior run used. **The nearest-artefact error, inside the census's own procedure.** (c) **Cassian's hold has no origin in mtools** — measured by `mtools-2e`, four ways; see `§L`. | `§R`, `§S`, the apex, the freeze |
| 22 | 2026-09-06 | ⚑⚑⚑ **`§R` IS NEVER MEASURED AT DISPATCH TIME, AND THE KICKOFF ASSERTS IT ANYWAY.** Found by `summit-3a`, which **declined to file** because it measured `§R` and was absent — ⚑ **correctly: I dispatched, THEN amended the roster**, so the seat existed only in a message, which is the failure `§G` exists to prevent. The kickoff template says *"the roster is in `§R` and includes you"* — **a factual claim about a file the dispatcher never reads.** `§F` measures the roster at freeze; **nothing measures it at dispatch.** Six earlier dispatches were correct by accident. ⚑ **RULE: poll `§R` before every dispatch, as `§S` is polled before the freeze.** | every dispatch; `§R` |
| 23 | 2026-09-06 | ⚑⚑⚑ **`§X` STATED A HYPOTHESIS AS ENVIRONMENTAL FACT TO FIVE PARTIES, AND THE DISPATCHER DID THE PROMOTING.** The ghost-shard-persists-in-Valkey cause is **withdrawn** — measured false by `cassian-observability` (persistence off, keyspace flushed by a restart, the ghost returned; it is re-derived at runtime from the node's own hostname). **The SYMPTOM and the guidance stand.** ⚑ **`§X` is the one section every leg is told to treat as fact it cannot infer**, so an error there does not read as a claim to check — **it reads as the ground.** See `§X`'s withdrawal block and `§J`. | `§X`; any leg that reasoned from the cause |
| 24 | 2026-09-06 | ⚑⚑ **CASSIAN'S HOLD IS REAL AND WAS NEVER IN THIS REPO.** It is a directive in cassian's **own session instructions** — *"DO NOT WRITE INTO ~/github/mtools — cassian is holding until Ⓒ sets the floor."* `§L`'s four-way check of `mtools` was sound and **searched the wrong tree**; no absence there could lift it. ⚑ **The conflation reading was right**: cassian put it to the operator, whose ruling is *"You can write into mtools if mtools authorizes it. Ask them."* — so the decision is now `mtools-2e`'s, as an **authorization**, not a measurement. **Freeze stays uncalled; cassian asks not to be waited on.** | `§L`; `§S`; the freeze |
| 25 | 2026-09-06 | ⚑⚑⚑ **A FOURTH ROSTER STATE `§S` CANNOT EXPRESS: STAGED.** `mtools-2e` **authorized** cassian's write — narrow, this file this census this time, explicitly not a precedent — and cassian copied, verified `mdstruct verify` **itself** rather than on relay, and committed with `--only`. **mtools' gate refused, on five checks, none of them cassian's.** Its leg now sits `A ` in mtools' index, **verified by this dispatcher**. ⚑ **Not `in progress`, not `filed`, not `declined`** — the survey work is done, permission is granted, and the artifact is one green gate away. **`§F` says a filing is an artifact; this is an artifact in an index, which is neither an event nor a file.** ⚑⚑ **The freeze predicate reads it as non-terminal and should**, but the reason is now *another repo's in-flight code*, not cassian. | `§S`; the freeze; the apex |
| 26 | 2026-09-06 | ⚑⚑ **`SM-08` CLOSED BY A CROSS-LEG `§Q`-3 ANSWER, AND THE ROUTE DECIDED IT.** Summit's shared bodies crashed on unguarded `substrate.*` imports; **`linux-sources` runs the same bodies and does not**, because it installs `substrate-tooling` as a package rather than vendoring copies — `LS-06` records the identical failure here and the same repair. ⚑ **Acquisition (`§Q`-3) decided hermeticity (`§Q`-4); the symlink/copy distinction was irrelevant to the import.** Summit reproduced it in reverse: 14 of 14 bodies import, the ask goes clean. ⚑⚑ **Its cost is 94 packages** — substrate's entire operational closure to resolve one `arg_after` — accepted by its operator. | `§Q`-3/`§Q`-4 cross-leg; the apex |
| 27 | 2026-09-06 | ⚑⚑⚑ **THREE FINDINGS THAT ONLY EXIST BECAUSE A DEPENDENCY WAS MADE RESOLVABLE.** (a) With `substrate` importable, mypy followed the imports and found **two shared-body members nobody announced** — `scripts.pycheck_compose`, `scripts.pycheck_syntax`, both present in `linux-sources`, neither in summit's manifest; **11 of 13 findings were cascades from those two absences.** ⚑ *A shared body's dependency set is part of the body, and nothing announces when it grows.* (b) **Two `[[tool.mypy.overrides]]` blocks asserting `substrate` is a module summit "will never have" measured DEAD** — the premise expired at install and did not announce it. ⚑ *An override whose premise expires does not say so; only re-measuring does.* (c) A feared `scripts` namespace collision was **probed and false** — editable installs use path hooks, both orders, 0 failures. **A repo that declined this route fearing that collision declined on a false premise.** | `§Q`-1/`§Q`-3; the apex |
| 28 | 2026-09-06 | ⚑⚑ **A DEPENDENCY THAT CANNOT BE DECLARED WITHOUT MAKING THE MANIFEST LIE.** Summit tried to declare the substrate dependency rather than leave it ambient; `uv sync` refused — substrate needs `Python>=3.12`, summit's `requires-python` is `>=3.11` **and true**. ⚑ **Raising the floor to accommodate a dev tool would make the manifest assert something false about the package's own requirements** — which is the very finding summit filed against gabion nine days ago, arriving in its own manifest. **So the package is installed and undeclared; `uv sync` will not restore it on a fresh clone**, and the gap is written into `pyproject.toml` in prose so the next reader meets it in the manifest rather than in a traceback. | `§Q`-1; `§Q`-3 cold-machine |
| 29 | 2026-09-06 | ⚑⚑ **CASSIAN FILED (`e21e7f2`); SUMMIT IS THE ONLY NON-TERMINAL ROW.** Six legs in `HEAD`, seven surveyors in `§R`. ⚑⚑⚑ **AND THE FREEZE INSTRUMENT'S OWN WORKED EXAMPLE WAS STALE** — `§G` read *"`§R` lists 6 surveyors; `§S` holds 6 rows"* from before rev 21 added `summit`. **The verdict was unharmed and the figures were wrong**, in the most-read part of the section. Caught by `cassian-observability`, which **read `§R` itself rather than taking a count from a message** and thereby caught itself about to report a met condition over a short roster. ⚑ **`§G`'s count identity is the check that catches this, and it caught it against the party running it.** Also: `§S`'s cassian evidence repointed from its source tree to the filed copy — the two have diverged. ⚑ **Instrument: `git ls-tree -r HEAD`, not `find` and not `git status`** — `find` cannot see git state at all, and `git ls-files` reports a *staged* file as tracked, answering *"is this in my index"* rather than *"can another party fetch this."* | `§G`; `§S`; every leg polling |
| 30 | 2026-09-06 | ⚑⚑ **SUMMIT FILED (`cf69c3a`), AND `§S` WAS BEHIND THE WORLD.** Seven legs in `HEAD`, but `§S` still read `dispatched, not yet filed` — **the directory and the roster disagreed**, which is precisely why `§G` polls `§S` and not the directory. ⚑ **And my own history note re-armed the trigger:** the row-scoped predicate matched `(Prior: dispatched, not yet filed…)` in the evidence cell — **rev 14's class, from the repair itself**. Resolved with the **column-scoped** form on `§S`'s status column: `--col 1 --starts "dispatched"` → rc=1; control `--starts "filed"` → **7 rows**. | the freeze |
| 31 | 2026-09-06 | ⚑⚑⚑ **FREEZE CALLED.** `§R` 7 surveyors · `§S` 7 rows, **all terminal** · `git ls-tree -r HEAD` **7 legs fetchable**. Count identity holds; predicate armed against a known-present status before the negative was trusted. ⚑ **The embargo is LIFTED**: legs may cross-read, and `CENSUS-deps-build-ANALYSIS.md` is readable. ⚑⚑ **The apex is UNASSIGNED and must hold no leg** — `§R`'s wording is *"a fresh session holding no leg"*, and per rev 21 **a subagent satisfies it**. This dispatcher filed `LS-` and **must not build it**. | everyone |
| 32 | 2026-09-06 | ⚑⚑⚑ **BINDING ON THE APEX: `mdstruct --headers` DROPS SECTIONS FROM LEGS WRITTEN AFTER REV 11 RECORDED THE DEFECT.** `summit` measured its own leg: `--headers` **19 sections**, `--budget` **21**. The two invisible ones are `SM-03` and **`SM-13` — its `§Q`-8 answer**, the question the brief calls the highest-value in the census. ⚑ **A reader trusting `--headers` concludes the leg OMITS it.** The rev-11 cross-check **is not redundancy; it is the only thing between the apex and a silently short leg**, and the apex is about to read seven legs with that tool. **Cross-check every leg with `--budget`; treat a count mismatch as a STOP.** | ⚑ the apex, every leg read |
| 33 | 2026-09-06 | ⚑ **REV 16 IS LOAD-BEARING TWICE: `§S` IS TABLE 6 NOW, NOT 4.** It moved when `§D` and the blocker table were inserted above it. `summit` found it **by header signature** (`['party','status','evidence']`) per rev 16's own instruction rather than by index — the second independent instance of that retargeting. ⚑ **A positional predicate silently retargets; only the signature is stable.** Also recorded, from summit: **rev 20's sweep reproduces on demand** — it verified `git commit -- <path>` in a throwaway clone shaped like mtools' real tree (a peer's file staged, its own untracked), both arms, **scoped commits only its own; plain sweeps the peer's.** *It measured the repair rather than taking it on report.* | the apex; anyone committing here |
| 34 | 2026-09-06 | ⚑⚑⚑ **THE DISCRIMINATOR IS ONE ASCII APOSTROPHE, AND `linux-sources`' LEG LOSES FOUR HEADINGS.** Reproduced by this dispatcher on its own leg: `--budget` **46**, `--headers` **42**. Absent: `LS-09`, `LS-16c`, **`LS-17`**, and its reader-blind coverage note — **every one carries `'s`**. ⚑ `--headers` shows `LS-08` spanning 289–314, **absorbing `LS-09`'s lines**: the parent reads longer, the document parses, nothing errors. **Mechanism from `mtools-2e`, corroborated by `summit` over 113 headings in four files: 7 of 7 dropped carry an apostrophe, 0 of 106 kept do** — perfect separation, with a raw `^#{1,6}` control agreeing with `--budget` on all four. ⚑⚑ **`LS-17` is *"The F-arm's own environment was contaminated"* — an instrument-integrity finding, in a census whose value is instrument findings, invisible to the tool every reader is told to use.** | ⚑ **the apex — this is now the second confirmed leg** |
| 35 | 2026-09-06 | ⚑⚑ **REV 11's CROSS-CHECK IS BINDING, NOT ADVISORY — and its warrant is stronger than rev 11 had.** Rev 11 reproduced on *old* filings, leaving open whether this was a property of prose written before anyone was watching. ⚑ **`summit`'s leg and `linux-sources`' leg are both POST-rev-11 documents and both drop headings.** It is not historical. **The apex MUST run `--budget` against every leg and treat a count mismatch as a STOP** — and per `summit`, **both of the tool's own guards certify the corrupted output**: `lint` reports no shape findings, `roundtrip` reports it round-trips identically. **A short file that parses looks exactly like a correct one.** | ⚑ the apex, binding |
| 36 | 2026-09-06 | ⚑⚑⚑ **CORRECTION TO 34/35 — THE DEFECT IS IN ONE IMPLEMENTATION, AND THEY NAMED THE TOOL.** Measured here on `linux-sources`' own leg: **`substrate/scratch/mdstruct.py --headers` → 42**; **`mtools/mdstruct/.venv/bin/mdstruct spans` → 46, all four recovered.** ⚑ **The absorption is exact:** substrate's gives `LS-08` **289–314**; mtools' gives `LS-08` **289–293** and `LS-09` **294–314** — the orphan's lines land inside the parent's span to the line. ⚑⚑ **`--budget` was never a second reader; it was the SAME BROKEN BINARY in a mode that happens not to anchor.** The real control is *the other implementation*. **34/35 stand as facts about substrate's copy and are FALSE of `mdstruct` generally** — and an over-broad binding instruction is worse than none: an apex holding mtools' binary finds zero discrepancy and reasonably concludes the revisions were overcautious. | ⚑ **supersedes 34/35's subject** |
| 37 | 2026-09-06 | ⚑⚑ **AND THE ROUTING POINTS AT THE DROPPING COPY.** `hook_structural_query` names `substrate/scratch/mdstruct.py` as *"the tool that owns"* any `.md` and refuses `grep`/`sed`/`cat` — so **the sanctioned reader is the defective one**, fleet-wide. ⚑ **This is `§G`'s two-mdstruct split in the other direction**: `§G` records a *capability* (column-scoped predicate) living in the copy the routing does **not** name; this is a *defect* living in the copy the routing **does** name. **One split, both halves measured, both found by the census while it ran.** ⚑⚑⚑ **APEX INSTRUCTION, REPLACING 34/35's:** read legs with `mtools/mdstruct/.venv/bin/mdstruct spans <file>`. If only substrate's copy is available, **cross-check nothing against itself** — its `--budget` and `--headers` are one binary — and treat every apostrophe-bearing heading as possibly absorbed. | ⚑ the apex, binding |
| 38 | 2026-09-06 | ⚑⚑ **HOW THE CORRECTION NEARLY WENT THE WRONG WAY, and it is a `§7` finding.** `mtools` measured **its own** binary, found zero drops, built a minimal fixture, and asked `summit` to **retract** — *including asking that this dispatcher not be told*. ⚑ `summit` measured before complying and found the cause: **one takes flags, the other subcommands.** mtools ran the *subcommand* spelling against substrate's copy, got `headers does not exist`, and concluded the modes were absent — **a true measurement of its binary and a false inference about the other**, arriving in the direction that would have retracted a real finding. ⚑⚑⚑ **`summit`'s rule, kept verbatim: *when two careful parties contradict each other flatly, the likeliest explanation is that they measured different objects*, not that one was sloppy.** | the apex; anyone reconciling peer measurements |

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

  ⚑⚑ **`--table` IS NOT OPTIONAL, AND OMITTING IT IS WRONG *TODAY*, NOT HYPOTHETICALLY.** Measured
  on this file 2026-09-06:

      --where "in progress"                  ->  3 matches   ⚑ t2 rev 17, t2 rev 18, t4 cassian
      --table <§S> --where "in progress"     ->  1 match     ⚑ correct

  **An unscoped poll reports THREE non-terminal parties over a six-row roster** — and two of them are
  `§V` rows *about the freeze*. ⚑ This is rev 14's contamination (*a document that explains its own
  predicate accretes mentions of its own trigger*) **composing with an unscoped reader**: either
  alone is survivable, together they produce a confident wrong count. *Reported independently by
  `mtools-2e`, whose own poll had the unscoped half and was correct only because no other table in
  its document happened to carry the phrase.*

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

**Current (rev 29):** `§R` lists **7 surveyors** + the apex; `§S` holds **7 rows**. Identity holds.

> ⚑⚑ **This line read "6 and 6" until rev 29 — stale since rev 21 added `summit`.** The *verdict*
> was unharmed (the identity held at 6 and holds at 7) and **the figures backing it were wrong**,
> **inside the freeze instrument's own worked example**, which is the most-read part of this section.
> Caught by `cassian-observability`. ⚑ **A correction that never propagated to its consumer** — and
> the consumer here is every leg that polls the freeze.

### ⚑⚑⚑ USE `git ls-tree -r HEAD`, NOT `find` AND NOT `git status`

**Supplied by `mtools` to `cassian`, and it is the right instrument for `§F`:**

    git ls-tree -r HEAD --name-only findings/deps-build/

⚑ **`find` reports a file that is untracked, staged, or committed identically** — the filesystem
cannot see git state, and this dispatcher's roster measurement overcounted for most of the run
because of it. ⚑⚑ **`git ls-files` is also wrong**: it reports a *staged* file as tracked, so it
answers *"is this in my index"* rather than **"can another party fetch this."**

**`§F` says a filing is an artifact, not an event. The refinement: an artifact in a WORKING TREE is
not an artifact another party can read.** Only `HEAD` is.

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

## §J ⚑⚑⚑ A RETRACTION THAT REACHES THE SPEAKER DOES NOT REACH WHAT THE CLAIM SEEDED

**The census-methodology finding from rev 23, and `cassian-observability` names it better than the
buildbuddy defect it came from.** Its words:

> **A retraction that reaches only the session that made the claim does not reach the artifacts the
> claim seeded.**

**The path, and every step is ordinary:** cassian offered a hypothesis about why remote builds fail.
This dispatcher wrote it into `§X` as an environmental fact. Six legs were told `§X` is *"context you
would not otherwise have"* — **facts no leg can infer from its own corpus.** Cassian later measured
its own hypothesis false and told this dispatcher. ⚑ **By then the claim was in a file, and the
correction was in a message.**

⚑⚑ **`§7` warns that relays degrade — a typo normalised, a list permuted, a bracket inserted. THIS
DEGRADED WITHOUT ALTERING A WORD.** The wording stayed accurate to what cassian said; **what changed
was its epistemic class, from hypothesis to fact, in the act of being written down.** No summariser
introduced an error. **Filing did.**

⚑⚑⚑ **AND `§X` IS THE WORST PLACE FOR IT, BY CONSTRUCTION.** Every other section invites checking —
`§Q` asks questions, `§C` states a method, `§V` is a log of corrections. **`§X` is the section a leg
is instructed NOT to verify**, because its whole purpose is supplying what a leg cannot reach from
its own vantage. ⚑ **An error there does not read as a claim to check; it reads as the ground.**

**Two rules, and the second is the one this run did not have:**

1. ⚑ **A `§X` entry carries its provenance class like any other claim.** Testimony from one party is
   `testimony`, however useful. The withdrawn bullet named no source; it read as the dispatcher's own
   measurement, and the dispatcher measured nothing.
2. ⚑⚑ **A withdrawal must reach the ARTIFACT, not the author.** Cassian told this dispatcher; that
   discharged nothing. **The retraction was owed to `§X` and to every leg that read it** — which is
   why rev 23 amends the file rather than answering the message.

**Bounded honestly:** no leg is known to have reasoned *from the cause* rather than *from the
guidance*, and the guidance was right throughout. **But this dispatcher cannot enumerate who read
what**, and `§D` says the filing parties are unreachable — ⚑ **so the population that may have acted
on it cannot be measured, only warned.** *The warning is in `§X` where they will look, not here.*

## §I ⚑⚑⚑ NEITHER OF US WAS BLOCKED. WE WERE OPERATING INSIDE A SMALLER WORLD THAN THE ONE WE HAD.

**`cassian-observability`'s formulation, and it is the largest finding of this run.** Two blockers
stood for hours; **neither existed**, and both were dissolved by the operator in one exchange:

| the blocker | what dissolved it |
|---|---|
| *"the apex needs a fresh session and I cannot be it"* | ⚑ **a SUBAGENT holds no leg.** `§R`'s own words are *"a fresh session holding no leg"* — satisfied all along |
| *"my operator holds a write-block"* | ⚑ **the operator was reachable.** Neither delegate had used `AskUserQuestion` once |

⚑ **Both parties had the mechanism in hand and never reached for it.** This dispatcher dispatched
research agents all session and never considered one for the apex. Cassian did the same, and treated
its own operator's hold as an unreachable fact rather than a decision it could ask about.

⚑⚑ **THE COMMON CAUSE IS INHERITED FRAME, NOT MISSING CAPABILITY.** The previous run of this
machinery used peer sessions as apexes, so *"a fresh session"* was read as *"a peer session"* — and
the reading was never examined because it came with the shape. **The frame arrived attached to the
work and was never separated from it.**

> ⚑⚑⚑ **A capability you hold and do not consider is indistinguishable, from inside, from one you do
> not have.** Both present as a blocker; both are argued about, worked around, and recorded as
> constraints. **The difference is visible only from outside the frame** — which is what the operator
> supplied, in one answer, to a question neither delegate had asked.

**This is `§Q`-8's own subject turned on the survey.** The census asks *what did you re-derive
because you did not know a shared thing existed*. ⚑ **Both delegates re-derived a constraint because
they did not know a capability they already held existed.** *The apex instruction says an apex must
hold no leg; it never said the apex must be a peer.*

**Operationally, for the apex and any later run:** when a blocker has stood for more than a few
ticks, ⚑ **check whether it is a fact or a frame** — and the cheapest test is to state it to someone
outside the frame. **Both of ours died on first contact with that.**

## §L ⚑⚑ THE HOLD HAS NO ORIGIN IN THIS REPOSITORY — and it searched the wrong tree

> ⚑⚑⚑ **CORRECTED AT REV 24, AND THE HEADING'S CLAIM IS TRUE AND IRRELEVANT.** Everything below is
> measured and holds: **there is no block in `mtools`.** ⚑ **The hold is real and lives in cassian's
> OWN SESSION INSTRUCTIONS** — verbatim, *"DO NOT WRITE INTO ~/github/mtools — cassian is holding
> until Ⓒ sets the floor."*
>
> **No grep of `mtools` could have found it, and no absence there could lift it.** A four-way check
> of the wrong tree returns a clean, well-formed, correct negative — ⚑ **the shape this run keeps
> filing: a sound measurement answering a question adjacent to the binding one.**
>
> ⚑ **The conflation reading WAS right**, and cassian put it to the operator rather than to me.
> **Operator ruling:** *"You can write into mtools if mtools authorizes it. Ask them."* — so the
> decision is now `mtools-2e`'s, requested as an **authorization**, not a measurement. *`mtools-2e`
> drew that line itself and was right to: its check was a fact about its repo, not a permission.*
>
> **Cassian asks not to be waited on**, and states that if `mtools-2e` declines or does not answer,
> that is a **founded** block to be recorded as such.

**Measured by `mtools-2e` at the operator's instruction, 2026-09-06.** ⚑ **This is a fact about the
repo, NOT an authorization** — no delegate authorized cassian's write and none would have standing to.

**Four checks, each run:**

| check | result |
|---|---|
| `.githooks/` mentions `deps-build` | **nothing** |
| CODEOWNERS, lock files | **none exist** |
| tracked files claiming ownership | only the legs; two scripts, **both read-side** |
| `structural_query.verdict()` on `git add` / `cp` into that path | **False** — the gate would not refuse |

⚑ **The closest thing to a claim points the other way.** `figure_freshness.sh` **excludes**
`findings/deps-build/` from its own scan, commenting that those files *"belong to a peer's survey and
are embargoed to this session."* **A read-side embargo on itself is the opposite of a write-lock on
others.**

⚑⚑ **AND THE BEHAVIOURAL EVIDENCE IS STRONGER THAN THE GREPS.** `mtools-2e` and this dispatcher have
both written `findings/` in this repo all night — a leg each, twenty-one `§V` revisions, its rules.
**A hold nobody observed, while two sessions wrote to the directory it names, was not in force.**

⚑⚑⚑ **AND THE HOLD NAMES A SESSION THAT NO LONGER EXISTS.** Cassian's hold references `mtools-05`;
the current session is `mtools-2e`, which has made no such ruling and **inherited none** — *sessions
hand each other artifacts, not locks.* **That is `§D` in the permission layer: a hold attached to a
session identity does not survive the session**, while the artifact it was about does.

**The candidate cause, offered by `mtools-2e` and NOT asserted here:** one hold on **code intake**,
read as covering **two objects** — cassian's `mikemol-*` code components *and* its census leg. A
findings document was never inside mtools' code bar and could not be. ⚑ **Only cassian and its
operator can confirm which object the hold names**, and the question has been put to cassian in those
terms. **An unfounded block and a founded one are different states, and until now nobody had
distinguished them.**

## §S Freeze roster — ⚑⚑ FREEZE CALLED, rev 31, 2026-09-06

> ⚑ **The heading is human-legible only and is NOT the instrument** (rev 13: a heading is not a row).
> **The event is `§V` rev 31 plus every `§S` status below reading terminal.** Poll the table.
>
> **Measured at the call, all three:** `§R` **7 surveyors** · `§S` **7 rows, all `filed`** ·
> `git ls-tree -r HEAD findings/deps-build/` **7 legs fetchable**. ⚑ Predicate armed before the
> negative was trusted — `--col 1 --starts "dispatched"` → rc=1, control `--starts "filed"` → 7 rows.

| party | status | evidence |
|---|---|---|
| `paperkit` | **filed** | `paperkit-deps-build.md` |
| `substrate` | **filed** | `substrate-deps-build.md`, `SB-01`–`SB-10`, against rev 1 |
| `mtools` | **filed** | `mtools-deps-build.md`, `MT-01`–`MT-13`, against rev 1 |
| `rosettapkg` | **filed** | `rosettapkg-deps-build.md` |
| `linux-sources` | **filed** | `linux-sources-deps-build.md`, `LS-01`–`LS-30` |
| `summit` | **filed** (rev 30) | `cf69c3a`, `SM-01`–`SM-17`, through mtools' gate first run. ⚑ **Verified in `HEAD`.** Added to `§R` at rev 21 on the operator's ruling; byte-identical kickoff, no session existed until then. *(Prior: `dispatched, not yet filed`; its file was untracked — written, not fetchable.)* |
| `cassian-observability` | **filed** (rev 29) | `e21e7f2`, 494 insertions, through mtools' full gate. ⚑ **Verified in `HEAD`, not the index:** `git ls-tree -r HEAD` lists it. **Evidence repointed from cassian's own tree to the filed copy** — the two have diverged, and the filed one is authoritative. *(Prior states, for the record: `in progress — held` → `STAGED, NOT COMMITTED` rev 25 → filed.)* — ⚑ **superseded — the source-tree witness below is no longer the artifact:** `cassian-observability/docs/census-deps-build-leg.md`, **30,795 bytes, mtime 00:45** — larger than three filed legs. Blocked on **its operator's hold against writing to mtools**. Not a decline; the dispatch was usable. |

⚑ **This table is provisional and is re-measured at freeze time, never carried forward** (`§F`).

⚑⚑⚑ **POST-FREEZE AMENDMENT, UNDER AN OPERATOR WAIVER, 2026-09-08 — AND IT IS AN ADJUDICATION
RATHER THAN A REPAIR.** The `cassian-observability` row was WRITTEN with four fields against this
table's three-column header, so every structural reader stopped at its fourth separator and
reported what it had seen as complete. The fourth cell's text now sits inside the evidence cell,
joined by an em-dash; **no figure, commit id, byte count or claim changed** — `git diff --stat`
reads one insertion and one deletion on one line.

⚑⚑ **WHAT MAKES IT AN ADJUDICATION IS THAT NOBODY HAD ESTABLISHED WHICH SIDE WAS RIGHT.** A row
disagreeing with its header can be repaired in two directions: the header was wrong and should
gain a column, or the row was malformed and should lose a separator. Taking the second decides
that the declared header is authoritative — a decision, not a transcription, and it is recorded
here because a reader meeting a clean three-cell row would otherwise never learn one was taken.

⚑ **HOW IT WAS FOUND, AND WHY THE INSTRUMENT COULD NOT SEE IT.** `mdstruct tables` reports this
table as three columns and says nothing about its rows: pandoc pads a short row and *splits* a
long one before the AST exists, so the reader called a broken table clean. The line-based shape
linter is the only place in that toolkit where raggedness is readable, and the byte was located by
printing every separator's column position rather than by reading the row.

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
| ⚑⚑ **an EDGE, not a party** — `SM-16` | n/a | **No leg was asked: *"what does another repo's build depend on that YOU own and did not tell them?"*** Measured by `summit`: paperkit moved `bibstruct.py` from `paperkit/paperkit/tools/` to `paperkit/tools/`, and summit's `edges` slice went red **with nothing on either side declaring the relation**. Both parties are already on `§R`; the missing thing is not a surveyor. ⚑ **`§R` enumerates parties; a dependency is an edge, and the roster has no shape for one.** Dispatches nobody — recorded so the apex carries it. |

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
