# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `pyc`: a planted .py becomes an UNCHECKED_HASH .pyc that loads and runs."""

from __future__ import annotations

import importlib.util
import py_compile
from typing import TYPE_CHECKING

import pytest

from mikemol.pkgbuild import pyc

if TYPE_CHECKING:
    from pathlib import Path

_FLAGS_OFFSET = 4
_FLAGS_END = 8
_UNCHECKED_HASH_FLAGS = 0b01  # PEP 552: hash-based, check_source bit clear


def _compile(tmp_path: Path, source: str) -> Path:
    """Plant `source` as a module and compile it with `pyc.main`.

    Returns:
        The path of the .pyc.

    """
    src = tmp_path / "planted.py"
    src.write_text(source, encoding="utf-8")
    out = tmp_path / "planted.pyc"
    assert pyc.main([str(src), str(out)]) == 0
    return out


def test_compiled_pyc_loads_and_runs_the_planted_source(tmp_path: Path) -> None:
    """The .pyc, loaded as a sourceless module, runs the code the source held."""
    witness = tmp_path / "ran.txt"
    out = _compile(
        tmp_path,
        f"import pathlib\npathlib.Path({str(witness)!r}).write_text('ran', encoding='utf-8')\n",
    )
    spec = importlib.util.spec_from_file_location("planted_from_pyc", out)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(importlib.util.module_from_spec(spec))
    assert witness.read_text(encoding="utf-8") == "ran"


def test_pyc_is_unchecked_hash_so_the_runtime_never_rechecks_the_source(tmp_path: Path) -> None:
    """The header flags say hash-based with check_source clear (PEP 552 UNCHECKED_HASH)."""
    header = _compile(tmp_path, "X = 1\n").read_bytes()
    flags = int.from_bytes(header[_FLAGS_OFFSET:_FLAGS_END], "little")
    assert flags == _UNCHECKED_HASH_FLAGS


def test_pyc_is_byte_deterministic_across_a_source_mtime_change(tmp_path: Path) -> None:
    """Same content, different mtime, same bytes: the artifact records a hash, not a time."""
    first = _compile(tmp_path, "X = 1\n").read_bytes()
    (tmp_path / "planted.py").touch()
    second = _compile(tmp_path, "X = 1\n").read_bytes()
    assert first == second


def test_pyc_refuses_a_source_that_does_not_compile(tmp_path: Path) -> None:
    """A syntax error raises instead of writing a half-artifact."""
    src = tmp_path / "broken.py"
    src.write_text("def (:\n", encoding="utf-8")
    out = tmp_path / "broken.pyc"
    with pytest.raises(py_compile.PyCompileError):
        pyc.main([str(src), str(out)])
    assert not out.exists()
