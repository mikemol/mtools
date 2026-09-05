# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The cases for `mikemol.hooks.cmdparse` — the tokenizer every hook's verdict rests on.

⚑⚑ THE WRAPPER CASES ARE THE LOAD-BEARING ONES, AND EACH IS A MEASURED BYPASS. A scan that stops
at the first word cannot see the program behind `timeout` — and a `timeout` prefix is the ordinary
invocation shape, so a hook built on `toks[0]` is open for nearly every command a session issues.
The bypass was demonstrated live against the predecessor.

⚑ THE FALSE-POSITIVE CASES ARE THE POSITIVE CONTROL. Every wrapper case above would pass against a
`programs()` that reported EVERY token as a program; only the quoted-data cases, which require the
parse to be a real shell parse, distinguish that from a working one.
"""

from __future__ import annotations

import pytest

from mikemol.hooks import cmdparse

# The two sides of a single delimiter — named because a bare `2` in the assertion says nothing
# about WHICH property is being pinned, and the property is that `|&` splits once rather than
# twice.
_ONE_DELIMITER_SPLITS_INTO = 2


def _progs(cmd: str) -> list[str]:
    """Return just the program names `cmd` invokes."""
    return [p for p, _args in cmdparse.programs(cmd)]


def test_a_bare_command_names_its_program() -> None:
    """The base case, without which every wrapper case below is unanchored."""
    assert _progs("grep -n foo x.py") == ["grep"]


@pytest.mark.parametrize(
    ("label", "cmd"),
    [
        ("timeout", "timeout 180 grep -c foo x.py"),
        ("env", "env grep foo x.py"),
        ("xargs", "xargs grep foo"),
        ("sudo", "sudo grep foo x.py"),
        ("a VAR= prefix", "PYTHONPATH=. grep foo x.py"),
        ("an absolute path", "/usr/bin/grep foo x.py"),
        ("a backslash-quoted name", "\\grep foo x.py"),
        ("stacked wrappers", "timeout 60 env nice grep foo x.py"),
        ("a duration operand", "timeout 30s grep foo x.py"),
        ("a uv subcommand", "uv run grep foo x.py"),
    ],
)
def test_a_wrapper_does_not_hide_the_program(label: str, cmd: str) -> None:
    """⚑ EVERY ENTRY HERE WAS A LIVE BYPASS SHAPE, not a hypothetical.

    A wrapper DELEGATES, so finding one means keep looking. `label` names the shape so a failure
    reports which wrapper stopped being transparent rather than an opaque index.
    """
    assert _progs(cmd)[-1] == "grep", label


def test_the_arguments_belong_to_the_real_program() -> None:
    """⚑ A FIRST DRAFT SKIPPED THE WRAPPER AND REPORTED `180` AS THE PROGRAM.

    Naming the right program is only half of it: a verdict is rendered over the ARGUMENTS, so a
    caller handed the wrapper's operands examines the wrong words.
    """
    assert cmdparse.programs("timeout 180 grep -c foo x.py")[0][1] == ["-c", "foo", "x.py"]


@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        ("cat x.py | grep foo", ["cat", "grep"]),
        ("make && grep foo x.py", ["make", "grep"]),
        ("make ; grep foo x.py", ["make", "grep"]),
        ("make || grep foo x.py", ["make", "grep"]),
    ],
)
def test_every_command_in_a_chain_is_seen(cmd: str, expected: list[str]) -> None:
    """Not just the first — the question is whether a tool appears ANYWHERE in command position."""
    assert _progs(cmd) == expected


def test_the_pipe_and_stderr_operator_is_one_token() -> None:
    """⚑ THE DEFECT A SECOND COPY OF `OPERATORS` CAUSED, pinned as a fact about shlex.

    A consumer's private copy lacked `|&` on the false premise that shlex reduces it to `|` + `&`.
    It does not — `punctuation_chars=True` emits it whole — so `make |& grep foo x.py` was ALLOWED
    while `make | grep foo` was denied. The package removes the second copy; this case keeps the
    shlex behaviour that copy was wrong about, which outlives the arrangement of the callers.
    """
    assert cmdparse.tokenize("make |& grep foo") == ["make", "|&", "grep", "foo"]


def test_the_pipe_and_stderr_operator_does_not_hide_the_program() -> None:
    """The same defect at the level a hook actually consults."""
    assert _progs("make |& grep foo x.py") == ["make", "grep"]


def test_the_pipe_and_stderr_operator_delimits_exactly_once() -> None:
    """⚑ ONE DELIMITER, NOT TWO — no spurious empty command between them."""
    got = cmdparse.commands("make |& grep foo x.py")
    assert len(got) == _ONE_DELIMITER_SPLITS_INTO


@pytest.mark.parametrize(
    ("label", "cmd"),
    [
        ("a quoted pipe", "grep -nE 'foo|bar' notes.md"),
        ("a quoted semicolon", "awk '{print; n++}' data.tsv"),
        ("a quoted ampersand", "grep 'a && b' notes.md"),
    ],
)
def test_a_quoted_operator_is_data_and_not_a_delimiter(label: str, cmd: str) -> None:
    """⚑ THE POSITIVE CONTROL FOR THE WHOLE SPLITTER.

    Every chaining case above would pass against a naive `cmd.split()` over the operator
    characters; only these require a real shell parse. Without them the suite cannot tell a
    tokenizer from a string split — and a hook built on the latter refuses a search PATTERN as a
    shell composition, which is a false refusal of a legitimate command.
    """
    assert len(cmdparse.commands(cmd)) == 1, label


def test_an_unparseable_command_yields_nothing_rather_than_raising() -> None:
    """⚑ AN UNBALANCED QUOTE IS BASH'S VERDICT, NOT OURS.

    A hook that raises here breaks the session on a command the shell would have rejected anyway —
    trading a refusal the author can read for a traceback they cannot.
    """
    assert cmdparse.programs("echo 'unterminated") == []


def test_an_empty_command_yields_no_programs() -> None:
    """The degenerate input, asserted rather than assumed."""
    assert cmdparse.programs("") == []


def test_a_command_that_is_only_a_wrapper_names_no_program() -> None:
    """⚑ THE SKIP MUST NOT RUN OFF THE END AND INVENT ONE.

    `timeout` alone wraps nothing; reporting a program here would mean the loop had fabricated one
    out of the wrapper's own operands.
    """
    assert cmdparse.programs("timeout 60") == []


@pytest.mark.parametrize(
    ("label", "cmd"),
    [
        # ⚑ MEASURED BYPASSES — each reported the FLAG'S ARGUMENT as the program before the fix.
        ("env -u takes a var name", "env -u LD_PRELOAD grep -n foo x.py"),
        ("sudo -u takes a user", "sudo -u nobody grep -n foo x.py"),
        ("timeout -s takes a signal", "timeout -s KILL 5 grep -n foo x.py"),
        ("env -C takes a directory", "env -C /tmp grep -n foo x.py"),
        # ⚑⚑ NON-NUMERIC ARGS FOR nice/xargs ON PURPOSE. With `nice -n 10` and `xargs -n 1` the
        # parser passes ACCIDENTALLY: `_is_operand` eats a numeric token, so the case would go
        # green against a parser that models no flag arguments at all. A test that encodes an
        # accident as an assertion is worse than no test — these use argument shapes that only
        # the flag-argument model can consume.
        ("xargs -d takes a delimiter", "xargs -d , grep foo x.py"),
        ("xargs -I takes a replace-str", "xargs -I {} grep foo x.py"),
        ("ionice -c takes a class", "ionice -c best-effort grep foo x.py"),
        ("stdbuf -o takes a mode", "stdbuf -o L grep foo x.py"),
        ("watch -d takes an option word", "watch -n cumulative grep foo x.py"),
        # long form, separated
        ("--signal separated", "timeout --signal KILL 5 grep foo x.py"),
        ("--user separated", "sudo --user nobody grep foo x.py"),
    ],
)
def test_a_wrapper_flag_argument_does_not_become_the_program(label: str, cmd: str) -> None:
    """⚑ THE SAME CLASS AS THE WRAPPER BYPASS, ONE FLAG-SHAPE DEEPER.

    A wrapper flag that takes a SEPARATE argument hid the program behind it: the flag was
    skipped correctly and its argument was then read as a program, so `programs()` reported
    `LD_PRELOAD` / `nobody` / `KILL` / `tmp` and the real command was never seen. A hook
    gating on `programs()` was open for every one of these shapes.

    `_is_operand` is deliberately NOT widened to cover them: a flag's argument can be any
    string, which is value-shaped and would defeat its conservative "cannot name a program"
    test, reopening the wrapper bypass to buy this one. The arg-taking flags are enumerable
    per wrapper; the strings they carry are not.
    """
    assert _progs(cmd)[-1] == "grep", label


@pytest.mark.parametrize(
    ("label", "cmd"),
    [
        ("short glued", "env -C/tmp grep -n foo x.py"),
        ("long attached", "env --chdir=/tmp grep -n foo x.py"),
        ("glued signal", "timeout -sKILL 5 grep -n foo x.py"),
    ],
)
def test_an_attached_flag_value_is_not_consumed_twice(label: str, cmd: str) -> None:
    """⚑ THE OVER-CONSUMPTION HALF, which the separated-form fix would otherwise cause.

    `-C/tmp` and `--chdir=/tmp` carry their value in the SAME token. If the parser consumed a
    following word for these too it would swallow the real program — turning a bypass into a
    blindness. Only the separated form may consume the next word, and these cases pin that.
    """
    assert _progs(cmd)[-1] == "grep", label


def test_a_flag_argument_at_the_end_does_not_overrun() -> None:
    """A trailing arg-taking flag with nothing after it must not index past the words.

    `env -u` with no argument and no command is malformed shell, but a parser that assumes a
    following word exists raises IndexError inside a PreToolUse hook — which fails the turn on
    a command the user merely mistyped.
    """
    assert _progs("env -u") == []
