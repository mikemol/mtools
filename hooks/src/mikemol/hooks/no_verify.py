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

⚑⚑ PARSE, DO NOT SUBSTRING-MATCH — the false-positive surface IS the design, and this hook's
sibling learned it first. `grep -n 'no-verify' file`, `echo "never --no-verify"` and a commit
message quoting the policy all CONTAIN the banned text and none of them bypass anything. A guard
whose first act is to break a working session trains its owner to disable it. So the token stream
is split with `shlex` and the flag is recognised only where git would recognise it: as an argument
to `commit` or `push`, never inside a quoted string.

⚑ ARMED, NOT ADVISORY. `NOVERIFY_HOOK_BLOCK=0` stands it down; otherwise the shared
`STRUCT_HOOK_BLOCK` governs. Advisory mode is SILENT TO THE AGENT — an unarmed hook exits 0 with no
`permissionDecision` and the harness reads that as "allow, nothing to report", so the text reaches
nobody. Two states only: armed, or absent.
"""

from __future__ import annotations

import json
import os
import shlex
import sys

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
# an indirection. Both are refused on the KEY, not on the value: `core.hooksPath=/dev/null` and
# `core.hooksPath=` and `core.hooksPath=/tmp/empty` are one move.
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


def _disarms_hooks(arg: str) -> bool:
    """Report whether this argument points `core.hooksPath` away from the repo's hooks.

    ⚑ BOTH FORMS, ONE PREDICATE. `-c core.hooksPath=X` sets it inline; `--config-env=` names
    an environment variable holding the value, which is the same bypass wearing an
    indirection. The test is on the KEY rather than the value, because `/dev/null`, the empty
    string and an empty directory are one move.

    Returns:
        True when this argument names `core.hooksPath` in either form.

    """
    return _HOOKS_PATH_KEY in arg.lower()


def findings(command: str) -> list[str]:
    """Every refusal this command earns, as reader-facing sentences.

    ⚑ RETURNS A LIST RATHER THAN A BOOL so the refusal can name WHICH shape it saw. A guard that
    says *refused* without saying what it matched is a verdict with a hidden operand, and this repo
    has measured what those cost.

    Returns:
        One sentence per bypass shape found, empty when the command is ordinary work.

    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        # ⚑ AN UNPARSEABLE COMMAND IS NOT A BYPASS. Unbalanced quotes mean the shell would refuse it
        # too; reporting a policy violation here would be a statement about the parser.
        return []

    found: list[str] = []
    for i, word in enumerate(tokens):
        if word != "git":
            continue
        rest = tokens[i + 1 :]
        # ⚑ THE CONFIG BYPASS IS REFUSED WHEREVER IT APPEARS AFTER `git`, because it precedes the
        # subcommand by construction — `git -c core.hooksPath=/dev/null commit` — so waiting to see
        # the subcommand first would look past it.
        found.extend(
            f"`{arg}` points core.hooksPath away from the repo's hooks — "
            "that disarms the gate as surely as --no-verify"
            for arg in rest
            if _disarms_hooks(arg)
        )
        sub = next((t for t in rest if not t.startswith("-")), None)
        if sub not in _GATED:
            continue
        found.extend(
            f"`git {sub} {arg}` skips the gate — mtools policy is "
            "never --no-verify (operator, 2026-09-07)"
            for arg in rest
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
