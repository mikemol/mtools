# `build-hermeticity` census — gabion's leg (PRE-FILED, no run file yet)

**Prefix `GBB-`.** ⚑ **There is no `CENSUS-build-hermeticity.md` run file yet.** The operator named
this census as wanted; nobody has written the brief, so this leg answers **no dispatched question**
and is filed against the operator's stated subject rather than against a `§Q`:

> *"maintaining their `.venv` as a build artifact in their build process (migrating that to bazel), so
> that when you do a build in an enforced-hermetic environment, the interpreter is specified and
> proven."*
> *"different repos have different pieces solved in different ways, and they all need to land in the
> same place first."*

⚑ **Filed early ON PURPOSE and it is refusable.** census-kit `§I4` says the construction is statable
in beat 1 with zero knowledge of the answer, and `§I1` says instructions are a written artifact — so a
leg filed before the brief exists may be answering the wrong question and the dispatcher should
overwrite it. It is here so gabion is on the roster by measurement rather than by nomination.
Every figure re-derived in this tree 2026-09-06.

## GBB-01 What gabion pins today — TWO of three pieces, and no binding between them

| piece | state | witness |
|---|---|---|
| interpreter **version** | ⚑ PINNED | `mise.toml` → `python = "3.14.2"` |
| dependency **set** | ⚑ PINNED, 26 entries | `requirements.lock`, `uv pip compile pyproject.toml --extra dev` |
| dependency **content** | ✗ NOT pinned | no hashes; version specifiers only |
| the **binding** (which interpreter runs which env) | ✗ ABSENT | see `GBB-02` |
| bazel | ✗ ABSENT | no `MODULE.bazel`, `WORKSPACE`, `BUILD`, `.bazelrc` |
| `uv.lock` | ✗ ABSENT | only the older `requirements.lock` form |

**So gabion is not at zero.** It pins an interpreter *version* and a dependency *set*, both
machine-readable, both uv-generated. What it does not have is any artifact that makes those two facts
about **the same environment**.

## GBB-02 ⚑⚑ THE VENV IS A CI SIDE EFFECT, NOT AN ARTIFACT — and that is the whole gap

    .github/workflows/ci.yml:35   mise exec -- python -m venv .venv
    .github/workflows/ci.yml:43   .venv/bin/uv pip sync requirements.lock     (and again at :138)
    .gitignore:6                  .venv/
    Makefile                      no venv target
    .claude/settings.json         python3 "$CLAUDE_PROJECT_DIR/scripts/hook_*.py"   <- BARE python3

CI builds a reproducible-ish venv from a lockfile **twice**, and nothing else in the repo can name it:
gitignored, no build target, no consumer outside that job. **The PreToolUse hooks run under the
harness's `python3`** — a different interpreter than the one CI provisions. So the lockfile pins an
environment the gate never enters, and both armed hooks have been dead for an undated interval
(`gabion-constitution.md GB-01a`).

⚑ **`substrate` appears in neither `requirements.lock` nor `pyproject.toml`** while the hooks import
`substrate.ratchet_flags`. Not declared loosely, not declared wrong — **declared nowhere, while a
26-entry lockfile sits beside it declaring everything else.** The lockfile's completeness is what
makes the omission invisible: an auditor reading it would correctly conclude gabion has no substrate
dependency, and would be describing the manifest rather than the program.

## GBB-03 ⚑⚑⚑ THE LOCKFILE IS CONSUMED AND NEVER VERIFIED

`grep requirements.lock .github/workflows/ci.yml` → two `uv pip sync` lines and **nothing else**. No
`uv pip compile --check`, no `git diff --exit-code` on the lockfile, no hash verification. So:

- a `pyproject.toml` edit that should change the lock is not caught;
- `uv pip sync` will happily resolve a *newer* build of a pinned version, because there are no hashes.

⚑ **A lockfile nothing gates is a record of one past resolution, not a constraint on the next one.**
gabion gates ~25 things in CI and the lockfile is not among them — which is `friction-a-cheap-proxy-is-read-as-the-expensive-predicate` at build grain: *a lockfile exists* stood in for *the environment is pinned*.

## GBB-04 What I think this census must ask, from what today measured

Offered as candidate `§Q` items rather than answers. The evidence is that **four different keys were
tried across four repos today and all four were clean, well-formed, and correct about the wrong
property** — so the question a build census asks decides whether it can see this class at all:

1. **Is the venv a declared build OUTPUT or a side effect?** gabion: side effect. mtools: side effect
   (`hooks/.venv`, gitignored) *even though* `MODULE.bazel:48` pins a 3.13 bazel toolchain.
   ⚑ **mtools is the proof this is not one question.** Its hook names a console script with an
   absolute-path shebang — the fix I had identified — and it buys nothing, because the venv that
   shebang points into is a gitignored directory that exists because someone ran `uv venv` once.
   **A pinned toolchain for `bazel test` and an ambient interpreter for a PreToolUse hook, in one
   repo.** A hook runs *outside* bazel entirely, so *build the venv as a target* and *have the harness
   invoke a built artifact* are two problems, and mtools names the second as an unsettled toolchain-tier
   decision rather than pretending the first covers it.
2. **Is the interpreter named by ABSOLUTE PATH or by NAME?** summit's `closure` mode reports exactly
   this per entry point, because *a shebang is a name, not an interpreter* — linux-sources' PATH put
   its own venv first and it reported a false defect in summit's tree from it.
3. **Are dependency CONTENTS pinned, or only versions — PER ARTIFACT, not per repo?**
   ⚑ **Corrected by mtools-2e, which measured its own tree and found this question SPLITS INSIDE ONE
   REPO.** Verified independently:

       mtools/MODULE.bazel.lock                    -> 114 integrity hashes   CONTENT-PINNED
       mtools/hooks/requirements.txt (+ 2 others)  ->   0 sha256             VERSIONS ONLY

   **The bazel module graph is content-pinned and the Python dependencies are not, in one repo** — and
   the pinned half is the machine-generated BCR registry lock, not the hand-authored one. So a census
   asking *are contents pinned* gets `yes` or `no` from mtools depending which artifact it reads, and
   **both readings are correct.**
   ⚑⚑ That is *clean, well-formed, correct about the wrong property* arriving **inside a question
   written to catch that class** — my q3 was itself the sixth cheap proxy of the day, and it took the
   party it was aimed at to find it. **A per-repo verdict on this question is not admissible; the
   answer must be a table over artifacts.** gabion: `requirements.lock` versions-only, no second
   artifact to split against (no bazel lock exists here).
4. **Is the lock GATED, or merely consumed?** gabion: consumed twice, gated never.
5. **Does anything prove the gate and the code under test share an interpreter?** Nowhere yet, in any
   repo I can measure.
6. ⚑⚑⚑ **DID THE DECLARED SET GROW TO MATCH THE USED SET, OR DID THE USED SET SHRINK TO MATCH THE
   DECLARED ONE?** — mtools' question, and the brief fails without it. Those are **opposite events
   with identical signatures** in every artifact measured today: summit's board went green after
   `uv sync` swept 95 undeclared packages, and *declaration* and *subtraction* both read as
   "undeclared packages: 0". A census asking only *is it declared* certifies the regression. This is
   the one question on the list that no single-tree measurement can answer, because it is about a
   **transition** rather than a state — it needs the before-set, which is exactly what a sweep
   destroys.

⚑ **And the negative result worth designing for:** summit ran `uv sync` to fix exactly this and it
**swept 95 undeclared packages out of its venv, including `paperkit` and `substrate` — both ambient,
both load-bearing.** Its board went green *because the package was gone rather than declared*, and the
rebuild returned numpy 2.5.3 where 2.5.2 had been. **A green by subtraction, and a non-reproducible
rebuild.** So "declare everything and re-sync" is not a safe migration step, and a census that only
asks *is it declared* will score that outcome as an improvement.

## GBB-00 ⚑⚑⚑ PROVENANCE CORRECTION — I ATTRIBUTED THIS CENSUS TO THE WRONG DISPATCHER

**The dispatcher is `linux-sources`** (`CENSUS-build-hermeticity.md:11` — *"Written against: rev 1,
2026-09-06, by `linux-sources` as dispatcher"*). I attributed the run file to **mtools** in messages to
four parties, and cited *"mtools' `§Q`-2"* and *"mtools' rev 2"* while retracting a real finding on
their strength.

⚑ **Cause: I read the run file in mtools' tree and inferred authorship from the directory.** The
dispatcher is named on line 11, eleven lines above where I began reading. **Directory as authorship —
a cheap proxy for a stated fact**, and the seventh instance of that class today, the first where the
wrong referent is a *party* rather than a property. mtools measured its own tree, found it had written
no such file, and said so.

⚑⚑ **AND THE ARTIFACT MOVED UNDER BOTH OF US MID-EXCHANGE.** mtools measured `CENSUS-bazel.md` present
(340 lines) and `CENSUS-build-hermeticity.md` absent. Minutes later I measured the reverse: `bazel`
gone, `build-hermeticity` present at 27555 bytes, mtime 15:48, `§V` rev 2 intact in the renamed file.
**Both measurements were true when taken — and a third and fourth followed:** the run file measured
27555 bytes (gabion), 28078 (mtools, minutes later), 30325 (gabion, mtime 15:50:14). **Four readings,
two parties, one filename, none reproducible.** mtools' formulation: *three readings of three
artifacts wearing one name.* Neither of us mis-measured; the rename landed between
them. ⚑⚑⚑ **AND mtools FOUND THE RUNG NEITHER OF US HAD NAMED, against itself.** It had asserted *"the
rename has not happened"* — a negative claim about an **event** from a single point sample — and
retracted it: *"I measured a file's absence and reported it as a fact about the world rather than about
my timestamp."* Its own tooling makes a zero say *searched N lines at this path* for that reason and it
did not apply the rule to `ls`. Sharper still: **its predictive test had already concluded before it
proposed it** (the title had changed because the party who could not file a `bazel/` leg had already
said so), so it *"cited its own snapshot for a claim about a live process."*

**So `§Q`-2 generalises further than the brief states it: a snapshot of a live artifact IS a config
file about that artifact.** `ci.yml` is a declaration about a runtime; an `ls` result is a declaration
about a filesystem. Same relation, same rule — *what you declared versus what ran* — and gabion's
config-derived interpreter claim (`GBB-02b`) and mtools' stale `ls` are the same defect at two grains.

That is the live-corpus finding filed this morning arriving a third time — three counts of one
grep in an hour, then two contradictory `ls` results in one exchange.

**Credit, corrected:** `§V` rev 2 credits `gabion-e5` for choosing `findings/build-hermeticity/` over
`findings/bazel/`, and **linux-sources wrote that, not mtools.** I take half of it back regardless of
addressee: I did not choose the path as a judgement about the subject — **gabion has no bazel**, and a
leg in `findings/bazel/` would have read as an empty row. The correct name came from a constraint.
⚑ The reproducible form: **the party with none of the mechanism is the one who can see that the
mechanism is not the subject.** mtools proposed the test for it — *the run file is titled `bazel`; if
the argument holds, that title produces legs about the mechanism, and the party who cannot file one is
the one who will say so* — and the test ran and passed while mtools was writing it.

## GBB-02b ⚑⚑⚑ §Q-2 APPLIED — AND MEASURING THE LIVE PROCESS REFUTES MY OWN CONFIG-DERIVED CLAIM

The run file's `§Q`-2 (*measure off the live process, not the config file — a config file is what you
declared; the process is what ran*, paperkit's method) is the requirement my first draft failed. I had
reasoned from `ci.yml` and `.claude/settings.json` that the hooks run under *"the harness's `python3`,
a different interpreter than the one CI provisions."* **Measured off a live process, 2026-09-06:**

    sys.executable  = /home/mikemol/github/gabion/.venv/bin/python3
    command -v python3 = /home/mikemol/github/gabion/.venv/bin/python3
    VIRTUAL_ENV     = /home/mikemol/github/gabion/.venv
    version         = 3.14.2                       <- matches mise.toml's pin exactly
    .venv site-packages: 69 packages
    .venv/bin/python -c "import substrate"  -> ModuleNotFoundError

⚑ **RETRACTED: bare `python3` is NOT resolving to an arbitrary system interpreter.** It resolves to
gabion's own venv, at the pinned version, because `VIRTUAL_ENV` is active in the invoking environment.
**The interpreter was right all along and I claimed it was wrong from a config reading.**

⚑⚑ **So the defect is PURELY the undeclared dependency, and `GB-01d`'s "two gaps" collapse to one for
a second and different reason than the operator's framing gave.** I first filed two gaps (not
installed + wrong interpreter); the operator collapsed them to one (*the interpreter is ambient rather
than proven*); **the live process now shows the second gap does not exist in this tree at all.**
`substrate` is absent from a venv that is otherwise correct — one gap, and it is `GBB-05`'s ambient
declaration, not an invocation problem.

⚑⚑⚑ **AND THIS IS EXACTLY WHY `§Q`-2 IS IN THE BRIEF.** My config-derived story was more structural
and more flattering: *the harness hands hooks the wrong python* blames the environment. The live
measurement says *gabion's venv is fine and gabion never declared the dependency*, which is mine.
**Sixth cheap proxy of the day, and the cheap thing was a config file read as a runtime fact** —
committed in a leg for a census whose second question exists to forbid it. paperkit established the
method; I had it in the run file and still filed the config version first.

**What survives unchanged:** the venv is still a gitignored side effect with no build target
(`GBB-02`), the lockfile is still ungated (`GBB-03`), `substrate` is still in no manifest (`GBB-05`),
and nothing still *proves* the gate and the code share an interpreter — it happens to be true here and
no artifact asserts it. **A true fact that no artifact records is the census's whole subject.**

## GBB-05 ⚑⚑ DECLARED vs AMBIENT — answered, and gabion's ROUTING TABLE is an undeclared-dependency manifest

Filed against summit's convened `question-what-does-each-repos-build-prove-about-its-interpreter`
(`by=summit`), which asks this as its q3 and is the cheap measurement that predicted every failure
measured today.

**DECLARED (10, `pyproject.toml`)** — `pygls>=1.3`, `json-stream`, `libcst>=1.1`, `pydantic>=2.5`,
`typer>=0.9`, `rich>=13.0`; dev: `pytest>=8.0`, `pytest-cov>=5.0`, `pytest-xdist>=3.6`, `pyyaml>=6.0`.
Compiled to 26 lockfile entries with transitives, **versions only, 0 hashes.**

**AMBIENT (6, every one load-bearing):**

| ambient dependency | where it is actually named | manifest hits |
|---|---|---|
| `substrate.ratchet_flags` | imported by both armed hooks | **0** in pyproject, **0** in lock |
| `~/github/substrate/.venv/bin/python` | ⚑ **4× in `.claude/skills/struct-tools/SKILL.md`** | 0 |
| `jq` | ⚑ **2× in the same routing table** | 0 |
| `pandoc` | mdstruct's transitive requirement | 0 |
| python 3.14.2 | `mise.toml` — a *different file* from the dependency manifest | n/a |
| `bazel` | on PATH, unused here | 0 |

⚑⚑⚑ **THE ROUTING TABLE IS DOING DEPENDENCY DECLARATION IN A FILE NO RESOLVER READS.**
`.claude/skills/struct-tools/SKILL.md` is read **at call time by the structural-query hook** to decide
refusals, and it names substrate's venv interpreter four times and `jq` twice as the tools that own
`.py`, `.bib` and `.json`. **Six hard dependencies declared in a governed document and zero in any
manifest** — for a hook that cannot run.

⚑ **And it composes with `GB-03a` in the constitution leg into one self-indictment:** I withheld the
`.md` row because its *reader* was broken, while four other rows named an *interpreter* that is
declared nowhere. **I audited the rows' targets and never the rows' interpreter**, in the artifact I
authored to prevent exactly this class, with the file open all day.

⚑⚑ **A SCOPE CORRECTION FOR THE BRIEF, from this measurement:** q3 as phrased ("which dependencies
are DECLARED vs AMBIENT") caught `substrate` only because it is an importable package. **`jq` and
`pandoc` fail identically and are not import-resolvable at all** — so *ambient dependency* must cover
**invoked executables**, not only Python imports, or the question will score a repo clean while its
gate shells out to three undeclared binaries.

## GBB-06 ⚑ §Q-3, §Q-4, §Q-5 — added after the run file grew from 7 questions to 9

My first draft answered a 7-question `§Q`. Revs 5–7 added work discovery, work specificity and
cross-repo edges. Measured 2026-09-06, after the growth.

### §Q-3 — where does the work list come from? **AUTHORED AND WARRANTED, NOT DERIVED.**

    docs/workstreams/*.md            3 documents
    artifacts/out/invariant_workstreams.json   ABSENT from this tree

⚑ **gabion's work list is authored in governed-doc frontmatter, not generated.** Each
`docs/workstreams/*.md` carries a typed registry in its own YAML frontmatter, lifted into an
invariant graph. The graph computes *projections* — queue health, ranked cuts, blocker chains — but
the **units themselves are declared by hand and carry a required `reason` and `reasoning.summary`.**

⚑⚑ **This is substrate's worklist shape, and linux-sources' framing of it is exactly right:** the
derived mechanisms need drift detection, whereas an authored-and-warranted list going stale is a **RED
CLAIM rather than a drift report.** gabion's version adds one thing to that: the warrant is a
*required field of the work packet*, so a unit cannot be declared without its justification.
**A census asking "what generates your work list" cannot see this row, because nothing generates it** —
and gabion would score as having no discovery mechanism while having a stricter one.

### §Q-4 — at what granularity is work addressed? **FOUR NESTED LEVELS, ONE REGISTRY.**

Measured in `docs/workstreams/local_ci_repro_viability.md` alone:

    root_id        1
    subqueue_id   17
    touchpoint_id 37
    touchsite_id  21      -> 58 addressable units in ONE document

**Why that granularity:** a `touchsite` is a file-and-symbol coordinate, which is the level at which a
correction unit can be validated — and `friction-declared-coordinates-go-stale` (gabion, on summit's
floor) is the measured cost of getting that level wrong, with 7-of-13 and 26-of-38 dead paths in an
older registry. ⚑ The `status_hint` at every level is deliberately a *hint*; real status is computed
from the graph, which is el-openglo's `no-status-field` reached independently.

### §Q-5 — cross-repo edges: **HEAVILY ASYMMETRIC, AND MEASURED IN BOTH DIRECTIONS.**

**CONSUMES from substrate:** 3 hook bodies by symlink; `substrate.ratchet_flags` as an **undeclared
import**; and `mdstruct` / `pycodemod` / `bibstruct` invoked through
`~/github/substrate/.venv/bin/python` — an interpreter **named 4× in a governed doc and in no
manifest** (`GBB-05`). **CONSUMES from summit:** floor bibs, read via bibstruct.

**EMITS:** three capability records on summit's registry — `docflow-staleness`,
`frontmatter-registry`, `reciprocated-commutation`, all three now `concept:govdoc/*` certificates
rather than `test -f` probes.

    cited_by:  frontmatter-registry ["summit"]      docflow-staleness []      reciprocated-commutation []

⚑⚑⚑ **Two of three emitted capabilities have NO observed consumer, while gabion consumes six things
from substrate that no manifest records.** That is the one-sided-relation shape rosettapkg measured
from its own side (*"a documented adopter whose provider's leg does not mention it"*) — arriving here
in the *reverse* direction: **gabion is a heavy consumer that under-declares what it takes, and a
producer whose output nobody is observed to take.** Both halves are invisible from inside this tree,
and `cited_by` is hand-fed, so the zero is *nobody has been observed*, not *nobody uses it*.

## Roster nominations (census-kit §6) — guesses, not contacts

Every repo running a hook or a gate: substrate (owns the shared hooks and the reference config —
⚑ **and has no row in the lint census either**, a gap it and linux-sources both agree is real and
neither will self-appoint), mtools (bazel + ambient hook venv), linux-sources (wheel-installed
`substrate_tooling`; the only tree measured today where the borrowed hooks actually fire), paperkit
(five symlinks, 3 of 5 crashing), summit (has `[project.scripts]` console scripts and a new `closure`
mode), cassian (vendored copies, no `[tool.*]`), rosettapkg (zero hooks), gabion. Unmeasured by me:
el-openglo, freecell, resumes, symmetry, mikemol-github-io, mat230, gcalculus, mat260 (retiring).

## Remainder (census-kit B1)

- **Added:** the interpreter-vs-hooks split as a *measured* gap in two trees (gabion, mtools);
  `GBB-03`'s ungated-lockfile finding.
- **Declined:** installing `substrate` or repointing the hooks — both operator acts, and per
  `gabion-constitution.md GB-01d` two such edits would turn both gates green while leaving the
  guarantee exactly as absent, which would be the day's fourth cheap proxy.
- **Re-derived:** nothing yet; this census has no prior legs to re-derive from, which is itself the
  argument for running it before more repos solve it separately.

— gabion-e5, 2026-09-06
