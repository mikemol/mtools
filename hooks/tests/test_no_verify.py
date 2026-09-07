# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The no-verify hook: DENY WHEN ARMED, and NOT-DENY WHEN UNARMED.

⚑⚑⚑ TWO-ARMED THROUGHOUT, BECAUSE A ONE-ARMED TEST PASSES A BROKEN-SHUT GATE. A hook that refused
every command would satisfy every deny-arm in this file and be useless; the allow-arms are what
make the deny-arms mean something. The discipline is `cassian`'s, measured at 25/25 probes on its
own routing hook.

⚑⚑ THE FALSE-POSITIVE SURFACE IS THE DESIGN, not an afterthought. This policy's own text contains
the string it forbids — *"never --no-verify"* — so a substring matcher would refuse the commit
message announcing the policy. That is not a hypothetical: this module's own commit quotes it.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mikemol.hooks.no_verify import findings

# ⚑⚑⚑ NO `__file__.resolve()`, AND A SIBLING ARM CAUGHT ME WRITING ONE. `test_bar_fires`
# refuses a path that resolves out of the runfiles tree: under bazel the test runs from a
# symlink forest, and `resolve()` follows the link back to the DEVELOPER'S WORKING TREE — so
# the arm would read whatever is on disk rather than what was declared as an input, and pass
# in the sandbox for the wrong reason. ⚑ The unresolved parent is the runfiles path.
_DIST = Path(__file__).parent.parent
_BIN = _DIST / ".venv" / "bin" / "mikemol-hook-no-verify"

# ⚑ THE PAYLOAD IS A TYPED CONSTANT, NOT AN INLINE LITERAL. `json.dumps` over a bare dict literal
# infers `Any` under this distribution's `disallow_any_expr`, and mypy refused it at both call
# sites. Naming the type once also keeps the two end-to-end arms from drifting apart — they must
# send the SAME command for the armed/unarmed pair to mean anything at all.
_PAYLOAD: dict[str, dict[str, str]] = {
    "tool_input": {"command": "git commit --no-verify -m x"},
}

# ⚑ THE BYPASS SHAPES, EACH A MEASURED ROUTE RATHER THAN A GUESS. `git` accepts unambiguous
# abbreviations of long options, so `--no-ver` reaches the same code path as `--no-verify`; a
# membership test over three spellings would pass the fourth.
_MUST_DENY = [
    "git commit --no-verify",
    "git commit -n",
    "git commit --no-ver",
    "git commit --no-verif",
    "git push --no-verify",
    "git -c core.hooksPath=/dev/null commit -m x",
    "git -c core.hooksPath= commit -m x",
    "git --config-env=core.hooksPath=EMPTY commit -m x",
    "git commit -m 'x' --no-verify",
]

# ⚑ EVERY ONE OF THESE CONTAINS SOMETHING A NAIVE MATCHER WOULD FIRE ON, or is ordinary work the
# guard must not touch. A guard whose first act is to break a working session trains its owner to
# disable it.
_MUST_ALLOW = [
    "git commit -m 'never --no-verify'",
    "git commit -F msg.txt",
    "grep -n 'no-verify' blockers.sh",
    "echo 'policy: never --no-verify'",
    "git push origin HEAD:main",
    "git log --oneline -5",
    "git -c user.name=x commit -m y",
    "git notes --no-verify",
    "git commit -am x",
]


@pytest.mark.parametrize("command", _MUST_DENY)
def test_every_gate_bypass_shape_is_refused(command: str) -> None:
    """⚑ EACH REFUSED SHAPE IS A ROUTE AROUND THE GATE, and they are not variants of one string.

    `--no-verify` names the flag; `-n` is its short form; the abbreviations reach it because git
    accepts unambiguous prefixes; `core.hooksPath` disarms every hook at once without naming the
    flag at all. **A guard that enumerated only the flag would leave the config route open**, which
    is the same shape as a checker whose population is a hand-written list.
    """
    hits = findings(command)
    assert hits, f"{command!r} bypasses the gate and was not refused"


@pytest.mark.parametrize("command", _MUST_ALLOW)
def test_ordinary_commands_are_not_refused(command: str) -> None:
    """⚑⚑ THE ARM THAT MAKES THE OTHER ARM MEAN SOMETHING.

    A hook that denied everything would pass every deny-arm above. These commands include the
    policy's own wording quoted in a commit message, a `grep` for the flag name, and a subcommand
    this policy does not cover — **each is a shape a substring matcher refuses and git would have
    run.**
    """
    hits = findings(command)
    assert not hits, f"{command!r} is ordinary work and was refused: {hits}"


def test_an_unparseable_command_is_not_a_bypass() -> None:
    """⚑ UNBALANCED QUOTES MEAN THE SHELL WOULD REFUSE IT TOO.

    Reporting a policy violation on a string that cannot be parsed would be **a statement about the
    parser wearing the shape of a finding about the command** — the class this repo has measured
    repeatedly, arriving in a guard.
    """
    assert not findings("git commit --no-verify 'unterminated")


def test_the_installed_console_script_denies_when_armed() -> None:
    """⚑⚑⚑ THE PREDICATE AND THE ENTRY POINT ARE DIFFERENT CLAIMS.

    Every arm above tests `findings` directly. **A hook can have a correct predicate and a broken
    entry point**, and only an end-to-end arm can tell them apart — this repo shipped `no_chaining`
    with 52 warrants and no `settings.json` wiring, its own docstring saying so while the suite
    stayed green. So this arm runs what the harness actually invokes.
    """
    if not _BIN.exists():
        pytest.skip(f"console script not installed at {_BIN}")
    payload = json.dumps(_PAYLOAD)
    result = subprocess.run(
        [str(_BIN)], input=payload, capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "NOVERIFY_HOOK_BLOCK": "1"}, check=False,
    )
    assert result.returncode == 0, "a hook must exit 0 and decide via its payload"
    # ⚑ `isinstance(x, dict)` NARROWS TO `dict[Any, Any]`, NOT TO A TYPED MAPPING, so indexing it
    # is still an `Any` expression under `disallow_any_expr`. Reading the value out through a
    # `str()` boundary is the honest narrowing: the harness contract is that the field is a string,
    # and asserting on the string is what this arm actually claims.
    decision: object = json.loads(result.stdout)
    assert isinstance(decision, dict)
    out: object = decision["hookSpecificOutput"]
    assert isinstance(out, dict)
    assert str(out["permissionDecision"]) == "deny"


def test_the_installed_console_script_is_silent_when_unarmed() -> None:
    """⚑⚑ AN UNARMED HOOK MUST EMIT NO DECISION AT ALL, not an advisory.

    Measured by `linux-sources`: an unarmed hook that exits 0 with no `permissionDecision` is read
    by the harness as *allow, nothing to report*, **so any advisory text it prints reaches nobody.**
    Two states only — armed, or absent. This arm holds the hook to that rather than letting it grow
    a third state that looks like caution and behaves like silence.
    """
    if not _BIN.exists():
        pytest.skip(f"console script not installed at {_BIN}")
    payload = json.dumps(_PAYLOAD)
    result = subprocess.run(
        [str(_BIN)], input=payload, capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin"}, check=False,
    )
    assert result.returncode == 0
    assert not result.stdout.strip(), (
        "an unarmed hook must emit nothing; an advisory here would be invisible to the harness"
    )


def test_the_hook_is_wired_into_settings() -> None:
    """⚑⚑⚑ A SHIPPED HOOK NOTHING INVOKES IS THE PACKAGER NOT USING ITS OWN PACKAGE.

    This repository's named defect, measured on its own sibling: `no_chaining` carried a rubric
    section, 52 tests and 52 warrants while `settings.json` wired only `structural_query`. **Its
    module docstring said so in the first paragraph and the suite was green.** So the wiring is an
    assertion, not a convention.

    ⚑ AND THE ARMING IS INLINE IN THE COMMAND STRING, not in the `env` block alone: both peers
    measured that a session already running when `settings.json` changes never picks up the env, so
    the hooks keep exiting 0 — *detecting every violation and reporting none.*
    """
    raw: object = json.loads(
        (_DIST.parent / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    assert isinstance(raw, dict)
    hooks_cfg: object = raw["hooks"]
    assert isinstance(hooks_cfg, dict)
    pre: object = hooks_cfg["PreToolUse"]
    assert isinstance(pre, list)
    commands: list[str] = []
    for entry in pre:
        assert isinstance(entry, dict)
        inner: object = entry["hooks"]
        assert isinstance(inner, list)
        for hook in inner:
            assert isinstance(hook, dict)
            command: object = hook["command"]
            assert isinstance(command, str)
            commands.append(command)
    wired = [c for c in commands if "mikemol-hook-no-verify" in c]
    assert wired, "the no-verify hook ships but settings.json invokes it nowhere"
    assert "NOVERIFY_HOOK_BLOCK=1" in wired[0], (
        "arming must be inline in the command string; an env-block-only arming is not picked up "
        "by a session that was already running"
    )


def test_the_post_commit_verifies_the_gate_ran_before_pushing() -> None:
    """⚑⚑⚑ THE SECOND MECHANISM, AND IT FAILS DIFFERENTLY FROM THE FIRST.

    The PreToolUse hook reads a COMMAND STRING and can be evaded by a spelling nobody enumerated.
    The post-commit reads the RESULT: a commit whose tree the gate never verified has no witness,
    **however it was produced.** Neither subsumes the other, which is why the operator ruled both.

    ⚑⚑ THE WITNESS KEYS ON THE STAGED TREE BECAUSE IT MUST. `pre-commit` runs before the commit
    object exists, so there is no SHA to name; `write-tree` is what the gate actually verified and
    the commit that follows carries that same tree.

    ⚑ AND THE ABSENCE OF THE WITNESS FILE IS A DIFFERENT FACT FROM A TREE MISSING FROM IT — the
    first says the gate has never run in this clone (a statement about the ENVIRONMENT), the second
    says it ran for other commits and not this one (a statement about THIS COMMIT). Only the second
    is a bypass, and collapsing them would be this repo's standing defect one layer out.
    """
    gate = (_DIST.parent / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    post = (_DIST.parent / ".githooks" / "post-commit").read_text(encoding="utf-8")
    assert "git write-tree" in gate, "the gate must record the tree it verified"
    assert "gate-verified" in gate, "the gate must write its witness where post-commit reads it"
    assert "gate-verified" in post, "post-commit must read the gate's witness"
    assert "HEAD^{tree}" in post, "post-commit must key on HEAD's tree, matching the witness"
    # ⚑ THE TWO BRANCHES ARE DISTINGUISHED, not collapsed into one refusal.
    assert "about the environment" in post, (
        "a missing witness file must be reported as an environment fact, not as a bypass"
    )
    assert "THE GATE DID NOT RUN FOR THIS COMMIT" in post, (
        "a tree absent from a present witness is the bypass, and must say so"
    )
