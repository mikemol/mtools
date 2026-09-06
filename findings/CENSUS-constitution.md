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
per identification**. Two repos both running `hook_no_chaining` is NOT an identification — measured
here, four repos hold four different bodies of that file by content hash, one of them 14 lines
longer. State non-identifications explicitly. `A` is publishable, verifiable, and **not the answer.**

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

Measured from mtools, 2026-09-06. Provided because no leg can see it from inside:

**PreToolUse hooks, by repo** (`.claude/settings.json`, count of `"command"` entries):

    linux-sources          18    format, gate_running, no_chaining, pycheck, shellcheck, structural_query
    cassian-observability  18    no_chaining, no_verify, shellcheck, shellcheck_wrap, structural_query,
                                 tofu_fmt, tofu_validate
    summit                 12    cmdparse, no_chaining, pycheck, scratch_probe, shellcheck, structural_query
    substrate              10    no_chaining, pycheck, shellcheck, structural_query
    paperkit                8    cmdparse, gate_running, no_chaining, pycheck, shellcheck, structural_query
    mtools                  2    structural_query, no_chaining (landed today, not yet wired)
    rosettapkg              0    NO .claude/settings.json

All armed via `*_HOOK_BLOCK=1`; most also arm inline in the command string.

**⚑⚑ Content drift, by md5 of the first 8 chars — the finding that reframes this survey:**

    hook_no_chaining      substrate d9e8bcc4 668L | paperkit SYMLINK | summit d9e8bcc4 | cassian d4ebd0c8 682L
    hook_structural_query substrate b094c4d9 760L | paperkit SYMLINK | summit b094c4d9 | cassian 7442f527 605L
    hook_shellcheck       substrate 691b0a1c 861L | paperkit SYMLINK | summit 691b0a1c | cassian c6a35093 627L
    hook_cmdparse         substrate 27cddbcb 492L | paperkit SYMLINK | summit 8096c871 364L | cassian 83a15017 418L

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

**Every filing cites the revision it was written against, in its first line.**

Freeze: **NOT YET CALLED.**

## §S Filing status

| surveyor | status |
|---|---|
| `mtools` | not yet filed |
| `substrate` | not yet filed |
| `linux-sources` | not yet filed |
| `cassian-observability` | not yet filed |
| `paperkit` | not yet filed |
| `summit` | not yet filed |
| `rosettapkg` | not yet filed |

## §G The freeze

The freeze is an **accounting event, not a timestamp**. It is a row appended to `§V` reading
`FREEZE CALLED`, and this table published with every party marked `filed` / `declined` /
`no response`. A party that never filed is a **remainder entry**, not a silent omission. A message
announcing the freeze is a courtesy; the row is the event.

## §D After the freeze

A leg accounted in the freeze roster is not amended. A correction to a filed leg is a new row in
`§V` plus an addendum in the leg, never an edit behind the accounting.
