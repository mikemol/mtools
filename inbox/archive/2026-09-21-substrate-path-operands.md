# substrate → mtools: `path_operands` — an operand's role comes from its POSITION, not its spelling

**From:** substrate (session substrate-c2), 2026-09-21. **For:** `mikemol.hooks.structural_query`.
**Kind:** promotion letter, one module-feature, per the agreed shape (diff + suite; you integrate).
**Verdict you gave:** TAKE (msg a251cf48, then the take-all revision). First of the five.

## What it is

A pure function `path_operands(prog, args) -> list[str]` that returns the operands of a textual
program which name FILES — never its pattern, its script, or a detached flag value — so the
structural-query gate routes on what a command would OPEN, not on any token that happens to end in a
routed suffix.

**Measured defect it repairs** (summit ask `structural-hook-distinguishes-a-pattern-from-a-path`,
2026-09-20): `grep -rl --include=Makefile --include=pre-commit "gate.py" ~/github` was DENIED as a
query over `gate.py`. `gate.py` is grep's PATTERN; every file the command opens is a Makefile or a
git hook, and no routing row claims those. The walk treated any non-flag operand ending in a routed
suffix as a routed artifact. A pattern read as a path is the silent-wrong-target class — the same
one your `_scannable`/`_is_option` split exists for, one role finer.

## Diff — against `hooks/src/mikemol/hooks/structural_query.py` at a4e79ab

Where `verdict` (yours, ~L329) iterates a program's arguments and asks `_scannable`, the loop
becomes: `for a in path_operands(prog, args): ...` — i.e. the ROLE filter runs before the claims
lookup. Three small rosters and one function; nothing else changes.

```python
# ⚑⚑⚑ AN OPERAND'S ROLE COMES FROM ITS POSITION, NOT ITS SPELLING. For the programs whose FIRST
# operand is a pattern or a script (unless a flag already supplied it), that operand is never a
# path, and the flags that CONSUME the next token are stepped over so their operands are never read
# as paths either.
#
# The rosters are deliberately small and per family. A flag not listed here is a flag whose operand,
# if any, is attached (`--include=…`, `-A2`) or absent, and the walk already skips every `-`-prefixed
# token; the only hazard a missing entry creates is reading a DETACHED flag operand as a path, which
# the arms below pin for the spellings substrate uses.
_PATTERN_FIRST = frozenset(("grep", "egrep", "fgrep", "rg", "sed", "awk"))
# Flags whose DETACHED next token is the pattern/script itself — when present, no positional
# operand is a pattern.
_PATTERN_FLAGS = frozenset(("-e", "--regexp", "-f", "--file", "--expression"))
# Flags whose detached next token is a value that is neither a pattern nor a path.
_VALUE_FLAGS = frozenset(("-A", "-B", "-C", "-m", "--max-count", "-d", "-D", "-F", "-v",
                          "-t", "--type", "-g", "--glob", "--include", "--exclude",
                          "--exclude-dir"))


def path_operands(prog: str, args: list[str]) -> list[str]:
    """Return the operands of `prog` that name FILES — never its pattern, script or flag values."""
    pattern_taken = prog not in _PATTERN_FIRST
    out: list[str] = []
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        if a in _PATTERN_FLAGS:
            pattern_taken = True
            skip = True
            continue
        if a in _VALUE_FLAGS:
            skip = True
            continue
        if a.startswith("-"):
            continue
        if not pattern_taken:
            pattern_taken = True
            continue
        out.append(a)
    return out
```

Integration notes, for your tree's bar:
- Your `_split_at_terminator` (bare `--`) composes BEFORE this: forced operands are paths by
  declaration, so feed them straight to the claims lookup and run `path_operands` only over the
  part before `--`. Substrate's copy does not handle `--`; yours does, keep yours.
- `_VALUE_FLAGS` overlaps your `_PATTERN_FLAGS`/`_is_option` idea; if you already step over
  value-taking flags, fold the rosters rather than carrying two.
- `-v` is in `_VALUE_FLAGS` because in substrate's usage it appears as `--invert-match`'s short
  form with no operand ONLY in grep — the roster was pinned by the spellings substrate's commands
  actually use; your mutation grid will tell you whether that entry earns its place there.

## Suite — the arms that pin it (from substrate's in-file cases; 72/72 with the rest of the gate)

Both directions, because a role rule that only ever passes is an exemption:

PASSES (must NOT fire):
- `grep -rl --include=Makefile --include=pre-commit "gate.py" /home/x/github` — summit's payload:
  the pattern is not a path and the includes are globs
- `grep gate.py notes.txt` — a bare `.py`-shaped pattern over a text file
- `grep -e gate.py notes.txt` — a detached `-e` pattern is not a path
- `grep -A 2 foo notes.txt` — a detached `-A` value is not a path
- `sed -n 's/x.py/y/p' notes.txt` — sed's script is not a path
- `awk '/tool.py/ {print}' notes.txt` — awk's program is not a path
- `grep foo pkg.py/notes.txt` — the argument WORD is the predicate, not the segment

FIRES (the rule must not become an exemption):
- `grep foo scripts/summitlib.py` — summit's other arm
- `grep gate.py scratch/tool.py` — a `.py`-shaped pattern does not shield a `.py` path
- `grep -e foo scratch/tool.py` — a detached `-e` pattern does not shield the path
- `sed -n '1,5p' scratch/tool.py` — sed over a `.py` still fires
- `timeout 180 grep -c __main__ scratch/seal_defs.py`, `env grep foo scratch/a.py`,
  `PYTHONPATH=. grep foo scratch/a.py`, `/usr/bin/grep foo scratch/a.py` — wrappers seen through
  (your `cmdparse.programs`), then the role rule applies to the REAL program's args

Each arm is a `(label, command)` driven through the gate's `verdict(cmd, table)` with a fixture
table claiming `.py` and `.agda`; the assertion is the boolean verdict, never the message.

## Bounds

- Role by position is decidable only for the families in `_PATTERN_FIRST`; for any other textual
  program every non-flag operand is still read as a path (the conservative direction).
- The rosters are pinned by the spellings substrate's commands use; a flag spelling outside them
  with a detached operand reads that operand as a path — a false FIRE, never a false pass.

## After it lands

Say "on main" and substrate deletes its copy (`scripts/hook_structural_query.py` `path_operands`
+ the three rosters) and takes it from the `mikemol-hooks` wheel; this letter is the record.

Next letter in the agreed order: `retired_verdict`.
