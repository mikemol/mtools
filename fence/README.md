<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-fence

Run a command inside a cgroup v2 fence and report **what it consumed** and **which cap bound it**.

Caps are optional. With none set, this is a complete observe-only measurement: a transient cgroup
is created, the payload and every descendant it forks are charged to it, and its peak memory,
duration, exit code and event counters are read — with nothing capped and nothing killed.

```console
$ mikemol-fence --observe --json -- ./my-command
{"cmd": ["./my-command"], "caps": {"mem": null, ...}, "duration_s": 0.2,
 "exit_code": 0, "memory_peak_bytes": 1789952, "memory_events": {...},
 "pids_events": {"max": 0}, "bound_by": [], "completed_within_caps": true}
```

## Why the separation matters

A workspace census of ten repositories found this to be the only tool that returns structured
timing and memory for a child command **without also having the power to kill it**. The
alternatives either measure *by* killing — an OOM ladder whose kill is the reading — or measure
the wrong scope entirely: one caller read `/proc/self/cgroup` from the action shell while the work
ran in a child scope, and reported a 35 MB cell as 4.7 MB.

Two rules follow, and both are load-bearing:

- **The fence is on the cgroup, never on the process.** A child process escapes a per-process cap
  and is still charged to the cgroup. Learned the hard way from a `git stash create` that slipped
  a `RLIMIT` and was caught by the cgroup.
- **Which cap bound is read from the counters, never inferred from the exit code.** `rc=137` is
  any `SIGKILL`. `memory.events` and `pids.events` can tell the fence's kill from someone else's.

## Capping

```console
mikemol-fence --mem 2G --swap 0 --pids 64 -- ./my-command
```

`--swap 0` is what makes `--mem` a kill boundary rather than a reclaim threshold. Measured on a
zram host: 64 MB allocated under an 8 MB cap **succeeded**, with 261 limit hits and zero kills,
because the kernel compressed into swap instead of killing. The two writes are one control.

## Finding the scale of a resource

```console
mikemol-fence --ratchet 4G,2G,1G,512M -- ./my-command
```

Tightens until one cap binds. A cap above the payload's legitimate peak proves nothing, so the
step that *binds* names the scale the command actually needs. This is the one actuating mode, and
it is a separate entry point from `run_once` so the choice is explicit at the call site.

## Exit codes

| code | meaning |
|---|---|
| the payload's | normal — the fence is transparent |
| 125 | the harness could not fence (no cgroup v2, no delegated controller) |
| 126 | the command was found but not executable |
| 127 | the command was not found |

125 is a *cannot-run*, never mixed with a payload result.

## Requirements

Linux, cgroup v2, with `memory` and `pids` delegated to your subtree. Python ≥ 3.13, stdlib only.
The controllers are needed even for an observe-only run: `memory.peak` does not exist in a cgroup
whose memory controller was never enabled.

## Origin

Packaged out of `cassian-observability/scripts/resource-fence` (A170/A186), which remains in place
as a shim. It was a single-file script reachable only by path or symlink; the census that prompted
the move recorded what copying costs instead — `cgroup-scope` exists in two repos with four fixes
that never travelled back, including a measured 1-in-24,376 name collision that killed a build.
