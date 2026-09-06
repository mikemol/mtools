# `summit` — deps-build census leg

**Prefix `SM-`.** Filed against `CENSUS-deps-build.md` rev 21, brief rev 1.

## §9 Disclosures, first paragraph as required

I am `summit-1c`, and I own the subject: summit is my own repo and I wrote most of the machinery
described below during the days preceding this filing. ⚑ **My dispatch differed from every peer's,
and the difference is itself a finding I have already filed into `§V`.** The kickoff message told me
*"The roster is in `§R` and includes you"*; I polled `§R` structurally and **it did not**. Summit was
in `§N` as a *nomination*, explicitly undispatched. I declined to file, and `linux-sources-f6`
confirmed the ordering was inverted — an operator ruling on `§N` (*"Summit is up now; ask them"*) had
been given, and the roster was amended to rev 21 **after** the dispatch went out. So my leg is
written against a seat that existed in a message before it existed in the record, which is `§G`'s own
class arriving in the dispatch layer. ⚑ **Two further asymmetries a peer would not have:** I hold no
`§X` context beyond the run file, and I am the only leg whose repo is *also nominated as a dependency
of another leg* (`§N`: summit is "a live, uncacheable build input" to `linux-sources`' `registry`
slice). ⚑ **I was told, and I suspect peers were not, that the freeze is blocked on cassian's
location-hold and not on work** (`§S` rev 18) — that reached me in a peer message, and I record it as
**testimony**, not citation.

⚑ **`§D` applies to this document the moment it is filed.** Every "I" below means *`summit-1c` at
filing time*, a session that will not be reachable when the apex reads this.

## §10 Coverage, stated as a population

Read, with counts, all measured at filing time by running the instrument rather than recalling it:

```
A  summit's own board, all 19 slices (scripts/check)               -> 19 slices
B  python files under summit, excluding .venv                       -> 89 parse, 81 lint-clean
C  the vendored shared bodies (scripts/vendored.tsv)                -> 14 rows, 1 HOLD
D  declared dependencies (pyproject.toml [project] + [dependency-groups])
                                                                    -> 7 runtime, 2 dev
E  the floor, as the engine sees it                                 -> 408 reports, 23 asks
F  registry records                                                 -> 76 (20 delegates, 51
                                                                       capabilities, 5 services)
G  paperkit projects in-tree (paper.toml with a declared root)       -> 3
                                                            TOTAL   -> the above
```

⚑⚑ **THESE FIGURES WERE RE-MEASURED IMMEDIATELY BEFORE FILING, AND FOUR OF THE SEVEN HAD MOVED.**
As first written they read `85 parse`, `12 rows`, `407 reports`. Between writing and committing, two
more shared bodies were vendored (`pycheck_compose`, `pycheck_syntax` — see `SM-08`), a friction was
filed, and I wrote two probes. ⚑ **The corrected `89 parse` moved AGAIN while I was correcting it**,
because the probe verifying my own commit form is itself a `.py` under summit.

⚑ **This is not tidiness; it is the census's own `§F` at the level of the figures.** *A filing is an
artifact, not an event* — and a count written at drafting time is a recollection by the moment it is
committed. **A leg surveying a live tree cannot hold a still population**, and the honest form is to
state when the count was taken rather than to imply the tree stopped. Every figure above was
re-derived by running the instrument during the commit turn, not carried from the draft.

⚑ **Corrected BEFORE the freeze roster accounts this leg, deliberately.** `§D` rules that legs are
not to be amended once accounted, because *rewriting a filed leg after the accounting is amending
the record behind it*. `§S` still reads `dispatched, not yet filed` for summit, so this window is the
last one in which correcting a figure is a revision rather than a violation.

**Not searched, and why:** peers' legs and `CENSUS-deps-build-ANALYSIS.md` (§2 embargo, and the
companion is embargoed until the freeze); summit's git history beyond `git log` for the antecedent
probe (§6 asks for origins, not a history census); `~/github`'s other 30 repos (§Q says survey
yourself). **Unreadable/unparseable: 0** — every file in populations A–G was read by a tool that
reported a count, and no read failed. ⚑ **One population I could not enumerate honestly is named in
`SM-11`.**

## §12 Termination test

*Could a reader of this file alone reconstruct what was asked of the other legs?* **No.** `§Q`'s ten
items are visible here only as the shape of my answers, and my `§N` nomination answer is about who is
missing from a roster this file does not reproduce. Reconstructing the question set, the span, and
who else holds what is the apex's job.

---

## `SM-01` — Dependency declaration: one file, two tiers, and the tiers mean different things (`§Q`-1)

**citation** — `pyproject.toml`, verbatim:

> ```toml
> dependencies = [
>     "json-stream>=2.3.2",
>     "libcst>=1.9.0",
>     "panflute>=2.3.1",
>     "pydantic>=2.5",
>     "pygls>=1.3",
>     "rich>=13.0",
>     "typer>=0.9",
> ]
> ```

Seven runtime, floating lower bounds, pinned in `uv.lock` (uv-generated, committed). Two dev
(`mypy>=1.13`, `ruff>=0.8`) in `[dependency-groups]`.

⚑ **The two tiers are not "needed" versus "nice".** The comment above `dependencies` states the
rule this repo runs on: **the venv is for the BORROWED READERS, not for summit.** Summit's own
modules are stdlib-only, because paperkit runs `cmd:` checks as subprocesses under a default-deny
`clean_env` where no venv is active — so **a dependency present at the terminal and absent inside the
gate is worse than one simply absent**: it works by hand and fails in the only run that gates.

⚑⚑ **Six of the seven are not summit's dependencies at all — they are gabion's**, taken whole
because `library/witnesses/govdoc.py` imports gabion's real governance module rather than
reimplementing its predicates. **inference:** a consumer that imports a peer's live tree inherits
that peer's entire runtime closure, and no manifest anywhere records that relation.

## `SM-02` — The interpreter is pinned in a second file, and the two pins are different claims (`§Q`-1)

`mise.toml` pins `python = "3.14"`; `pyproject.toml` declares `requires-python = ">=3.11"`.

⚑ **Collapsing them would reproduce a defect summit had just filed against a peer.** The floor is
what *summit's own code* requires (it genuinely runs on 3.11); the mise pin is what the *development
environment* needs to import gabion's tree. **citation**, `pyproject.toml`:

> `# Raising this to >=3.14 would assert that summit's modules need 3.14, which is false`

**The pin is provisional and says so in the file**, quoting the operator: *"for the time being."* It
tracks a peer's undeclared requirement — see `SM-03`.

## `SM-03` — A peer's declared floor was unsatisfiable by three of the versions it admits (`§Q`-1, `§Q`-2)

**Measured 2026-08-31.** gabion declares `requires-python = ">=3.11"` and its source references
`ast.Interpolation` — a node CPython added in **3.14**. So the declared floor admits three
interpreter versions that cannot import the package, and **the failure is invisible from any tree
running 3.14**, which is every tree where gabion's own suites pass.

⚑ **It surfaced only behind another defect, and each fix exposed the next.** `ModuleNotFoundError:
json_stream` → install it → `ast.Interpolation` → pin 3.14 → `ModuleNotFoundError: pydantic`. **Three
unrelated defects behind one UNAVAILABLE**, each invisible from in front of the one before it.

⚑⚑ **The repair was to stop reading tracebacks and read the declaration.** After two one-package
rounds I installed gabion's whole `[project] dependencies` set. **inference, and I think it
generalises:** *a dependency list built by repeated failure records the ORDER OF DISCOVERY, not the
requirement*, and it terminates only by accident.

Filed as `friction-a-declared-version-floor-is-not-the-one-the-source-requires`.

## `SM-04` — Dependency discovery: three mechanisms, and the implicit ones are where the failures are (`§Q`-2)

| what | how it is discovered | who notices when it breaks |
|---|---|---|
| declared packages | `uv sync` against `uv.lock` | uv, loudly |
| the paperkit engine | `scripts/engine.py` resolves `PAPERKIT` / `PAPERKIT_ENGINE` / `PAPERKIT_HOME`, else a sibling checkout | the `where` mode, and every slice that refuses on an absent engine |
| the vendored shared bodies | `scripts/vendored.tsv`, sha256 per file | the `vendored` slice |
| ⚑ **peer trees at fixed relative paths** | **nothing** | ⚑ **nothing until it crashes** |

⚑⚑ **The fourth row is the finding.** Summit reaches `../substrate/scratch/pycodemod.py`,
`../substrate/scratch/mdstruct.py`, `../gabion/src`, and `../paperkit/tools/bibstruct.py` — four
peer trees, by relative path, none declared anywhere a manifest can read. **Measured today:
paperkit moved `bibstruct.py` from `paperkit/paperkit/tools/` to `paperkit/tools/` and summit's
`edges` slice went red with `no such file`.** The routing table names the old path; nothing derives
it.

⚑ **Implicit dependencies I can enumerate, per `§Q`-2's prompt:** `shellcheck` on `PATH` (via a
mise shim); `pandoc` as a system binary that `mdstruct` shells to and **which is in no lockfile on
either side**; `git` for the `modes` and `ledger` slices; `mise` itself, which the `interpreter`
slice invokes.

## `SM-05` — ⚑ EVERY MISE SHIM ON THE MACHINE WAS A DANGLING SYMLINK, AND THREE SLICES WENT RED FROM IT (`§Q`-2, `§Q`-4)

**Measured 2026-09-01.** ~170 mise shims — `python`, `uv`, `node`, `cargo`, `java`, `bazel`,
`pytest`, `shellcheck` — each hardcoded `/snap/mise/203/bin/mise`, a snap revision snap had replaced
with 207 then 209. **Every shim was dangling.**

⚑ **The damage was silent and selective**, which is why it is a census finding rather than an
incident: everything invoked through a login shell kept working, because `PATH` also carried the real
installs. The breakage appeared **only where the environment is stripped** — and summit's `routes`
probe deliberately runs hooks under `PATH=/usr/bin:/bin`, which is the arm that saw it.

⚑⚑ **One dangling symlink presented as three independent instrument failures**: `routes` reported
`hook_shellcheck` armed-but-returning-no-decision, the paperkit gate failed on
`concept:instrument/hooks-armed`, and the witness failed. **The hook was behaving exactly as
designed** — announcing itself inert and failing open because its dependency was unreachable.

⚑ **And the repair reproduces the defect one revision later**: `mise reshim` repointed all ~170 at
`/snap/mise/209`, a revision rather than `/snap/mise/current`. **inference:** this is the dual of
`SM-06` — a *pinned path* fails when the file moves; a *floating alias* fails when the name is
repointed. Neither is safe alone.

## `SM-06` — A venv pins an ALIAS, and three clocks drift apart with nothing recomputing any (`§Q`-3)

⚑ **Venvs do not vendor python.** `.venv/bin/python` was stored as a link to
`.../mise/installs/python/3.14/bin/python` — an alias to `./3.14.5`; uv does the same with
`cpython-3.14-linux-x86_64-gnu`.

When the alias moves: the venv runs a **new** interpreter, `site-packages` still holds C extensions
(`pydantic-core`, `libcst`) compiled against the **old** one, and `pyvenv.cfg`'s `version_info` keeps
reporting the version captured at **creation** — which is the field tools read.

⚑⚑ **The instrument built to measure the interpreter was blind to it BY CONSTRUCTION.**
`scripts/slices/interpreter.py` compares `mise which python` against `.venv/bin/python`, and **both
sides dereference the same alias**, so the comparison is satisfied whatever it points to. It read
green across the entire episode.

⚑ **And the first witness written to catch it PASSED against the live defect**, because it called
`resolve()` — measuring where the alias points *today* rather than the link as *stored*, which is
what a later install re-points. Corrected to `readlink()`, then armed both ways.

⚑ **`--copies` is the near-miss and not the escape.** uv exposes no `--copies` at all (its
`--link-mode` governs package installs). The stdlib's `python -m venv --copies` copies the **binary**
— three real 32 MB files, measured — but `pyvenv.cfg` still names `home`, so the copied interpreter
finds its **standard library** in the tree it came from. **The binary is vendored and the stdlib is
not.**

## `SM-07` — Acquisition: vendored, not symlinked, on a ruling — and the cost is measured in both directions (`§Q`-3, `§Q`-9)

Summit holds 12 shared bodies from substrate as **real copies with recorded sha256**, not symlinks.
**citation**, `scripts/vendored.tsv`:

> `# ⚑ VENDORED RATHER THAN SYMLINKED, on the operator's standing advice: a symlink`
> `# crosses a VCS boundary, so a peer's UNCOMMITTED edit is executable here at write`
> `# time.`

⚑ **Both halves of the trade are recorded, which is what makes this a decline with a reason
(`§Q`-9) rather than a preference.** The same write-time reach that made an in-flight peer
regression redden summit's board **is what let `--only routes` catch that regression in minutes,
while the owning repo's selftest structurally could not.** Vendored, an upstream fix does not arrive
at all — **detection moves from immediate to opt-in**, which is why the `vendored` slice exists and
why a stale copy is a RED rather than a note.

⚑⚑ **What was vendored was never a committed upstream state, and the manifest says so rather than
glossing it**: at copy time substrate's `git status` read `??` for several of these files. **These
digests pin a WORKING TREE, not a revision.**

## `SM-08` — ⚑⚑ A SHARED BODY IMPORTED A PACKAGE ONLY ITS OWNER HAS, AND TOOK THE WHOLE GATE DOWN (`§Q`-4, `§Q`-7)

**Measured today, 2026-09-06, during this filing.** Substrate's `hook_cmdparse.py:437` reads
`from substrate.ratchet_flags import arg_after` — **unguarded, at module scope**. Summit's board went
from 19 slices to a **traceback**. `substrate/scratch/bibstruct.py:48` does the same with
`substrate.bib_parse` and took the `edges` slice down separately. A witness written to measure it
found **two more** — `hook_no_chaining` and `hook_shellcheck` — that the board could not report
because `routes` crashed before reaching them.

⚑ **The consequence is the worst state this ecosystem names:** *a hook that raises on import ALLOWS
every command after it* — and **the slice that measures arming could not run either**, because it
imports the same chain. Armed in review, off in fact, **with the instrument that would say so taken
down by the same import.**

⚑⚑ **The principle is already written in the file beside the one that violates it.**
`hook_structural_query` guards its own `substrate` import in try/except — **citation**:

> *"a borrowing repo has no `pycodemod` to retire, so the honest degradation is 'no retirement
> verdict here', never a crash that takes the whole gate"*

⚑ **And a borrower can neither take this drift nor decline it**, which is why it is filed as an ask
rather than a hold-and-forget: the same change carries a **real security fix** — `env -C /tmp grep`,
`timeout -s KILL 60 grep` and `sudo -u nobody grep` each **bypassed every hook** routing through
`programs()`, because the flag-skip loop read a flag's *operand* as the program. Summit is holding
the prior digest and therefore **running without that fix**, recorded as a cost accepted in the
hold's own reason.

## `SM-09` — Hermeticity: what the build reaches that it does not declare (`§Q`-4)

⚑ **The gate that passes by NOT RUNNING is the case `§Q`-4 asks for, and summit has hit it three
times**, each time in a different instrument:

1. **A hook whose dependency is absent fails OPEN and says so once on stderr** — correct design, and
   it means an absent `shellcheck` reads identically to a clean tree to anything that only checks the
   exit code. `--only routes` exists to require `permissionDecision: deny` back, so a hook that is
   merely noisy cannot certify.
2. **Three `govdoc/*` witnesses ERRORED through fourteen hours of green boards** on a missing
   `json_stream`, while the `capabilities` slice excused them as *"gated elsewhere, run by another
   slice"* — **and no slice ran them.** A deferral is a claim about a runner, and nothing checked the
   runner existed.
3. **`FLOOR.md` is generated, ungated, and was twelve days stale** — 95 KB produced only when the
   engine's projector runs against the floor, **and nothing runs it**. The cause was an exclusion
   inheriting more than it was drawn for: `floor/` gates red by design, so the `gate` slice carves it
   out, and **the carve-out was drawn around the VERDICT and silently carried the PROJECTION CHECK
   out with it.**

⚑⚑ **How summit knows: `env -i`.** **citation**, `CLAUDE.md`:

> `Verify with env -i .venv/bin/python library/concepts.py --list, never from an interactive shell,`
> `whose ambient path is the thing that hides it.`

## `SM-10` — Build design: there is no build. There is a board, and it is discovered rather than declared (`§Q`-5)

Summit has **no build graph, no cache, and no remote execution** — and that is a design position, not
an absence. What exists is `scripts/check`: **19 slices, each one file, discovered from
`scripts/slices/`**. Adding `slices/foo.py` *is* the whole act of adding a slice; no list is edited.

⚑ **Nothing is cached, deliberately.** Every slice recomputes from the tree on every run, because
**this repo's governing rule is that nothing records status** — an ask is OPEN exactly when its check
exits non-zero, recomputed every run. **A cache is a recorded status with a shorter half-life.**

⚑⚑ **The cost is real and I state it rather than defend it:** a full board takes minutes, most of it
subprocess spawns, and it is run dozens of times a session. **`§X` says the binding constraint on
this host is CPU.** So summit's design *converts the machine's scarcest resource into the property it
values most*, and it does so without measuring what that costs. **inference:** I do not know whether
that trade is correct; I know it was never priced.

**On the shared executor (`§X`):** summit is **not** on BuildBuddy and has no Bazel. `§X` says the
difference between parties on that config and parties not on it is *"a finding, not an error to
hide"* — so: **summit has nothing to submit to a remote executor**, because it has no unit of work
larger than a subprocess.

## `SM-11` — Test design: there are no tests. There are witnesses, and the difference is falsifiability (`§Q`-6)

⚑ **A test in summit is a `--selftest` that must prove the check can SEE what it looks for.**
**citation**, `CLAUDE.md`:

> `A scan whose all-clear has never been shown to differ from its found-something is not a
> measurement.`

Every slice carries a T-arm and an **F-arm**, and the F-arm is the one that matters. Measured
consequences, each of which is a `§Q`-6 answer:

- **A gate that only ever catches other people is a gate nobody has tested.** Three of summit's gates
  caught *summit* in one session. **The contrast is measured**: paperkit's 21 boundary suites were
  green for their entire existence **and could not fail**.
- **The linter caught a tautology in one of my T-arms** — `same == same`, PLR0124 — which exercises
  no code path the slice depends on. *A T-arm that cannot fail is the same defect as an F-arm that
  cannot fail, and easier to write by accident.*
- ⚑⚑ **A witness of mine PASSED against a live defect** (`SM-06`) because it measured the
  dereferenced target instead of the stored link.

⚑ **The population I cannot enumerate honestly** (`§10`): **I do not know how many of summit's 19
slices have F-arms that have ever fired on a real defect rather than a synthetic one.** I know
several have; I have not censused it, and *"I checked and found none"* is a count of what the query
could see. **Naming it rather than estimating it.**

## `SM-12` — Gate design: five armed hooks, and ⚑ YES, THEY HAVE FIRED (`§Q`-7)

| gate | when | what it reads |
|---|---|---|
| `hook_structural_query` | PreToolUse | a routing table: is a TEXTUAL tool aimed at a STRUCTURED artifact |
| `hook_no_chaining` | PreToolUse | shell composition where one tool call belongs |
| `hook_shellcheck` | PreToolUse, Edit/Write too | what the shell MEANS, not its shape |
| `hook_pycheck` | Edit/Write | ruff + mypy over the file **as it would be after the edit** |
| `hook_scratch_probe` | PreToolUse | ⚑ the only hook summit WROTE: a `.py` Write outside the repo |
| `.githooks/pre-commit` | commit | the full board + the ledger's monotonicity |

⚑ **`§Q`-7 asks whether a gate has ever fired. Measured, during this session alone:** the chaining
hook refused six of my commands; the structural-query hook refused four; `hook_pycheck` refused
**eleven** edits, three of which were real defects I would otherwise have shipped (a guessed symbol,
a tautological T-arm, an undefined name). **A gate that has never refused anything is a
configuration, not a gate** — these are gates.

⚑⚑ **ARMED IS A THIRD STATE, NOT A SECOND.** `PRESENT` (on disk, unarmed) reads identically to
`ARMED` in review and refuses nothing. **citation**, `CLAUDE.md`:

> `ADVISORY IS NOT A WEAKER GUARD, IT IS NO GUARD.`

And **verification is by FIRING, never by reading `settings.json`** — `--only routes` feeds each hook
a real violation and requires `deny` back, with an F-arm that re-runs the same violation with the
arming variable absent, so a hook that is merely noisy cannot certify.

## `SM-13` — ⚑ WHAT I RE-DERIVED (`§Q`-8) — the census's own highest-value question

Four, and I rate the first two as defect reports about the shared object:

1. **`vendor_hooks.py --diff`, built today.** The manifest header has always ended *"Regenerate with
   `--apply` after reviewing the upstream diff"* — and the tool had **three modes, none of which
   showed a diff**. So the instruction routed its reader to `diff`, which summit's own hook refuses
   over a `.py`. ⚑ **A documented precondition with no mode behind it is an instruction to break a
   rule**, and the rule held: four files sat drifted while the decision waited on a review nothing
   could produce.
2. **A note-tail parser, THREE times.** `library/witnesses/report.fields()` owns the `note` grammar;
   `slices/convened.py` and `modes/ask.py` had each re-derived it. ⚑ **The type checker is what
   surfaced it**, not review: with `bib.parse` honestly typed, `.split()` on a possible list is a
   finding, and *a type error over a duplicated parser points at the duplication*.
3. **`stubs/` for paperkit** — because paperkit ships no `py.typed` and no stubs. Substrate had
   already built `stubs/paperkit/bib.pyi`; I did not know until I went looking, and mine is
   differently shaped because summit imports `bib` bare where substrate imports `paperkit.bib`.
   ⚑ **Two repos wrote stubs for one engine, in different shapes, neither knowing.**
4. **`scripts/slices/interpreter.py`** — nothing in the ecosystem measures whether a venv is built
   from the interpreter its config pins.

## `SM-14` — What I declined, with reasons (`§Q`-9)

- **Symlinking the shared hooks** — declined for `SM-07`'s reason; the cost is recorded in the same
  file.
- **`[[tool.mypy.overrides]]` as relief** — ⚑ **declined today, on an operator ruling that the bar is
  universal.** Summit carried **four** override blocks, each with a careful comment explaining why
  its case was special. **inference, and it is the sharpest thing I learned this week:** *four
  careful explanations for one prohibited move is what a repo deciding the bar is not universal for
  THEM looks like from inside.* Replaced by `stubs/`, which is **checkable** — a stub is a claim
  `stubtest` can refute; an override is unfalsifiable. ⚑ **My first stub was wrong and mypy said so
  within seconds** — which is the entire argument.
- **`warn_return_any = false`** — I added it and the operator refused it: *"we don't want `Any`.
  Don't override that."* **Following the report instead found a real bug in a peer's code** (a guard
  testing `_RETIRED` while the calls name `pycodemod_retired`, which the `except` branch never
  binds).
- **`.python-version`** — written and deleted. It names a **version**, and the two interpreters that
  diverged in `SM-06` shared theirs. ⚑ *A guard that cannot express the fact it was added to pin is
  protection in appearance only.*

## `SM-15` — What binds me (`§Q`-10) — ⚑ typed, not ranked, per rev 9

**The binding constraint is that summit's instruments and its subjects are the same objects, so a
defect in a shared body takes down the instrument that would report it.**

It is not CPU (though `§X` says the host's is), and not the board's runtime. It is that **today, one
unguarded import in a peer's file made 19 slices into a traceback** — and the slice whose job is
reporting that hooks are armed was itself unable to load. Every other constraint I have is
recoverable by running something; this one removes the ability to run the thing that would tell me.

**Type:** a *reflexivity* constraint, not a throughput one. ⚑ Per rev 9 this must not be summed or
averaged with another leg's answer.

## `SM-16` — Roster nominations (§0, brief) — ⚑ one name, and it is not a repo

**On the six already in `§N`:** I hold no independent evidence for `earley`, `freecell`,
`el-openglo` or `gabion` beyond what `§N` records, and saying more would be relaying. `gcalculus` and
`summit` I can speak to: both are real, and `§N` already carries them.

⚑ **The party I would add is `paperkit`, and it IS on `§R` — so my nomination is not a party but a
CAPACITY nobody was asked for.** No leg was asked *"what does another repo's build depend on that
you own and did not tell them?"* Measured today: **paperkit moved `bibstruct.py` and summit's `edges`
slice went red**, with nothing on either side declaring the relation. paperkit cannot know who reaches
into its tree by relative path, and I cannot know when it will move.

⚑⚑ **So the index may be short in a dimension `§R` cannot express**: `§R` enumerates *parties*, and
the missing thing is an *edge*. **inference:** a roster of surveyors computes a span over what each
party holds; it computes nothing over what each party's holdings depend on. That is `§Q`-2's implicit
dependencies at the census's own level.

## `SM-17` — Antecedent probe (§6), for the artifacts cited above

⚑ **Every artifact I cite was created within the last three weeks**, and I checked rather than
assumed: `scripts/vendored.tsv`, the `interpreter` and `concepts` and `lint` and `modes` and
`deferrals` slices, `stubs/`, and `vendor_hooks.py --diff` all postdate 2026-08-25. The oldest
load-bearing artifact is `CLAUDE.md`'s "ask the tool, never the file" rule and the
`hook_structural_query` that enforces it — **adopted from substrate, not authored here**, which is
`§Y`'s consolidation trap in miniature: a `git log` in summit attributes to summit an enforcement
layer another repo built.

⚑ **The one antecedent I could not resolve:** `scripts/vendored.tsv`'s own header records that the
files it pins were **untracked in substrate at copy time**, so `git log --all` in the owning repo
returns nothing for them. **There is no origin witness available to me for the shared bodies summit
runs**, and I state that rather than substituting a date.
