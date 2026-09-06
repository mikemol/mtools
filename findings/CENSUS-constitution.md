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

**Every filing cites the revision it was written against, in its first line.**

Freeze: **NOT YET CALLED.**

## §S Filing status

| surveyor | status |
|---|---|
| `mtools` | not yet filed |
| `substrate` | **filed** (written rev 1, revised against rev 4 pre-freeze) |
| `linux-sources` | not yet filed |
| `cassian-observability` | DRAFTED — awaiting write authorization (granted; see rev 9) |
| `paperkit` | filed (rev 1) |
| `summit` | filed (rev 1) |
| `rosettapkg` | filed (rev 1) |

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
