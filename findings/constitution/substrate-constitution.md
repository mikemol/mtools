# `substrate` — constitution census leg

**Written against `CENSUS-constitution.md` rev 1; revised against rev 4 before the freeze.**
Freeze not called at time of filing or of revision.

⚑ **Revision note.** Revs 2–4 landed after my first filing and added two obligations to question 1
(HELD-vs-UNEXAMINED, rev 3; dependency resolution DECLARED-vs-AMBIENT, rev 4). `§D` bars amending a
leg *accounted in the freeze roster*; the freeze is not called, so this is a revision rather than an
addendum. The rev-1 content is unchanged below except where marked; the new material is
**SB-12 … SB-15**, and **SB-13 contradicts `§V` rev 3 on a point of fact about substrate's own
code.**

## §9 Disclosures

I am the substrate session. **I own the subject under survey**: `scripts/hook_*.py` are authored
here, and `§X` reports that paperkit symlinks five of them into `../../substrate/scripts/`, so my
corpus is upstream of at least one peer's. That is a conflict worth naming — a leg reporting on
code it wrote will read its own choices as settled rather than as contestable.

**My inputs differed from peers' in one way I can see:** the dispatch I received was a two-line
message naming the run file and the roster. I do not know whether other legs received more. I read
`CENSUS-BRIEF.md` and `CENSUS-constitution.md` and nothing else in `findings/`.

**⚑ I was handed measurements of my own corpus.** `§X` reports substrate's hook count, four content
hashes and four line counts. Under brief §7 that is **testimony**, not citation, so I re-derived it
(SB-01, SB-02). Where I could not reproduce a figure I say so rather than adopting it.

**I have not read any peer leg.** Independence per brief §2 held.

## §3 Inclusion predicate — what I read

```
A  .claude/settings.json (harness hook wiring)                      -> 1 file, 63 lines
B  scripts/hook_*.py (hook bodies, md5 + presence)                  -> 5 files
C  scripts/** suffix .py (population denominator for B)             -> 131 files
D  .githooks/pre-commit via gate_status.py --list (wired gates)     -> 37 gates
E  CLAUDE.md + .claude/skills/*/SKILL.md (settled rulings in prose) -> read, not counted
F  summit capability --unknown-to substrate (prior-art probe)       -> 51 capabilities
G  none — no CI config in this repo; no .github/workflows present
                                                    TOTAL A–D       -> 174 records
```

**Exclusions, with counts and reasons:**

- `agda/**` (~3.5k modules) — not read. The subject is hooks and settled rulings, not the Agda
  corpus those rulings govern.
- `scratch/**` (509 .py) — not read as bodies. Counted only where a hook or gate names one.
- Peer repos — forbidden by brief §2 until the freeze.

## §10 Coverage

Files read in full: 4 (`settings.json`, `CENSUS-BRIEF.md`, `CENSUS-constitution.md`, this leg's
sources). Files probed by tool without full read: 5 hook bodies, 131 `scripts/*.py` (population
only), 37 gate declarations.

**Unparseable / unreadable: 1.** `substrate/code_lines.py` produced no output on a bare run and no
output when given four file arguments (SB-09). I claim nothing about what it would have reported.

**What I did not search, and why:** per-hook line counts. `§X` asserts them; my attempt via `wc`
was refused by my own `hook_structural_query` (SB-03), the owning tool `pycodemod` has no mode I
could find for whole-file line counts, and I declined to burn further calls guessing mode names
after one wrong guess cost a full banner dump. **The line-count half of `§X`'s substrate figures is
therefore UNVERIFIED BY ME** — not disputed, unverified.

## §5 Negatives

**SB-N1 — substrate has no CI workflow.** Spelling searched: `.github/**`. Denominator: repo root.
Reader: `scratch/vfs.py --census` (working-tree matcher). Result: `total 0`.

**Positive control, same reader, same tree:** `vfs.py --census '.githooks/**'` → `PRESENT nonempty
4`. So the reader can see dotted config directories, and the zero above is a fact about the tree
rather than about the instrument.

⚑ **A mode this instrument silently accepts and ignores, declared per brief §5:** the control run
also returned `BROKEN 1 — .githooks [Errno 21] Is a directory`, exit 2. The reader counts a
directory entry as a broken member rather than skipping it, so a `**` census over any directory
inflates its total by one and exits non-zero. That does not change either verdict here, but a leg
quoting `vfs --census` totals without saying so would be off by one.

Conclusion: **no CI config appears among the shapes my reader decodes.** substrate's gating is
entirely local — `.githooks/pre-commit` plus the harness hooks.

**SB-N2 — the forum has no entry for the spelling `hooks`.** `summit capability hooks` →
*"no entry carries the spelling 'hooks' (51 capabilities, 389 registered spellings)"*. **Positive
control:** `summit capability --unknown-to substrate` returns 43 rows from the same reader, so the
index is readable. ⚑ Per summit's own rule this is a fact about the SPELLING, not about the
ecosystem — and SB-10 shows the capability exists under two other names.

---

## Q1 — What substrate runs today

**SB-01 · PreToolUse hooks, and a count that depends on how you count.** `citation` —
`.claude/settings.json:9-40`.

Substrate wires **four distinct hook programs** across **two matchers**, as **five `"command"`
entries**:

| matcher | hooks |
|---|---|
| `Bash` | `hook_structural_query.py`, `hook_no_chaining.py`, `hook_shellcheck.py` |
| `Edit\|Write\|NotebookEdit` | `hook_pycheck.py`, `hook_shellcheck.py` |

⚑ **`§X` reports substrate at 10.** I count 5 `"command"` entries, or 4 distinct programs, with
`hook_shellcheck` wired twice. I cannot reproduce 10 under any reading I tried. **This is a
divergence in the dispatcher's own table**, and it matters for the survey's headline: a hook COUNT
is as ambiguous as a hook NAME. Whether the difference is a counting convention or a stale read, I
cannot tell from inside — recorded, not adjudicated.

**SB-02 · Content identity, re-derived.** `citation` — `md5sum` over `scripts/`:

```
d9e8bcc41403a9e98c2e7d9eda45c580  scripts/hook_no_chaining.py
b094c4d9ad4ac2c063c1a728b27b4115  scripts/hook_structural_query.py
691b0a1c828a10e64067c28ec23986a2  scripts/hook_shellcheck.py
391d9eda2acc063348a2548475c78472  scripts/hook_pycheck.py
27cddbcb875e9c53ab80561789896546  scripts/hook_cmdparse.py
```

All four hashes `§X` attributes to substrate **confirm** (`d9e8bcc4`, `b094c4d9`, `691b0a1c`,
`27cddbcb`). The testimony is accurate on hashes.

⚑ **`hook_pycheck.py` (`391d9eda`) is wired here and absent from `§X`'s drift table.** Substrate
runs five hook files and the drift table covers four. A drift census that omits a wired hook cannot
report drift in it — and I am the only party who can see that, which is why it is in my leg.

**SB-03 · How the code got here: written here, and consumed by symlink downstream.**
`inference` from SB-02 + `testimony` from `§X`. All five bodies are authored in this repo. `§X`
reports paperkit symlinking into `../../substrate/scripts/`. I did not verify the symlinks (peer
tree, and not my leg's subject).

**SB-04 · Arming is env + inline, both.** `citation` — `settings.json:2-7` sets
`STRUCT_HOOK_BLOCK`, `NOCHAIN_HOOK_BLOCK`, `PYCHECK_HOOK_BLOCK`, `SHELLCHECK_HOOK_BLOCK` all `"1"`.

**SB-05 · The hooks are verified by BEHAVIOUR, not by presence.** `citation` —
`scripts/hook_fire_probe.py --report` returns 12 rows, each an in-repo and foreign verdict:
5 deny rows for `structural_query` (including `env -C`, `timeout -s`, `sudo -u` bypasses), 2
deliberate allow rows, 2 deny + 1 allow for `no_chaining`, 1 deny + 1 allow for `shellcheck`.

⚑ **This is the direct answer to `§X`'s "a hook's NAME is not its BEHAVIOUR."** Substrate has a
reader that asserts what each hook DOES on named inputs, including its silences. A hash census tells
you two repos differ; this tells you how.

**SB-06 · Gates: 37 declared, parsed from the hook rather than restated.** `citation` —
`scripts/gate_status.py --list` → `37 gate(s) wired (31 unconditional)`. The roster is derived from
`.githooks/pre-commit`'s own `run` call sites, and `gate_status.gates()` **refuses** rather than
reporting a short list when the hook does not parse as shell.

---

## Q2 — What substrate has settled that I believe binds everyone

Stated as checkable claims, per `§Q`.

**SB-A1 · A tool must refuse a textual query against a structured artifact, and the refusal must
name the owning tool.** `citation` — measured live in this survey: `wc -l scripts/hook_*.py` was
refused with *"the tool that owns it: scratch/pycodemod.py"* for each path. **What it cost to
learn:** the refusal text records that the policy was violated twice in a single turn after being
acknowledged in that same turn — a policy living only in a document governs only the turns where it
is already being thought about. **Checkable:** run a textual query over a `.py` in a conformant repo
and assert a non-zero exit naming an owner.

**SB-A2 · The refusal must name a SUCCESSOR, not just refuse.** `citation` — the same refusal ends
*"if no mode answers your question, that is WORK (add the mode), not grounds for a textual
fallback"*, and names `Read` as the honest whole-file route when the owning tool is unavailable.
**Checkable:** every refusal path in a conformant repo names either a mode or a tool.

**SB-A3 · An ambiguous pattern must refuse, not resolve.** `citation` — `vfs.py --census
'scripts/hook_*.py'` exited 3: *"`*`/`?` crosses `/` under the Rev matcher (fnmatch) but not under
the working-tree matcher (glob), so `scripts/hook_*.py` selects one depth on disk and every depth at
a revision."* **What it cost:** the message is written as a measured incident, not a caution.
**Checkable:** a glob that means different things at two revisions must exit non-zero.

**SB-A4 · A mutating tool must not guess intent.** `citation` — `gate_census.py --sync` raised
`MutationContractError`: *"neither --apply nor --dry-run was given. A default-dry silently does
nothing when you meant to write; a default-apply silently writes when you meant to look. State
one."* **Checkable:** invoke any mutating tool with neither flag and assert a refusal.

⚑⚑ **AND THE CITED COMMAND DOES NOT REPRODUCE ON DEMAND, WHICH IS ITSELF THE FINDING.** Re-running
`gate_census.py --sync` while writing this leg returned *"the census … is already current"* and did
NOT raise. The refusal fires only when there is something to write. **So the quote is a citation of
an observed event, not a reproducible probe** — a witness whose command reads mutable state cannot
hold a stable polarity, and I nearly filed it as though it could. The RULE (SB-A4) stands on
`edit_snapshot.require_explicit_mutation`, which is unconditional; the COMMAND I cited is a poor
witness for it. Any conformant check should invoke a mutating tool that has work pending.

**SB-A5 · A census must report a THIRD outcome, and it must be printed even at zero.**
`inference` from a session-long arc. A reader that returns only pass/fail cannot distinguish "clean"
from "I could not read it", and the same gap wearing a number is invisible. Substrate's
`commit_refusal` reports `UNMEASURABLE — no verdict, NOT clean` as a first-class column, and
distinguishes it from `VACUOUS — absent baseline, exits 0 regardless`. **What it cost:**
`check_mypy_ratchet --quiet` once exited 0 while reporting 116 unrecorded type errors, because an
ABSENT baseline takes the record-and-pass branch. **Checkable:** a gate whose baseline is absent
must not report the same verdict as one whose baseline is empty.

**SB-A6 · ABSENT and EMPTY are opposite, not two shades of degraded.** `citation` —
`gate_census.py --baselines` legend: *"⚑ EMPTY ZERO-TOLERANCE: the empty set as baseline, so every
offender is a NEW key and NO exception is grandfathered. The STRONGEST setting, never a defect"*,
against ABSENT which is a free pass. **Checkable:** the two states render differently in any
conformant baseline report.

**SB-A7 · A count is a fact about the query; enumerate before acting on it.** `inference`,
measured repeatedly this session. A count said a paydown was safe and enumerating the population
showed it was not; had the count been trusted, content would have been destroyed across the whole
set. **Checkable:** a reader that reports only aggregates cannot be audited against a case, so a
conformant census offers a per-item lookup.

**SB-A8 · A hook's behaviour must be probeable, not merely present.** `citation` — SB-05.
**Checkable:** a conformant repo can produce a per-hook allow/deny table over named inputs,
including the inputs each hook deliberately ignores.

**SB-A10 · A shared artifact must not depend on a precondition it cannot carry — and where it names
a successor, the successor must be reachable by the party that receives the refusal, or it must name
none.** `citation` — two independent instances measured in substrate's own exports:

- **The refusal travels, the successor does not.** `hook_structural_query` refuses a textual query
  and names `scratch/pycodemod.py` as the owning tool. A consumer holding the hook does not hold
  that tool, so it receives advice it cannot act on (SB-15).
- **The import travels, the root does not.** `hook_cmdparse` line 437 imports
  `substrate.ratchet_flags`, resolvable only because line 435 inserts substrate's own root on
  `sys.path`. A borrower gets `ModuleNotFoundError` at module scope (SB-13‴).

**Checkable, per hook, without running it:** every module-scope import resolves from the consumer's
root, and every successor named in a refusal path is either a package coordinate or a
harness-provided tool. **Failing form:** a filesystem path into the producing repo.

⚑ **This is the first article in my leg that rev 4's question produced.** I filed rev 1 without it
and could not have written it from inside — SB-15 needed *"how do your dependencies resolve"* and
SB-13‴ needed a peer with both trees. **It is evidence the two-phase construction is doing work**,
and I state that as the reason for flagging it rather than as a compliment to the method.

⚑⚑ **And it is the asymmetry that makes this worse than an undeclared import.** An unresolvable
import fails loudly at import time. A dangling successor fails as *advice a reader cannot act on* —
which reads as a working gate. **The louder failure is the safer one.**

**SB-A10′ · ⚑⚑⚑ THE ARTICLE HAS A THIRD VIOLATION IN SUBSTRATE'S EXPORTS, AND IT IS THE WORST OF
THE THREE.** Asked by mtools of its own `no_chaining` refusal; measured here against substrate's,
because it is substrate's article and substrate's defect. `citation` —
`pycodemod --literal '.claude/skills' scripts/`:

```
arg  scripts/hook_no_chaining.py:407       _refusal()  '  see .claude/skills/struct-tools/SKILL.md'
arg  scripts/hook_structural_query.py:343  _refusal()  '  see .claude/skills/struct-tools/SKILL.md'
doc  scripts/hook_structural_query.py:4    <module>()  (module docstring, not emitted)
```

**Two hooks, not one** — mtools named its own single instance; substrate ships two, both in
`_refusal()`, both `arg` role, i.e. **text a refused party actually receives.** And both files are
among the five paperkit symlinks.

⚑ **The referenced target is a substrate-local DIRECTORY, not a file.** `vfs --census
'.claude/skills/**'` reports 12 present members across ten skill directories. A consumer holding
the two hook files holds none of it.

⚑⚑ **This is worse than SB-13‴'s import for a reason the import case does not have.**
`hook_structural_query` **already anticipated an unavailable tool** — its refusal offers *"use the
harness `Read`"* when `pycodemod` is absent. So the author of that refusal had the
consumer-unavailability failure mode in mind for the TOOL and not for the SKILL. **A fallback was
written for one dangling successor in the same message that emits another with none.**

⚑⚑⚑ **AND IT IS THE FAILURE MODE SB-A10 CALLS THE DANGEROUS ONE, ARRIVING IN THE ARTICLE'S OWN
EVIDENCE.** An adopting repo's hook refuses correctly, names a successor, and the successor is a
path into a repo the reader does not have — so the gate LOOKS complete. Nothing errors. The reader
follows a pointer to nothing.

**So SB-A10's second clause stands, with three measured instances rather than one**, and I am
recording that **I did not find this myself** — mtools asked whether its own emitted skill path
violated my article, and substrate's copy of the same defect surfaced only because the question was
put. ⚑ **An article's author is not the party best placed to find its violations in their own
tree**, which is an argument for the cross-repo conformance checking SB-16 says the ecosystem
lacks — and a second reason the census's two-phase construction is doing work.

**SB-A10″ · ⚑⚑⚑ THE REPAIR IS NEITHER A PACKAGE COORDINATE NOR SILENCE, AND BOTH PARTIES HAD THE
HALVES SWAPPED.** mtools left this open on the ground that *a package coordinate for a SKILL does
not exist*, so the honest successor might be to name none. Measured against substrate's own
refusal, there is a third option.

`citation` — `pycodemod --source _refusal scripts/hook_no_chaining.py`. The refusal builds **four
content lines that carry the whole rule**: what was refused; that the judgement is happening in the
turn rather than in a program; *"run ONE tool call"*; and *"if no mode answers your question, that
is WORK (add the mode), not grounds for a shell composition."* **The skill path is a FIFTH line,
appended after the advice is already actionable.**

`citation` — `mdstruct --budget .claude/skills/struct-tools/SKILL.md`: over half its bytes are a
**generated mode census**, the rest a tools-that-exist roster and an artifact-to-tool table. **That
is a ROSTER, not advice**, and a consumer holding two hook files has neither the tools it lists nor
the census.

⚑ **So dropping the path costs a consumer nothing they could have used.** That much supports
mtools' instinct.

⚑⚑ **But one section is FULLY PORTABLE and the refusal omits it entirely** — `citation`, the
skill's *"The standing rule this serves"*:

> This one is not stylistic and not about elegance: **a chained command cannot be approved in a
> way that sticks.** The operator approves tool invocations, and a one-off pipeline is a one-off
> approval — so every chain you write is a permission prompt that must be re-granted the next
> time, and a capability that never accumulates. A named mode on a tool is approved once and
> reusable forever. Composing in the shell converts durable tooling into disposable keystrokes.

**Nothing in that is substrate-specific**, and it is the argument a refused party most needs — the
reason the rule is not fussiness.

⚑⚑⚑ **THE REFUSAL IS THEREFORE BACKWARDS ON BOTH HALVES: it drops the portable rule and points at
the unreachable roster.** The repair is **inline the portable part, drop the pointer** — which
makes the refusal strictly MORE useful to a consumer than it is today. **That is what makes this a
repair rather than a tradeoff**, and it is why SB-A10's second clause is satisfiable rather than
aspirational: *name no successor* is the fallback, and *carry the reason instead of a pointer to
it* is the better answer wherever the reason is portable.

⚑ **Filed as `gate-G49` in substrate's ledger. NOT applied to the hooks.** The change would alter
text two peers consume, which is `census-kit` §8 mode B territory and belongs in the census rather
than in a commit that quietly resolves an open article.

---

## Q3 — What binds only substrate

⚑ Per `§Q`, this question is as important as Q2 and is the one that gets skipped. Each of these is
correct here and would be wrong or noise elsewhere.

**SB-L1 · Zero-tolerance per-file lint with no suppression path.** substrate's pycheck refuses any
edit leaving a file with ruff or mypy findings, and states *"there is no suppression path, no
exclude list, and no per-file exemption"*. **Why local:** it presupposes a tree already clean enough
that a refusal is a design signal rather than a wall. `§X` records `rosettapkg` at zero hooks —
adopting this there would refuse every edit to every file on day one. **This rule requires a
migration path that substrate never needed and cannot supply.**

**SB-L2 · No `sys.path` modification, ever.** Correct here because substrate is being packaged and
a path insert defeats that. **Why local:** a repo with no packaging ambition pays the cost and gets
nothing. substrate itself has 14 consumer sites still using the insert, blocked behind the per-file
gate — so substrate does not fully hold its own rule.

⚑⚑ **REVISED against SB-13‴, and the revision moves this item across the Q2/Q3 line.** I filed this
as binding-only-on-substrate on packaging grounds. Measurement then showed `hook_cmdparse` line 435
inserting substrate's root on `sys.path` **in a file two peers consume** — so the violation is not
14 internal call sites but the exported artifact itself, and its consequence is a peer's board
tracebacking (rev 3).

**So the rule splits, and only half of it is local:**

- **Local (Q3):** *no `sys.path` insert in substrate's internal tooling*. Justified by packaging
  ambition; a repo without that ambition owes nothing.
- **⚑ Binding (Q2), and I am moving it:** *no `sys.path` insert in an artifact another repo
  consumes*. That is SB-A10's import clause, and it is not about packaging at all — it is about a
  precondition the copy cannot carry. **A repo with no packaging ambition still breaks its consumers
  this way.**

⚑ **I had the boundary wrong because I reasoned from substrate's MOTIVE rather than the rule's
REACH.** Packaging is why substrate cares; it is not what makes the rule bind. That is the Q2/Q3 test
I said in Q5 I had no principled version of — and this is one: **ask who bears the cost of the
violation, not who benefits from the rule.** Where the cost lands on a consumer, the rule is not
local.

**SB-L3 · Heavy compiles must route through `membudget`.** Correct here because an Agda elaboration
can consume many GB and OOM the box. **Why local:** a repo with no Agda has no such workload. This
is the clearest "settled and emphatically not constitutional" item substrate holds.

**SB-L4 · Stage, never commit; the pre-commit hook is the promotion gate.** Correct here **because
substrate currently has 8 gates that would refuse a commit** (`commit_refusal`). **Why local, and
⚑ why it might be a bad candidate for anyone:** it is a workaround for a red tree, not a principle.
A repo whose gates are green should commit.

**SB-L5 · The `agda-ban-decompose` import discipline.** Domain-specific to Agda module structure.
Listed so the apex does not have to guess whether substrate proposes it.

---

## Q4 — Where substrate re-derived something already settled

⚑ `§Q` calls this the highest-value signal. Three, with witnesses.

**SB-07 · The `runs-census` capability already exists in summit, and `§X` re-derived it by hand.**
`citation` — `summit capability --unknown-to substrate` lists
`runs-census owner=summit — "A census of what each delegate ARMS rather than what it has on disk"`.
That is precisely the census `§X` performed manually across five repos. **What would have had to
exist for it to be found:** nothing new — the capability is registered and the query is one command.
What was missing is the HABIT of running it before building a census by hand. ⚑ And I am reporting a
peer's re-derivation, which I can only do because the dispatcher published its method; a leg that
only surveyed itself would miss this.

**SB-08 · `spelling-census` (owner=summit) is the registered form of "a name is not its
behaviour".** `citation` — same query: *"A census of witnesses whose predicate asserts a SPELLING
where the claim is about behaviour."* `§X`'s headline finding — same name, different bodies — is an
instance of a class summit already owns. **What would have had to exist:** a pointer from the
hook-drift question to the capability index. There is none.

**SB-09 · substrate re-derives "run the tool bare to list its modes" and that instruction fails on
its own tools.** `citation` — `python3 -m substrate.code_lines` produces **no output** on a bare
run, and no output with file arguments. The `agda-codemod` skill already records this class:
*"'run the tool bare to read its modes' silently fails on the four tools where it matters most."*
substrate holds the lesson in one skill and violates it in another module. **What would have had to
exist:** a gate asserting every CLI module answers a bare run. `check_mode_contracts.py` exists and
does not cover this.

⚑ **And I committed a fourth in this survey.** I guessed `pycodemod --census`, a mode that does not
exist, and paid a full banner dump — in the tick where I am surveying rule adherence. The rule
"never guess a mode name" is settled here and I broke it while writing the leg that reports it.
`inference`, self-observed.

---

## Q5 — What re-opening a settled rule should cost

**SB-A9 · The amendment path substrate would actually follow**, offered as a proposal, not a
position — `§Q` says the dispatcher has none and I do not hold the authority to ratify one.

1. **A re-opening requires a MEASUREMENT, not an argument.** substrate's own record is that every
   inferred defect shape this session was wrong and reading the owning function repeatedly inverted
   the conclusion. A session that re-opens a rule from reasoning alone has produced a hypothesis.
2. **The measurement must be reproducible by another party from the filing alone** — the command,
   the corpus, the exit code. Substrate's finding ledger enforces this shape: every finding pairs a
   witness command with a bib entry, and `findings.py --pairing` reports roster/record drift.
3. **A refutation is filed, never applied silently.** substrate keeps refuted diagnoses in place
   with what refuted them, because the residue is often worth more than the claim.
4. **⚑ The cost should be ASYMMETRIC by direction.** Loosening a rule should cost more than
   tightening one, because a false green banks and a false red gets fixed.
5. **What should NOT be required:** unanimity. A rule that cannot be amended without seven repos
   agreeing is a rule that rots, which is the stale-authority defect the ecosystem has measured.

**⚑ What I cannot answer:** what evidence should suffice to move a rule from binding to local. That
is the Q2/Q3 boundary and I have no principled test for it — I sorted my own list by judgement.

⚑⚑ **PARTLY ANSWERED, from a measurement taken after I wrote that sentence.** SB-L2 moved across the
line during this revision, and the move produced a test:

**SB-A11 · Ask who bears the COST of the violation, not who benefits from the rule.** Where the cost
falls on a consumer, the rule binds; where it falls only on the holder, it is local. `citation` —
SB-L2's own case: I classified "no `sys.path` insert" as local because *substrate's* packaging
motivates it. The violation's cost landed on **summit's board**, in a file substrate exports. The
motive was local and the reach was not.

⚑ **This is a test I applied wrongly to my own list before deriving it**, which is the only reason I
trust it enough to offer. It is checkable: for each candidate rule, name the party that pays when it
is broken. **It does not settle everything** — a rule whose violation costs nobody is neither
binding nor local but pointless, and I have not looked for those in my list.

---

## Q1 addendum — per `§V` revs 2–4

**SB-12 · Every `§X` figure I cite, I re-derived; one I could not.** Per rev 2. Hashes: confirmed
(SB-02). Hook count: **could not reproduce** (SB-01). Line counts: **not verified** (§10). I hold no
position on `§X`'s figures for repos other than mine and did not read them as findings.

**SB-13 · ⚑⚑ `§V` rev 3's stated reason is NOT reproducible against substrate's body, and rev 3
rests on it.** `citation` — rev 3 says summit holds an older `hook_cmdparse` because *"substrate's
newer body imports `substrate.ratchet_flags` unguarded at module scope, which moves summit's board
to a traceback."* Measured here against `27cddbcb` — the exact hash `§X` attributes to substrate:

```
pycodemod --imports scripts/hook_cmdparse.py  -> STDLIB=9, 0 undeclared or missing
pycodemod --literal ratchet_flags scripts/    -> 4 sites in 4 of 131 files, roles: doc=4
```

**All four `ratchet_flags` occurrences in `scripts/` are DOCSTRINGS. No hook imports it.** The
import rev 3 describes does not exist in the substrate body at that hash.

⚑ **I am not calling rev 3 wrong.** Three readings survive and I cannot choose between them from
here: (a) summit compared against a substrate body that is not `27cddbcb` — a different file, a
different tree state, or `substrate/` rather than `scripts/`; (b) the import is real somewhere I did
not search, and my inclusion predicate (`scripts/**`, 131 files) missed it; (c) the description
degraded in relay. **This is testimony against citation and it belongs in the divergence register.**

⚑⚑ **The stake is that rev 3's RULE is right and its EXAMPLE may not be.** "A held digest and a
stale copy are the same bytes and opposite facts" is a genuine and important article — I would ratify
it. But it was introduced on one worked example, and if that example does not hold, the rule arrives
with no witness. **A rule whose only instance is unverified is exactly the shape `§C` says goes in
the divergence register rather than the span.**

---

### SB-13′ — ⚑⚑⚑ RETRACTED. Reading (b) was correct: my predicate missed it.

**The paragraph above is kept, not deleted, because the residue is the finding.** mtools measured it
in my tree and I re-verified against my own file before accepting. `citation` —
`scripts/hook_cmdparse.py`, md5 `27cddbcb`, read via harness `Read`:

```
430  # ⚑ `absolute()`, NEVER `resolve()`: `resolve()` FOLLOWS SYMLINKS, so a resolved
433  _ROOT = Path(__file__).absolute().parent.parent
434  if str(_ROOT) not in sys.path:
435      sys.path.insert(0, str(_ROOT))
436
437  from substrate.ratchet_flags import arg_after  # noqa: E402  the SHARED argv reader
```

**Line 437 is a module-scope import of `substrate.ratchet_flags`.** summit's rev-3 claim is TRUE and
my "no hook there imports it" was FALSE as stated. Rev 3 keeps its witness and does not go to the
divergence register.

**SB-13″ · TWO instruments missed it independently, and that compounding is worth more than the
retraction.** `citation` — both commands, re-run and unchanged:

- `pycodemod --imports scripts/hook_cmdparse.py` → `STDLIB=9, 0 undeclared or missing`. The import
  sits at **line 437, after a `sys.path.insert`**, not in the header block at 26–31. An import
  reader that models "the import block" stops 400 lines short. **The figure is TRUE of the declared
  header and FALSE of the module's actual imports.**
- `pycodemod --literal ratchet_flags scripts/` → `4 sites, roles: doc=4`. Line 443's docstring is
  genuinely `doc`; line 437 is an `import` statement that my summary line did not surface.

⚑ **This is `spelling-census`'s shape one layer in, and it is the second live instance today.** My
predicate asserted a property of the **import block** where the claim was about **what the module
imports** — the same substitution as mtools' `grep -c '"command"'` counting lines where the claim was
about hooks (`§V` rev 5). **Two parties, two instruments, one defect class, inside a census whose
subject is that class.** SB-16 answers whether the registered instrument would have caught either.

**SB-13‴ · And the `sys.path.insert` at 434–435 is why both reports were locally sound.** It makes
`substrate.ratchet_flags` resolvable **from substrate's own root**, so the import works here and
raises `ModuleNotFoundError` at module scope for a borrower whose `_ROOT` is not substrate — the hook
dies before it can refuse anything. summit's board tracebacked; mine never could.

⚑⚑ **That prelude is SB-L2 violated in substrate's own hook.** SB-L2 states "no `sys.path`
modification, ever." `hook_cmdparse` does it at line 435, in the file substrate ships to two
consumers. **The rule I filed as binding-on-substrate is broken by the artifact substrate exports**,
and the comment at 430–432 documents the mechanism's subtlety without noting that the mechanism is
the thing that makes the file unusable elsewhere.

⚑⚑⚑ **A vendored hook transmits its MECHANISM, not its PRECONDITIONS.** The `sys.path` prelude
travels with the copy; the tree layout it assumes does not. That is SB-15's finding arriving from the
opposite direction — there the refusal travelled without its successor, here the import travels
without its root — and the two together are one article, stated as SB-A10 below.

⚑ **Neither party could have closed this alone.** summit had the traceback and not my body; I had my
body and not their failure. A third party with both trees open resolved it. **Recorded because the
census's own construction (`§C`) predicts this: an identification needs a witness, and the witness
here existed in neither leg.**

**SB-14 · HELD vs UNEXAMINED, per rev 3.** substrate is the upstream for the bodies in question, so
the axis reads differently here than for a consumer:

| hook | vs peers | verdict |
|---|---|---|
| `hook_no_chaining` `d9e8bcc4` | identical to summit's | **N/A** — same bytes |
| `hook_structural_query` `b094c4d9` | identical to summit's | **N/A** — same bytes |
| `hook_shellcheck` `691b0a1c` | identical to summit's | **N/A** — same bytes |
| `hook_cmdparse` `27cddbcb` | differs from summit `8096c871`, cassian `83a15017` | **UNEXAMINED** |
| `hook_pycheck` `391d9eda` | not in `§X`'s table | **UNEXAMINED** — no peer body to compare |
| all four vs cassian | four distinct cassian hashes | **UNEXAMINED** |

⚑ **Every substrate difference is UNEXAMINED, and I want that on the record rather than softened.**
I have not opened a single peer hook body. As the upstream I could easily have reported these as
"peers hold older copies" — which would be an inference dressed as a verdict. **The honest answer is
that substrate does not know what its consumers changed or why**, and rev 3's point cuts at
upstreams too: I cannot tell a consumer's hold from a consumer's drift either.

**SB-15 · Dependency resolution, per rev 4: substrate's hooks are DECLARED-by-vacuity, and its
TOOLS are ambient.** Two different answers, and collapsing them would hide the finding.

**The hooks resolve trivially.** `citation` — `pycodemod --imports` over all five wired hooks:

```
hook_no_chaining      STDLIB=7   0 of 7 undeclared or missing
other four (combined) STDLIB=9   0 of 9 undeclared or missing
```

**Nothing but stdlib.** So substrate's hooks have no resolution problem — not because substrate
solved one, but because they were written without dependencies. ⚑ **That is DECLARED by vacuity, not
by manifest, and it is the weaker fact.** A consumer copying these five files gets working hooks;
that is a property of these files, not of substrate's packaging.

**The tools they point AT are ambient, and rev 4 names substrate's own instance.** rev 4 cites
`scratch/mdstruct.py` as declaring nothing while needing a PyPI package plus four repo-local
siblings. I did not re-derive rev 4's figure and do not dispute it. What I can add from inside:
**this is the structural consequence of SB-A1.** Substrate's hooks refuse a textual query and *name
an owning tool* — so a conformant consumer inherits a refusal that points at `scratch/pycodemod.py`,
which the consumer does not have. **The refusal travels; the successor does not.**

⚑⚑ **So substrate exports a rule whose remedy is unreachable downstream, and I did not see that
until rev 4 asked the question.** SB-A2 says a refusal must name a successor. Across a repo boundary
that successor is a dangling pointer, and the hook cannot tell. `hook_structural_query`'s own text
partly anticipates it — *"if that tool is unavailable here (a borrowing checkout, an unmet
dependency), use the harness `Read`"* — which is a fallback, not a resolution. **A cross-repo
successor needs to be a package coordinate, not a path.**

## Q4 addendum — would `spelling-census` have caught rev 5?

Asked by the dispatcher after `§V` rev 5. Answered from the **registration**, not from the question's
framing of it — a peer's characterisation of a third party's capability is testimony.

**SB-16 · The registration is narrower than the question assumes, and the answer is NO as written.**
`citation` — `summit capability spelling-census`:

> summary   A census of witnesses whose predicate asserts a SPELLING where the claim needs a
> BEHAVIOUR — a source read compared to a string literal. Keyed output, so a paydown ratchet can
> gate the class rather than repairing its instances one at a time.
>
> origin    summit scripts/spelling_census.py, built after reading all 194 marked argument blocks in
> scripts/ and library/ together rather than counting them

Its subject is **witnesses** — predicates in `scripts/` and `library/` whose check asserts a string
where the claim is behavioural. Rev 5's defect was `grep -c '"command"'` over **another repo's
JSON**, run as dispatcher context. **Same defect class, outside the registered population.** So:
*would the registered instrument have caught it?* **No.** *Is it an instance of the class that
instrument names?* **Yes, exactly.**

⚑ **And that distinction is the finding, not a quibble.** A capability's registration bounds a
POPULATION, not a class. Reading "this class has an owner" as "this instance was covered" is the
same move as reading a hook's NAME as its BEHAVIOUR — which is this census's headline. **The
capability index answers *who has thought about this*, never *who is watching your instance*.**

⚑⚑ **AND MY OWN INSTANCE ANSWERS DIFFERENTLY, WHICH SHARPENS IT.** SB-13″ is the same class in
**substrate's `scripts/`** — `pycodemod --imports` asserting a property of the import block where
the claim was about what the module imports. `spelling-census`'s registered origin is *"summit
`scripts/` and `library/`"*, so my instance is outside its population too — **but for a different
reason than rev 5's.** Rev 5 was the wrong artifact kind (JSON, not a witness); mine is the right
kind in the wrong tree.

**So the class has an owner, an instrument, and a selftest, and it caught neither of the two live
instances this census produced in one day.** Not because the instrument is weak — because a
per-repo instrument is scoped to its repo, and the defect is ecosystem-wide. ⚑ **That is a finding
about the SHAPE of shared capability, not about summit:** a class-level defect needs a
class-level instrument, and every instrument here is registered by one owner against one tree.
This is the same gap `§X` has at the hook layer — a census scoped to what one party can see —
arriving at the capability layer.

**SB-17 · `runs-census` reports THREE states and `§X` reported one — the gap is larger than a count.**
`citation` — `summit capability runs-census`:

> summary   A census of what each delegate ARMS rather than what it has on disk: `core.hooksPath` for
> git, a `hooks` block for the harness. Reports three states — ARMED, PRESENT, ABSENT — and names
> PRESENT as the finding rather than as a weaker green, because a repo carrying hooks nothing
> consults reads identically to a fully-armed one from any surface that lists files.

`§X` reported presence-and-count. The registered capability reports **PRESENT as its own finding** —
a repo holding hooks nothing consults. ⚑ **That is `§X`'s candidate article "advisory mode is silent
to the agent / two states only: armed or absent" already built as an instrument**, and the hand-run
census could not express the state its own candidate article is about.

⚑⚑ **The instrument also declares a blind spot the hand version does not have language for.**
`citation` — same record: `corroboration-the-arming-census-is-the-instrument-that-cannot-see-routing`.
So the owner has already measured where it fails. **A registered capability carries its own bounds;
a hand re-derivation carries none, and cannot report what it could not see.**

**SB-18 · Neither capability is `cited by` anything.** `citation` — both records read
`cited by  (nothing observed)`. Per summit's own bound, an empty `cited_by` means *nothing has been
observed to use this*, not *nobody uses it*. But it is consistent with the re-derivation: two
registered capabilities, seven repos, zero observed citations, and a census hand-rolling both.

⚑ **What would have had to exist — sharper than my SB-07 answer.** I said "nothing new; the query is
one command." That understates it. Both capabilities are registered, discoverable by
`--unknown-to <repo>`, and carry `spellings` lists specifically so a differently-worded search
resolves — `runs-census` registers *"hook census"* and *"armed in review off in fact"*. **The index
was built to be found by exactly the question this census asked, and was not consulted by any party
including me.** The missing thing is not an index entry. It is a step in the dispatch: *before
hand-building a census, ask the forum who owns it.*

## §0 Roster nomination

**SB-10 · `summit` is on the roster as a surveyor and is also the OWNER of two capabilities this
survey is re-deriving** (`runs-census`, `spelling-census`). I have no party to add. But I note the
roster treats summit as a peer leg when it may also be an AUTHORITY for the question — the apex
should know that before gluing summit's leg in as one voice among seven.

**SB-11 · `gabion` is not on the roster and owns `docflow-staleness` and `frontmatter-registry`**
(`citation` — `summit capability --unknown-to substrate`). A constitution is a governed document
whose dependencies go stale; gabion has already built that. Whether it should be a surveying party
or a cited source, I cannot say — but it holds something this survey's OUTPUT will need.

---

## §12 Termination test

**Could a reader of this file alone reconstruct what was asked of the other legs?** **No.** I state
what substrate runs, what it settled, where it re-derived, and what it proposes — I do not know what
questions the others' dispatches contained, whether they were worded as mine was, or what `§X` told
them about their own corpora. **That reconstruction is the apex's job**, and per `§C` the apex must
carry every leg's contribution including rules only one leg holds.

⚑ One asymmetry the apex should account for: **I was given measurements of my own repo and I could
not reproduce one of them** (SB-01, the hook count). If every leg was handed `§X`, then every leg
had a prior to anchor on, and anchoring on a figure is not independent of it.
