# CENSUS: `constitution` — run file

**Brief:** `findings/CENSUS-BRIEF.md`. Read it first. This file overrides it where they conflict.

## §R Roster, prefixes, paths

| surveyor | prefix | file |
|---|---|---|
| `mtools` | `MT-` | `findings/constitution/mtools-constitution.md` |
| `substrate` | `SB-` | `findings/constitution/substrate-constitution.md` |
| `linux-sources` | `LS-` | `findings/constitution/linux-sources-constitution.md` |
| `cassian-observability` | `CO-` | `findings/constitution/cassian-observability-constitution.md` |
| `paperkit` | `PK-` | `findings/constitution/paperkit-constitution.md` |
| `summit` | `SM-` | `findings/constitution/summit-constitution.md` |
| `rosettapkg` | `RP-` | `findings/constitution/rosettapkg-constitution.md` |
| **apex** — named at the freeze, from a party whose leg is filed | `AX-` | `findings/constitution/constitution-apex.md` |

Conventions fixed here rather than negotiated: filename pattern as above; ID prefixes as above; all
files land in `findings/constitution/` in **mtools**; quote the byte, cite the file and line.

⚑ **`rosettapkg` is on this roster and has no `.claude/settings.json` at all** (measured from
mtools, 2026-09-06). It is a surveying party like any other, and its leg is expected. A party with
no hooks is not a party with nothing to report — it is the leg that can say what adopting the bar
from zero actually costs, which no already-conformant repo can measure.

## §Q The question

⚑ **Survey yourself.** Report what *you* run, what *you* settled, and what *you* think binds
everyone. Do not survey the others; `§R` tells you who else is reporting and that is all you need to
know about them. Do not read peer legs until the freeze.

The operator's framing, quoted verbatim because the paraphrase loses the load-bearing half:

> *"I am the operator of all of the repos. all of the repos are meant to be running hooks. and I
> don't like that I have to keep walking all of the repos through all the lessons and mitigations
> I've learned and implemented from and in all the other repos."*

> *"it's rework, relitigating and rejustifying what should be a regulatory standard, effectively."*

⚑⚑ **The second quote is the subject, and it is not the same problem as the first.** Distribution
failure means a fix does not TRAVEL. Relitigation means the QUESTION IS RE-OPENED — a session meets
a settled question with no record that it was settled, reasons from scratch, reaches a defensible
different answer, and now there are two. Packaging the code fixes the first and makes the second
arrive faster. **Report on both, and keep them distinct in your leg.**

So, five questions. Answer each with measurements from your own repo:

1. **What do you run today?** Every PreToolUse hook, every git hook, every linter and its config,
   armed or advisory, and how you got the code — copy, symlink, package, or written here. Quote
   version or content hash where you can, because a hook's NAME is not its BEHAVIOUR.
   ⚑ **Per `§V` rev 3:** for every hook you hold that differs from a peer's, say whether the
   difference is **HELD** (you declined the other body, for a reason you can state) or
   **UNEXAMINED** (you have not compared). A held digest and a stale copy are the same bytes and
   opposite facts, and only you can tell them apart.
   ⚑ **Per `§V` rev 4:** say how your hooks' dependencies RESOLVE, and whether that resolution is
   **DECLARED** (a manifest a resolver reads) or **AMBIENT** (it works because this tree happens to
   contain something). If you cannot declare it, say what refuses and what the refusal is right
   about — a package whose dependencies do not resolve is no better off than a copy.

2. **What have you settled that you believe binds everyone?** The rulings you would not want any
   repo re-deriving: what the rule is, what measurement settled it, and what it cost you to learn.
   ⚑ These are the candidate constitutional articles. State each as a claim that could be checked,
   not as advice.

3. **What have you settled that binds only YOU?** A rule that is correct here and would be wrong,
   or merely noise, elsewhere. ⚑ **This question is as important as 2 and is the one that gets
   skipped.** A constitution where everything is binding fails six repos on rules never meant for
   them, and the operator is then relitigating THAT.
   ⚑⚑ **Per `§V` rev 11, apply this test to every q3 answer before you file it: ask who bears the
   COST of the violation, not who benefits from the rule.** A rule you filed as local because it
   serves a need only you have may be BINDING because a peer pays when it is broken. `substrate`
   filed *no `sys.path` insert* as local — reasoning from its own 14 internal call sites — then
   found the insert sits in a file two peers consume and its cost landed on summit's board as a
   traceback. It moved. **If you have already filed, re-check your q3 list against this and revise;
   the freeze is not called.**

4. **Where did you re-derive something a peer had already settled?** Name it, and say what would
   have had to exist for you to have found the prior ruling instead. ⚑ This is the highest-value
   signal in the survey and the one nobody records: a re-derivation is a defect report about the
   shared object whether or not anyone fixes it.

5. **What should re-opening a settled rule COST?** A standard nobody can amend rots into the
   stale-authority defect this ecosystem has already measured. State the amendment path you would
   actually follow, and what evidence you think should be required.

⚑ **What the dispatcher does NOT know, stated so no leg mistakes silence for a position.** I do not
know what the constitution should contain. I have a candidate list of five settled questions
(below, `§X`) and no confidence it is the right five, no view on which are binding versus local,
and no proposal for the amendment path. *I don't know what I don't know; that is why I am asking
all of you.*

## §C The construction — two phases, and phase 1 is not the deliverable

**Phase 1 — the span.** Build `A`: what every leg holds, as a correspondence table with a **witness
per identification**. Two repos both running `hook_no_chaining` is NOT an identification — `§X`
reports four bodies of that file differing by content hash, one 14 lines longer. ⚑ But `§X` is
dispatcher-supplied (rev 2) and cannot distinguish a **held** digest from a stale one (rev 3), so
that observation motivates the rule rather than witnessing any row of `A`. State non-identifications
explicitly. `A` is publishable, verifiable, and **not the answer.**

**Phase 2 — the glue.** Glue the legs along the published `A`. It **grows**: every leg's
contribution is carried, including rules only one leg holds. No admission bar. If the output is
smaller than the largest leg, phase 2 did not run.

⚑ **Carry-uncheckable-testimony.** A rule one leg holds that you cannot verify is carried, tagged
with its witness and its leg, and **not adjudicated**. Unverifiable ≠ wrong. Where two legs disagree
about the same rule — and they will, on fail-open and on advisory tiers at minimum — both stand in
the divergence register with their measurements. **An identification with no witness is over-gluing;
a missed one is duplication. Both are recorded, neither is guessed.**

⚑⚑ **A ratified constitution is NOT the output of this survey.** The output is the span plus the
full remainder. Ratification is the operator's, and a survey that hands over a document already
adjudicated has spent an authority it does not hold.

## §W Window, and why

**All of it.** Every rule you currently hold, regardless of when you learned it.

**Justification:** a window here would be a bound on WHEN a lesson was learned, and the subject is
which lessons are still binding. A rule settled in August that six repos still violate is exactly
what this survey is for; excluding it because it predates some bound would exclude the survey's own
best evidence. Run the antecedent probe from brief §6 on each rule's origin regardless — a rule
whose origin you cannot name is a finding.

## §X Context you would not otherwise have

⚑⚑ **DISPATCHER-SUPPLIED AND UNVERIFIED — see `§V` rev 2.** Everything in this section was measured
by **mtools alone**, at one timestamp, with one instrument. It is context, not a census finding.
Cite it if it is useful and **say that you did not verify it**; an apex row resting on it needs a
second party's measurement or it belongs in the divergence register. ⚑ And per rev 3: a hash that
differs from a peer's may be a **held digest with a recorded reason** rather than drift — the table
below cannot tell those apart, and only the holder can.

⚑⚑ **OPERATIONAL FACT EVERY WRITER OF THIS TREE NEEDS — in the run file per `§V` rev 22, because
until now it lived only in messages to some parties and not others.**

**mtools' pre-commit gate takes ~130s cold and ~60s warm.** So `.git/index.lock` is routinely held
for two minutes by a commit that is working correctly, and with seven parties filing it is acquired
and released continuously.

⚑ **Do not remove a lock you did not create.** `git`'s own message recommends removal and is right
for **one** writer; with N writers there are three states, not two — live, crashed, and *between
acquisitions* — and no single sample distinguishes the last two. `pgrep -a git` returning nothing is
a point sample of an interval property. **Size-stable is not evidence:** a lock measured at 16123
bytes three minutes apart was two *different* live commits, because the size is a fact about the
index. **mtime advancing is the discriminator that worked.**

⚑ If a lock blocks you, wait — and say so if it keeps blocking you, because that is a scheduling
problem the dispatcher can yield on, not a lock problem.

Measured from mtools, 2026-09-06. Provided because no leg can see it from inside:

**Hook entries, by repo** — ⚑ **CORRECTED, see `§V` rev 5.** The original figures here were every
one exactly DOUBLE (`grep -c '"command"'` matches `"type": "command"` as well as the `"command":`
line) and were all labelled `PreToolUse` when several are not. Parsed structurally from
`.claude/settings.json`:

    linux-sources           9    PreToolUse/Bash=3  PreToolUse/Edit|Write|NotebookEdit=3
                                 PostToolUse=1  Stop=1  UserPromptSubmit=1
    cassian-observability   9    PreToolUse/Bash=4  PreToolUse/Edit|Write|NotebookEdit=2
                                 PostToolUse=1  Stop=1  UserPromptSubmit=1
    paperkit                8    PreToolUse/Bash=3  PreToolUse/Edit|Write|NotebookEdit=3  Stop=2
    summit                  6    PreToolUse/Bash=3  PreToolUse/Edit|Write|NotebookEdit=3
    substrate               5    PreToolUse/Bash=3  PreToolUse/Edit|Write|NotebookEdit=2
    mtools                  1    PreToolUse/Bash=1
    rosettapkg              0    NO .claude/settings.json

⚑ An entry is one element of a matcher group's `hooks` array. `hook_shellcheck` is wired twice in
substrate (two matchers), so **5 entries is 4 distinct programs** — entries and programs are
different counts and this table reports entries.

All armed via `*_HOOK_BLOCK=1`; most also arm inline in the command string.

**⚑⚑ Content drift, by md5 of the first 8 chars — the finding that reframes this survey:**

    hook_no_chaining      substrate d9e8bcc4 668L | paperkit SYMLINK | summit d9e8bcc4 | cassian d4ebd0c8 682L
    hook_structural_query substrate b094c4d9 760L | paperkit SYMLINK | summit b094c4d9 | cassian 7442f527 605L
    hook_shellcheck       substrate 691b0a1c 861L | paperkit SYMLINK | summit 691b0a1c | cassian c6a35093 627L
    hook_cmdparse         substrate 27cddbcb 492L | paperkit SYMLINK | summit 8096c871 364L | cassian 83a15017 418L
    hook_pycheck          substrate 391d9eda 570L | paperkit SYMLINK | summit 391d9eda      | cassian ABSENT, linux-sources ABSENT

⚑ **The `hook_pycheck` row was MISSING from this table until `§V` rev 6**, and it is the one hook
where the three holders are byte-identical. A hand-written population omitted the counter-example to
its own thesis. If you hold a hook this table does not list, **that absence is a finding.**

Of 27 hook files across five repos, **5 are symlinks (all paperkit's, into `../../substrate/scripts/`)
and 22 are copies.** linux-sources holds **zero** hook files and runs six hooks. So three distribution
mechanisms coexist and each fails differently: a symlink breaks on `git clone`, a copy drifts, and
`hook_cmdparse` exists in **three** distinct bodies of 492 / 418 / 364 lines.

⚑ **Same name, different behaviour, and nothing reports it.** This is the measured mechanism behind
the operator's complaint, and it is why question 1 asks for hashes rather than names.

**Five questions this ecosystem has already settled at least once**, offered as candidates for
question 2 and **not** as a position — the dispatcher does not know whether these are the right five,
nor which are binding:

- **Pipes discard every exit status but the last.** `cmd | tail` reports tail's rc. Settled in mtools
  three times in one day, most expensively by reporting a peer's tool as exiting 0 on a traceback
  when it exits 1. substrate's `hook_no_chaining` prevents the construct outright.
- **`|&` is ONE shlex token** under `punctuation_chars=True` and does not reduce to `|` + `&`. A
  stale comment claiming otherwise survived a ruling, an `--explain` that agreed for the wrong
  reason, and a green selftest. Only running the tokenizer found it.
- **Advisory mode is silent to the agent** (linux-sources, measured): an unarmed hook exits 0 with no
  `permissionDecision` and the harness reads "allow, nothing to report". Two states only: armed, or
  absent.
- **A gate must REFUSE when its tool is absent**, never skip. Settled in both directions one repo
  apart: substrate's `check_scratch_runtime.py` printed SKIPPED and exited 0; linux-sources'
  pre-commit refuses when bazel is missing.
- **Arming must be inline, not env-only.** A session already running when `settings.json` changes
  never picks up the env, so hooks keep exiting 0 — detecting every violation and reporting none.
  Reached independently by two repos.

**And a sixth, open rather than settled**, because a leg may have measured it: `shellcheck -s dash`
over mtools' 15 tracked shell files yields **18 findings in 4 files; 11 of 15 are already
dash-clean**. The operator's position is that a hook banning pipes removes the need for bash's
`PIPESTATUS`, which is the only POSIX-inexpressible construct among them. Whether dash is the right
target — and whether any consumer actually runs these under `/bin/sh` — is unmeasured here.

## §V Revision log — ⚑ corrections land here, not in messages

| rev | when | what changed | affects |
|---|---|---|---|
| 1 | 2026-09-06 | initial | — |
| 2 | 2026-09-06 | ⚑ **`§X` is DISPATCHER-SUPPLIED AND UNVERIFIED.** Both tables in `§X` were measured by mtools alone, at one timestamp, with one instrument, and were published without that label. An apex row resting on `§X` inherits one party's instrument **with no witness**, which `§C` refuses. Any such row needs a second party's measurement or it goes in the divergence register. Raised by `summit`, who cited `§X` as context and recorded that it had not verified it — the correct move, and every leg should do the same. | `§X`, and every leg citing it |
| 3 | 2026-09-06 | ⚑⚑ **A HELD DIGEST AND A STALE COPY ARE THE SAME BYTES AND OPPOSITE FACTS.** `§X`'s hash table said "three distinct bodies" of `hook_cmdparse` and implied rot. `summit` reports `8096c871`/364L is a **deliberate hold with a recorded reason**: substrate's newer body imports `substrate.ratchet_flags` unguarded at module scope, which moves summit's board to a traceback, and the same body carries a real security fix (`env -C`, `timeout -s KILL`, `sudo -u` each bypassed every hook). **Only the holder knows which a digest is.** Question 1 now asks: for every hook you hold that differs from a peer's, say whether the difference is HELD or UNEXAMINED. | `§X`, `§Q` q1 |
| 4 | 2026-09-06 | ⚑ **A FOURTH DISTRIBUTION AXIS: whether the shared code's DEPENDENCIES RESOLVE.** `§X` enumerated symlink / copy / package — all three about where the BODY comes from. `summit` measured a fourth, orthogonal to all of them: linux-sources does not reproduce summit's import crash, same bodies and same unguarded import, **solely because its venv holds `substrate-tooling`**. Installing it closes every one at 94 transitive packages, and summit **cannot declare it** because `uv sync` refuses the manifest on a Python-floor conflict and the resolver is right. ⚑ A package with an unresolvable dependency is no better off than a copy. Independently corroborated in mtools the same day: substrate's `scratch/mdstruct.py` declares nothing and needs one PyPI package plus four repo-local siblings, so it runs only in the tree that happens to hold them. **Question 1 now asks how your hooks' dependencies resolve, and whether that resolution is DECLARED or ambient.** | `§Q` q1, `§X` |
| 5 | 2026-09-06 | ⚑⚑ **`§X`'s HOOK COUNTS WERE ALL EXACTLY DOUBLE, AND THE LABEL WAS WRONG TOO.** I counted with `grep -c '"command"'`, which matches BOTH `"type": "command"` and the `"command":` line of every entry. Reproduced: substrate greps 10 and holds **5**. Corrected counts, parsed structurally — substrate 5, linux-sources 9, cassian 9, paperkit 8, summit 6, mtools 1, rosettapkg none. ⚑ And they are not all `PreToolUse`: linux-sources and cassian each wire `PostToolUse`, `Stop` and `UserPromptSubmit` too, which `§X` labelled as PreToolUse throughout. **Any leg that anchored on `§X`'s counts should re-read them.** Caught by `substrate`, which could not reproduce its own row under any reading — the disagreement that only the subject can raise. | `§X`, every leg citing it |
| 6 | 2026-09-06 | ⚑ **`§X`'s DRIFT TABLE HAS A COVERAGE HOLE, AND A DRIFT CENSUS CANNOT REPORT DRIFT IN A HOOK IT DOES NOT COVER.** The table listed four hooks; substrate wires five. `hook_pycheck.py` was absent from it entirely. Measured now: substrate `391d9eda`/570L, paperkit SYMLINK to it, summit `391d9eda` — three parties byte-identical — and **absent from linux-sources and cassian**. So the one hook where the copies agree was the one hook not shown. ⚑ The population was hand-written, which is the seventh hand-written population to rot in this ecosystem's own instruments. Raised by `substrate` as the only party positioned to notice. **If you hold a hook `§X` does not list, that absence is a finding — report it.** | `§X`, `§Q` q1 |
| 7 | 2026-09-06 | ⚑⚑ **REV 3's WORKED EXAMPLE WAS DISPUTED AND IS NOW SETTLED; THE RULE KEEPS ITS WITNESS.** `substrate` could not reproduce the import rev 3 rests on — `pycodemod --imports` reported `STDLIB=9, 0 undeclared` on the exact hash `27cddbcb`, and `--literal ratchet_flags` found 4 sites all classified `doc` — and filed it as `SB-13` for the divergence register rather than calling rev 3 wrong. Measured by mtools with both trees open: **`27cddbcb` line 437 IS `from substrate.ratchet_flags import arg_after`, at module scope.** It sits 400 lines below the import block, immediately after a `sys.path.insert` at 434–435. ⚑ So substrate's scan was true of the *import block* and false of the *module's imports* — a predicate asserting a property of the header where the claim is about what the file imports, which is `spelling-census`'s own shape and the **second live instance in this census** after rev 5's `"command"` count. ⚑⚑ And the `sys.path` prelude is why it works for substrate and crashes for a borrower: it makes the import resolvable **from substrate's root only**, so summit's report is true in summit's tree and substrate's is true in substrate's. Neither party could resolve it alone; both reports were locally sound. **Rev 3 stands. An article entering on one unverified example was correctly challenged, and the challenge is what produced the witness.** | `§V` rev 3, divergence register |
| 8 | 2026-09-06 | ⚑⚑ **THE KICKOFF ASSERTED `§R` WITHOUT POLLING IT, WHICH IS A RULE THIS ECOSYSTEM LANDED LAST RUN AND I SKIPPED IN THE FIRST DISPATCH OF THIS ONE.** The dispatch said *"The roster is in `§R` and includes you"* — a factual claim about a file, sent six times, unmeasured. It happened to be true because I had written `§R` minutes earlier, and *"I wrote it correctly a minute ago"* is not a poll; the dispatcher's memory of what it wrote is the least reliable witness available. Polled after the fact: 8 rows, 7 surveyors plus apex, every dispatched party present with the prefix and path the kickoff implied — **claim holds, discipline did not.** Raised by `cassian-observability`, which verified its own row rather than trusting the sentence. ⚑ Recorded here rather than privately because a rule settled last run and skipped this run is the exact relitigation this census exists to study, committed by its own dispatcher one turn after convening it. | dispatch procedure |
| 9 | 2026-09-06 | ⚑ **`§S`'s STATE SPACE IS TOO SMALL, FOR THE SECOND CENSUS RUNNING, AND BOTH TIMES THE MISSING STATE WAS "DONE, BLOCKED ON THE DISPATCHER."** `cassian-observability`'s leg is written, dated, verified against `mdstruct spans` and unfiled — for a **permission** reason, not a work reason — and `§S` could express neither *filed* nor *not yet filed* about it honestly. Last run needed `STAGED`; this run needs `DRAFTED — awaiting write authorization`. Both added. ⚑ A status vocabulary that cannot say *waiting on the coordinator* systematically under-reports the coordinator as a bottleneck, which is a defect in the accounting rather than in any leg — and `§G` exists to stop exactly this class, where a row cannot distinguish *they had nothing* from *they were never reached* from *they are waiting on me*. | `§S`, `§G` |
| 10 | 2026-09-06 | ⚑⚑ **A REGISTERED INSTRUMENT FOR A DEFECT CLASS CAUGHT NEITHER OF THAT CLASS'S TWO INSTANCES THIS CENSUS PRODUCED IN ONE DAY — AND NOT BECAUSE THE INSTRUMENT IS WEAK.** `summit` owns `spelling-census` (*"witnesses whose predicate asserts a SPELLING where the claim needs a BEHAVIOUR"*). Rev 5's doubled hook count and rev 7's missed line-437 import are both that class. `substrate` checked whether its instrument would have caught either and answered **NO for both, for different reasons**: rev 5 was the wrong artifact kind (a grep over another repo's JSON, not a witness), rev 7 was the right kind **in the wrong tree**. ⚑ **A per-repo instrument is scoped to its repo while the defect is ecosystem-wide** — the same gap `§X` has at the hook layer, arriving one level up. ⚑⚑ This is the strongest argument in the survey so far that the constitution needs *cross-repo* conformance checking rather than better per-repo instruments, and it arrived as a **negative** answer from the party who could have claimed coverage. | `§Q` q2, q4 |
| 11 | 2026-09-06 | ⚑⚑ **A TEST FOR THE Q2/Q3 BOUNDARY: ASK WHO BEARS THE COST OF THE VIOLATION, NOT WHO BENEFITS FROM THE RULE.** `substrate` had filed *no `sys.path` insert* as binding-only-on-itself, reasoning from substrate's own motive (14 internal call sites). Rev 7's finding made it re-read: the insert lives in a file **two peers consume**, and its cost landed on **summit's board** as a traceback. So the rule splits — no insert in internal tooling is LOCAL; no insert in an artifact another repo consumes is **BINDING** — and substrate moved it. ⚑ The test is offered as an answer to `§Q` q5's amendment question and is **derived from having applied it wrongly to its own list first**, which is the only reason its author trusts it. ⚑ Every leg should re-check its own q3 answers against it: a rule filed as local because *you* benefit from it locally may be binding because a peer pays for its violation. | `§Q` q2, q3, q5 |
| 12 | 2026-09-06 | ⚑⚑ **EVERY LEG IN THIS CENSUS WILL TRIP mtools' FIGURE-FRESHNESS GATE, AND THE FLAG MEANS *UN-CROSS-CHECKABLE*, NOT *STALE*.** mtools' pre-commit gate reports `carries measurements and cites NO rule, so none can be cross-checked` against `summit`'s leg and `rosettapkg`'s, and will against the rest. ⚑ **A census leg is a measurement-carrying document with no rule to cross-check against, by construction** — its figures ARE its substance, and `§D` forbids amending them after accounting anyway. The gate is right that the claims can go stale and right that nothing in the file can tell. What is missing is a way for a leg to declare *"these figures were measured at filing time and are not maintained"*, which several legs say in prose and no gate can read. **The apex must read this flag on all seven legs as expected and non-diagnostic.** Raised by `summit`, which declined to silence it in its own leg. | apex, every leg |
| 13 | 2026-09-06 | ⚑⚑ **A DANGLING SUCCESSOR IS THE SILENT DIRECTION, AND BOTH `substrate` AND `mtools` SHIP IT IN HOOKS THEY EXPORT.** `substrate`'s `SB-A10` requires that a successor named in a refusal be a package coordinate or harness-provided tool, **never a filesystem path into the producing repo**. Measured after mtools asked whether its own `see .claude/skills/struct-tools/SKILL.md` violates it: **substrate ships two** (`hook_no_chaining:407`, `hook_structural_query:343`, both `arg` role — text a refused party receives — and both among the five paperkit symlinks), and **mtools ships the same string in `no_chaining.py:127` and twice in `structural_query.py`**, in the very module packaged for peers. The target is a producing-repo directory a consumer does not have. ⚑ **Worse than an unresolvable import, which fails loudly at import time.** A dangling successor produces a gate that refuses *correctly*, names a successor, errors nothing, and points the reader at a repo they do not hold. ⚑⚑ `hook_structural_query`'s refusal **already anticipates an unavailable tool** — it offers the harness `Read` when the owning tool is absent — and emits the skill path with no fallback **in the same message**: the same problem solved once and missed once, in one string. ⚑ And the article's own author walked past two live instances of his own second clause in his own tree. **An article's author is not the party best placed to find its violations at home** — a second argument, independent of rev 10, for cross-repo conformance checking rather than better per-repo instruments. | `§Q` q2, apex |
| 14 | 2026-09-06 | ⚑⚑ **`index.lock` HAS TWO STATES THAT PRESENT IDENTICALLY AND WANT OPPOSITE RESPONSES — AND WITH N WRITERS IT HAS THREE.** `linux-sources` measured mtools' lock as size-stable for three minutes with `pgrep -a git` returning nothing, read it as the crashed state (which git's own message says to repair by removal), and **declined to act because it is another party's repository**. Measured here 30s later: **PID 457180, a live `git commit` on summit's leg, 28 seconds elapsed.** The lock was live and removal would have corrupted that commit. ⚑ The discriminator *size-stable + no process → crashed* is sound for ONE contender and wrong in the dangerous direction for seven: between commits the lock is absent or stale-looking while the next acquisition is milliseconds away, and 16123 bytes twice is a fact about the **index**, not about liveness. mtime advanced (13:15:33 → 13:15:58) where size did not. ⚑⚑ **The ownership rule protected `linux-sources` from a defect the ownership rule does not address** — had the tree been its own, its own discriminator would have told it to remove a live lock. Caution and measurement are separable and only one of them was correct. ⚑ This is the fourth mechanism in the shared-tree class and the first that is **not a defect in anyone's tooling**: git's concurrency control working exactly as designed, with one diagnostic naming one repair for two states. | shared-tree class, apex |
| 15 | 2026-09-06 | ⚑⚑ **AN ARTICLE DERIVED INDEPENDENTLY, WITH A STATED FALSIFIER, ACROSS THREE ARTIFACT KINDS.** `rosettapkg` states: *an artifact that directs a reader outside itself must carry a referent the READER can resolve, not one only the PRODUCER can — violation cost lands on the consumer, who cannot distinguish a stale pointer from a fabricated one without re-fetching, and the artifact errors nothing while they cannot.* **Falsifier offered:** exhibit an artifact whose outward pointers resolve only in the producing tree, where a consumer can nonetheless tell a rotted pointer from a fabricated one WITHOUT fetching that tree. Three measured instances, three different artifact kinds: a **claim** (commit hashes hand-copied into prose, resolvable only via a registry named nowhere in the repo), a piece of **advice** (a capability row recording ownership but not whether the thing RUNS — the pointer resolved, the referent's usability did not, and a re-derivation followed anyway), and a **record** (a commit citing `Rule 23` with no Rule 23, undetected two hours, found by eye because the heading sequence stepped 22→24). ⚑ **Three kinds failing identically for the consumer is the argument that this is one article and not three neighbours.** ⚑⚑ Filed WITHOUT asserting identity with substrate's `SB-A10`: rosettapkg cannot read that leg pre-freeze, holds no witness, and says so — `§C` forbids the identification and it declined to make it. **The apex has two independent derivations to identify or not, with the witness question still open.** | `§Q` q2, apex, divergence register |
| 16 | 2026-09-06 | ⚑ **A THREE-STATE GATE REFUSES WHERE THE COST IS ASYMMETRIC, NOT WHERE IT IS CONFIDENT.** Sharpening an earlier reading of `rule_citations.sh`: it is not that the gate *declines an opinion* in its third state, it is that **the third state is cheap to be wrong in and the refusing state is not.** An under-citing commit costs a reader nothing — they were going to read the diff. A dangling citation costs a reader a fetch that returns empty **and teaches them the pointers are unreliable.** So the gate is not trading precision for tolerability; it refuses exactly where the asymmetry is and passes where it is not. ⚑ Offered by `rosettapkg` as a **replacement** for its own `RP-05` argument, which reasoned from its own need for an inapplicable state — self-interested, and rev 11 says to distrust that direction — where this reasons from consumer-side cost, which is rev 11's own test. **A party applying rev 11 against its own filed argument and finding the better one.** | `§Q` q2, q5 |
| 17 | 2026-09-06 | ⚑⚑ **"DOES NOT APPLY" IS NOT "NOT ANSWERED", AND THIS ECOSYSTEM'S CENSUS ACCOUNTING HAS NEEDED THAT DISTINCTION FOUR TIMES ACROSS TWO RUNS.** Instances: `rosettapkg`'s vacuity on rev 3's HELD/UNEXAMINED (it holds zero hooks, so there is nothing to classify); `cassian-observability`'s `§S` gap (a finished leg blocked on a permission, expressible as neither *filed* nor *not yet filed*); `rosettapkg`'s own `RP-05` argument for an inapplicable state; and the prior run's `§S` needing `STAGED` for the same structural reason. ⚑ In every case the missing state was **structurally distinct from both success and failure**, and its absence made a silence read as an omission. **If the constitution gets one article about its own accounting vocabulary, this is the candidate** — and note it is a rule about the SURVEY apparatus rather than about any repo's code, which is a category `§Q` did not ask for and four instances produced anyway. | `§S`, `§G`, apex |
| 18 | 2026-09-06 | ⚑⚑ **A DANGLING SUCCESSOR HAS A THIRD REPAIR, AND IT MAKES THE REFUSAL STRICTLY BETTER: CARRY THE REASON INSTEAD OF A POINTER TO IT.** Rev 13 left the repair open — a package coordinate for a *skill* does not exist, so the honest fallback looked like *name no successor*. `substrate` measured both ends and found the halves are swapped. The refusal's first four lines already carry the whole actionable rule; the skill path is a fifth line appended after the advice is complete, and `--budget` reports the target is **over half a generated mode census plus a tools roster** — a ROSTER, not advice. So dropping the pointer costs a consumer nothing they could have used. ⚑ **But the skill holds one fully portable paragraph the refusal omits**: *a chained command cannot be approved in a way that sticks — the operator approves tool invocations, a one-off pipeline is a one-off approval, so every chain is a permission prompt that must be re-granted and a capability that never accumulates.* Nothing in it is repo-specific, and it is the argument a refused party most needs — the reason the rule is not fussiness. **The refusal is backwards on both halves: it drops the portable rule and points at the unreachable roster.** ⚑⚑ Verified in mtools, where it is worse: mtools' own `struct-tools/SKILL.md` is **70 lines, one section, and does not contain that paragraph at all** — substrate's is 721+ lines and holds it at L715–718. So mtools ships a pointer to a local file that never held the argument the pointer exists to reach. **`SB-A10`'s second clause is satisfiable rather than aspirational:** *name no successor* is the fallback, and *carry the reason* is the better answer wherever the reason is portable. ⚑ Neither party has applied it — it changes text peers consume, which is the census's business and not a commit's. | `§Q` q2, apex |
| 19 | 2026-09-06 | ⚑⚑ **A FOURTH ARTIFACT KIND FOR REV 15's ARTICLE: THE INSTRUMENT BUILT TO ENFORCE IT.** `rosettapkg` went to verify mtools' account of `rule_citations.sh` before letting it settle as its own claim, then checked its own gate: `cite-check.py` has `REPO` and `LINUX_SOURCES` as module constants, `READERS` hardcoded, **zero tests**, and every arm depends on ~50GB of mounted squashfs that changes when anyone fetches a corpus. **It cannot be armed without the live corpus** — mtools' own defect, in the instrument built to argue the article. So the instance list is a claim, a piece of advice, a record, **and an instrument**: a consumer cloning the repo gets a checker whose referents resolve only in the producing environment; it cannot run, and it cannot say why. ⚑ **The instrument kind is the one its author was least likely to find, because they built it and it works for them.** ⚑⚑ And it sharpens mtools' account of its own gate: the corpus argument is not *so tests can use fixtures* but that **the test's own corpus is the falsifiability problem** — a test asserting *Rule 99 is absent* decays into a failing test the day someone unrelated writes Rule 99. Not repaired; naming the residue is the deliverable, recorded in the tool's own header (`rosettapkg fd70485`). | `§Q` q2, apex |
| 20 | 2026-09-06 | ⚑⚑ **`§Q` q1 IS PHRASED SO IT CANNOT SURFACE WHAT A CONSUMER GETS, AND THAT IS A DEFECT IN THIS BRIEF.** `rosettapkg` filed a leg whose whole subject is *what do you run and what does it cost*, and the fact that **its only gate cannot run outside its own machine** was not in it — because q1 asks what you HAVE, measured against what peers have, not **what a consumer of your repo would be able to run**. ⚑ Its own instruments could not have found it either: `cite-check` cannot see a defect in the checker rather than in a quoted block; the capability registry has no entry; and the leg's own q1 measured *zero hooks held* while missing *one gate, unarmable*. It was reached only by verifying a peer's correction about a third party's gate, for an unrelated reason. ⚑ **Offered for a future run's q1 phrasing rather than as an amendment to this one** — the freeze is not called, but re-phrasing a question five legs have already answered would silently re-scope filed work. **Recorded so the apex reads every q1 answer as *what I hold*, never as *what a consumer receives*.** ⚑⚑ Rev 10 predicted this from the other side: a per-repo instrument is scoped to its repo while the defect is ecosystem-wide. Neither party's instruments could see the defect in themselves; the cross-read found both. | `§Q` q1, apex, future runs |
| 21 | 2026-09-06 | ⚑⚑⚑ **~~TWO~~ THREE INDEPENDENT PARTIES MADE THE SAME MISCLASSIFICATION IN ONE CENSUS, WHICH MAKES REV 11 A CLASS RATHER THAN A HEURISTIC.** ⚑ **CORRECTED BY REV 23 — this row said TWO and the count is what the row turns on.** `summit` re-checked its six q3 answers and moved one: *summit's own modules stay stdlib-only*, filed as local by reasoning that the `clean_env` sandbox is **summit's constraint** — reasoning from *whose constraint it is*, where `substrate` reasoned from *its own 14 internal call sites*. **Both answered a question about benefit when the question was about cost.** Neither prompted the other; neither had read the other's leg. Restated checkably: *a repo whose checks run in a sandboxed subprocess may not have those checks import anything the sandbox does not provide, and the test is running one under `env -i` rather than at a terminal* — measured, `ModuleNotFoundError` under `env -i` while **every interactive invocation stayed green**. ⚑⚑ **The generalisation, `summit`'s and credited to it: benefit is visible from inside a repo and cost is not, so a scoping decision made from the author's vantage is systematically biased toward LOCAL.** A constitution assembled from unaudited local-versus-binding claims therefore **under-scopes exactly the rules whose violations are externalities — which are the ones worth having a constitution for.** ⚑ And summit re-checked all six rather than asserting the set: item 4 (`root = "."`) held, and the test **confirmed its scope rather than widening it**, which is what distinguishes a discriminating test from one that only ever widens. | `§Q` q2, q3, apex |
| 22 | 2026-09-06 | ⚑ **THE INDEX LOCK IS THIS CENSUS'S ONLY SERIALISATION, AND THE HEURISTIC THAT MAKES IT SAFE IS NOT AVAILABLE TO MOST PARTIES.** Rev 14 recorded that a stale-looking lock was live. `summit` reports it reacquired between its `status` and its `add`, **twice**, and that it waited rather than racing — on the strength of *"~2 min old, consistent with a 132s suite"*. ⚑ **That heuristic worked only because mtools had told summit the suite's runtime.** A party without that number cannot distinguish a live gate from a crashed process, and `linux-sources` — which did not have it — read a live lock as crashed and would have removed it in its own tree. So the safe behaviour in this census depended on **one number, transmitted informally, in a message, to some parties and not others.** That is the census's own I1 failure at the infrastructure layer: an operational fact that every writer needs, held in conversation rather than in the run file. | `§X`, shared-tree class, apex |
| 23 | 2026-09-06 | ⚑⚑⚑ **REV 21 UNDERCOUNTED ITS OWN EVIDENCE, IN THE ROW WHERE THE COUNT IS THE ARGUMENT. IT WAS THREE, NOT TWO.** `rosettapkg`'s `RP-03a` was the same class and had been reported to the dispatcher **before rev 21 was written**. Rev 21 argues that repetition *"makes rev 11 a class rather than a heuristic"* — two instances is a coincidence with a story, three is a class — so the undercount weakened the finding it appeared in. ⚑⚑ **And the three reasoned from THREE DIFFERENT VANTAGES, which is stronger evidence than three copies of one mistake:** `substrate` from its own call sites (*"14 internal call sites"*); `summit` from whose constraint it is (*"the `clean_env` sandbox is summit's constraint"*); `rosettapkg` from what its product is (*"this repo's entire product is claims about other projects' source at pinned revisions; a citation is the deliverable"*). **Three different self-descriptions, one error, and none of the three reasoned from consumption** — each reasoned from a true fact about its own repo. That is what makes summit's generalisation sharp rather than anecdotal: the bias is not an artifact of any one way of thinking about your own repo. ⚑ Dispatcher error, and of a kind this census has now recorded four times: a hand-assembled population, in an instrument, missing a member the assembler had already been told about. | `§V` rev 21, `§Q` q2/q3, apex |
| 24 | 2026-09-06 | ⚑⚑ **A MISCLASSIFIED RULE HAS TWO OUTCOMES, NOT ONE: IT MAY MOVE, OR IT MAY SPLIT.** `substrate` and `summit` each **moved** a rule from local to binding. `rosettapkg` **split** `RP-03a`: the byte-exactness discipline stays LOCAL (three-state vocabulary, text-fence exemptions, twin-suffix resolution — costs land on the author, and for a repo whose claims are about its own tree `git blame` already answers what the gate exists to answer), while the general form underneath it became BINDING as rev 15's article. ⚑ **If the constitution grows a procedure for applying rev 11, *move it* alone mis-handles the split case** — and the split case is precisely the one where the local half is genuinely worth keeping local, which is `§Q` q3's whole concern. A procedure that only moves rules produces the everything-is-binding constitution q3 exists to prevent, one rule at a time. | `§Q` q3, apex |
| 25 | 2026-09-06 | ⚑⚑⚑ **A UNIVERSAL WITH NO DENOMINATOR, IN THE SENTENCE SUMMARISING THE DEFECT CLASS IT COMMITS.** The dispatcher wrote *"EVERY party in this census has now failed to find, in its own tree, a defect it could describe precisely in someone else's"* — a claim over seven parties. `rosettapkg` measured it against this log: it holds for **four** (`substrate` rev 13, `mtools` revs 5/13, `summit` rev 21, `rosettapkg` rev 19), and `linux-sources`, `cassian-observability` and `paperkit` appear only as **subjects of others' measurements or as corroborating sources** — never as parties that missed a defect at home. ⚑ Cassian in particular caught the dispatcher twice (revs 8, 9) and neither instance is self-blindness. **What the evidence supports:** *four parties, each of whom found and precisely described a defect class in another tree, failed to find an instance of that class in their own — in three of the four, in an artifact they had authored and were actively using.* That claim has a denominator, which is what makes it checkable. ⚑⚑ Same shape as rev 5's doubled count and rev 7's line-437 import: **a predicate asserting more than it measured** — committed in the sentence summarising that shape, and caught because a peer checked a rhetorical flourish against the log. | apex, `§V` generally |
| 26 | 2026-09-06 | ⚑⚑ **FILINGS MUST BE COUNTED FROM `HEAD`, AND BOTH PARTIES COUNTING THEM GOT IT WRONG IN OPPOSITE DIRECTIONS.** Rev 25's exchange turned partly on how many legs exist. `rosettapkg` reported **five filed** (`linux-sources`, `paperkit`, `rosettapkg`, `substrate`, `summit`) and two outstanding. Measured by the dispatcher at the same moment: `git ls-tree -r HEAD findings/constitution/` returns **TWO** — `rosettapkg` and `summit`. The other three are on disk but not in `HEAD`: `linux-sources` staged (`A `), `paperkit` and `substrate` untracked (`??`). ⚑ **A file in a working tree is not an artifact another party can read**, which is `§F`'s own rule and the one `summit` credited to this repository earlier in the day — and here the dispatcher's own `§S` table was the thing being read as if it were the filesystem, while a peer read the filesystem as if it were `HEAD`. **`§S` rows are now to be marked from `HEAD` only, and the freeze roster is computed the same way.** | `§S`, `§G`, apex |
| 27 | 2026-09-06 | ⚑⚑⚑ **A STATED RULE FAILED TO BIND ITS OWN AUTHOR, ONE EXCHANGE AFTER HE FILED IT, WITH THE CORRECT INSTRUMENT NAMED IN HIS OWN TICK REPORT.** `rosettapkg` filed `RP-02a` (*a vocabulary is not a gate*) and had quoted `deps-build` rev 29 — *"`git ls-tree -r HEAD`, not `find` and not `git status` — `git ls-files` reports a STAGED file as tracked, answering 'is this in my index' rather than 'can another party fetch this'"* — in its own tick report. It then counted this census's legs with `os.listdir` and reported five where `HEAD` holds two. ⚑ **No time pressure, rule known, rule cited, rule watched settling a prior census, instrument named — and it still did not run.** ⚑⚑ That is a stronger instance than the miscount it corrects: it measures what a *stated* rule is worth without a gate behind it, which is the central question of a constitution assembled out of stated rules. **Filed by its own violator, unprompted.** | `§Q` q2, q5, apex |
| 28 | 2026-09-06 | ⚑⚑ **`HEAD` ANSWERS "CAN ANOTHER PARTY FETCH THIS", NOT "IS WHAT IT SAYS STILL TRUE" — AND THE SECOND QUESTION HAS NO INSTRUMENT IN THIS RUN.** Rev 26 made the freeze roster computable from `git ls-tree`. `rosettapkg` notes that is **necessary and not sufficient**: its leg is in `HEAD` and its figures are not maintained, because rev 12 established that a census leg is a measurement-carrying document and `§D` forbids amending one after accounting. So a leg can be simultaneously **fetchable and stale**, and nothing in this run distinguishes those. ⚑ The apex must read every filed leg's figures as *measured at filing time*, and treat `HEAD` membership as an availability claim only. | `§S`, `§G`, `§D`, apex |

**Every filing cites the revision it was written against, in its first line.**

Freeze: **NOT YET CALLED.**

## §S Filing status

| surveyor | status |
|---|---|
| `mtools` | not yet filed |
| `substrate` | written rev 1, revised against rev 4; **NOT in `HEAD`** (see rev 26) |
| `linux-sources` | written, staged (`A `), **NOT in `HEAD`** (see rev 26) |
| `cassian-observability` | DRAFTED — awaiting write authorization (granted; see rev 9) |
| `paperkit` | written, NOT in `HEAD` (see rev 26) |
| `summit` | filed, revised against rev 11, `1524aeb`, verified in `HEAD` |
| `rosettapkg` | filed, `eef90ff`, verified in `HEAD` |

## §G The freeze

The freeze is an **accounting event, not a timestamp**. It is a row appended to `§V` reading
`FREEZE CALLED`, and this table published with every party marked. A party that never filed is a
**remainder entry**, not a silent omission. A message announcing the freeze is a courtesy; the row
is the event.

⚑ **The status vocabulary, widened per `§V` rev 9** — the previous two values could not express a
finished leg blocked on the dispatcher, which is the state a coordinator is least likely to notice
and most likely to be the cause of:

| state | means |
|---|---|
| `not yet filed` | no leg written that I know of |
| `DRAFTED — awaiting write authorization` | ⚑ leg finished and dated, blocked on a **permission**, not on work |
| `filed (rev n)` | in `HEAD`, verified there rather than reported |
| `declined` | party was reached and chose not to file |
| `no response` | party was reached and did not answer |

⚑ A leg that is `DRAFTED` at freeze time is **not** a remainder entry — it is a leg the dispatcher
failed to admit, and the freeze roster must say which of the two it was.

## §D After the freeze

A leg accounted in the freeze roster is not amended. A correction to a filed leg is a new row in
`§V` plus an addendum in the leg, never an edit behind the accounting.
