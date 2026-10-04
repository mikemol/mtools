# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One sweep cell's arguments, as a typed record rather than a loose Namespace.

Ported from paperkit's `tools/cellargs.py` (paperkit:W142), behaviour unchanged. Argument parsing
is its own concern: it decides what the cell was ASKED to do, and knows nothing about doing it.

A bare `argparse.Namespace` types every attribute `Any`, so every field read poisons every
expression derived from it. Here the parse targets a Namespace SUBCLASS that declares each
attribute's type, so the record is typed at the seam and an unknown flag is a typed refusal
(argparse exits 2 naming it) instead of an `AttributeError` at the first use: a typo'd flag that
silently does nothing would be a whole sweep's worth of wrong answers with no red anywhere.
`argparse` still owns `--help`, the error messages and the required-flag checks.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class CellArgs:
    """What one def-sweep cell was asked to do."""

    engine_dir: str
    check: str
    claim: str
    site: str
    out: str
    module: str = ""
    mutant_py: str = ""
    mutant_pyc: str = ""
    content_path: str = ""
    content_textfile: str = ""
    peak: str = ""


class _Parsed(argparse.Namespace):
    """The typed shape `argparse` fills in: one annotated attribute per flag."""

    engine_dir: str
    check: str
    claim: str
    site: str
    out: str
    module: str
    mutant_py: str
    mutant_pyc: str
    content_path: str
    content_textfile: str
    peak: str


def _parser() -> argparse.ArgumentParser:
    """Build the cell's argument parser.

    Returns:
        The parser; the five required flags and six optional ones of one cell.

    """
    ap = argparse.ArgumentParser(description="run one def-sweep cell")
    ap.add_argument("--engine-dir", required=True, help="the staged engine dir, e.g. paperkit")
    ap.add_argument("--check", required=True, help="the check script, e.g. paper/checks/claims.py")
    ap.add_argument("--claim", required=True, help="the claim key this cell evaluates")
    ap.add_argument("--site", required=True, help="the def-site label, recorded in the result")
    ap.add_argument("--out", required=True, help="where to write this cell's record")
    ap.add_argument(
        "--module",
        default="",
        help="the mutated module's .py path (empty for a file/content cell)",
    )
    ap.add_argument(
        "--mutant-py",
        default="",
        help="the mutated module SOURCE (identity for the empty-set baseline)",
    )
    ap.add_argument("--mutant-pyc", default="", help="the mutated module BYTECODE")
    ap.add_argument("--content-path", default="", help="a content cell's target file")
    ap.add_argument(
        "--content-textfile",
        default="",
        help="the substring to drop/inject, delivered as a FILE (no shell escaping)",
    )
    ap.add_argument(
        "--peak",
        default="",
        help="write this cell's in-scope memory.peak here (empty = not observing)",
    )
    return ap


def parse(argv: Sequence[str]) -> CellArgs:
    """Parse `argv` into a typed record.

    An unknown flag never reaches the record: argparse exits 2 with a message naming it.

    Returns:
        The cell's arguments; every optional flag absent from `argv` reads as the empty string.

    """
    ns = _parser().parse_args(argv, namespace=_Parsed())
    return CellArgs(
        engine_dir=ns.engine_dir,
        check=ns.check,
        claim=ns.claim,
        site=ns.site,
        out=ns.out,
        module=ns.module,
        mutant_py=ns.mutant_py,
        mutant_pyc=ns.mutant_pyc,
        content_path=ns.content_path,
        content_textfile=ns.content_textfile,
        peak=ns.peak,
    )
