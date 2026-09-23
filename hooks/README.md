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
