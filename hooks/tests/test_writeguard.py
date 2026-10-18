# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the write guard: a shell write into the project is refused (W1560)."""

from __future__ import annotations

import shlex
from pathlib import Path

import pytest

from mikemol.hooks import writeguard

ROOT = Path("/repo")


def _names(cmd: str, root: Path | None = ROOT, cwd: Path = ROOT) -> list[str]:
    # The tokens `writeguard` flags in a command, split as the hook splits it.
    lexer = shlex.shlex(cmd, punctuation_chars=True)
    lexer.whitespace_split = True
    return [token for token, _ in writeguard.findings(list(lexer), root, cwd)]


@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        ("sed -i s/a/b/ f.py", "sed"),
        ("sed -Ei s/a/b/ f.py", "sed"),
        ("sed -i.bak s/a/b/ f.py", "sed"),
        ("sed --in-place=.bak s/a/b/ f.py", "sed"),
        ("awk -i inplace {print} f.py", "awk"),
        ("gawk -i inplace {print} f.py", "gawk"),
    ],
)
def test_an_in_place_edit_is_refused_wherever_it_points(cmd: str, expected: str) -> None:
    """These rewrite their input file, so the location does not matter."""
    assert _names(cmd, root=None) == [expected]


@pytest.mark.parametrize(
    "cmd",
    [
        "sed -n 1p f.py",
        "sed -e s/i/x/ f.py",
        "sed --regexp-extended s/a/b/ f.py",
        "awk {print} f.py",
        "grep perl notes.txt",
        "echo tee",
    ],
)
def test_reading_commands_and_words_that_only_name_a_tool_pass(cmd: str) -> None:
    """A tool named as an argument, or run without writing in place, is not a write."""
    assert _names(cmd) == []


def test_perl_and_tee_are_refused_in_command_position_through_a_wrapper_too() -> None:
    """Behind env assignments, `env` and `timeout` they are still the command."""
    assert _names("perl x.pl", root=None) == ["perl"]
    assert _names("A=1 perl x.pl", root=None) == ["perl"]
    assert _names("timeout 5 perl x.pl", root=None) == ["perl"]
    assert _names("env A=1 tee out.txt", root=None) == ["tee"]
    assert _names("echo a | tee out.txt", root=None) == ["tee"]


@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        ("echo a > x.py", ">"),
        ("echo a >> x.py", ">>"),
        ("echo a > /repo/x.py", ">"),
        ("cat >> tests/t.py <<EOF\nhello\nEOF", ">>"),
    ],
)
def test_a_redirect_into_the_project_is_refused(cmd: str, expected: str) -> None:
    """A heredoc append is a redirect: the write lands in the tree without the edit bar."""
    assert _names(cmd) == [expected]


@pytest.mark.parametrize(
    "cmd",
    [
        "echo a > /var/tmp/x",
        "echo a > ../outside/x",
        "cmd > /dev/null",
        "cmd 2>&1",
        "cmd >&2",
    ],
)
def test_a_redirect_outside_the_project_or_to_a_stream_passes(cmd: str) -> None:
    """Scratch space, the null device and stream duplication are not writes into the tree."""
    assert _names(cmd) == []


def test_a_path_through_dot_dot_is_read_as_text_and_never_resolved() -> None:
    """`../repo/x` from inside the root names the root again; nothing is looked up on disk."""
    assert _names("echo a > ../repo/x.py") == [">"]


@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        ("cp /var/tmp/x.py /repo/x.py", "cp"),
        ("mv /var/tmp/x /repo/y", "mv"),
        ("cp -r /var/tmp/d /repo/", "cp"),
        ("install /tmp/f /repo/f", "install"),
    ],
)
def test_a_copy_into_the_project_from_outside_is_refused(cmd: str, expected: str) -> None:
    """Content that arrives from outside the tree never met the edit bar."""
    assert _names(cmd) == [expected]


@pytest.mark.parametrize(
    "cmd", ["cp /repo/a.py /repo/b.py", "mv /repo/a /repo/b", "cp /repo/a.py /var/tmp/a.py"]
)
def test_a_copy_inside_the_project_or_out_of_it_passes(cmd: str) -> None:
    """A rename within the tree or an export to scratch adds no unjudged content."""
    assert _names(cmd) == []


def test_with_no_project_root_only_the_location_free_rules_apply() -> None:
    """The guard fails open: a redirect or copy cannot be placed, so it is not a finding."""
    assert _names("echo a > x.py", root=None) == []
    assert _names("cp /tmp/x /repo/x", root=None) == []
    assert _names("sed -i s/a/b/ f", root=None) == ["sed"]
