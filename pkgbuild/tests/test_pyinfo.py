# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `pyinfo`: it names the interpreter that runs it."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.pkgbuild import pyinfo

if TYPE_CHECKING:
    import pytest


def test_pyinfo_prints_sys_executable_and_the_version_number(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Output is exactly the `executable:` and `version:` lines, paperkit's spelling."""
    assert pyinfo.main() == 0
    expected = f"executable: {sys.executable!r}\nversion: {sys.version.split()[0]}\n"
    assert capsys.readouterr().out == expected
