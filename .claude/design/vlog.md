# mikemol-vlog: structured output to VictoriaLogs (W1165 to W1182)

Asked by github-8f for the operator: tool output that is already JSON should reach VictoriaLogs as
fields, not as a flattened logger string. Nothing in mtools or luthen did this for stdin or for a
producer's exit status; luthen's `checks/log_ship.py` tails files by offset and mtools'
`hooks/refusal_log.py` sends one event, so both were read first and neither was rewritten.

## The command (hooks dist, console script `mikemol-vlog`)

    tool | mikemol-vlog --stream tool=commit --stream repo=mtools
    mikemol-vlog --stream tool=katas -- mikemol-katas tick end --note N     (exit status is the tool's)
    mikemol-vlog --stream tool=app --from-file app.log --state app.state    (once, from an offset)
    mikemol-vlog --drain                                                    (send what is spooled, now)
    mikemol-commit REPO --waypoint W --subject S --ship [PATH ...]          (its verdicts, as fields)

- A line that is a JSON object keeps its fields; `message` becomes `_msg`, the first of `_time`,
  `time`, `timestamp`, `ts` becomes `_time` (RFC3339 microseconds, never an integer; `--unit` for
  epoch numbers). A line that is not JSON, or is JSON but not an object, becomes a record whose
  message is the line and which carries `parse_failure`. Nothing is dropped; an over-long line is
  cut and says `truncated`.
- The caller only appends to a spool (one file per sorted set of stream keys) and starts a detached
  drainer; it never waits for the endpoint. No wall-clock timeout exists in the path. A stalled
  drainer is ended by a no-progress count over later runs (W1180), not a timer.
- The endpoint is found by NAME: `~/.config/mikemol/vlog.toml` holds `service`, `resolver` (an argv
  list with `{name}`), `spool_dir`, `max_lines`, `max_bytes`; flags override. With no service the
  lines are spooled and kept. No address is written in any source or card.
- The exit status is the producer's in the wrapper form (a pipe cannot see it); the stdin and file
  forms return 0 once the lines are spooled, 2 for a usage error.

## What was measured

- Live smoke (2026-10-14), file form from the rebuilt venv: the JSON line kept its fields and a
  normalized `_time`; the plain line became `parse_failure=not-json`.
- Live smoke, wrapper form: `mikemol-vlog ... -- mikemol-katas` with no subcommand returned the
  katas status 2 unchanged (W1182). The katas dist cannot import hooks, so the wrapper form is the
  way katas ticks are shipped; its lines that are not JSON arrive flagged, which is true of them.

## Open

- W1170: offer luthen the library so its `log_ship` becomes a caller (luthen mints its own card).
- The stack form of `mikemol-commit` does not take `--ship` yet.
