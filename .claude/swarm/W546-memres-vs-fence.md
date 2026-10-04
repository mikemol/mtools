# W546: paperkit memory/cgroup tools vs mtools fence (content measured)

Fence modules (fence/src/mikemol/fence/): __init__, cgroup, cli, core, peaks, ledger, autosize, admit, membudget_cli, label_lease, git_env.
Grep over fence/src for `cpu.weight`, `zswap`, `memory.current`, `sqlite`: no hits. `MemTotal` appears once (admit.py:627).

## Per module

| paperkit module | does | reads / writes | closest fence | class |
|---|---|---|---|---|
| mem_learn.py | pow2-buckets per-claim cell peaks into a delta-encoded per-project manifest `{file,def,claims}` (resolution(), 36; pow2(), 29; main(), 57) | reads `<claim>__{calc,dcalc}.peak` files (bytes or `unavailable:*`); stdout JSON | ledger.bucket (ledger.py:59) is the same pow2 rule; ledger.report/p90 (ledger.py:218/202) aggregate peaks; autosize.size (autosize.py:70). Fence keys by ledger label, has no file/def resolution, no claim ladder, no manifest | SUBSET (pow2 only) |
| mem_db.py | sqlite observation store, monotone-max upsert per (project,resolution,claim,cell), manifest() as a query, provenance() (mem_db.py:40-111) | writes/reads `mem.sqlite` table `peak` | fence's store is a TSV label ledger (ledger.py:parse 132, record 303) and the admit ledger; no sqlite anywhere. Role is analogous to ledger.record but the schema, key and "raise never lower" rule differ (fence records clean exits only, ledger.py:260) | DISJOINT (different store, different key; same idea only) |
| mem_project.py | project mem.sqlite to `mem.json` for Starlark, with `--check` freshness (render, 29) | reads sqlite, writes `mem.json` | none. Consumer is bibtex.bzl repo rule (bibtex.bzl:752) | DISJOINT (Bazel build input; fence has no such consumer) |
| mem_harvest.py | rglob `*.peak` under bazel-out and deposit into sqlite (peaks_for 40, deposit 68) | reads `bazel-out/**/*.peak`; writes sqlite via mem_db | none. fence peaks come from its own run_once (core.py:229, cgroup.read_peak cgroup.py:284), not from a file tree | DISJOINT |
| mem_converge.py | checks each bib project with a pk_eval grid has a `def` bucket and no cell at the floor (survey 86) | reads external BUILD.bazel (`pk_eval(... mem = N)`), MODULE.bazel, `mem.json` | none. Self-labelled "INSTRUMENT, not a gate"; no caller | DISJOINT, and uncalled (retire candidate) |
| sweep_budget.py | RAM budget for `--local_ram_resources`: env `PAPERKIT_SWEEP_RAM_MB`, else MemTotal x 0.4 (budget_mb 43) | reads /proc/meminfo, env; stdout int | admit.default_total_mb (admit.py:619): `min(70% of MemTotal, 8192)` MB, same /proc/meminfo read. Fence's value seeds the admission ledger; paperkit's goes to a Bazel flag | SUBSET (same MemTotal-fraction derivation, different fraction/cap/consumer) |
| cpuweight.py | creates `paperkit-build.scope` under app.slice, sets `cpu.weight` (default 20), moves bazel client and server in, `--verify` cells inside, runnable/core report (build_cgroup 103, apply 217, verify 188) | writes cpu.weight, cgroup.procs; reads /proc/*/cgroup, comm, /proc/stat | fence cgroup.py has own_cgroup (89) and parent_with_controllers (118), write_interface (239) for creating a sibling cgroup, but sets memory.max/pids only (core.py:165); CPU weight is unmeasured by fence | DISJOINT (CPU share, not memory; fence has no cpu controller use). Shares cgroup-v2 plumbing only |
| zswap_probe.py | one-pass sample of a cgroup's current, peak, zswap, zswapped, zswap.max, memory.max, pinned flag, hierarchy walk (sample 93, zswap_bound 69) | reads memory.current/peak/stat/zswap.max/zswap.current/memory.max/memory.swap.max | cgroup.read_peak (cgroup.py:284) covers memory.peak only; fence has no zswap or memory.current read | DISJOINT (different data product: zswap compression and pinning). Uncalled |
| cellcgroup.py | a sweep cell reads its own cgroup `memory.peak`, writes it to the `.peak` file; oom_counts/oom_happened from memory.events (own_cgroup 29, peak_bytes 37, write_peak 58, oom_counts 66, oom_happened 87) | reads /sys/fs/cgroup/<own>/memory.peak, memory.events; writes `.peak` file | cgroup.own_cgroup (cgroup.py:89), cgroup.read_peak (cgroup.py:284), cgroup.read_events (cgroup.py:257), bound_by (cgroup.py:318, uses oom_kill) | DUPLICATE of fence's cgroup.py read primitives (in-process, no fence lifecycle). Not a drop-in swap: output format is paperkit's `.peak` vocabulary and it must run inside the cell |

## Call sites in paperkit (Grep over *.py, *.bzl, BUILD.bazel, .githooks/pre-commit)

- mem_learn: tools/calc.bzl:270 (`_tool`, rule pk_mem_learn), tools/bibtex.bzl:1100, tools/BUILD.bazel:8, BUILD.bazel:87; imported by mem_db, mem_harvest. LIVE.
- mem_db: imported by mem_project, mem_harvest; BUILD.bazel:84, tools/BUILD.bazel:8; test paperkit/tests/boundaries_mem_db.py. LIVE.
- mem_project: .githooks/pre-commit:236 (`--check`); tools/BUILD.bazel:8. LIVE.
- mem_harvest: .githooks/pre-commit:315 (best-effort). LIVE.
- sweep_budget: .githooks/pre-commit:239, tools/rungate.py:62. LIVE.
- cpuweight: .githooks/pre-commit:294; test paperkit/tests/boundaries_cpuweight.py. LIVE.
- cellcgroup: tools/eval.py:43,360-381; tools/BUILD.bazel:57. LIVE (every sweep cell).
- mem_converge: docstring says referenced by no BUILD, .bzl, hook or warrant. Grep hits only its own file plus listings; no caller found. UNCALLED.
- zswap_probe: same docstring claim. I found no caller outside itself in the grep file list (the file list contained it only via the pattern); UNCALLED. Test boundaries files named boundaries_dispatch.py, sortaudit.py, closure.py, components.bzl, arch/BUILD.bazel, warrants.bib matched the pattern; I did not open them, so a mention there (for example as a warrant) is UNMEASURED.

## Second memory-budget client?

No. None of the nine reads, writes or locks the admit ledger (grep for membudget/admit/lease in the pre-commit, sweep_budget, cpuweight: none besides prose; tools/cgroup-scope mentions membudget in comments only, and I did not read that script's logic past the grep). sweep_budget.py computes a number and hands it to Bazel (`--local_ram_resources`); that is a sizing input, not a lease. It is nonetheless a second, independent derivation of "how much RAM may the box spend" (0.4 x MemTotal vs fence 70% capped 8192); not a ledger client, so no conflict with "the one client", but a divergence risk.

## Recommendation

- Fold into fence (cgroup.py/ledger.py consumers): nothing wholesale. Candidate re-expressions: cellcgroup's own_cgroup/peak_bytes/oom_counts onto fence.cgroup.own_cgroup/read_peak/read_events (needs fence to be importable inside a Bazel sandbox cell: UNMEASURED); mem_learn.pow2 onto ledger.bucket (floor differs: paperkit LO=4 vs ledger BUCKET_FLOOR_MB, value not read here: UNMEASURED); sweep_budget onto admit.default_total_mb (policy differs, operator decision).
- Separate package for the DISJOINT remainder: `mikemol-memres` is justified for the reservation-ladder pipeline only: mem_learn, mem_db, mem_project, mem_harvest (one data product: per-project sqlite of cell peaks projected to mem.json for a Bazel generator) plus cellcgroup (its producer of `.peak`). It has a different consumer (bibtex.bzl) than fence. It would depend on fence.cgroup for the primitives.
- cpuweight and zswap_probe are CPU-share and zswap telemetry, not memory admission; they do not belong in memres by data product. cpuweight is live in pre-commit and tied to Bazel server discovery: leave in paperkit (or a `cpuweight` module if ported). zswap_probe: leave or retire.
- Retire candidates (no callers): mem_converge.py, zswap_probe.py (confirm the unopened files above first).
- Also: sweep_budget stays with the pre-commit/rungate caller; consider reading admit.default_total_mb instead of a second fraction.

## UNMEASURED
- Whether fence is importable in a Bazel sandbox cell; ledger.BUCKET_FLOOR_MB value; contents of tools/cgroup-scope logic; whether warrants.bib/arch/BUILD.bazel/boundaries_dispatch.py mention zswap_probe or mem_converge as warrants; runtime behaviour of any module (nothing executed).
