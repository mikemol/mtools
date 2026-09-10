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

### ⟐FENCE-WARRANTS — the gate's warrant loop has a hand-written population

`.githooks/pre-commit` line ~403 reads `for dist in hooks mdstruct ratchet`. `fence` is
not in it, so its 27 test functions carry ZERO warrants and the 1:1 ledger never looks.
⚑ The gate is CORRECT OVER THE WRONG SET — the mis-named-population defect, in the gate.

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

### ⟐VENV-AS-BUILD-ARTIFACT — the operator's standing direction, and the seed omitted it

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
- The venv has THREE non-bazel consumers: `.githooks/pre-commit` (13 call sites),
  `preflight.sh` (7 sites), and the interactive dev loop. All reach `<dist>/.venv/bin/…`
  as a host path no rule produces.
- The repeated shape is exact across all four distributions — same `[dependency-groups]`,
  same tracked `uv.lock`, same `bin/{ruff,mypy,python3}` contract. Four identical
  instantiations of one macro.

⚑⚑ THERE IS NO `py_venv` RULE. I asked the operator whether to *bump to a version with
`py_venv`* and they decided on that description; MEASURED against the actual releases,
it does not exist at 1.0.0 OR at 2.3.3 — checked `//python`, `//python/bin` and
`//python/uv` BUILD files directly. Re-asked with the correction; the ruling stands: bump
anyway (done, `50cb2c2`), then build the rule on `//python/uv`'s hermetic uv toolchain.

### ⟐POLL-RUF201-POPULATION — NEW 2026-09-10, small, unlanded

`blockers.sh`'s RUF201 line prints `for d in hooks mdstruct ratchet` as the command to
measure the preview paydown. `fence` landed at `cc3d301` and is NOT in that list, so the
figure a reader would measure omits a whole distribution — the same hand-written
population as ⟐FENCE-WARRANTS, in the poll instead of the gate.

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
