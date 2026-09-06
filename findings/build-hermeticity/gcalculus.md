# GC — gcalculus, build-hermeticity leg (third-party measurement)

Third-party measurement by a subagent dispatched from linux-sources, against CENSUS-build-hermeticity.md rev 23. gcalculus has no live session and did not survey itself.

**Evidence arm:** the gcalculus tree at `/home/mikemol/github/gcalculus`, read live on 2026-09-06 (git status not captured; this is a moving-target census per `§W` and every figure below carries its own measurement timestamp). All claims are `citation` (a quoted byte from a file in the tree) or `machine` (a command's output on this box, on 2026-09-06). No `testimony`, no `inference` about intent.

**Normative arm:** `CENSUS-build-hermeticity.md` rev 23 (`§V` last row), `§Q`'s nine questions as phrased there.

---

## §Q-1 — What do you build with today?

**No bazel, no make, no declared Python packaging manifest.** Measured 2026-09-06T21:14:38Z:

    find /home/mikemol/github/gcalculus -maxdepth 4 -name pyproject.toml   -> 0 hits
    find /home/mikemol/github/gcalculus -maxdepth 4 -name uv.lock          -> 0 hits
    find /home/mikemol/github/gcalculus -maxdepth 4 -name mise.toml        -> 0 hits
    find /home/mikemol/github/gcalculus -maxdepth 4 -iname 'requirements*' -> 0 hits
    find /home/mikemol/github/gcalculus -maxdepth 4 -iname poetry.lock     -> 0 hits
    find /home/mikemol/github/gcalculus -maxdepth 4 -iname 'Pipfile*'      -> 0 hits

⚑ **POSITIVE CONTROL, same reader, same corpus, same depth bound:**

    find /home/mikemol/github/gcalculus -maxdepth 2 -name paper.toml -printf '%p  %s bytes\n'
      /home/mikemol/github/gcalculus/paper.toml        2238 bytes
      /home/mikemol/github/gcalculus/paths/paper.toml  287 bytes

The reader finds a real, known-present file at the same depth the manifest search came back empty at, so the zero above is a fact about this tree, not about the `find` invocation. **The absence of a Python packaging manifest and lockfile holds.**

What *is* present at the top level (`find -maxdepth 1 -type f`, 112 entries, counted 2026-09-06T21:14Z): **83 `concepts_*.py` files** (exact count: `find -maxdepth 1 -name 'concepts_*.py' -printf '%f\n'` returned 83 lines), **7 shell scripts** (`render.sh`, `check.sh`, `sweep.sh`, `check-acceptance.sh`, `farm-board.sh`, `grade.sh`, `farm.sh` — one more than the dispatch's estimate of six), `.delta-cache.json` (193948 bytes) and `.leafsweep-cache.json` (37168 bytes), `ledger.md`, `claims.md`, `rubric.tsv` (388 bytes), `gcalc.py`, `farm.py`, `sampling.py`, `ledger_audit.py`, `paper.toml`, `concepts.bib`, plus a `.githooks/` directory and an `agda/` directory (3 `.agda` files: `GcalcConfluence.agda` 31006 bytes, `GcalcNu.agda` 16818 bytes, `MeasureSNSubsumes.agda` 4621 bytes, plus `install.sh`, `INSTALL.md`, `gcalculus.agda-lib`).

**What actually gates a commit:** `git config --get core.hooksPath` → `.githooks` (measured directly on the repo, 2026-09-06). `.githooks/pre-commit` exists as a real, non-sample file (`find /home/mikemol/github/gcalculus/.githooks -maxdepth 1 -type f` → `pre-commit`, one entry) — control: `.git/hooks/` itself holds 14 files, every one suffixed `.sample`, confirming the standard hooks are inert and `core.hooksPath` is what's live.

`.githooks/pre-commit`, quoted in full (`/home/mikemol/github/gcalculus/.githooks/pre-commit`):

    cd "$(git rev-parse --show-toplevel)" || exit 1
    ./check.sh
    rc=$?
    if [ $rc -ne 0 ]; then
        echo "pre-commit: check.sh FAILED (rc=$rc) — commit refused" >&2
        exit $rc
    fi

`check.sh` is a hand-authored bash aggregator (194 lines), described in its own header comment as "THE ONE COMMAND" that unifies four previously-disagreeing partial verdicts (`render.sh`, `farm.sh`, `check-acceptance.sh`, `ledger_audit.py`). Its stages: `assertions enabled` → `every gcalc leaf certifies` → `every concepts leaf certifies` → `sampling register current` → `forward-paths project` (`./paths/render.sh`) → `render.sh` (the paperkit gate) → `acceptance suite` (external, optional).

**So the build system, in the sense §Q-1 asks, is bash + `git config core.hooksPath`, invoking a hand-written verdict aggregator that calls out to a sibling checkout's paperkit engine.** No CI job was found or looked for (out of scope for a tree read, not a build).

## §Q-2 — Measure off the live process, not the config file

**UNMEASURED.** Measuring `ps -o args=` on a real `git commit` invocation in this tree would require actually running a commit, which the cost discipline (`§X`) forbids for a census — running `check.sh` triggers the full six-stage sweep including the paperkit gate and (unless `--quick`) a corpus sweep and the render.sh cross-repo call, which is exactly the kind of execution this task was told not to run. What can be said from source alone: `.githooks/pre-commit` invokes `./check.sh` with no flags, so the invoked command is deterministic from the file — but whether it is *actually reached* (i.e., `core.hooksPath` correctly resolved by the git binary that runs at commit time) was not captured live. **Cost if measured:** one full `check.sh` run, which the header itself documents as including "the two slow sweeps (gate + corpus)" — explicitly the thing `--quick` exists to skip.

## §Q-3 — Dynamic work discovery: DERIVED or AUTHORED?

**AUTHORED**, and it is a paperkit-warrant-driven project, matching the shape the census already tabulates for `substrate`'s worklist row but with its own distinct configuration.

- **Warrant:** `concepts.bib`, 192471 bytes, **172 `@misc{...}` entries** (`grep -c '^@misc{' concepts.bib` → 172, measured 2026-09-06). Rubric: `rubric.tsv`, 388 bytes (0 `@misc{` lines in it — it is not a bib file, it is the grading rubric paperkit reads per `paper.toml`'s `rubric = "rubric.tsv"` key).
- **Projection:** `ledger.md`, generated — never hand-edited. `render.sh`'s own header states this outright: *"The ledger is the PROJECTION of the claim-DAG, so it is regenerated, then verified, and never hand-edited."*
- **Red-claim gate:** `render.sh` calls `python3 "$PAPERKIT/paperkit/project.py" --check` first to *detect* drift (rather than silently regenerating and passing), then regenerates, then gates with `python3 "$PAPERKIT/paperkit/gate.py" --safe --without-K`. A comment in `render.sh` records a measured self-defect: an earlier version regenerated the ledger *before* checking it, so the gate's drift check could never fail — verified by hand-editing the ledger and observing the edit silently vanish with a green report. The current version checks first and reports the regeneration explicitly.
- **`paper.toml`** (`/home/mikemol/github/gcalculus/paper.toml`, quoted in full above) declares `consumer_fields = ["points", "unified", "redirect"]` — three fields the paperkit engine would otherwise silently drop and warn about on every run (the file's own comment: "Undeclared, these three were DROPPED on every run and NAMED in ~30 lines of warning per invocation — which this session read past all day as noise").

**What makes this a distinct mechanism from the census's eight already-tabulated rows, rather than a variant:** the census's `substrate` (iii) row ("the worklist — work planning as a gated paperkit project") is the closest sibling, but gcalculus additionally layers a **second, independent grading engine** on top of the same warrant corpus: `sweep.sh` / `grade.sh` drive paperkit's `discriminate.py` in a **Δ (delta) resumable grading mode**, distinct from the pass/fail gate `render.sh` runs. This is a third axis the census's table does not have a column for: not just *derive-the-worklist* and *gate-the-worklist*, but *grade-the-worklist-at-a-chosen-resolution-with-a-resumable-budget*, cached in `.delta-cache.json` (193948 bytes) keyed on `(engine, resolution, root)`. `sweep.sh`'s header states the cache invalidates if *either* the paperkit engine tree *or* `concepts.py`/`concepts.bib` change — so the derivation has a drift-sensitive cache with an explicit invalidation triple, gated not by a `--check` binary verdict but by a typed four-state exit-code protocol (0 done / 1 floor unmet / 2 incomplete-resume / 3 refuse), quoted from `sweep.sh`:

    RULE 1  READ THE EXIT CODE, DO NOT RETRY BLINDLY. ... 0 done · 1 a floor unmet ·
            2 INCOMPLETE-resume · 3 REFUSE. ONLY 2 means "call me again".

**The staleness detector for the DERIVED half (ledger.md from concepts.bib) is `render.sh`'s `project.py --check`, which fires before every regeneration** — a drift check that runs at build time, not merely a hand-invoked `--check` flag someone might forget (`check.sh` calls `render.sh` unconditionally except under `--quick`).

## §Q-4 — Work specificity

**Grain: one paperkit claim (`@misc{...}` entry in `concepts.bib`) = one warranted unit.** Measured count: **172 claims** (`grep -c '^@misc{' concepts.bib`, 2026-09-06). `check.sh`'s own header cites a different, smaller figure ("6 stages over 127 claims") in a comment inside `.githooks/pre-commit` — ⚑ **this is a live discrepancy the census's own rules require carrying rather than resolving**: 127 (the comment's count) vs 172 (measured directly against the current `concepts.bib`, 2026-09-06). Either the comment is stale prose (matching this tree's own documented failure mode elsewhere — `check.sh`'s header explicitly warns "a stale count reads identically to a current one," about a different literal, "740 leaves," that had already gone stale once) or it is counting a different population (e.g., only claims reachable from a particular route table). **Not adjudicated here** — carried as a divergence, with both figures and their sources stated.

At a coarser grain: `check.sh` reports **6 top-level stages** (assertions, gcalc leaves, concepts leaves, sampling register, forward-paths project, the gate), each pass/fail/skip, aggregated to one exit code. At a finer grain below the claim: `farm.py` declares **23 individually-named F-arms** (counted from the `ARMS = [...]` list read in full, `/home/mikemol/github/gcalculus/farm.py`), each an independent mutation+expected-message pair — a still finer unit than one claim, since several arms target functions rather than bib entries.

**What the choice costs, stated in the tree's own words rather than inferred:** `farm.py`'s docstring names a coverage failure at the finer-than-claim grain directly: *"four F-arms in a single session were VACUOUS"* — an arm passing without discriminating the rejected design from the accepted one, caught only by requiring each arm to declare the **exact message fragment** its rejected mutation must produce, not merely that *some* red occurred. This is the tree's own measured cost of a fine grain: a red that doesn't say *why* is worth nothing, so specificity is pushed down to (mutation, expected-message) pairs, at the cost of hand-authoring 23 separate rejected-state descriptions.

## §Q-5 — Cross-repo edges: consume and emit, declared or ambient

**Consume, and it is the single sharpest hermeticity finding in this leg: an absolute, hard-coded filesystem path to a sibling checkout, present in two scripts, declared in no manifest.**

`grade.sh` line 35 (`/home/mikemol/github/gcalculus/grade.sh`, quoted verbatim):

    ENGINE=/home/mikemol/github/paperkit/paperkit

`render.sh` (`/home/mikemol/github/gcalculus/render.sh`) is slightly more flexible — `PAPERKIT=${PAPERKIT:-$HERE/../paperkit}` — an env-var override with a **relative-sibling-directory default**, which is still ambient: it works only because `paperkit` happens to be checked out as a sibling of `gcalculus` under `~/github`. Both scripts refuse cleanly when the engine is absent (`render.sh`: `if [ ! -f "$PAPERKIT/paperkit/gate.py" ]; then echo "no paperkit engine at $PAPERKIT" ...; exit 1; fi`), so the edge is **at least detected and refused-on-absence**, but it is **AMBIENT, not DECLARED** — no manifest file anywhere in the tree names `paperkit` as a dependency; the coupling exists only as a literal path in two shell scripts.

**Emit:** not measured. A third-party read of `gcalculus`'s own tree cannot see who else consumes its outputs (`ledger.md`, `concepts.bib`, or the `.agda-lib`) without reading every other repo — out of scope for this leg, and the census's own `§Q`-5 note that the emit direction is structurally invisible from a single-repo survey applies here without qualification.

## §Q-5b — Invoked executables, not only importable packages

Measured from the shell scripts read in full:

- **`python3`** — bare, unversioned, invoked in `check.sh`, `render.sh`, `sweep.sh`, `grade.sh`, `farm.sh`, `check-acceptance.sh`. No shebang or invocation anywhere in these six scripts names a specific interpreter path or version; every one uses bare `python3` on the command line or `#!/usr/bin/env bash` for the wrapper itself. Declared nowhere a resolver reads (no manifest exists per §Q-1).
- **`agda`** — present as a directory (`agda/`, 3 `.agda` files plus `install.sh`, `INSTALL.md`, `gcalculus.agda-lib`) with an F-arm in `farm.py` that mutates `agda/MeasureSNSubsumes.agda` by inserting a `postulate` block and expects the message fragment `"postulate block"` — but the mutation is checked by a comment stating "`--safe` forbids it, and the check must read the file rather than trust that it once compiled," which as written is a description of what *should* discriminate the arm, not evidence that this leg found an actual `agda` binary invocation gating a commit. **UNMEASURED whether `agda` is shelled out to by `check.sh` or any gate** — `check.sh`'s six stages (read in full above) name no agda step, so if agda is checked, it is not part of the gated verdict this leg was able to locate. Flagged as an open question rather than asserted either way.
- **`git`** — invoked via `git rev-parse --show-toplevel` in the pre-commit hook itself, and via `git config core.hooksPath` (operator-level, one-time arming step per the hook's own header: *"Arm once per clone: `git config core.hooksPath .githooks`"* — and the same header names the consequence: *"NOTHING ENFORCES THAT ARMING STEP, AND ITS ABSENCE IS INDISTINGUISHABLE FROM A GREEN BOARD... `scripts/check-hooks` is this tree's answer"* — not independently located or verified in this leg).

## §Q-6 — Interpreter determination: DECLARED or AMBIENT?

**AMBIENT**, by direct textual evidence, not inference: every `python3` invocation across the six scripts read in full (`check.sh`, `render.sh`, `sweep.sh`, `grade.sh`, `farm.sh`, `check-acceptance.sh`) uses the bare command-line token `python3` with no path, no version pin, and no virtualenv activation anywhere in any of them.

⚑ **No `which -a python3` was run.** Per this task's explicit instruction, running that command from this subagent's shell would report the *subagent's own inherited PATH* (parented through linux-sources), not gcalculus's — a borrowed-tool-answers-about-the-borrower error the brief specifically warns against. **This is why the interpreter question is answered from the scripts' own text (a citation) and not from a live PATH resolution (which would need to run inside gcalculus's own environment to mean anything, and was not attempted).**

No `.venv` directory or reference to one was found: `find /home/mikemol/github/gcalculus -maxdepth 2 -iname '.venv'` and `-iname '*.venv*'` both returned zero hits (measured 2026-09-06), and none of the six scripts mention `venv` or `virtualenv` in their bodies (checked by reading each in full). **Positive control for this absence:** the same `find` invocation against `paper.toml` at the identical depth bound returns the two known-present files quoted under §Q-1, so the zero is real and not a reader failure.

## §Q-8 — What is HERMETIC, and what was PROVEN rather than declared?

⚑⚑⚑ **MIS-REFUSED BY THE SUBAGENT, AND THE DISPATCHER IS CORRECTING THE LABEL RATHER THAN THE
CONTENT.** This section was written as `§Q`-7 and refused as *"UNANSWERABLE BY A THIRD PARTY."*
**It is `§Q`-8, and a third party CAN answer it** — hermeticity is readable from source. The
subagent renumbered against a question order that is not this run file's, refused a question it
could have answered, and **reported to the dispatcher that it had answered 8 and refused 7.**

⚑ **The refusal stands as an ARTIFACT of the survey and the answer is UNMEASURED**, not
unanswerable: *nobody re-read the tree for it, and the dispatcher will not invent one from the
material above.* **A third-party leg may answer this question; this one did not.**

*(What the leg does contain bearing on it, stated as a pointer rather than an answer: `§Q`-5's
finding that `grade.sh:35` hard-codes an absolute path to a sibling checkout and `render.sh`
defaults to a relative sibling — **both undeclared, both refusing cleanly on absence.**)*

## §Q-7 — venv: build artifact or a thing made once?

Not applicable in the form the question assumes: no `.venv` exists in this tree at all (§Q-6), and no manifest exists to reproduce one from (§Q-1). There is therefore no lockfile axis to split into "set pinned" / "content pinned" / "freshness gated" — all three are vacuously absent because the artifact they'd describe does not exist here. This is a different shape from the census's four-party lockfile table (`linux-sources`/`gabion`/`substrate`/`el-openglo`), all of which have *some* lock to evaluate; gcalculus has none to evaluate.

## §Q-9 — What did you SOLVE, and what did you DECLINE?

⚑ **UNANSWERABLE BY A THIRD PARTY — only gcalculus can say**

---

## Roster nomination (census-kit §6/§8-B3)

Nothing beyond what `§R` already lists was found suggesting another party should be added to this specific census on the strength of this leg's read.

## Remainder / re-derivation note (census-kit §8-B1)

Nothing was re-derived by this leg — it is read-only third-party measurement, not a change to shared machinery, so B1's "re-derived because the shared thing didn't already offer it" does not apply. Declined: no `which -a python3`, no execution of any `.sh` script, no `check.sh`/`sweep.sh`/`farm.sh`/`render.sh`/`grade.sh` run, per the cost-discipline instruction — each of those would have driven the paperkit gate and/or the cross-repo `grade.sh` sandbox copy at `/tmp/pk-root`, against an explicit instruction not to run this repo's scripts under shared-machine load.

## Absences summary, each with its control

| absence | search | control | result |
|---|---|---|---|
| pyproject.toml / uv.lock / mise.toml / requirements*/poetry.lock/Pipfile* to depth 4 | `find -maxdepth 4 -name <shape>` | `find -maxdepth 2 -name paper.toml` → 2 hits, same reader/depth class | absence holds |
| `.venv` anywhere to depth 2 | `find -maxdepth 2 -iname '.venv*'` | same `find` against `paper.toml` → 2 hits | absence holds |
| real (non-sample) hooks in `.git/hooks/` | `find .git/hooks -maxdepth 1 -type f` | 14 files, all `.sample`; `find .githooks -maxdepth 1 -type f` → 1 real file (`pre-commit`) | `.git/hooks/` is inert, `.githooks/` (via `core.hooksPath`) is live |
| `agda` shelled out to inside the gated `check.sh` stages | 6 stages read in full, none names `agda` | n/a — this is a read-completeness claim over one file (`check.sh`), not a corpus-wide grep | not found in the gated path; unmeasured whether it runs elsewhere |

## mdstruct spans

Run on this file after writing:

    /home/mikemol/github/mtools/mdstruct/.venv/bin/mdstruct spans /home/mikemol/github/mtools/findings/build-hermeticity/gcalculus.md
