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
mikemol-paths-forward --state S --unlinked       `n of m live waypoints linked`, then UNLINKED W<n> TITLE per isolated one; exit 2 if none live
mikemol-paths-forward --state S --lock HOLDER    exit 3 if another holder took it under 30 min ago
mikemol-paths-forward --state S --unlock HOLDER
mikemol-paths-forward --state S --armed JOB_ID
mikemol-paths-forward --state S --update W7 [--status S] [--blocked-on WHO…] [--blocked-kind K]
                                            [--next T] [--evidence-append T] [--ticks-blocked N]
                                            [--title T]   one non-blank line
mikemol-paths-forward --state S --add TITLE [--next T] [--enables W…] [--touches TAG…]   ledgers `minted`
mikemol-paths-forward --state S --drop W7 REASON
mikemol-paths-forward --state S --bump-blocked [--except W…]   prune landed blockers, then count a tick: NUDGE at 1,2,4,8 · ESCALATE at 16
mikemol-paths-forward --state S --prune-landed [--root R]   only the prune: idempotent, no counter, safe
                                            from a hook; a foreign repo:W<n> blocker is resolved by
                                            READING R/<repo>/.claude/paths-forward.json (default
                                            ~/github), one KEPT line for each that stays
mikemol-paths-forward --state S --inbound [--root R] [--all]   W577: read-only census of peer cards
                                            blocked on THIS repo; one `UNCLAIMED <peer>:W<n> :: <title>
                                            :: <claim command>` line per row nobody claimed, `UNREADABLE
                                            <repo>: <why>` per peer queue that cannot be read; --all
                                            adds the `CLAIMED ... by ...` rows; exit 0 either way
mikemol-paths-forward --state S --ledger SYM OUTCOME MECHANISM NOTE [--kind K] [--evidence E]
mikemol-paths-forward --state S --outcomes-set ADVANCE_CSV OTHER_CSV   W533: declare the OUTCOME words
                                            tick/interrupt --ledger lines may carry (off until set;
                                            an unlisted word is refused, exit 2, naming both sets)
mikemol-paths-forward --state S --outcomes-clear               remove the field (absent, never {})
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

## The inbound census

`--inbound` answers "who is waiting on this repo, and has anyone claimed it?" without anyone
nudging. It lists the sibling directories of `--root` (default `~/github`) that hold a
`.claude/paths-forward.json`, reads each through `store.load` only (never a save, never the
peer's lock; a repo name holding a separator or `..` and a link are refused as data), and applies
the rule of nemik's `nemik-inbound` (`nemik/blocks.py: inbound`), restated in `inbound.py`:

- a peer card counts when its status is not `done`, and one of its `blocked_on` entries names
  this repo (`<repo>:W<n>`, the repo, a `<repo>-<2 hex>` session, or `<repo>: prose`);
- it is CLAIMED by a local waypoint (any status) whose `enables` cites `<peer>:W<n>` or whose
  `caused_by` is that reference, and a `<repo>:W<n>` naming a local waypoint or residue symbol is
  its own claim (a name that points at nothing is skipped, as nemik skips it);
- otherwise it is UNCLAIMED, and the printed command (`--add ... --enables <peer>:W<n>
  --caused-by <peer>:W<n>`) claims it.

`--payload` carries the same census: an `inbound:` section, right after the standing rules and
before `waypoints:`, listing each UNCLAIMED row (peer card and title) and naming each unreadable
peer. A repo with nothing to say gets a payload byte-identical to one without the feature. The
section is the last thing the budget ladder gives up: only after the done list is gone does one
more rung collapse the rows to the `inbound:` heading, and the `truncated=true dropped=` marker
says `inbound-rows`. `--payload` takes `--root` for the same scan.

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
