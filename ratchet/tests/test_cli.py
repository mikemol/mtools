# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the CLI: the birth move, and which invocation mutates."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.ratchet import cli
from mikemol.ratchet.core import read_baseline
from mikemol.ratchet.state import BaselineState

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _dist(tmp_path: Path, findings: frozenset[str]) -> Path:
    """Build a fake distribution whose ruff reports `findings`.

    Returns:
        The distribution root.

    """
    binroot = tmp_path / ".venv" / "bin"
    binroot.mkdir(parents=True)
    body = "".join(f'echo "{key.split(":")[0]}:1:1: {key.split(":")[1]}: msg"\n'
                   for key in sorted(findings))
    ruff = binroot / "ruff"
    ruff.write_text(f"#!/bin/sh\n{body}exit 1\n", encoding="utf-8")
    ruff.chmod(0o755)
    return tmp_path


def test_the_bare_invocation_refuses_an_absent_baseline(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The bare invocation refuses an absent baseline.

    ⚑⚑ ABSENT EXITS 1 AND NAMES THE BIRTH MOVE. A gate with no baseline reports green over
    nothing, which is indistinguishable from a gate that examined a clean tree.
    """
    assert cli.main([str(_dist(tmp_path, frozenset({"a.py:some-rule"})))]) == 1
    assert "--init-absent" in capsys.readouterr().out


def test_the_bare_invocation_does_not_mutate(tmp_path: Path) -> None:
    """The bare invocation does not mutate.

    ⚑⚑ THE CHEAP READ IS THE DEFAULT AND EXECUTION IS OPTED INTO.

    A sibling's `--list` did not list — it executed every witness and blew a timeout. The
    tell is not in the name, so the bare invocation here must leave the tree untouched.
    """
    dist = _dist(tmp_path, frozenset({"a.py:some-rule"}))
    cli.main([str(dist)])
    assert not (dist / "ratchet-preview.txt").exists()


def test_init_absent_mints_the_census(tmp_path: Path) -> None:
    """The birth move records what is there, once, because someone said so."""
    dist = _dist(tmp_path, frozenset({"a.py:r1", "b.py:r2"}))
    assert cli.main([str(dist), "--init-absent"]) == 0
    state, keys = read_baseline(dist / "ratchet-preview.txt")
    assert state is BaselineState.OK
    assert keys == frozenset({"a.py:r1", "b.py:r2"})


def test_a_second_init_absent_is_refused(tmp_path: Path) -> None:
    """A second init-absent is refused.

    ⚑ RE-MINTING WOULD LAUNDER GROWTH INTO A NEW FLOOR, which is the one thing a
    paydown-only ratchet must never permit.
    """
    dist = _dist(tmp_path, frozenset({"a.py:r1"}))
    assert cli.main([str(dist), "--init-absent"]) == 0
    assert cli.main([str(dist), "--init-absent"]) == 1


def test_growth_is_refused_through_the_cli(tmp_path: Path) -> None:
    """End to end: a new key refuses, and the refusal names it."""
    dist = _dist(tmp_path, frozenset({"a.py:r1"}))
    cli.main([str(dist), "--init-absent"])
    (dist / ".venv" / "bin" / "ruff").write_text(
        '#!/bin/sh\necho "a.py:1:1: r1: m"\necho "b.py:1:1: r2: m"\nexit 1\n', encoding="utf-8")
    (dist / ".venv" / "bin" / "ruff").chmod(0o755)
    assert cli.main([str(dist)]) == 1
