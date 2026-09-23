# mikemol-pathsforward

This package is the one reader and writer of a paths-forward loop's state file,
`<project-root>/.claude/paths-forward.json`. The loop itself is described by the
`paths-forward-loop` skill.

Six repositories each carried their own copy of this tool. The copies drifted into four hash
byte-forms, two lock races and two hardcoded roots. This package replaces all of them. Its
contract has two parts: the console script `mikemol-paths-forward` and the `v2:` hash.

## Usage

`--state PATH` is required. There is no default root. The mirror (`.md`), the ledger
(`.ledger`) and the flock sidecar (`.flock`) all sit beside that path.

```
mikemol-paths-forward --state S                  one-line summary (the cheap default read)
mikemol-paths-forward --state S --hash           v2:<16 hex>
mikemol-paths-forward --state S --verify H       0 match/transition · 4 divergence (FILE wins)
mikemol-paths-forward --state S --payload        the scheduler payload, or exit 1 if it cannot fit
mikemol-paths-forward --state S --render         write the derived mirror
mikemol-paths-forward --state S --queue          one line per waypoint: working, ready, blocked, rest
mikemol-paths-forward --state S --check          every mechanical charter property; exit 2 on a finding
mikemol-paths-forward --state S --check-evidence --check, plus a stat of every evidence path (opt-in)
mikemol-paths-forward --state S --lock HOLDER    exit 3 if another holder took it under 30 min ago
mikemol-paths-forward --state S --unlock HOLDER
mikemol-paths-forward --state S --armed JOB_ID
mikemol-paths-forward --state S --update W7 [--status S] [--blocked-on WHO…] [--blocked-kind K]
                                            [--next T] [--evidence-append T] [--ticks-blocked N]
                                            [--title T]   one non-blank line
mikemol-paths-forward --state S --add TITLE [--next T] [--enables W…] [--touches TAG…]
mikemol-paths-forward --state S --drop W7 REASON
mikemol-paths-forward --state S --bump-blocked [--except W…]   NUDGE at 1,2,4,8 · ESCALATE at 16
mikemol-paths-forward --state S --ledger SYM OUTCOME MECHANISM NOTE [--kind K] [--evidence E]
mikemol-paths-forward --state S --show W7
mikemol-paths-forward --state S --preamble-set FILE | --preamble-clear
mikemol-paths-forward --selftest
```

Exit codes:

| code | meaning |
|---|---|
| 0 | ok |
| 1 | the payload is over budget |
| 2 | refused: an unreadable file, a failed check, a refused edit, or bad arguments |
| 3 | the lock is held by another holder |
| 4 | the hash diverged, so the file wins |

## The hash

`v2:` is sha256 over `waypoints`, serialised with `sort_keys=True`, compact separators and
`ensure_ascii=True`, truncated to 16 hex digits.

`--verify` also accepts an untagged legacy value of 12 to 64 hex digits when it is a prefix of
any of the four legacy byte-forms (D/A, D/U, C/A, C/U). Such a value is reported, and
ledgered, as a **transition**. It is never reported as a divergence.

## Writes

Every read-modify-write holds `flock` on the `.flock` sidecar. Every write goes to a temp file
that then replaces the state file, so a concurrent reader sees either the old bytes or the new
ones. A stale-lock takeover is written to the ledger.

## Development

```
uv sync
.venv/bin/python -m pytest -o faulthandler_timeout=60
.venv/bin/ruff check
.venv/bin/mypy
python3 ../mutate_runner.py .venv/bin/python pyproject.toml
```
