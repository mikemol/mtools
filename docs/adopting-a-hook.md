<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# Adopting a mikemol-hooks hook in another repo

This page is about the two context hooks, `mikemol-hook-inbound-asks` and `mikemol-hook-nemik-check`. They
are not `PreToolUse` gates. They run at `SessionStart` and `UserPromptSubmit`, never refuse, and hand the
model text as `additionalContext`. The gating hooks (`mikemol-hook-structural-query` and the rest) are
wired the same way but take an arming variable; see [hooks/README.md](../hooks/README.md).

Three shapes have been considered. One is built and measured, one is built and run from a checkout, and
one is not built.
Wherever the hook is wired, `mikemol-hook-inbound-asks --check` tells you whether its pieces are present.

## What each hook does

`mikemol-hook-inbound-asks` runs this command, with the repo's own queue file as the state path:

```console
$ mikemol-paths-forward --state .claude/paths-forward.json --inbound
```

When that prints rows, the hook hands them to the model. The rows are peer asks that wait on this repo
with no claiming waypoint.

`mikemol-hook-nemik-check` runs the fleet reader `nemik-check --root <project parent>` and hands the
model only this repo's block: its `OK` or `VIOLATES` header and the indented `Warning` and `VIOLATES`
rows. A Warning is not cosmetic.

Both hooks:

- always exit 0 and have no Stop behaviour;
- serve `SessionStart` and `UserPromptSubmit` only; any other event, and a payload that is not JSON,
  produce no output;
- keep one digest file per session, so `UserPromptSubmit` emits only when the text changed;
- say that they could not run, on stderr and in the context, rather than claim there is nothing to report.

### Known limits

- **The envelope is confirmed live at `UserPromptSubmit` in two repos and unverified at `SessionStart`.**
  The `additionalContext` shape reached a live session on a prompt; whether a `SessionStart` emission
  reaches the model has not been measured. Do not rely on a session-start row alone.
- **nemik-check is slow.** The fleet read took 12.3 s wall over 19 repos when measured. So on a prompt the
  hook skips the reader, with no spawn, when the repo's `.claude/paths-forward.json` has the same sha256 as
  at the last successful run. `SessionStart` always runs it. Another repo's queue changing can alter this
  repo's rows without this repo's file changing; such a change shows at the next `SessionStart` or the next
  change to this queue.
- **The reader must exist.** inbound-asks looks for `<project>/.venv/bin/mikemol-paths-forward`, then
  `PATH`, and gives up after 20 s. nemik-check looks for the executable named by `NEMIK_CHECK`, then
  `nemik-check` on `PATH`, then `<project parent>/nemik/.venv/bin/nemik-check`, and gives up after 60 s.

## Shape (a): a vendored wheel pinned to an mtools sha, plus the repo's own settings

This is the shape luthen-observability used for `mikemol-hook-inbound-asks` and `mikemol-hook-nemik-check`,
taking the nemik-check hook from mtools commit `03749d5` in its own commit `ec48c55`. The mtools side of
that is checked in this repository; the luthen-observability commit was reported to me and not read here.

1. Pin the wheels to one sha, as [INSTALL.md](../INSTALL.md) says. The inbound-asks hook runs
   `mikemol-paths-forward`, so the repo needs `mikemol-pathsforward` as well:

   ```console
   $ uv add "mikemol-hooks @ git+https://github.com/mikemol/mtools.git@<sha>#subdirectory=hooks"
   $ uv add "mikemol-pathsforward @ git+https://github.com/mikemol/mtools.git@<sha>#subdirectory=pathsforward"
   ```

2. Add the following to the repo's own `.claude/settings.json`. The commands are the installed console
   scripts. No arming variable is needed, because neither hook has a deny mode for a switch to select. A
   repo whose venv lacks a script gets a missing-command error in the transcript and no context.

   ```json
   {
     "hooks": {
       "SessionStart": [
         {
           "hooks": [
             {"type": "command",
              "command": "\"$CLAUDE_PROJECT_DIR/.venv/bin/mikemol-hook-inbound-asks\""},
             {"type": "command",
              "command": "\"$CLAUDE_PROJECT_DIR/.venv/bin/mikemol-hook-nemik-check\""}
           ]
         }
       ],
       "UserPromptSubmit": [
         {
           "hooks": [
             {"type": "command",
              "command": "\"$CLAUDE_PROJECT_DIR/.venv/bin/mikemol-hook-inbound-asks\""},
             {"type": "command",
              "command": "\"$CLAUDE_PROJECT_DIR/.venv/bin/mikemol-hook-nemik-check\""}
           ]
         }
       ]
     }
   }
   ```

3. Run the check from the repo root once the wiring is in place:

   ```console
   $ .venv/bin/mikemol-hook-inbound-asks --check
   ```

   It prints `OK` or `MISSING` for the reader, the queue file and the settings wiring, and exits 0 only
   when all three are `OK`. Its `MISSING` lines name the repair; see the `--check` section of
   [hooks/README.md](../hooks/README.md). It covers `mikemol-hook-inbound-asks` only. A green result is
   not proof that the model sees the context: the envelope is confirmed live only at
   `UserPromptSubmit`, so confirm by watching for the context on a real prompt.

4. Move the pin by editing every spec to one new sha. A new hook shipped in mtools does not reach the repo
   until the pin moves.

## Shape (b): one user-level entry using an MTOOLS_ROOT launcher

**Not built.** The idea is one entry in `~/.claude/settings.json` that serves every repo, with a launcher
that finds the mtools checkout through `MTOOLS_ROOT`. No such user-level wiring exists, and the open
decision about whether and how to build it is waypoint W580. Until that is decided, use shape (a) or (c)
per repo. The consumer-side launcher `hooks/adopt/tools-hook` already reads `MTOOLS_ROOT`, but it was
written for `PreToolUse` gates, and nothing has measured it under a user-level settings file.

## Shape (c): running from an mtools checkout through hooks/bin launchers

The tracked launchers in `hooks/bin/` are what this repository's own `.claude/settings.json` names. They
take their venv from `$CLAUDE_PROJECT_DIR/bazel-bin/hooks/.venv`, so they serve mtools itself. If the venv
is not built, the nemik-check launcher says so on stderr and lets the call proceed:

```console
$ bazel build //hooks:.venv
```

This is the wiring in `.claude/settings.json` here, for the two context hooks:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {"type": "command",
           "command": "\"$CLAUDE_PROJECT_DIR/hooks/bin/mikemol-hook-inbound-asks\""},
          {"type": "command",
           "command": "\"$CLAUDE_PROJECT_DIR/hooks/bin/mikemol-hook-nemik-check\""}
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {"type": "command",
           "command": "\"$CLAUDE_PROJECT_DIR/hooks/bin/mikemol-hook-inbound-asks\""},
          {"type": "command",
           "command": "\"$CLAUDE_PROJECT_DIR/hooks/bin/mikemol-hook-nemik-check\""}
        ]
      }
    ]
  }
}
```

A repo that is not mtools can run the built hooks from a checkout through `hooks/adopt/tools-hook`, which
`hooks/README.md` documents for the gating hooks. Its root comes from `MTOOLS_ROOT`, or from the real path of
the file when the adopter symlinked it, and it accepts only entry names of the form `mikemol-hook-<name>`.
Its failures are `PreToolUse` deny answers. Whether that is right for a context event has not been measured,
and the inbound-asks reader still has to be found in the adopting repo, so for the two context hooks prefer
shape (a).

## What is not built

- **The user-level route.** Shape (b), waypoint W580.
- **A `SessionStart` confirmation.** See the known limits above.
