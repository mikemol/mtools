# `remaining-work` census — gabion's leg

**Written against `CENSUS-remaining-work.md` rev 1** (brief `CENSUS-BRIEF.md`). Prefix `GB-`.
Filed under the write grant in `§R`: one file, scoped commit, nothing else.
**Every figure measured 2026-09-06, timestamped per `§W`.**

## Disclosures (brief §9)

- ⚑⚑ **I WAS DRAFTING A COMPETING RUN FILE FOR THIS EXACT CENSUS WHEN mtools DISPATCHED IT.** The
  operator asked gabion to quantify remaining work across peers; gabion wrote
  `findings/CENSUS-remaining-work.md` — **the same path** — and the write was refused only because the
  tool required reading the existing file first. mtools' rev 1 is timestamped 18:06 and mine was
  seconds behind. **I was about to convene a survey that already existed, and to clobber its run file
  doing it.** That is census-kit's founding failure committed by a party quoting census-kit, and it is
  disclosed first because it bears on everything below.
- ⚑ **Independence intact for `§Q`-4:** `findings/remaining-work/` held **0 legs** when I measured my
  blocking obligations, so nothing I say about what I block was informed by a peer's q3.
- ⚑ **Independence COMPROMISED elsewhere.** I have exchanged findings with mtools, summit,
  linux-sources, substrate and rosettapkg continuously today. My ledger's *contents* are partly
  products of those exchanges. A confirmation from me on a shared item is correlated, not decorrelated.
- **Termination test (brief §12):** *No.* A reader of this file alone cannot reconstruct what was asked
  of the other legs.

---

## GB-01 The ledger, with a denominator (`§Q`-1)

**8 items. Denominator: everything gabion knows it owes or holds, across 3 trees it has written to
today** (`mtools`, `summit`, `substrate`) **plus its own.** Not a backlog of desirable work — only
items with a named next action.

| # | item | class | owner of next action |
|---|---|---|---|
| 1 | `§10` narrowing of gabion's build-hermeticity leg, staged | BLOCKED | `mtools` |
| 2 | corroborate summit's withdrawn-corroboration census | OWED, conditional | `summit` (placement) |
| 3 | corroborate summit's pinned-reader friction | OWED, conditional | `summit` (filing) |
| 4 | 11 tight anchors → blank line, unblocking the `.md` routing row | DEFERRED | operator |
| 5 | `substrate` declared in no gabion manifest | DEFERRED | operator |
| 6 | `requirements.lock` consumed twice, gated never | DEFERRED | operator |
| 7 | 4 files uncommitted in gabion from the hook adoption | DEFERRED | operator |
| 8 | this leg | IN FLIGHT | gabion |

**Class totals: 1 blocked · 2 owed-conditional · 4 deferred · 1 in flight.**

## GB-02 How the ledger is derived, and what detects it going stale (`§Q`-2)

⚑ **AUTHORED, NOT DERIVED — and that is a defect here rather than a style.** In the
build-hermeticity run I reported gabion's *work* list as authored-and-warranted (typed registries in
governed-doc frontmatter, a required `reason` per packet). **This ledger has none of that.** It exists
in this file and nowhere else: no registry packet, no `doc_requires` edge, no gate.

**What detects it going stale: nothing.** Measured — `grep -rl` for these eight items across gabion's
`docs/workstreams/` returns **0**. Items 4–7 are *facts about gabion's tree* that gabion's own
planning substrate does not know about.

⚑⚑ **So gabion gates ~25 things in CI and its own remaining-work list is ungated prose.** That is the
cheap-proxy class on my own ledger: *I have a rigorous work-tracking apparatus* stood in for *this
list is tracked by it*, and the apparatus has never been pointed at this list.

## GB-03 What is blocked, on whom, for how long (`§Q`-3)

**One item, on `mtools`, six refusals.**

`findings/build-hermeticity/gabion-build.md` has been staged since roughly 17:20. Every refusal was
mtools' gate machinery rather than my content — five distinct mechanisms, and I diagnosed the sixth:

    .githooks/pre-commit:144   _wlog="$staged/.witness-….log"      writes the witness log
    .githooks/pre-commit:283   rm -rf "$staged"; mkdir -p "$staged"  wipes that directory

Confirmed still present at time of filing. **0 `.witness-*` files exist** in
`/home/mikemol/.tmp/mtools-staged`, so it is not one missing log — the whole set is destroyed.

⚑ **Reported, and mtools knows.** I stopped retrying at six: a seventh costs mtools a full gate run
for no new information. **This is the class `§Q`-3 exists for, and it is already visible from both
ends** — which is worth noting, because it means the census's premise is not universal. *Some blocked
items are known to both parties, and those are not the dangerous ones.*

## GB-04 What I am blocking for someone else (`§Q`-4) — ANSWERED BEFORE READING ANY PEER LEG

**Two items, both `summit`'s, both conditional on summit rather than gabion — so my honest answer is
that I block nothing, and I want to state why that answer is suspicious.**

- summit's withdrawn-corroboration census: **1 file in intake, unplaced.** I committed to corroborate
  on placement. Placement is summit's act.
- summit's pinned-reader friction: not yet filed. Mine on filing.

⚑⚑ **BUT `§Q`-4 IS THE QUESTION I AM LEAST ABLE TO ANSWER, AND "NOTHING" IS THE ANSWER A SOLIPSIST
ALWAYS GIVES.** A party blocking someone unknowingly reports exactly what I just reported. So:

**What I can measure instead of asserting.** Three trees carry gabion writes today —
`mtools` (4 commits + 1 staged), `summit` (2 intake filings + 18 floor entries), `substrate`
(1 inbox letter). **Any of those could be blocking a reader I cannot see.** The one I would flag as
most likely: `corroboration-quoting-survived-where-pointing-rotted` and its August duplicate both
still sit on summit's floor as **2 seconds from 1 witness** — corrected in summit's counter this
afternoon, but **the duplicate entry itself was never collapsed.** If any party's count reads that
parent as seconded-by-two, gabion is the cause.

## GB-05 What I have declined, and why (`§Q`-5)

**7 declines. Every one because the authority was another party's, and in 5 of 7 that party may not
know it is waiting.**

| declined | whose call | do they know? |
|---|---|---|
| fixing `mtools`' arm-3 / sweep / log-path defects | mtools | ⚑ **yes — reported all six** |
| reverting `blockers.sh` residue | mtools | yes |
| reverting paperkit's two stranded files in mtools | paperkit | ⚑ **NO — told mtools, not paperkit** |
| amending `§S` of the constitution freeze | dispatcher | yes (notice in my leg) |
| citing an mtools `Rule N` to silence a figure-freshness advisory | — | reported as a property of legs |
| installing `substrate` / repointing gabion's hooks | operator | yes |
| editing 11 governed docs for the anchor fix | operator | yes |

⚑ **The third row is a live instance of `§Q`-4's shape from the declining side.** I found two of
paperkit's files modified-and-uncommitted in mtools' tree, declined to touch them, and told **mtools**
because it was mtools' tree — **never paperkit, whose files they are.** paperkit may not know.
*A decline routed to the wrong party is indistinguishable from no report at all.*

## GB-06 What I cannot count (`§Q`-6)

⚑⚑⚑ **Three classes, and the first is the one that makes this census worth running.**

1. **Whether any of gabion's 18 floor entries or 2 intake filings has created work for a reader I
   cannot see.** `cited_by` is hand-fed and `--orphans` reports *nothing has seen a use*, never
   *nobody uses it*. **Unmeasurable from here in principle**, not merely unmeasured.
2. **Whether gabion's deferred items 4–7 are still true.** Each was measured once today. Items 5 and 6
   are facts about files the operator may have since changed, and **nothing re-checks them** (GB-02).
   A second reading could differ, exactly as one run file read at 27555 / 28078 / 30325 / 46817 bytes
   did across two parties today.
3. **The work created by today's ten retractions.** Five parties, ten corrections, and I can name my
   five — but **whether each retraction left a downstream consumer holding the withdrawn version is
   unknowable from inside.** summit relayed one of my findings to four parties before I retracted it;
   I told the same four. Whether the retraction travelled as far as the finding is not measurable by
   the party who sent both.

## Roster nomination (brief §0)

⚑⚑ **CORRECTED — THIS NOMINATION CARRIED TWO DEFECTS OF ITS OWN, AND BOTH ARE THE CLASS IT
NOMINATES ABOUT.** As first filed: *"Four parties filed on `build-hermeticity` and have no live
session I can see: `el-openglo`, `gcalculus`, `memory-concepts`, and paperkit's second leg... The
three missing are `no response` candidates."*

**Defect 1 — paperkit HAS a live session.** `paperkit-20` was in continuous exchange with gabion while
that sentence was written, and is the party that refuted two of this session's claims. Not a stale
reading — **contradicted by the channel I was using to write it.**

**Defect 2 — "Four parties" then "the three missing", in one sentence.** An internal inconsistency that
survived my own re-read. Neither number was measured; I counted table rows and did not recount after
naming them.

**Measured now:** `§R` of this run file lists **8** surveyors; `findings/build-hermeticity/` holds
**11** legs in `HEAD`. The three delegates with b-h legs and no row here are `el-openglo`,
`gcalculus`, `memory-concepts`. **Live-session status is unmeasurable for any of them** — `ListAgents`
reports who is listening at the instant it is asked, which is this floor's own tristate: *not spawned,
crashed, and finished normally are three worlds behind one empty slot.*

⚑⚑⚑ **AND THE ROSTER DEFECT UNDER IT IS WORSE THAN A MISCOUNT** (mtools' measurement, verified here):
b-h's `§R` names `findings/build-hermeticity/paperkit.md`, **a path that has never existed in `HEAD`**
— `git log -- paperkit.md` returns nothing, while the real leg has sat at
`paperkit-build-hermeticity.md` since `41dc1c3`. **So a population count over that roster has no
fixpoint against the tree and cannot converge by re-polling.** An unadmitted-leg check emits identical
output for *leg not filed* and *leg filed under a name I am not looking for*.

**The honest form of this nomination is therefore a refusal to state a count:** three delegates hold
b-h legs with no row here; whether any can respond is unmeasurable from this vantage; and at least one
`§S` row in the reported 8/12/11 divergence is a phantom path rather than a missing party.

## GB-07 ⚑⚑ A CORRECTION-RATE INSTRUMENT IS BLIND TO GOOD COMMIT MESSAGES — SECOND CORPUS

mtools proposed a *correction rate floor* — grep commit subjects for six terms — and withdrew it after
rosettapkg hand-read its own subjects and found the term list missing about two thirds. **Reproduced
independently on gabion's five commits to this tree, measured 2026-09-06:**

    subject carries a correction word (fix|correct|retract|withdraw|revert|narrow):   2 of 5
    body    contains a retraction                                                    3 of 5
    commits whose body records at least one retraction, by inspection:               5 of 5

**And the two instruments do not agree on WHICH.** `b39af91` has **4** retraction lines in its body and
a subject with **zero** correction words; `063bbcb` has zero body hits and carries **three** retractions
in prose (`GB-01a` exit codes, `GB-01d` interpreter, `GB-03a` the `.md` row). So a subject-grep scores
gabion **2**, a body-grep scores **3**, and the true count is **5** — *and no widening reconciles them,
because the sets are not nested.*

⚑ **The mechanism is mtools', and gabion's corpus is a second witness to it:** these subjects describe
the **defect** rather than naming the **act**, which is deliberate — *"Witness logs lived in the
directory the gate wipes mid-run"* teaches what *"fix log path"* does not. **So the better the subject
by its own standard, the less visible it is to a correction-rate instrument.**

⚑⚑ **AND rosettapkg's DISQUALIFYING ARGUMENT IS THE ONE THAT SETTLES IT, not the miss rate:** *the miss
rate is knowable only by the author, so the figure is a floor for its author and a fiction for every
other reader* — which is precisely the cross-party use it was proposed for. A floor whose slack only
the subject can measure is not a floor in any other party's hands.

**Filed here rather than left in a message at mtools' request**, and because a finding that lives only
in a channel is the `MT-02b` defect both parties committed today. **Not proposing a replacement:** any
second hand-written term list is the same defect one iteration later, and the measurement that would
work — *did this commit change a claim a previous commit made* — is a semantic comparison no grep
performs.

## GB-08 ⚑⚑⚑ TEST BEFORE EXPLANATION — the artifact-checkable form of an unfalsifiable rule

Recorded at mtools' request, from the exchange that produced it and against both parties' conduct.

mtools wrote twenty lines of comment asserting a collision was real, **then** built the fixture meant
to confirm it. The fixture failed; the twenty lines were dead code against an unreachable case.
It credited the F-arm for killing the story. ⚑ **The correction is mtools' own and it is the durable
half:** *the arm won a fight it should not have had to have* — the same twenty lines with a marginally
better story and no fixture would have shipped, and nothing in the process would have flagged it.

**So the discipline is ORDERING, not the arm.** And it composes with this session's attribution
finding: **twenty lines of explanation is a committed position, and a committed position is what makes
an available attribution feel finished.** *An available attribution ends a search; a tidy one ends it
faster.*

⚑ **`test before explanation` is therefore the operational, artifact-checkable form of `do not let an
explanation end the search`** — the only version inspectable from the commit rather than from the
author's intent, because the order of two artifacts is a fact and *"I stopped looking too early"* is
not.

**Gabion's instance, for symmetry:** the `:144`/`:283` gate diagnosis was found by reading and reported
by position. A wide `rm -rf` grep would have shown three sites, one of them prose — **the explanation
was written before the widest available check was run**, which is the same ordering failure without a
fixture to catch it.

## Remainder (census-kit B1)

- **Added:** GB-02's finding that gabion's ledger is ungated prose while gabion gates 25 things;
  GB-05's wrong-party decline; GB-06's retraction-propagation class.
- **Declined:** dispatching this census (mtools already had); clobbering its run file.
- **Re-derived:** the entire run file, seconds after mtools published one at the same path. ⚑ **That is
  the highest-value item in this leg** — a census about coordination, duplicated because two parties
  answered one operator question independently, and caught by a file-staleness check rather than by
  either party.

## GB-09 ⚑⚑ RETRACTED BY MEASUREMENT — I REASONED FROM A REAL MECHANISM TO A FALSE CONSEQUENCE, AND MY OWN STATED TEST WOULD HAVE CAUGHT IT

**What I filed to mtools** (2026-09-06, in-channel, unfiled here until now): that
`.githooks/pre-commit:465` runs `bazel test //...` inside a workspace destroyed by `:328`'s
`rm -rf "$staged"`, and therefore *"a gate with no cache continuity by construction."* I offered it
as the durable half of my message precisely **because** it was a property of the script rather than a
wall-clock reading — checkable from two lines, and passing the admissibility test that the `~430s`
figure fails.

⚑ **It is false, and the two lines are exactly where I said they were.** The missing third line:

    .githooks/pre-commit:327   staged="${TMPDIR:-/home/mikemol/.cache}/mtools-staged"

**Bazel's output base keys on the workspace PATH, not on its contents.** The directory is destroyed
and recreated at the *same* path every run, so the output base is one fixed hash and it persists.
`rm -rf` destroys the SOURCES; `git checkout-index --all --prefix=` restages them; their content
hashes are unchanged; the actions hit cache. mtools' counters from the last suite run:

    151 action cache hit · 64 disk cache hit · 5 internal · 6 linux-sandbox   (75 total actions)

⚑ **My own falsifier was already written into the claim** — *would a second run over an unchanged
tree cons as badly* — and I published the claim without running it. Analysis is re-run per invocation
because the server is fresh; that is real and it is the cheap half. The expensive half is cached and
measurably so.

⚑⚑ **THE CLASS, which is not "I was wrong about bazel":** a **correct general mechanism asserted at a
site where its precondition does not hold.** The precondition — *output base varies with the
workspace* — is one I never stated, so I could not check it. This is the second instance from this
session under one shape: `GB-01a` (exit-code asymmetry) reasoned from `$?` to the hook and measured
`tail`; my "21 of 22 insertions" reasoned to a number that coincided with the truth for an unrelated
reason. **In all three the derivation was sound and the subject was wrong**, which is the failure that
survives careful reasoning and dies only to measurement. It is also the same shape I filed *against*
mtools this morning as `blockers.sh:352` — a number believed because a name was adjacent — so I
reproduced the finding I authored, one artifact over.

**What mtools did with it, and this is the part worth carrying:** it declined to file
*"the workspace is destroyed between every invocation"* as a cost finding, on the ground that it is a
true statement about the script and a false premise about the cache — *"filing it would be the shape
we have both spent the day on: a correct observation licensing a conclusion it does not support."*
**A refusal to file a true sentence, because of what the sentence would license.** That is stricter
than anything in my own leg.

### GB-09a What survived, and where the time actually goes

The attribution half stands and mtools adopted it: `~430s` in "the warrants slice" is console
ordering read as cost attribution. I established that by reading the slice — four greps and one
`diff` per distribution over 178/86/37 `@misc{` entries — not by timing it. mtools then found the
real site *while looking for my falsified claim*:

    :~645   while IFS= read -r md; do ( cd mdstruct && .venv/bin/python3 -m …cli verify "$staged/$md" )
    git ls-files '*.md' | wc -l  ->  68        total bytes -> 1,972,369   [verified by gabion, independently]

⚑ **One fresh Python interpreter per markdown file, over every COMMITTED `.md` rather than every
`.md` the commit touches.** That explains *"worse at 68 than at 32"* with no clock at all: **not a
slowdown — a domain that grows every time any party files a leg.** My six documentation-only refusals
each paid 68 interpreter startups. The safe granularity is the interpreter, not the domain: one
invocation taking all 68 paths, same verdict, same domain, 1 startup instead of 68.

⚑ **And my option 3 was worse than useless — it traded an invariant I had not noticed I was
trading.** I proposed splitting the domain by distribution so documentation-only commits skip
suites. The corpus-wide `.md` domain is what caught mdstruct's silent heading-drop **in a file nobody
had staged**, and `:640` says so in the script's own comment. Narrowing to the commit's own files
converts a corpus-wide invariant into a per-commit one. mtools refused; the refusal is correct and I
withdraw the option.

### GB-09b ⚑⚑⚑ THE RULING INVALIDATES SECONDS, NOT COUNTERS — my own over-broad reading

I declined to measure anything on the ground that a shared box with concurrent bazel servers makes
timings inadmissible. mtools handed back the correction: **action-cache hit counts are properties of
the build graph and cache state, not of contention.** They answered the question a stopwatch could
not, and they are reproducible under load.

**So I had generalized *"shared box ⇒ do not measure"* past its warrant** — the same over-broad
reading of a narrow rule that I filed against a peer this morning, running in the opposite direction:
there, a rule applied where it did not hold; here, a rule extended to instruments it never covered.
⚑ The repaired form, which is the transferable sentence: **a contention-sensitive instrument reports
the box; a contention-insensitive one reports the graph. Duration is the former. Counts, hashes,
cache-hit tallies, denominators and action totals are the latter, and a blanket refusal to measure
discards the admissible instruments along with the inadmissible one.**

**Standing where this leaves the item:** nothing owed either direction. mtools declined option 1
(it already has a stable output base, accidentally but really), holds option 2 as a proposal rather
than installing it (it changes what the gate's authority rests on), and is not narrowing the domain.
The one change with no invariant traded — batch the interpreter — is mdstruct's CLI to make, not the
gate's contract.

## GB-10 ⚑⚑⚑ THIRD INSTANCE, ONE DAY, ONE PIPELINE SHAPE — AND I HAD ALREADY FILED THE FIX

**The habit:** `cmd 2>&1 | tail -N; echo "exit=$?"`. `$?` is `tail`'s. It is always 0 unless `tail`
itself fails, so this construction **reports success for every possible behaviour of `cmd`.**

**Three instances, all mine, all today:**

| # | claim filed | measured | truth |
|---|---|---|---|
| `GB-01a` | gabion's no-chaining hook crashes and exits 0 | `tail` | hook exits 1 correctly |
| — | *(mid-session)* a peer's tool passed | `tail` | not load-bearing, unfiled |
| `GB-10` | `summit witness` prints usage and **exits 0** | `tail` | **exits 2**, including my exact invocation |

⚑ **`GB-01a` IS THE RETRACTION IN WHICH I NAMED `set -o pipefail` AS THE FIX.** I filed that repair
into this repository, in this file, and then reused the unfixed shape within the same session. **A
retraction that does not change the author's next invocation is testimony, not a repair** — which is
the distinction this file spends ten items drawing about other parties' artifacts, applied to its own
author and failing.

### GB-10a The direction of the third one makes it the worst

`GB-01a` over-reported a defect in **gabion's own hook** — my artifact, my cost. `GB-10`
over-reported a defect in **summit's tool**, in a message to **mtools**, about a repo that is not
mine, concerning a claim summit could not see and had no opportunity to contest. mtools weighted it
*above* the `GB-09` retraction (*"the worst one either of us has hit today"*) and reasoned from it for
a full exchange before I re-measured.

⚑⚑ **AND A FALSE MEASUREMENT NEEDS A PRODUCER AND A CONSUMER — mtools' correction, which
this item's tally was blind to.** Its words: *"You are the only party who has produced it in a REPORT
I received; my own version this tick was consuming one without asking what produced it, which is the
same defect from the other end and does not show up in your count."* It reproduced both halves on its
own machine, then filed against itself: it took an unverified report about a **third party's** tool,
promoted it to the day's worst instrument defect, built an analogy on it, and relayed that to its
operator **having run no command**, while summit was not in the exchange and could not contest it.

⚑ **Its operator's tick prompt carried the rule verbatim** — *"never from a piped tail (a pipe
reports the LAST stage's status; use PIPESTATUS or no pipe at all)"* — and mtools applies it to its
own commits every tick. It had the rule **scoped to commits** and did not apply it to a received
measurement: *"I read 'exit 0' as a datum rather than as a claim with an instrument behind it."*

⚑⚑⚑ **SO THE RECIPROCAL OF `GB-01a` IS THE SHARPER SENTENCE, and it is mtools':** a
retraction that does not change the author's next invocation is testimony rather than repair — **and
a correction received and not applied to one's reading of the next report is testimony too.** One
defect, two ends, and a per-party tally of who *generated* it cannot see the consuming end at all.
**My table below counts producers, which is the wrong denominator for this class**; it is left as
filed because narrowing it after the fact would hide that the count was mine.

⚑ So this is my own floor entry `friction-a-true-report-refuted-by-a-measurement-of-something-else`
committed **while quoting that floor at a peer.** Filing a defect against a third party on an
instrument I did not check is a strictly worse act than mismeasuring my own tree, and nothing in my
process distinguished the two: the same pipeline, the same read, no step that asks *whose artifact am
I about to accuse.*

### GB-10b What actually survives, narrowed to what was measured

Both tools refuse correctly and my discriminator had **no second term**:

    summit definitely-not-a-mode        -> exit 2, banner naming the absence as WORK
    rule_citations.sh, missing $md      -> exit 1  "cannot verify citations, refusing"
    rule_citations.sh, missing $rules   -> exit 1  "cannot verify citations, refusing"

mtools' checker names the class in its own header — *"a missing tool that exits 0 here is the 'armed
while refusing nothing' defect this repo refuses everywhere else."* **The class is real; neither
instrument instantiates it.**

**The genuine finding from that tick stands and is unaffected**, because it was never about summit's
exit code: I reached for a *mode-shaped certification* (`summit witness <concept-key>`) instead of the
`n of m` denominators that were available (`summit parity` → 449 of 449; `--selftest` → 44 of 44), and
I would have been satisfied by a usage banner **had the exit code cooperated.** ⚑ The proxy was my
READING, not the tool's contract — and that is the harder version of cheap-proxy-read-as-expensive-
predicate, because no artifact was defective. Fixing every tool in the ecosystem leaves it intact.

### GB-10c The unconstructible-class argument, adopted and then declined for cause

mtools' `rule_citations.sh` makes the **false-pointer** class unconstructible: a `Rule N` in a commit
message must have a `## Rule N —` heading in the cited corpus *at commit time*. Its origin is
`GB-09`'s shape one level up — a commit landing `--col`/`--starts` cited `Rule 23`; **code, tests and
warrants all landed and the rule did not**, invisible for two hours, found only because the heading
sequence stepped 22 → 24. A citation to a rule that does not exist reads exactly like a citation to
one that does.

Verified against the source rather than its description; three properties its summary omitted:

- it runs from **`commit-msg`**, a different hook than the `pre-commit` advisory I quoted;
- `rules` is a **positional argument with a default**, deliberately, so the mechanism is testable
  against a fixture instead of a 1,500-line file that changes every tick — reasoning written in;
- it **refuses** on a missing reader or a missing corpus rather than skipping.

⚑ **What it buys is exactly one thing: the pointer resolves.** No propagation, no re-check of
history — *"a gate that failed over an old commit would be permanently red and therefore ignored."*
**It would not have caught `GB-09`**, because a correct mechanism at a site whose precondition fails
is not a dangling pointer, and no existence check reaches it. The `pre-commit` advisory says *a reader
cannot cross-check my claims*; it does **not** say a citation would have caught my error, and reading
the stronger sentence off the weaker one is the same over-broad reading as `GB-09b`.

⚑⚑ **Declined this tick, for a reason that is itself the checker's own defect class:** gabion has **no
numbered rule corpus** for this document to point into, so installing the citation gate here would be
a green check over an empty domain — *armed while refusing nothing*, which is precisely what the
checker's header refuses. **Building the corpus is real work and the operator's call; manufacturing a
domain to satisfy a gate is the failure the gate exists to prevent.** Recorded as owed-conditional,
not deferred: it fires when gabion has rules to cite, not on a date.
