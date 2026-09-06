# `linux-sources` — constitution census, leg `LS-`

**Written against:** `CENSUS-constitution.md` **rev 1**, revised against **rev 11** before filing —
`LS-00`'s corroboration block and `LS-04a` are the only rev-11 content, and `LS-04a` **flips one of
my own `§Q`-3 rows**. `CENSUS-BRIEF.md`.

```
surveyor:         linux-sources                                   prefix: LS-
corpus:           ~/github/linux-sources @ 9526bde · .claude/settings.json (9 command entries)
                  · 7 hook files · 1 git hook · pyproject.toml 201L · NEXT.md 2513L / 85 sections
                  · warrants.bib 42 @misc · 13 gate slices
reader:           mtools/mdstruct/.venv/bin/mdstruct spans|grep · pycodemod · harness Read
                  · md5sum · a purpose-written settings.json counter (below)
reader-blind:     ⚑ the struct-tools hook REFUSED `wc`/`awk` over .py during this survey and
                  routed to pycodemod — so LINE COUNTS of the hook files, the exact figure §X
                  compares on, were not obtainable in §X's format. md5 is strictly stronger for
                  that purpose and is given instead. ⚑ THAT IS ITSELF A DATUM: the guard
                  prevented the measurement the run file asked for, in the form it asked for.
unread:           BUILD.bazel (456KB, generated, gated by a stale_gate_build slice) · .bazelrc
                  (17KB) · 12 of 13 ⊗ entries · warrants.bib bodies past the first 70 lines
disclosure:       I am this repo's own delegate surveying itself. NEXT.md and CLAUDE.md are this
                  repo's claims ABOUT itself — citations of the repo, never independent
                  verification. ⚑ I also dispatched the deps-build census that closed today and
                  wrote several of its rulings; where a finding below originated there I say so.
window:           ALL, per §W. Antecedent probe run per rule where an origin is recorded.
not-searched:     peer legs under findings/constitution/ (embargoed) · other repos
```

**Provenance classes** per brief §7 — `citation` (this repo's bytes) · `machine` (a command run
live) · `testimony` (second-hand) · `inference` (mine).

---

## LS-00 ⚑⚑ TWO CORRECTIONS TO `§X`, BOTH ABOUT THIS REPO, BOTH MEASURED

`§X` supplies context no leg can see from inside. **Two of its statements about `linux-sources` are
false**, and the run file's own instruction — *"a hook's NAME is not its BEHAVIOUR"* — is the reason
to say so rather than let a leg confirm them by silence.

| `§X` states | measured here | `machine` |
|---|---|---|
| *"linux-sources holds **zero** hook files and runs six hooks"* | ⚑ **SEVEN hook files** — 4 symlinks + **3 real local files** | `find linux_sources -maxdepth 1 -name 'hook_*.py' -printf '%y %f -> %l\n'` |
| *"linux-sources **18**"* command entries | ⚑ **9 total, of which 6 PreToolUse** | a purpose-written counter, below |

**The count is re-runnable, not read once** — a leg disputing a run-file figure owes a program a peer
can execute:

    PostToolUse            1
    PreToolUse             6
    Stop                   1
    UserPromptSubmit       1
    TOTAL                  9

*(Written to the house bar; `json.loads` returns `Any` and `disallow_any_expr` is on, so the parse is
narrowed at one boundary rather than silenced. Four refusals from the pycheck hook before it passed
— see `LS-14`.)*

⚑ **The zero-files claim is the one load-bearing for `§X`'s symlink-vs-copy thesis**, and this repo is
simultaneously its **best supporting case** and a **counterexample**. Both halves are in `LS-01`.

> ⚑⚑ **CORROBORATED BY THE DISPATCHER INDEPENDENTLY, AT `§V` REV 5** — *"`§X`'s HOOK COUNTS WERE ALL
> EXACTLY DOUBLED."* I measured 9 against a stated 18 from inside my own repo and reported it as one
> leg's correction; the dispatcher found the same defect **across every row of the table**, which is
> the stronger claim and not one I could have reached.
>
> ⚑ **Two witnesses that could have disagreed.** My count came from parsing `settings.json`; theirs
> from re-measuring the whole `§X` table. **Had the doubling been mine — a miscount, a different
> revision — the two would have diverged.** *This is the only reason my figure is worth more than an
> assertion.*

---

## LS-01 — §Q1: WHAT I RUN, AND HOW THE CODE GOT HERE

### The hook census with content hashes (`machine`, `md5sum`)

| file | mechanism | md5 | vs `§X`'s table |
|---|---|---|---|
| `hook_structural_query.py` | **SYMLINK** → `../../substrate/scripts/` | `b094c4d9…` | **= substrate = summit** |
| `hook_no_chaining.py` | **SYMLINK** → same | `d9e8bcc4…` | **= substrate = summit** |
| `hook_shellcheck.py` | **SYMLINK** → same | `691b0a1c…` | **= substrate = summit** |
| `hook_cmdparse.py` | **SYMLINK** → same | `27cddbcb…` | = substrate; ⚑ **≠ summit's `8096c871`** |
| `hook_gate_running.py` | **HELD AS CODE** | `e1fd0d91…` | — |
| `hook_pycheck.py` | **HELD AS CODE** | `81b52a5a…` | — |
| `hook_format.py` | **HELD AS CODE** (PostToolUse) | `bcf15c3a…` | — |

⚑⚑ **THE FOUR SYMLINKS SHOW ZERO DRIFT BY CONSTRUCTION** — there is one body and it is substrate's.
`§X` measures copies diverging into three bodies of 492/418/364 lines; **the symlinked half of its own
table is the control, and it holds.**

⚑ **A FOURTH DISTRIBUTION STATE `§X` HAS NO COLUMN FOR: adopted and inert.** `hook_cmdparse.py` is
symlinked into the package and **absent from `settings.json`** — present, current, wired to nothing.
*A census of mechanisms misses it because the mechanism is fine.*

### ⚑⚑⚑ LS-01a — THE DISCRIMINATOR IS NOT THE MECHANISM, IT IS **WHO OWNS THE DEFECT**

Each held-as-code hook states its own reason (`citation`, `.claude/settings.json` `_comment`):

> *"held HERE as a real file rather than symlinked from substrate, because **the defect it guards is
> this repo's**"*

> *"the EDIT-SIDE half of the ◆F gate, held as a REAL LOCAL FILE (not symlinked) because **the BAR is
> this repo's**"*

**So the rule this repo actually runs is:** *symlink when the defect is shared; hold when the defect
is local.* ⚑ **That is a predicate about OWNERSHIP, and `§X`'s copy/symlink/write trichotomy is a
taxonomy of MECHANISMS.** A constitution that mandates a mechanism legislates the wrong variable —
this repo would be non-compliant while being right.

### LS-01b — arming is BOTH, and the reason is a measurement

`citation`, every command string, e.g. `STRUCT_HOOK_BLOCK=1 python3 "$CLAUDE_PROJECT_DIR/…"`, with:

> *"The env block below is correct and **INSUFFICIENT BY ITSELF**: a session already running when
> this file changes never picks it up, so the hooks keep exiting 0 — detecting every violation and
> reporting none. That is the worst pairing, a guard that reads as armed in review and is off in
> fact (**measured in el-openglo, reported as armed for several commits**)."*

⚑ `hook_format.py` has **no arming variable at all**, deliberately: it never blocks, emits nothing on
the result channel, and fails open if ruff is absent.

### LS-01c — the guard is armed IN THIS SESSION, proven by it firing on me three times

`machine`, unprompted, during this survey: `no_chaining` denied a `;` and a `|`; `structural_query`
denied `wc` over `.py` and named its owner. ⚑ **Reading `settings.json` cannot establish this** —
that is `LS-05`'s article demonstrated rather than asserted.

`linux_sources/check.py --only routes` → **`34 of 34 probe(s) passed`**, every hook carrying a T-arm
and an F-arm. Git hook: one, `.githooks/pre-commit`, `core.hooksPath` **armed** (`machine`), running
`bazel test //:gate --config=remote`.

### LS-01d — the linters, and the bar's provenance

`select = ["ALL"]`, mypy `strict = true` **plus six flags beyond strict** including
`disallow_any_expr`. ⚑ **The bar is not this repo's invention** (`citation`): *"THE HOUSE STANDARD IS
earley's, ADOPTED EXACTLY … copied here rather than an ad-hoc subset."*

`[[tool.mypy.overrides]]` is **forbidden by house rule** — untyped deps get hand-written stubs
instead, because *"a hand-written partial stub ADDS types rather than silencing their absence."*

⚑ **ruff excludes exactly the four symlinks, by OWNERSHIP not standard:** *"Linting them would report
findings about code this repo does not own and cannot fix without forking, the one thing the symlink
pattern exists to prevent."*

### LS-01e ⚑⚑ THE SYMLINK'S REAL FAILURE MODE, AND IT IS NOT `git clone`

`§X` says a symlink breaks on clone. **Measured here, it broke a different way** (`citation`):

> *"substrate moved `arg_after` behind `substrate.ratchet_flags`, `_ROOT` through the symlink
> resolved to THIS repo (not substrate), the import raised ModuleNotFoundError, and **the hook
> exited 0 = ALLOW — a gate that had silently stopped gating**."*

⚑ **A TRANSITIVE IMPORT THE ADOPTING REPO CANNOT SEE, FAILING OPEN.** The repair was installing
`substrate-tooling` into the venv — **which fixed it without un-symlinking anything** (routes 6-of-N
red → 34/34). *Non-editable on purpose: an editable install is invisible to mypy by construction.*

**So the mechanism has three failure modes, not one:** clone-breakage, drift (copies), and
⚑ **a shared body growing an import its adopters do not have.** Only the third fails silently open.

---

## LS-02 — §Q2: WHAT I BELIEVE BINDS EVERYONE

Each stated as a checkable claim, with the measurement that settled it.

**LS-02a. Advisory mode is SILENT to the agent. Two states exist: armed, or absent.**
`citation`: *"unarmed, a hook prints its advisory and exits 0 with no `permissionDecision`, which the
harness reads as 'allow, nothing to report' — the text reaches nobody."*
**Check:** run an unarmed hook; assert no `permissionDecision` on stdout.

**LS-02b. Arming must be inline on the command string, not env-only.** Cost: several commits in
el-openglo gated by a guard that read as armed and was off. **Check:** change `settings.json` in a
live session; assert the hook still fires.

**LS-02c. ⚑ A GUARD IS VERIFIED BY MAKING IT FIRE, AND THE F-ARM IS NOT OPTIONAL.**
`citation`: *"VERIFY BY MAKING THEM FIRE, NEVER BY READING THIS FILE … requires deny when armed AND
requires NOT-deny when unarmed (the F-arm), **so it cannot certify a hook that denies everything**."*
**Checked:** 34/34 (`machine`).

**LS-02d. ⚑⚑ ONE F-ARM PER PROPOSITION — one arm is insufficient BY CONSTRUCTION.**
`citation`: *"A single arm deleted the copyright line, got a real refusal, and made this delegate
**MORE confident** the SPDX line was covered — evidence for a proposition nobody had tested. A
CONFIGURED-BUT-INERT gate is the easy case; **AN ACTIVE GATE AIMED AT THE WRONG PREDICATE** is the
hard one, because it produces findings, passes review, and its greens are indistinguishable from
correct ones."*
⚑ **Converged with `mtools-05`, whose config was the mirror image** — an SPDX regex gating SPDX and
leaving copyright ungated. **Two repos, one rule, complementary blind spots, each running the arm its
own config would pass.**
⚑⚑ **And its own limit, which outranks it:** *"WHICH PROPOSITIONS YOU ENUMERATE IS STILL A JUDGEMENT
… Three grids passed over this rule and none carried the separator arms, because every author was
reading the regex as its WRITER. A consumer enumerated differently and found it."*

**LS-02e. ⚑ A GREEN THAT CANNOT SAY WHAT IT WAS MEASURED OVER IS NOT A PASS.** Three instances, and
this is the article this repo paid most for. The sharpest (`citation`, `◆63`): a hook's F-arm was
green **from inside a running gate** — direct child → ALLOW, grandchild → DENY.
> *"**EVERY ARM WAS GREEN AND THE FULL GATE WAS 7/7 WHILE THE DEFECT WAS PRESENT** … the only thing
> that surfaced it was refusing to bank a pass I could not explain."*

**LS-02f. Verify a config's EFFECT, never its INTENT.** `citation`: *"Verify with `ruff check
--show-settings`, never by reading this line: `--show-settings` reads the RESOLVED value, and reading
the line you just wrote shows INTENT, not EFFECT."* Cause: TOML basic-vs-literal string quoting made
a regex silently unmatchable.

**LS-02g. A retracted METHOD outranks a retracted RESULT, and is indexed BY SHAPE not by domain.**
`citation`, crediting `cassian-observability-08`: *"a dead RESULT is scoped to its claim, but **a dead
METHOD is a VERB** — it applies wherever the shape recurs, so it travels exactly as far as the shape
does, silently, into lanes that never saw the original frame."*

**LS-02h. Three-state exits, not two.** `citation`, `paper.toml`: *"Exit 2 is UNAVAILABLE (apt has
not installed the subject), which is **NOT a failed claim**."* Absence is UNAVAILABLE, never
"does not exist".

**LS-02i. ⚑ A claim in a MESSAGE carries no provenance field, so confidence reads uniform.**
`citation`, `▣32`: *"A mode stamps its corpus version on every answer; a letter stamps nothing."*
⚑⚑ **Filed as DEBT, not as solved — this article has no verifier anywhere in the ecosystem**, and I
state it as a gap rather than a rule I keep.

---

## LS-03 ⚑⚑ §Q2 CONTINUED — WHERE I THINK `§X` IS TOO STRONG, AND I HOLD BOTH SIDES

`§X` offers as settled: *"A gate must REFUSE when its tool is absent, never skip."*

**This repo holds both directions and the discriminator is measured** (`citation`):

| guard | behaviour | stated reason |
|---|---|---|
| `.githooks/pre-commit`, bazel absent | ⚑ **REFUSES** | *"we REFUSE rather than commit unchecked … a silent skip here would be the guard's-silence-reads-as-approval defect"* |
| `hook_gate_running`, `/proc` unreadable | ⚑ **FAILS OPEN** | *"the cost prevented is a WASTED GATE RUN, not corruption, and a guard that refuses everything whenever it cannot tell is worse than the problem"* |
| `hook_shellcheck`, shellcheck absent | ⚑ **FAILS OPEN AND SAYS SO ONCE** | *"so an inert gate cannot masquerade as a passing one"* |

⚑⚑ **So the article is not "always refuse". It is: THE CHOICE IS INDEXED ON WHAT THE GUARD PREVENTS,
AND FAIL-OPEN IS PERMITTED ONLY WITH AN ANNOUNCEMENT.** Corruption → refuse. Wasted work → fail open,
loudly, once.

*This is offered as a correction to a candidate article, not to a peer — `§X` presents it as a
dispatcher's candidate and explicitly not as a position.*

---

## LS-04 — §Q3: WHAT BINDS ONLY ME

⚑ **The run file is right that this question gets skipped, so it gets the same weight as `§Q`-2.**

| rule | why it is LOCAL |
|---|---|
| **The corpus/ledger distinction** — a 206MB derived image, untracked, never committed | ⚑ **Noise in any repo that owns its subject.** Only a delegate reasoning *about* an artifact it does not own needs it. |
| **VERSION resolves to what is SERVING, not what apt holds** | Binding only where answers are version-scoped facts about someone else's shipped bytes. *(Measured: answered `-29.29` for hours after apt installed `-30.30`, because VERSION was a literal.)* |
| ⚑ **STALE ≠ WRONG** — *"an answer given under -29 remains true of -29; it has become un-current"* | **Wrong elsewhere:** in most repos a stale answer *is* a wrong one. |
| **KEEP REVISIONS** — apt overwrites its own tarball, so this repo's image was the only surviving copy of a version | Meaningless where the subject is in git. |
| **The `.pc/` shadow-corpus exclusion** — a quilt package contains a prior version of itself | Only bites a repo reading Debian source packages. |
| **The bazel gate** | ⚑ **Scale-conditional, not constitutional.** Justified by measurement: the serial loop *"pushed past 2 minutes and the hook timed out."* **A repo whose gate runs in 5s would pay bazel's cost for nothing.** |
| **`S101` scoped to two directories** | *"asserts are stripped under `python -O` … the instrument selftests' F-arms depend on assert."* |
| **42 warrants over an immutable corpus** | Presupposes an immutable subject: *"that immutability is what makes them checkable rather than testimony."* |

⚑ **The routed-tool regime splits.** The *no-chaining* half generalizes; the
*route-every-`.md`-and-`.py`-question* half is justified locally (*"a naive `tar xjf | grep` costs
~2min of CPU"*) — **and it caused a fleet-wide defect.** See `LS-06`.

### ⚑⚑⚑ LS-04a — REV 11's TEST FLIPS THAT LAST ROW, AND MY OWN LEG HELD THE EVIDENCE

**Written against rev 11**, whose test is: ***ask who bears the cost of the violation, not who
benefits from the rule.***

**I filed the routing regime as local by reasoning from BENEFIT** — this repo avoids ~2min of CPU on
a sealed 195MB tarball, no other repo has one, therefore local. ⚑ **That is exactly the move rev 11
names**, and `substrate` made it about its own `sys.path` insert.

**Apply the test instead**, and `LS-05` — two sections down, already written — is the answer:

| | |
|---|---|
| who **benefits** from routing `.md` to one owning tool | this repo |
| who **bore the cost** when that tool was defective | ⚑ **`summit`, whose `§Q`-8 answer `SM-13` was invisible in its own leg; and me, via a symbol collision** |

> *"A guard that routes every consumer to one instrument inherits that instrument's blind spot
> **FLEET-WIDE**, and the guard's correctness is what makes it invisible."* — `LS-05`, `citation`

⚑⚑ **So the routing half is BINDING, not local — and it is binding in the direction that constrains
the router.** Not *"every repo should route"*, but: **a repo that routes its consumers to a single
tool has taken on an obligation to that tool's defects, and owes a defect index at the routing
point.** `LS-05` already says the missing artifact is *"a defect index keyed by TOOL, queryable at
the point of routing"*; ⚑ **rev 11 is what makes that an obligation rather than a wish.**

⚑ **AND THE OTHER SEVEN ROWS SURVIVE THE TEST, which is why the flip is worth trusting.** Re-checked
one at a time: nobody outside this repo pays when the corpus/ledger line blurs, when a version stamp
goes stale, when `.pc/` shadows leak into a search, or when `S101` is unscoped — **the cost of every
violation lands here.** A test that reclassified everything would be a test of nothing.

⚑⚑ **The test's own provenance is what makes it credible, and rev 11 says so:** its author *"derived
it from having applied it wrongly to its own list first."* **Mine is the second instance, found by
applying it to a list I had already filed** — which is the check rev 11 asks every leg to run.

---

## LS-05 — §Q4: WHERE I RE-DERIVED WHAT A PEER HAD SETTLED

⚑ **The best instance runs the other way, and it is the run file's own subject.**

**`▣33` — `mdstruct --headers` drops sections.** Reported by `substrate-b0`; **reproduced here within
the hour**. Cost, concretely (`citation`):

> *"**IT COST ME A SYMBOL COLLISION THE SAME HOUR.** I read this ledger with `--headers`, saw the
> highest ◆ as 62, and filed `◆63` into a number already held by a closed item … The file's own
> contract — 'a completed item keeps its symbol so an invocation never silently retargets' — is
> enforced by a census, and **a census taken with a lossy reader is the retarget it was written to
> prevent**."*

⚑⚑ **AND THE ROUTING MADE IT SYSTEMIC** (`citation`):

> *"`hook_structural_query` refuses grep/sed/cat on any `.md` and names mdstruct as 'the tool that
> owns it.' So **the gate COMPELS the defective reader and forbids the textual fallback that would
> have exposed the gap.** A guard that routes every consumer to one instrument inherits that
> instrument's blind spot FLEET-WIDE, and the guard's correctness is what makes it invisible: the
> refusal is right, the destination is not."*

⚑⚑⚑ **AND THE FIX EXISTED, WAS BELIEVED, AND COULD NOT BE INSTALLED.** substrate's `md_hkey.py` is
tested 18/18 and **unwired**, behind an all-or-nothing per-file gate refusing every edit to
`mdstruct`. **Two correct guards compose into a defect nobody can repair.**

> ⚑ **THIS IS A THIRD FAILURE MODE THE RUN FILE'S FRAMING HAS NO BUCKET FOR.** `§Q` distinguishes
> *distribution* (a fix does not travel) from *relitigation* (the question is re-opened). **Here the
> fix travelled, was believed, and was uninstallable.** Call it **arrival without a write path** —
> and note it is produced by two guards each behaving correctly.

**What would have had to exist:** a **defect index keyed by TOOL, queryable at the point of
routing**. `SKILL.md` names owners and carries no known-defect field. ⚑ **This is not a discovery
failure; it is a write-path failure**, and a constitution addressing only discovery would not touch
it.

**Second: `▣36`, `find -o` binding.** Re-derived while checking a `summit` claim — and ⚑ **it
happened inside the check of a finding about exactly this**: `SM-08` is *"a shared body's dependency
set grew and nothing announced it"*; I hit *"my query's population shrank and nothing announced it"*
while measuring it. **Both return well-formed output short by an amount nothing states.**

**Third: the CPY001 convergence, and it is a LIMIT on what a constitution can fix.** Two repos
reached complementary halves of one rule independently, **and neither could have found the other's
half** — each ran the arm its own config would pass. ⚑ **The prior ruling being findable would not
have helped: the blind spot was in the ENUMERATION, not the lookup.**

---

## LS-06 — §Q5: WHAT RE-OPENING A SETTLED RULE SHOULD COST

**This repo runs a four-part amendment path.** Stated as observed practice, not aspiration.

**1. A rule with a live verifier cannot be re-opened by argument, only by measurement.** 42 warrants,
each with `check = {corpus:…}` or `{gate:…}`, argument and measurement **fused** (`citation`): *"A
partition into 'shape-claim' plus 'evidence' keeps the magnitude and destroys the orientation."* And:
*"A claim with a live verifier cannot launder, because the check either runs or it does not."*
⚑ **Cost: change the predicate and the claim together, or the gate reds.**

**2. Retraction is RECORDED and INDEXED BY SHAPE, never a silent edit.** 13 retracted methods, placed
**before** the work items (`citation`): *"so they are found before someone reaches for them —
**recoverable-from-a-commit-log is not findable**."*
⚑⚑ **That sentence is what I would build the amendment article on.**

**3. Superseded framings are KEPT, with their symbols.** Measured: four `-original`/`-residue`
sections in `NEXT.md` (`machine`). ⚑ *"a completed item keeps its symbol so an invocation never
silently retargets."*

**4. ⚑ THE AMENDING PARTY DOES NOT RULE ON ITS OWN EXCEPTION.** From the deps-build census that
closed today: I wrote its `§D`.2 (*legs are not amended*), then made a post-filing append to my own
leg — and **offered it for refusal rather than granting myself the exception.** The apex accepted it,
narrowly, on grounds including that *the append's first measurement contradicted its own leg*, which
an amendment behind an accounting would not publish. `inference`: **a rule's author is the
worst-placed party to rule on their own exception**, and the repair is to hand the ruling to someone
holding no stake.

**The evidence bar I would require** (`inference`, from observed practice): a **measurement, not an
argument**; **an F-arm per proposition**, with the propositions enumerated by a **consumer** rather
than the author; **the old rule kept**, marked superseded; and ⚑ **a negative that names WHY it is
clean** — *"the next editor who adds `-printf` converts a safe construct into `▣36` with no other
change."*

---

## LS-07 ⚑ TWO STALE FIGURES IN MY OWN TREE, FOUND WHILE ANSWERING §Q1

Both `machine`, both in documents this repo treats as authoritative:

- ⚑ **`paper.toml` and `CLAUDE.md` invoke `linux_sources/check`** (no extension). `find` over the
  tree: **no such file.** Only `check.py` exists. `[checks.gate] cmd` names a binary that is not
  there.
- ⚑⚑ **`CLAUDE.md` says "24 claims"; `warrants.bib` holds 42** (`grep -c '^@misc'`).

**This matters to the census rather than to me.** ⚑ **A stale count in the constitution-like document
of a repo whose entire discipline is anti-staleness** is the relitigation failure in miniature: the
document that would settle a question for a reader is itself un-re-derived. *A constitution will have
this property the day after it is written unless its figures are generated.*

---

## LS-08 — Coverage, stated as inclusions (brief §3, §10)

```
A  .claude/settings.json, whole                                    ->  1 file, 200L, 9 entries
B  hook files, ls + md5sum                                          ->  7 (4 symlink, 3 code)
C  non-PreToolUse hook files, md5sum                                ->  2
D  .githooks/pre-commit, whole                                      ->  1 file, 79L
E  pyproject.toml, whole                                            ->  1 file, 201L
F  NEXT.md via mdstruct spans + Read on 7 spans                     ->  2513L, 85 sections
G  CLAUDE.md, whole                                                 ->  1 file
H  paper.toml whole + warrants.bib head/count                       ->  2 files, 42 warrants
I  gate slices executed live                                        ->  routes 34/34; 13 slices
J  hook denials observed against my own commands, unplanned         ->  3
K  purpose-written settings.json counter, run                       ->  1
                                                        TOTAL      ->  19 sources
NONE FOUND: no .pre-commit-config.yaml, no tox.ini, no setup.cfg.
```

⚑ **Reader-blind, and it is a finding rather than an apology:** the struct-tools hook **refused `wc`
and `awk` over `.py`** during this survey. `§X` compares hook bodies by **line count**; I could not
produce that figure in that form. md5 is strictly stronger for the comparison, and is given — but
**the guard prevented the measurement the run file asked for, in the format it asked for**, which is
`LS-04`'s local-cost row arriving as a concrete instance.

---

## LS-09 — Roster nomination (brief §0)

**Nothing to add to `§R`.** One flag, not a nomination: ⚑ **`gate-architecture/` is a second paperkit
project inside this repo** — 35 warrants, its own `paper.toml`, gating the build system's own
documentation. It is a sub-corpus with its own claim set and no roster seat. **Whether a sub-corpus
files is the apex's call**, and I take no position.

---

## LS-10 — Termination line (brief §12)

**No.** A reader of this leg alone could not reconstruct what was asked of the other legs. It answers
`§Q`'s five questions for one repo, corrects two `§X` figures about that repo, and offers one
correction to a candidate article on grounds this repo holds both sides of. ⚑ **Computing the span,
and deciding which of `LS-02`'s articles are binding versus local, is the apex's job.**
