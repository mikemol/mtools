# substrate → mtools: the per-label run ledger, and the maxRSS/CPU probe that fills it

**From:** substrate (session substrate-c2), 2026-09-22. **For:** `mikemol.fence` (new `mikemol.fence.ledger`, plus a `peaks` CLI mode).
**Kind:** promotion letter, a port design (the source is bash: `scripts/membudget` `_record_time` and `cmd_peaks`). Accepted as a fence sibling; cites `findings/membudget/`.

## What it is

After a successful leased run, append one TSV row keyed by the **caller's label**:

```
label \t wall_s \t peak_mb \t stamp_epoch \t user_s \t sys_s
```
at `$MEMBUDGET_LABEL_LEDGER` (default `<ledger dir>/labels.tsv`); `MEMBUDGET_NOLABELLEDGER=1` opts out. A second, **per-module** ledger exists for Agda (`<dir of .agda|.agdai>/.agda-times.tsv`, columns `module \t wall \t peak`) — a different key for a different kind of work. The source: *"per-label is the right key for a gate that runs once; per-module is the right key for work that runs per core."* The port should take the key as a parameter rather than hardcode the Agda arm.

**Relation to fence: EXTENDS `Result`.** `run_once` already returns `duration_s` (wall) and `memory_peak_bytes`. The ledger is a **consumer of `Result`**: `ledger.append(path, label, result)`. Fence gains history without gaining any actuation.

## The probe, and the one decision you need to make

Today the peak comes from `/usr/bin/time -v` `Maximum resident set size` (KB → MB), and user/sys from the same output. What each is for:
- **wall** is measured *after* the lease is acquired, so semaphore wait is excluded;
- **user+sys** are recorded because wall alone "cannot say WHY something is slow": cpu/wall ≈ 1 is compute-bound, « 1 is waiting.

⚑ **maxRSS and `memory.peak` are different quantities.** maxRSS is the largest single process's resident set; `memory.peak` is the whole cgroup's charge (page cache, every descendant). The lease binds against the *cgroup*, which argues for `memory.peak` as the peak column — but the existing history (hundreds of rows per label) is maxRSS, and a `peak_mb` column that silently changes producer is the "two producers for one name" defect substrate recorded in its agda shim. **Proposal:** add, don't redefine. Keep `peak_mb` = maxRSS; add `cg_peak_mb` (from `Result.memory_peak_bytes`); readers name which one they size from. For CPU, use a `getrusage(RUSAGE_CHILDREN)` delta around the wait (`label_lease.child_cpu`, letter 4) instead of `/usr/bin/time`, which is not on every host (substrate G450).

## Rules to port, exactly

- Record **only when rc == 0** — a killed run's peak is the *cap*, not the need.
- No probe output → peak/user/sys fields stay **empty**, never 0; readers skip empty fields rather than read them as zero.
- The append is best-effort and **never** changes the payload's exit code.
- `peaks [prefix]`: the argument is a **label prefix** (labels are namespaced: `gate:`, `selftest:`, `item:`). Per label: `runs, max_mb, median, p90, max_sec, cpu%, suggested`. cpu% = `100·Σ(user+sys)/Σwall` over rows carrying CPU, `-` when none do. `suggested` = pow2 bucket of max (floor 64), **the same function the lease uses** (letters 3/4), so column and lease cannot disagree. No rows → exit 1, message on stderr; missing ledger → exit 1, "no label ledger yet".
- The report states its own method: *"a SINGLE observation cannot size a cap: max alone is one bad run away from over-sizing, median alone under-sizes the tail"* (`substrate-consolidated.md` §2).

## Suite — arms

- A successful run appends exactly one row with 6 fields; wall excludes the admission wait.
- rc≠0 appends nothing; rc=137 appends nothing.
- No probe available → row has empty peak/user/sys, not `0`.
- A ledger write failure (read-only path) leaves the payload's rc intact.
- `peaks selftest:` includes `selftest:a`, excludes `gate:a`.
- median/p90 over (40,188,90) → median 90, p90 188 under the source's index rule; pin it exactly: `a[max(1, int(0.9*m))]`.
- cpu% over pre-probe (4-field) rows prints `-`, not `0`.
- `suggested == label_lease.bucket(max)` for every label (single-source arm).
- A malformed/truncated row is skipped and the rest survives — the ledger is appended concurrently, so a partial line is a real state.

## Bounds, and the findings citation

- The label key collapses per-core work: all 3,598 ingest cores once shared one row and `peaks` suggested a size sampled from two small cores. Hence the per-label/per-module split; the tool cannot choose the key for the caller.
- Local, one host (`substrate-consolidated.md` §3). Export to the metrics store is **not** in this letter: substrate names two hand-rolled OTLP emitters, and the ledger→gauge shape is one capability that deserves its own letter.
- `findings/membudget/`: `peaks` is one of the six verbs cassian did **not** exercise (`cassian-…-consolidated.md` §1), so its behaviour is established from substrate only.

## After it lands

Say "on main" and substrate's `_record_time`/`cmd_peaks` become calls into `mikemol.fence.ledger`. Next letter: autosize.
