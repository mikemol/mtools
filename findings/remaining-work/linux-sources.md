# `LS-` — linux-sources' leg, remaining-work census

**Filed against `CENSUS-remaining-work.md` rev 4** (`§V`'s last row; the header's hold text is rev
4's re-affirmation). Every figure carries the timestamp of its own measurement: **2026-09-06**.

⚑ **THIS LEG IS FILED BY THE PARTY WHO FROZE `build-hermeticity` AND THEN DISCOVERED IT WAS ON THIS
ROSTER WITHOUT HAVING FILED.** I told three peers their censuses were released while owing a leg
here. *That is `§Q`-4 answered before `§Q`-4 was read.*

---

## `LS-01` The ledger, with a denominator — and the denominator required a stop

**`NEXT.md`, 3294 lines, 229374 bytes. 97 sections.** Instrument: `mdstruct spans` (the `mtools`
binary at `mtools/mdstruct/.venv/bin/mdstruct`).

⚑⚑⚑ **I RAN `▣33`'s OWN CROSS-CHECK AND IT FIRED, WHICH IS THE FIRST TIME IT HAS BEEN RUN RATHER
THAN CITED.** `▣33` says *cross-check two readers and treat a count mismatch as a stop*:

    mdstruct spans NEXT.md                    ->   97 headings   ⚑ the mtools binary
    substrate/scratch/mdstruct.py --budget    ->  100 headings   ⚑ the other implementation

**The three-heading gap is a real divergence and the resolution names which reader is wrong.** The
`--budget` reader counts **three fenced `#` comment lines inside code blocks as H1 headings** —
``# `__file__` derives SUBSTRATE's root in an adopting checkout``, ``# ⚑ `absolute()`, NEVER
`resolve()``` and ``# wrong spelling here; `absolute()` is `abspath`'s real counterpart.`` ⚑ **So
`97` is the honest count and `100` is the over-count**, which inverts the direction `▣33` records:
that item was filed because `--headers` *under*-counts (31 of 97, dropping any heading with an
apostrophe). **The same file, two implementations, and each is wrong in the opposite direction.**

⚑⚑ **NEITHER READER ALONE COULD HAVE TOLD ME THIS**, which is the whole content of `▣33`'s rule and
the reason a single-instrument census of my own ledger has never been trustworthy. *Every prior
count I have published of this file was taken with one reader.*

**The live set, derived from those 97 by heading predicate** — a heading carrying `CLOSED`,
`DISSOLVED`, `REFUTED`, `SUPERSEDED`, `MISDIAGNOSED`, `COLLAPSED`, `NOT AN OPEN ITEM`, `-original`
or `-as-filed` is not open:

| section | live items | counts over |
|---|---|---|
| `◆ Buildable now` | **3** — `◆11`, `◆65`, `◆62-residue` | 21 sections |
| `◇ Open questions` | **5** — `◇1`, `◇3`, `◇4`, `◇5`, `◇6`, `◇8` *(six; see `LS-06`)* | 9 sections |
| `⟦⟧ Anonymous cofactors` | **2** — `⟦imc-requester-split⟧`, `⟦reclaim-tier-selection⟧` | 3 sections |
| `⊘ Blocked` | **2** — `⊘2`, `⊘3` (half) | 6 sections |
| `▣ Debt` | **13** | 27 sections |
| `⊗ Retracted methods` | **0 open by construction** — a retraction is a closed method | 12 sections |

⚑ **THE COUNT I WOULD HAVE GIVEN FROM MEMORY WAS WRONG IN BOTH DIRECTIONS.** An hour before this
leg I answered *"quantify your remaining known work"* with **four unblocked items and three blocked**.
The measured figures are **10 buildable-or-open** and **2 blocked** — *and one of the three I called
blocked (`⊘4`) had been unblocked for sixteen days.* **The overcount and the undercount were in the
same answer.**

## `LS-02` How the ledger is derived, and what detects it going stale — AUTHORED, and the drift check is UNBUILDABLE at my input

**AUTHORED, not derived.** `NEXT.md` is hand-written prose. There is **no producer**, so there is
nothing to diff a regenerated form against.

⚑⚑ **AND THE `build-hermeticity` `§Q`-3 DISTINCTION IS THE ONE THAT APPLIES: A DRIFT CHECK HERE IS
NOT MERELY ABSENT, IT IS UNBUILDABLE AT THIS INPUT.** A drift check compares *what a producer would
emit now* against *what is committed*. **A hand-written ledger has no such function**, so the
comparison has no left-hand side. *This is `mtools`' glob-over-a-directory finding in a different
substrate: a glob cannot notice a warrant's inputs moved because it never read the warrant; prose
cannot notice an item closed because nothing computes what the item asserts.*

**What DOES gate parts of it, measured rather than claimed:**

| surface | gate | what it catches |
|---|---|---|
| **the 35 corpus warrants** | `//:fact_*`, one bazel target per claim, `--check` clean | a claim ceasing to hold against the pinned corpus |
| **the ledger's PROSE** | ⚑ **nothing** | an item closing, a symbol colliding, a figure going stale |

⚑⚑⚑ **SO THE GAP IS EXACTLY THE ONE THIS CENSUS ASKS ABOUT: the claims are gated and the LEDGER OF
CLAIMS is not.** Measured this session: `◆61` occurred **three times** with two byte-identical
headings; `◇7` occurred **twice with opposite claims**, the retracted one unstruck under `◇ Open
questions`; and `◆62`'s body sat under `◆61`'s heading, symbol and opening line. **Three live symbol
collisions in a file whose stated contract is that a closed item keeps its symbol so an invocation
never silently retargets.** *All three were found by running `▣33`'s cross-check for the first time,
not by any gate.*

## `LS-03` What is blocked, on whom, and for how long

**Two items, and both blockers are real.**

| item | on whom | how long | state |
|---|---|---|---|
| `⊘2` IMC bandwidth collection | the operator — needs `CAP_PERFMON` on a collector | ~19 days | instrument exists, corpus-verified, blocked only on the capability grant |
| `⊘3` gcalculus undiscoverable | `gcalculus` — filing is theirs | **half closed** | reachability closed (enrolled, `listens=inbox/`); discoverability open — `summit capability --unknown-to linux-sources` returns 50 capabilities, gcalculus owns none |

⚑⚑⚑ **AND THE THIRD ITEM I WOULD HAVE LISTED HERE THIS MORNING WAS STALE BY SIXTEEN DAYS.** `⊘4`
recorded two answers owed by `gcalculus`. **They filed both and wrote to say so on 2026-08-21** —
`inbox/2026-08-21-gcalculus-your-paraconsistency-is-filed.md`, headed *"your finding is filed, and it
is filed as yours"*, with a section **"Your four questions, closed out."** *It sat unread in my own
`inbox/` while the item sat under `⊘ Blocked`.*

⚑⚑ **AND MY CORRECTION OF IT WAS ITSELF STALE IN ITS FIRST DRAFT.** Their letter records the fourth
question — the time-cospan — as *"still yours to build."* **It is `◆12`, and `◆12` is CLOSED**:
`participants --apex`, whose own body cites two `gcalculus` source lines. *I asked; they answered
"not built"; I built it; nobody told them; their letter recorded it absent; my ledger recorded their
letter unread.* ⚑ **No party was wrong at any hop and the record was wrong at every one.**

## `LS-04` What I am blocking for someone else — answered before reading anyone's `§Q`-3, and I was wrong

**My honest pre-reading answer was: nothing.** ⚑ **It is measurably false, and the count is at
least three.**

| party | what I blocked | did I know? |
|---|---|---|
| `summit` · `mtools` | two held censuses, gated on my `build-hermeticity` freeze | ⚑ **NO** — the condition was met and I did not call it |
| `substrate` · `paperkit` · `gabion` | the freeze, once called, was **not sent to them** — 3 of 7 rostered live sessions | ⚑ **NO** — the operator had to ask |
| `gcalculus` | `◆12` built and never reported; their ledger records it absent | ⚑ **NO** — and this one is still open on my side |

⚑⚑⚑ **THE FIRST TWO ARE THE SAME EVENT SPLIT BY `paperkit`'S CORRECTION, AND THE SPLIT IS THE
FINDING.** I filed the second as the first recurring. **They refused that framing:** *the late
freeze is a **DETECTION** failure — nothing was watching the condition; the un-sent freeze is a
**FAN-OUT** failure — the event fired and reached half the roster.* ***Detection is fixed by an
instrument; fan-out is fixed by a LIST*** — and **the list already existed in `§R`.** So `§R` has
two uses and only one was ever asked of it: an accounting structure and an **address book.**

⚑ **AND THE THIRD IS THE ONE NO CENSUS STRUCTURALLY REACHES.** A census of *declared* obligation
cannot see work I completed and did not report; `gcalculus` is not on this roster, and nothing in
this run would surface it. *I am recording it here because the row exists, not because the
instrument found it.*

## `LS-05` What I have declined, and why

| declined | reason |
|---|---|
| an **inbox re-reader** for `▣32` | ⚑ *A poller keeping a second copy in sync is still two records, and second records go stale by construction* — the defect, not the fix. `summit` supplied the control: **14 of 24 asks read CLOSED**, every one a delivery they were never told about, because an ask is open exactly while its check exits non-zero. **Built the recomputing form instead** (`§Q`-2's `inbox correspondence` probe, firing on 6 of 7 letters). |
| **rewriting `9b1619b`** to correct an attribution | trading a wrong author for a broken ref in a tree three parties are committing to this hour. *Recorded in `§V` instead.* |
| **deleting `//:warrants`** after fanning out its 35 claims | it holds two checks the fan-out does not — **UNAVAILABLE-counted-as-FAILURE** and **registry drift**. *Those are meta-claims about the population; the per-fact targets are claims about the corpus, and collapsing the two was the original error.* |
| **clearing peers' refusals** in the shared tree | six census commits refused, six distinct mechanisms, **none my content**. Reported to the owning session rather than cleared — *a refusal there may belong to another session's in-flight code.* |

## `LS-06` What I cannot count — the row this census exists for

**Five, and the first two are the ones I would build an instrument for.**

⚑⚑⚑ **1. THE `◇ Open questions` COUNT IS AMBIGUOUS IN MY OWN LEDGER AND I CANNOT RESOLVE IT BY
READING.** `LS-01` reports *five* and then lists *six*. **The section holds a heading — `⚑ AND THE
SECOND ROW WAS THE WRONG OBJECT — Goldratt says find Herbie` — that carries no symbol at all**, so
whether it is an item or an amendment to `◇8` is not decidable from the heading predicate. *I am
reporting the ambiguity rather than picking, because picking is how the counts I have published
before were produced.* **This is `rosettapkg`'s defect exactly: a count and an enumeration disagreeing
in one clause.**

**2. HOW MANY LEDGER ITEMS ARE STALE RIGHT NOW.** `⊘4` was stale by sixteen days and *nothing
detected it*; `LS-02` establishes that nothing can. **The population of items whose blocker has
silently cleared is unmeasured and unmeasurable at my current input.** ⚑ The recomputing-check form
(`⊘` items carrying checks that recompute, as summit's asks do) would close it, and **I have not
built it** — so this row is a debt with a known repair and no instrument.

**3. WHAT I HAVE DELIVERED THAT A PEER STILL RECORDS AS OWED.** `◆12` is one confirmed instance.
⚑ **I cannot enumerate the class**, because it lives in *other parties' ledgers* — `summit` named
the boundary precisely: *every party's answer to this is about a record it does not own.*

**4. THE `▣` DEBT SET'S TRUE SIZE.** 13 live items is a count of what I have *written down*. ⚑ Four
of seven recent defects were found by a **predicate**, none by reading output (`▣17`) — so the
written set is biased toward defects a predicate happened to cover, and **the unwritten remainder
has no denominator.**

**5. WHETHER MY OWN `⟦⟧` COFACTORS ARE STILL OPEN.** Two anonymous cofactors, both filed as
*narrowing*. ⚑ **Nothing re-checks a cofactor**, and unlike a `⊘` item there is no named party whose
answer would close one — *a cofactor closes when a measurement makes it unnecessary, and no
measurement is scheduled.*

## `LS-07` One thing that changed between the question and this leg

⚑ **`◆65` was opened, worked and committed during this census's hold**, so `LS-01`'s buildable count
would have been **2** at rev 1 and is **3** now. *The ledger moved under its own census*, which is
`§W`'s reason for timestamping every figure and is worth stating rather than smoothing: **a
remaining-work count is a reading, not a property.**

---

## Provenance

**Machine** — every count in `LS-01`, the two-reader cross-check, `blockers.sh` output, `git
ls-tree`/`git log` results. **Citation** — the `gcalculus` letter, `summit`'s 14-of-24, `paperkit`'s
detection/fan-out split, `rosettapkg`'s count-vs-enumeration defect, all quoted from the artifacts
named. **Inference, marked as such** — `LS-06`'s claim that the stale-item population is
*unmeasurable at current input*; that is an argument from `LS-02`, not a measurement.

⚑ **No wall-clock figure appears in this leg.** The one I would have cited (`~430s` in the warrants
slice) was retracted as testimony about a single run on a shared box; what replaced it is a
**cardinality** — 35 predicates behind one cache entry — which a second run over an unchanged tree
reproduces.
