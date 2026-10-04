# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `cellargs`: one cell's argv becomes a typed record, or a typed refusal."""

from __future__ import annotations

import pytest

from mikemol.mutantcell import cellargs

_REQUIRED = [
    "--engine-dir",
    "eng",
    "--check",
    "chk.py",
    "--claim",
    "c1",
    "--site",
    "m.py::f",
    "--out",
    "o.json",
]
_OPTIONAL = [
    "--module",
    "a/m.py",
    "--mutant-py",
    "mut.py",
    "--mutant-pyc",
    "mut.pyc",
    "--content-path",
    "f.txt",
    "--content-textfile",
    "t.txt",
    "--peak",
    "p.peak",
]
_USAGE_EXIT = 2


def test_the_five_required_flags_parse_and_the_six_optional_ones_read_empty() -> None:
    """A minimal argv yields the five operands and the empty string for every optional one."""
    got = cellargs.parse(_REQUIRED)
    assert got == cellargs.CellArgs(
        engine_dir="eng",
        check="chk.py",
        claim="c1",
        site="m.py::f",
        out="o.json",
    )
    assert (got.module, got.mutant_py, got.mutant_pyc) == ("", "", "")
    assert (got.content_path, got.content_textfile, got.peak) == ("", "", "")


def test_every_optional_flag_lands_in_its_own_field() -> None:
    """Each of the six optional flags is read into the field of its name, none crossed."""
    got = cellargs.parse([*_REQUIRED, *_OPTIONAL])
    assert got.module == "a/m.py"
    assert got.mutant_py == "mut.py"
    assert got.mutant_pyc == "mut.pyc"
    assert got.content_path == "f.txt"
    assert got.content_textfile == "t.txt"
    assert got.peak == "p.peak"


def test_a_missing_required_flag_is_a_usage_refusal_naming_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Without `--claim` argparse exits 2 and says which flag is missing."""
    argv = [*_REQUIRED[:4], *_REQUIRED[6:]]
    with pytest.raises(SystemExit) as refused:
        cellargs.parse(argv)
    assert refused.value.code == _USAGE_EXIT
    assert "--claim" in capsys.readouterr().err


def test_an_unknown_flag_is_a_typed_refusal_not_a_silent_no_op(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A typo'd flag exits 2 naming it, instead of being ignored."""
    with pytest.raises(SystemExit) as refused:
        cellargs.parse([*_REQUIRED, "--sitee", "x"])
    assert refused.value.code == _USAGE_EXIT
    assert "--sitee" in capsys.readouterr().err
