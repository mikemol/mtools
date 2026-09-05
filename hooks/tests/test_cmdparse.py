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
