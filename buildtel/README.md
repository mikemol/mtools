<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-buildtel

The build-telemetry tools of paperkit's `tools/`, ported here (mtools:W543, paperkit:W142).
Behaviour is paperkit's; the entry points are console scripts and `python -m` modules instead of
paths. Standard library only.

| module | script | does |
|---|---|---|
| `mikemol.buildtel.bb_records` | `-m` only | `<invocation-id>`: counts BuildBuddy's execution records by worker and command, as JSON |
| `mikemol.buildtel.buildpulse` | `-m` only | `--log <f>`: a running `//:hook`'s progress and windowed action rate; names a failure, a gone build, a stall; `--selftest` proves each arm can fire |
| `mikemol.buildtel.logs_push` | `mikemol-logs-push` | `<hook-log> [--rc N] [--seconds N] [--run-id ID] [--url URL]`: pushes a gate run's findings to a log store |
| `mikemol.buildtel.coord_sample` | `mikemol-coord-sample` | `<pid> <out.jsonl> [--interval=S]`: appends the coordinator's memory until the pid exits |
| `mikemol.buildtel.image_digest` | `mikemol-image-digest` | `<image>`: prints the executor image's digest, or `absent` |
| `mikemol.buildtel.probe` | `-m` only | `<file> [--no-resync]`: how many actions editing one file re-executes |
| `mikemol.buildtel.proc` | none | the one place a child process is started |

## Not ported

`project_endpoints` is left out: it locates `.bazelrc` from the module's own path
(`Path(__file__).resolve().parents[1]`), which is paperkit's tree and has no meaning for an
installed module. Which `.bazelrc` it edits is a decision for paperkit, not a guess here.

## Changes from paperkit's modules

- Each module has `main(argv=None)` and a `__main__` guard; paperkit's `# noqa` waivers became
  structure. Child processes (`pgrep`, `bazel`) go through `proc`, and every module that reaches
  the network, a child, `/proc` or a clock takes it as a parameter, which is how the tests drive
  them.
- `coord_sample` handles SIGINT inside `main` (paperkit did it in the `__main__` guard), so the
  console script exits 0 on it too.
- `probe`: the marker line names `mikemol.buildtel.probe` instead of `tools/probe.py`; the revert
  is verified after the `finally` that performs it, because a `return` inside a `finally` swallows
  the exception being unwound.
- `buildpulse --selftest`: its checks are `(name, verdict)` pairs, and their labels are ASCII
  (`delta`, `=>`) where paperkit's were Greek and angle-bracket glyphs.
- `image_digest`: a digest reply that is JSON but not an object is `absent` (paperkit raised
  `AttributeError`).
- `bb_records` and `logs_push` print their module's own name in usage and messages instead of the
  script path.

`image_digest` still names luthen-observability's checkout by absolute path
(`/home/mikemol/github/luthen-observability`), as paperkit's did; `directory` is a parameter.
