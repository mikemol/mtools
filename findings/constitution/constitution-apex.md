# `constitution` — APEX

**Built against `CENSUS-constitution.md` rev 37 (FREEZE CALLED, 2026-09-06T14:54:59-04:00).**
Prefix `AX-`. Author: a session that filed no leg, argued no position in this census, and read the
seven legs cold after the freeze. The operator chose this over letting a party build it.

## AX-00 My own denominator, stated first

| what | count |
|---|---|
| legs read **completely**, via harness `Read`, whole file | **7 of 7** |
| run file read completely (`CENSUS-constitution.md`, 304 lines, revs 1–37) | 1 of 1 |
| legs I could not read | **0** |
| peer repos I inspected directly | **0** — I measured nothing in any tree |

⚑ **What that costs, stated as a control and not as a hedge.** Every figure in this apex is
**quoted from a leg**, and per `§V` rev 12 and rev 28 a leg's figures are *measured at filing time
and not maintained*. I re-derived **nothing**. Where two legs measured the same object I can compare
their reports and that comparison is mine; where one leg reports alone, the claim is that leg's and
I say whose.

⚑ **`§X` is dispatcher-supplied and unverified (rev 2), and it was wrong six times by its own
author's count (`mtools-constitution.md:20`).** No row of this apex rests on `§X` alone. Where `§X`
is cited it is cited as *the thing a leg was correcting*.

⚑ **Anything I refuse to rule on is in `AX-09`, not omitted.**

---

## AX-01 The span — what every leg holds, with a witness per identification

Phase 1 per `§C`. **An identification needs a witness; a bare name-match is not one.** Below,
**CONVERGENT** means two or more legs state the same rule with independently stated measurements;
**IDENTICAL-SUBJECT** means they name literally the same artifact.

### AX-01a The four rules stated by five or more of seven legs

Counted by reading each leg's q2 section in full. Denominator **7** throughout.

| rule | legs stating it | citation per leg |
|---|---|---|
| **A verdict is `$?` from the command itself, never after a pipe, never from stdout** | **5 of 7** — mtools, paperkit, summit, cassian, (substrate implicitly via SB-A5's genre argument) → **counted as 4 explicit + 1 adjacent; I report 4** | `mtools:87` "MT-02a"; `paperkit:161` "PK-02a"; `summit:111` "1. A verdict is `$?`"; `cassian:223` "`CO-A1`" |
| **An unarmed / unrunnable gate is silent and reads as a pass — armed-ness is OBSERVED, never inferred** | **5 of 7** — linux-sources, summit, cassian, paperkit, rosettapkg | `linux-sources:166` "LS-02a"; `summit:145` "8. Advisory is not a weaker guard; it is no guard"; `cassian:252` "`CO-A3`"; `paperkit:81` "THREE OF FIVE ARMED HOOKS CRASH … THEY FAIL OPEN"; `rosettapkg:66` "a gate nobody runs is a script" |
| **A negative must carry its denominator / population / positive control** | **5 of 7** — mtools, rosettapkg, summit, paperkit, substrate | `mtools:97` "MT-02b"; `rosettapkg:110` "`RP-02b`"; `summit:122` "3. Report `n of m`, never a bare count"; `paperkit:183` "PK-02e"; `substrate:187` "SB-A5" |
| **Re-opening a settled rule costs a MEASUREMENT, never an argument** | **7 of 7** | `mtools:229`; `paperkit:339`; `rosettapkg:252`; `summit:311`; `linux-sources:403`; `cassian:456`; `substrate:408` |

⚑ **The fourth row is the only unanimous one in the entire census, and `AX-05` argues it is
worthless as stated.**

### AX-01b Two identifications I make, with witnesses

**AX-01b-i — `substrate`'s `SB-A10` and `rosettapkg`'s rev-15 article are ONE article.**
`§V` rev 15 explicitly left this open: rosettapkg *"cannot read that leg pre-freeze, holds no
witness, and says so"*, and the run file records *"The apex has two independent derivations to
identify or not, with the witness question still open."*

I identify them. The witness is that **each derivation's own instance list contains an artifact kind
the other's does not, and both lists fail identically for the consumer.**

- substrate, `substrate-constitution.md:212`: *"A shared artifact must not depend on a precondition
  it cannot carry — and where it names a successor, the successor must be reachable by the party
  that receives the refusal, or it must name none."* Instances: a refusal's successor path
  (`SB-A10′`), a module-scope import (`SB-13‴`).
- rosettapkg, via `§V` rev 15: *"an artifact that directs a reader outside itself must carry a
  referent the READER can resolve, not one only the PRODUCER can."* Instances: a **claim** (commit
  hashes in prose), a piece of **advice** (a capability row), a **record** (a commit citing a
  nonexistent Rule 23), an **instrument** (`cite-check.py`, rev 19).

**Six instances, six artifact kinds, one failure for the consumer: the pointer resolves in the
producing tree and nowhere else, and nothing errors.** Neither party's instance set is a subset of
the other's, which is what makes this a convergence rather than one party hearing the other.

⚑ **What I do NOT identify:** substrate's *checkable form* (`every module-scope import resolves from
the consumer's root; every successor is a package coordinate or harness-provided tool` —
`substrate:224`) is **narrower** than rosettapkg's, which covers prose claims and records that have
no import to check. The article is one; **substrate's gate is a partial implementation of it** and
should not be read as the article's full test.

**AX-01b-ii — `paperkit`'s `hook_gate_running.py` and `linux-sources`' are NOT identified.**
paperkit asked for exactly this ruling: *"Two repos, same need, no shared body. I cannot tell from
inside whether mine descends from theirs or is parallel; my earliest commit touching it is `0893d86`.
This is exactly the identification the apex must witness rather than assume"* (`paperkit:312`).

**I refuse the identification and it is not a coin-flip.** linux-sources reports its file **HELD AS
CODE, md5 `e1fd0d91`** (`linux-sources:83`); paperkit reports *"paperkit's own file, local"*
(`paperkit:39`) and gives **no hash**. **The identification cannot be made because one of the two
witnesses does not exist in the record.** ⚑ And the two stated *reasons* diverge sharply — paperkit's
is a **2,496–14,420 second** gate (`paperkit:200`), linux-sources' is `/proc`-readable process-table
inspection that **fails open** because *"the cost prevented is a WASTED GATE RUN, not corruption"*
(`linux-sources:229`). **Same name, adjacent need, unknown relation.** Recorded in the divergence
register (`AX-08`), not glued.

### AX-01c The non-identifications, stated explicitly per `§C`

- **`hook_cmdparse`** exists in four bodies: substrate `27cddbcb`/492L, summit `8096c871`/364L
  (**HELD**, with reason, `summit:87`+`SM-06`), cassian `83a15017`/418L (**drifted, reported as
  yellow**, `cassian:193`), mtools `d7d16278`/245L (**HELD**, one function deliberately dropped,
  `mtools:71`). ⚑ **Three of four differences are HELD with a stated reason and only cassian's is
  drift.** `§X` called this *"three distinct bodies"* and implied rot; **rev 3's correction was
  right and it undercounted — there are four bodies and three are deliberate.**
- **paperkit's five hooks are byte-identical to substrate's and are a different program.** paperkit
  measured this itself and retired its own claim: *"Identical bytes in a different tree are a
  different program"* (`paperkit:94`). **A hash-based identification of hook bodies across repos is
  refuted by measurement in this census.** Any conformance instrument keying on content hash
  inherits that defect.

---

## AX-02 ⚑⚑ THE SILENCES — what NO leg says

This is the highest-value section per the brief and I put my sharpest findings here.

### AX-02a ⚑⚑⚑ NO LEG PROPOSES A MECHANISM BY WHICH AN ARTICLE REACHES A REPO. 0 of 7.

Every leg answers q5 (*what should re-opening cost*). **Not one answers the question one step
earlier: what does ADOPTING cost, and who performs the adoption.** The legs specify:

- the **evidence bar** to amend (7 of 7: a measurement)
- the **residue discipline** (paperkit `PK-05`.3, cassian `§Q-5`.1, substrate `SB-A9`.3,
  linux-sources `LS-06`.2 — 4 of 7)
- the **direction asymmetry** (substrate `SB-A9`.4 *"Loosening a rule should cost more than
  tightening one"*; rosettapkg `§Q5`.4 same — 2 of 7)

**And zero of seven say who runs the adoption, when, or what a repo does on the day an article
lands.** rosettapkg comes closest and states the gap rather than filling it: *"I hold zero hooks, so
**every article is a re-opening for me** — I cannot adopt one without deciding it applies, which is
the relitigating the operator is complaining about, performed seven times"* (`rosettapkg:247`).

⚑ **That is the operator's complaint verbatim, and the census answered around it.** The survey asked
what re-opening should cost and got seven careful answers; **the operator said he is tired of
walking repos through lessons**, which is an *adoption* cost, not an *amendment* cost. **The
question `§Q` asked is not the question the operator asked.**

### AX-02b ⚑⚑ NO LEG PROPOSES A DEFAULT FOR A REPO THAT HAS NOT ANSWERED. 0 of 7.

Every leg treats articles as opt-in. Nothing in any leg says what a repo is presumed to hold before
it has been surveyed. **rosettapkg is the live case** — zero hooks, zero settings.json, and its own
`RP-03c` asks for an **inapplicable** state (`rosettapkg:260`) — and even it does not propose a
default. ⚑ `§V` rev 17 named this as the census's *own accounting* gap (*"does not apply" is not
"not answered"*, four instances across two runs) and **no leg carried it into the constitution's
design.** The apparatus needed the distinction four times and the product does not have it.

### AX-02c ⚑⚑⚑ NO LEG ASKS WHAT HAPPENS WHEN TWO ARTICLES CONFLICT. 0 of 7.

And **the census contains a live conflict nobody flagged as one.** `linux-sources:222` explicitly
contests the candidate article *"A gate must REFUSE when its tool is absent, never skip"* and holds
**both directions** with a measured discriminator; `cassian:264` states the refusing side and calls
it *"a strictly stronger form"*; `mtools:124` states the refusing form flat as `MT-02e`. **Three
legs, three positions, and no leg has a rule for what an implementer does with that.** I rule on it
in `AX-03a`.

### AX-02d ⚑⚑ NO LEG MEASURES WHETHER ANY OF ITS OWN ARTICLES WOULD PASS IN A PEER'S TREE. 0 of 7.

Every leg's q2 is stated as *checkable*. **Not one leg ran its own check against another repo**, and
the embargo (`§Q`, brief §2) is what made that impossible. The three legs that came closest all
report the same shape from different angles and **none of them draws the conclusion**:

- `substrate:611` — *"a per-repo instrument is scoped to its repo, and the defect is
  ecosystem-wide"*
- `mtools:220` — *"Gated locally. ⚑ Insufficient, per rev 10"*
- `linux-sources:283` — *"a repo that routes its consumers to a single tool has taken on an
  obligation to that tool's defects"*

⚑ **So the census produced 30+ checkable articles and zero cross-repo checks, in a census whose own
strongest structural finding (rev 10, rev 13, `mtools:222`) is that per-repo instruments cannot see
this class.** The legs diagnosed the disease and every one of them shipped the treatment that
doesn't work. **Naming it did not immunise any of them — which is `AX-06`'s article arriving at the
level of the census itself.**

### AX-02e ⚑ NO LEG COSTS THE CONSTITUTION. 0 of 7.

No leg estimates what conformance would cost in engineering time, what it would break, or what
fraction of its current tree would fail. paperkit measured three of five hooks fail-open
(`paperkit:81`) and did **not** fix them, filing rather than patching — correctly, per its own
reasoning. **But no leg answers "if this constitution were ratified tomorrow, how many of my gates
go red."** rosettapkg is the party positioned to price adoption from zero (`§R` says so explicitly,
run file line 21–24) and its answer is *"every article is a re-opening for me"* — a shape, not a
number.

### AX-02f ⚑ NO LEG NAMES A RATIFYING AUTHORITY OR A QUORUM. 0 of 7.

substrate is the only leg to touch it and only negatively: *"What should NOT be required: unanimity.
A rule that cannot be amended without seven repos agreeing is a rule that rots"* (`substrate:418`).
**Nobody says what IS required.** `§C` reserves ratification to the operator and no leg engages with
what that means procedurally.

### AX-02g ⚑⚑ NO LEG CONSIDERS THE ARTICLES' OWN STALENESS, THOUGH TWO NOMINATED THE AUTHORITY ON IT.

`summit:381` and `cassian:487` both nominate **`gabion`** for exactly this — summit quoting its own
`CLAUDE.md`: *"paperkit governs claim ↔ witness (is this true?); gabion's docflow governs document ↔
dependency-over-time (is this still current?). **Freshness is not truth.**"* — and warning *"A
constitution census that omits the freshness authority will produce a truth-only constitution."*
⚑ **It did.** Every q5 answer is about *is this still true*; **none is about *is this still
current*.** And `linux-sources:441` supplies the instance in miniature: its own `CLAUDE.md` says 24
claims where `warrants.bib` holds 42, in *"a repo whose entire discipline is anti-staleness"*, with
the correct generalisation already written: *"A constitution will have this property the day after
it is written unless its figures are generated."*

---

## AX-03 Adjudications — q2 vs q3, and q2 vs q2

I apply rev 11's cost test and rev 24's split option myself. Where I decline, `AX-09`.

### AX-03a ⚑⚑ RULING — *a gate must REFUSE when its tool is absent* is WRONG AS STATED. It SPLITS.

**The disagreement.** `mtools:124` (`MT-02e`) states it flat and binding. `cassian:264` (`CO-A4`)
states the refusing side plus a third state. `linux-sources:222` (`LS-03`) contests it and holds
**both directions in one repo** with three measured cases.

**I rule with linux-sources, and the evidence that decides it is that linux-sources is the only
party holding both arms.** Its table (`linux-sources:226-230`):

| guard | behaviour | its own stated reason |
|---|---|---|
| `.githooks/pre-commit`, bazel absent | **REFUSES** | *"a silent skip here would be the guard's-silence-reads-as-approval defect"* |
| `hook_gate_running`, `/proc` unreadable | **FAILS OPEN** | *"the cost prevented is a WASTED GATE RUN, not corruption, and a guard that refuses everything whenever it cannot tell is worse than the problem"* |
| `hook_shellcheck`, shellcheck absent | **FAILS OPEN AND SAYS SO ONCE** | *"so an inert gate cannot masquerade as a passing one"* |

⚑ **A leg holding both directions of a rule, with a stated discriminator, outranks two legs each
holding one direction** — because the two one-directional legs have never been on the wrong end of
their own rule, which is summit's own `SM-02`.7: *"A gate that only ever catches other people is a
gate nobody has tested"* (`summit:140`).

**BINDING (the article):** *the refuse-vs-fail-open choice is indexed on WHAT THE GUARD PREVENTS —
corruption or an unrecoverable false green → REFUSE; wasted work → fail open — and **fail-open is
permitted only with an announcement**, exactly once.* linux-sources states it at `:232`.

⚑⚑ **AND CASSIAN'S THIRD STATE SURVIVES THE SPLIT AND IS THE STRONGER HALF.** `CO-A4`
(`cassian:264`): *"'cannot run' is a THIRD state, distinct from pass and fail"*, gated as `T134`,
*"a projector that cannot run is UNKNOWN, not stale."* **That is orthogonal to refuse-vs-fail-open
and both legs need it.** substrate independently: `SB-A5`, *"UNMEASURABLE — no verdict, NOT clean"*
(`substrate:191`), and `SB-A6`, *"ABSENT and EMPTY are opposite, not two shades of degraded"*.

**So the ruling is a split with a three-state floor:**
- **BINDING:** a guard that cannot run must emit a **third verdict** distinguishable from pass and
  from fail. *(cassian `CO-A4` + substrate `SB-A5`/`SB-A6` + summit `SM-02`.5 = 3 of 7 independent,
  and linux-sources' `LS-02h` "Exit 2 is UNAVAILABLE … NOT a failed claim" makes 4.)*
- **BINDING:** the pass/refuse choice is indexed on what is prevented, per linux-sources.
- **NOT BINDING:** *"always refuse"* as `mtools:124` states it. ⚑ **The conclusion mtools reached is
  right for its own gate and its stated warrant generalises falsely.** See `AX-04a`.

### AX-03b ⚑⚑ RULING — the rev-11 misclassification is a CLASS. Confirmed at FIVE, not three.

`§V` rev 21 said two, rev 23 corrected to three (substrate, summit, rosettapkg). **Reading the seven
legs, it is five.** Enumerated, because rev 25 established that a universal without a denominator in
this census is a defect:

| party | rule filed local | reasoned from | outcome | citation |
|---|---|---|---|---|
| `substrate` | no `sys.path` insert | its own 14 call sites | **SPLIT** | `substrate:334` |
| `summit` | modules stay stdlib-only | *whose constraint it is* | **MOVED** | `summit:206` |
| `rosettapkg` | byte-exact citation discipline | *what its product is* | **SPLIT** (rev 24) | `rosettapkg:169` |
| `paperkit` | symlinked hooks (`PK-03b`) | *paperkit's motive — zero drift* | **MOVED**, general half filed | `paperkit:228` |
| `cassian` | `CO-L4` prepare-never-apply; `CO-L2` unit caps | *its own motive (`sudo` denied)*; *"a fact about this host"* | **`CO-L4` MOVED, `CO-L2` SPLIT** | `cassian:370`, `cassian:337` |

**Five of seven parties. Six rules. Every one reasoned from a true fact about its own repo, and no
two reasoned the same way.**

⚑ **AND THE TWO WHO DID NOT ARE THE INFORMATIVE HALF.** `mtools` applied the test *before* filing
and **explicitly declined a move that rev 11 alone would have forced**: *"It stays LOCAL because the
rule is right and the cost is an artifact of seven sessions sharing one working tree… Recorded
because I nearly filed it as binding on rev 11's test alone, and rev 11 without rev 24's split would
have produced that"* (`mtools:165`). `linux-sources` applied rev 11, over-moved
(`LS-04a`), then rev 24 arrived and it **split its own flip** (`LS-04b`, `linux-sources:294`).

**So the ruling is: rev 11 is a real class at 5/7, AND rev 11 unaccompanied by rev 24 over-moves.**
Two of the seven have now demonstrated the over-move — one by avoiding it under protest, one by
committing and repairing it. ⚑ **Rev 11 and rev 24 are one article and must not be adopted
separately.**

**AX-03b-ii — cassian's own honest limit, which I sustain.** `cassian:510`: *"What I still cannot
see is whether the two that survived (`CO-L1`, `CO-L3`) survive because they are genuinely local or
because I stopped looking after two flips — the test has no stopping rule."* ⚑ **The test has no
stopping rule and none of the five parties supplied one.** I do not supply one either; see `AX-09b`.

### AX-03c ⚑ RULING — the four q3 rules I confirm as genuinely LOCAL, with the cost test applied by me

I applied rev 11 to every q3 item across all seven legs. These four survive cleanly and I state them
because a constitution needs to be able to say *this is not an article*:

1. **linux-sources' corpus/ledger distinction and its seven siblings** (`linux-sources:246-254`).
   The leg re-checked each one at a time and I agree: *"nobody outside this repo pays when the
   corpus/ledger line blurs, when a version stamp goes stale, when `.pc/` shadows leak"*. ⚑ **And
   `STALE ≠ WRONG` is the sharpest genuinely-local rule in the census** — `linux-sources:249`:
   *"Wrong elsewhere: in most repos a stale answer is a wrong one."*
2. **summit's `floor/` gates red by design** (`summit:232`). A green floor means no ask is
   outstanding. Nobody outside summit reads that slice.
3. **paperkit's mutation sweep** (`paperkit:224`) — *"the cost of not sweeping is paperkit's own
   claims grading indeterminate."*
4. **rosettapkg's `text`-fence exemption** (`rosettapkg:178`) — and it is the best-argued local rule
   in the census, because it records the failed *general* version: *"my first fix was too broad — it
   also exempted untagged fences… **the author's tag is evidence; the absence of a tag is not.**"*

### AX-03d ⚑⚑ RULING — mtools' `MT-03c` is a SPLIT it declined to make, and I make it.

`mtools:158`: *the pre-commit gate reads the whole tree rather than the staged pathspec*, filed
**LOCAL**, with the leg recording that the cost does **not** land only on mtools: *"every party
serialises on the dirtiest party's green… `paperkit` and `substrate` each had a scoped, correct
commit refused by my in-flight mdstruct edits."*

mtools' stated reason for keeping it local: *"the cost is an artifact of seven sessions sharing one
working tree, which is a deployment fact rather than a property of the rule."*

⚑ **That reasoning is sound for the rule and it leaves a binding half unfiled, exactly as
`paperkit:273` diagnosed in itself twice** (*"I filed the instance and not the principle"*). Applying
rev 24:

- **LOCAL:** *a witness must mutate the real file, not a copy* — mtools' actual rule, and its warrant
  (*"a witness over a copy proves the copy's domain"*) is correct and repo-shaped.
- ⚑ **BINDING, and I file it because nobody did:** *a gate whose failure surface is wider than the
  committing party's own changes must publish that fact to every party sharing the tree.* The cost
  landed on **two named peers' correct commits** (`mtools:162`). Both declined `--no-verify` — which
  is to say **both peers paid, correctly, for a scope they had not consented to and could not
  observe.** That is cassian's `CO-L4` binding form (`cassian:389`) — *"an actor that mutates state
  SHARED with parties who did not consent must not do so unilaterally"* — arriving on a gate's
  refusal surface instead of on a kernel.

**Evidence that decides it:** the identical shape is filed by three other legs from three
directions — `cassian:389` (host state), `paperkit:225` (an unbudgeted gate oversubscribing a shared
box), `§V` rev 22 (the index lock). **Four instances, one article, and the fourth is mtools' and
unfiled.**

### AX-03e ⚑ RULING — cassian's `CO-A6` (regenerate, don't check) is BINDING but NARROWER than filed.

`cassian:291`: *"A projector's artifact must be REGENERATED by the gate, not merely checked
against"*, on the operator's own ruling (`cassian:296`). The leg states its own cost honestly:
*"projector correctness becomes commit-critical — the `--check` form refused a bad render, this form
writes it"* (`cassian:302`).

⚑ **I bind the diagnosis and not the remedy.** The binding half is `linux-sources:441`'s form: **a
figure in a governing document must be generated, not asserted** — *"A constitution will have this
property the day after it is written unless its figures are generated."* **Regeneration-in-the-gate
is one implementation and it trades a false-red for a false-write**, which cassian says out loud. A
repo whose projectors are less trusted than cassian's should not be forced into it.

**SPLIT: the anti-staleness obligation is BINDING; regeneration-at-commit is LOCAL to a repo whose
projectors are gate-quality.**

---

## AX-04 ⚑⚑ CONCLUSION vs WARRANT — right verdicts on wrong reasons

Per the brief's article: *a right verdict on a wrong warrant is a defect that ships in the
explanation.* I found three in the frozen legs.

### AX-04a mtools `MT-02e` — right rule for its gate, warrant generalises falsely

`mtools:124`: *"A gate must REFUSE when its tool is absent, never skip… **The union takes the shape
as a rule, not the instance.**"* Its warrant is the union of two observations: substrate's
`check_scratch_runtime.py` printed SKIPPED and exited 0, and linux-sources' pre-commit refuses.

⚑ **The union of two points is not a shape.** linux-sources holds **three** cases and the third
(`hook_shellcheck`, fails open with an announcement, `linux-sources:230`) falsifies the universal.
**mtools generalised from a two-element population** — which is `MT-02d`, its own article
(*"a hand-written population in a checker rots"*), committed in the leg that states it. The verdict
is right for mtools' bazel gate; the warrant would make a conformance checker red linux-sources for
being right.

### AX-04b paperkit `PK-01` — a claim retired twice in one leg, and the second retirement is the finding

`paperkit:44`: *"PAPERKIT HAS ZERO CONTENT DRIFT, AND NOT BECAUSE IT IS DISCIPLINED."* Retired at
`:94` (*"identical bytes in a different tree are a different program"*) and retired **again** at
`:142` (*"PK-01b said identical bytes … True, and it presumes the bytes are stable. They are not"*).

⚑ **Both retirements are kept in place and the leg says why** (`paperkit:341`: *"A withdrawn ruling
stays visible as residue, never deleted… because deleting them repeats the move they illustrate"*).
**I record this as the census's best-executed instance of the residue discipline** and note that the
*conclusion* the leg reaches from it — *"the code a repo executes must be nameable"* (`paperkit:150`)
— is stronger than any warrant paperkit started with. **This is a wrong warrant repaired into a
better article by the party that held it, without being challenged.**

### AX-04c linux-sources `LS-04a` — right flip, insufficient warrant, self-corrected one revision later

`LS-04a` flipped the routing regime whole to BINDING on rev 11's test. `LS-04b` (`linux-sources:294`)
splits it: *"`LS-04a` HAD ONLY TWO OUTCOMES AVAILABLE AND SO IT OVER-MOVED."*

⚑ **The verdict "the routing half binds" survived both passes; the warrant changed completely.** The
first warrant was *the cost landed on summit*; the second is *routing and forbidding-the-fallback are
two rules and only the first binds*. **A reader inheriting the first warrant would have bound the
fallback ban on every repo** — which linux-sources itself measured as the half doing the damage
(`linux-sources:322`: *"Forbidding the textual fallback removed the second opinion that caught it"*).

---

## AX-05 ⚑⚑⚑ THE CENSUS'S UNANIMOUS ARTICLE IS THE ONE ITS OWN EVIDENCE REFUTES

**7 of 7 legs say re-opening should cost a measurement, not an argument** (`AX-01a`, row 4). It is
the only unanimity in the census.

⚑ **And the census measured, at least five times, that a stated rule does not bind its own author —
including authors who had published that exact rule.** Enumerated, with the denominator, because
this is a claim about a population:

| party | rule it held | how it broke it | citation |
|---|---|---|---|
| `rosettapkg` | `git ls-tree -r HEAD`, not `os.listdir` — quoted in its own tick report | counted legs with `os.listdir`, reported 5 where `HEAD` held 2 | `§V` rev 27 |
| `linux-sources` | point-sample-is-not-an-interval — **filed the class that morning** | reported *"PIDs recent and advancing"* from one sample, to the party who had refuted it | `§V` rev 33 |
| `linux-sources` | held `64.064s` in its own artefact | asserted the lock's nature for three ticks without taking it | `§V` rev 31 |
| `mtools` | PIPESTATUS discipline, **written into its own pre-commit as code** | lost an exit status to a pipe three times in one day | `mtools:91` |
| `substrate` | *never guess a mode name* — settled in its own tree | guessed `pycodemod --census`, *"in the tick where I am surveying rule adherence"* | `substrate:396` |
| `substrate` | `SB-L2`, no `sys.path` insert, ever | **its own exported hook does it at line 435** | `substrate:513` |

**Six instances, five distinct parties, denominator 7.** None under time pressure. **Three had
published the rule.**

⚑⚑ **So the unanimous article is unanimously believed and locally unenforceable, and the census
proved that about itself.** mtools is the only leg to draw the conclusion and it draws it flatly:
*"the amendment cost is the wrong question until the enforcement question is answered. A
constitution of stated rules, amendable at any price, changes nothing — it produces a document six
repos agree with and violate"* (`mtools:210`).

**I rule that mtools' three-tier framing (`mtools:215`) is the census's most load-bearing single
finding**, and I restate it because it is the answer to the operator's second quote:

1. **Stated** — costs nothing, binds nobody, measured worthless six times above.
2. **Gated locally** — binds its own repo, and is **insufficient**: rev 10 (summit's registered
   `spelling-census` caught neither of that class's two instances), rev 13 (substrate walked past two
   violations of its own article in its own directory), `substrate:611` (*"a per-repo instrument is
   scoped to its repo, and the defect is ecosystem-wide"*).
3. **Gated across repos** — the only tier with evidence.

⚑⚑⚑ **AND NO REPO IN THIS ECOSYSTEM CURRENTLY OPERATES TIER 3. 0 of 7.** That is `AX-02d`'s silence,
restated as a positive claim, and it is the constitution's actual first article.

---

## AX-06 ⚑⚑ AN ARTICLE NO LEG FILED, WHICH FIVE LEGS SUPPLY THE EVIDENCE FOR

**AX-06a — `AN ARTICLE'S AUTHOR IS THE WORST-PLACED PARTY TO FIND ITS VIOLATIONS AT HOME.`**

Filed as a candidate article by two legs in passing (`substrate:270`, `mtools:227`) and by neither as
a numbered claim. **`§V` rev 25 established its denominator, correctly, at four**, after rosettapkg
challenged a seven-party universal: *"four parties, each of whom found and precisely described a
defect class in another tree, failed to find an instance of that class in their own — in three of
the four, in an artifact they had authored and were actively using."*

Reading the legs, **the count is now five**, and the fifth is the one rev 25 could not have:

| party | class it described precisely elsewhere | its own instance | citation |
|---|---|---|---|
| `substrate` | `SB-A10` dangling successor | two in its own `_refusal()`, both symlinked to paperkit | `substrate:236` |
| `mtools` | hand-written populations rot (`MT-02d`) | its own `§X` drift table omitted `hook_pycheck` — *"the counter-example to its own thesis"* | `mtools:120` |
| `summit` | reasoning from benefit not cost | its own item 2 | `summit:206` |
| `rosettapkg` | the article of rev 15 | its own `cite-check.py`, unarmable outside its tree | `§V` rev 19 |
| ⚑ **`cassian`** | `CO-A5`, *a correction must reach the CONSUMER, not sit beside the claim* | **`CO-02`: its own `hook_shellcheck_wrap.py` docstring asserts a symlink constraint that was lifted by `◆hook-vendoring`** — *"the wrapper survived the change that dissolved its reason"* | `cassian:113` |

⚑ **Cassian's is the sharpest of the five and cassian did not connect the two halves of its own leg.**
`CO-A5` is stated at `:277` as an article about *this repo's session-entry file asserting a refuted
claim for weeks*. `CO-02` at `:103` is the identical class **in cassian's own hook docstring**, filed
120 lines earlier as a separate finding about `§X`. **Same leg, same defect class, two sections, no
cross-reference.** I state that as the corroborating instance the class needed, not as a criticism —
rev 25's whole point is that this is structural.

**AX-06b — the corollary, and it is the operator's problem in one sentence.** Combine `AX-06a` with
`AX-05`: **the party that just fixed a class is not covered against it, and the party that authored
an article cannot audit it at home.** ⚑ **Together those two make a self-enforced constitution
impossible in principle, not merely in practice.** The constitution's enforcement must be performed
by a party other than the article's author, or it does not enforce.

---

## AX-07 ⚑⚑ THE THIRD FAILURE MODE — the run file's own framing is incomplete

`§Q` distinguishes **distribution failure** (a fix does not travel) from **relitigation** (the
question is re-opened) and instructs every leg to keep them distinct. **Three legs report a failure
that is neither, and each names it independently.**

| leg | the shape | citation |
|---|---|---|
| `linux-sources` | **arrival without a write path** — substrate's `md_hkey.py` is *"tested 18/18 and unwired, behind an all-or-nothing per-file gate refusing every edit to `mdstruct`. **Two correct guards compose into a defect nobody can repair.**"* | `linux-sources:373` |
| `paperkit` | **arrival without effect** — *"the ruling was in the file, in this repo, in my editor — and it was relitigated anyway. So a package fixes strictly less than half of this."* 20 `⚑` rulings in `.bazelrc`, 3 re-derived the hard way in one session | `paperkit:298` |
| `rosettapkg` | **arrival without its measurement** — *"a packaged hook arriving without its settling measurement still faces a fresh session that reasons from scratch. **The measurement must travel with the code.**"* | `rosettapkg:270` |

⚑⚑ **These are three faces of one thing and I name it: the fix arrived, and the ARRIVAL was not the
binding event.** In linux-sources' case a second correct guard blocked the write; in paperkit's the
reader read past it; in rosettapkg's the code came without its warrant.

**RULING — this is a third category and the constitution needs it.** Distribution and relitigation
are both about *whether the rule got here*. This is about **whether being here does anything**, which
is `AX-05`'s three tiers viewed from the artifact rather than from the ecosystem. ⚑ **And it is the
category the operator will hit first**, because packaging — the obvious remedy for his first quote —
produces exactly this failure and produces it silently.

**paperkit's repair statement is the best in the census and I adopt it as the article's form**
(`paperkit:308`): *"A comment is a ruling with no index and no query surface. What was missing is the
ability to ASK **'what has already been settled about this file?'** and get an answer that is not a
full read."*

---

## AX-08 The divergence register — carried, not adjudicated (per `§C`)

Every entry stands with its leg and its witness. **Unverifiable ≠ wrong.**

| # | the divergence | positions | why I do not rule |
|---|---|---|---|
| D1 | **`hook_gate_running` identity** | paperkit `PK-04b` vs linux-sources `LS-01` | paperkit reports no hash. `AX-01b-ii`. |
| D2 | **The index-lock discriminator** | `§V` rev 22 (mtime advancing) → rev 29 (**refuted**, one-directional) → `cassian:140` (*"I hit the same lock, five times, and reached the correct conclusion without knowing the suite's runtime"*, mtime **advanced** for it) | ⚑ **Cassian's counter-instance and rev 29's refutation are compatible and neither party knows it.** Rev 29 proves mtime-STABLE is not evidence; cassian observed mtime-ADVANCING, which rev 29 explicitly preserves as *"evidence of life"*. **Both are right.** Cassian's stronger claim — *"an observation-based discriminator is available to every party"* (`cassian:151`) — survives; its **instance** was one of the two directions that works. Carried as a resolved-by-me identification, not a divergence. |
| D3 | **`§X`'s hook counts** | cassian `CO-01` (2× for every repo, with a per-repo control) vs substrate `SB-01` (*"I cannot reproduce 10 under any reading"*) vs `§V` rev 5 (dispatcher's own confirmation) | Three parties, one defect, three independent detections. ⚑ **Cassian's is strictly the strongest because it carries the control that shows the method was NOT uniform: paperkit's `§X` figure is the correct parsed count while its grep count is 16** (`cassian:74`). A table whose rows used two methods, in one column. **No divergence remains; I record the priority.** |
| D4 | **Whether summit is a peer or an authority** | `substrate:650` (*"the roster treats summit as a peer leg when it may also be an AUTHORITY for the question"*) | ⚑ **A structural question about the census, not about a rule.** I flag it and take no position: summit owns `runs-census` and `spelling-census`, both of which this census hand-re-derived (`substrate:373`, `:386`), and summit's own leg does not claim the authority. The operator's call. |
| D5 | **Advisory tier** | `§X` predicted legs would disagree on fail-open and advisory tiers | ⚑ **They did not.** 5 of 7 legs state *advisory is no guard* and **0 of 7 defend an advisory tier.** The predicted divergence did not occur. Recorded because a predicted-and-absent divergence is a finding about the prediction. |

---

## AX-09 ⚑ WHAT I REFUSE TO RULE ON, AND WHY

Per the brief: *a false PASS gets banked; a false finding gets argued with.* Prefer refusing.

**AX-09a — Whether `mdstruct`'s literal-by-default is a defect or a contract.** `§V` rev 30 and
`mtools:130` (`MT-02f`) call it a defect in the interface; `linux-sources:311` agrees and both
parties fixed the message. ⚑ **I cannot rule because the artifact changed under the census** —
`§V` rev 32 records that peers had been executing mtools' *uncommitted working tree* all afternoon,
and I did not measure the tool. **The two legs' agreement here is not two witnesses: one owns the
tool and the other was told the diagnosis** (`linux-sources:313`: *"diagnosed by `mtools-2e`, who
owns the tool"*). **Corroboration that could not have failed is decoration.**

**AX-09b — A stopping rule for rev 11's test.** cassian asked for one explicitly (`cassian:510`) and
handed it to the apex. ⚑ **I decline.** Every candidate I can state (*apply until two consecutive
items hold*; *apply to all items*) is either arbitrary or is what cassian already did. **The honest
answer is that the test has no stopping rule and a party applying it to its own list is the operator
whose bias it was written to catch** — which means the stopping rule is *a second party applies it*,
and that is `AX-06b`, not a procedure.

**AX-09c — Whether `~/.claude/skills/` should be a party.** Nominated by **two legs from two
directions** — `rosettapkg:231` (*"Three of the five rules I hold most firmly reached me through
skills in `~/.claude/skills/`… That tree is on no roster, files no leg"*) and `paperkit:357`
(*"census-kit's own postmortem… **That tree holds settled rulings, binds every session on this
machine, and is on no roster.**"*). rosettapkg records that the same nomination arrived in a *prior*
census: *"Two parties, two censuses, same absent party."* ⚑ **This is the strongest roster finding in
the survey and it is the operator's decision, not mine.** I record only that it is 2 of 7 legs plus a
prior run, and that `RP-02b` — one of the census's five-of-seven articles — **originated there and
was read, not derived** (`rosettapkg:292`).

**AX-09d — Whether any leg's figures are still true.** Per `§V` rev 28: a leg can be *fetchable and
stale* simultaneously and **nothing in this run distinguishes those.** Every figure I quote is as of
each leg's filing time. ⚑ **I did not re-derive one number** and I do not present any as current.

**AX-09e — mtools' `MT-06` working-tree inversion, as a checkable article.** `mtools:263`: *"for
every artifact another party invokes by path, is the invoked bytes' provenance `HEAD` or the working
tree? **No party in this census had asked it before today.**"* Corroborated in three legs
independently (`paperkit:106` measured five hooks executing files *in no commit anywhere*;
`§V` rev 36 measured substrate's `scratch/mdstruct.py` **untracked**). ⚑ **The finding is
established at 3 of 7 with measurements. What I refuse is the REMEDY**: paperkit's *"the code a repo
executes must be nameable"* (`:150`) and `§V` rev 36's note that *"the operator ruling that peers
copy from the working tree makes that intentional for READS"* are in tension, **and the operator has
already ruled on half of it.** Naming the remedy would spend authority I do not hold.

---

## AX-10 What I would hand the operator, ordered by evidence

Not a ratified constitution — `§C` forbids that and reserves it to the operator. **This is the span
plus the remainder, ordered.**

**Tier 1 — articles with 3+ independent derivations and a measurement each. 4 articles.**
1. *A guard that cannot run emits a THIRD verdict, distinguishable from pass and from fail.*
   (cassian `CO-A4`, substrate `SB-A5`/`SB-A6`, summit `SM-02`.5, linux-sources `LS-02h` — **4 of 7**)
2. *Armed-ness is OBSERVED by firing the guard, never inferred from configuration; and the F-arm is
   not optional.* (linux-sources `LS-02c` 34/34, summit `SM-02`.9 + `--only routes`, cassian `CO-A3`
   25 probes, substrate `SB-A8` 12 rows — **4 of 7, each with a running instrument**)
3. *A negative carries its denominator, its scope, and its mode; an asserted absence carries a
   positive control.* (**5 of 7**, `AX-01a`)
4. *A pointer out of an artifact must resolve for the READER, not only the producer.*
   (substrate `SB-A10` + rosettapkg's rev-15 article — **identified in `AX-01b-i`, 6 instances, 6
   artifact kinds**)

**Tier 2 — articles I ruled on in `AX-03`, as split.** The refuse/fail-open indexing rule; the
anti-staleness-of-figures obligation; the shared-tree-consent rule of `AX-03d`.

**Tier 3 — the three findings about the constitution itself, which outrank every article above.**
- ⚑ **`AX-05`:** a stated rule binds almost nothing — 6 measured instances, 5 parties, 3 of whom had
  published the rule. **The enforcement question precedes the amendment question.**
- ⚑ **`AX-06`:** an article's author cannot audit it at home (5 parties), and a party that just
  fixed a class is not covered against it. **Together: self-enforcement is impossible in principle.**
- ⚑ **`AX-07`:** arrival is not binding. Packaging fixes the operator's first quote and produces this
  failure silently.

**Tier 4 — the silences (`AX-02`), which are what the next run should ask.** Adoption cost and
mechanism (0 of 7); the default for an unsurveyed repo (0 of 7); article conflict resolution (0 of 7,
with a live conflict); cross-repo checking (0 of 7 operate it, 3 of 7 diagnose its necessity);
conformance cost (0 of 7); ratifying authority (0 of 7); article freshness (0 of 7, 2 nominated the
authority).

⚑⚑ **And the single sentence I would put at the top, which is `rosettapkg`'s and not mine**
(`rosettapkg:79`): ***a vocabulary is not a gate.*** The census produced 30+ well-argued articles and
measured, six times, that its own authors do not obey the ones they wrote. **A constitution is the
vocabulary. The question the operator asked is about the gate.**
