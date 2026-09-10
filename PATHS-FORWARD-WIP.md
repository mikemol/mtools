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
resolver can produce both artifacts. Not investigated. Do not assume the divergence is
harmless — `ast-serialize` is a mypy transitive, so the two substrates may run different
mypy behaviour on identical source.

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
