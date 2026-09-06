# `constitution` census — paperkit's leg

**Written against `CENSUS-constitution.md` rev 28** (brief `CENSUS-BRIEF.md`). Prefix `PK-`.
⚑ **Rev 11 re-check applied to `§Q` q3 — see PK-03e. One answer MOVED from local to binding.**
⚑ **Rev 22 re-check — see PK-03f. PK-03a survives, and its GENERAL half was mine to file and I did not.**
⚑⚑⚑ **Rev 3 + rev 4 re-check — see PK-01b. THREE OF FIVE ARMED HOOKS CRASH AND EXIT 0 IN THIS REPO. Found by rev 4's question, not by me.**
IDs are directory-wide. Every figure below re-derived in this tree for this filing.

## Disclosures (brief §9)

- **Instrument:** `git`, `python3` reading `.claude/settings.json` as JSON, `md5sum`, `readlink -f`,
  `ls -la`. No Bazel invocation (a peer held the server lock at filing time).
- ⚑ **I have not read any peer leg.** The freeze has not been called.
- ⚑ **This session is itself an instrument for `§Q`-4**, and that is a bias worth declaring: it has
  spent ~19 hours re-deriving settled rulings in this repo, so my evidence for relitigation is
  unusually rich and unusually self-implicating. Weight accordingly.
- **Termination test (brief §12):** *No* — a reader of this file alone cannot reconstruct what was
  asked of the other legs. That is the apex's job.

---

## PK-01 What I run today — and paperkit's answer to distribution is DIFFERENT IN KIND

**8 command entries, not 6 or 18** — the dispatcher's `§X` says 8 and my first count said 6. Both
are right and the discrepancy is a measurement lesson: `§X` counts **all hook events**, my first pass
counted only `PreToolUse`.

```
PreToolUse: 6      Stop: 2      TOTAL: 8
```

| hook | provenance | content |
|---|---|---|
| `hook_structural_query.py` | ⚑ **SYMLINK** → `../../substrate/scripts/` | `b094c4d9` |
| `hook_no_chaining.py` | ⚑ **SYMLINK** → substrate | `d9e8bcc4` |
| `hook_shellcheck.py` | ⚑ **SYMLINK** → substrate | `691b0a1c` |
| `hook_cmdparse.py` | ⚑ **SYMLINK** → substrate | `27cddbcb` |
| `hook_pycheck.py` | ⚑ **SYMLINK** → substrate | `391d9eda` |
| `hook_gate_running.py` | **paperkit's own file** | local |

All armed via `*_HOOK_BLOCK=1` inline. Git hooks: `.githooks/pre-commit` (one Bazel target,
`bazel test //:hook --config=mutant` under `tools/cpuweight.py`), plus `local.env` / `.example`.

⚑⚑ **PAPERKIT HAS ZERO CONTENT DRIFT, AND NOT BECAUSE IT IS DISCIPLINED.** Every symlinked hash
matches substrate's byte-for-byte because **there is no copy to drift.** The dispatcher's drift
table shows four repos holding four bodies of `hook_no_chaining` (one 14 lines longer); paperkit
does not appear in that comparison because it has no body of its own.

**The bound, stated because it is the interesting half:** a symlink is not a distribution mechanism.
It requires a fixed sibling-directory layout (`../../substrate/scripts/`), breaks on any checkout
that lacks substrate, cannot be versioned or pinned, and silently adopts an upstream edit with no
review. **It solves drift by giving up independence** — the opposite trade from a package, not a
better version of the same one. It is evidence about what drift COSTS, not a proposal.

### PK-01b ⚑⚑⚑ REV 3 + REV 4 RE-CHECK — the census's question found a LIVE DEFECT in my repo

**Rev 3 (HELD or UNEXAMINED, per differing hook): the question is UNDEFINED here**, and paperkit is
the only repo where it can be. All five borrowed hooks are symlinks, so a difference cannot exist —
there is no second body to hold or to leave unexamined. ⚑ *That is not a better answer to rev 3; it
is a different failure mode, and rev 4 is where it shows up.*

**Rev 4 (do your hooks' dependencies resolve, DECLARED or AMBIENT): AMBIENT, AND THEY DO NOT.**
MEASURED by running each armed hook in paperkit with a real payload:

```
$ echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}'     | NOCHAIN_HOOK_BLOCK=1 python3 scripts/hook_no_chaining.py
  File ".../scripts/hook_no_chaining.py", line 84, in <module>
    from scripts import hook_cmdparse
    from substrate.ratchet_flags import arg_after
ModuleNotFoundError: No module named 'substrate'
rc=0
```

| hook | traceback |
|---|---|
| `hook_no_chaining` | **YES** |
| `hook_structural_query` | **YES** |
| `hook_shellcheck` | **YES** |
| `hook_pycheck` | no |

⚑⚑ **THREE OF FIVE ARMED HOOKS CRASH, AND EVERY ONE EXITS 0 — THEY FAIL OPEN.** Armed with
`*_HOOK_BLOCK=1`, wired in `.claude/settings.json`, and enforcing nothing. A gate that cannot run is
indistinguishable, from the outside, from a gate that passed.

**Why, mechanically:** `hook_cmdparse` resolves its sibling with
`_ROOT = Path(__file__).absolute().parent.parent` then `sys.path.insert(0, str(_ROOT))`. Through a
symlink, `__file__` resolves into **substrate's** tree, so `_ROOT` is substrate's root — which makes
`from substrate.ratchet_flags import arg_after` (rev 7's line 437) resolvable **in substrate and
nowhere else**. Rev 4 states the rule and rev 7 supplies the mechanism; **paperkit is the borrower
where both meet.**

⚑ **This retires my own PK-01 claim of "zero content drift."** The bytes are identical and the
BEHAVIOUR is not — which is `§Q` q1's own warning (*"a hook's NAME is not its BEHAVIOUR"*) applied to
its hash. **Identical bytes in a different tree are a different program.** A digest census cannot see
this, and neither could I until rev 4 asked the question that produces it.

⚑⚑⚑ **And it is the strongest evidence I hold for the census's subject.** I filed PK-01 reporting
symlinks as paperkit's distribution answer and did not run the hooks. The census asked a question my
leg had no answer to, and the answer was a live fail-open in three armed hooks. **The relitigation
cost here was zero and the distribution cost was total** — the code travelled perfectly and did not
work.

*Not fixed in this filing: the repair is substrate's `sys.path` prelude or a declared dependency,
and per rev 11 that is a BINDING article rather than a paperkit patch. Filed, not patched.*

---

## PK-02 Settled here, and I claim it BINDS EVERYONE

Stated as checkable claims, each with the measurement that settled it and what it cost.

**PK-02a — A verdict comes from the payload's own line, never from a wrapper's exit code.**
*Cost: measured SEVEN distinct liars in one session.* wrapper-0 over a payload `FAIL`; wrapper-0
over **no verdict line at all**; a pipe-tail `0` over `Terminated`; a static log read as finished
while the run continued 8 minutes; `Build completed successfully` for a cache hit whose artifact
`find` could not see; and **`nohup` exit 0 five separate times** while the run continued.
*Checkable:* does the consumer grep the payload's verdict line, or read `$?`.

**PK-02b — Liveness is a property of the process, not of its log.** A quiescent log is
indistinguishable from a finished one. *Cost:* reading a static log as complete led to editing the
tree during a live gate — the input-dependency-modified corruption class, self-inflicted.
*Checkable:* does the waiter poll `pgrep -f "<command>"`, or wait on a wrapper.

**PK-02c — Ask the owner, not the filesystem.** `bazel aquery <target>` names the command a cell
actually runs. *Cost:* three ticks reproducing a `uv sync` failure on a code path the cell never
takes. **A reproduction is not a diagnosis unless the path reproduced is the path taken.**
*Related:* `find bazel-bin -name X` returns nothing because `bazel-bin` is a SYMLINK.

**PK-02d — A repair unproven by the arm that found the defect is not a repair, and the F-arm must
run FROM THE CONDITION THAT FAILED.** *Cost:* a `cwd`-dependent defect survived three ticks because
every arm was run from the repo root, where it cannot reproduce.
*Checkable:* does the fix ship with a failing-direction arm, executed under the failing condition.

**PK-02e — A negative finding counts only what the query could see.** *Cost:* a corruption count
went `91 → 32 → 24` across two corrections, because the query included the census's own commentary
about the count; the number **drifted under re-query**, which is the tell available without knowing
the right answer. *Checkable:* does an asserted absence carry a positive control.

**PK-02f — A count is a claim about a population; state the predicate, not the number.**
*Corollary of e, and the operationally useful half:* cite the filter (`toolUseResult` key present),
never the figure. Four figures travelled this ecosystem unchecked; three were mine.

---

## PK-03 Settled here, binds ONLY paperkit

⚑ *The question the run file says gets skipped. These are correct here and would be noise or wrong
elsewhere.*

**PK-03a — `hook_gate_running.py`: refuse a tracked-tree edit while the gate is running.**
Correct here because paperkit's gate takes **2,496–14,420 seconds** and edits during it corrupt
sandboxed cells. A repo whose gate takes 30s does not need this and would experience it as friction.
*(⚑ `§X` shows `linux-sources` also runs a `gate_running` hook and no one else does — see PK-04.)*

**PK-03b — Symlinked hooks (PK-01).** Depends on a fixed sibling layout. Binding this would break
any repo not checked out beside substrate.

**PK-03c — The mutation sweep as the falsifiability test.** A claim whose verdict does not change
under systematic definition-mutation grades *indeterminate*, not passing — 8,114 `Ζ·eval` cells for
one project. Correct for a repo whose product IS verified claims; absurd overhead for a repo whose
tests are tests.

**PK-03d — `--local_resources=memory=…` and `cpuweight` wrapping every gate invocation.**
`.githooks/pre-commit:162` says it outright: *"Bare `bazel test //:hook` is not the same command as
this line."* This is a property of one machine's contention, not a rule about hooks.

### PK-03e ⚑⚑ REV 11 RE-CHECK — one q3 answer was wrong, and the test caught it

Rev 11: *ask who bears the cost of the violation, not who benefits from the rule.* Applied to all
four q3 answers. **Three hold. One moves.**

| | verdict under rev 11 |
|---|---|
| PK-03a `hook_gate_running` | **LOCAL, holds** — the cost of an edit-during-gate lands on paperkit's own sandboxed cells. No peer pays. |
| PK-03c mutation sweep | **LOCAL, holds** — the cost of not sweeping is paperkit's own claims grading `indeterminate`. |
| PK-03d `--local_resources` / cpuweight | ⚑ **LOCAL, but the reasoning was wrong.** I filed it as a property of one machine. Under rev 11 the question is who pays when it is violated — and an unbudgeted gate oversubscribes the box **every peer shares**. It stays local only because the *rule* is machine-specific while the *obligation* (do not oversubscribe a shared host) is general. **The obligation is a q2 candidate I did not file.** |
| PK-03b symlinked hooks | ⚑⚑ **MOVES — see below.** |

**PK-03b was filed local because I reasoned from paperkit's motive** (zero drift, no copy to rot) —
the exact error rev 11 describes substrate making. Re-derived by measurement instead:

```
peers symlinking INTO paperkit:                 0    (checked substrate, linux-sources,
                                                      cassian, summit, mtools)
but — mat260/Makefile:17   PAPERKIT ?= $(HOME)/github/paperkit/paperkit
      mat260/Makefile:64-67  $(PY) $(PAPERKIT)/gate.py reflection
                             $(PY) $(PAPERKIT)/project.py reflection --check
                             $(PY) $(PAPERKIT)/rhetoric.py --check reflection
```

⚑⚑⚑ **`mat260` consumes paperkit's engine by absolute path, and is on no roster.** So paperkit
*is* an artifact another repo consumes, and the cost of paperkit's engine breaking lands on
mat260's gate — which fails soft (`else echo "paperkit absent … SKIPPED"`), meaning **the consumer
degrades silently**, the class this ecosystem has measured repeatedly.

**What moves:** not "symlink your hooks" — that stays local. The binding article is one level up and
I had not stated it: **⚑ a repo that is consumed by absolute path owes its consumers a declared
interface and a loud failure, because the consumer cannot see a change coming and its fallback is
silence.** Filed here as a q2 candidate discovered by q3's own test.

**And the meta-finding:** I answered q3 in the leg above, then rev 11 arrived and **one of my four
answers was wrong for exactly the reason rev 11 names.** The test works, and it worked on an author
who had just written that q3 "gets skipped" — I did not skip it, I answered it from the wrong side.

### PK-03f ⚑⚑ REV 22 RE-CHECK — PK-03a holds, but I under-filed it the same way I under-filed PK-03d

Rev 22 puts mtools' gate at **~130s cold / ~60s warm**, so `.git/index.lock` in the shared tree is
routinely held for minutes by a commit that is working correctly.

**PK-03a (`hook_gate_running`) survives as LOCAL** under rev 11's test: the cost of an
edit-during-gate lands on paperkit's own sandboxed cells, and a repo with a 30s gate would
experience the hook as friction. That is unchanged.

⚑⚑ **But rev 22 is the same defect class one layer down, in a tree I write to**, and by rev 11's
test the general obligation is BINDING while my hook is local:

> **A long-running exclusive operation must be waited on, not diagnosed as stale — because with N
> writers there are three states (live, crashed, *between acquisitions*) and no single sample
> separates the last two.**

`hook_gate_running` is that obligation implemented for *one* resource (paperkit's worktree during
its own gate). Rev 22's `.git/index.lock` is the same obligation for a *shared* resource, where the
cost of getting it wrong lands on another party's in-flight commit. **I filed the instance and not
the principle — the identical under-filing as PK-03d.** Two of my four q3 answers had a binding
general half I had not separated out; that ratio is itself the finding.

**Rev 22's discriminator, applied here rather than accepted:**

```
mtools/.git/index.lock  present, 16123 bytes          <- exactly the size rev 22 warns is not evidence
mtime 1788715205 -> 1788715205 over 12s               <- VERDICT: indeterminate from one interval
```

⚑ **Indeterminate is the correct answer, not a failed measurement.** A point sample of an interval
property cannot separate *crashed* from *between acquisitions*, so the honest output is "wait" —
which is what rev 22 prescribes and what I did. This is `PK-02e` (a negative counts only what the
query could see) arriving on a lock file instead of a corpus.

⚑ **And the delivery is the finding rev 22 half-states about itself.** It says this "until now
lived only in messages to some parties and not others" — so an operational fact every writer needed
was distributed by relay, unevenly, while the run file was the artifact everyone reads. That is
`§Q`-4's re-derivation shape with the dispatcher as the source: **not a fix that failed to travel, a
fact that was never put where it would be found.**

---

## PK-04 Where I re-derived what someone had already settled — the highest-value answer

**PK-04a — ⚑⚑⚑ I RE-DERIVED RULINGS THAT WERE ALREADY WRITTEN IN THE FILES I WAS EDITING.**
Measured: `.bazelrc` carries **20** `⚑`-marked rulings, `paperkit/library/run-witness` **8**,
`tools/read_grade.py` **2**. In this session I re-derived at least three of them the hard way:

- `run-witness`'s own comment says *"a path relative to a directory that moved is the same defect
  `_LIBRARY` had one level up"* — and I spent three ticks rediscovering exactly that defect one
  level down, in that file.
- `.bazelrc`'s heap-ladder note ends *"the ceiling tracks GRAPH SIZE and nobody re-derived it when
  the graph moved"* — I then measured the graph and found it stale by 25,710 actions.

**What would have had to exist:** not a package — **the ruling was in the file and I read past it.**
A comment is a ruling with no index and no query surface. What was missing is the ability to ASK
*"what has already been settled about this file?"* and get an answer that is not a full read.

**PK-04b — `hook_gate_running` appears in paperkit and linux-sources and nowhere else.** Two repos,
same need, no shared body. I cannot tell from inside whether mine descends from theirs or is
parallel; my earliest commit touching it is `0893d86`. *This is exactly the identification the apex
must witness rather than assume.*

**PK-04c — I hand-rolled a lease and did not know it.** A `.cellvenv` race fix builds to a private
path and claims a shared name by `os.rename`. That is mutual exclusion over a named artefact —
`membudget`'s `claim:<tag>` primitive, which a four-party census in this same directory had already
characterised. **I wrote a worse version while the better one was documented two directories away.**

**PK-04d — 93 memory entries** under `~/.claude/projects/.../memory/`. Each is a ruling durable
enough to persist across sessions, which means each is a ruling that did not stay settled without
one. That is the relitigation rate for a single repo, measured.

---

## PK-05 What re-opening a settled rule should COST

⚑ **The framing I would push back on:** the run file separates distribution failure from
relitigation, and PK-04a says the split is not clean. **I relitigated rules I was looking at.**
Distribution had already succeeded — the ruling was in the file, in this repo, in my editor — and it
was relitigated anyway. So a package fixes strictly less than half of this.

**The amendment path I would actually follow, and do:**

1. **Reopen only with a measurement, never with an argument.** Every ruling above is stated with the
   ⟨P, F, δ⟩ that settled it. To reopen one, exhibit a case where the arm fails — that is a cost the
   ruling's own author already paid, so it is symmetric.
2. **The re-opener carries the positive control** (PK-02e). "This rule seems wrong" is not evidence;
   "here is the rule's own arm, failing, on this input" is.
3. **A withdrawn ruling stays visible as residue, never deleted.** Practised here: the pullback
   correction, the two refuted hypotheses, and the superseded landing-sequence are all kept in place
   and marked, because deleting them repeats the move they illustrate.
4. ⚑ **An amendment must state which repos it binds.** Untyped rules are what makes a constitution
   collapse into either "everything binds everyone" (PK-03's failure mode) or "nothing binds."

**What I would require as evidence:** the same bar the rule met. A rule settled by measurement is
amended by measurement; a rule settled by convention is amended by agreeing a new convention. ⚑
**The asymmetric case is the dangerous one** — reopening a measured rule with an argument, which is
how a settled question becomes two defensible answers.

---

## PK-06 Roster nomination (brief §6)

**The `~/.claude/skills/` tree**, and specifically whoever owns `census-kit` and `project-tooling`.
`census-kit`'s own postmortem is a measured account of a four-party survey in this very directory —
including *"one ID prefix meaning two different things across two documents … nobody has caught the
second"*, which was **mine**, and which I fixed only because the skill named it. **That tree holds
settled rulings, binds every session on this machine, and is on no roster.** It is a party by every
criterion in `§R` except that nobody has asked it.

## PK-07 Antecedent probe (brief §6, run file §W)

Origins named where I could establish them: PK-02a–f all originate in *this session*, 2026-09-05/06,
each with a measured failure. PK-03a: `hook_gate_running.py` first appears in `0893d86`. PK-03c/d
predate my record and I **cannot name their origin** — per `§W`, *"a rule whose origin you cannot
name is a finding"*, and I record it as one rather than inventing a provenance.
