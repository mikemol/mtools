# Paths forward — derived 2026-09-05, after the move fix landed

⚑ **Re-derived, not replayed.** The list reorders as blockers clear. This derivation moved two
items and *retired the reason* for a third, on measurement rather than on report.

## Standing blockers, re-measured this cycle

`./blockers.sh`, plus `ListAgents` for the one thing that script deliberately cannot cover.

| blocker | last cycle | now | moves |
|---|---|---|---|
| substrate ratchet island | 9 of 32 tracked | **10 of 32** | ⚑ see below — the count is not the finding |
| `scripts/membudget-ledger` | untracked | untracked | Ⓔ still blocked |
| cassian's components | none landed | none landed | Ⓓ still blocked |
| `import paperkit` | fails | fails | Ⓕ's consumer still absent |
| `inbox/` | empty | empty | ⚑ and peers ARE writing — see below |
| peer reachability | all live | **all four live** | nothing blocked on contact |

### ⚑⚑ The island count moved by one and that is the least interesting thing about it

A tracked-file count answers "how much" and the question is "what can I take." Measured the
**import closure** instead, which is the property intake actually depends on:

```
ratchet_move.py  ratchet_churn.py  ratchet_key.py  + their selftests
    -> every substrate import they make is ALSO TRACKED.  CLOSED.

ratchet_family.py  -> ratchet_census, ratchet_witness, witness_family, witness_row   UNTRACKED
baseline_health.py -> baseline_state, corpus                                          UNTRACKED
```

**So the island is tracked LEAVES-FIRST, and a closed subgraph is already available.** The
previous derivation recorded this blocker as "substrate cannot ship the island" — a statement
about substrate's whole tree, which was true and is now too coarse to act on. ⚑ **A blocker
stated at the wrong granularity reads as blocking more than it blocks.**

⚑ **Counting tracked files could never have surfaced this.** 9→10 looks like slow progress;
the closure says the three modules I need are landable today and the two I do not need are not.

⚑⚑⚑ **FALSIFIED NINE TICKS LATER, AND LEFT HERE BECAUSE THE FALSIFICATION IS THE LESSON.** "Landable
today" was read from `git ls-files`, which reports a **staged** file as tracked — correctly, since
the index *is* the tracking record. But *tracked in a peer's index* and *fetchable by me* are
different properties, and only the second decides whether code can move. Measured under the
corrected predicate: **not one island module has a commit on any branch.** Every `TRACKED` this
derivation printed for ten ticks was staged-only. See Rule 27.

⚑⚑ **AND THE CORRECTION REACHED THE RULES FILE WITHOUT REACHING THIS ONE.** For nine ticks the
findings document recorded the retraction while the file a session reads *first* — to decide what to
do — still said the work was available. **A corrected claim and its uncorrected restatement can
coexist in one repository indefinitely**, because nothing links them: the rule knows what it
supersedes, and the derivation does not know it was superseded.
Same population, same command, different question.

### ⚑ `inbox/` is empty AND peers are writing — both true, and the pair is the finding

Two peers filed substantive findings into this session **this cycle** (cassian's cquery
amendment, substrate's four-reading header retraction), and `inbox/` is empty. **The inbox is
not the channel; the message bus is.** The inbox measures a thing nobody uses.

⚑ That makes `inbox/` a gate reporting green over nothing, in a repo whose subject is exactly
that. It is not currently costing anything — but it is a *claim* that peer writing would be
visible there, and it would not be. Recorded; see Ⓩ.

## The sequence

| | step | unblocked? | why here |
|---|---|---|---|
| ~~Ⓜ~~ | ~~Intake the closed move subgraph~~ | **DONE** | Rule 11. Every classification agrees; the peer's fan-out defence defaults OFF. Divergence pinned as a test. |
| ~~Ⓑ¹~~ | ~~`:31464` counters under my own traffic~~ | **DONE** | Rule 12. It counts redundant EXECUTION, not redundant transfer. Control arm + F-arm. |
| **Ⓨ** | Standing witness on the mypy transitive domain | YES | the Π-typing claim has no permanent arm |
| **Ⓩ** | Retire or wire `inbox/` | YES | cheap; removes a green-over-nothing |
| **Ⓝ₄** | 62-key preview debt paydown | YES | pure paydown, no leverage to anything |
| **Ⓔ** | membudget ledger / the keyway | **NO** | `scripts/membudget-ledger` untracked — substrate must commit |
| **Ⓓ** | cassian's three components | **NO** | with cassian's operator; also triggers the platform fix |
| **Ⓕ** | warrant paydown for projection | **NO** | `import paperkit` still fails |

### Why Ⓜ is top, and it is not "because it is newly unblocked"

⚑⚑ **It is top because I have a live divergence with a peer on a component we both implement,
and every cycle that passes makes the two copies more expensive to reconcile.** I derived
one-to-one-plus-path-plausibility from that peer's docstring warning without reading its code;
its `ratchet_move.py` is 63 lines and now tracked. Either it agrees with my construction — in
which case two independent derivations converging is the strongest evidence the rule is right —
or it does not, and one of us is wrong *now*, cheaply, rather than after both trees depend on it.

⚑ **This is the hash-consing case the README names, arriving live.** Two repos, one component,
independent implementations. The interning argument says a fix that lands in one does not travel;
that is only actionable while the divergence is small.

Structural leverage to what follows: it settles whether mtools' ratchet or substrate's is the
canonical one, which is a precondition for Ⓓ (cassian's components arrive under a ratchet) and
for Ⓔ (the claim ratchet is the same machinery).

### What would unblock the blocked three

- **Ⓔ** — substrate commits `scripts/membudget-ledger`. It is nine gates away in that tree.
- **Ⓓ** — cassian's operator releases the three components; cassian has the platform fix committed
  and the first sandbox-tier target makes it live, so Ⓓ and that fix are one event.
- **Ⓕ** — paperkit publishes something importable. Not a decision anyone here can take.


---

# Re-derivation, same session, after Ⓜ and Ⓑ¹

⚑ **Two items consumed; the list is re-derived rather than resumed.** Neither completed step
unblocked anything downstream — which is itself the finding, and it changes what belongs on top.

## What the two completions actually changed

- **Ⓜ** settled the canonical-ratchet question by *convergence*: two independent implementations
  partition identically. That was a precondition I had assigned to Ⓓ and Ⓔ. **It is now met, and
  both remain blocked for unrelated reasons** — so clearing it moved nothing forward. ⚑ A
  precondition that was not the binding constraint.
- **Ⓑ¹** discharged a debt to a peer and produced Rule 12, but nothing here consumes the metric.

⚑⚑ **So the top of the list is now determined by what is OWED to this tree rather than by what
unblocks a peer.** Both completed items were outward-facing. The next one should not be.

## The sequence, re-derived

| | step | unblocked? | why here |
|---|---|---|---|
| **Ⓢ** | `suspect` — the third ratchet state | YES | measured gap, named in Rule 11, in the component both trees now depend on |
| **Ⓨ** | Standing witness on the mypy transitive domain | YES | the Π-typing claim is load-bearing and has no permanent arm |
| **Ⓩ** | Retire or wire `inbox/` | YES | cheap; removes a green-over-nothing |
| **Ⓝ₄** | 62-key preview debt paydown | YES | pure paydown; leverage to nothing |
| **Ⓔ Ⓓ Ⓕ** | ledger / components / projection | **NO** | unchanged: untracked, operator, unimportable |

### Why Ⓢ is top

⚑⚑⚑ **It is the only item on the list that this session has already MEASURED to be a defect and
then declined to fix in the same breath.** Rule 11 records: the ratchet is two-valued, it reports a
fan-out identically to ordinary growth, and an operator cannot tell which refusal was ambiguous.
That was written down as *owed* — and a thing recorded as owed by the same session that recorded it
is at maximum risk of never being collected, because the writing feels like discharge.

**Structural leverage:** the three-outcome discipline is already this repo's rule (a comparison
that cannot be made reports INVALID, not FALSE). The ratchet is the one place holding it that
violates it. Every later component lands *under* the ratchet, so a two-valued ratchet propagates
its ambiguity into everything Ⓓ brings in.

⚑ **And it closes the one axis where the peer is ahead**, which matters while the divergence is
small — the same hash-consing argument that made Ⓜ urgent, still live.


---

# Tick 2 — 2026-09-06

**Measured:** 5 of 6 census legs filed (`rosettapkg` landed since tick 1); all six parties live; **no
freeze called**. Substrate's island unchanged at 10/32; ledger untracked; paperkit unimportable.

**Consumed: Ⓨ** — the mypy domain witness, wired into the gate and F-armed. Rule 16.

⚑ **The tick's own instrument was the previous tick's item, and this tick's item found two defects
in itself.** `blockers.sh` (tick 1) and `domain_witness.sh` (tick 2) are both meta-instruments —
things that check whether a check is real. That is not a coincidence of ordering: **an unarmed claim
outranks an unpaid debt**, because the debt is visible and the unarmed claim is not.

## Re-derived

| | step | unblocked? | why here |
|---|---|---|---|
| **Ⓖ¹** | Domain witness for the OTHER two distributions | YES | `hooks` and `mdstruct` have the same unarmed claim; the witness is written and takes an argument |
| **Ⓩ** | Retire or wire `inbox/` | YES | measures a channel nobody uses; cheap |
| **Ⓝ₄** | 62-key preview debt paydown | YES | pure paydown, leverage to nothing |
| **Ⓒ¹** | Intake the closed ratchet subgraph under the operator ruling | **PARTIAL** | ruling exists; substrate must confirm with its own operator |
| **Ⓢ¹** | selftest→pytest conversion (Rule 13's contract) | **NO** | needs the code to be intaken first |
| **Ⓔ Ⓓ Ⓕ** | ledger / components / projection | **NO** | unchanged |

**Ⓖ¹ is top** and it is nearly free: the witness already takes `(dist, target, victim)`. ⚑ Arming one
distribution and leaving two carrying the identical unarmed claim is the *"a control proves the query
works, never that the search space was right"* defect — the witness exists, so the remaining cost is
naming the other two victims, and not doing it would leave 2/3 of the corpus asserting an untested
property.


---

# Tick 3 — 2026-09-06

**Measured:** identical to tick 2 — 5 of 6 legs, no freeze, all six live, no blocker cleared.
⚑ **A tick where nothing moved is still a tick**; the measurement is what makes "nothing moved" a
finding rather than an assumption.

**Consumed: Ⓖ¹** — domain witness extended to `mdstruct` and `hooks`. Rule 17. Cost: **77s/commit**,
uncacheable by construction.

## Re-derived

| | step | unblocked? | why here |
|---|---|---|---|
| ~~Ⓩ~~ | ~~Retire or wire `inbox/`~~ | **DONE — and the premise was false** | Rule 18. 79 messages across 4 peers; mine is the only empty one. WIRE, not retire. |
| **Ⓝ₄** | 62-key preview debt paydown | YES | pure paydown; leverage to nothing |
| **Ⓡ** | Domain witness for the OTHER checkers (ruff, ratchet) | ⚑ **NEWLY VISIBLE** | see below |
| **Ⓒ¹** | Intake the closed ratchet subgraph | PARTIAL | ruling exists; substrate confirms with its operator |
| **Ⓔ Ⓓ Ⓕ Ⓢ¹** | ledger / components / projection / conversion | NO | unchanged |

### ⚑⚑ Ⓡ became visible only by finishing Ⓖ¹, which is what the sequencing rule is for

Three ticks have armed **mypy's** domain across three distributions. **Nothing has armed ruff's or
the ratchet's.** The claim is weaker for them — ruff is per-file, so its domain is less obviously
transitive — but *"weaker claim"* is not *"tested claim"*, and the ratchet's domain includes its own
**baseline file**, which is the input a careless declaration drops (`ratchet_check.sh` says so in its
own header and nothing verifies it).

⚑ **The witness is generic and takes `(dist, target, victim)`.** The remaining cost is naming a
victim per checker — but ⚑⚑ **arm 2 needs a defect the checker will actually catch**, and a *type*
error is mypy-specific. A ruff witness needs a lint violation; a ratchet witness needs a new census
key. **The witness's arm-2 payload is checker-specific and currently hardcoded** — that is the real
work in Ⓡ, and it was invisible until three mypy witnesses existed to generalize from.

⚑ **Ⓩ still outranks it** on cost: retiring `inbox/` is minutes and removes a standing green-over-
nothing, where Ⓡ is a parameterization job.


## ⚑⚑ Tick 3 addendum — Ⓩ reversed the derivation that proposed it

Tick 1 recorded: *"the inbox is not the channel; the message bus is. The inbox measures a thing
nobody uses."* **Measured across peer trees: 79 messages in four peer inboxes, zero in mine.** The
channel is the ecosystem's most-used durable transport and mtools is the only party receiving
nothing — while I had written **four files into peer inboxes the same day**.

⚑ **The item survived three derivations as "cheap, removes a green-over-nothing" because the
derivation kept re-reading its own earlier conclusion instead of the directory.** That is precisely
what "derive it FRESH" is for, and it took actually running a command against peer trees to break.

**Standing action, not a code change:** peers do not know this inbox exists. Telling them is a
message, and it is the only thing that converts a working channel into a used one.


---

# Tick 8 — 2026-09-06

**Measured:** freeze **NOT CALLED** (`roster: 6 of 6, 1 non-terminal`), no blocker cleared, all six
parties live, one inbox message already consumed. ⚑ The freeze poll now runs from `blockers.sh`
rather than being reconstructed — the first tick where I read the answer instead of deriving it.

**Consumed: Ⓠ** — the cron's own *"prefer runnable over recorded"* instruction, applied literally,
and it found a defect in the record on the first look.

## What the instruction actually surfaced

Counting: **26 rule headings, 9 executable lines in the gate.** But the useful finding was not the
ratio — it was that the heading sequence **stepped 22 → 24**. Rule 23 was cited by a commit and
never written.

⚑⚑ **Every gate here checks whether the CODE is correct. Nothing checked whether the MESSAGE was
true** — and the message is the durable artifact. A reader six months out reads the commit, not the
diff. Now gated (`rule_citations.sh` + a `commit-msg` hook), and armed against **the real historical
commit**: it refuses at the moment the defect was made and passes now.

**Second-order:** wiring that hook exposed the shellcheck target naming **7 files by hand against a
repo holding 11**. `domain_witness.sh` and `collect_check.sh` had been written and never added. That
is Rule 15's denylist defect **inside the target whose purpose is total coverage** — globbed, and
F-armed with a deliberately broken `.sh` at the root.

⚑ **Three ticks running, the item has been an instrument rather than a feature**, and each was found
by using the previous one. `blockers.sh` (tick 1) → the domain witness (2–5) → the freeze poll
(7) → the citation gate (8). **An unarmed claim outranks an unpaid debt** still holds, and the
supply of unarmed claims is not running out because each new instrument makes a new class visible.

## Re-derived

| | step | unblocked? | why here |
|---|---|---|---|
| **Ⓝ₄** | 62-key preview debt paydown | YES | the only remaining item that is *work* rather than instrumentation |
| **Ⓦ** | A witness that a rule's *claim* is still true, not just cited | YES | the citation gate proves a rule EXISTS; nothing checks it still holds |
| **Ⓒ¹** | Intake the closed ratchet subgraph | PARTIAL | operator ruling exists; substrate confirms with its own operator |
| **Ⓔ Ⓓ Ⓕ Ⓢ¹** | ledger / components / projection / conversion | NO | unchanged |

⚑ **Ⓦ is the honest successor to this tick and I am naming it rather than doing it**, because it is
the same shape one layer up: a rule can be present, cited, and *stale*. Rule 12's counter semantics,
Rule 3's platform behaviour and Rule 6's mypy claim are all measurements of a system that changes
under them. **A citation gate proves the pointer resolves; it says nothing about whether the target
is still true.** That is a real instrument and a large one.


---

# Tick 10 — 2026-09-06

**Measured:** freeze **NOT CALLED** (6 of 6, 1 non-terminal), no blocker cleared, six parties live.

**Consumed:** the inbox reader — it listed messages *present* rather than *unread*, so the
rosettapkg letter (acted on, and the basis for Rule 21) reported as new mail every tick and would
have forever. ⚑ **Rule 18's own failure forming inside the instrument that produced Rule 18.**
Fixed by adopting `inbox/archive/`, **measured in two peer trees before inventing anything**
(cassian 9 live / 11 archived; paperkit 42 / 5).

## Ⓝ₄ examined and NOT taken — it is an operator decision, not work

The 62-key preview debt breaks down as:

```
35  docstring-missing-returns      <- 56% of the whole debt, one rule
 6  noqa-comments
 5  docstring-missing-exception
 5  compare-to-empty-string
 4  suspicious-subprocess-import
 7  others (7 distinct rules, 1 each)
```

⚑⚑ **The 35 are not missing documentation.** Measured: almost every flagged docstring **already
states its return in the summary line** — *"Return the baseline's state and its key set"*, *"Run the
ratchet…; return 0 on pass, 1 on refusal"*. DOC201 wants a literal `Returns:` **section**; the
corpus uses a declarative first line, consistently, across ~150 files (**3 sectioned docstrings
total, repo-wide**).

⚑ **A hypothesis I ran instead of reporting:** that this was one unset config key
(`[tool.ruff.lint.pydocstyle] convention`). **Measured: `pep257` leaves all 10 ratchet findings
standing** — that key governs `D` rules, not `DOC` rules. Verified the accepted form by adding a
real `Returns:` block to one method: `All checks passed!`. So the paydown is genuine work, ~35
docstrings, and **it would restate what the summary lines already say.**

**This is a decision about house style, not a defect**, and it is the operator's:

| option | cost | effect |
|---|---|---|
| pay it down | ~35 docstrings across 3 dists | satisfies DOC201; adds a section restating each summary line |
| declare the convention | one `ignore` entry, with its measurement | ⚑ but this repo's rule is **declare, never suppress** — an `ignore` needs an argued reason, not a preference |
| leave it baselined | zero | the ratchet already refuses *growth*; the debt is frozen and cannot expand |

⚑ **Leaving it baselined is not neglect** — the set-membership ratchet refuses any new key, so this
debt is bounded. **Ⓝ₄ is therefore the lowest-leverage item on the list and I am not taking it
without a ruling**, because either action changes ~35 files to satisfy a preference nobody has
stated.

## Re-derived

| | step | unblocked? | why here |
|---|---|---|---|
| **Ⓐ¹** | Wire `rule_freshness.sh` into `blockers.sh` too | YES | it runs in the gate but not in the tick's own re-derivation |
| **Ⓝ₄** | preview debt | ⚑ **NEEDS A RULING** | see above — style decision, not work |
| **Ⓒ¹ Ⓔ Ⓓ Ⓕ Ⓢ¹** | intake / ledger / components / projection | NO | unchanged |


---

# Tick 12 — 2026-09-06

**Measured:** freeze **NOT CALLED**, nothing unread, both environment premises FRESH, six live.

⚑ **A blocker moved without anyone telling me, and only re-measuring found it.**
`substrate/file_header.py` was reported as *"staged, not committable"* two ticks ago. **It is now
TRACKED**, along with its selftest. No message announced that — which is precisely Rule 14: the
record moved, and I would only ever have learned it by going to read the record.

## The intake boundary, measured rather than relayed

Substrate claimed the module's **reader half** (`read`, `entry`, `entries`, `missing`, `by_tree`)
imports neither `corpus` nor `walk_scope`, so it lifts without their untracked dependencies. **Rule
25 says run it, so I did** — twice, because the first pass contradicted it:

```
grep:  corpus used at 144-145, walk_scope at 192   -> "the claim is half wrong"
```

⚑ **That reading was mine, not theirs.** Locating the enclosing functions: `corpus` is used only by
`population()` and `walk_scope` only by `main()` — the corpus-walker and the CLI, exactly the two
substrate named. An AST pass over the five reader functions confirms it: **they touch neither name.**

⚑⚑ **The near-miss is the finding: a line-number grep answered "where does this appear" when the
question was "which function needs this".** Same file, same tool, one quantifier apart — Rule 25's
shape again, and this time it would have contradicted a peer's correct report.

## Ⓢ¹ is closer than the plan says, and its precondition is now a question rather than a blocker

| | was | now |
|---|---|---|
| operator ruling (mtools side) | given | given |
| `file_header.py` committable | ⚑ staged only | **TRACKED** |
| reader-half closure | claimed | ⚑ **AST-verified here** |
| substrate's own operator | outstanding | **unknown — asking** |

**So the only remaining unknown is substrate's operator**, and that is a question to ask rather than
a state to infer from a git listing. ⚑ **Inferring readiness from `git ls-files` would be exactly
the permission-laundering shape I refused earlier**: a peer's tracked file is not a peer's consent.
