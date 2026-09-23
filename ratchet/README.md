<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-ratchet

This is a ratchet that only lets debt go down. It stores a baseline as a **set** of keys, one per
file and rule (`path:rule`). It runs a ruff census with preview rules over a distribution and
compares the result with `ratchet-preview.txt`. It refuses any key that is not in the baseline.
With `--write`, it lowers the baseline when debt has been paid down. It never raises the baseline.
There are no runtime dependencies.

```console
$ RUFF_BIN=ratchet/.venv/bin/ruff mikemol-ratchet dist/
baseline EMPTY: 0 key(s), unchanged

$ cp <an unlinted script> dist/src/mikemol/ratchet/scratch_new.py
$ RUFF_BIN=ratchet/.venv/bin/ruff mikemol-ratchet dist/        # exit 1
4 new key(s) REFUSED:
  + src/mikemol/ratchet/scratch_new.py:line-too-long
  + src/mikemol/ratchet/scratch_new.py:literal-membership
  + src/mikemol/ratchet/scratch_new.py:magic-value-comparison
  + src/mikemol/ratchet/scratch_new.py:missing-copyright-notice
```

These runs are real, against a scratch copy of this distribution. The census runs
`<dist>/.venv/bin/ruff` unless `RUFF_BIN` names another binary. The build sets `RUFF_BIN` so that
the census never reaches a developer venv (`census.py`, `pyproject.toml`).

## Usage

```text
mikemol-ratchet DIST                     report only (the cheap default)
mikemol-ratchet DIST --init-absent       create an EMPTY baseline where none exists
mikemol-ratchet DIST --write             lower the baseline after a paydown
mikemol-ratchet DIST --key-schema S      key grammar: ruff (default) or a substrate:* schema
mikemol-ratchet remap DIST FILE... [--rev REV] [--write]
```

`remap` is a separate subcommand. It guards JSON baselines against a git revision, using
`git show --end-of-options <rev>:<file>`. It shares neither ruff nor the census baseline, so it is
not a flag on the census (`cli.py`, `remap.py`).

## Adopting

Install from git by subdirectory, pinned to a sha. See the repo-root [INSTALL.md](../INSTALL.md):

```toml
"mikemol-ratchet @ git+https://github.com/mikemol/mtools.git@<sha>#subdirectory=ratchet"
```

Then run `mikemol-ratchet <dist> --init-absent` once. Commit the empty `ratchet-preview.txt` it
creates, and let your gate run the report mode.

## Why it is built this way

- **The baseline is a set, not a count.** A count-based ratchet can be fooled by substitution: pay
  one key down, add another, and the count stays the same. ⚑ The origin measured this as
  "six-vs-six different sets". Under set membership, the added key is refused. The test
  `test_a_substitution_at_constant_size_is_refused` checks this (`core.py`).
- **A move is neither paydown nor growth.** A key that moves to another place is still debt, and
  the total has not grown. Each of the three outcomes means something different to a reader
  (`core.py`).
- **A baseline has four states, carrying two independent properties.** The states are OK, EMPTY,
  ABSENT and UNREAD. One property is `is_defect`: the gate cannot be trusted. The other is
  `deserves_mark`: a reader should look. **ABSENT is the dangerous state.** With no baseline file,
  the gate reads green while asserting nothing. **EMPTY is the strictest state:** every key counts
  as new. ⚑ The origin had three separate readers that each collapsed the states into
  `!= "ok"` and reported strictness as debt (`state.py`).
- **The first baseline is created only on request.** A baseline that created itself on the first
  run would accept whatever debt happened to be present, and nobody would have chosen that set.
  `--init-absent` makes the choice explicit (`cli.py`).
- **The write switch is an argument, not an environment variable.** An ambient switch that arms a
  write can make a write silently not happen. ⚑ Under a build system, a cached write is a skipped
  write (`core.py`).
- **The default mode only reads.** ⚑ In a sibling repo, `--list` ran every witness and hit a
  two-minute timeout. Here, the bare invocation only reports (`cli.py`).

Requirements: Python ≥ 3.13 and a ruff binary (`<dist>/.venv/bin/ruff`, or `RUFF_BIN`).
