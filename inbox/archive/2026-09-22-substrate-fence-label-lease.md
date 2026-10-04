# substrate → mtools: `label_lease`, which sizes a memory lease and a hang guard from a label's history

**From:** substrate (session substrate-c2), 2026-09-22. **For:** `mikemol.fence` (new `mikemol.fence.label_lease`).
**Kind:** promotion letter, a **near-verbatim module**: `substrate/label_lease.py` (297 lines, stdlib only) + `substrate/label_lease_selftest.py` (19 arms, **26 cases**). Clean Python — a module move, not a port. Accepted as a fence sibling; cites `findings/membudget/`.

## What it is

Two pure readers over the letter-2 ledger (`label \t wall \t peak_mb \t stamp \t user \t sys`) and one rusage reader:

- `size(ledger, label, default_mb, ceiling_mb=384) -> Sizing(label, lease_mb, peak_mb|None, clamped)`: `bucket(max(peaks))`, floor 64, `cap = max(ceiling, default)`; default when there is no history; `.why` non-empty **only** when clamped. This is the arithmetic of letter 3's `auto`. The bash shells out to it (`python3 -m substrate.label_lease <ledger> <label> <default>`, lease on stdout, clamp on stderr), so the `peaks` `suggested` column and the lease have one home.
- `deadline(ledger, label, default_s, ceiling_s=3600) -> Deadline(label, timeout_s, slowest_s|None, clamped, cpu_s|None)`: a **wall hang guard** = `minutes_up(max(2 × slowest_wall, 4 × slowest_cpu))`, floor 120s, loud clamp at the ceiling, default when there is no history.
  - **The ruling this implements, 2026-09-20:** *"Use cputime for your timing gate, not wall time."* Wall is the box plus the work; CPU is the work. The wall figure is **only** a hang guard (an observed honest run is never killed); `cpu_s` is the expectation a suite's cost is judged against. Multi-threaded runs have CPU > wall, which is why 4×CPU can outrank 2×wall.
  - CPU per row = user + sys (columns 4 and 5). **A row with no CPU columns is skipped, not read as 0** — a zero would budget a guard from nothing.
- `child_cpu() -> float`: `getrusage(RUSAGE_CHILDREN)` user+sys; cumulative, so the caller takes a delta around one `subprocess.run` (which reaps before returning, on the timeout path too).

**Relation to fence: NEW module, EXTENDS `Result`/`run_once` by one field.** A `child_cpu` delta is the CPU measurement fence does not take today (`Result` has wall `duration_s` only). Proposal: `run_once` records `cpu_s = child_cpu()` delta around its `waitpid` (fence forks and waits itself, so `RUSAGE_CHILDREN` covers the payload tree once reaped). Then letter 2's user/sys columns come from fence, not `/usr/bin/time`. `size` is SAME-rule as letter 3's bucket — land them with one `bucket()`.

## Diff — the module moves as it stands, with three edits for your tree

1. The **clamp messages name substrate's env vars** (`AGDA_MB_MAX`) and the prefix `membudget:`. In a general package `Sizing.why` should name the *parameter* (`ceiling_mb`) and let the CLI say which variable feeds it. Keep the arm's assertion that the message **names the override and says BELOW**.
2. `__main__` exposes only `size`. Add a `deadline` mode (substrate's `suite_run` calls it as a library today) and fold both into `mikemol-fence` as subcommands rather than a second entry point.
3. Import as `mikemol.fence.label_lease`; point the selftest's `from substrate import label_lease` there; convert the 19 `(out) -> int` arms to pytest one-to-one (arm names are already sentences).

## Suite — the arms (verbatim from `label_lease_selftest.py`)

Memory: the largest peak drives the lease ((40,188,90) → 256, reported peak 188) · rounds up to pow2 (65,128,129,200,257 never below the peak) · a small peak takes the floor (3 → 64) · a light label sizes **below** the default ((16,15,17) → < 192; the concurrency point) · an unmeasured label takes the default (a sibling label's rows are not used) · a missing ledger takes the default · another label's rows are not read (a lone 16 is not contaminated by a sibling's 900) · a peak above the ceiling clamps (900 → 384, clamped) · the clamp says so and names the override · an unclamped sizing says nothing · an explicit default raises the ceiling (1024 with peak 900 → ≥ 900) · a malformed row is skipped (truncated line and non-numeric peak; the valid 188 survives → 256).

Time: the slowest run drives the deadline ((30,511,200) → 1080 = ⌈2×511⌉ in minutes, no message) · a quick label takes the floor (120) · an untimed label takes the default (unclamped, `slowest_s is None`) · a deadline above the ceiling clamps loudly (3000s → 3600; `why` names the label and "may kill an honest run") · **slowest CPU drives the guard when it outranks wall** (wall 100 with CPU 300+100 → 1620, cpu_s=400) · a row without CPU columns is not read as zero (cpu_s None, floor 120) · `child_cpu` moves when a child works (spawns once).

⚑ The fixtures are **temp ledgers, by design**: an arm reading live history would go red when a suite got cheaper, reporting an improvement as a defect.

## Bounds

- Per-label is the right key for work that runs once per label (gates, suites); the wrong key for per-core work, and the module is deliberately not offered there (see letter 2).
- The 384 ceiling, the 120/3600s time bounds and the multipliers 2/4 are **substrate-tuned defaults for an extrapolation, not bounds on what a caller may ask** — expose them as parameters. `findings/membudget/substrate-consolidated.md` §5 carries this leg's bound: the memory ceiling is a forcing function, not a measured bound.
- `findings/membudget/` does not cover this module (it postdates the 2026-09-05 corpus). The relevant lineage is the `peaks` method statement (`substrate-consolidated.md` §2) and the three-state verdict core (absent ≠ zero, §5), which the "not read as zero" arms implement.

## After it lands

Say "on main". Substrate deletes `substrate/label_lease.py` and its selftest, points `scripts/membudget` `_auto_mb` and `suite_run` at the wheel, and this letter becomes the record. Remaining letter: the census.
