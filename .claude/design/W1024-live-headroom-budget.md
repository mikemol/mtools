# W1024: the sweep's memory budget follows live headroom (second order), not 0.4 × MemTotal

Written 2026-10-12. Evidence arm: the files named below, read in this session, and the three peer
messages quoted. Not measured: any heavy gate against the nvme sandbox (github-8f asked for one);
paperkit's full-sweep VmHWM (paperkit-d8 has a floor of 9.23 GB for the gate server only).

## What happened

2026-10-12 01:20-01:35Z, paperkit's W319 gate ran `bazel test //:hook --config=mutant
--config=remote --local_resources=memory=51482` through mikemol-commit's isolated path. With the host
`~/.bazelrc` putting `--sandbox_base=/dev/shm`, bazel ran about 24 local sandboxes of about 2 GiB
each in a RAM-backed tmpfs (48 to 51 GiB), filled the 64 GiB zram swap and set `zram_write_failed`.
(luthen-observability:W838/W839, github-8f, paperkit-d8.)

## Where 51482 comes from (read, not guessed)

`paperkit/.githooks/pre-commit` line 245: `PK_SWEEP_RAM=$("$PY" -m tools.sweep_budget)`, then line
301-302: `... --local_resources=memory="$PK_SWEEP_RAM"`. `tools/sweep_budget.py` (paperkit's own copy)
returns `PAPERKIT_SWEEP_RAM_MB` if set, else `int(MemTotal × 0.4)`; 0.4 × the 125.7 GiB this host
reports is 51482 MB. mtools' `memres/src/mikemol/memres/sweep_budget.py` is the same function, ported
(paperkit:W142) and **not called by paperkit's gate**; mtools' `gatecheck/rungate.py` calls
`<repo>/tools/sweep_budget.py`. So a change in `memres` reaches paperkit only when paperkit consumes it
(paperkit:W289). The docstring says why the default ignores `MemAvailable`: on a zram host it is low
by design, and budgeting against it would run one cell. That reasoning was right for MemAvailable and
wrong as a whole: it has **no swap term and no sandbox term**, so it cannot see the two things that
failed.

## What the operator asked for (via github-8f, 2026-10-12)

True fixes are second-order: not first-order, not thresholds. Rails are neither linear nor static. A
budget is a LEASE that follows live headroom: level (MemAvailable plus swap and sandbox headroom),
slope and acceleration, re-evaluated while the run goes, shrinking allowed parallelism when use is
accelerating and recovering when it decays. luthen W842 and host W26 supply the predictors. The vehicle
should be the membudget and fence leases if they can be resized mid-run. Publish rail engagement
(granted, resized, refused). The nvme sandbox_base (host `~/.bazelrc`, set by github-8f) is the static
stopgap beneath it.

## Constraints that shape the design (read from code)

1. **Bazel cannot change `--local_resources` while running.** The flag is read at invocation. So
   "re-evaluated while the run goes" cannot be a changing flag. It has to be an admission gate that
   each memory-heavy action passes through, or a ceiling applied outside bazel (the cgroup, W1026).
2. **A held fence lease cannot be resized.** `fence/admit.py` has acquire, release and gc and no
   verb that changes a held lease's mb. The ledger TOTAL can be resized in place keeping live leases
   (`membudget init --reset N`, `resize()` in `membudget_cli.py`): that throttles NEW admissions only.
   A resize verb for a held lease is W1029; the engagement series is W1030.
3. **paperkit's cells already declare a `resource_set` per cell (about 2 GB).** The sweep grid is
   what the budget bounds; its per-claim checks declare none (paperkit pre-commit, comment at line 222).
4. **The sandbox is memory too** when `--sandbox_base` is tmpfs. With it on nvme (done) the RAM cost
   is the cells' own, but the page cache of copied inputs still counts.

## The design in three slices

**A. The rail model, pure (mtools:W1033).** In `memres`: from a window of `(t, level_mb)` samples
compute level, slope and acceleration (finite differences, with the window length and the sample
count as parameters, not constants buried in code); and a pure policy
`next_allowance(prev, level, slope, accel, cell_mb, floor, ceiling) -> int` that returns how many
cells may run: it shrinks when `slope < 0` and the extrapolated level inside one horizon would go
below a reserve, shrinks harder when acceleration is also negative, recovers by one step while
`slope >= 0`, never below a floor of one cell and never above the old 0.4 × MemTotal ceiling. No I/O,
so it is tested without a host. `level` is `MemAvailable` plus the part of free swap the zram ratio
makes usable, minus a sandbox term; the exact weights are inputs, to be fitted from luthen's series.

**B. The sampler and the vehicle (mtools:W1034).** A small process that reads `/proc/meminfo` on an
interval, feeds A, and applies the allowance by resizing the fence ledger TOTAL (works today, new
admissions only) and, once W1029 exists, by resizing held leases; and writes the engagement counts as
a Prometheus textfile (W1030). Best-effort, like `cpuweight`: failing must never fail a build.

**C. paperkit adopts it (mtools:W1035, a letter; paperkit:W334/W289 own the change).** Its pre-commit
calls the mtools `memres` budget instead of its own `tools/sweep_budget.py`, and its sweep cells hold
fence leases so the allowance has something to gate. Until then paperkit's stopgap is
`PAPERKIT_SWEEP_RAM_MB`, set by hand to a figure with headroom (told 2026-10-12: 16000).

## What this design does not claim

That 0.4 is wrong in itself (it is a ceiling, kept as one), that a slope estimate from a few samples
is reliable on a host this bursty (the 01:20-01:35Z burst was 60 GB in 15 minutes: a sampler on a
seconds interval may see it only after it is done; that is a reason the lease gate should sit in front
of the cells, not behind a sampler), or that the zram term is right. Those want luthen's series.
