# linux-sources → mtools: `mikemol-paths-forward --update ... --next ""` writes `""`, not `null`

**What I hit, four times in one session (2026-09-26):** closing a waypoint via

```
mikemol-paths-forward --state ... --update W<n> --status 'done' --next "" ...
```

writes `"next_bounded_step": ""` into the state file. linux-sources' own reconcile check
(`checks/pf_reconcile.py`) requires `next_bounded_step` to be `null` on a `done` waypoint, and
fails otherwise:

```
FAIL  W64 is done but next_bounded_step is not null (parsed value)
```

Occurrences: **W64, W69, W70, W71** — each time I closed a waypoint and passed `--next ""` to
clear the field, and each time I had to patch the JSON directly afterward:

```python
w["next_bounded_step"] = None
```

**Downstream effect, also hit twice:** a waypoint left with the stale (non-null) field caused
`mikemol-paths-forward --check` to separately flag a dependent waypoint as blocked-on-a-done-item
(`W65 is blocked on W64, which is done` / `W72 is blocked on W71, which is done`), because
whatever check drives that comparison apparently reads the same field.

**Ask:** either `--update ... --status done --next ""` should map the empty string to `null`
itself, or `--check`/`--verify` should treat `""` as equivalent to `null` for a done waypoint's
`next_bounded_step`. Your call which side owns the fix — I don't know which is intended
behaviour vs. an oversight. Argument order in each case was `--status 'done' --blocked-on
--next "" --evidence-append "..."`, if that narrows it down (the bare `--blocked-on` with no
following value, to clear it, worked fine every time).

**Bound:** measured against this one state file, four occurrences, all the same shape. I have
not checked whether `--next ""` on a non-done waypoint (to clear it while leaving it `ready`)
has the same issue, since I never did that.
