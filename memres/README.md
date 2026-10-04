<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-memres

The memory-reservation tools of paperkit's `tools/`, ported here (mtools:W554, paperkit:W142). One
data product: a per-project sqlite store of observed cell peaks, its Starlark-readable projection,
and the build-host sizing helpers beside it. Behaviour is paperkit's; the entry points are console
scripts and `python -m` modules instead of paths, and the host's cgroup, proc and meminfo roots are
parameters so a test can plant a fake host.

None of these touches the memory-admission ledger, so none folds into `mikemol-fence` (W546).

| module | script | does |
|---|---|---|
| `mikemol.memres.mem_learn` | (library; `-m`) | pow2-buckets observed `.peak` files into a delta-encoded manifest |
| `mikemol.memres.mem_db` | (library; `-m`) | the `mem.sqlite` observation store: monotone-max upsert, manifest as a query, provenance |
| `mikemol.memres.mem_project` | `mikemol-mem-project` | projects `mem.sqlite` to `mem.json`, with `--check` freshness |
| `mikemol.memres.mem_harvest` | `mikemol-mem-harvest` | folds the cell peaks found under `bazel-out` into the store |
| `mikemol.memres.mem_converge` | (`-m` only) | has the reservation loop converged: a `def` bucket and no cell at the floor |
| `mikemol.memres.sweep_budget` | `mikemol-sweep-budget` | the RAM budget for `--local_ram_resources` |
| `mikemol.memres.cpuweight` | `mikemol-cpuweight` | puts the build's own cgroup under a proportional CPU weight |
| `mikemol.memres.zswap_probe` | (`-m` only) | one-pass sample of a cgroup's memory and zswap counters |

`mem_converge` and `zswap_probe` have no caller in paperkit; they are ported as they stand and
retiring them is paperkit's call.
