# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the per-test duration ceiling in the py_test entry point (mtools:W935).

⚑ THE FAST MODULE IS THE POSITIVE CONTROL: without it, a run that fails over the ceiling cannot be
told from an entry point that fails everything. Each arm runs pytest on a module written into
tmp_path, with a ceiling small enough that a short sleep crosses it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest_main

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_CEILING = 0.05
_SLEEP = 0.2
_SMALL_TIMEOUT_S = 60
_MEDIUM_CEILING_S = 75.0
_PASSED = 0
_FAILED = 1
_ARGS = ["-q", "-p", "no:cacheprovider"]
_SLOW = f"import time\n\n\ndef test_slow():\n    time.sleep({_SLEEP})\n"
_FAST = "def test_fast():\n    assert True\n"
_RED = "def test_red():\n    assert False\n"


def _module(tmp_path: Path, body: str) -> str:
    """Write a one-test module under a name no other arm uses, and name it for pytest.

    ⚑ ONE BASENAME PER ARM: the nested runs share this process's module table, and a second
    `test_probe` is "import file mismatch" at collection, which exits 2 and reads as the code under
    test.

    Returns:
        the module's path as a string.

    """
    path = tmp_path / f"test_{tmp_path.name}.py"
    path.write_text(body, encoding="utf-8")
    return str(path)


def test_a_fast_green_module_passes(tmp_path: Path) -> None:
    """The positive control: under the ceiling the exit code is pytest's own."""
    assert pytest_main.main([*_ARGS, _module(tmp_path, _FAST)], _CEILING) == _PASSED


def test_a_green_module_with_a_slow_test_fails_and_names_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A passing test over the ceiling fails the target, with its node id on stderr."""
    code = pytest_main.main([*_ARGS, _module(tmp_path, _SLOW)], _CEILING)
    assert code == _FAILED
    assert "::test_slow" in capsys.readouterr().err


def test_a_red_module_keeps_its_own_exit_code(tmp_path: Path) -> None:
    """A real failure is reported as pytest reports it, not folded into the ceiling's."""
    assert pytest_main.main([*_ARGS, _module(tmp_path, _RED)], _CEILING) == _FAILED


def test_the_default_ceiling_is_a_quarter_of_a_small_targets_timeout_at_most() -> None:
    """15s against the 60s a `size = "small"` target allows: room for four such tests, not one."""
    assert pytest_main.CEILING_S * pytest_main.FRACTION <= _SMALL_TIMEOUT_S


def test_the_ceiling_follows_the_targets_timeout_when_bazel_names_it() -> None:
    """A medium target (300s) gets 75s; no timeout, a non-number or a non-positive one gets 15s."""
    env = pytest_main.TIMEOUT_ENV
    assert pytest_main.ceiling_from({env: "300"}) == _MEDIUM_CEILING_S
    assert pytest_main.ceiling_from({env: "60"}) == pytest_main.CEILING_S
    assert pytest_main.ceiling_from({}) == pytest_main.CEILING_S
    assert pytest_main.ceiling_from({env: "soon"}) == pytest_main.CEILING_S
    assert pytest_main.ceiling_from({env: "0"}) == pytest_main.CEILING_S
