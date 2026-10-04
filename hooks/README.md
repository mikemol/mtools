<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-hooks

These are Claude Code `PreToolUse` hooks. They refuse a tool call before it runs. The hooks refuse
textual queries over structured artifacts, composed shell commands, gate bypasses, shell that
shellcheck flags, and Python edits that ruff or mypy flags. Each hook reads the harness's JSON
payload on stdin and answers with a `permissionDecision` on stdout.

## Console scripts

- `mikemol-hook-structural-query` (Bash). It refuses `grep`, `cat` and similar over a file kind
  that has a structural reader. The routing comes from the edited repo's `struct-tools` skill.
- `mikemol-hook-no-chaining` (Bash). It refuses `&&`, `;`, `|` and `for`. It parses with `shlex`,
  so a quoted `|` stays inside its token.
- `mikemol-hook-no-verify` (Bash). It refuses `--no-verify`, `-n`, `core.hooksPath=` and the other
  measured ways around the pre-commit gate.
- `mikemol-hook-shellcheck` (Bash, Edit and Write). It refuses shell that shellcheck flags.
- `mikemol-hook-pycheck` (Edit and Write). It refuses a `.py` edit when ruff or mypy flags the
  result.
- `mikemol-shellcheck` is the same linter run by hand. It has no `mikemol-hook-` prefix because it
  is not a hook.

Here are two real runs of the built entries against crafted payloads. `chain.json` carries
`"tool_input": {"command": "ls -l | tail -3"}` and `noverify.json` carries
`git commit -n -m wip`. The bazel-built entries have no shebang, so the command runs them through
the venv's `python3`, the same way the launcher does:

```console
$ NOCHAIN_HOOK_BLOCK=1 .venv/bin/python3 .venv/bin/mikemol-hook-no-chaining < chain.json
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
 "permissionDecisionReason": "no-chaining: this command COMPOSES where one tool call belongs.\n
  `|`  a pipe — the tool should have the mode that produces this directly\n ..."}}

$ NOVERIFY_HOOK_BLOCK=1 .venv/bin/python3 .venv/bin/mikemol-hook-no-verify < noverify.json
{"hookSpecificOutput": {..., "permissionDecision": "deny", "permissionDecisionReason":
 "no-verify: this command BYPASSES the pre-commit gate.\n  ⚑ `git commit -n` skips the gate ..."}}
```

When a command is allowed, the hook prints nothing. The same hook given a plain `ls -l` printed
nothing and exited 0.

## Arming

Each hook reads a switch that you set inline in its command line. The switches are
`STRUCT_HOOK_BLOCK`, `NOCHAIN_HOOK_BLOCK`, `NOVERIFY_HOOK_BLOCK`, `SHELLCHECK_HOOK_BLOCK` and
`PYCHECK_HOOK_BLOCK`. This is how this repository wires one of them (`.claude/settings.json`):

```json
{"type": "command",
 "command": "NOCHAIN_HOOK_BLOCK=1 \"$CLAUDE_PROJECT_DIR/hooks/bin/mikemol-hook-no-chaining\""}
```

Put the switch on the command line so it cannot drift from the hook it arms. `no_chaining` treats
`NOCHAIN_HOOK_BLOCK=0` as a stand-down. When the switch is unset, the shared `STRUCT_HOOK_BLOCK`
governs (`no_chaining.py`).

## Inbound asks (SessionStart and UserPromptSubmit)

`mikemol-hook-inbound-asks` is the one hook here that is not a `PreToolUse` gate. It tells a session
about the peer asks that wait on its repo, without a peer's nudge. It runs
`mikemol-paths-forward --state <project>/.claude/paths-forward.json --inbound` and, when that
prints rows, hands them to the model as `additionalContext`:

```json
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext":
 "inbound: peer ask(s) wait on this repo with no claiming waypoint:\nUNCLAIMED peer:W3 :: ...\n
  to claim a row, run its --add command; to decline, send the peer a letter ..."}}
```

- **It never refuses and has no Stop behaviour.** A Stop block on an unanswered row would trap a
  session that cannot satisfy it: the ask may not be theirs, and declining is a letter, not a queue
  state a hook can read. It always exits 0.
- **Events.** `SessionStart` and `UserPromptSubmit` are served. Any other event, and a payload that
  is not JSON, produces no output.
- **Silent cases.** The project has no `.claude/paths-forward.json`, or the reader printed nothing.
- **The reader.** `<project>/.venv/bin/mikemol-paths-forward` first, then `PATH`. If neither exists,
  it exits non-zero, or it runs longer than 20 s, the hook says so in the context text and on
  stderr and does not claim there are no asks. The argv is constants plus the state path as one
  word, never through a shell.
- **No flood.** One digest file per session, `<tmp>/mikemol-inbound-asks/<session_id>`.
  `SessionStart` always emits what it finds. `UserPromptSubmit` emits only when the text differs
  from the last emission, so a failure notice is also said once per session. The cost is one reader
  run per prompt, bounded by the timeout, and one small file write per change.
- **The project** is `CLAUDE_PROJECT_DIR`, else the working directory.

To arm it, a repo owner adds the following to the repo's `.claude/settings.json`. No arming variable
is needed, because the hook has no deny mode for a switch to select; a `*_HOOK_BLOCK=1` prefix
would be decoration. The command is the installed console script, so it fails soft: a repo whose
venv lacks it gets a missing-command error in the transcript and no context.

```json
"SessionStart": [
  {"hooks": [{"type": "command",
              "command": "\"$CLAUDE_PROJECT_DIR/.venv/bin/mikemol-hook-inbound-asks\""}]}
],
"UserPromptSubmit": [
  {"hooks": [{"type": "command",
              "command": "\"$CLAUDE_PROJECT_DIR/.venv/bin/mikemol-hook-inbound-asks\""}]}
]
```

### Checking the wiring with `--check`

`mikemol-hook-inbound-asks --check` asks whether a project has everything the hook needs. It takes no
stdin payload. Run it from the project (the project is `CLAUDE_PROJECT_DIR`, else the working
directory):

```console
$ .venv/bin/mikemol-hook-inbound-asks --check
```

The `hooks/bin/mikemol-hook-inbound-asks` launcher does not forward its arguments, so it cannot run
the check. In mtools itself, run the built entry with the venv's `python3`, as the examples above do:
`CLAUDE_PROJECT_DIR=$PWD bazel-bin/hooks/.venv/bin/python3 bazel-bin/hooks/.venv/bin/mikemol-hook-inbound-asks --check`.
It prints three lines, one per piece, each starting `OK <piece>:` or `MISSING <piece>:`:

- `reader`: `mikemol-paths-forward` is in `<project>/.venv/bin` or on `PATH`, and its `--help` names
  `--inbound`. MISSING means either there is no reader (install `mikemol-pathsforward`, as
  [adopting-a-hook.md](../docs/adopting-a-hook.md) says), or the reader is too old, or its
  `--help` probe timed out or could not start (move the pin to a newer sha).
- `queue`: `<project>/.claude/paths-forward.json` exists. MISSING means the repo has no queue, so the
  hook would stay silent; create one with the reader.
- `settings`: `<project>/.claude/settings.json` names `mikemol-hook-inbound-asks` under both
  `SessionStart` and `UserPromptSubmit`. MISSING says why: the file could not be read, is not valid
  JSON, or lacks the hook for the named event or events. Add the blocks shown above.

The exit status is 0 only when all three are `OK`, 1 otherwise, and 2 for any other argument. The
only thing it runs is one bounded `<reader> --help` probe (20 s, no shell). It never denies and
writes nothing.

A green `--check` shows the pieces are present. It does not show that the model sees the context:
the envelope is confirmed live only at `UserPromptSubmit`.

## Nemik check (SessionStart and UserPromptSubmit)

`mikemol-hook-nemik-check` is the sibling of the inbound-asks hook. It runs the fleet reader
`nemik-check --root <project parent>` and hands the model only this project's rows (the repo is the
basename of `CLAUDE_PROJECT_DIR`) as `additionalContext`: the repo's `OK`/`VIOLATES` header line and
the indented `Warning`/`VIOLATES` rows beneath it, quoted verbatim, with one line saying these are
nemik's shapes, to fix them (the remedy is in each row), and that a Warning is not cosmetic.

- **It never refuses and has no Stop behaviour.** It always exits 0, like inbound-asks.
- **Events.** `SessionStart` and `UserPromptSubmit`; any other event, and a payload that is not
  JSON, produces no output.
- **Silent cases.** This repo's block has no indented rows, or the repo is absent from the output.
- **The reader.** The executable named by `NEMIK_CHECK`, else `nemik-check` on `PATH`, else
  `<project parent>/nemik/.venv/bin/nemik-check`. If none exists, it times out (60 s), or it exits
  non-zero with no block for this repo, the hook says COULD NOT RUN in the context and on stderr and
  does not claim the queue is clean. A non-zero exit that still prints this repo's block is read as
  output. The argv is constants plus the root as one word, never through a shell.
- **No flood.** One digest file per session, `<tmp>/mikemol-nemik-check/<session_id>`, with the
  same rule as inbound-asks.
- **Cost.** The reader took 12.3 s wall over 19 repos when measured, so `UserPromptSubmit` skips it
  (silent, no spawn) when the project's `.claude/paths-forward.json` has the same sha256 as at the
  last successful run, kept in `<session_id>.state` beside the emission digest. `SessionStart`
  always runs it. A missing or unreadable queue file, no session id, an unwritable temp directory
  or a failed last run means the reader runs; the skip is never taken on doubt.

To arm it, add the same two blocks as for inbound-asks to the repo's `.claude/settings.json`, naming
`mikemol-hook-nemik-check`. No arming variable is needed, because the hook has no deny mode.

## Git hooks (not harness hooks)

`mikemol-githook-pre-push`, `mikemol-githook-post-commit` and
`mikemol-githook-prepare-commit-msg` are run by git, not by the harness.
They have no `mikemol-hook-` prefix, so no `settings.json` wiring is needed. A repo installs each as
a one-line stub, for example `.githooks/post-commit`: `exec <venv>/bin/mikemol-githook-post-commit`.

`mikemol-githook-post-commit` is the shared form of substrate's post-commit. It prints an advisory
and amends the commit just made so its message carries `post-commit advisory (auto-captured)` and
the advisory beneath it. That text is the marker that substrate's `pre-push.local` checks, and
el-openglo's own post-commit writes the same one.

- **The repo's advisory** comes from `<toplevel>/.githooks/post-commit.local`, when it is
  executable. Its stdout is the advisory body, its stderr passes through, and a non-zero exit is
  recorded in the advisory. Without one, the advisory is the header line alone and the marker is
  still written.
- **Skipped, with the advisory still printed:** while a rebase, merge, cherry-pick or revert is in
  flight, and when the message already carries the marker. The amend sets `_POST_COMMIT_AMENDING`,
  so the hook it re-fires does nothing.
- **A failure is reported.** The shell version ended its amend in `|| true`. Here a failed amend, a
  missing git and a run outside a repository each write a reason to stderr and exit 1. Git ignores
  a post-commit status, so no commit is harmed.
- **It never pushes.** Auto-push is repo policy and belongs in the repo's own stub, after the
  `mikemol-githook-post-commit` call returns.

`mikemol-githook-prepare-commit-msg` is the shared form of substrate's prepare-commit-msg. Its
argv is git's own, `<message-file> [<source>]`, so the stub must pass it on:
`exec <venv>/bin/mikemol-githook-prepare-commit-msg "$@"`. It appends the pre-commit gate report
(`<git dir>/precommit-report.txt`, minus `[N/total]` progress and blank lines, indented) to the
message under `pre-commit gate report (auto-captured):` and deletes the report. A `merge` or
`squash` source, or a message that already carries the marker, only deletes the report; no report
is a quiet no-op. The shell version swallowed every failed step, and its `rm -f` consumed the report
even when the append had failed. Here a missing argument, missing git, a non-repository, an
unreadable report and an unwritable message each write a reason to stderr and exit 1, and a failed
append keeps the report. Git aborts the commit on that exit.

## Adopting

Install from git by subdirectory, pinned to a sha. See the repo-root [INSTALL.md](../INSTALL.md):

```toml
"mikemol-hooks @ git+https://github.com/mikemol/mtools.git@<sha>#subdirectory=hooks"
```

If your repo runs mtools' built hooks and does not install them, symlink `tools/hook` to
`hooks/adopt/tools-hook` and write each hook command as
`STRUCT_HOOK_BLOCK=1 tools/hook mikemol-hook-structural-query`. The launcher gets its mtools root
from `MTOOLS_ROOT` or from its own realpath. It does not guess `$HOME/github/mtools`. It accepts
only entry names of the form `mikemol-hook-<name>`. If the root is missing or the venv is not
built, it answers with an explicit deny. The one command it lets through is
`env -C <root> bazel build //hooks:.venv`, which repairs the venv (`hooks/adopt/tools-hook`).

## Why it is built this way

- **Every hook fails closed.** If a hook exits 0 with an empty stdout, the harness reads that as
  *allow*. ⚑ When linux-sources measured advisory mode, the advisory text reached nobody. So an
  armed hook that cannot check anything returns a deny that names the repair (`no_chaining.py`,
  `shellcheck.py`, `pycheck.py`). The deny cannot deadlock: `pycheck` never sees Bash, and
  `shellcheck` allows the one command that repairs it.
- **Adoption is a console script, not a symlink.** A symlinked script works out its root with
  `abspath(__file__)`, and that does not resolve the link. ⚑ In one peer repo, an adopted tool
  failed on every call with `ModuleNotFoundError` for this reason (`pyproject.toml`).
- **There is no exception list.** A category of question that no reader covers yet is a gap in
  the toolkit. The fix is to add the reader, not to carve out an exception (`structural_query.py`).
- **The hook refuses any spelling that gets around the gate.** Git accepts `--no-ver`, and
  `core.hooksPath=` works as well as `/dev/null`. `no_verify` refuses every measured spelling. The
  post-commit witness catches any spelling nobody listed (`no_verify.py`).
- **A checker has three verdicts: clean, findings and could-not-run.** A missing module also exits
  1, so `No module named` is read before the exit code (`verdict.py`).
- **The checkers are runtime dependencies.** ruff has a floor, `>=0.16.6`, and no exact pin.
  ⚑ An exact pin made `uv add mikemol-hooks` unsolvable against substrate's `ruff>=0.16.8`
  (2026-09-22). `shellcheck` is a system binary. When it is absent, the hook says so; it never
  passes silently (`pyproject.toml`).

Requirements: Python ≥ 3.13, ruff and mypy (installed as dependencies), and `shellcheck` on PATH.
