# W881: the inbound-asks hook at user level (operator's W580 ruling: wire once)

Not applied by the agent: `~/.claude/settings.json` is the operator's. This is the drafted grant.

## What changed in the tree

`hooks/bin/mikemol-hook-inbound-asks` resolves the built venv under `MTOOLS_ROOT` when it is set,
else under `CLAUDE_PROJECT_DIR` as before. The module still serves `CLAUDE_PROJECT_DIR` (the repo the
session is in), so one launcher covers every repo; a repo with no `.claude/paths-forward.json` stays
silent. It never denies: an unbuilt venv, or neither variable set, is a stderr line and exit 0.
Witnesses: `hooks/tests/test_inbound_launcher_root.py` (5 tests).

## The lines for the operator to merge into `~/.claude/settings.json`

Add one entry to each of the `SessionStart` and `UserPromptSubmit` arrays under `hooks` (create the
array if absent; keep any entries already there):

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "MTOOLS_ROOT=/home/mikemol/github/mtools /home/mikemol/github/mtools/hooks/bin/mikemol-hook-inbound-asks"
    }
  ]
}
```

## After applying

In a repo with a queue, `MTOOLS_ROOT=/home/mikemol/github/mtools CLAUDE_PROJECT_DIR=$PWD
/home/mikemol/github/mtools/hooks/bin/mikemol-hook-inbound-asks --check` prints OK/MISSING per
piece. Its settings piece reads the repo's own settings.json, so it reports MISSING there even when
the user-level wiring is live; the user-level file is the witness for that piece. W622 waits on this.
