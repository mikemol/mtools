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

### ⟐UPSTREAM-DOCSTRING-LIES — a STANDING constraint on what may be claimed, not work to do

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

⚑⚑⚑ **RE-MEASURED 2026-09-11 AND IT STILL HOLDS — BOTH HALVES, because the finding is a MISMATCH
and one half going stale would dissolve it.** `parse_requirements.bzl:70` still promises *perform a
consistency check against*; `:89` still reads `if uv_lock and toml_decode:` and returns immediately.
Neither moved.

⚑⚑ **RECLASSIFIED FROM LIVE TO STANDING, WHICH IS A DIFFERENT STATE AND NOT A CLEARING.** Nothing
here is work: this repository does not use `uv_lock`, so there is no defect in the tree to repair.
What the section does is FORBID A FUTURE CLAIM — the same shape as ⟐REMOTE-DISCARDS-MODE-BITS,
reclassified one tick ago for the same reason. ⚑ A CONSTRAINT PARKED IN THE LIVE COLUMN reads as
undone work and invites a tick to "finish" it; a constraint deleted because nothing is broken
leaves the next reader to inherit the docstring's sentence as evidence, which is exactly the damage
it exists to prevent.

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

### ⟐MODULE-RUFF-CLAIM-STALE — CLEARED; the comment was corrected and this section outlived it

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

⚑⚑⚑ **CLEARED 2026-09-11 — AND IT WAS ALREADY DONE IN THE FILE, SO THIS SECTION WAS THE LAST
STALE RECORD OF ITS OWN DEFECT.** `MODULE.bazel:184-212` now opens *"the reason recorded here went
stale"*, quotes the withdrawn premise as withdrawn (kept visible *because a reader will have spent
it*), carries the measurement table, and states explicitly what is NOT established. Both items
above are answered: the comment is corrected, and the redundancy question is recorded as unmeasured
rather than acted on.

⚑⚑ **BOTH LEGS RE-MEASURED TODAY RATHER THAN READ**, since a comment is output and this symbol
exists because one went stale:

```
bazel cquery '@hooks_dev//ruff:extracted_whl_files'  ->  bin/ruff STAGED (+ site-packages,
                                                          the control that it is not returning all)
file …/bin/ruff  ->  ELF 64-bit LSB pie executable … stripped
…/bin/ruff --version  ->  ruff 0.16.6          (a build is not a verdict; it RUNS)
entry_points:  ruff 0 · mypy 5 · pytest 2      (the control: the reader can see them)
```

⚑ **THE SURVIVING LEG IS THE ENTRY-POINT ONE AND IT HOLDS.** `ruff` declares zero console scripts,
so there is nothing for `py_console_script_binary` to regenerate and the `http_archive` remains the
right instrument — for that reason rather than the withdrawn staging one. ⚑⚑ **A CONCLUSION THAT
SURVIVES ITS ORIGINAL ARGUMENT IS NOT THEREBY UNSUPPORTED, AND IT IS NOT THEREBY SUPPORTED EITHER**:
the second leg had to be measured on its own, which is what the comment records and what this
re-measurement confirms.

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

### ⟐GATES-AS-TARGETS — OPERATOR RULING 2026-09-10, and most of it is ALREADY TRUE

⚑⚑⚑ **THE RULING:** *"the gate verdicts should use the build's venv. To that end, the gates should,
honestly, be build TARGETS."* Answering the question raised one tick earlier about the three
non-bazel consumers.

⚑⚑ **AND THE FIRST MEASUREMENT REFRAMES THE WORK: the checks ARE targets already.**
`bazel query 'kind("sh_test", //...)'` returns **13**: `ruff`, `mypy` and a ratchet gate for each of
the four distributions, plus `//:shellcheck_githooks`. The per-module `py_test` witnesses are
targets too. So "make the gates targets" is not construction — it is **removing a second,
host-venv copy of verdicts the graph already produces.**

**Measured: the gate runs two verdicts over the same subject.** `.githooks/pre-commit:379-381`
materialises the index with `git checkout-index --all --prefix="$staged/"`, then:

```
:405  run_checked ruff    $root/$dist/.venv/bin/ruff    over $staged   ← host venv
:410  run_checked mypy    $root/$dist/.venv/bin/mypy    over $staged   ← host venv
:429  run_checked pytest  .venv/bin/python3 -m pytest   over $staged   ← host venv
:554  ( cd "$staged" && bazel test //... )                             ← the targets
:711  ratchet/.venv/bin/mikemol-ratchet                                ← host venv
```

⚑⚑⚑ **RE-MEASURED 2026-09-11: THAT TABLE IS A HISTORICAL READING AND TWO OF ITS ROWS ARE GONE.**
`grep -n 'venv/bin' .githooks/pre-commit` now returns twelve lines and **no ruff and no mypy among
them** — both verdicts come from the targets. What still runs out of a host venv, measured:

```
:448  env -C $dist .venv/bin/python3 -m pytest -q        ← per-distribution suite
:724  mdstruct .venv/bin/python3 -m mypy.stubtest        ← the stub-authority witness
:752  ratchet/.venv/bin/mikemol-ratchet                  ← the preview-debt ratchet
:775  mdstruct .venv/bin/python3 -m …cli verify / lint   ← the markdown witnesses
```

⚑⚑⚑ **AND THAT CORRECTION OVERSTATED ITS OWN FINDING — MEASURED 2026-09-11, ONE OF THE FOUR
SURVIVORS *IS* A DUPLICATE.** The sentence below reads *every survivor is a check with no
equivalent target the gate can reach*. It was written from reading the GATE; the claim is about
the GRAPH, and `bazel query 'kind("py_test|sh_test", //...)'` answers it:

- **`:448` pytest over the developer tree** — target `//<dist>:test_*`. **Not** a duplicate, and
  the gate argues it in place at `:442`: the developer venv surfaces a missing dependency as an
  import error, where a sandbox never had it.
- **`:724` stubtest over panflute** — target `//mdstruct:test_stub_authority`. **DUPLICATE.** Same
  tool, same allowlist, run twice.
- **`:752` ratchet over `$root/$dist`** — target `//<dist>:ratchet`. **Not** a duplicate: the
  target censuses the RUNFILES tree — it had to be taught to exclude synthesized `__init__.py`
  files the source tree lacks — while the gate censuses the REAL tree, because census keys are
  paths a reader must be able to go fix.
- **`:775` mdstruct verify / lint** — no target exists.

⚑⚑ **AN ABSENCE CLAIM ABOUT THE BUILD GRAPH, ASSERTED FROM READING A SHELL SCRIPT.** Three of the
four rows survive the check and one does not, which is the difference between a measured finding
and a plausible one. ⚑ The same shape this document records thirty-odd times, arriving in the
correction to a stale table rather than in the table itself.

⚑ **THE STUBTEST TARGET IS A REAL SUCCESSOR, F-ARMED BEFORE ANY REMOVAL IS PROPOSED**: planting a
divergence in `stubs/panflute/__init__.pyi` (renaming `stringify`'s first parameter) makes
`//mdstruct:test_stub_authority` go RED. A deletion premised on a successor must prove the
successor fires; this one does. The removal itself is not taken here — the ruling covers it, but
`run_checked` also supplies the gate's failure REPORTING, and whether the target's log reaches a
refused committer as legibly is a second question nobody has measured.

⚑⚑ **SO THE RULING IS MOSTLY DISCHARGED AND WHAT REMAINS IS SMALLER THAN THE TABLE SUGGESTS.** The
two duplicated verdicts that went were ruff and mypy; a third — stubtest — is measured as
duplicated and not yet removed. The other three survivors each answer about a subject no target
reaches: the developer tree, the real tree, and markdown that has no target at all. ⚑ **REMOVING A
DUPLICATE, KEEPING A DIFFERENT SUBJECT, AND BUILDING A MISSING TARGET ARE THREE JOBS** — the
original row list said only "host venv" and made them look like one.

⚑ **THIS SECTION IS ITSELF THE STALE-RECORD CLASS IT DESCRIBES, in the document a tick reads
first.** The table was true when written; nothing re-measured it while the work moved underneath,
and it sat in the LIVE section where a reader takes it for the current state.

⚑⚑⚑ **AND `bazel test` RUNS INSIDE `$staged` TOO, WHICH FALSIFIES A COMMENT AT `:541`.** That
comment reads *"ruff and mypy already ran in `$staged`; `bazel test` did not"* — the `cd "$staged"`
on line 554, thirteen lines below it, contradicts it. Both halves check the same materialised
index. So the duplication is **not** tree-vs-index; it is one subject through two instruments.

**The two instruments differ, and here is the whole of the measured difference:**

```
                host .venv                     built .venv (//:venv.bzl)
interpreter     3.13.11  (mise, via uv)        3.13.13  (bazel toolchain)
ruff            0.16.6                         0.16.6      ← agree TODAY
mypy            2.3.1                          2.3.1       ← agree TODAY
declared in     nothing                        MODULE.bazel
pyvenv.cfg      home = ~/.local/share/mise/…   home = ../bin
```

⚑ **THE CHECKER VERSIONS AGREE AND THAT IS NOT A GUARANTEE — it is a coincidence maintained by
hand, from two resolvers with no shared constraint.** The honest statement of the risk is narrow
and real: the ratchet's baseline keys ARE ruff findings, so a future divergence mints or clears
keys the build would not, and both halves would report green in their own terms.

⚑⚑ **THE BLOCKER ON REPOINTING, MEASURED: the built venv has no `bin/` entry points.**
`bazel-bin/hooks/.venv/bin/` contains exactly one file — `python3`. `ruff` and `mypy` are present
in `site-packages` but have no console scripts, because `//:venv.bzl` only ever creates the
interpreter symlink. The gate invokes `.venv/bin/ruff` directly, so repointing it today fails
immediately. **That is a gap in the rule I wrote and did not measure.**

#### ⚑⚑⚑ STEP 1 AND STEP 3 LANDED TOGETHER, BECAUSE AN ARM CORRECTLY REFUSED TO LET THEM SPLIT

The host-venv `ruff` and `mypy` are gone from `.githooks/pre-commit`. `//<dist>:ruff` and
`//<dist>:mypy`, run by `( cd "$staged" && bazel test //... )`, are now the only run of either.

**The redundancy was measured before the deletion, not inferred from target names:**

```
ruff   three binaries — host venv, @ruff//:bin, built venv site-packages — ALL 0.16.6
       on a PLANTED defect: host PLR2004 rc=1 | archive PLR2004 rc=1 | identical rule sets
       ruff_check.sh passes the same --config and `check .` from the same directory
mypy   the target deletes synthesized __init__.py markers a staged checkout never has
       population: 24 source files BOTH ways; a planted type error flips host to rc=1
       with the population held at 24
```

**And the delegation was then shown to carry the coverage**, which the arm cannot assert:
control green on both targets, then `//hooks:ruff` rc=3 on a planted magic value and
`//hooks:mypy` rc=3 on a planted return type, tree restored.

⚑⚑ **STEP 3 WAS FORCED, NOT CHOSEN.** `test_the_preflight_runs_the_ruff_the_gate_runs` refused the
tree the moment the gate changed — preflight was still running `.venv/bin/ruff`, predicting a check
the gate had stopped performing. That arm existed exactly for this and fired exactly when it
should. `preflight.sh` now runs `bazel test //<dist>:ruff //<dist>:mypy` with `--test_output=errors`
so a refusal still carries its finding; both targets are cached, so a clean tree answers from the
action cache and the script stays fast.

⚑ **FOUR EXISTING ARMS REFUSED THE DELETION, AND ALL FOUR WERE RIGHT TO.** Each asserted a
property of the deleted block:

- **`MYPYPATH="$staged/`** — asserted the *workaround* for the editable-install import closure. Its
  subject is gone; the target reads a bazel sandbox built from declared `srcs`, where that hazard
  cannot arise. Rewritten to assert the structural fact instead of demanding the workaround.
- **three typed check labels** in the capture-discipline arm — a hand-written population inside an
  arm about capture, refusing a correct change because two of its three names no longer exist. Now
  derived from the file.
- **the ruff-agreement arm** — the real finding above.
- **the vacuity sweep** — caught a literal (`ruff EXITED`) that the rewrite had orphaned.

**The sequence the ruling implied, with 1 and 3 now done:**

1. **Delete the duplicated host-venv checks** at `:405`, `:410`, `:429`, `:711` — the graph already
   produces those verdicts at `:554`, over the same staged tree. This is subtraction, needs no new
   rule, and removes the divergence rather than managing it.
2. **`//:venv.bzl` grows console scripts** (`rules_python` has `py_console_script_binary`), for the
   remaining consumers that genuinely need an activatable venv — the interactive dev loop.
3. **`preflight.sh`** then predicts the gate by running the same targets rather than a second set.

⚑ **AND ONE COST TO STATE PLAINLY BEFORE ANY OF IT:** a gate whose only verdict comes from bazel
hard-depends on the build. A fresh clone cannot commit until it builds, and the fast host loop
disappears. That is the trade the ruling accepts; recorded here so nobody re-litigates it as a
surprise.

### ⟐ARG-AFTER-OWED — CLEARED 2026-09-10, after being carried as owed TWICE

⚑⚑ **THE RAISE-SHAPE IS ABSENT AND THE CAPTIVITY WAS PRESENT, IN ONE PLACE.** cassian reported
`_arg_after` reading `sys.argv` in their copies and named the real defect: *the captivity is the
defect and the raise is its symptom* — reading the global means no case can vary the input, so the
branch a docstring describes has never been exercised. mtools recorded it as owed; cassian checked
their own tree **because of that sentence**; mtools carried it as owed a second time without
looking.

Measured across all four distributions, 36 source files, **with a constructed positive control**
so the searcher is known to see the shape it reports absent:

```
argv.index(                     (none)
_arg_after                      (none)
sys.argv read inside a helper   mdstruct/src/mikemol/mdstruct/cli.py
```

**`cli.main()` read the global with no parameter.** Its usage, unknown-mode and grep-arity branches
were reachable only through a caller that mutates `sys.argv` and restores it — which
`tests/test_verify.py::_run_cli` did, in a `finally`, putting every case in that module behind one
restore. A case that forgot it would poison its neighbours and nothing would catch that.

**Repaired:** `main(argv: list[str] | None = None)`, defaulting to the global so the console script
is unchanged — pinned by its own arm, the same discipline as the grader's interpreter default. The
workaround in `_run_cli` is retired: one line now, no global, no `finally`.

⚑ *A finding filed outward is not a finding fixed at home*, and the second carry is the part worth
remembering — the first was honest ignorance, the second was a record I had already written.

### ⟐EXE002-REMOTE-ONLY — CLEARED 2026-09-11 by operator ruling; ⟐REMOTE-DISCARDS-MODE-BITS STANDS

⚑⚑⚑ **`bazel test //... --config=remote` IS GREEN FOR THE FIRST TIME: 46 of 46, 26 actions on the
executor.** It was 43 of 46 for many ticks, three targets red from one cause.

**Operator ruling: normalise the POPULATION, not the rule.** The alternatives put were disabling
`EXE002` repo-wide — which turns off a check that is *correct* on the instrument developers
actually run — or excluding the lint targets from remote, conceding the stronger sandbox. Both
were declined.

⚑ **THE MECHANISM WAS INVESTIGATED BEFORE BEING BUILT, because I had flagged it as unmeasured.**
Three candidates; `bazel help build` mentions no mode-preserving flag, and the staged files are
**owner-writable**, so an action may normalise its own copy. ⚑⚑ And the idiom was already in the
tree: `mypy_check.sh` deletes the synthesized `__init__.py` markers rules_python writes into a
runfiles tree, for exactly this reason. `ruff_check.sh` now strips `+x` the same way.

⚑⚑ **AND THE FIRST REPAIR REACHED ONE CALL SITE OF TWO.** `//hooks:ruff` and `//hooks:ratchet` went
green; `//hooks:test_bar_fires` stayed red because its suppression arm runs **its own** ruff
invocation rather than going through `ruff_check.sh`. *"A repair applied to one call site is not a
repair to the class"* — recorded elsewhere in this repository about a different check, measured
again here, in the arm whose own comment already says it must share the gate's setup.

```
before            43 of 46 remote   (ruff → ratchet → test_bar_fires, ONE cause)
after script fix  45 of 46 remote   (the arm's own invocation still unnormalised)
after both        46 of 46 remote, 46 of 46 local
```

⚑⚑⚑ **AND THIS HEADING SAID BOTH SYMBOLS WERE CLEARED, WHICH IS TRUE OF ONE OF THEM.** The three
red targets are fixed. **The CAS still discards mode bits** — the repair NORMALISES the population
so the rule stops misfiring, and changes nothing about the executor. ⟐REMOTE-DISCARDS-MODE-BITS
therefore STANDS as a property to design against, and its own section records why: any check keying
on a mode bit is unsound remotely, and none should be written without knowing that.
⚑⚑ **A FIX FOR A SYMPTOM FILED AS A FIX FOR ITS CAUSE is the recurring shape in this repository's
own clearing record** — the symptom is what went red, so it is what a reader remembers, and the
cause quietly inherits the *CLEARED* the symptom earned.

### ⟐RUF201 — DISCHARGED 2026-09-11 at f7d92c9, all four distributions armed and paid

⚑ **THE BLOCKING CLAIM WAS TRUE, MEASURED:** `--select magic-value-comparison` gives `rc=2 ruff
failed` without `--preview` and `rc=1` with it. A name selector genuinely needs preview to load, so
"rename first" was never available.

⚑⚑ **AND MY OWN PROBE OF THE POPULATION WAS THE WRONG INSTRUMENT.** `--select RUF201` reported
**zero sites in all four distributions**, contradicting the poll's 18-in-hooks. `--select`
*replaces* the config's selection, so it loaded the rule without the `select = ["ALL"]` context
that produces the findings. `--extend-select` reproduces the poll's figure exactly. **The poll was
right and the probe was wrong** — the same shape as arm C measuring replacement semantics rather
than the tree.

**The real population in hooks, listed:** 18 `RUF201` (every one in `pyproject.toml`'s own `ignore`
and `per-file-ignores` lists) + 18 `RUF106` (suppression comments in `test_bar_fires.py` ×17 and
`test_checkers.py` ×1). **All 36 auto-fixable.** Repo-wide the preview paydown is 171.

**Ruled: arm `preview = true` repo-wide and pay the 171 down.** ⚑⚑⚑ **DONE, IN FOUR COMMITS:**
`9802790` hooks · `39b25ad` ratchet · `9129a3d` mdstruct · `f7d92c9` fence. Census measured **0
across all four**; every ratchet baseline is EMPTY, each lowered on an operator ruling and F-armed
(a planted finding is refused by name, a clean copy passes).

⚑⚑ **AND THE 171 WAS NEVER RE-MEASURED AFTER IT WAS WRITTEN, WHICH IS WHY IT OUTLIVED ITS SUBJECT.**
Measured fresh at each arming it read 170, then 122, then 114, then 60, then 0 — the figure in this
paragraph and in the tick prompt stayed 171 throughout. A recorded count announces no way to
re-check itself; the poll's own repair for this was to stop printing the number and print the
command instead, and this section is the same defect one document over.

⚑ **WHAT IS WORTH CARRYING FORWARD IS NOT THE STATUS BUT THE ORDER AND ITS TWO TRAPS**, for whoever
arms the next preview-gated rule: arm first, rename second (a name selector cannot LOAD without
preview — measured, rc=2); and probe with `--extend-select`, never `--select`, which replaces the
config's `select = ["ALL"]` and reported zero where the tree held eighteen.

### ⟐ROLE-AXIS-ROW-WAS-AN-ARTIFACT — NEW and CLEARED 2026-09-11, a published row proved nothing

⚑⚑⚑ **cassian RAISED IT AS A HYPOTHESIS ABOUT MY TOKENISER RATHER THAN A CLAIM ABOUT MY TREE, AND
IT HOLDS FOR EXACTLY ONE ROW.** The role-axis table published at `e046800` carried
`----  a COMMENT being written` as evidence that role does not matter within readers. Measured:

```
# COMMENT in a heredoc body   tokens: ['>','g.txt','<<','EOF','EOF']   ⚑ the mention is GONE
BARE mention in a body        tokens: [... 'notes.md', 'EOF']          the mention survives
```

`#` opens a shell comment that swallows the rest of the line, so **the token never existed.** That
row measured comment-stripping and supported nothing.

⚑⚑ **THE CONCLUSION SURVIVES ON THE OTHER ROWS — a correction, not a retraction.** `touch
scratch.md` and `echo hello.md` pass **with the token present**, which is the real evidence for
reader-scoping. Five of six rows were measurements; one was an artifact of my own fixture. Against
a reproduction of the PRE-FIX scan: the bare mention **fired**, the comment did not — so the
distinction was live and invisible.

⚑ **THE ARM ASSERTS ITS OWN PRECONDITION.** It checks the mention reaches the token stream before
asserting the pass; otherwise it would go green for the same accidental reason the published row
did. *An arm that cannot tell "the gate allowed it" from "the shell ate it" is measuring the
fixture.*

### ⟐HEREDOC-DROP-LOST-A-CATCH — NEW and CLEARED 2026-09-11, cassian's bound was better than mine

⚑⚑ **DROPPING EVERYTHING AFTER `<<` THREW AWAY A REAL READ.** Measured:

```
cat > g.txt <<EOF / body / EOF / grep -n foo notes.md
  drop-everything   -> ['>', 'g.txt']                             ⚑ the grep vanishes
  terminator-aware  -> ['>', 'g.txt', 'grep', 'foo', 'notes.md']   the read survives
```

The tokeniser does not split on the newline after a terminator, so a heredoc followed by **any**
command folds that command into the same invocation — ordinary shell, not an exotic shape — and the
gate went quiet on it for one tick.

⚑ **ADOPTED cassian'S BOUND BY MEASURING IT, NOT BY COPYING THE DESCRIPTION** — the same discipline
that caught the `-e` divergence, where copying would have been wrong. Their safe-direction argument
is kept and holds on inspection: an unterminated tag swallows the remainder, because a body token
read as an ARGUMENT is a false refusal of a command that reads nothing, while an argument read as
BODY is a missed catch in a command that is WRITING, whose destination is still scanned.

### ⟐PATTERN-AS-ARTIFACT — FIXED 2026-09-11, both arms, and the file could not be written past it

⚑⚑⚑ **THE DEFECT REFUSED THE ARMS WRITTEN TO FIX IT — six refusals in one write, every one from a
test fixture.** `cat` is in `TEXTUAL`, so a heredoc carrying `grep -n "SKILL.md" x.py` was read as
six textual queries. The file documenting the bug could not be written through the gate carrying
it; the suffix is composed from parts in that test module for exactly that reason.

**Two arms, two different discriminators, fixed in `_scannable()`:**

```
PATTERN   for {grep,rg,egrep,fgrep,ag,ack} the first non-flag argument is what you search FOR,
          and `-e`/`-f` carry it too. Dropped once, never for cat/head/wc.
HEREDOC   everything from `<<` onward is a BODY the command creates. `>` and `>>` name a
          DESTINATION and STAY IN SCOPE.
```

⚑ **THE `-e` CASE IS A MEASURED DIVERGENCE FROM cassian'S TREE.** They reported `_FLAGS_WITH_ARG`
consuming `-e`'s argument before the scan sees it; here it does **not** — that table covers
WRAPPERS (timeout, env, sudo, xargs), never the textual programs. `grep -e PAT file` left the
pattern as the first non-flag argument, so **a fix copied from their report alone would have left
this shape firing.** Tokenisation read, not assumed.

⚑⚑ **TWO EXISTING ARMS REFUSED MY FIRST CUT, AND THEY WERE RIGHT.** It dropped everything from the
first redirection operator onward, which exempted `cat >> scratch/tool.py` — a shell append to a
claimed artifact. That arm carries an **operator ruling verbatim**: *"don't support redirection,
support editing"* / *"appendation causes files to grow out of control"* — and its comment records
that an earlier fix exempting `>>` was the wrong repair, **with the measured damage**: a staging
block appended to and never drained outgrew the budget of the reader loading it every session.
**I reproduced that exact wrong repair.** The arm is what caught it.

⚑ **AND MY OWN HEREDOC ARM WAS WRONG TOO**, measuring two properties at once: it wrote to
`/tmp/x.py`, and `.py` is claimed in the test table, so the destination firing was *correct
behaviour*. Isolated with an unclaimed `.txt` destination, plus a new control arm asserting a
heredoc write to a **claimed** destination still fires.

**Live, through the rebuilt hooks:** cassian's originally-reported command now works; a heredoc
whose body names `notes.md` goes through; `grep -n test README.md` is still refused.

### ⟐PATTERN-AS-ARTIFACT — the measurement that preceded the fix

⚑⚑⚑ Writing this tick's arms, the structural-query hook refused a `cat` heredoc **because the
Python source being written contained the literal `"doc.md"`** — a string inside a test, not a
path, not a grep pattern, not an argument to anything.

```
cat > tests/test_verify.py <<'PY' ... doc = tmp_path / "doc.md" ... PY
  -> structural-query: `cat` over "doc.md" (.md → markdown)
```

⚑⚑ **AND "ANY TOKEN IN THE COMMAND TEXT" WAS MY OVERSTATEMENT, CORRECTED BY MEASURING TWO AXES
SEPARATELY.** cassian's reply supplied the missing half — the claims table — and the two together
separate *which suffixes* from *which positions*:

```
ROLE varied, suffix fixed at .md        SUFFIX varied, role fixed at a real target
  deny  a real TARGET                     deny  .md
  deny  a grep PATTERN                    ----  .tsv .bib .py .agda .txt
  deny  a STRING LITERAL being written
  ----  part of a COMMENT being written
  ----  an argument to a non-reader (touch)
  ----  bare, in an echo
```

**So the scan is scoped to commands the hook classifies as READERS, and within those the token's
role does not matter** — target, grep pattern, and a string literal inside a heredoc all fire,
while `touch scratch.md` and `echo hello.md` pass. Not "any token anywhere"; not "the first
non-flag argument" either.

⚑ **THE SUFFIX TABLE IS WHERE THE BLAST RADIUS LIVES**, measured by cassian across three trees from
each repo's own `SKILL.md` claims column: **mtools 1** (`.md`), **cassian 3** (`.bib .md .tsv`),
**substrate 9** (`.agda .agdai .bib .jsonl .lagda .md .mk .py .pyi` — including `.py`). That
explains my three vacuous `.tsv` arms exactly, and predicts substrate has by far the widest
exposure. Neither of us has measured substrate's copy; recorded as their observation, not a claim
about their tree.

⚑⚑ **AND A DEFECT STATED WITHOUT ITS DOMAIN READS AS UNIVERSAL** — cassian's own phrasing for why
their "wider" claim cost me a measurement. It is the `rubric.tsv` class travelling OUTWARD, which
is the worse direction: I spent a probe discovering their scope rather than checking their claim.

### ⟐FAIL-SHUT — NEW and CLEARED 2026-09-10, the launcher deadlocked the repository in production

⚑⚑⚑ **THE LAUNCHER SHIPPED AT `c4675fe` REFUSED ITS OWN PRESCRIBED REPAIR.** It denies when the
built venv is absent — correct, and the reason the fail-open window closes. One tick later a
rebuild invalidated `bazel-bin`, the launcher refused as designed, and then refused
`bazel build //hooks:.venv` — **the command its own refusal message tells the reader to run.**
Every Bash call was blocked, including the one that repairs the condition.

⚑⚑ **THE SESSION ESCAPED ONLY BY AN ACCIDENT OF SCOPE:** the hook matcher is `Bash`, and `Edit` is
not gated. Had the matcher been wider there would have been no way out from inside.

**Repaired with a bootstrap exemption, measured 7 of 7 with the venv absent:**

```
bazel build //hooks:.venv      ALLOW   the repair itself
bazel build //hooks/...        ALLOW   the package form
bazel test //...               deny    ⚑ a test run repairs nothing
bazel build //mdstruct:.venv   deny    ⚑ a DIFFERENT venv is not this hook's repair
rm -rf /                       deny
grep -n foo README.md          deny    an ordinary refusable command
echo bazel build //hooks:.venv ALLOW   ⚑ HONEST LIMIT, recorded rather than hidden:
                                       a substring match cannot tell a build from an echo
```

⚑ **A GATE WHOSE REFUSAL CANNOT BE SATISFIED IS NOT FAIL-CLOSED; IT IS FAIL-SHUT, AND THE
DIFFERENCE IS WHETHER A PARTY CAN GET OUT.** The fail-open analysis was right and incomplete: I
measured what happens when the hook cannot run, and not what happens when it runs and refuses
everything. Both are ways for a gate to stop being useful; only one of them looks like safety.

### ⟐CASSIAN-ROUND-2 — answered 2026-09-10, and THREE OF MY OWN FIVE ARMS WERE VACUOUS

cassian confirmed all three findings from `ab722b5` and reported the pattern-as-artifact defect as
**wider** than I measured — not `.md`-specific but *any* claimed suffix inside a pattern, cause
positional at their `verdict():205`.

⚑⚑ **MEASURED HERE, AND THE CORRECTION IS MINE TO MAKE:**

```
grep -n "SKILL.md"   <a .py file>    DENY     ⚑ live here — the original report
grep -n "rubric.tsv" preflight.sh    no deny
grep -n "panels.tsv" blockers.sh     no deny
grep -n foo README.md                DENY     the guard itself, still firing
grep -n foo hooks/rubric.tsv         no deny  ⚑ A REAL .tsv TARGET ALSO DOES NOT ROUTE
```

The last row is the finding: **`.tsv` has no owner in mtools** (`grep -rn tsv routing_table.py`
returns nothing), so the three `.tsv` arms measured **nothing at all, in both directions**. They
would have read as *mtools is clean* when they only mean *mtools does not route that suffix*.
The defect is live here for `.md` — one instance, not a class. Their fix shape (positional, scoped
to the grep family, with `cat`/`head`/`wc` explicitly excluded so the guard is not de-armed) is
right and is expected to be taken.

⚑ **AND `_arg_after` IS OWED TWICE NOW.** Their sentence — *a finding filed outward is not a
finding fixed at home* — applies to me symmetrically: I recorded it as owed, they checked their own
tree because of that, and I still have not checked mine.

### ⟐CONSOLE-SCRIPTS — OPERATOR-RULED and BUILT 2026-09-10, closing ⟐GATES-AS-TARGETS step 2

⚑⚑⚑ **I TOLD THE OPERATOR THIS MATTERED "ONLY FOR THE INTERACTIVE DEV LOOP" AND THAT WAS FALSE.**
`.claude/settings.json` invokes all three `mikemol-hook-*` console scripts as PreToolUse hooks —
they are the gates refusing commands in this very session. The host copies carry
`#!/home/mikemol/github/mtools/hooks/.venv/bin/python3`, an absolute path generated by `uv`: host
state, load-bearing for the harness.

⚑⚑ **AND A MISSING HOOK FAILS OPEN.** Measured: the built venv could not run the entry point, and
reported **rc=0, empty stdout, no decision** — which the harness reads as *allow*. Every refusal
would stop, silently. That is what makes the launcher's refusal arm the point rather than a nicety.

**Ruled: build the scripts AND route the harness through tracked launchers.** Both landed.

⚑ **ONLY AN ABSOLUTE SHEBANG WORKS, MEASURED, THREE SHAPES, TWO WORKING DIRECTORIES:**

```
#!<abs>/python3         runs from any cwd, under the venv's interpreter        ✅
#!./python3             POSIX resolves `#!` against the CWD, not the script's
                        directory — wrong python, and cannot exec from elsewhere
#!/usr/bin/env python3  runs, and runs the HOST mise python — the leak
```

So the generated scripts carry **no shebang at all**: they are executed by an interpreter the
caller names, and insert the venv's `site-packages` on `sys.path` themselves. The launcher supplies
the interpreter from `$CLAUDE_PROJECT_DIR` at run time.

#### ⚑⚑⚑ FIVE HYPOTHESES FOR ONE WARNING, FOUR REFUTED

`Could not find platform dependent libraries <exec_prefix>` appeared on every invocation:

```
H1  pyvenv.cfg `home` names the wrong directory    corrected it — PERSISTS
H2  no lib-dynload under the venv                  host venv has the identical shape — QUIET
H3  the toolchain binary warns                     run directly: QUIET
H4  the symlink-chain shape differs                built BOTH shapes in a scratch tree: BOTH QUIET
H5  the `bazel-bin` CONVENIENCE SYMLINK            ✅ same venv, two paths, one variable:
      via bazel-bin  WARNS   prefix=/home/.../bazel-bin/hooks/.venv
      via real path  QUIET   prefix=.../execroot/_main/bazel-out/.../hooks/.venv
```

CPython resolves `sys.executable` without following `bazel-bin` and computes `exec_prefix` beneath
it. **The `home` fix was not the fix** — it is correct on its own terms and is kept as such, with
the comment saying so. The launcher's `realpath` removes the warning; measured, it does.

⚑⚑ **THE ARM READ 21 CHARACTERS OF A 79-CHARACTER COMMAND.** `"command":\s*"([^"]+)"` stops at the
first quote, and these commands embed escaped quotes around the path — so the capture was
`'STRUCT_HOOK_BLOCK=1 \'` and the venv path the arm forbids was **never in the searched text**.
The arm passed on a haystack that could not contain its needle, and **only the F-arm caught it**.
A structured file read with a regex is the shape this repository's own toolkit hooks refuse for
markdown, done here inside the suite that enforces it. Parsed as JSON now.

⚑ **AND THE VACUITY SWEEP REPORTED THE FIRST FORM VACUOUS — CORRECTLY, FOR A REASON WORTH KEEPING.**
`[c for c in commands if "bazel-bin" in c]` puts an `In` node in the tree, which the sweep resolves
against the file the arm reads; `bazel-bin` is absent from `settings.json` *because the repair
removed it*. The sweep matches `In`, not `NotIn`, so an assertion of ABSENCE must be written `not
in` to be read correctly. Two shapes that mean the same thing to a human, only one of which the
instrument can classify.

### ⟐POLL-NAMES-A-RETIRED-INSTRUMENT — NEW and CLEARED 2026-09-10, the last host-venv consumer

⚑⚑⚑ **`blockers.sh` WENT ON HANDING OUT THE INSTRUMENT THE REPOSITORY HAD STOPPED TRUSTING.** Its
RUF201 line printed `env -C $d .venv/bin/ruff check --preview --statistics .` as the way to measure
the preview debt — a host-venv ruff — while `ad49f96` had removed host ruff from both
`.githooks/pre-commit` and `preflight.sh` on the operator's ruling that gate verdicts use the
build's venv. Derived, it was the **last live consumer**: `grep -rn '.venv/bin/ruff|mypy'` across
the poll, the gate, preflight and `orphan_check.sh` returns one prose mention and this one
instruction.

⚑⚑ **IT SURVIVED BECAUSE THE TWO AGREE.** Measured on `hooks`, byte-identical output — 48 errors,
same seven rules, same counts — host venv and `@ruff//:bin` alike. Both 0.16.6, a coincidence
maintained by hand between resolvers with no shared constraint. **A stale instruction that still
produces the right answer is invisible until the coincidence ends.**

⚑ **AND THE OBVIOUS REPAIR WAS WRONG IN A WAY ONLY RUNNING IT SHOWS.**
`bazel cquery '@ruff//:bin' --output=files` prints `external/+_repo_rules+ruff/ruff` — **execroot-
relative** — so under `env -C $d` it resolves against the distribution directory and fails.
`bazel info execution_root` supplies the prefix. The printed instruction was then executed
verbatim: **4 distributions, 60 / 48 / 55 / 8 = 171 findings.** A printed instruction nobody has
run is prose, not a measurement.

⚑⚑ **`//<dist>:ratchet` ALREADY RUNS `--preview` AND IS NOT A SUBSTITUTE.** It reports refusals
against a baseline — *did the debt grow* — while this line asks *how big is the debt*. Different
questions; the target answers the first, and nothing answers the second without running ruff.

⚑⚑⚑ **THE SWEEP CAUGHT MY ARM, AND THE DEFECT WAS SYMMETRY.** The first cut read
`".venv/bin/ruff" in ln or ".venv/bin/mypy" in ln` — obvious, balanced, and `.venv/bin/mypy`
appears **nowhere** in `blockers.sh` (measured: 0), so that half could never match. The vacuity
sweep names exactly that, in an arm about stale instructions. The paths are composed from the
checker names now, which keeps the property and gives the sweep nothing false to resolve.

### ⟐FILTER-ATE-THE-FINDING — NEW and CLEARED 2026-09-10, in the repair from one tick earlier

⚑⚑⚑ **THE COMMENT PROMISED THE FINDING AND THE FLAG BESIDE IT THREW THE FINDING AWAY.**
`preflight.sh`, rewritten at `ad49f96` to run `//<dist>:ruff` and `//<dist>:mypy`, passed
`--test_output=errors` with a comment saying *"so a refusal carries its finding"* — and
`--ui_event_filters=-DEBUG,-WARNING,-INFO` on the same line. **Bazel emits test output as an
`INFO` event.**

Measured on a planted `PLR2004`, one flag varied at a time:

```
--test_output=errors --noshow_progress --ui_event_filters=-DEBUG,-WARNING,-INFO
                                         rc=3, names PLR2004: FALSE   (7 lines)
--test_output=errors --noshow_progress   rc=3, names PLR2004: TRUE   (26 lines)
--test_output=errors                     rc=3, names PLR2004: TRUE   (33 lines)
```

⚑⚑ **TWO HYPOTHESES WERE REFUTED BEFORE THE THIRD WAS MEASURED.** First: *`errors` prints only for
tests bazel EXECUTES, so a cached failure prints the path* — refuted, `--nocache_test_results`
changed nothing. Second: *`errors` never replays and `all` is required* — refuted, `all` was also
FALSE **under the filter**. Only then did the filter become the candidate, and varying it alone
settled it. Writing "because caching" after the first arm would have been the invented-cause shape.

**What a reader saw before and after,** on the same planted defect:

```
before   //ratchet:ruff  FAILED in 0.1s
         /home/mikemol/.cache/bazel/.../test.log          ← go open it yourself
after    PLR2004 Magic value used in comparison, consider replacing `42` ...
           --> src/mikemol/ratchet/cli.py:83:17
         83 |     return n == 42
```

⚑ **AND THE DETAIL WAS ALWAYS IN THE LOG** — rule, file, line, source excerpt. This is the
*detail that exists somewhere is detail the reader does not have* class the gate repaired for its
own checks with `run_checked`, reintroduced one file over by a flag chosen for tidiness.

⚑⚑ **THE ARM THAT NOW FORBIDS THE PAIRING HAD TO CONCEDE TO A SIBLING ARM, AND THE TENSION IS
REAL.** Its first draft derived the consumer list into a local variable and read each file in a
loop — which `test_no_string_assertion_in_this_module_is_vacuous` cannot resolve, because that
sweep follows `<CONST>.read_text(...)`. The unresolved ceiling went 22 → 23. **Raising the ceiling
would have been expanding a baseline to fit my code**, so the arm reads through the module
constants instead and keeps its population derived from them. *Deriving a population and being
statically resolvable pull against each other; here both were satisfiable, and where they are not,
the ceiling wins.*

### ⟐PREFLIGHT-FAILS-OPEN — CLEARED, and the clearing needed an F-arm rather than a reading

⚑⚑ **`preflight.sh:114` carries the identical `if [ -x ratchet/.venv/bin/mikemol-ratchet ]` guard
repaired in the gate at `0097f22`** — and `preflight.sh:63-72` states the rule in its own words:
*"an absent one REFUSES rather than skips … a skipped check and a passing one are
indistinguishable downstream, and this script exists to predict the gate rather than to produce a
second, weaker verdict."* Forty-five lines later it skips silently.

⚑ **THE ARM THAT CAUGHT THE GATE COULD NOT SEE THIS**, because it reads `_GATE` alone — a
population of one, hard-coded, in an arm written against the hand-written-population defect. The
repair is to derive the consumers: `grep -rln 'venv/bin' .githooks/ preflight.sh` returns exactly
those two files.

⚑⚑⚑ **CLEARED 2026-09-11, AND THE READING ALONE WOULD NOT HAVE SETTLED IT.** Measured at HEAD: the
`if [ -x ]` guard is gone, a refusing `_singleton` check stands three lines above the invocation,
and `preflight.sh:157` states *no guard: presence is REFUSED ON above*. But **the repair being in
the file and its return being PREVENTED are two claims**, and this repository's standing rule is
that a deletion premised on a successor must prove the successor FIRES.

⚑⚑ **SO THE SUCCESSOR WAS F-ARMED, AND THE FIRST MUTATION WAS MINE RATHER THAN A GAP.** Planting
an `if [ -x ratchet/.venv/bin/mikemol-ratchet ]` guard left
`test_every_tool_the_gate_invokes_is_refused_when_absent` **PASSING** — which looked like a hole and
was the arm being right: its predicate is not *no guards* but *no guard on a tool the file does not
ALSO refuse on*, and that tool is refused three lines above, so the guard is unreachable-when-absent
and harmless. ⚑ **I planted against the arm's NAME; the predicate lives in its helper.** Reading the
helper is what separated a real gap from my own misfire.

⚑ **RETARGETED AT THE ACTUAL SHAPE — a guard on a tool with NO refusal — the arm FAILS and names
it:** *`preflight.sh` guards on `['mdstruct/.venv/bin/pandoc']` … while its refusals cover only
`['mikemol-ratchet', 'mypy', 'python3', 'ruff']`*. The repair is covered going forward; the working
tree was left clean, the mutation having been applied to a copy.

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


### ⟐HOST-VENVS-DANGLE — NEW 2026-09-16, found by a PEER, half-repaired by operator ruling

**`~/.local/share/mise/installs/` was removed 2026-09-15 20:47 and took every host interpreter in
this tree with it.** Found not by this session but by `linux-sources`, who filed unprompted after
their own gate died calling `mdstruct/.venv/bin/mdstruct`.

⚑⚑⚑ **THE ERRNO NAMED THE WRONG ARTEFACT, AND THAT IS THE TRANSFERABLE HALF.** Their report:
`FileNotFoundError ... mdstruct/.venv/bin/mdstruct` — where **that file exists**, 340 bytes, mode
775. `execve` reports ENOENT against a SCRIPT when its shebang INTERPRETER cannot be resolved. This
session would have read that as *the script is missing* and looked in the wrong place.

⚑⚑ **THEIR CENSUS IS A DENOMINATOR NO SOLIPSIST MEASUREMENT HERE COULD REACH:** 37 venvs under
`~/github`, **25 dangling, 12 resolving** — and every one of the twelve resolves to a `uv`-managed
interpreter or `/usr/bin`, **none through mise**. So the split is not random; it is exactly the
venvs built against the removed root. That is the census-kit obligation arriving unprompted from
the other side.

### Measured here, independently

| | |
|---|---|
| `~/.local/share/mise/installs/` | **absent** |
| `mise ls --installed` | empty |
| `mise` binary | present, `/snap/bin/mise` |
| `bazel`, `bazelisk` | **not on PATH** |
| `mdstruct/.venv/bin/python3 --version` | **exit 127** |
| `bazel-bin/mdstruct/.venv/bin/python3 --version` | **Python 3.13.13** |
| the bazel **cache** | survives, `~/.cache/bazel/_bazel_mikemol` |

⚑⚑⚑ **NOTHING IN THIS TREE FAILED OPEN, AND THAT WAS MEASURED RATHER THAN HOPED.** Two guards were
suspected and both are honest:

- `.githooks/pre-commit` tests `[ ! -x "$dist/.venv/bin/$tool" ]` over `ruff`, `mypy`, `python3`
  per distribution (**12 call sites, re-derived — the comment in `venv.bzl` says 13**) and refused
  with *"fence/.venv/bin/python3 not found — cannot run the gate, commit refused"*.
- `venv_python_for` gates on `Path.exists()`, which I suspected of admitting a dangling symlink.
  **Measured false:** `.exists()` FOLLOWS the chain and returned `False` for the dead link while
  returning `True` for the bazel-built control. The resolver is correct as written.

⚑ **AND `venv_from_hub` PAID OFF EXACTLY AS ARGUED.** Its comment states the reason directly — *an
artifact that is only valid at the path it was built at is host state with a build step in front of
it* — and the operator ruled for a whole-distribution venv over rules_python's per-target one
knowing the non-bazel consumers would depend on it. The mise root vanishing is the failure that
argument was about. **This is not a lucky side effect; it is the design's stated purpose meeting
its case.**

### The repair, by operator ruling: migrate to uv-managed interpreters

Ruled against the alternative of reinstalling mise, on the evidence that the twelve surviving venvs
under `~/github` all resolve through uv. `uv venv --python 3.13 --allow-existing` per distribution:

- uv **fetched cpython-3.13.13**, byte-matching what `venv_from_hub` pins and what the bazel venv
  reports — so the pin did not have to move.
- ⚑ `--allow-existing` REPLACED ONLY THE INTERPRETER LINKS. Every installed package survived:
  `ruff 0.16.6` and `mypy 2.3.1` still run in all four. The damage was one symlink per venv.
- **VERIFIED BY RUNNING, NOT BY `-x`** — which is this tick's own lesson, since the dead interpreter
  was `-x`-true until `execve` refused it. All **12 of 12** tool/distribution pairs print a version.

⚑⚑ **THE GATE NOW GETS FURTHER AND STILL REFUSES, HONESTLY:** all four suites run (fence 53,
hooks 417+3s, mdstruct 151, ratchet 43 — **664 tests**), then *"bazel not found — cannot run the
hermetic suite, commit refused"*. That is `linux-sources`' own fail-shut shape working as designed.

### Still open

- **`bazel` is gone and uv does not manage it.** The cache survives, so a reinstalled binary would
  find its state. Not covered by the ruling; **commits remain blocked** until it is decided.
- ⚑ **A REPLY IS OWED TO `linux-sources`:** they asked whether to file this against the other 24
  affected repos and explicitly said they would rather ask than spray. Unanswered.
- ⚑ **THE `project-tooling` SKILL IS NOW PARTLY STALE** and says so by measurement: it maps mise to
  `/usr/bin/mise` (this box has `/snap/bin/mise`) and names `~/.local/share/mise/installs/` as where
  interpreters live — the directory that no longer exists. Its uv half is exactly right and is what
  this repair followed.

### ⟐GATE-KEYS-ON-RC — NEW 2026-09-19, and the tree already held the correct predicate forty lines away

**The pre-commit gate judged `bazel test //...` by `[ $_suite_rc -ne 0 ]` alone.** `domain_witness.sh`,
in the same file's execution path, has carried `_bazel_green` — a positive predicate on bazel's own
success line plus a test tally — since 2026-09-12, with a comment explaining why the exit status is
not a verdict. **The gate did not use what the tree knew.** `linux-sources` built a three-row
discriminator from this tree's relayed rc=38 datum, shipped it in *their* gate on 09-16, and wrote to
say so; this is the same repair arriving home three days later.

| state | rc | bazel's own summary |
|---|---|---|
| green | 0 | `Build completed successfully` |
| executor absent, nothing ran | **34** | `Build did NOT complete successfully` |
| BEP upload failed, every test passed | **38** | `Build completed successfully` + `ERROR: The Build Event Protocol upload failed` |

⚑⚑ Rows 2 and 3 are both non-zero and bazel says OPPOSITE things about them. Keying on the scalar
refused row 3 — a commit whose gate bazel itself reports passing — every time the sink was down.

⚑⚑⚑ **AND THE OBVIOUS REPAIR FAILS OPEN, which the peer named before this tree could ship it.**
Keying on *"BEP upload failed" is present* passes a run where a real target also failed, because
both messages are in the log together. The repair is POSITIVE: green requires the affirmative line
AND a tally. Shipped in `.githooks/pre-commit` (staged) as `_suite_green`.

### ⟐BAZEL-GREEN-IS-A-CONJUNCTION — the same peer letter, the other half

`_bazel_green`'s tally conjunct is a **false red over any build target** — a `bazel build` with a
dead sink prints the success line and no tally, because there are no tests to tally. The peer
reproduced this on their box (BES → discard port `127.0.0.1:9`) and found `build` and `test` emit
different summary lines for one state; my relayed spelling would have missed the state it was built
for.

⚑⚑ **THE SCOPE IS STRUCTURAL, NOT A COINCIDENCE OF CALLERS.** `_bazel_green` issues `bazel test`
INSIDE itself — it cannot be handed a build label. So the conjunct is sound there and would be wrong
anywhere the invocation is `build`. *A census of callers bounds what IS; only a stated scope bounds
what CAN BE.* The scope is now stated in the function's comment and **asserted in an arm**:
`test_the_witness_reads_bazels_artifact_not_its_exit_status` requires `bazel test "$1"` inside the
function body and forbids `bazel build` there. F-armed: switching the fixed invocation to `build`
reds it by name.

⚑ Filed against this tree by the peer as `ask-bazel-summary-line-differs-by-invocation` in
`summit/floor/asks.bib`. The answer is scope, not rewrite, and it is in the tree.

### ⟐NO-CLUSTER-ON-THIS-HOST — measured, HELD by operator ruling

This host (Gentoo, 2026-09-19) has no BuildBuddy. `bep_probe.py` — **rebuilt in the tree** after its
scratchpad predecessor was erased — reports `REFUSED — nothing is listening`. `.bazelrc` hardwires
`--remote_cache` and `--bes_backend` to `127.0.0.1:31985` unconditionally, so `bazel test` returns
**rc=34** (row 2: the remote *cache* needs a capabilities handshake before any action) and every
commit is blocked. Measured that the tree is sound: with `--remote_cache= --bes_backend=` passed
per-invocation, `//:shellcheck_githooks` passes 1/1 over the edited gate.

⚑⚑ **OPERATOR RULING: wait on BuildBuddy. `linux-sources` and `cassian-observability` are bringing
up infra on luthen.** `.bazelrc` is not edited, the gate is not routed around, `--no-verify` is not
used. Seven paths are staged and survive a boundary; the dispatcher's unstaged rev 17 to
`findings/CENSUS-paperkit-use.md` is theirs and untouched.

⚑ THREE HOST INPUTS DIED ON THIS HOST IN ONE TICK: the uv interpreter root (host venvs dead again),
`shellcheck` (mise-managed), and **`pandoc`** — which is why this section was written with the
harness `Edit` rather than `mdstruct append-section`: the structural writer shells to `pandoc` on
PATH and there is none. The bazel graph stages `@pandoc//:bin` as a declared input; the host-side
tool does not, and that asymmetry is this symbol's argument arriving for the third time in one tick.

⚑ A COST ON THIS HOST, NAMED: every bazel invocation that touches the action graph invalidates the
hook venv, and the PreToolUse hook then refuses all Bash until `bazel build //hooks:.venv` is re-run.
Three rebuilds this tick. The hook is right to refuse rather than fail open; the cost is real.

### ⟐MUTATION-GATE-TARGETS — `mutate_check.sh` rewritten IN THE TREE, 2026-09-19 tick 18

The scratchpad copy died with the OS change; this one is at the repo root and staged. Shellcheck-clean
through `//:shellcheck_githooks` (the target re-executed — 2 sandbox actions — so it genuinely read the
new file; host `shellcheck` is gone). Interpreter DERIVED from `dirname` of the config, never
`realpath`'d; refuses when not `-x`; refuses on empty output.

⚑ **MEASURED ON THIS HOST, both arms:** the runner through `bazel-bin/ratchet/.venv/bin/python3`
reports **13 = 11 killed + 2 unreachable, 0 survived, 0 errored** — identical to the 09-13 baseline
through a third interpreter. And the script's precondition refuses the dead host venv by name
(`ratchet/.venv/bin/python3 was not staged`) — a real dead interpreter, not a plant.

⚑⚑ **THE RUNFILES QUESTION IS NARROWED, NOT ANSWERED.** `venv.bzl:176` returns
`DefaultInfo(files=..., runfiles=ctx.runfiles(files=outs))`, so `data = [":.venv"]` SHOULD stage
the tree — yet the 09-13 runfiles listing showed `mutants`, `pyproject.toml`, `src`, `tests` and no
`.venv` at all. The one `declare_symlink` output (`bin/python3`, line 44) could be dropped from a
runfiles tree, but that would lose one file, not the whole directory. **Whatever the cause, it needs
`bazel test` to reproduce, and the hold forbids that.** The BUILD wiring stays unwritten until 31985
answers. Written down as the next measurement, not as a hypothesis to edit in.

### ⟐SECOND-INSTRUMENT-FOR-NARROWING — CLEARED (staged) 2026-09-19 tick 19

`_population_negatives_by_binding` walks binding → assert-use, the reverse of the existing
assert → binding walk, and `test_two_walks_agree_on_every_population_shaped_negative_by_name`
asserts the two sets are EQUAL by member. Both live in `test_bar_fires.py`; the scratchpad
predecessor `vacuity2.py` is not needed and is not coming back.

⚑⚑⚑ **THE PLANT WAS CHOSEN BY MEASUREMENT, AND THE FIRST GUESS DEMONSTRATED THE WRONG THING.**
Dropping `ListComp` lost nine of thirteen — the floor caught it, so both arms red and the gap was
not shown. A one-off reader censused the binding shapes: `DictComp 1 · Call 2 · ListComp 10`.
Dropping `Call` loses exactly two, 11 clears the floor of 10, and the result is `.F` — **floor
passes, agreement reds, naming the two members and which walk dropped them.** That is F-arm C's
gap closed by a second instrument rather than a bigger assertion. Symmetric: the reverse plant
reds with the same two on the other side.

⚑ THE POPULATION IS THIRTEEN, NOT TWELVE — grown by one since 09-13 (the selector-resolution arm
from `4ab4a14`), re-derived rather than quoted. And the agreement arm's own two negatives are
counted in the population it measures, correctly: they are bound from `sorted(...)`, guarded by the
floor above them, and admitted by both walks. Fifteen with those two.

⚑ RUFF CAUGHT A COMPOSITE ASSERTION (`not A and not B` names neither half) and the split is
better: each direction of narrowing now says which WALK dropped what, because the repair differs by
direction. The plant-selection reader was deleted rather than kept — it was a probe, not a
component, and under the distribution's bar it would have been five findings.

⚑⚑ **THREE PRE-EXISTING ARMS FAILED ON THIS HOST FOR A REASON WORTH NAMING — repaired tick 20.**
`_needs_reader` guarded them on the mdstruct console script EXISTING (`is_file()`), and
`mdstruct/.venv/bin/mdstruct` exists — its shebang interpreter does not. `FileNotFoundError` against
the script, the file present: the ENOENT-names-the-wrong-artefact shape linux-sources measured,
inside this tree's own guard.

### ⟐READER-GUARD-TESTS-PRESENCE-NOT-RUNNABILITY — CLEARED (staged) 2026-09-19 tick 20

The predicate is now `_reader_runs()`: an invocation of the reader with `--help`, where any exit
proves `execve` accepted it and `OSError` is the corpse. On this host the three arms now SKIP with a
reason that names present-but-unrunnable, where they FAILED blaming a present file. **Three skipped
arms with a stated reason is the honest state on a host without the reader; three failed arms
blaming the wrong file is not.**

⚑⚑ **BOTH ARMS OF THE GUARD, IN THE TREE, HOST-INDEPENDENT.** `test_reader_guard.py` builds a
live reader (shebang `/bin/sh`) and a corpse (shebang at a path that does not exist, mode 775,
`is_file()` true) and asserts the predicate admits one and skips the other. The corpse is
CONSTRUCTED, not found — pointing at the host's actual dead script would make the arm's verdict
depend on which host it runs on, the exact coupling the guard exists to survive. F-armed: making
the predicate ignore `OSError` reds the dead-shebang arm and only that arm.

⚑ Ruff surfaced six findings in the new module and mypy one; all repaired structurally — the
`subprocess` import declared per-file in `pyproject.toml` with the reason (the guard's subject IS
execution), `Path` moved to a type-checking block, docstrings given Returns sections. No noqa beyond
the one call-site directive the file's convention already uses.

⚑ NINE OTHER ARMS FAIL ON THIS HOST and none is this change: `fence/.venv` not built here, the hook
console scripts absent from the dead host venv, `test_adoption`'s probe venv refused by the bazel
interpreter's missing `exec_prefix`. Host state, each — and each the same class as the one just
repaired, which is why they are listed rather than fixed in this tick.

### What the boundary erased, so it is not re-derived from nothing

The OS change moved the scratchpad and emptied it. Lost: `await_bep.py`, `mutate_check.wip.sh`,
`mutate_runner.wip.py`, `vacuity2.py`, every F-arm plant, every probe. ⚑ **Census-kit B5, measured
the expensive way:** a handle only survives if its referent lives outside the context. `bep_probe.py`
is the first instrument rebuilt in the tree; the mutation gate wiring (`mutate_check.sh`) must be
rewritten the same way — shellcheck-clean, interpreter derived from `dirname` of the config, NOT
`realpath`'d.

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

### ⟐EXE002-REMOTE-ONLY — the measurement that preceded the fix (CLEARED; see the section above)

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

### ⟐REMOTE-DISCARDS-MODE-BITS — a STANDING property of the CAS, not a defect that was fixed

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

### ⟐RUF201 — DISCHARGED; this was a SECOND live section for one symbol

⚑⚑⚑ **THIS DOCUMENT CARRIED TWO ⟐RUF201 SECTIONS, BOTH IN THE PRESENT TENSE, AND NEITHER KNEW
ABOUT THE OTHER.** The section above held the measurement and the ruling; this one held a summary —
*blocked on a preview-wide paydown … the poll prints the command that measures it* — and the poll
stopped printing that command the same day the paydown finished. A reader scanning headings meets
whichever comes first.

⚑⚑ **A SUMMARY OF A LIVE ITEM IS A SECOND PLACE FOR ITS STATUS TO ROT, and it rots faster than the
original** because it carries no measurement to contradict it. The full section is above; this stub
remains only so a reader who followed a line reference here is not left wondering whether a third
account exists.

### ⟐MD056-CORPUS-12 · ⟐VACUITY-CEILING · ⟐CLASSIFY-SPANS-ALL-TABLES

Carried. MD056: 12 ragged rows, all measured out of reach (frozen leg directories, filed
legs). Vacuity: the poll now prints a CEILING, honestly labelled, not a count.

⚑⚑⚑ ⟐CLASSIFY-SPANS-ALL-TABLES — **CLEARED 2026-09-12**, and the cost of carrying it was
larger than the note suggested. The note said only *"walks every table without disclosing its
span"*. Measured: on `findings/CENSUS-remaining-work.md`, which carries FOUR tables of entirely
different kinds — a surveyor roster, a revision log, a status table, and the state vocabulary
itself — unscoped `classify` reports **56 rows, 48 UNCLASSIFIED**. Scoped to the one table that
carries statuses: **8 rows, 0 unclassified**.

⚑⚑ SO THE UNDISCLOSED SPAN DID NOT MERELY WITHHOLD CONTEXT, IT MANUFACTURED A FINDING. A reader
seeing 48 unclassified infers a documentation gap in the census; the true answer is that 47 of
those rows are from tables the question does not apply to. A revision-log row was never meant to
carry a state.

⚑ THE RESIDUE GROUP WAS ALREADY PRINTED AND THAT WAS NOT ENOUGH. Reporting the unclassified
count without saying WHAT WAS READ describes a defect in the DOCUMENT; naming the tables
describes a defect in the QUESTION. The tool's own stated rule — every mode prints its
denominator — was half-kept: a count of rows is half a denominator, and which tables they came
from is the other half.

### ⟐PEER-MDSTRUCT-CLAIMS — three claims measured 2026-09-12; ONE REAL, TWO FALSE

`linux-sources-94` filed three claims about mtools' mdstruct. Measured before acting on any:

**FALSE — "`hooks/src/mikemol/hooks/no_chaining.py` routes to substrate's mdstruct."** The line
at `no_chaining.py:18` is a DOCSTRING citing a 2026-09-06 PIPESTATUS incident. It is prose about
a past measurement, not a route. Nothing in `hooks/` invokes any mdstruct.

**FALSE — "25 references to `scratch/mdstruct` are live routes."** All 25 hits are findings-corpus
PROSE — a recorded measurement naming where the instrument stood when it was measured. ⚑ Rewriting
them would falsify the record, which is the opposite of the migration's intent.

⚑⚑ BOTH FALSE CLAIMS HAVE ONE SHAPE: **a grep hit read as a route.** A reference to a tool inside
a docstring, a finding, or a commit message is a FACT ABOUT THE PAST, and the query that finds it
cannot distinguish it from an invocation. This is the repository's own recurring shape — a
plausible reading pointing at the wrong subject — arriving from outside it.

**REAL and CLOSED at `7e4134e` — `find_section` had no `exact=` escape.** The peer's phrasing is
exact and is quoted in the code: *a correct refusal a caller cannot escape is a dead end*. The
measurement was 27 substrings of `Residue`, all failing against a document whose other heading
contains it. `exact=` lands on `find_section`, `replace_section` and `append_to_section` — all
three, on operator ruling, spelled as substrate's `md_spans` spells it.

⚑ The routing table at `.claude/skills/struct-tools/SKILL.md:25` ALREADY names
`mdstruct/.venv/bin/mdstruct` — mtools' own build, not substrate's. The repoint the peer asked for
had already landed; the claim was made against a stale reading of this tree.

⚑ **Recorded here as well as replied, on operator ruling ("Both"):** the correction reaches the
peer before they act, AND this tree keeps the measurement for the next reader who greps
`substrate` and finds 25 hits. A correction that lives only in a message is a correction the next
vantage does not inherit.

### ⟐MDSTRUCT-CLI-HAS-NO-WRITER — NEW 2026-09-12, measured while filing the section above

⚑⚑⚑ **The structural-query hook routes WRITES to a tool whose CLI cannot perform them.** Its
refusal says, correctly, *"the owning tool is the route for WRITES TOO: `mdstruct/.venv/bin/mdstruct`"*
— and `mdstruct --help` lists eleven modes, **every one of them a READER**. `replace_section` and
`append_to_section` exist in `sections.py` and are reachable only as a library import.

Measured by running the tool, not by reading it: attempting to file this very section hit the
refusal, then found no mode to obey it with. The declared fallback (`Write`/`Edit`, for when the
owning tool is unavailable) is what wrote it — which is honest, but the tool is not *unavailable*,
it is *incomplete*, and those should not resolve to the same escape.

⚑ SAME SHAPE AS ⟐PEER-MDSTRUCT-CLAIMS' real claim, one layer up: a gate that names a successor is
only half a gate if the successor has no mode for the job. The refusal is correct; the route it
names is a dead end for writes.

⚑⚑ AND THE CENSUS THAT PRODUCED "eleven modes, all readers" WAS ITSELF COMPUTED FROM THE
UNDER-REPORTING BANNER. `--help` listed ten modes while the registry held eleven; `verify` —
registered, green, and named by the routing table's own *"`verify` before any bounded write"* —
was absent from the usage text. Fixed at `b554842` with an arm that drives BOTH surfaces as
subprocesses and compares what each PRINTS. ⚑ A tool with two spellings of its own capability list
will drift, and **the hand-written one is the one adopters read**: a mode absent from `--help`
reads as a mode the tool does not have, and the honest conclusion from that reading is to keep
using the other implementation. An under-reporting tool loses an adopter without ever failing.

⚑⚑⚑ AND I MISCOUNTED THE REFUSAL WHILE FIXING IT — *12 and 11*, wrong in both terms, shipped in
the commit message and the warrant. I read the comma-separated list BY EYE rather than running a
counter, inside the repair whose subject is a hand-maintained figure drifting from a derived one.
`linux-sources-94` re-measured and reported 11; the registry literal holds 11. Corrected in the
warrant and the arm's docstring. ⚑ The lesson is not *count more carefully*: a count stated in
prose is the same object as the banner, one layer up, so the arm asserts a RELATION between two
live surfaces and never a cardinality.

⚑ `verify` IS THE DETECTOR FOR THE CLASS SUBSTRATE'S READER HAS, reported by `linux-sources-94`
after running it on `TICK.md` after every structural edit: it answers *did every source heading
reach the section list* directly, and a silently-swallowed heading is exactly substrate's defect.
So the tool without the defect carries the instrument that finds it — worth knowing when the
migration argument is made on grounds other than provenance.

⚑⚑⚑ OPERATOR RULING 2026-09-12, BOTH AXES — the writer is UNBLOCKED. **Subcommands**, and
**needle before file**, matching `grep`.

⚑ THE SUBCOMMAND RULING CONFIRMS THE EXISTING SURFACE RATHER THAN CHANGING IT, which is a fact
about this tree measured before the ruling was applied: `mdstruct spans FILE.md` is already a mode
name then arguments. So the migration cost falls on SUBSTRATE, whose `md_spans` is flag-style
(`--headers --tables --rows`) — the peer's "aliases vs convert once" trade was about their call
sites, not a change to mine.

⚑⚑ NEEDLE-FIRST IS THE ONE-RULE ANSWER AND IT COSTS NOTHING TO REACH. `grep PATTERN FILE.md` is
the only existing two-positional mode, and it takes the subject before the file because real
`grep` does. So `replace-section HEADING FILE.md` gives the tool ONE convention for every
two-positional mode with no existing call site broken. The alternative — file first, reading
naturally for a writer — would have left `grep` as the odd one out or required re-spelling it,
which is a migration for peers already using it.

⚑ WHAT IS STILL OWED, and it is implementation rather than decision: the write modes must carry
`exact=` (the ambiguity refusal and its escape compose at the write path — see the section above),
and the body has to arrive as a file rather than an argument, because a shell that can pass a
multi-line body inline is the `>>` this toolkit refuses.

### ⟐THREE-CLIS-NO-SHARING — NEW 2026-09-12, measured when the operator asked about a shared module

⚑⚑⚑ THE OPERATOR ASKED WHETHER SUBSTRATE'S `cli` MODULE — *"everything was supposed to normalize
around"* — MADE IT OVER. Measured: **no, and the split is worse than its absence.**

    fence/src/mikemol/fence/cli.py        argparse
    ratchet/src/mikemol/ratchet/cli.py    argparse
    mdstruct/src/mikemol/mdstruct/cli.py  HAND-ROLLED (_MODES dict, manual _flag parser)
    hooks/                                no cli module at all

**Three CLIs, zero sharing, TWO argument frameworks.** mdstruct is the odd one out in its own
tree: its `_flag()` helper re-derives `--name value` / `--name=value` handling that `argparse`
already does, one directory from two modules that use `argparse`.

⚑⚑ AND THIS IS THE MEMBERSHIP CRITERION'S OWN CASE, arriving from the inside. The rule is *reuse
across repos, not repo-local* — and here is machinery re-derived THREE TIMES within ONE repo,
which no cross-repo criterion would ever surface. A dispatcher is not repo-local by any reading;
it was simply never interned, because each distribution authored its own on the way to its first
green.

⚑ IT CHANGES WHAT THE WRITER IS BUILT ON. The ruling above says subcommands, and `argparse` has
first-class subcommand support (`add_subparsers`) that both siblings already use. So *"confirm
mdstruct's existing surface"* and *"normalize on the shared mechanism"* are not the same
instruction, and building `replace-section` onto the hand-rolled dispatcher would author the
surface twice if the second is intended. ⚑ ASKED `substrate-9c` DIRECTLY rather than inferring:
what the module is, whether it is domain-neutral, and whether it can actually SHIP — the ratchet
island qualified on merits and was blocked on mechanics, and a normalization point that cannot
land is one mtools must provide locally instead.

⚑ NOT RESOLVED BY ADOPTION. If substrate's module carries an argument order or dispatch shape
disagreeing with the operator's ruling, the RULING wins here and the divergence is recorded — a
convention is not authority, and reconciling quietly to a peer's shape would be gluing with no
witness.

⚑⚑⚑ ANSWERED 2026-09-12, AND THE ANSWER IS: ADOPT NEITHER MODULE'S DISPATCHER, BUILD THE GATE.
`substrate-9c` disclosed two modules and the accounting for this tree is not what either of us
assumed.

`climode` is NOT a parser — it declares per-mode contracts (`operand`, `paths`, `opts`, `scans`,
`writes`, `why`) that a gate checks. So *"argparse or climode"* was a MALFORMED question and it
was mine. It sits beside argparse rather than instead of it.

`bib_modes` is the generic dispatcher, surfaced only after the operator named it — substrate
searched for the word `cli` that I used rather than the capability I described, which is the
census-keyed-on-one-spelling defect inside a reply about avoiding duplicated capability. ⚑ ITS
COUPLING IS WORSE THAN `climode`'s AND SUBSTRATE SAID SO UNPROMPTED: `dispatch` is generic in the
HANDLER but reads a module-level `MODES` global that is bibstruct's own roster — a dispatcher for
one tool wearing a generic signature. Porting is parameterising the roster, a real edit.

⚑⚑ AND ITS HEADLINE FEATURE DOES NOT APPLY HERE, measured rather than accepted. `unbound()`
reports *declared-without-handler* and *handled-without-declaration* separately, and substrate
believed mtools lacked the second. **It cannot have it.** `_MODES` is a SINGLE dict literal, so
the roster IS the handler table — one definition, one lookup, one derived refusal (`grep -n
_MODES` → three sites, and two are uses). A handler with no declaration is unconstructible. Their
`unbound` exists because bibstruct's roster and handlers are separate objects; this defect is
structural to their layout, not general.
⚑ THE DRIFT THAT DOES EXIST HERE IS ONE LAYER OVER AND IS ALREADY ARMED: the hand-written BANNER
is the second spelling, and `f235328` asserts `dispatchable == documented` in both directions.
That is `unbound()` aimed at the drift this tree actually has.

⚑ SO `bib_modes` SUBSUMES: a 3-line dispatch that is already correct, and a refusal already
derived. It does NOT subsume `_flag()` — deliberately, since neither substrate module parses argv
— and `_flag()` is the piece carrying the real defect below. **Two of three, both already solved.**

⚑ NO CLI-SHAPE CONFLICT, confirmed from their side: neither module has an opinion about argument
order. `bib_modes` assumes only that a mode is keyed by a STRING, and whether that string is
`--spans` or `spans` is opaque to it. The operator's ruling lives entirely in the entry point.

### ⟐DASH-LEADING-NEEDLE-IS-EATEN — NEW 2026-09-12, and it BLOCKS the writer

⚑⚑⚑ `main` FILTERS EVERY TOKEN STARTING WITH `-` OUT OF ITS POSITIONALS, so an argument whose
text begins with a dash is silently discarded and the arguments after it SHIFT LEFT. Measured
against the real program, twice:

    mdstruct grep '-- caveats' FILE.md   → usage error: the needle vanished
    mdstruct grep -- '-- caveats' FILE.md → same — `--` is stripped like any other dash token

**There is no end-of-options mechanism at all.**

⚑⚑ FOR A READER THIS IS A BAD RESULT; FOR A WRITE IT IS THE SILENT-WRONG-TARGET CLASS. `grep`
survives only because its arity check catches the collapse. `replace-section HEADING FILE.md
--body-file X` with a dash-leading heading leaves `args = ["replace-section", "doc.md"]` — a
VALID two-element shape — so the FILE lands in the needle slot and the write proceeds against a
target the caller never typed. That is precisely what the ambiguity refusal and `exact=` exist to
prevent, defeated one layer below them, before `find_section` is ever called.

⚑ A HEADING BEGINNING WITH PUNCTUATION IS NOT EXOTIC — this very document has `⟐`-prefixed
headings, and `-`-prefixed ones are ordinary in changelogs. The existing modes never hit this
because a PATTERN that looks like a flag is unusual; a HEADING that does is not.

⚑ SO THIS IS THE FIRST WORK ITEM OF THE WRITER, not a follow-up: positional-aware parsing with a
real `--` terminator. ⚑⚑ AND IT IS THE ARGUMENT FOR `argparse` ON THE MERITS RATHER THAN FOR
CONSISTENCY — `argparse` gives `--` for free, both sibling distributions already use it, and
`_flag()` is a hand-rolled re-derivation that got this wrong. Neither substrate module helps:
they do not parse argv, by design.

### ⟐DECLARE-THE-PARTIAL · ⟐MUTATION-LAYER — OPERATOR RULING 2026-09-12: BOTH

Four shapes of green-but-vacuous arm measured across two trees in three days. Each is green under
every checker either tree has, and each is a TRUE statement about something other than its subject:

| shape | where the not-running happens | measured by |
|---|---|---|
| a PATH never reached | before the code | cassian — a run bailed on an unrelated precondition |
| a BUILDER never shipped | between code and consumer | mtools — arms on a builder nothing shipped |
| a POPULATION never populated | inside the derivation | mtools — a set empty for unrelated reasons |
| a POPULATION filtered empty | inside the traversal | cassian — a false ordering premise, ten days of logs lost |

⚑⚑⚑ THE OPERATOR SENT ME TO ASK `paperkit-82` HOW THEY DO MUTATION TESTING, and the answer is
valuable because it is UNFLATTERING to the thing I was sent to ask about. Against `body → raise`
at def-site granularity: **one of the four caught, three missed.** Their phrasing, kept because it
is the whole finding — *mutation testing at this granularity tests whether your test EXERCISES
code, not whether it MEASURES anything.* Three of the four are POPULATION defects: the data an arm
gathers rather than code it runs, and no def-site mutation can express *return a differently
ordered list*.

⚑⚑ SO THE RULING IS **BOTH**, and they are separable work answering different questions.

**⟐DECLARE-THE-PARTIAL — first, because it is small and catches three of four.** paperkit's own
name for the construction, and they point at it rather than at their framework: *the defect is
never emptiness, it is UNDECLARED emptiness.* An arm asserts its population is non-empty AND that
its members are what the arm believes, printed. This tree already has the shape in places — the
guard at `01f1450`, the shell-consumer assertion — and nowhere as a rule.
⚑ AND SOURCE-SIDE NON-EMPTINESS IS NECESSARY, NOT SUFFICIENT. The fourth shape passes it: every
source was non-empty throughout and the TRAVERSAL was wrong. Catching that needs the output
asserted non-empty given a known-non-empty input, or two instruments compared.

**⟐MUTATION-LAYER — its own arc, and the cost is architectural rather than compute.** paperkit's
three reusable ideas, none of which require bazel:

- the mutant as a CACHED, CLAIM-INDEPENDENT build artifact — N claims × M sites costs M builds
- content-addressed bytecode (PEP 552 `UNCHECKED_HASH`, no mtime) so a CAS replays it across runs
- a fingerprint keyed by MEMBER IDENTITY rather than a kill score

⚑ THEIR MEASURED RETURN IS THE ARGUMENT: on a 223-claim census, **6 claims pass with an empty
sensitivity set** — they cannot be shown to fail, and every one was green under every other check
for as long as it existed. 206 behavioural, 10 refuted, 1 unreachable, 6 vacuous.
⚑⚑ AND THEIR RECORD HAS HALF THE RATCHET I WOULD WANT, which they volunteered: the fingerprint
names the KILLED sites, so a site absent from it either survived or was never mutated and the
record cannot say which. Absent ≠ surviving. That is the half to build differently here.
⚑ THE PRICE THEY PAID was turning their engine into per-module bytecode targets with a declared
import DAG before one mutant could be built. Not to be discovered mid-arc.

⚑ ONE ARM IS WRITTEN, MEASURED, F-ARMED AND WITHHELD pending this layer: a cross-instrument
agreement check comparing an arm's parsed population against `count_test_functions.py`. Its F-arm
reported *parsed 316, counter reported 313* — the fourth shape caught with a NON-EMPTY population
on both sides, which no source-side guard can do. It is withheld only because it pushed the string
sweep's unresolvable ceiling from 22 to 23, and that ratchet may only DECREASE. It returns when an
instrument admits it without a raise.

#### ⚑⚑⚑ ⟐DECLARE-THE-PARTIAL IS BUILT AND HELD — operator ruling 2026-09-12, the SECOND hold

Written, F-armed both ways, and withheld at the operator's ruling for the same reason as the
agreement arm before it: it reads files through a LOOP VARIABLE rather than a module-level target,
so the older string-membership sweep cannot resolve it and its unresolvable ceiling would go
22 → 23. **That ratchet may only DECREASE.** Held pending ⟐MUTATION-LAYER, which is the instrument
that admits both without a raise.

⚑⚑ WHAT IT MEASURED, so the arc inherits measurements rather than a description:

- **12 population-shaped negatives in this tree, all named and all guarded.** Not a count — the
  arm prints its whole swept population on a green run, which is `paperkit-82`'s second idiom
  (*the count in the description*): a reader sees the members whether it reds or not, so a sweep
  that quietly narrowed is visible before it matters.
- **F-arm A:** a planted `assert not offenders` over an unguarded comprehension REDS, names the
  planted arm, and prints all 13 beside it.
- **F-arm B:** emptying the classifier entirely REDS on the vacuity guard.
- ⚑ **F-arm C EXPOSED A REAL LIMIT AND IS RECORDED RATHER THAN GLOSSED.** Replacing the
  comprehension types with `pyast.Lambda` left 12 of 13 still admitted through the CALL branch,
  and the arm PASSED. So the guard catches a classifier that recognises NOTHING and not one that
  NARROWS: the floor is *the shape is still recognised at all*, never *recognised completely*.
  The stronger check is a second instrument, not a bigger assertion — the fourth vacuity shape
  arriving inside the sweep built for the third.

⚑ TWO IDIOMS TAKEN FROM `paperkit-82`, who ran my sweep's earlier shape against their own suites
and returned 1-in-10 precision against my 1-in-4 — WORSE, which is what made the report useful:

- **a VERDICT is not a POPULATION.** 26 of their 36 candidates were ⟨F⟩ arms — `assert not
  analyze(cmd)` says *this input must not fire*, and one call's answer cannot be empty. No syntax
  carries that distinction, so the exclusion list is declared and named rather than inferred.
- **the guard may sit AFTER the negative.** Two of my four original candidates were guarded by
  arms immediately below them; a position-sensitive check reported its own blind spot as a finding
  about the suite.

⚑⚑ APPLYING BOTH, THE SWEEP RETURNS **12 population-shaped, 0 undeclared** — the one real instance
having been fixed at `01f1450`. The refined sweep is in the scratchpad as `vacuity2.py`; the arm
itself is reconstructable from this section and the two F-arm results above.


#### ⚑⚑⚑ LANDED at `19432cc` — operator ruling 2026-09-13, and the hold's two halves came apart

**CLEARED.** The arm is in the suite as
`test_every_population_shaped_negative_is_guarded_against_being_empty`, warranted, with all three
F-arms re-run against the shipping code.

⚑⚑ **THE HOLD HAD A REASON AND A RELEASE CONDITION, AND ONLY THE REASON WENT VOID.** Stated above:
withheld because a loop-variable read would push the old sweep's unresolvable ceiling 22 → 23, and
*that ratchet may only DECREASE* — **held pending ⟐MUTATION-LAYER**. Measured at `433c1ce`: that
sweep was replaced at `aab9f8b`, `population_sweeps` is now a declared printed category with no
ceiling, and `_MAX_UNRESOLVED` has no arm comparing any population against it. So landing it could
ratchet nothing. **But ⟐MUTATION-LAYER is still a scratchpad probe, so the release condition was
never met.**

⚑ **A TRIGGER IS NOT A RELEASE CONDITION, AND THAT DISTINCTION WAS MEASURED ELSEWHERE THE SAME
DAY.** `cassian-observability-6a` read a kubelet's eviction trigger (5%) as its release condition
(15%) and got a wrong diagnosis out of it. A void reason is not a lifted hold — so this was put to
the operator rather than inferred, and the ruling was **land it now**.

⚑⚑⚑ **RE-MEASURING F-ARM C CHANGED WHAT THIS SECTION RECORDS, AND THE CORRECTION IS THE FINDING.**
Above, F-arm C is written down as a real limit: narrowing the classifier to `pyast.Lambda` left
*12 of 13 admitted through the CALL branch and the arm PASSED*, generalised to **a floor catches a
classifier recognising NOTHING, never one that NARROWS.** Re-run here, the equivalent plant —
keep the CALL branch, drop the comprehensions — **REDS at `2 >= 10`.**

The generalisation was too strong. This suite's population negatives are overwhelmingly
comprehensions, so dropping that branch removes ten of twelve rather than one of thirteen. **The
floor's reach is a fact about the CORPUS, not about the floor:** it catches a narrowing exactly
when the narrowed-away shape is most of the population, and a floor of 10 over 12 members tolerates
losing two. That bound is real, the arm does not claim past it, and the stronger check is still a
second instrument rather than a bigger assertion.

⚑⚑ **TWO INSTRUMENTS AGREED ON MEMBERSHIP RATHER THAN ON A COUNT** — the discipline three
near-misses this session were about, two of which agreed by luck. `scratchpad/vacuity2.py` sweeps a
HAND-WRITTEN root list and reports 12; the landed arm GLOBS `*/tests/test_*.py` and reports the
same 12 **by name**. The arm's own population was read by forcing its floor negative and reading
what it printed, rather than by re-implementing the walk a third time.

⚑ **RUFF AND MYPY EACH FOUND A REAL DEFECT IN THE LANDING, BOTH REPAIRED STRUCTURALLY.** Complexity
11 > 10 plus two undocumented returns, answered by hoisting `_population_negatives` and `_guarded`
to module scope; then `disallow_any_expr` on `isinstance(src, X | Y)`, whose `UnionType` expression
types as `Any` — an untyped expression deciding a classification, which is what `payload.py` carries
nine warrants about. The tuple form is the same test, fully typed. No waiver, no `noqa`.

⚑ **STILL OWED, AND NOT BLOCKED BY THIS:** ⟐MUTATION-LAYER-DURABLE remains a scratchpad probe. It
was this hold's release condition and is now simply the next item, carrying its own argument —
136 def-sites, 11 survivors all closed, and paperkit's ATTEMPTED-beside-KILLED correction.


#### ⚑⚑⚑ ⟐MUTATION-PROBE-COUNTS-ERRORS-AS-KILLS — found and repaired at `6143c7d`, and it was in the probe this section quotes

**The precondition for promoting the probe, discovered by reading the artifact rather than this
record.** `scratchpad/mutate_probe.py` sorted every mutant with
`(killed if proc.returncode else survived).append(name)`, while `errored` was bound, printed in
the report, and **never appended to** — three references, no writer.

⚑⚑ **A POPULATION NEVER POPULATED — the third of the four shapes tabulated above — inside the
instrument built to find them.** A mutant that cannot import returns non-zero and was recorded as
KILLED, crediting the suite with noticing something it never ran. That is `paperkit-82`'s own
correction arriving from the opposite side: their fingerprint names only KILLED sites so *absent ≠
surviving*; this one folded ERRORED into KILLED, the same ambiguity with the opposite sign, and it
**flatters** rather than under-reports.

⚑ **THE OBVIOUS REPAIR DOES NOT WORK, MEASURED.** pytest's exit codes are documented as separating
tests-failed (1) from internal error (3) and no-tests-collected (5). Across four shapes, all three
non-zero cases return **rc=1** — a collection error prints `1 error` rather than carrying a
distinct code. The discriminator is the terminal summary line: weaker than an exit code, and the
one that exists. Keying on `rc` would have been a second wrong answer wearing a measurement's
clothes.

⚑⚑ **RE-MEASURED WITH THE REPAIRED CLASSIFIER, AND THE FIGURES IN THIS SECTION SURVIVE:**

```
cli.py    ATTEMPTED 28   killed 28   survived 0   errored 0    40.4s (1.4s/cell)
core.py   ATTEMPTED  8   killed  8   survived 0   errored 0     4.4s (0.5s/cell)
```

The recorded survivors — mdstruct 10, fence 1 including `core.ratchet` — were real and are now
closed. **No figure this section quotes was inflated by the defect: the conflation was live but
never fired on this corpus.** Still a defect, because nothing was keeping it unexercised.

⚑ **AND THE ATTEMPTED SET THIS SECTION ASKED FOR IS NOW ASSERTED RATHER THAN CARRIED.** The probe
raises unless `killed + survived + errored` is exactly `attempted`, naming any unclassified site,
and prints the ERRORED section **when empty** — the predecessor hid it behind `if errored:`, so a
reader could not distinguish *none occurred* from *never populated*, which is precisely the gap the
defect lived in.

Full account, with the five-shape F-arm and the measurement that refuted the exit-code premise:
`findings/mutation-probe-errors-as-kills.md`.

⚑⚑⚑ **SO ⟐MUTATION-LAYER-DURABLE IS UNBLOCKED AND ITS PRECONDITION IS NAMED: do not promote a
probe with a known defect — that is how a defect becomes a component.** The architecture argument
above stands unchanged (AST rewrite into a temp tree, 45 cells, no caching layer, do not import
paperkit's build layer); what changes is that the thing being promoted now distinguishes three
outcomes instead of two.


#### ⚑⚑⚑ PROMOTION ATTEMPTED 2026-09-13 AND DELIBERATELY NOT LANDED — operator ruled the SHAPE, and the build found three things

**Operator ruling: a gate target, per distribution** — `sh_test`/`py_binary` per distribution so the
DAG decides when the grid re-runs, unchanged sources meaning a cache hit. That settles the design
question this section carried; what follows is what building it measured.

⚑⚑ **THE COST IS NOT THE PROBLEM, AND THAT IS NOW MEASURED PER DISTRIBUTION RATHER THAN ASSERTED:**

| distribution | modules | def-sites | per cell |
|---|---|---|---|
| ratchet | 4 | 13 | 0.2s |
| hooks | 10 | 56 | 0.4s |
| fence | 3 | 25 | 0.5s |
| mdstruct | 12 | 64 | 1.4s |

**158 def-sites, under four minutes whole-tree.** ⚑ AND THE WIP'S RECORDED FIGURE WAS **136** — stale
by 22, quoted across at least six ticks. Nothing was wrong when written; the tree grew and nothing
re-derived it. `-x` means a KILLED cell stops at the first failing test, so only SURVIVORS pay a
full suite — the opposite of the profile paperkit's caching layer exists for.

⚑ **AND THE RUNNER IS NOT LANDED, DELIBERATELY.** It reports **all 64 of mdstruct's def-sites as
ERRORED**, which is a whole-distribution failure and therefore a defect in the runner rather than a
finding about the suite. ⚑⚑ `run()` and `verdict()` classify the same mutant as **KILLED** when
called directly — traced, with the mutant's `AssertionError` in the output — so the defect is
somewhere in `main()`'s loop and is NOT yet diagnosed. Landing it would be exactly what the
preceding section forbids: *do not promote a probe with a known defect.* The work-in-progress is at
`scratchpad/mutate_runner.wip.py`.

⚑⚑⚑ **MY FIRST DIAGNOSIS OF THAT FAILURE WAS WRONG, AND I REASONED IT RATHER THAN MEASURING IT.**
I ran `which pandoc`, found `~/bin/pandoc`, concluded the runner's pinned `PATH=/usr/bin:/bin` was
starving mdstruct's suite, and changed the code. Re-run: **identical 64 ERRORED.** A repair to
something that was not the defect. ⚑ The reason it was believable is that my standalone
reproduction *worked* — because it RECONSTRUCTED `run()` by hand instead of calling it, and so
differed from the real path in ways invisible to me. **A reproduction that is not the code under
test is a second instrument**, which is this session's most-repeated defect arriving in the probe
built to diagnose a defect.


#### ⚑⚑⚑ THE RUNNER'S DEFECT IS DIAGNOSED at tick 10, AND FOUR WRONG DIAGNOSES CAME FIRST

**Not a whole-distribution failure. ONE TEST MODULE fails collection, and `-x` aborts the rest.**
The framing "all 64 def-sites ERRORED" was true as a count and wrong as a description, and the
wrong description is what sent four diagnoses into the environment.

⚑⚑ **THE MECHANISM, MEASURED:** `mdstruct/tests/test_cli_flags.py` imports the CLI module **at
module scope** (line 66, `_CLI_SOURCE = Path(str(_cli_module.__file__))`), and the CLI imports
`panflute`. In the mutant's temp tree that import resolves against the copied `src` and fails with
`ModuleNotFoundError: No module named 'panflute'` — at COLLECTION, before any mutated code runs.
So every cell reports ERRORED for a reason that has nothing to do with its mutation.

⚑ **AND THE ASYMMETRY EXPLAINS WHY IT LOOKED LIKE A WORKING RUNNER.** Measured:
`mdstruct` declares `dependencies = ["panflute"]`; `ratchet` and `fence` declare `[]`. The two
distributions the runner was validated on are exactly the two that cannot exercise the defect —
**a probe validated on the corpora that could not refute it**. `hooks` would fail the same way.


#### ⚑⚑⚑ FIVE HYPOTHESES REFUTED, THE REPAIR STILL NOT WRITTEN, AND THE PROBE HAD TO BE FIXED THREE TIMES

**Tick 11 spent on the repair and produced NEGATIVES, not a fix.** Filed because a set of
eliminated causes is a real result and because the next tick must not re-walk them.

⚑⚑ **WHAT IS NOW ELIMINATED BY MEASUREMENT, each against the mutated tree:**

| candidate | measured |
|---|---|
| the temp tree itself | **151 passed** unmutated — the copy is sound |
| the runner's env (PYTHONPATH + HOME) | mutated control **`1 failed, 73 passed`** — a KILL, correctly |
| (3) PYTHONPATH + venv site-packages | same KILL — no improvement, nothing to fix |
| (2) symlink site-packages beside temp/src | same KILL |
| (1) `pip install -e` the temp tree | same KILL |
| empty `__init__.py` deletion | **no empty markers exist** in the distribution — a no-op |
| inherited `PYTHONPATH` from the parent | **unset** — the tick-10 append branch is inert |
| temp-disk exhaustion | 64 GiB free; each copy is 8.4 MiB and is freed per cell |

**So every named difference between the probe and the runner is eliminated, and the probe
reproduces a correct KILL where the runner reports `ModuleNotFoundError`.** The mechanism is not
established. My model of the runner is wrong somewhere I cannot yet name.

⚑⚑⚑ **AND THE PROBE ITSELF WAS WRONG THREE TIMES, EACH CAUGHT BY ITS OWN CONTROL.** This is the
part worth keeping:

1. **`--collect-only`** — the control COLLECTED cleanly, so all four rows read identically and the
   probe discriminated nothing. Its own docstring says *the control must fail or this measures an
   unbroken tree*, and it measured an unbroken tree on the first run.
2. **No mutation** — the control PASSED 15 of 15, because the runner REWRITES a source through
   `ast.unparse` before running and the probe did not.
3. **One module instead of `tests`** — still passed. Naming the directory is what the runner does,
   and only then did the control finally FAIL.

⚑ **THREE DRAFTS, EACH DIFFERING FROM THE CODE UNDER TEST IN ONE ARGUMENT, AND EACH PASSING
BECAUSE OF IT.** That is the second-instrument defect four deep in one session — and the only
reason it was caught each time is that the probe carried an explicit control with a stated
required outcome. **A probe without a must-fail control cannot tell you it is measuring nothing.**

⚑⚑ **LOAD-DEPENDENCE: TESTED AND REFUTED.** The host is under real pressure (`MemAvailable
2.05 GiB`, `psi memory avg10=6.18`, zram holding 4.89 GiB in 1.16 GiB), and the probe runs 4 cells
where the runner runs 64 — so accumulation was the one variable the probe could not hold constant.
**Measured: the FIRST cell fails, at 0.05s.** Not accumulation, not exhaustion.

⚑⚑⚑ **AND 0.05s IS ITSELF THE SHARPEST REMAINING CLUE, RECORDED RATHER THAN CHASED.** The probe's
equivalent run takes 2.5–3s and reaches a real KILL. A failure returning in **0.05 seconds has not
imported anything** — it is too fast for the interpreter to have reached `panflute` at all. The
error path also changed with the tick-10 rootdir fix, from `../../../github/mtools/mdstruct/
test_cli_flags.py` to `tests/test_cli_flags.py`, so the config now resolves inside the temp tree
and the failure moved with it rather than disappearing.

⚑ **WHAT IS STILL NOT EXPLAINED: the probe and the runner now agree on the copy (identical
`ignore_patterns`), the config path, the environment, the mutation, and the target (`tests`) — and
one takes 3s to a KILL while the other takes 0.05s to a ModuleNotFoundError.** Something differs
that I have not named, and naming it is the next tick's first job. The candidate worth testing
first is whatever makes a 0.05s failure possible: an import that fails before `sys.path` is
consulted at all.

⚑ **THE RUNNER STAYS UNLANDED.** Five refuted hypotheses do not make a repair, and the rule that
kept it out of the tree two ticks running is the same one: do not promote a probe with a known
defect.


#### ⚑⚑⚑ THE SANDBOX QUESTION IS MEASURED AND THE ANSWER IS YES — and the per-cell cost figure turned out to be load-dependent

**Tick 13. The runner is landed at `35931c3`; this measures what a gate target needs before any
BUILD file is written.** Nothing was typed into a build file this tick: the open question was
whether the runner's central assumption — shelling to a venv interpreter **by path** — survives a
bazel sandbox at all, and that is now answered.

⚑⚑ **ONLY A VENV INTERPRETER WORKS, WITH A CONTROL THAT FAILS.** Measured against the runner's own
`run()` on `mdstruct` (the distribution that declares `panflute`, so the one that can refute):

| interpreter | verdict |
|---|---|
| the distribution's `.venv/bin/python` | **killed** |
| the bare mise interpreter the venv symlinks to | errored |
| `sys.executable` of the calling process | errored |

So the dependency on the venv is real and structural, not incidental — which is the same fact the
`.resolve()` defect was made of, now stated as a requirement rather than discovered as a bug.

⚑⚑⚑ **AND THE TREE ALREADY BUILDS A VENV AS A TARGET: `venv_from_hub` (⟐VENV-AS-BUILD-ARTIFACT),
called once per distribution.** Its interpreter symlink is deliberately RELATIVE — its own comment
records measuring both arms, because *an artifact that is only valid at the path it was built at is
host state with a build step in front of it*. That is precisely the property a sandboxed gate
needs, and it was built for a different reason two arcs ago.

**MEASURED END TO END:** `bazel build //mdstruct:.venv` produces `bazel-bin/mdstruct/.venv/bin/
python3`, and handing THAT to the runner **kills the mutant** — the same verdict as the host venv.
The gate target therefore stages `//<dist>:.venv` as data and passes its interpreter. No new
mechanism is needed.

### ⚑⚑⚑ THE COST FIGURE IN THIS SECTION IS LOAD-DEPENDENT, AND NOTHING RECORDED THAT

The per-cell figures recorded above — `ratchet 0.2s · hooks 0.4s · fence 0.5s · mdstruct 1.4s`,
and the *under four minutes whole-tree* conclusion drawn from them — were taken on a quiet machine.
Re-measured this tick at **load average 48.65**:

```
host venv        23.6s for ONE mdstruct cell   (recorded: 1.4s)
bazel-built venv 27.9s for the same cell       (~18% slower than host, which is the real comparison)
```

⚑⚑ **SO THE HONEST STATEMENT IS A RANGE WITH ITS CONDITION ATTACHED, NOT A NUMBER.** At 1.4s/cell
mdstruct's 64 sites are 90 seconds; at 23.6s they are 25 minutes. The first whole-grid run this
tick **timed out at 300s** and that timeout was the machine, not a hang — established by running
one cell under both interpreters with the host venv as a control that had to finish.

⚑ **THE BAZEL-VS-HOST DELTA IS THE FIGURE THAT SURVIVES, because both arms were measured in the
same minute under the same load: ~18%.** A ratio between two things measured together is robust to
a condition that moves them both; an absolute second-count is not. **The recorded absolutes should
be read as *taken quiet*, and the gate's cost argument re-measured on the machine that will run
it** rather than inherited from this section.

### ⚑⚑ THE OPERATOR RE-CONFIRMED THE RULING AGAINST THE CORRECTED RANGE

Asked with the 17x spread stated: **wire it as ruled — the DAG absorbs it.** The reasoning
recorded with the ruling: the per-commit cost is ~0 for untouched distributions, one grid for a
changed one, and the 25-minute figure is a cold worst case on a loaded machine rather than a tax.

### Written this tick, and where it stopped

`mutate_check.sh` (shellcheck clean, runs correctly outside bazel: ratchet 13 = 11 killed + 2
unreachable) and a `//ratchet:mutants` `sh_test`. ⚑ THE SCRIPT DELIBERATELY DOES **NOT** `realpath`
THE INTERPRETER, where `mypy_check.sh` does — mypy's runner is a staged `py_binary`, but
dereferencing a venv symlink is the defect that cost three ticks.

⚑⚑ **BAZEL REFUSED `$(location :.venv)` AND THE REFUSAL WAS CORRECT:** that target expands to
2,225 files, so no single-file expression can name `bin/python3`. Repaired by deriving the
interpreter from `dirname` of the config, which is the distribution root under any staging prefix.

⚑⚑⚑ **THEN THE TARGET FAILED IN 0.6s, AND THE SCRIPT'S OWN REFUSAL IS WHAT CAUGHT IT:**

```
mutate_check: ratchet/.venv/bin/python3 was not staged — refusing rather than running a grid
  under whatever interpreter happens to be on PATH
```

**MEASURED: the runfiles tree holds `mutants`, `pyproject.toml`, `src`, `tests` — and no `.venv`,
despite `:.venv` being named in `data`.** Why a `venv_from_hub` target listed as data does not
stage is **UNMEASURED** and is the next tick's first job.

⚑ **AND THE 0.6s IS THE DURATION-AS-EVIDENCE LESSON PAYING OFF IMMEDIATELY.** A grid cannot run in
0.6s; the clock said *the interpreter precondition fired* before the log was read. The same reading
took three ticks to arrive at last time, on a 0.04s failure whose message named a missing package.

⚑⚑ **THE PRECONDITION EARNED ITSELF ON ITS FIRST REAL USE.** Without it the grid would have run
under whatever `python3` the sandbox provides — reporting every site ERRORED, which reads as *the
suite did not run* rather than *the harness is misconfigured*. That is exactly the three-tick
ambiguity, and the refusal converted it into one line.

⚑ **NOTHING FROM THIS TICK LANDS IN THE TREE, AND THE SCRIPT IS HELD RATHER THAN COMMITTED.** The
BUILD changes are reverted because the target is RED. `mutate_check.sh` is correct on its own
(shellcheck clean, runs the grid outside bazel) but **no target calls it** — committing it would
be the *console script nothing consumed* shape this tree measured once already, where
`mikemol-hook-structural-query` was a distribution's only entry point and nothing used it. It sits
at `scratchpad/mutate_check.wip.sh` until the staging question is answered and the target is green.

### ⚑⚑⚑ FOUR HYPOTHESES, EACH PROPOSED AND EDITED IN BEFORE BEING TESTED

| # | hypothesis | how it died |
|---|---|---|
| 1 | stripped `PATH=/usr/bin:/bin` starves the suite of `pandoc` | changed to inherit `os.environ`; re-ran **byte-identical** |
| 2 | `PYTHONPATH` replaced resolution instead of prepending | changed to prepend; re-ran **byte-identical** |
| 3 | the editable install's `.pth` finder | refuted by probe before editing |
| 4 | pytest `rootdir` set to the real tree by `-c <real>/pyproject.toml` | changed to the temp copy; re-ran **byte-identical** |

⚑⚑ **THE PATTERN IS THE FINDING, NOT ANY ONE MISS.** Three of the four were *edited into the code
before the mechanism was tested*, and each re-ran identically — which is the cheapest possible
refutation and arrived only after the edit. The fourth was refuted by a one-variable-at-a-time
probe **in under a minute**, because that probe tested the mechanism instead of assuming it.

⚑ **WHAT FINALLY WORKED WAS MEASURING A GAP RATHER THAN PROPOSING A CAUSE.** Two facts were
already established — `import panflute` succeeds under the runner's exact environment, and pytest
fails in the same tree — so the question became *what differs between them*, answered by printing
`sys.path` from inside both. Both resolved `panflute`; a synthetic pytest module importing it
**passed**. That eliminated the environment entirely and pointed at the one module that does the
import at collection time.

⚑⚑ **AND THE DEBUG MODE IS WHAT MADE ANY OF IT VISIBLE.** `mutant_in_stdout=False` on every cell
said the mutant was never reached — the single most informative bit, and it was one print
statement inside the runner's own `run()`. The previous tick's standalone reproduction could not
have shown it, because it was not the code under test.

### Not repaired

The repair is not written. Candidates, none measured yet:

1. **Install the distribution into the temp tree**, so its dependencies resolve the way they do in
   the real one. Correct and slow — it pays a pip install per cell against a 1.4s cell.
2. **Symlink or copy the venv's `site-packages`** into the temp tree. Cheaper, and it makes the
   mutant's environment differ from the real one in a way that needs its own argument.
3. **Point `PYTHONPATH` at the temp `src` AND the real venv's site-packages explicitly**, rather
   than relying on the editable finder that resolves to the real tree.

⚑ (3) looks right and **that is exactly what the four dead hypotheses each looked like.** It is
not taken this tick, and the runner stays unlanded.

### Three real findings the build produced, which stand regardless of the runner

⚑⚑ **1. THE ERRORED CATEGORY FIRED ON ITS FIRST REAL RUN AND FOUND A STRUCTURAL LIMIT.**
`BaselineState.__init__` and `__str__` in `ratchet/state.py` error rather than kill: `BaselineState`
subclasses `enum.Enum`, so its members are constructed **when the class body executes** — mutating
them raises at import and no test ever collects. That is a limit of `body -> raise` at def-site
granularity, not a gap in the suite, and the two are easy to confuse because both read as *the
suite did not notice*. Declared as a fourth category, UNREACHABLE, **derived structurally** (a
method of an `Enum` subclass) rather than by a name list — matching `__init__` by name would
exclude every ordinary constructor, over-declaring the limit to cover two cases. Measured: 158
def-sites tree-wide, exactly 2 in this class, both the ones ERRORED named.

⚑⚑⚑ **2. THE FIRST ERRORED PREDICATE WAS TOO BROAD AND ITS OWN CATEGORY CAUGHT IT.** It read *any*
collection error as ERRORED, on a four-shape measurement where every error was an import failure.
Run against `fence`, three ordinary functions errored — and the traceback showed the suite calling
them **at collection time**, through a module-level `_WHY = _unfenceable()` guard that decides
whether to skip. The suite's own code ran and REACHED the mutant. **So the distinction is not *did
collection finish* but *was the mutant reached*,** which is the question the grid asks. With that
corrected, fence goes 22-killed-3-errored → **25 of 25 killed**. ⚑ And the exit code there was
`rc=2`, a shape the original four-case measurement never produced — a predicate is only as wide as
the corpus it was measured on.

⚑ **3. THE ACCOUNTING ASSERTION IS WHAT MAKES THE CATEGORIES HONEST.** `attempted` is carried and
the runner refuses unless `killed + survived + errored + unreachable` equals it exactly. An
UNREACHABLE site stays in `attempted` rather than being dropped — dropping it would balance the
books by shrinking the denominator, which is the flattering direction and the one the predecessor
took with ERRORED.

### ⟐STRING-SWEEP-IS-A-DETECTOR — measured 2026-09-12 on the operator's question

The operator asked the right question about the string sweep: *a stale literal is something that
needs to be kept in sync, so the solution is ensuring that sync. What makes it stale?*

⚑⚑⚑ MEASURED, AND THE PREMISE PARTLY FAILS. The originating literal was **wrong at authoring, not
stale**. The arm's own record says it checked *"a pattern whose escaping did not match
`blockers.sh`"* — the escaping never matched, so there was no sync to break and nothing had
drifted. The sweep's framing as a VACUITY check was a misdiagnosis carried in its name.

⚑⚑ BUT DRIFT IS ALSO REAL, so both failure modes exist. 223 string-membership assertions in one
module name strings in files that have been edited **56** (`blockers.sh`) and **49** (the gate)
times. A literal written against either has had many opportunities to decouple.

⚑ SO WHAT MAKES A LITERAL STALE IS THAT **A TEST NAMES A STRING IN A FILE IT DOES NOT OWN, AND
NOTHING COUPLES THE TWO.** The sweep detects the decoupling after the fact; it does not create a
coupling. The operator's proposed repair — ensure the sync — is the right shape, and the question
is whether a sync is available.

⚑⚑⚑ IT IS AVAILABLE FOR **7 OF 223**, WHICH IS THE MEASUREMENT THAT DECIDES THE ITEM:

| class | count | can a coupling be built |
|---|---|---|
| the literal IS a declared name | 7 | yes — derive it from the target |
| quoted code MENTIONING a name | 31 | no — deriving a whole shell line from a variable is not a coupling |
| prose | 185 | no — a sentence has nothing to bind to |

⚑⚑ AND THE LOOSE MEASUREMENT SAID 38 BEFORE THE STRICT ONE SAID 7. The first pass counted a
literal bindable if it CONTAINED a declared name, which admitted fragments like
`'note_failure "$dist: ratchet'` — a quoted line that merely mentions `note_failure`. Reading the
members rather than the count is what showed it; the number 38 looked like a fifth of the corpus
and was mostly one defect in the classifier.

⚑ THE CONCLUSION: **building the coupling is not the repair.** It would fix 3% and leave the sweep
standing for the other 97%, so the sweep is a DETECTOR by nature rather than by omission — an
instrument for a class where prevention is unavailable, which is a legitimate kind of tool and a
different kind from a ratchet. Its ceiling counts arms it could not resolve; an arm that sweeps a
DIRECTORY is structurally outside its reach and counting it as debt mis-states what the number
means. That is the collision holding two built arms.


### ⟐CEILING-WITHOUT-A-CONSUMER — NEW 2026-09-13, measured while repairing ⟐ORPHANED-EVALUATOR

`_MAX_UNRESOLVED = 22` **no longer has any arm asserting against it as a bound.** Measured by
enumerating every reference in the tree rather than by reading the constant's comment:

| reference | what it asserts |
|---|---|
| `_MAX_UNRESOLVED_WAS = 23` | the former value, for the direction check |
| `assert _MAX_UNRESOLVED < _MAX_UNRESOLVED_WAS` | that it FELL — not that anything is under it |
| `assert "_MAX_UNRESOLVED" in commands` | that the POLL mentions it |
| `for typed in (..., "_MAX_UNRESOLVED")` | that it is TYPED |

⚑⚑⚑ **NOT ONE OF THEM COMPARES A MEASURED POPULATION TO IT.** The sweep that did —
the string-membership vacuity check — was replaced at `aab9f8b` by a target-resolution check
whose unresolvable arms are a *declared, printed category* with no ceiling at all. So the
constant survives as a number that four arms assert facts *about*, and none assert *with*.

⚑⚑ **THAT IS FURNITURE WITH A NUMBER ATTACHED, WHICH IS WHAT ITS OWN CARRIER WAS NAMED TO
PREVENT.** `test_the_sweeps_ceiling_falls_rather_than_standing` opens *"A CEILING OVER A STATIC
POPULATION IS FURNITURE WITH A NUMBER ATTACHED"* and cites `linux-sources`' measurement that a
probe printing SIX gets read past for six consecutive ticks — the operative property being
CONSTANT rather than zero. The arm now carries exactly the object its docstring refuses.

⚑ **AND IT IS NOT THE SAME DEFECT AS ⟐ORPHANED-EVALUATOR, WHICH IS WHY IT IS FILED SEPARATELY.**
That one was a builder never shipped and is repaired at `cebbe58`. This one is a live constant
whose consumers all went away — the population it bounded is no longer computed by anyone. Two
different vacuity shapes arriving from one commit.

**The work, and the choice is a measurement rather than a preference:**

1. **Retire the constant and the direction arm together**, if nothing wants a bound on
   unresolvable arms now that `unresolved` is an outright refusal. ⚑ Honest only if the
   replacement sweep's refusal is genuinely stricter — it asserts `not unresolved`, so it is,
   and a ceiling above zero would be a RELAXATION of a check that currently admits none.
2. **Re-point it at the new sweep's `population_sweeps`**, if a bound on *declared* sweeps is
   wanted. ⚑ Refused as stated: that category was made declarative precisely because a ratchet
   over arms the instrument structurally cannot reach measures the instrument, not the debt.

⚑ **(1) LOOKS RIGHT AND MUST STILL BE MEASURED, because the four recorded rises (18→19→20→21→22)
each documented a real arm.** Deleting the constant deletes that record. The reading to take
first: does any arm today resolve to nothing *and* pass? If `assert not unresolved` holds on a
green run, the ceiling is bounding an empty set and (1) follows; if it does not, the sweep is
already failing and this is the wrong question.

⚑⚑ **AND THE GUARD SHAPE IS THE TRANSFERABLE HALF.** `assert "_MAX_UNRESOLVED" in commands` is
the same substring-satisfied-by-its-own-definition shape that hid ⟐ORPHANED-EVALUATOR for a
commit — it is satisfied by the poll *mentioning* the name, never by the poll *using* the value.
Two instances of one defect in one module, found in one tick, and the second is still live.


#### ⚑⚑⚑ WORKED at `4ab4a14` — three parts, and two were not in the filing above

**Two parts CLEARED, the third DELIBERATELY NOT TAKEN.** The filing named one defect; measuring it
found three, which is the case for re-deriving a list against the tree rather than against its own
record. **The tree knew more than this section did.**

⚑⚑⚑ **PART 1, CLEARED — a live BLOCK-WITHOUT-A-ROUTE in this repository's own advice line.**
`blockers.sh` printed `pytest tests/test_bar_fires.py -k vacuous` to any reader wanting the real
count. **Measured: `no tests collected (144 deselected)`.** `aab9f8b` renamed the arm two commits
earlier. The poll offered a route the reader could not take — the defect the routing table refuses
to commit one layer up, arriving in this tree's own poll, because **a rename orphans every pointer
and a `-k` selector fails SILENTLY**.

⚑⚑ **PART 2, CLEARED — a structural concession that outlived its cause.** An arm read its files
through hand-typed constants, explaining itself as *a CONCESSION TO A SIBLING ARM ... the first
draft pushed that sweep's unresolved ceiling 22 -> 23.* Correct when written; void since `aab9f8b`
replaced that sibling and made loop-variable reads a declared category. **The mechanism was retired
and the thing that bent around it stayed bent.** Its comment also claimed a derivation via
`_SHELL_CONSUMERS` that never existed in the module.

⚑ **AND THE DERIVATION FOUND NINE WHERE THE TYPED LIST HELD THREE — the repair's author predicted
four.** Members, read by forcing the floor above the population: `blockers.sh`, `commit-msg`,
`domain_witness.sh`, `message_counts.sh`, `pre-commit`, `preflight.sh`, `refusal_record.sh`,
`rule_citations.sh`, `shellcheck_test.sh`. The arm passes over all nine, so the six newly-admitted
scripts hold no violations — a result rather than an assumption.

⚑⚑ **PART 3, CLEARED — the substring guard replaced by a resolution check.**
`assert "_MAX_UNRESOLVED" in commands` passed if the poll NAMED the constant, never if it USED the
value, and it was the **third** time that block had been keyed to a spelling (its own comment
records the previous two). The arm now parses the module and asserts every `-k` selector the poll
prints matches a real test name. F-armed: restoring `-k vacuous` REDS naming `['vacuous']`.

⚑⚑⚑ **WHAT IS NOT DONE, AND WHY IT IS NOT A LEFTOVER: `_MAX_UNRESOLVED = 22` STILL EXISTS.**
Re-measured after the repair, its surviving references are exactly two live assertions — that it
**fell** from 23, and that it is **typed** — plus one that is now **DORMANT BY DESIGN RATHER THAN
DEAD**: `if "_MAX_UNRESOLVED" in commands: assert "CEILING" in commands`. That one fires only when
the poll greps the constant, which it no longer does, and its own comment says why it is built that
way: *a required presence cannot be emptied by deleting prose — the difference between an arm that
survives its own repair and one that only survived until it worked.* Nothing asserts WITH the
value. The two closures this section proposed are both still open, and the reason for not taking
either is now clearer than when they were written:

1. **Retiring it deletes the record of four documented rises (18→19→20→21→22), each a real arm.**
   That record is the only place the *reasons* live — each rise names the arm and the runtime
   predicate that made it unresolvable. Deleting the constant without rehoming that prose loses
   measurements, which this tree treats as a worse outcome than carrying a dead number.
2. **The ceiling-falls arm asserts a DIRECTION, and a direction over a retired constant is not
   obviously meaningless** — it still refuses a flattering edit to a number, which is a property
   with no current subject rather than a property that is false.

⚑ **So the honest state is: the LIVE defects are repaired and the DEAD constant is carried, with
its record intact and its uselessness written down.** That is a different thing from unfinished
work, and the distinction is the point — a number nobody can raise, whose removal would cost
measurements, is furniture that is cheaper to label than to move.

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
