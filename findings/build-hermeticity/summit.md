# `SM-` — summit's leg, build-hermeticity census

**Written against** `CENSUS-build-hermeticity.md` **rev 13** and `CENSUS-BRIEF.md`.
**Destination** `mtools:findings/build-hermeticity/summit.md` per `§R`, **authorized by mtools**
before writing — a dispatcher naming a path in a third repo is not that repo granting access to
it, and summit had twice today declined to write into a peer's artifact on someone else's say-so.

⚑ **MEASUREMENT WINDOW, per `§W`: every figure below was taken between
`2026-09-06T19:00Z` and `2026-09-06T20:19:26Z`, in one session, on a tree being edited by that
same session.** `§W` requires per-figure stamps because gabion measured *three different counts
from one grep over summit's tree within an hour, all honestly obtained* — so the single stamp here
is a **bound, not a point**, and any figure in this leg may differ from a re-run. ⚑⚑ **Two figures
below are known to have moved DURING the window and both are marked inline**: summit's tracked
`.py` count (110 → 113 as this session added probes) and the venv's package set (95 removed and 94
restored, `numpy 2.5.2 → 2.5.3`). **A leg over a live tree that reports a single number for either
would be reporting a rendering rather than a measurement.**

## §9 Disclosures, first paragraph as required

Summit **owns the venue this census is filed through** and its moderator authored the routing rule
the dispatcher's `§Q`-5b cites. It does **not** own the census, the brief, or `mtools`. ⚑ Summit's
inputs differed from peers' in one way that matters: **the operator's two framing quotes in `§Q`
were delivered to summit directly, mid-session, before this census existed** — summit filed
`question-what-does-each-repos-build-prove-about-its-interpreter` from them at 2026-09-06 and
`linux-sources` convened this run separately. Whether other parties saw the quotes first-hand or
via `§Q` is unknown to me. ⚑⚑ **And summit has read no peer leg**: `gabion-build.md` and
`rosettapkg.md` exist in the destination directory and were not opened (`§2`).

⚑ **Two peer findings reached summit before dispatch and are recorded as `testimony` under `§7`,
not citation**, because acting on them is what `§2` forbids and recording them is what it requires:
gabion's measured declared/ambient split, and mtools' `MODULE.bazel.lock` 114-hashes-against-zero
split. Neither was verified by summit in the peer's tree and neither is load-bearing below.

## §10 Coverage, as a population

    A  summit's own python, tracked                     -> 113 files @20:15Z (`git ls-files
                                                            '*.py'`, 81 at the `lint` slice's
                                                            grain; the difference is untracked
                                                            probes). ⚑ WAS 110 @19:20Z — this
                                                            session added three. The figure is
                                                            a reading, not a property.
    B  manifests read verbatim                          -> pyproject.toml, uv.lock, mise.toml,
                                                            floor/paper.toml, .githooks/pre-commit
    C  subprocess call sites enumerated                 -> 74 (`subprocess.run([` across
                                                            scripts/, library/, registries/)
    D  vendored shared bodies                           -> 14 (12 matching upstream, 2 not)
                                        TOTAL              113 files + 5 manifests

    NOT SEARCHED, and why:
      - peers' trees — `§2` forbids it and `§Q` says survey yourself
      - `.claude/settings.local.json` allowlist — read for arming, not for dependencies;
        it is a permission surface, and I did not audit it as a dependency manifest
      - shell scripts other than `.githooks/pre-commit` — summit has none tracked
    UNPARSEABLE / UNREADABLE: 0. `parses` reports 113 of 113.

## §Q-1 What summit builds with today

**Nothing that builds.** No bazel, no make, no CI. Summit has `uv` for the venv and
`mise` for the interpreter, and its only enforcement is a git hook.

    .githooks/pre-commit    armed per clone by `git config core.hooksPath .githooks`
                            runs `python3 ledger/check.py --staged`, then `scripts/check`

⚑ **This is a leg, not an abstention** (`§Q`-1's own instruction). Summit is a *venue*: its
artifacts are registries, a floor of bib entries and a ledger, and its "build" is a projection —
`scripts/split_ledger.py --project`, `scripts/project_registries.py`. **There is no compilation
step to be hermetic about, and the hermeticity question lands entirely on the READERS it borrows.**

## §Q-2 Measured off the live process

`scripts/check` runs as a **plain subprocess of the shell**, not under a build tool, so there is no
rc-file/env/command-line三-way to reconcile. The interpreter question is the live one, and the
process-level measurement is `which -a python3`:

    /home/mikemol/github/summit/.venv/bin/python3     <- FIRST
    /home/mikemol/.local/share/mise/installs/python/3.13/bin/python3
    /home/mikemol/.local/share/mise/shims/python3
    /usr/bin/python3
    /bin/python3

⚑⚑ **The second entry is 3.13 and summit pins 3.14.5.** So a `python3` resolved one position
later is a different MINOR VERSION, not merely a different venv — and summit's tooling depends on
that ordering wherever a shebang is used.

## §Q-3 Work discovery — AUTHORED, and gated rather than checked

Summit's work list is **authored**, and per `§Q`-3 rev 11 that is a mechanism rather than its
absence. Two authored populations, each with a different staleness answer:

- **The floor** (`floor/reports-*.bib`, 413 entries) — hand-filed by delegates. Staleness is not a
  concept: a report's state is its corroboration count, recomputed every run.
- **The asks** (`floor/asks.bib`, 24) — ⚑ **an ask is OPEN exactly when its check exits non-zero,
  recomputed every run. Nothing records status, so nothing about status can go stale.** When an
  upstream fix lands the ask closes with nothing edited here. Measured today: `14 closed / 10 open
  / 0 UNAVAILABLE of 24`.

**What IS derived, and what checks it:**

| producer | input | output | fan-out | drift check |
|---|---|---|---|---|
| `scripts/split_ledger.py --project` | `ledger/entries/*.md` (291) | `ledger/ledger.md` | 291 → 1 | `ledger/check.py --entries` REFUSES when they disagree |
| `scripts/project_registries.py` | `registries/{delegates,capabilities,services}/` | each record's body | 76 → 76 | `check --only registry` |
| paperkit's projector | `floor/*.bib` | `floor/FLOOR.md` | 413 → 1 | ⚑ **NOTHING. Measured stale by 12 days.** |

⚑⚑⚑ **The third row is summit's own worst finding and it is filed:**
`friction-the-one-generated-file-outside-the-gate-is-the-one-that-rotted`. The `gate` slice carves
out `floor/` because the floor is EXPECTED to gate red, and **the carve-out was drawn around the
VERDICT and silently carried the PROJECTION CHECK out with it.** Two properties, one exclusion, and
nothing recorded that the second was considered.

## §Q-4 Work specificity — one slice per file, one entry per claim

**Grain: the slice.** 20 slices, discovered from `scripts/slices/`, each reporting its own `n of m`.
One level coarser is one board verdict (which exists: `summit-check: FAIL (20 slice(s))`); one
level finer is the arm — `routes` alone carries 38 checks across 5 sub-arms.

**Second grain: the ledger entry.** 291 files, one per entry, discovered from the directory.
⚑ **There is deliberately no append mode**: append makes every writer contend for one file's tail,
which is the concurrent-write hazard `floor/inbox/` exists to avoid.

**What the grain COSTS, as `§Q`-4 demands:**

- ⚑ **A slice-grained board cannot say WHICH of 38 routing checks failed without `-v`.** `routes
  32 of 38` is unattributable at the verdict line; a reader must re-run to localise.
- ⚑⚑ **And the fine grain on the ledger bought something a coarse one could not**: a vanished
  entry FILE is the same forbidden move as a vanished bullet, and `ledger/check.py`'s F-arm catches
  it. At monolith grain a dropped bullet is a diff nobody reads.
- **The floor's grain is one entry per claim, and it was WRONG once**: 242 entries in one bib
  became five per-genre files, and the split immediately produced a false refusal — a corroboration
  resting on a use-case in a sibling file read as dangling **when it is not**. Specificity created
  a defect that did not exist at the coarser grain, and the fix was `--corpus`, not re-merging.

## §Q-5 Cross-repo edges

**CONSUME:**

| from | what | DECLARED or AMBIENT |
|---|---|---|
| `paperkit` | the engine (`bib`, `gate`, `resolver`, `layout`) | ⚑ **AMBIENT** — located via `PAPERKIT`/`PAPERKIT_ENGINE`/`PAPERKIT_HOME`, never declared |
| `substrate` | 14 vendored shared bodies; 3 hooks as SYMLINKS | ⚑⚑ **AMBIENT AND UNDECLARABLE** — see below |
| `substrate` | `bibstruct.py`, `mdstruct.py`, `pycodemod` as borrowed readers | AMBIENT, named in `SKILL.md` |

⚑⚑ **`substrate-tooling` CANNOT be declared and the resolver is right.** It requires
`Python>=3.12`; summit declares `requires-python = ">=3.11"`; `uv sync` returns `No solution
found`. So the dependency is real, load-bearing, and structurally undeclarable without changing
summit's own floor. **Measured cost, today:** a `uv sync` swept **95 undeclared packages** out of
summit's venv including `paperkit` and `substrate`, and the `interpreter` slice went from *warning
about undeclared packages* to reading **CLEAN — a green arriving by SUBTRACTION.**

**EMIT** — and `§Q`-5 is right that nobody records this direction:

- **the floor itself.** 413 entries by 20 delegates; peers cite summit keys in their own warrants.
- **`summit anchored`** reports which records depend on a named tree still existing.
- ⚑ Summit emits **rulings and modes**, and this session added four (`intake`, `closure`,
  `converge`, `premise`) that no peer knows exist. **A capability nobody can discover is
  functionally absent** — summit's own finding, landing on summit.

## §Q-5b Invoked executables — enumerated, none declared

74 `subprocess.run([` call sites across `scripts/`, `library/`, `registries/`. Non-Python binaries:

    git         many sites (modes/reach.py ×5, modes/runs.py, modes/invite.py, slices/modes.py,
                slices/lint.py, slices/registry.py, slices/reports.py, probe_commit_only.py)
    mise        1  (slices/interpreter.py:51 — `mise which python`)
    uv          2  (probe_substrate_install.py:53,66)
    env         2  (slices/routes.py:436 — `env -i`, deliberate)
    test        1  (probe_metrics_reachable.py:106)

⚑ **Zero of these appear in `pyproject.toml`, `uv.lock` or `mise.toml`.** An import-resolvability
predicate scores summit clean while `slices/interpreter.py` shells out to `mise` and every git-based
slice shells out to `git`.

⚑⚑ **And the dispatcher's sharpest instance applies to summit unchanged.**
`.claude/skills/struct-tools/SKILL.md` is read at call time by the structural-query hook and names
borrowed readers and their interpreters. **Summit's own routing table is a dependency manifest in a
file no resolver reads** — and summit audited that table's TARGETS repeatedly this session (adding
a "RUNS IS NOT ANSWERS CORRECTLY" arm) while never auditing its INTERPRETERS. *Credited: gabion
found this shape in its own table by answering summit's question about declared-versus-ambient.*

## §Q-6 Interpreter determination

**Mixed, and the mixture is the finding.**

| surface | how the interpreter is chosen | DECLARED? |
|---|---|---|
| `scripts/summit`, `scripts/check` | `#!/usr/bin/env python3` | ⚑ **AMBIENT — a NAME resolved against PATH** |
| console scripts `summit`, `summit-check` | `#!/home/mikemol/github/summit/.venv/bin/python3` | **DECLARED**, absolute, added 2026-09-06 |
| every `subprocess.run` | `sys.executable` | inherits — declared iff the parent was |
| `.githooks/pre-commit` | `python3` for the ledger, `scripts/check` for the board | ⚑ AMBIENT |

⚑⚑⚑ **MEASURED FAILURE, TODAY, ON THE ROUTED ENTRY POINT.** `linux-sources` ran
`summit/scripts/summit ask` — the documented surface, not an ad-hoc call — from a shell whose own
venv came first, and read **`0 closed / 24 open / 0 UNAVAILABLE of 24`**. Controlled pair, same
tree, seconds apart:

    env python3 …/scripts/summit ask          -> 0 closed / 24 open
    .venv/bin/python …/scripts/summit ask     -> 14 closed / 10 open

**Every witness died at `import library`; `ask_state` folded exit 1 into OPEN, and all 24 asks read
open on one crash.** ⚑ **A shebang is a NAME, not an interpreter.** Repairs: `[project.scripts]`
so the routed entry points carry an absolute interpreter, and a guard in `ask_state` so a crashed
witness reads **UNAVAILABLE, never OPEN** — proven by firing against a real foreign venv,
`0 closed / 0 open / 24 UNAVAILABLE`.

## §Q-7 The `.venv` — two independent properties, as `§X` requires

- **Set pinned?** YES. `uv.lock`, generated from `pyproject.toml`. @20:12Z
- **Content hash-pinned?** YES. **505 `sha256` entries** in `uv.lock`. @20:12Z
- **Does anything gate the lock's freshness against the manifest?** ⚑ **NO.** Nothing in
  `scripts/check` compares `uv.lock` to `pyproject.toml`. A manifest edit without a re-lock is
  invisible to the board.

⚑⚑ **AND THE VENV IS NOT REPRODUCIBLE, MEASURED THE SAME DAY.** `uv sync` removed 95 packages;
restoring them with `uv pip install -e ../substrate` returned **numpy 2.5.3 where 2.5.2 had been**.
So it is a thing made once, whose content is partly a fact about this machine's history.
**`summit closure`'s verdict refuses the stronger reading in its own words:** *resolving is not
hermetic — this reports the venv this tree HAS, never one a build proved.*

## §Q-8 What is hermetic, and what fired

**One real hermeticity check, and it has fired.** `scripts/slices/routes.py:436`:

    env -i <entrypoint> --where|--selftest

⚑ `env -i` strips `PATH`, `VIRTUAL_ENV` and `PYTHONPATH` — *the environment a cross-repo caller
actually has*. Both entry points must run under it; a `Traceback` fails the arm and the message
names the missing module. Board reports it as `2 entrypoints run under a stripped environment`.

**Has it fired?** YES — it exists because of
`friction-borrowed-tool-needs-its-owners-interpreter`, and its own comment records that the defect
was *caused by the fix for a different defect*. ⚑⚑ It also carries a `⟨P,F,δ⟩` self-proof on a
SYNTHETIC subprocess rather than on the tree, because an environment-dependent F-arm would stop
proving anything the day someone installs `panflute` globally.

**Second, weaker:** paperkit runs `cmd:` checks under a default-deny `clean_env`, which is why
**summit's own modules must stay stdlib-only** — a dependency present at the terminal and absent
inside the gate works by hand and fails in the only run that gates.

⚑⚑⚑ **What is NOT hermetic and I will not claim otherwise:** everything above tests that summit's
entry points survive a stripped environment. **Nothing tests that the RESULT is reproducible.** An
undeclared input is invisible to every unsandboxed green, and summit has no sandboxed one.

## §Q-9 Solved / declined

**SOLVED, and offered:**

1. **The three-state read.** `scripts/askstate.py` — paperkit's `result:` returns a bool and
   swallows exceptions, so absent/crashing/failing collapse. Summit keeps `unavailable` distinct
   and the guard is proven by firing. ⚑ **Measurement that made me trust it:** it caught a real
   loss within minutes of shipping, when `uv sync` swept the package a witness needed.
2. **A verdict line that refuses its own strongest reading.** Adopted from gabion's proposal.
   `summit closure` says *resolving is not hermetic*; `summit premise` says *`entailed` means NO
   RECORDED WITHDRAWAL, never a verified live instance*. **Free, and it is the only defence any
   party found today against reporting a correct answer about the wrong property.**
3. **`env -i` on entry points** (`§Q`-8). Cheap, and it catches the exact cross-repo class three
   delegates hit today.

**DECLINED — HELD (a reason I can state):**

- **bazel.** Summit has nothing to compile; its 20 slices are a read-only reporter over 413 bib
  entries and 291 ledger files, and its own rule is that an instrument must not mutate what it
  measures. ⚑ *What I do NOT claim: that this generalises. It is a fact about a venue, and the
  operator's direction is fleet-wide.*
- **Declaring `substrate-tooling`.** Measured: makes summit uninstallable. Held with the
  measurement attached.
- **`disallow_any_explicit`** — free at 0 errors and deliberately NOT taken: `Any` is how you ask
  mypy what a type should be, and the flag would ban the interrogation instrument with the
  sloppiness.

**DECLINED — UNEXAMINED (never compared), stated as such:**

- **Gating `uv.lock` freshness against `pyproject.toml`.** Never considered until `§Q`-7 asked.
- **Any RBE, BES, or remote cache.** No opinion; never evaluated.
- **A sandboxed reproducibility check.** ⚑ This is the one I would most want and have not thought
  about at all.

## §Q-0 (brief `§0`) Nomination

**`memmesh`** is not on `§R`'s live-session table and holds
`friction-a-numbers-scope-is-invisible-in-the-number`, the entry this fleet's `n of m` provenance
rule rests on. It appears in the "no session, active" list; ⚑ **I would flag that its leg matters
more than its tier suggests**, because the specificity question (`§Q`-4) is a counting question and
memmesh owns the counting finding.

## §X-adjacent — a notice carried here because this is the only file I can be held to

⚑ **I asked mtools for write authorization before creating this file, and flagged two concerns.
mtools authorized and corrected one of them, which I record rather than quietly drop.**

- **The freshness advisory will fire on this leg and should stay fired.** mtools measured its gate
  at **7 pass / 10 flagged** and verified that *the only passing legs are the two written by
  parties that own the rules*. That is the gate's premise made visible — **it assumes the measurer
  and the rule-holder are the same party, and in a census they never are.** Citing an mtools
  `Rule N` from a summit leg would silence the advisory without making anything cross-checkable,
  which is green-by-subtraction at document grain. gabion declined the same cheap fix independently.
- ⚑⚑ **MY SECOND CONCERN WAS WRONG AND IT IS THE MORE USEFUL HALF.** I warned that this leg would
  make the count 9 against a freeze accounted at 7. **That arithmetic belongs to the CONSTITUTION
  roster, not this one** — build-hermeticity has no `§S` yet, and mtools' poll reports it as
  **PRE-FILING, not short-rostered**, a distinction it had to add after the conflation *manufactured
  a deletion claim about a table nobody had written*. I carried a true figure from one census into
  a claim about another; the two are the same shape and different objects.

## §12 Termination test

*Could a reader of this file alone reconstruct what was asked of the other legs?* **No.** This file
answers nine questions for one venue and names no peer's obligations. That is the apex's job.

## §5 Negatives in this leg — the positive-control rule

Three absences asserted above, each with its control:

| absence | spelling searched | denominator | reader | positive control |
|---|---|---|---|---|
| no build system | `bazel`, `Makefile`, `BUILD.bazel`, `.github/workflows` | summit tree | `ls`, `git ls-files` | ⚑ `.githooks/pre-commit` EXISTS and is found by the same read — so the reader can see a build-ish artifact when one is there |
| no binary declared in a manifest | `git`, `mise`, `uv`, `jq`, `pandoc` | `pyproject.toml`, `uv.lock`, `mise.toml` | `grep` | ⚑ `libcst`, `panflute`, `json-stream` ARE found in `pyproject.toml` by the same read |
| nothing gates lock freshness | `uv.lock`, `lock` | `scripts/slices/*.py` (20) | `grep` | ⚑ `mise.toml` IS read by `slices/interpreter.py` and the same grep finds it |

⚑ **Mode my instrument silently accepts and ignores:** `grep -r` honours `.gitignore`, and
`floor/inbox/` is gitignored — **so a recursive search from summit's root cannot see 42 pending
intake drafts.** Measured today by gabion, which read an unplaced draft as a convened census.
`summit intake` was built in response and is the only surface that sees them.
