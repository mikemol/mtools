# W916 (luthen-observability:W710): a run-time guard for the fenced commit (2026-10-09)

Ask (operator via luthen): a datastore-latency guard "belongs in mikemol-commit as a fence
predicate": while a heavy gate runs, sample an external reading (kine p99 from VictoriaMetrics) and
interrupt the build's bazel client when it stays over a limit. Reference implementation:
luthen-observability/checks/kine_guard.py (320b714), tests kine_guard_test.py.

## What the fence has today (answers question 1)

Admission predicates only: `admit.load_ok` (fence/src/mikemol/fence/admit.py:475) and the zram gate
`zram_fits` (:724) / `_zram_state` (:897) are read BEFORE a request is admitted, and the request
waits while they fail. Nothing is evaluated while the fenced command RUNS, and nothing acts on a
trip. A run-time guard is a new concept, so it is designed here rather than quoted.

## Design

A **guard** is a declared row, a reading, and a rule:

```
[[guard]]
name = "kine-latency"
reading = "promql"                       # the source kind
endpoint = "vmsingle-http"               # a NAME; the address is the host's, never mtools'
query = 'histogram_quantile(0.99, sum by (le) (rate(kine_sql_time_seconds_bucket[5m])))'
above = 4.0                              # seconds
samples = 6
interval_s = 30
signal = "SIGINT"
target = "bazel"                         # the descendant process to interrupt
```

- **Rule (pure)**: `streak_after(streak, sample, limit)` and `trip_index(samples, limit, n)`; an
  unreadable sample (None) neither counts nor resets the streak: a blind guard must not kill a
  healthy build. Unit-tested with planted series (answers question 4: no live store needed).
- **Reading (effectful edge)**: ask the named endpoint one PromQL instant query. The name resolves
  through a host-supplied name-to-url file (`MIKEMOL_ENDPOINTS`, JSON), so no address is in mtools
  (question 3: the limits live in the policy row, the address in the host's file). A transport
  failure or an unparseable answer is a blind sample.
- **Watcher**: runs beside the fenced command, samples every `interval_s`, feeds the rule, and on a
  trip sends `signal` to the descendant of the command whose name is `target` (the bazel CLIENT:
  it cancels the invocation and the executors drain) (question 2). It ends when the command exits,
  or when it trips, never on a timeout.
- **Wiring**: `mikemol-commit` reads the rows from a TOML policy (the `katas.toml` pattern: read at
  start, every required key named when absent); an absent policy means no guard, said once.
- Injected clock, reader and signaller make every piece testable without a store, a sleep or a signal.

## Slices

W918 the rule, W919 the reading source, W920 the watcher, W921 the policy row and the commit wiring,
W922 the reply letter (with W715's answer).
