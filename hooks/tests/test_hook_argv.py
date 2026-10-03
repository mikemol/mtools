# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the hook argv contract: any argument refused by name, one declared mode (W526).

el-openglo measured (el-openglo:W99) `mikemol-hook-structural-query --help` exiting 0 with empty
stdout. These arms run each console-script entry with an argument and a stdin that fails the
test if it is read, so a hook that reaches its payload before refusing is caught.
"""

from __future__ import annotations

import io
import sys
from typing import TYPE_CHECKING, override

from mikemol.hooks import entry, hook_argv, routing_table

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest

_REFUSED = hook_argv.EXIT_REFUSED
_ENTRIES: dict[str, Callable[[], int]] = {
    "mikemol-hook-structural-query": entry.structural_query_main,
    "mikemol-hook-no-chaining": entry.no_chaining_main,
    "mikemol-hook-no-verify": entry.no_verify_main,
    "mikemol-hook-shellcheck": entry.shellcheck_main,
    "mikemol-hook-pycheck": entry.pycheck_main,
}


class _Untouchable(io.StringIO):
    """A stdin whose read is a test failure: a refusal must come before the payload."""

    @override
    def read(self, size: int | None = -1) -> str:
        msg = f"stdin was read ({size}) before argv was refused"
        raise AssertionError(msg)


def test_no_arguments_runs_the_hook() -> None:
    """With no arguments the contract steps aside: the hook reads its payload as before."""
    assert hook_argv.mode("h", ["h"]) is None


def test_an_unknown_flag_is_refused_by_name(capsys: pytest.CaptureFixture[str]) -> None:
    """`--help` is refused with exit 2, naming the argument and saying a hook reads stdin."""
    assert hook_argv.mode("h", ["h", "--help"]) == _REFUSED
    err = capsys.readouterr().err
    assert "'--help'" in err
    assert "takes no arguments" in err


def test_a_bare_word_is_refused_too() -> None:
    """A positional is refused: a hook has no operands, so a word can only be a mistake."""
    assert hook_argv.mode("h", ["h", "payload.json"]) == _REFUSED


def test_a_declared_mode_is_returned_and_named_in_refusals(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A declared mode alone is returned; with anything else it is refused, the modes offered."""
    assert hook_argv.mode("h", ["h", "--routes"], ("--routes",)) == "--routes"
    assert hook_argv.mode("h", ["h", "--routes", "x"], ("--routes",)) == _REFUSED
    assert "its modes are --routes" in capsys.readouterr().err


def test_every_hook_entry_refuses_an_argument_before_reading_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each `mikemol-hook-*` entry returns 2 on `--help` and never touches stdin.

    ⚑⚑ THE DEFECT el-openglo:W99 MEASURED: each hook read an empty stdin, allowed, and exited 0.
    """
    monkeypatch.setattr(sys, "stdin", _Untouchable())
    codes = {}
    for prog, run in _ENTRIES.items():
        monkeypatch.setattr(sys, "argv", [prog, "--help"])
        codes[prog] = run()
    assert codes == dict.fromkeys(_ENTRIES, _REFUSED)


def test_routes_prints_the_table_the_hook_reads(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--routes` prints `artifact<TAB>tool` rows from `routing_table.routes`, exit 0."""

    def rows() -> list[tuple[str, str]]:
        return [(".md", "mdstruct"), (".py", "pycodemod")]

    monkeypatch.setattr(routing_table, "routes", rows)
    monkeypatch.setattr(sys, "stdin", _Untouchable())
    monkeypatch.setattr(sys, "argv", ["mikemol-hook-structural-query", "--routes"])
    assert entry.structural_query_main() == 0
    assert capsys.readouterr().out == ".md\tmdstruct\n.py\tpycodemod\n"


def test_routes_with_no_table_says_so_and_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no table, `--routes` exits 1 and says where it looked: never a blank pass."""

    def rows() -> list[tuple[str, str]]:
        return []

    monkeypatch.setattr(routing_table, "routes", rows)
    monkeypatch.setattr(sys, "argv", ["mikemol-hook-structural-query", "--routes"])
    assert entry.structural_query_main() == 1
    assert "no routing table found" in capsys.readouterr().err
