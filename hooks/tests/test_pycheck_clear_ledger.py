# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-pycheck --clear-ledger ROOT`: `--clear` over every file the ledger names.

W1110 (gabion:W1051 ran `--clear` over ~700 files from a scratch wrapper). ⚑ THE ALL-ADMITTED RUN
IS THE POSITIVE CONTROL: with every file admitted the exit is 0, so a 1 or a 3 is a file's doing.
The ledger reader and the per-file clear are injected; no ruff runs and nothing is written.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import pycheck_clear, pycheck_cli

if TYPE_CHECKING:
    import pytest

_ADMITTED = 0
_REFUSED = pycheck_cli.EXIT_REFUSED
_NOT_RUN = 3
_ROOT = "/repo"


def _run(names: list[str] | None, answers: dict[str, int]) -> tuple[int, str, list[str]]:
    seen: list[str] = []

    def clear_one(path: Path) -> int:
        seen.append(path.name)
        return answers.get(path.name, _ADMITTED)

    out, err = io.StringIO(), io.StringIO()
    code = pycheck_clear.clear_ledger(Path(_ROOT), lambda _root: names, clear_one, out, err)
    return code, out.getvalue() + err.getvalue(), seen


def test_every_file_admitted_is_exit_zero_with_the_tally() -> None:
    """The positive control: three admitted, exit 0, and each file was visited in order."""
    code, said, seen = _run(["a.py", "b.py", "c.py"], {})
    assert code == _ADMITTED
    assert "3 ledger files: 3 admitted, 0 refused, 0 not checked" in said
    assert seen == ["a.py", "b.py", "c.py"]


def test_one_refused_file_makes_the_whole_run_refused() -> None:
    """The strictest answer wins, and the later files are still cleared."""
    code, said, seen = _run(["a.py", "b.py", "c.py"], {"b.py": _REFUSED})
    assert code == _REFUSED
    assert "2 admitted, 1 refused, 0 not checked" in said
    assert seen == ["a.py", "b.py", "c.py"]


def test_a_not_checked_file_without_a_refusal_is_exit_three_and_a_refusal_outranks_it() -> None:
    """3 alone is 3; 3 beside a 1 is 1."""
    assert _run(["a.py", "b.py"], {"a.py": _NOT_RUN})[0] == _NOT_RUN
    assert _run(["a.py", "b.py"], {"a.py": _NOT_RUN, "b.py": _REFUSED})[0] == _REFUSED


def test_an_unreadable_ledger_clears_nothing_and_is_exit_three() -> None:
    """No ledger: exit 3, the reason said, no file touched."""
    code, said, seen = _run(None, {})
    assert code == _NOT_RUN
    assert "no readable debt ledger" in said
    assert not seen


def test_an_empty_ledger_is_clean() -> None:
    """A ledger naming nothing has nothing to clear: exit 0."""
    assert _run([], {})[0] == _ADMITTED


def test_the_flag_takes_exactly_one_root(capsys: pytest.CaptureFixture[str]) -> None:
    """--clear-ledger with no root, or two, is the usage message."""
    assert pycheck_cli.main(["--clear-ledger"]) == pycheck_cli.EXIT_USAGE
    assert pycheck_cli.main(["--clear-ledger", "a", "b"]) == pycheck_cli.EXIT_USAGE
    assert "--clear-ledger ROOT" in capsys.readouterr().err
