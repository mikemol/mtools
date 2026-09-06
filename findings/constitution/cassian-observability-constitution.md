# `CO-` — cassian-observability's leg of the `constitution` census

**Written against `CENSUS-constitution.md` rev 1**, and `CENSUS-BRIEF.md` as it stood
2026-09-06. Measured at cassian `26ee4af`.

## §9 Disclosures, first paragraph as the brief requires

I own and authored the subject under survey: cassian-observability is my repo, its hooks
are mine to change, and four of the eight hook files here are cassian-authored rather than
adopted. **My dispatch differed from the standard form in one way I can see:** it arrived
as a peer message naming the run file and asserting *"The roster is in `§R` and includes
you"* — which is the exact claim the previous run's rev 22 recorded as unmeasured at
dispatch time. I verified it myself (`§R` line 12, `cassian-observability` → `CO-`) before
filing rather than taking it. **Nothing was relayed to me about this census's findings**,
and I have opened no peer leg; `findings/constitution/` contains no other file at the time
of writing. I was told one thing I suspect others were not: nothing. `§X` is stated as
context to every leg.

⚑ **I am also the party whose figures `§X` reports, so my `CO-01` below is a correction to
a measurement about me.** That is a conflict worth naming: a leg disputing the dispatcher's
number about itself is exactly the shape that should be checked hardest, so I give the
reproduction commands and the peer-wide control rather than asking to be believed.

---

## `CO-01` — ⚑⚑⚑ `§X`'s HOOK COUNTS ARE EXACTLY 2× THE TRUE COUNT, FOR EVERY REPO

**Class: citation + inference.** `§X` reports, under *"PreToolUse hooks, by repo
(`.claude/settings.json`, count of `"command"` entries)"*:

> ```
> linux-sources          18
> cassian-observability  18
> ```

**cassian runs 9 hooks, not 18.** Measured by parsing the file the harness parses:

| event | matcher | hook |
|---|---|---|
| PreToolUse | `Bash` | `hook_structural_query.py` |
| PreToolUse | `Bash` | `hook_no_chaining.py` |
| PreToolUse | `Bash` | `hook_shellcheck_wrap.py` |
| PreToolUse | `Bash` | `hook_no_verify.py` |
| PreToolUse | `Edit\|Write\|NotebookEdit` | `hook_shellcheck_wrap.py` |
| PreToolUse | `Edit\|Write\|NotebookEdit` | `hook_tofu_validate.py` |
| PostToolUse | `Edit\|Write` | `hook_tofu_fmt.py` |
| Stop | — | `tools/absence_audit.py` |
| UserPromptSubmit | — | `.claude/hooks/gate-reminder.py` |

**Six PreToolUse, nine total.**

⚑ **The cause is exact and it is not a slip.** Every hook object in the Claude settings
schema carries **two** keys matching the string `"command"`:

```json
{
  "type": "command",
  "command": "STRUCT_HOOK_BLOCK=1 python3 \".../hook_structural_query.py\""
}
```

A textual count matches both. `grep -c '"command"'` over cassian's settings returns **18**;
the parsed hook count is **9**.

⚑⚑ **The 2× holds across every repo with a settings file, which is what makes this a
finding about the INSTRUMENT rather than about cassian:**

| repo | `§X` says | `grep -c '"command"'` | parsed | ratio |
|---|---|---|---|---|
| `linux-sources` | 18 | 18 | 9 | 2.0× |
| `cassian-observability` | 18 | 18 | 9 | 2.0× |
| `summit` | 12 | 12 | 6 | 2.0× |
| `substrate` | 10 | 10 | 5 | 2.0× |
| `paperkit` | ⚑ **8** | ⚑ **16** | 8 | 2.0× |
| `mtools` | 2 | 2 | 1 | 2.0× |
| `rosettapkg` | 0 | — | — | no `settings.json` |

⚑ **`paperkit` is the one that proves the method was not uniform.** Its `§X` figure (8) is
the *correct* parsed count while its grep count is 16 — so five repos were counted one way
and paperkit another, and the table reads as one measurement. **A table whose rows were
produced by different methods, presented in one column, cannot be compared row to row** —
which is the only thing a by-repo table is for.

**Reproduce:** the script is
`scratchpad/census_xcheck.py` in my session dir; its body is four lines — for each repo,
`text.count('"command"')` against `sum(len(e["hooks"]) for … in json.loads(text)["hooks"]…)`.

**Why this matters beyond the arithmetic, and it is the census's own subject:** `§X` says
*"a hook's NAME is not its BEHAVIOUR"* and asks for hashes **because** names mislead. The
same sentence applies one level up: **a structured file's TEXT is not its CONTENT.** The
hashes in `§X` are right — I reproduce all four of cassian's exactly — because a hash reads
bytes and bytes are what a hash is about. The counts are wrong because they read text where
the question was about structure. cassian's routing table
(`.claude/skills/struct-tools/SKILL.md`) exists to route exactly this: a `.json`/`.tsv`/`.md`
question goes to the tool that parses it, never to grep. **The defect arrived in the
census's own context section, in the same document that names its mechanism.**

**Not adjudicated by me:** whether `§X`'s hook NAMES per repo are also affected. I checked
counts only.

---

## `CO-02` — ⚑ `hook_shellcheck.py` IS ON DISK, WIRED TO NOTHING, AND ITS WRAPPER'S REASON IS STALE

**Class: citation.** `§X` lists `shellcheck_wrap` among cassian's hooks, correctly. What
the count cannot show is that **`scripts/hook_shellcheck.py` (627L, `c6a35093`) is invoked
by no settings entry.** `hook_shellcheck_wrap.py` (156L, `793ad83d`) is wired in its place,
and imports it as a library.

⚑ **The wrapper's own docstring states a fact that is no longer true**, verbatim:

> *"`scripts/hook_shellcheck.py` is a SYMLINK into substrate's tree (the shellcheck guard is
> substrate's, adopted so upstream fixes propagate). This repo must not edit substrate's
> code"*

**Measured: it is a copy, not a symlink.** `◆hook-vendoring` replaced every symlink with a
vendored file on the operator's ruling (*vendor, don't symlink*). So the wrapper's
load-bearing justification — *I cannot edit that file, therefore I wrap it* — rests on a
constraint that was lifted, and the wrapper survived the change that dissolved its reason.

**This is the relitigation half of the operator's complaint, in miniature and inside one
repo.** Nothing is broken: the wrapper works, adds no suppression, and delegates. But a
future session reading that docstring learns a false constraint and will reason from it.
**A ruling that changes does not travel to the comments that depended on it.**

---

## `CO-03` — ⚑ THE LOCK DISCRIMINATOR DOES NOT REQUIRE THE SUITE'S RUNTIME, AND `§V` REV 22 OVERSTATES THE DEPENDENCY

**Class: citation + inference.** `§V` rev 22 records that the index lock is this census's
only serialisation, and that the heuristic making it safe *"depended on one number,
transmitted informally, in a message, to some parties and not others"* — `summit` inferred
*live* from *"~2 min old, consistent with a 132s suite"*, while `linux-sources`, lacking the
number, read a live lock as crashed.

**The mechanism rev 22 identifies is real and its remedy is right: that number belongs in the
run file.** But the dependency is narrower than stated, and I have a counter-instance from
the previous census.

⚑ **I hit the same lock, five times, and reached the correct conclusion without knowing the
suite's runtime.** Two discriminators, neither of which needs it:

1. **The mtime ADVANCED between my attempts** — `15355` bytes at `09:50:43`, then the same
   size at `09:54:38`. A crashed process leaves a lock whose mtime is frozen; **a live gate
   rewrites it.** That is a delta over two reads of the lock itself, and it requires no prior
   knowledge of how long anything takes.
2. **`pgrep -af 'git commit'` named the holder** — it printed `linux-sources`' commit with
   its message path in the argv, identifying the session by its own tree. When that returned
   only my own probe, the lock was genuinely gone and my next attempt succeeded immediately.

⚑⚑ **The distinction that matters for the constitution:** summit's heuristic reasons from a
MODEL of the system (*a suite takes 132s, this is 2 min old, therefore live*) and inherits
the model's transmission problem. Mine reads the SYSTEM (*is this file changing; does a
process hold it*) and inherits nothing. **A model-based discriminator must be distributed;
an observation-based one is available to every party at every moment, because the thing it
reads is the thing itself.**

**So the constitutional article I would draft from rev 22 is not *publish the runtime*** —
though that is worth doing and I support it — **but: *a shared-resource discriminator must be
readable from the resource, not from a fact about its user.*** The runtime number is a
property of mtools' suite; if mtools' suite gets slower, every party's heuristic silently
mis-calibrates and nothing announces it. The mtime delta cannot go stale, because it is
recomputed from the lock on every read.

⚑ **Where rev 22 is exactly right and my counter-instance does not touch it:**
`linux-sources` *would have removed a live lock*. That is the failure, and it is a failure
whether or not a better discriminator existed — because **nothing told linux-sources that a
better one existed either.** A method available to everyone that nobody was told to use is,
by this repo's own rule, functionally absent. Rev 22's real finding survives my correction:
*the operational fact every writer needed lived in conversation.* I am only disputing which
fact that was.

## `§Q`-1 — WHAT I RUN TODAY

**Population (brief §3, stated as inclusions):**

```
A  hook invocations parsed from .claude/settings.json          ->  9
B  hook_*.py files in scripts/                                 ->  8
C  git hooks in .githooks/ (armed: core.hooksPath=.githooks)   ->  4
D  gate claims (scripts/check --list)                          -> 42
E  selftest arms                                               -> 322 assertions
                                                       TOTAL   ->  9 + 8 + 4 + 42
```

Exclusions, counted separately: **1** — `scripts/hook_shellcheck.py` is present in B but
invoked by no entry in A (see `CO-02`).

**How the code got here — three mechanisms, all present in one repo:**

| file | md5₈ | lines | provenance |
|---|---|---|---|
| `hook_cmdparse.py` | `83a15017` | 418 | vendored from substrate, **drifted** |
| `hook_no_chaining.py` | `d4ebd0c8` | 682 | vendored from substrate, **drifted** |
| `hook_shellcheck.py` | `c6a35093` | 627 | vendored from substrate, **drifted**, unwired |
| `hook_structural_query.py` | `7442f527` | 605 | vendored from substrate, **drifted** |
| `hook_no_verify.py` | `6fc4e970` | 533 | **cassian-authored**, no upstream |
| `hook_shellcheck_wrap.py` | `793ad83d` | 156 | **cassian-authored**, no upstream |
| `hook_tofu_fmt.py` | `b3a4e9da` | 85 | **cassian-authored**, no upstream |
| `hook_tofu_validate.py` | `16160e2a` | 218 | **cassian-authored**, no upstream |

Against substrate's current copies: `cmdparse` 418L vs 492L, `no_chaining` 682L vs 668L,
`shellcheck` 627L vs 861L, `structural_query` 605L vs 760L. **All four drifted, in both
directions** — cassian's `no_chaining` is 14 lines *longer* than upstream's, the other
three shorter.

⚑ **The drift is REPORTED here, deliberately as a yellow and never a red.**
`scripts/check --only routes` compares each vendored copy against substrate's and emits
`VENDOR-STALE`. Its stated reason, which is a `§Q`-3 answer below: *"a red here would make
cassian's board hostage to substrate's commits, the exact coupling vendoring removes."*
Four `VENDOR-STALE` lines are showing right now and the gate is green.

**Git hooks:** `pre-commit` and `pre-merge-commit` are byte-identical (`a4d8d26f`, 395L);
`commit-msg` (`d260180b`, 85L) binds asserted numbers in a commit message to measurements
the run produced; `post-commit` (`00441acb`, 32L) runs `systemctl --user daemon-reload`.

---

## `§Q`-2 — WHAT I HAVE SETTLED THAT I BELIEVE BINDS EVERYONE

Stated as checkable claims, each with what settled it and what it cost.

**`CO-A1` — a verdict is `$?` taken from the command itself, never read from stdout and
never taken after a pipe.**
*Checkable:* every command substitution capturing an instrument's output takes `$?` within
two lines, unless it carries `--list`/`--claims` (an enumeration by contract). Gated as
selftest `T14`, over a **derived** scan set: every executable file or symlink in `scripts/`
and `.githooks/` — 44 today.
*What settled it:* a commit landed announcing *"selftest 30 assertions"* while the suite was
29 passing and 1 failing. `| tail -2 | head -1` returned a blank line and it was called
green. Two sibling instances the same day, one of which **put a false exit code in a bug
report to another repo**.
*Cost:* the first fix was a blacklist over shell constructs and was defeated by five
counterexamples in one review. It was rebuilt as a **whitelist over actual invocations**.
⚑ **The transferable half is the rebuild, not the rule:** *a blacklist quantifies over every
way to WRITE a hazard, which is not enumerable; a whitelist quantifies over the instrument
captures that actually EXIST, which is eleven and greppable. Choose the side you can
enumerate.*

**`CO-A2` — a verdict string may not assert more than its predicate measures.**
*Checkable per instance, not in general:* the mechanizable slices are gated; the general
rule is a judgement.
*What settled it:* six shipped remedies violated it in one stretch — correct logic, prose
that outran it. A timer being active was reported as *"the collector ran"*; a **failed read**
was reported as *"measured zero"*; an *"exactly one"* verdict enforced only half of it.
*Cost:* four boundary retrospectives running, `operator = self` has **never** caught its own
remedy's prose. The only instrument that has ever caught it is a decorrelated reviewer pass,
which is why they are non-optional here.
⚑ **The in-the-moment test:** *before a green verdict, ask what input would make this
sentence false, and whether the predicate catches that input.*

**`CO-A3` — a gate that is not armed is not a gate, and armed-ness is OBSERVED, never
inferred.**
*Checkable:* `scripts/check --only hook` reports whether `core.hooksPath` is actually set;
`--only routes` runs **both arms** for every deny-guard — armed-hook-denies and
unarmed-hook-does-not — 25 probes today.
*What settled it:* git cannot enable a hook from a commit, so a fresh clone has the file and
not the wiring. A commit once landed announcing a green suite that was red.
⚑ This is the same finding `§X` attributes to linux-sources (*"advisory mode is silent to
the agent… two states only: armed, or absent"*). **Reached here independently**, and I did
not know linux-sources held it until I read `§X` — which makes it a `§Q`-4 entry as well as
a `§Q`-2 one.

**`CO-A4` — a gate must refuse when its tool is absent, and "cannot run" is a THIRD state,
distinct from pass and fail.**
*Checkable:* selftest `T134` asserts that a projector which cannot execute reports
`GATE-BUILD-ERROR` — *"a projector that cannot run is UNKNOWN, not stale"* — and that this
is not the same output as drift.
*Cost:* a check slice reported freshness by running a projector; when the projector itself
errored, the slice's early form would have read the failure as "not stale."
⚑ `§X` lists this as settled *"in both directions one repo apart"* (substrate SKIPPED+0 vs
linux-sources refuses). **cassian holds the refusing side and gates the three-state
distinction specifically**, which is a strictly stronger form than refuse-vs-skip: it
separates *unknown* from *fail*, so a green cannot be manufactured by an instrument that
never ran.

**`CO-A5` — a correction must reach the CONSUMER, not sit beside the claim.**
*Checkable:* `scripts/check --only residue` verifies no superseded form is asserted where
claims acquire force (25 owned claims today); `--only regrounding-pointer` fails if the
session-entry document names anything but the newest boundary.
*What settled it:* this repo's session-entry file asserted *"memory is the binding
constraint"* for weeks after that claim was measured and refuted — and the refutation was
correctly recorded in the charter's Residue the whole time. It was loaded every session.
Separately, a PSI figure in the same file was stale by roughly an order of magnitude and was
**quoted to a peer as evidence during a cross-repo audit whose subject was authorities that
outlive their measurements.**
⚑ **The sharpest form:** *a number in a session-entry document is the least-revised and
most-read thing in a repo.* That is the worst possible combination and almost nothing gates
it.

**`CO-A6` — a projector's artifact must be REGENERATED by the gate, not merely checked
against.**
*Checkable:* `.githooks/pre-commit` walks `host/projectors.tsv`, asks each projector
`--sources`, and for any whose declared source is staged, regenerates and stages the
artifact before the hash is cut.
*What settled it:* the operator's ruling — *"freshness gates should be freshness enforcers,
given they can run as pre-commits"* — after a `--check` gate reddened on a live counter and
was hand-regenerated on **five consecutive work ticks**.
⚑ *A `--check` presumes a human already regenerated and merely verifies they did, which
leaves the treadmill intact. Regeneration-as-a-build-step deletes the human step: staleness
has no window in which to exist.*
⚑⚑ **And it carries a cost I state as part of the article, because a constitution that
hides its costs is advice:** projector correctness becomes **commit-critical** — the
`--check` form refused a bad render, this form writes it. It landed here **six hours ago**
and its first real run caught its own regression, via a selftest arm testing something else
entirely.

---

## `§Q`-3 — WHAT I HAVE SETTLED THAT BINDS ONLY ME

⚑ The run file is right that this is the skipped question. **I answered it wrong the first
time on two of four, and `§V` rev 11 is what caught it.**

> ⚑⚑ **REV 11's TEST, applied here before filing:** *"ask who bears the COST OF THE
> VIOLATION, not who benefits from the rule."* `substrate` filed *no `sys.path` insert* as
> local, reasoning from its own motive; the insert lived in a file two peers consume and the
> cost landed on **summit's board** as a traceback, so the rule split.

**Two of my four split the same way, and the mechanism is identical: I reasoned from my own
motive.** The environmental fact that decides it is one no leg can see from inside its own
repo and which the *previous* census's `§X` supplied — **all seven parties run on ONE
PHYSICAL HOST.** One kernel, one CPU, one memory, one swapfile. Measured while re-checking:
six peer sessions live, host CPU pressure `some avg10=60.95`. **So "a rule about this host"
is not automatically "a rule about only me" — if violating it consumes a shared resource, a
peer pays and never consented.**

⚑ I am stating the correction rather than quietly filing the corrected list, because the
first list is the evidence for how the error happens: *every one of my four reads as local
when you ask who benefits, and two stop reading that way the moment you ask who pays.*

**`CO-L1` — no Docker, ever, and no reasoning about a Docker daemon.**
`/usr/bin/docker` here is the `podman-docker` shim; the runtime is rootless podman + quadlet.
**Local because it is a fact about this host**, not a principle. A repo on a Docker host that
adopted this would be prevented from using its own runtime.

**`CO-L2` — ⚑ SPLITS UNDER REV 11. Two claims were bundled as one, and only one is local.**

- ⚑ **BINDING: a unit on a shared host carries a cap at all.** Who pays for the violation:
  every other party on the box. An uncapped unit takes CPU and memory six peers need, and
  they cannot see it coming or refuse it. **Every running cassian unit IS capped** —
  measured: `cassian-pcie-link-watch` 32 MiB/50 ms, `cassian-uevent-tap` 64 MiB/100 ms,
  `cassian-vmalert` 128 MiB/250 ms. But **15 of 28 unit FILES declare neither `MemoryMax=`
  nor `CPUQuota=`**, against a session-entry document that says *"Every unit still gets
  `MemoryMax=` **and** `CPUQuota=`."* Those 15 are collectors and backup one-shots; none is
  running now, so nothing is unbounded at this moment — but the declaration is the thing
  that survives a restart, and the rule as written is not met by the corpus.
  ⚑⚑ **A MEASUREMENT ERROR OF MINE, CAUGHT AND CORRECTED INSIDE THIS RE-CHECK, and it is
  the sharper half:** I first spot-checked one unit, got `MemoryMax=infinity`, and was about
  to file *"cassian holds a rule that every unit gets a cap and has a live unit that does
  not."* **systemd returns `infinity` for a unit that is NOT LOADED** — byte-identical to
  what it returns for a live uncapped one. The unit was simply not running. *The failure
  value and the success value were the same string, so the read could not distinguish "no
  cap" from "no unit", and only enumerating the running set separated them.*
- **LOCAL: which resource to tune AGAINST.** Measured since boot: CPU stall **53.6%** of
  uptime, memory stall **3.4%**, agreeing across all four PSI horizons; `memory` and `cpu`
  are delegated here, `io` is **not**, so `IOMax=`/`IOWeight=` are no-ops on this box. A repo
  adopting *that* conclusion inherits a claim about **cassian's hardware under cassian's
  workload**. ⚑ It was wrong HERE too until measured — the charter's original S2 said
  *memory is the binding constraint* and it is now in Residue with why. *The generalizable
  part is "measure which resource binds"; the answer is not portable.*

**`CO-L3` — retention is always explicit, on every store.**
Disk is 70% full and journald alone is 2.7 GB. Correct here; on a box with ample disk this is
ceremony that buys nothing. ⚑ **Re-checked under rev 11 and it HOLDS as local** — a store
that overruns fills a disk this repo shares, but the *rule* is a threshold judgement about
this disk's headroom, and a peer on the same box with a different retention answer costs me
nothing. What would be binding is the disk itself, which is `CO-L2`'s shape, not this one.

**`CO-L4` — ⚑⚑⚑ WITHDRAWN AS LOCAL. It is BINDING, and my reason for filing it local was
substrate's exact error.**

*What I filed:* the repo may PREPARE but never APPLY; a human executes and the repo verifies
(A15 co-sign; 34 discharges recorded, each shape-valid and fp-consistent). *My stated reason
for local:* this agent **cannot `sudo`** — verified again, `sudo -n true` exits 1 — so an
apply path is not merely undesirable but unrealizable, and a repo whose agent legitimately
holds root would be crippled by the rule.

⚑ **That reasons from MY MOTIVE, which is the thing rev 11 says not to do.** The test asks
who bears the cost of the **violation**. Measured: **all 25 preparable subjects are HOST
state** — `sysctl`, systemd units, `grub`, the swapfile, `udev`, oomd policy, polkit. Not
cassian's namespace: **the machine's**. Six peer sessions are live on this kernel now.

**So if cassian applied unilaterally, every peer inherits a changed kernel and none of them
consented, or could observe the change, or could refuse it.** The `sudo` fact explains why
cassian *cannot* violate the rule; it says nothing about who pays if it did — and a rule
enforced by an accident of permissions is not the same object as a rule that is right.

⚑ **The binding form, stated so it could be checked:** *an actor that mutates state SHARED
with parties who did not consent must not do so unilaterally, regardless of whether it
holds the privilege.* A repo whose agent holds root is not exempt — it is the case that
needs the rule most, because nothing stops it. cassian's version is enforced by a
permissions accident and that made it look local.

⚑ **What remains genuinely local is the MECHANISM, not the rule:** the specific co-sign
protocol here (`scripts/prepare` → a human runs the block → `scripts/discharge` → the gate
verifies the post-state and records the ledger row) is shaped by this repo's tooling and I
would not propose it. *The prohibition is binding; the ceremony is mine.*

---

## `§Q`-4 — WHERE I RE-DERIVED SOMETHING A PEER HAD ALREADY SETTLED

**`CO-R1` — armed-vs-advisory. Re-derived, and I learned of the peer's ruling from `§X`.**
`CO-A3` above. linux-sources had measured that an unarmed hook exits 0 with no
`permissionDecision` and the harness reads *"allow, nothing to report."* I reached
two-states-only independently and built both-arms probes for it.
*What would have had to exist:* a queryable index of settled rulings with their measurements.
⚑ **`summit` is exactly that index and it already exists** — I am an enrolled delegate and
query it before building. **I did not query it for this.** The capability was in hand and
unused, which is a worse finding than not having it: `a capability you hold and do not
consider is indistinguishable, from inside, from one you do not have`.

**`CO-R2` — the pipe/exit-status rule. Independently derived, expensively, on both sides.**
`§X` records mtools settling it three times in one day. cassian settled it via `A39` (above)
and then built `T14`. Two repos paid full price for one lesson.
*What would have had to exist:* the rule as a **checkable article with its test attached**,
not as prose. ⚑ The test is the transferable artifact — `T14`'s whitelist-over-invocations
construction is worth more than the sentence *"pipes discard exit status"*, which everyone
already believes and still gets wrong.

**`CO-R3` — the structural-query selftest asserted the ORIGIN repo's routing policy.**
Measured this session: cassian's vendored `hook_structural_query.py` was 19/35 red on a clean
baseline. Cause was **not** drift in the usual sense — substrate's upstream routing table
claims 9 suffixes (`.py`, `.agda`, `.jsonl`, …), cassian's claims 3 (`.tsv`, `.md`, `.bib`),
and the **selftest came vendored with the hook**, hardcoding `.py`. It asserted substrate's
policy against cassian's table. The hook was correct throughout.
⚑ **This is the distribution failure and the relitigation failure in one object.** The code
travelled (vendoring worked); the code's *tests* travelled too and carried a policy that was
not this repo's. *A vendored test is a vendored OPINION about what the consumer's
configuration should be.*
*Fix:* the arms now derive their expectations from the live table, so the same suite is
correct in both repos. Mutation-tested — three independent code mutations each turn it red —
because deriving an expectation from the source the code reads is precisely how a suite goes
vacuous.

**`CO-R4` — `membudget`.** Directed repeatedly to genericize it; cassian instead built
`scripts/resource-lease`, a fourth shape of the same idea, and the ecosystem now holds it in
six repos in four shapes.
⚑ I record this against myself: **my generalization has no consumer**, which by cassian's own
rule (`a capability nobody can find is absent`) makes it functionally absent. *A
generalization nobody uses is a weaker contribution than it reads as.*

---

## `§Q`-5 — WHAT SHOULD RE-OPENING A SETTLED RULE COST?

**The amendment path I would actually follow, because it is the one this repo runs:**

1. **A settled rule is a row with a status, and status is monotone.** Corrections rewrite in
   place; **removals are forbidden**. A superseded decision moves to **Residue** *with why it
   was wrong*, and a gate (`--only residue`) refuses its assertion anywhere claims acquire
   force. ⚑ *The reason a rule was abandoned is more valuable than the rule, because the next
   session will re-derive the rule and needs to meet the refutation.*
2. **The evidence required to re-open is a measurement that the CURRENT rule's own predicate
   would call false.** Not an argument, not a preference — an input the existing check
   accepts and should not, or rejects and should not. That bar is met routinely here and it
   is not high; it is just *specific*.
3. **A refutation's charges become the replacement's FIXTURES.** When `A49` refuted `T14`'s
   blacklist with five constructions, the replacement was not accepted until all
   four charges were fixtured, and `--only refutations` reports it (4 of 4 today). ⚑ **This is
   the amendment path's teeth:** you may re-open anything, and the cost is that your
   counterexample becomes a permanent test. Cheap for a real defect, expensive for a
   preference.
4. **A rule nobody can re-open rots into the stale-authority defect** — and cassian has the
   receipt: `CO-A5`'s refuted charter claim sat in the session-entry file for weeks, correctly
   recorded as refuted *elsewhere*. **The amendment path is not the risk; the un-propagated
   correction is.**

⚑⚑ **What I would NOT accept as an amendment path, having watched it fail here:** a document
that states the rule without a test. A projector here named a gate that **does not exist** —
`scripts/check --only playbooks` exits 2, *"no such claim playbooks"*, verified again while
writing this — and re-emitted that false instrument into **all 24 artifacts it generates**,
for as long as the projector had existed. ⚑ The freshness gate was REAL the whole time
(`scripts/docs --verify` reports `gate ok playbooks`), so the artifacts were never at risk;
what was false was the instrument the file told every reader to run. **That is the milder
half of the class and the harder half to notice**, because the artifact really is gated, so
no drift ever surfaces to contradict the sentence — only invoking the cited command
falsifies it, and nothing invokes a command quoted in a comment. Fixed at the source and all
24 regenerated, 2026-09-06. **Prose beside a predicate drifts from it, and the prose is what
gets read.**

---

## `§0` — ROSTER NOMINATION

**`gabion`.** Its governance docflow — frontmatter registries, dependency-staleness
detection, mandatory review notes — was built, then forgotten by its own author for months,
and no other repo learned it existed. That is *this census's subject as a completed case
study*, and gabion is the only party that can report what it cost from the inside. It is not
on `§R`.

⚑ **And a non-party observation, offered because `§R` enumerates parties:** the strongest
finding available here may be an **edge**, not a repo — *"which of your rules did another
repo's tooling force on you without either of you declaring the relation?"* cassian's
`CO-R3` is exactly that (a vendored test carrying an unstated policy), and `§R` has no shape
for it.

---

## `§12` — TERMINATION TEST

*Could a reader of my file alone reconstruct what was asked of the other legs?* **No.** This
file states what cassian runs, settled, localized, re-derived, and would require to re-open —
and it corrects one figure `§X` asserts about every party. It cannot say whether any peer
holds `CO-A1`–`CO-A6`.

⚑ **What it CAN now say, because `§V` rev 11 gave me the test:** two of my four "local"
rules were not local, and I found that by applying rev 11 rather than by reasoning further.
`CO-L4` is withdrawn as local and restated as binding; `CO-L2` splits. **What I still cannot
see is whether the two that survived (`CO-L1`, `CO-L3`) survive because they are genuinely
local or because I stopped looking after two flips** — the test has no stopping rule, and an
author applying it to his own list is the operator whose bias it was written to catch.
**That is the apex's job**, and it is a narrower handoff than the one I wrote first.

## `§10` — COVERAGE

**Read:** `.claude/settings.json` (9 hook invocations parsed, 18 textual matches);
8 `scripts/hook_*.py`; 4 `.githooks/` files; `scripts/check --list` (42 claims);
`host/actions.jsonl` (420 rows); the six peer `settings.json` files **for the `CO-01`
control only** — counts, never content, and no peer leg.
**Unreadable/unparseable:** 0.
**Not searched, and why:** peer hook *bodies* (out of scope — I report my own corpus, and
`§X` already carries the hashes); `docs/jea-transfer.md`, the 3,625-line curriculum archive
(its `T`-findings are a separate label space with its own index, and a rule sourced there
would need the index's supersession banners checked first — a real gap in this leg, stated
rather than glossed).
