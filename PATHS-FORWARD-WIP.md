# Outstanding WIP, for the 10-minute tick to re-derive against

⚑ THIS FILE IS A SEED, NOT A ROSTER. Every tick re-derives its queue from the tree —
`./blockers.sh`, `git log`, `git status --short`, `ListAgents`, `bazel test //...`. What
is written here is what a tick would otherwise have to reconstruct from a lost context,
and a symbol that survives a tick without being re-measured is an unrefreshed default.

Written 2026-09-10 by `mtools-27`. HEAD at writing: `9a97ed8`. Tree clean.

## The standing constraints (not the tick's to lift)

- `findings/CENSUS-deps-build-ANALYSIS.md` is EMBARGOED to surveyors pre-freeze.
- In `findings/CENSUS-deps-build.md` a pre-freeze surveyor reads §V, §S, §G and §D ONLY.
- Do NOT read peer legs in a census's leg directory until that census's freeze.
- Do NOT amend a filed leg of your own.
- Do NOT resume the per-case-target work (`collect_check.sh`, `CASES.txt`).
- The subagent sweep of peer BUILD-generation machinery stays held as testimony, unread.
- A peer cannot lift an operator's hold, and you cannot lift one for a peer.
- Never `--no-verify`. Commit with an EXPLICIT PATHSPEC — the index is shared.
- Do NOT expand the ratchet baseline. Lowering it is an operator decision.

## Open items, with what makes each blocked or ready

### ⟐FENCE-WARRANTS — CLEARED at `750cedd`, kept for what measuring it cost

⚑⚑ CLOSED. Nine sites derived (not the six recorded here), 33 warrants transcribed (not
27), `fence/rubric.tsv` written, sections verified by the gate's own diff. The entry
stays because three of its corrections are the reusable part, and a cleared item deleted
takes its measurements with it.

`.githooks/pre-commit` line ~403 read `for dist in hooks mdstruct ratchet`. `fence` was
not in it, so its test functions carried ZERO warrants and the 1:1 ledger never looked.
⚑ The gate was CORRECT OVER THE WRONG SET — the mis-named-population defect, in the gate.

⚑⚑⚑ AND THE WARRANT TARGET WAS THREE DIFFERENT NUMBERS. The gate counted `^def test_`
anchored at column 0; every fence test is a CLASS METHOD, so the harness counted **0**
and a ledger of zero warrants against zero functions is 1:1 and PASSES. Measured:
**0** by the gate's predicate, **33** methods, **45** pytest-collected cases. The "27" in
this file matched none of them — it came from an early pytest run and was carried across
ticks as ready work. ⚑ A figure with no stated provenance, in the seed, for several ticks.

⚑⚑⚑ I CARRIED THIS AS *BLOCKED, ALREADY ASKED* AND HAD NEVER ASKED IT. Flagged in prose
three times, never once through `AskUserQuestion` — the exact failure the tick prompt
names: *do not carry one as blocked without having actually asked it*. The operator
caught it by reading this file. ⚑ A claim about my own past action, unverified, wrong.

ANSWERED 2026-09-10: **derive the list from the filesystem, and write all 27 warrants.**
So this is TOP OF QUEUE and no longer blocked.

⚑⚑ THE SAME HAND-WRITTEN POPULATION IS IN THE TESTS TOO — `hooks/tests/test_bar_fires.py`
carries `for dist in ("hooks", "mdstruct", "ratchet")` at two sites. The arm that would
catch the gate's omission has the identical omission. Fixing only the gate leaves that.

⚑ AND DERIVING THE POPULATION EXPOSES A SECOND GAP: the loop also requires `rubric.tsv`,
and `fence/` has none (hooks, mdstruct, ratchet all do — measured). So fence needs BOTH
`warrants.bib` and `rubric.tsv` before a derived loop can pass.

The predicate is already used by `blockers.sh`: a directory with a `pyproject.toml`.
Measured: four match — hooks, mdstruct, fence, ratchet.

⚑⚑⚑ AND THE SCOPE IS SIX SITES, NOT ONE. `for dist in hooks mdstruct ratchet` appears at
FOUR sites in `.githooks/pre-commit` (lines 207, 340, 403, 670) and TWO in
`hooks/tests/test_bar_fires.py`. The warrant loop is only the one I happened to notice.
⚑ TWO OF THE GATE'S SITES RUN PER-VENV CHECKERS, so deriving them was blocked on
`fence/.venv` existing at all — which is why bootstrapping it surfaced the undeclared
`ruff`. Operator ruled: derive all six and bootstrap the venv. The venv is bootstrapped
and ruff is declared (`d8ee60b`); THE SIX SITES ARE STILL HAND-WRITTEN.

### ⟐TWO-RESOLVERS-DISAGREE — NEW 2026-09-10, measured, unresolved

⚑⚑⚑ EACH DISTRIBUTION HAS TWO LOCKS AND TWO RESOLVERS, AND THEY DISAGREE ON THE SAME
DECLARATION. `uv sync` resolves `pyproject.toml` into `uv.lock` (what the gate's per-venv
checkers run); `uv pip compile --group dev` writes `requirements-dev.txt` (what bazel's
`pip.parse` stages). MEASURED on `hooks`, same machine, same pyproject, same minute:

    uv sync            installed  ast-serialize==0.11.1
    uv pip compile     wrote      ast-serialize==0.9.0

⚑ NOT HAND-EDITABLE INTO AGREEMENT. Editing either file to match the other would make a
resolver's output a hand-written figure — the defect this tree removes everywhere else.
The operator ruled to TRACK `uv.lock` everywhere and accept it as the venv's declared
input; that is done, and it makes both locks declared rather than making them agree.

⚑ WHAT WOULD SETTLE IT: whether `pip.parse` can consume `uv.lock`, or whether one
resolver can produce both artifacts. Do not assume the divergence is harmless —
`ast-serialize` is a mypy transitive, so the two substrates may run different mypy
behaviour on identical source.

⚑⚑⚑ INVESTIGATED 2026-09-10, FROM SOURCE. `pip.parse` accepts a `uv_lock` label
(`extension.bzl`, added 2.2.0, not experimental): *the uv.lock file will be used as the
primary source for package metadata.* So one resolver CAN feed the graph — **for the dev
hubs only.**

⚑⚑ IT CANNOT SERVE THE SHIPPING HUBS, and the reason is in the implementation rather
than the docs. `_parse_uv_lock_json` (`private/pypi/parse_requirements.bzl:171`) iterates
`uv_lock["package"]` — EVERY package in the lock, with no group selection. MEASURED:
`ratchet/uv.lock` carries **28** package entries against a shipping lock of **0** runtime
deps and a dev lock of **12**. The lock is the UNION. Feeding `<dist>_deps` from it would
put pytest, mypy and ruff into what a consumer installs — the exact over-admission the
two-hub split in `MODULE.bazel` exists to refuse, argued there explicitly.

⚑ SO THE AVAILABLE FIX IS HALF THE ONE I DESCRIBED. The four `_dev` hubs can take
`uv_lock` — carrying the test runner is their whole point. The four `_deps` hubs keep
`requirements.txt`. The operator chose "point pip.parse at uv.lock" on my description of
it as a clean single-source fix; it is only that for half the hubs, and the other half is
not a defect to fix but a distinction to keep.

⚑ TWO THINGS THE READ TURNED UP THAT A DOCSTRING WOULD NOT HAVE: `toml_decode` is
REQUIRED alongside `uv_lock` and `_parse_uv_lock_json` fails without platforms
configured; and there is a `git_struct` branch reading `pkg["source"]["git"]`, so the
git-sourced `paperkit` survives that path — which was a live risk worth checking rather
than assuming.

### ⟐UPSTREAM-DOCSTRING-LIES — NEW 2026-09-10, measured, affects what may be claimed

⚑⚑⚑ `parse_requirements`' OWN DOCSTRING PROMISES A CHECK ITS CODE RETURNS BEFORE
REACHING. It reads: *If provided, the function will use the uv.lock file as the primary
source ... and perform a consistency check against requirements files if both are
provided.* MEASURED at `private/pypi/parse_requirements.bzl:89-100`: when `uv_lock` and
`toml_decode` are both set it returns `_parse_requirements_with_uv_lock` IMMEDIATELY, and
`requirements_by_platform` is consulted only to derive platform names. NO CONSISTENCY
CHECK RUNS.

⚑ THIS SESSION'S RECURRING SHAPE, IN UPSTREAM CODE: a plausible reading pointing at the
wrong subject. Believing the docstring would have had this repository report a
cross-check between `uv.lock` and `requirements-dev.txt` that the build never performs —
and report it as a REASON the two locks are safe to keep.

⚑ CONSEQUENCE FOR ANY TICK TAKING THE `uv_lock` WORK: adopting it for the dev hubs does
NOT buy a verification that the two locks agree. It buys ONE SOURCE for those hubs. If
agreement between `uv.lock` and `requirements-dev.txt` is ever asserted, it must be
measured here, not inherited from that sentence.

### ⟐VENV-AS-BUILD-ARTIFACT — BUILT 2026-09-10, all four distributions, and what it cost

⚑⚑⚑ **`//:venv.bzl` LANDS THE DIRECTION.** `venv_from_hub` is called once per distribution —
hooks, mdstruct, ratchet, fence — and each produces `bazel-bin/<dist>/.venv/bin/python3`. Measured
on all four: interpreter runs `3.13.13`, own package imports, full suite collects (370 / 124 / 43 /
45, matching the gate's own counts). `//hooks:test_venv_artifact` asserts it continuously: 7
functions, 22 cases, F-armed.

**The population is derived at every level.** `all_requirements` from the hub's generated
`requirements.bzl` (12 packages for hooks_dev, 13 the day one is added, no edit); the distribution
list from `*/pyproject.toml`, which is the rule `blockers.sh` and `test_bar_fires` already use.

⚑⚑ **THREE DEFECTS THE RULE SHIPPED AND MEASUREMENT CAUGHT — recorded because each is a shape,
not a typo.**

1. **`short_path` vs `path`, and a well-formed link to nothing.** The first draft computed
   `bin/python3` from `short_path`. An EXTERNAL file's `short_path` begins `../` — runfiles put
   other repositories beside the main one — so the common-prefix walk compared a workspace-relative
   path against an escape sequence. Result: a relative symlink resolving into `bazel-out/`, naming
   no file. **The target built green.** Only running the interpreter caught it. Measured by printing
   all four values during a build rather than reasoning about which to use:

   ```
   link.short_path   = hooks/.venv/bin/python3
   link.path         = bazel-out/k8-fastbuild/bin/hooks/.venv/bin/python3
   interp.short_path = ../rules_python++python+.../bin/python3      ← LEADING ../
   interp.path       = external/rules_python++python+.../bin/python3
   ```

   Same shape as the `sys.path` finding at `8221131`, one layer down: **a path that exists as a
   string and not as a file.**

2. **A guessed label suffix.** The first BUILD call wrote `dev_requirement("pytest") +
   "_extracted"`. Reading the generated `requirements.bzl` shows the accessors are
   `requirement`/`whl_requirement`/`data_requirement`/`dist_info_requirement` and **none** for
   `extracted_whl_files` — the guess named a label that does not exist. Caught by reading the
   source, not by the error. The `:pkg` → `:extracted_whl_files` rewrite now happens once inside
   the macro, so a wrong guess is wrong in one place rather than four.

3. **An arm asserting a property of an environment the environment denies.** The control arm
   carried *"deliberately NOT skipped — it reads the source tree, which is present wherever pytest
   runs"*. The sandbox has no source tree; the arm failed with `no directory under
   /execroot/.../runfiles carries a pyproject.toml`. It now carries the same guard as its siblings.

⚑ **AND ONE BOUND ON THE RELOCATABILITY CLAIM, found when an F-arm's control failed.** The venv
relocates **as a subtree, not as a lone directory** — the relative link climbs six levels expecting
the execroot's shape, so copying only `.venv` breaks it. That is the link working correctly. An
honest move carries the venv and the interpreter together at their relative offsets; done that way,
it runs after the move.

⚑ **`test_bar_fires` REFUSED THIS FILE'S FIRST DRAFT AND WAS RIGHT.** `Path(__file__).resolve()`
follows a runfiles symlink back out to the author's checkout — the escape `.bazelrc` documents.
The root is now derived from the working directory instead.

**Still open under this symbol:** `grade.py:110` still hardcodes `dist/".venv/bin/python3"` as a
HOST path, and `test_grade.py` still symlinks the host venv into its sandbox. The artifact now
exists to point them at; pointing them is the next step and is what closes
⟐GRADER-INTERPRETER-UNDECLARED.

### ⟐VENV-AS-BUILD-ARTIFACT — background: the direction, and how the route was chosen

⚑⚑⚑ *"All projects in this repo should be constructing their .venv the same way — as a
build artifact. This should be a trivially-templatizable thing."* Set 2026-09-10, and
ABSENT FROM THIS FILE FOR TWO TICKS while the file claimed to be the queue's seed.

⚑ IT SUBSUMES OTHER ENTRIES RATHER THAN SITTING BESIDE THEM. ⟐TWO-RESOLVERS-DISAGREE
dissolves if the venv is built rather than `uv sync`-ed — there is no second resolver.
⟐UNDECLARED-HOST-INPUTS shrinks, because the gate stops reaching a host path no rule
produces.

MEASURED, so a tick does not re-derive it:

- The BUILD files DELIBERATELY avoid the venv (`imports = ["src"]`, resolved by runfiles
  layout) — *"runs these witnesses with no venv at all."* So this is ADDITIVE: nothing in
  the graph starts depending on it.
- The venv has THREE non-bazel consumers: `.githooks/pre-commit` (⚑ 14 `.venv/bin` lines when
  re-measured 2026-09-10, not the 13 recorded here and repeated into the cron prompt — and the
  count was the wrong instrument anyway: those lines are not all *uses*. Three were fail-open
  guards and one is the refusal itself. See ⟐GATE-FAILS-OPEN.),
  `preflight.sh` (7 sites), and the interactive dev loop. All reach `<dist>/.venv/bin/…`
  as a host path no rule produces.
- The repeated shape is exact across all four distributions — same `[dependency-groups]`,
  same tracked `uv.lock`, same `bin/{ruff,mypy,python3}` contract. Four identical
  instantiations of one macro.

⚑⚑ THERE IS NO `py_venv` RULE. I asked the operator whether to *bump to a version with
`py_venv`* and they decided on that description; MEASURED against the actual releases,
it does not exist at 1.0.0 OR at 2.3.3 — checked `//python`, `//python/bin` and
`//python/uv` BUILD files directly. Re-asked with the correction; the ruling stands: bump
anyway (done, `50cb2c2`), then build the rule.

⚑⚑⚑ THE ROUTE IS DECIDED AND IT IS NOT uv: **build from the pip hubs.** Operator ruled
2026-09-10 after both options were measured.

⚑⚑ **RE-ASKED AND RE-RULED 2026-09-10, after measuring that rules_python already builds a
per-target venv** (below). The operator was given three options — use what bazel already builds
and inject the interpreter; build the whole-distribution venv anyway; or do both in sequence — and
chose **BUILD THE WHOLE-DISTRIBUTION VENV**. So the duplication of `venv_runfiles.bzl` is a known,
accepted cost, not an oversight: a per-target venv cannot be activated by a developer, and the
three non-bazel consumers above all reach `<dist>/.venv/bin/…`.

⚑ WHY uv WAS RULED OUT, measured both arms: `uv sync --offline` SUCCEEDS against a warm
cache (full venv, correct interpreter, `ruff==0.16.6`) and FAILS with an empty
`UV_CACHE_DIR`, naming the exact wheel URL it could not fetch. The control is what makes
the first arm mean anything — it proves the offline run used the CACHE rather than
silently reaching out. So uv is offline-capable only if the wheels are already local,
which a network-denied bazel action cannot assume; and `//python/uv` is marked
*EXPERIMENTAL: may be removed without notice*, while `python/uv/private/lock.bzl` turns
out to REGENERATE A LOCKFILE rather than materialise a venv — a different job.

⚑⚑ AND THE HUBS ALREADY STAGE EVERYTHING. `@<dist>_dev//<pkg>:extracted_whl_files`
exposes each wheel UNPACKED — measured on `@hooks_dev//ruff`: `site-packages/…` plus a
real `bin/ruff`. No installer to reimplement, no uv at build time, nothing experimental,
and every input already declared in `MODULE.bazel`. The venv becomes a VIEW over inputs
bazel already has.

⚑ THE GRADER IS THE FORCING CONSUMER, and this is why the direction is a precondition
rather than a parallel task — see ⟐GRADER-INTERPRETER-UNDECLARED below.

#### ⚑⚑⚑ rules_python ALREADY BUILDS A VENV PER TARGET — measured 2026-09-10, and the operator ruled anyway

`venv_runfiles.bzl` + `site_init_template.py` construct `_<target>.venv/bin/python3` for every
`py_test`/`py_binary`. That is what `sys.executable` names inside an action. So a
whole-distribution rule DUPLICATES construction that already exists — the ruling accepts that cost
deliberately, because a **per-target** venv is not activatable and *"every project constructs its
`.venv` the same way"* means one per DISTRIBUTION.

⚑⚑ **AND THE PER-TARGET VENV WORKS FROM OUTSIDE ITS ACTION, ONCE `RUNFILES_DIR` IS SET** — worth
recording because the failure mode is a trap, not an error. Invoked bare it reports
`ModuleNotFoundError: No module named 'pytest'` **while `sys.path` visibly contains the pytest
site-packages directory.** Both are true: `_find_runfiles_root()` falls back to walking up from
`_bazel_site_init.py`, lands one directory short (`bin/hooks` rather than
`bin/hooks/test_grade.runfiles`), and every dependency entry becomes a well-formed path to
**nothing**. Python skips nonexistent `sys.path` entries silently.

```
as it appeared in sys.path : exists=False   .../bin/hooks/<hub>/site-packages
under the runfiles root    : exists=True    .../bin/hooks/test_grade.runfiles/<hub>/site-packages
with RUNFILES_DIR set      : pytest 9.1.1, mikemol.hooks.grade imports
```

⚑ *"The path is right there in `sys.path`"* is the plausible reading; the subject is a **string**,
not a directory. Add it to the tally.

#### ⚑⚑ THE ASSEMBLY IS MEASURED END-TO-END, BY HAND, BEFORE ANY STARLARK

A rule written on an untested assembly is an explanation. Assembled in the scratchpad from the
staged hubs — symlinked site-packages, relative `bin/python3`, hand-written `pyvenv.cfg`:

```
ARM 0 control   runs: 3.13.13
ARM 1 packages  pytest 9.1.1 (also ruff, mypy)
ARM 2 dist      mikemol.hooks.grade imports
ARM 3 pytest    20 passed   (real hooks tests, tests/test_payload.py)
ARM 4 MOVED     runs AFTER MOVE — the build-artifact property
ARM 5 F-arm     panflute refuses
```

⚑⚑⚑ **ARM 4 IS THE ONE THAT MATTERS AND IT DEPENDS ON ONE BYTE OF DESIGN.** `bin/python3` must be
a **relative** symlink (`../../toolchain/bin/python3`). An earlier probe established that
`pyvenv.cfg`'s `home` is INERT — breaking it entirely changed nothing — and that the absolute
`bin/python3` symlink is the real dependency. A venv that cannot move is not a build artifact.

⚑ **AND THE CLOSURE MUST COME FROM `deps()`, NOT A DIRECTORY SCAN.** The probe scanned
`external/rules_python++pip+hooks_*` and found **39 directories: 2 with no `site-packages`** (the
hub aliases `hooks_deps`/`hooks_dev` themselves) and the rest **duplicate pairs** — a short alias
and a long platform-tagged name resolving to the same wheel. 29 top-level entries linked. The scan
worked only because duplicate names collide harmlessly; a rule must take
`deps(@<dist>_dev//<pkg>:pkg)` so the population is derived from the graph rather than from a glob
that happens not to hurt.

### ⟐MODULE-RUFF-CLAIM-STALE — NEW 2026-09-10, measured, a FALSE recorded measurement

⚑⚑⚑ `MODULE.bazel` ARGUES FOR ITS `http_archive` ON A PREMISE THAT NO LONGER HOLDS. It
states that ruff must be fetched as an archive because *rules_python STAGES ONLY
`site-packages`. The wheel's `bin/ruff` is dropped, so the installed package is a Python
shim whose `find_ruff_bin()` looks for a binary that is not there.*

MEASURED at 2.3.3 via `bazel cquery '@hooks_dev//ruff:extracted_whl_files' --output=files`:

    …/bin/ruff                                    <- STAGED
    …/site-packages/ruff-0.16.6.dist-info/…       <- and site-packages too
    …/site-packages/ruff/_find_ruff.py

and `file` on that path reports `ELF 64-bit LSB pie executable … stripped` — a real
binary, not the shim the comment describes. ⚑ The positive control is in the same
listing: `site-packages/` IS staged, so the query is not simply returning everything.

⚑⚑ THE PREMISE HELD AT 1.0.0 AND THE BUMP AT `50cb2c2` INVALIDATED IT, and nothing
noticed — a recorded measurement going stale inside a load-bearing comment is worse than
no comment, because a reader spends it as evidence. ⚑ TWO SEPARATE ITEMS: the comment is
false NOW and should be corrected regardless; whether the `http_archive` is therefore
REDUNDANT is a further question nobody has measured, and removing it on this evidence
alone would be acting past what was established.

### ⟐GRADER-INTERPRETER-UNDECLARED — CLEARED 2026-09-10, and one of its two claims was mine and false

⚑⚑⚑ **THE INTERPRETER IS NOW A DECLARED FIELD.** `Runner.interpreter: Path`, defaulting via an
empty-path sentinel to exactly what the old code computed, so no existing caller regrades — what
changed is that the fallback is now *stated* rather than being the only possibility. `run()` passes
it to `subprocess`; four arms pin it (declared value kept, default unmoved, declared interpreter
actually reaching subprocess, and never the string `"None"`), each shown to fail before the fix and
for the right reason.

⚑⚑ **AND THE NULLABLE VERSION WAS A HOLE I ALMOST SHIPPED.** First draft typed it `Path | None`
with the default resolved in `__post_init__` — mypy-clean, and still leaving `str(None)` able to
produce the literal `"None"` as an argv element. That is not an error: it is a path that does not
exist, so every arm would grade UNREACHABLE and the suite would report *nothing is falsifiable*
rather than *the grader was misconfigured*. Same shape as the two path findings above. Typed `Path`
with an empty-path sentinel instead, and pinned by its own arm.

⚑⚑⚑ **THE SECOND CLAIM BELOW WAS FALSE AND I WROTE IT.** The paragraph read: *"`test_grade.py`
SYMLINKS THE HOST VENV into its sandbox fixture — reaching out of the hermetic tree."* Measured:
`_venv()` derives from `sys.executable`, so **under bazel it names the ACTION'S OWN staged venv**,
and `//hooks:test_grade --config=remote` reports **21 passed on the executor**, where no host venv
exists to reach. The symlink is not an escape. It reads like one — `.venv` in a fixture, pointing
somewhere outside `tmp_path` — which is exactly why it went unchecked across several ticks and
into the cron prompt as established fact. **A claim about an escape needs the same arm as any
other claim.** What was genuinely wrong is that the fixture *relied on the path convention*; the
suite now routes every sandbox Runner through `_runner()`, which passes `interpreter=` explicitly,
so it exercises the path it recommends.

**The original entry follows, kept for what it got right.** `hooks/src/mikemol/hooks/grade.py`
built `dist / ".venv/bin/python3"`. Two problems, and the operator named the second:

⚑ THE SANDBOX CRASHED THE GRADER ON A MISSING INTERPRETER, in the very arm asserting it
distinguishes *could not run* from *ran and failed*. I fixed it with an `OSError` guard —
which makes the grader TOLERATE an absent interpreter without making one PRESENT. Operator:
*this is why you're supposed to have the .venv as a build artifact; then you know precisely
the interpreter you'll have because you built it.* Graceful degradation of an input the
graph should supply is the shape `external` was retired over.

⚑⚑ AND THE GRADER'S CLAIM DEPENDS ON IT. Its product is *run this test in a known
environment and see if it flips*. If the environment is whatever the host happens to have,
A FLIP IS NOT ATTRIBUTABLE — a test could go red because the subject changed or because the
interpreter differs. paperkit's `content_sensitive` exists to separate exactly that, and it
can only mean something when the environment is fixed by construction.

⚑ ~~ALSO UNRECORDED UNTIL NOW: `hooks/tests/test_grade.py` SYMLINKS THE HOST VENV into its
sandbox fixture — reaching out of the hermetic tree at the boundary the sandbox enforces.~~
**WITHDRAWN, see the correction at the head of this section:** the symlink target is derived
from `sys.executable` and under bazel names the action's own venv. 21 passed on the executor.

### ⟐GATE-FAILS-OPEN — NEW and CLEARED 2026-09-10, the gate broke a rule it states about itself

⚑⚑⚑ **`.githooks/pre-commit` REFUSES a commit when `ruff`, `mypy` or `python3` is missing from any
distribution, saying *"a skip here would report green over a check that never executed"* — and then
sixty lines later guarded three checks with `if [ -x <tool> ]`, which SKIPS SILENTLY.**

Measured, both populations derived from the file rather than typed:

```
refusing loop covers   ruff mypy python3      × every dist in $_dists (*/pyproject.toml)
guarded blocks         mdstruct/.venv/bin/python3   ×2  — REDUNDANT, the loop already refuses
                       ratchet/.venv/bin/mikemol-ratchet — NOT COVERED, a real hole
mikemol-ratchet lives in   ratchet/ only   (absent from fence, hooks, mdstruct)
```

So an absent `mikemol-ratchet` silently dropped the **preview-debt ratchet** — the check that has
refused most often here — and the commit reported green. That is substrate's
`check_scratch_runtime.py` defect, which the harness union refuses **as a shape**, reproduced in
mtools' own gate.

⚑ **AND THE ABSENCE PATH HAD NEVER BEEN EXERCISED.** Every guarded tool exists on this host, so the
guards had only ever taken their true branch. An armed-looking check whose refusal arm has never
run is exactly what the suite exists to catch — and nothing was catching it.

**Repaired:** two guards deleted as redundant, the third replaced by a real refusal (written as a
plain `if`, not a one-element `for` — shellcheck's SC2043 is right that the latter reads as a bad
expansion). `//hooks:test_bar_fires` now derives both populations and refuses any `if [ -x ]` guard
on a tool no refusal covers.

⚑⚑ **THE ARM PASSED VACUOUSLY ON ITS FIRST RUN AFTER THE REPAIR, AND THAT IS THE FINDING ABOVE THE
FINDING.** With every guard removed the guarded set is empty, so `assert not unrefused` is trivially
true: green over a property nobody is checking. It now *also* requires the refusals it credits to
exist, so a gate that deletes its `mikemol-ratchet` refusal fails even with no guards left.
F-armed both ways against a mutated copy — control passes, guard-reintroduction refuses,
refusal-deletion refuses via the second assertion.

⚑ **`re.findall` RETURNS `list[Any]`** and this distribution refuses `Any` in an expression — 20
mypy errors, the same leak that made a `dataclasses.fields()` arm unusable one commit earlier. The
answer is annotating each result, never widening the config.

### ⟐POLL-RUF201-POPULATION — CLEARED 2026-09-10, and the repair was to DERIVE rather than extend

`blockers.sh`'s RUF201 line printed `for d in hooks mdstruct ratchet` as the command to measure the
preview paydown. `fence` landed at `cc3d301` and was NOT in that list, so the figure a reader would
measure omitted a whole distribution — the same hand-written population as ⟐FENCE-WARRANTS, in the
poll instead of the gate.

⚑⚑ **FIXED BY DERIVATION, NOT BY ADDING `fence`.** Typing the fourth name would have reproduced the
defect one distribution later. The poll ALREADY enumerates every distribution by its
`pyproject.toml` (line 152, with a control arm asserting the query finds the three known ones); the
RUF201 line now interpolates that same query. Reads `for d in fence hooks mdstruct ratchet` today
and will read the fifth name the day one lands, with nobody remembering to edit it.

⚑ **AND THE ADJACENT COMMENT'S REFUSAL STILL STANDS, correctly.** It declines to RUN ruff inside
the poll — three process starts against a script measured at 222 — and that is a separate question
from which directories to name. Knowing the population is free here; measuring it is not.

### ⟐UNDECLARED-HOST-INPUTS — the argument that retired `external` does not stop there

`9a97ed8` removed `external` from `//fence:test_fence` on the operator's reasoning: a
target depending on state outside the build graph is unsound BY CONSTRUCTION, and
disabling its cache pays for the unsoundness rather than removing it.

⚑ The host property that witness depends on is *a process-free parent cgroup with
memory+pids delegated* — measured 2026-09-10, recorded in `fence/src/mikemol/fence/cgroup.py`,
DECLARED NOWHERE. So a cache hit asserts a fact about an undeclared input. Measured after
the change: `bazel test //fence:test_fence` reports `Executed 0 out of 1 test: 1 test passes`
from cache.

⚑⚑ AND I FLAGGED, WITHOUT MEASURING, that the same may hold for other `sh_test` checkers
here (`//fence:ruff`, `//fence:mypy`, the ratchet targets). THAT IS A CLAIM I HAVE NOT
TESTED. A tick taking this should MEASURE the scope before proposing anything — an
unmeasured generalisation from one instance is the shape this session kept catching.

### ⟐RATCHET-MEANS-TWO-THINGS — measured, reported, deliberately not acted on

`--ratchet` finds the scale at which the RESIDENT SET binds on a swap-backed host, and
the scale at which the workload DIES in a pod (k8s sets `memory.swap.max=0` on Guaranteed
pods). Its docstring reads as the second while doing the first here.

⚑ NOT CHANGED ON REASONING ALONE — that would be shipping a guess. cassian's stage 2
fences both arms per subject and will produce the measurement that settles whether it
needs saying. Ready when that measurement exists, blocked until then.

### ⟐VACUITY-IS-ONE-CELL — settled 2026-09-10 by research into two peer repositories

⚑⚑⚑ THE OPERATOR NAMED IT: *most of these checks smell like syntactic or existence
checks, not semantic ones.* Two repositories were read FROM SOURCE and they converge
without sharing vocabulary.

⚑ **v4cat DOES NOT DEFINE "vacuous"** — 1 occurrence in 90 files, casual English.
Positive control, same tool and flags: `witness` returns 14 commits, `vacuo` returns 0.
It does not need to: vacuity is the `10 LEFT` cell of a Klein-four read
(`methodology.md:288-297`), and `theory.md:436` gives the consequence — *any unary
operation throws away at least two cells.* `methodology.md:266` names the shape exactly:
*every read is a comparison. There is no unary query. What looks unary is always a binary
comparison whose right-hand referent is HIDDEN BY CONVENTION.*

⚑⚑ **paperkit HAS THE LADDER AS A LITERAL**, `grade.py:17`:

    vacuous(0) < indeterminate(1) < existence(1) < behavioral(2) < imported(3)

with `grade.py:21` giving the distinction — *existence (presence proven) < behavioral
(falsifiability proven).* So a green `test_no_string_assertion_in_this_module_is_vacuous`
is `existence`, TWO RUNGS BELOW behavioral (ranked 0 and 2). **Passing it means rung 0 was
avoided, not rung 2 reached.**

⚑ THE GRADER AT `2ed26a4` IS THE INSTRUMENT FOR RUNG 2, and it does not replace the sweep
— they measure different cells. What is still true of the sweep: it reports `10` only,
`01` is invisible, and `00` was never a blind spot because `U` was never bounded — which
`rigorous_use.md:78` calls an *unearned absence*.

⚑ AND `_MAX_UNRESOLVED` IS NOT A DEBT. It counts the RESOLVER'S REACH, a third syntactic
property, ratcheted by a guard that treats it as owed. The apparent 22→23 collision that
nearly triggered a redesign was a HELPER counted as a test; scoping to `test_`-prefixed
functions returned it to 22 with no constant moved.

### ⟐EXE002-REMOTE-ONLY — NEW 2026-09-10, measured, THREE TARGETS RED ON THE EXECUTOR

⚑⚑⚑ **`//hooks:ruff` IS GREEN LOCALLY AND RED REMOTELY ON IDENTICAL SOURCES.** Measured at
unmodified HEAD (`29240c9`), so it is not a consequence of any uncommitted change:

```
bazel test //hooks:ruff                     All checks passed!
bazel test //hooks:ruff --config=remote     Found 23 errors.  (EXE002, every .py file)
bazel test //mdstruct:ruff --config=remote  FAILED            (same shape, both distributions)
```

**Three targets fail and it is ONE cause.** `//hooks:ratchet` refuses 22 new
`shebang-missing-executable-file` keys — correctly; it is doing its job over ruff's output — and
`//hooks:test_bar_fires::test_every_suppression_directive_suppresses_under_the_gates_config`
fails with 2 `EXE002` for the same reason. With the tick's own new file present the ratchet count
is 23, the delta being exactly that file; **at HEAD it is 22, which is how all three were
confirmed pre-existing rather than introduced.**

⚑⚑⚑ **THE CAUSE, MEASURED DIRECTLY 2026-09-10 — AND IT CORRECTS THIS SECTION'S OWN FIRST
FRAMING.** An earlier revision of this entry said *"the rule's subject does not exist inside a
build action"* and asserted, without measuring it, that bazel does not preserve source mode bits.
Half right, and the wrong half was load-bearing. A probe `stat`-ing its own staged siblings from
inside an action, reporting through the failure channel:

```
                    local sandbox   remote executor   repository
hooks/tests/*.py    -rw-rw-r--      -rwxr-xr-x        -rw-rw-r--
S_IXUSR             False           True              False
```

⚑⚑ **SO THE SUBJECT DOES EXIST, AND IS READ CORRECTLY, LOCALLY. IT IS *REMOTE STAGING* THAT
DISCARDS THE MODE BIT** — the executor materialises every source `+x`. `EXE002` is not
malfunctioning: it truthfully reports a filesystem the CAS invented. The finding is true of the
staging and **false of the repository** — the mis-named-population class, where a correct check
runs over the wrong set.

⚑ **AND THE GENERAL FORM IS BIGGER THAN THIS RULE.** Anything keying on a mode bit is unsound
under `--config=remote`, not just `EXE002`. That is worth knowing before something else is built
on one. See ⟐REMOTE-DISCARDS-MODE-BITS.

⚑ **AND THIS IS THE HARD CASE, NOT THE EASY ONE.** An inert gate fires on nothing and someone
eventually notices. This gate FIRES, produces 23 findings with file and line, and would pass
review — while supplying evidence for a proposition nobody asked about. It is the
active-gate-aimed-at-the-wrong-predicate shape, arriving at the executor boundary.

**What it costs now:** `bazel test //... --config=remote` cannot go green, so every hermeticity
claim wanting the strong instrument sits behind a red bar that is not about the code.

⚑ **THE FIX IS AN OPERATOR DECISION AND HAS NOT BEEN TAKEN.** Candidates:

- **`ignore = [..., "EXE002"]`** with the measurement recorded. ⚑ NOTE THE JUSTIFICATION CHANGED
  WITH THE CAUSE: it is no longer "the subject is unobservable in an action" — the rule works
  locally — but "the remote population is not the repository's". That is a weaker warrant for
  disabling a rule that is *correct* on the instrument developers actually run. Still a change to
  the bar; *"lowering it is an operator decision"* covers the shape.
- **Keep `EXE002` and stop running `//*:ruff` remotely** — concedes the weaker instrument for the
  lint gate specifically, and is now the *cheapest correct* option rather than a concession: the
  rule's subject is a repository fact, and the local sandbox is the arm that can see it.
- **Normalise the mode bits during staging** — repairs the population rather than the rule; the
  structurally honest one, and the most work.

Carried as measured, red, and NOT worked around.

### ⟐REMOTE-DISCARDS-MODE-BITS — NEW 2026-09-10, measured, GENERAL

⚑⚑ **The executor stages every source file `-rwxr-xr-x`; the local sandbox stages it with the
repository's own `-rw-rw-r--`.** Measured from inside an action in both modes (see the table in
⟐EXE002-REMOTE-ONLY, which is the first instance rather than the whole finding).

**Why it is filed separately from the ruff red:** `EXE002` is the symptom that surfaced it, but the
property is about the CAS, not about ruff. **Any check keying on a mode bit is unsound remotely** —
an executable-script assertion, a permissions gate, a `py_binary` wrapper test. None exists here
yet; this entry is so that one is not written against a mode bit and then debugged as a flake.

⚑ **AND IT IS AN ASYMMETRY IN THE SUPPOSEDLY STRONGER INSTRUMENT.** Remote execution is adopted in
`.bazelrc` as the sandbox that proves declarations complete. On this axis it carries LESS
information than the local one — it cannot represent a fact the local sandbox represents
faithfully. That does not retract the hermeticity argument, which is about reachable inputs; it
bounds it. A stronger instrument on one axis is not stronger on all of them.

### ⟐OOM-GROUP — untouched, and correctly so

Whether the fence's CHILD cap binds before a POD's ceiling does. k8s sets
`memory.oom.group=1` on every pod cgroup, so a child cap that fails to bind means the
F-arm's 256MB kills the WHOLE EXECUTOR POD rather than reddening one test.

⚑ NOTHING HAS ALLOCATED ON ANY POD IN ANY RUN BY EITHER PARTY, so no `restarts=0` reading
is survival evidence. ⚑⚑ It does NOT need the RBE substrate: `--mem N --swap 0` on a host
cgroup is the same deliberate breach at a process-sized blast radius. Not proposed as work.

### ⟐RUF201 — carried, answered, blocked on a paydown

Operator ANSWERED 2026-09-07: adopt. Blocked on a preview-wide paydown whose size is
deliberately NOT stated anywhere — the poll prints the command that measures it. Renaming
first is unshippable: a name selector needs `--preview` to LOAD.

### ⟐MD056-CORPUS-12 · ⟐VACUITY-CEILING · ⟐CLASSIFY-SPANS-ALL-TABLES

Carried. MD056: 12 ragged rows, all measured out of reach (frozen leg directories, filed
legs). Vacuity: the poll now prints a CEILING, honestly labelled, not a count. Classify:
unscoped `classify` walks every table without disclosing its span.

## What the last stretch established, so a tick does not re-derive it

⚑⚑⚑ EVERY DEFECT IN THE FENCE EXCHANGE HAD ONE SHAPE: a plausible reading pointing at the
WRONG SUBJECT. Never a failure — always something that looked fine.

| collapse | what stood for what |
|---|---|
| `local` | host conflated with executor — `8 passed` about the wrong machine |
| `skipif(reason=)` | a hardcoded guess conflated with the measured cause |
| `ro` | one word for bind, superblock, and mount ROOT |
| *(the fourth)* | a REFUTATION standing in for a REQUIREMENT — every failure measured, never the success |
| `BOUND BY MEMORY` | throttled conflated with killed, while `--swap`'s own help drew the distinction |
| `manual` / `external` | scope management and cache management standing in for soundness |

⚑ The fence's requirement, measured and now stated: A PROCESS-FREE PARENT CGROUP with
memory+pids delegated. It cannot run in a cgroup namespace whose root holds processes —
sibling is forced by the namespace, child is forced out by the no-internal-process rule
(EBUSY, measured), and a writable bind would only move the refusal.
