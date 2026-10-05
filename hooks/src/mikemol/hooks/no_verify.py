# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""PreToolUse(Bash) — refuse any shape that commits or pushes around the gate.

⚑⚑⚑ OPERATOR POLICY, 2026-09-07: *never `--no-verify`* in mtools. This is the layer that says no
before the command runs. It is deliberately NOT the only layer — `.githooks/post-commit` verifies
that the gate actually ran for `HEAD`'s tree and refuses to push otherwise — because the two fail
DIFFERENTLY and neither subsumes the other.

⚑⚑ THE TWO MECHANISMS, AND WHY ONE IS NOT ENOUGH. This hook reads a COMMAND STRING and can be
evaded by a spelling nobody enumerated. The post-commit witness reads the RESULT and cannot be
evaded by spelling at all: a commit whose tree the gate never verified has no witness, however it
was produced. A guard that can be out-spelled plus a guard that cannot be out-spelled is not
redundancy — it is two different questions.

⚑ REFUSED SHAPES, AND EVERY ONE IS A MEASURED BYPASS RATHER THAN A GUESS AT ONE:

    git commit --no-verify              the named flag
    git commit -n                       its short form
    git commit --no-ver                 git accepts unambiguous abbreviations
    git push --no-verify                the pre-push side of the same policy
    git -c core.hooksPath=/dev/null …   points the hook path at nothing
    git -c core.hooksPath= …            the empty form does the same
    git --config-env=core.hooksPath=X   reads the path from an env var instead
    git config core.hooksPath /tmp/x    the same move through the config subcommand
    git config --unset core.hooksPath   removing the setting disarms too

⚑ THE VALUE RULE, STATED PLAINLY. The key is tested only where git reads config: the `-c` and
`--config-env` pairs before the subcommand, and the key operand of `git config`; never inside
`-m`/`-F` text or any other option's value. A `core.hooksPath` value is admitted ONLY when its
final path component (trailing slashes ignored) is exactly `.githooks` — that is arming the gate.
Empty, `/dev/null`, any other path, `--unset` and `--unset-all` are bypasses; `--config-env` is
always refused because its value is an env var this hook cannot see.

⚑⚑ PARSE, DO NOT SUBSTRING-MATCH — the false-positive surface IS the design, and this hook's
sibling learned it first. `grep -n 'no-verify' file`, `echo "never --no-verify"` and a commit
message quoting the policy all CONTAIN the banned text and none of them bypass anything. A guard
whose first act is to break a working session trains its owner to disable it. So the command is
parsed by the shared `cmdparse` and the flag is recognised only where git would recognise it: as
an argument to `commit` or `push`, never inside a quoted string or a heredoc body.

⚑ ARMED, NOT ADVISORY. `NOVERIFY_HOOK_BLOCK=0` stands it down; otherwise the shared
`STRUCT_HOOK_BLOCK` governs. Advisory mode is SILENT TO THE AGENT — an unarmed hook exits 0 with no
`permissionDecision` and the harness reads that as "allow, nothing to report", so the text reaches
nobody. Two states only: armed, or absent.
"""

from __future__ import annotations

import json
import os
import sys

from mikemol.hooks import cmdparse

# ⚑⚑ THE FLAG SPELLINGS, AND ABBREVIATION IS WHY THIS IS NOT A SET LITERAL. `git` accepts any
# unambiguous prefix of a long option, so `--no-ver` and `--no-verif` reach the same code path as
# `--no-verify`. A membership test against three spellings would pass the fourth. The predicate is
# therefore *is this a prefix of `--no-verify` long enough to be unambiguous*, which is a property
# rather than a list — the reified-population defect this repo has measured ten times over.
#
# ⚑ THE FLOOR IS `--no-v`: shorter prefixes (`--no`, `--n`) are ambiguous against git's other
# `--no-*` options and git itself refuses them, so refusing them here would reject commands that
# were never going to run.
_LONG = "--no-verify"
_MIN_PREFIX = len("--no-v")

# ⚑ THE CONFIG KEY THAT DISARMS THE HOOKS, in the two forms that reach it. `-c` sets it inline;
# `--config-env` names an environment variable holding the value, which is the same bypass wearing
# an indirection. `--config-env` is refused on the KEY (its value is invisible); `-c` and
# `git config` are judged by VALUE: only a final component of `.githooks` is admitted.
_HOOKS_PATH_KEY = "core.hookspath"

# ⚑ THE SUBCOMMANDS THIS POLICY COVERS. `commit` is the gate; `push` is the pre-push side and the
# publication step for a public repo. Naming them rather than refusing the flag everywhere keeps
# `git notes --no-verify`-shaped future subcommands from being silently governed by a rule written
# before they existed.
_GATED = frozenset({"commit", "push"})


def _is_no_verify(arg: str) -> bool:
    """Report whether this argument is `-n` or an unambiguous `--no-verify` prefix.

    ⚑ THE PARAMETER IS `arg`, NOT `token`, BECAUSE `S105` READ `token == "-n"` AS A HARDCODED
    CREDENTIAL. The rule keys on the NAME: anything called `token` compared against a literal
    looks like a secret. Renaming is the honest fix — these are command-line arguments and
    were never tokens in that sense — where a `noqa` would have declared the checker wrong
    about a name this file chose badly.

    Returns:
        True when git would read this argument as the verify-skipping flag.

    """
    if arg == "-n":
        return True
    if not arg.startswith("--no-v"):
        return False
    return len(arg) >= _MIN_PREFIX and _LONG.startswith(arg)


_GATE_DIR = ".githooks"

# Global options that consume the NEXT argument, so it is not mistaken for the subcommand.
_VALUE_GLOBALS = frozenset({"-C", "--git-dir", "--work-tree", "--namespace", "--super-prefix"})

# `git config` options that consume the next argument (a file, a type, a default), so that
# argument is not read as the key.
_CONFIG_VALUE_OPTS = frozenset(
    {"-f", "--file", "--blob", "--type", "--default", "--comment", "--url", "--fixed-value"}
)
_CONFIG_WORDS = frozenset({"set", "unset", "get", "list", "edit"})


def _unquote(operand: str) -> str:
    """Strip the quote characters `cmdparse` leaves on a word (its shlex is not POSIX mode).

    Returns:
        The operand without surrounding single or double quotes.

    """
    return operand.strip("'\"")


def _points_at_gate(value: str) -> bool:
    """Report whether a `core.hooksPath` VALUE names the repo's own gate directory.

    ⚑ THE VALUE RULE: a value is the gate when its final path component, ignoring trailing
    slashes, is exactly `.githooks` — `.githooks`, `./.githooks`, `/abs/repo/.githooks`,
    `$PWD/.githooks`. Everything else is a bypass: the empty string, `/dev/null`, `/tmp/x`,
    `.githooks/..`, `.githooks-off`. Arming the gate points AT it, so that shape is admitted;
    pointing anywhere else disarms it.

    Returns:
        True when the value's last component is `.githooks`.

    """
    return value.rstrip("/").rsplit("/", 1)[-1] == _GATE_DIR


def _pair_disarms(pair: str) -> bool:
    """Report whether a `-c` operand sets `core.hooksPath` to anything but the gate.

    A bare key with no `=` is git's boolean-true spelling, which is no gate directory either.

    Returns:
        True when the key is `core.hooksPath` and the value is not the gate directory.

    """
    key, sep, value = pair.partition("=")
    if key.lower() != _HOOKS_PATH_KEY:
        return False
    return not (sep and _points_at_gate(value))


def _env_disarms(operand: str) -> bool:
    """Report whether a `--config-env` operand names `core.hooksPath`.

    ⚑ THE VALUE LIVES IN AN ENVIRONMENT VARIABLE this hook cannot see, so it cannot be judged
    by value and every use of the key is refused.

    Returns:
        True when the key part of `key=ENVVAR` is `core.hooksPath`.

    """
    return operand.partition("=")[0].lower() == _HOOKS_PATH_KEY


def _split_globals(rest: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Cut git's arguments into `-c` operands, `--config-env` operands and the tail.

    ⚑ GIT READS CONFIG FROM THESE TWO GLOBAL OPTIONS ONLY WHILE THEY PRECEDE THE SUBCOMMAND, so
    this walk stops at the first argument that is neither an option nor an option's value; the
    tail starts at the subcommand. Option values (`-m` text, `-F` paths) are never inspected.

    Returns:
        The `-c` operands, the `--config-env` operands, and the arguments from the subcommand on.

    """
    pairs: list[str] = []
    envs: list[str] = []
    i = 0
    while i < len(rest):
        arg = rest[i]
        if arg == "-c" and i + 1 < len(rest):
            pairs.append(_unquote(rest[i + 1]))
            i += 2
        elif arg == "--config-env" and i + 1 < len(rest):
            envs.append(_unquote(rest[i + 1]))
            i += 2
        elif arg.startswith("--config-env="):
            envs.append(_unquote(arg.partition("=")[2]))
            i += 1
        elif arg in _VALUE_GLOBALS:
            i += 2
        elif arg.startswith("-"):
            i += 1
        else:
            break
    return pairs, envs, rest[i:]


def _config_positionals(args: list[str]) -> list[str]:
    """Return the non-option operands of `git config`, minus option values and the verb word.

    Returns:
        The key and optional value, in order.

    """
    out: list[str] = []
    skip = False
    for arg in args:
        if skip:
            skip = False
        elif arg in _CONFIG_VALUE_OPTS:
            skip = True
        elif not arg.startswith("-"):
            out.append(_unquote(arg))
    return out[1:] if out and out[0] in _CONFIG_WORDS else out


def _config_disarms(args: list[str]) -> bool:
    """Report whether `git config <args>` writes `core.hooksPath` to anything but the gate.

    ⚑ `--unset`, `--unset-all` (any abbreviation) and the `unset` verb remove the setting and so
    disarm; a write is judged by its value; a lone key is a read and is admitted.

    Returns:
        True when the key operand is `core.hooksPath` and the call unsets or mis-points it.

    """
    positional = _config_positionals(args)
    if not positional or positional[0].lower() != _HOOKS_PATH_KEY:
        return False
    if args[:1] == ["unset"] or any(a.startswith("--unset") for a in args):
        return True
    return len(positional) > 1 and not _points_at_gate(positional[1])


def _config_findings(rest: list[str]) -> tuple[list[str], list[str]]:
    """Return the config-bypass sentences for one git invocation and its subcommand tail.

    ⚑ THE KEY IS TESTED ONLY WHERE GIT READS CONFIG: the `-c` / `--config-env` pairs before
    the subcommand, and the key operand of `git config`. Text inside `-m`, `-F` or any other
    option's value is data and is never inspected. Value rule: a `core.hooksPath` value is
    admitted only when its final path component is `.githooks`; empty, `/dev/null`, any other
    directory, `--unset` and `--unset-all` are bypasses; `--config-env` is always refused.

    Returns:
        The sentences, and the arguments from the subcommand on.

    """
    pairs, envs, tail = _split_globals(rest)
    found = [
        f"`-c {pair}` points core.hooksPath away from the repo's hooks — "
        "that disarms the gate as surely as --no-verify"
        for pair in pairs
        if _pair_disarms(pair)
    ]
    found.extend(
        f"`--config-env {env}` reads core.hooksPath from an env var — "
        "that disarms the gate as surely as --no-verify"
        for env in envs
        if _env_disarms(env)
    )
    if tail[:1] == ["config"] and _config_disarms(tail[1:]):
        found.append(
            "`git config` points core.hooksPath away from the repo's .githooks "
            "(or unsets it) — that disarms the gate as surely as --no-verify"
        )
    return found, tail


def findings(command: str) -> list[str]:
    """Every refusal this command earns, as reader-facing sentences.

    ⚑ RETURNS A LIST RATHER THAN A BOOL so the refusal can name WHICH shape it saw. A guard that
    says *refused* without saying what it matched is a verdict with a hidden operand, and this repo
    has measured what those cost.

    Returns:
        One sentence per bypass shape found, empty when the command is ordinary work.

    """
    # ⚑ ONE PARSER DECIDES WHAT A COMMAND IS. `cmdparse.programs` cuts heredoc bodies, splits on
    # newlines and operators, and sees through wrappers, so `rest` is exactly git's own arguments.
    # An unparseable command yields no programs: unbalanced quotes are the shell's verdict, not a
    # policy violation.
    found: list[str] = []
    for program, rest in cmdparse.programs(command):
        if program != "git":
            continue
        config_hits, tail = _config_findings(rest)
        found.extend(config_hits)
        sub = tail[0] if tail else None
        if sub not in _GATED:
            continue
        found.extend(
            f"`git {sub} {arg}` skips the gate — mtools policy is "
            "never --no-verify (operator, 2026-09-07)"
            for arg in tail[1:]
            if _is_no_verify(arg)
        )
    return found


def _command_from_stdin() -> str:
    """Return the Bash command in the harness payload, or the empty string.

    ⚑⚑ ONE HELPER RATHER THAN FIVE EARLY RETURNS IN `main`, and `PLR0911` was right to object at
    seven: a function that can exit seven ways has seven paths a reader must hold at once to know
    whether the guard ran. ⚑ EVERY FAILURE HERE COLLAPSES TO THE EMPTY STRING BECAUSE THEY ARE ONE
    FACT — *there is no command to judge* — and a malformed payload is not a bypass. `mypy` forced
    the shape too: `json.load` returns `Any`, so each field is narrowed before use rather than
    carried untyped into the predicate.

    Returns:
        The command string, or empty when there is no command to judge.

    """
    try:
        payload: object = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return ""
    if not isinstance(payload, dict):
        return ""
    tool_input: object = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    command: object = tool_input.get("command")
    return command if isinstance(command, str) else ""


def main() -> int:
    """Read the harness payload, refuse a gate bypass, stay silent otherwise.

    Returns:
        0 always — a hook decides through its payload, never through its status.

    """
    if os.environ.get("NOVERIFY_HOOK_BLOCK", os.environ.get("STRUCT_HOOK_BLOCK", "0")) != "1":
        return 0
    hits = findings(_command_from_stdin())
    if not hits:
        return 0

    reason = "\n".join(
        [
            "no-verify: this command BYPASSES the pre-commit gate.",
            *(f"  ⚑ {f}" for f in hits),
            "  the gate is the only thing that has ever caught a wrong population here,",
            "     and every commit that skipped it would have been a commit nobody checked.",
            "  if a commit genuinely cannot pass, that is WORK (fix it, or state the exemption",
            "     in the message), not grounds for going around the gate.",
            "  ⚑ post-commit ALSO verifies the gate ran for HEAD's tree and refuses to push",
            "     otherwise, so a bypass that reaches a commit still does not reach GitHub.",
        ]
    )
    decision: dict[str, dict[str, str]] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    json.dump(decision, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
