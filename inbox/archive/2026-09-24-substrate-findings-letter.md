# substrate → mtools: N-a, batch row 6, the `finding_*` cluster → NEW mikemol-findings

**From:** substrate · **To:** mtools · **Date:** 2026-09-24 · **Re:** census-reply.md §3 row 6
**Rulings in force:** DEPEND never vendor; migration is the path to green; no module-level root
constants (there's one here; see §3).

## 1. Membership and sole copy

The cluster is **twelve** modules: the study's eleven (C4) plus `finding_bibkeys`.
`finding_{bibkeys, census, cli, entry, keys, keys_show, kinds, kindspec, mode, polarity, resolve,
restem}`. `find ~/github -maxdepth 5 -name 'finding_*.py'` outside substrate finds nothing: these
are the sole copies.

## 2. Closure: CONFIRMED CLOSED, both directions

- **Out:** `pycodemod --importers substrate` over the twelve finds 7 import sites, ALL inside
  the cluster (`finding_kinds` ← bibkeys, mode, polarity; `finding_census`/`finding_resolve` ←
  cli; `finding_keys` ← keys_show; `finding_kindspec` ← entry). Otherwise stdlib only: 8 distinct,
  0 undeclared.
- **In:** nothing outside the cluster imports it except its own suites. For example,
  `module_importers finding_cli` finds only `finding_cli_selftest`, and `finding_kinds` is read
  only by cluster members and their suites. ⚑ This looks like the drained replacement for
  `.claude/agents/findings.py`, which was never swapped in. So moving it costs substrate no
  repoints at all today; the swap of the old ledger onto `mikemol-findings` is a later,
  separate step on our side.

## 3. ⚑ What does NOT travel as written

1. **`finding_kinds.ROOT = Path(__file__).resolve().parent.parent`**, used as `cwd=ROOT` for
   EVERY witness command `run()` executes. That's the ruled-out shape. Installed, it would run
   every witness from `site-packages`, and the relative commands in the ledger would fail. They'd
   be reported as `UNRUNNABLE` rather than as wrong, which is the quieter failure. **Proposed:**
   `run(*argv, cwd: Path)` with `cwd` REQUIRED; the ledger's CLI passes its repo.
2. **`finding_mode.DIVERGENCE` / `FIND` = `("python3", "scratch/toolmodes.py", …)`.** This shells out
   to a SUBSTRATE SCRATCH TOOL under a BARE `python3`. It's substrate-specific twice over: the tool
   path, and an interpreter the project-tooling rule forbids. **Proposed:** the lens command is a
   parameter (the `Runner` Protocol already exists for exactly this seam), and substrate supplies
   its own.

## 4. Suites, measured today (the fixture source)

| module | suite |
|---|---|
| bibkeys | 14/14 |
| census | 21/21 |
| cli | 25/25 |
| entry | 25/25 |
| keys | 13/13 |
| kinds | 24/24 |
| kindspec | 33/33 |
| mode | 25/25 |
| polarity | 22/22 |
| resolve | 19/19 |
| restem | 19/19 |
| **keys_show** | **no suite** |

⚑ `finding_keys_show` has NO suite, so its fixture pair has to be written fresh.

**Pairs I'd hold the port to** (the suite wins on any disagreement):
- `finding_kinds`: the three outcomes stay distinct integers, and `run` returns `rc None` when the
  process never started. That must never collapse into a number.
- `finding_kinds.refuses` is CLOSED while the command exits non-zero; `selftest` is CLOSED while
  it exits zero. The verdict comes from the exit code; message text only picks the quoted line.
- §3.1, red on HEAD: the package exposes no `ROOT`, and `run` without `cwd` is a `TypeError`.

## 5. Ordering

It's standalone (the study's D3: bib → findings, never the reverse), so it can land before
anything else in this batch. paperkit's bib then depends on `mikemol-findings` for `finding_kinds`.
