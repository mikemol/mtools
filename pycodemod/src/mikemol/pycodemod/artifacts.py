# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Which tools read a failure-bearing build artifact: literals against a caller's vocabulary.

Cleanroomed from substrate's `scratch/_pycodemod_census.py` (`build_artifact_readers`,
`_artifact_readers`; W612). A tool that reads failure records produces commit-blockers by
construction, so the census classifies each file once: FAILURE (reads an artifact that can hold a
failure), SUCCESS (reads only artifacts a failure cannot appear in) or BOTH. A file reading no
artifact has no row; there is no third verdict.

⚑⚑ THE VOCABULARY IS THE CALLER'S, BOTH TUPLES, REQUIRED. The origin hard-coded the Agda build
vocabulary as module constants. An empty vocabulary measures nothing and must not read as a clean
census, so an empty `failure` or `success` is refused with `ValueError`.

⚑⚑ PROSE IS NOT A READ. The CST drops a docstring (the sole expression of an `Expr` statement);
comments are not tokens of the tree. Without this a tool that merely discusses an artifact looks
like one that consumes it.

⚑⚑ FAILURE IS MATCHED FIRST AND SUBTRACTED BEFORE THE SUCCESS PASS. When one token is a prefix of
another (`.agdai` of `.agdai.log`) a substring test makes every failure reader a success reader.
A literal that matched any failure token is excluded from the success pass.

What moved and what did not:

⚑ BOTH SIDES MATCH EXACTLY. The origin matched failure case-sensitively and success with `.lower()`
on both sides, so one token matched differently by side. Both are exact now.

⚑ AN UNREAD FILE IS REPORTED. The origin skipped an unreadable or unparseable file with `continue`;
it is a `Skip` here. libcst is required (see core), so the origin's `cst is None` skip is gone.

⚑ A LITERAL IS READ ONLY IF SHORTER THAN `MAX_LITERAL` AND SINGLE-LINE, as in the origin. The
origin's memo and its relpath base are dropped; paths are reported as given.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst
import libcst.matchers as m

from mikemol.pycodemod.core import Skip

if TYPE_CHECKING:
    from collections.abc import Sequence

MAX_LITERAL = 80


@dataclass(frozen=True, slots=True, order=True)
class Reader:
    """One file reading an artifact: the artifacts it names, failure ones first, and its verdict."""

    path: str
    artifacts: tuple[str, ...]
    bearing: str


@dataclass(frozen=True, slots=True)
class Readers:
    """Every file that reads an artifact, and the files that could not be read."""

    rows: list[Reader] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _literals(tree: cst.Module) -> list[str]:
    docstrings = {
        id(stmt.value)
        for stmt in m.findall(tree, m.Expr(value=m.SimpleString()))
        if isinstance(stmt, cst.Expr)
    }
    out: list[str] = []
    for node in m.findall(tree, m.SimpleString()):
        if id(node) in docstrings or not isinstance(node, cst.SimpleString):
            continue
        v = node.evaluated_value
        if isinstance(v, str) and v and len(v) < MAX_LITERAL and "\n" not in v:
            out.append(v)
    return out


def _read(path: str) -> list[str] | Skip:
    try:
        tree = cst.parse_module(Path(path).read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except cst.ParserSyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)
    return _literals(tree)


def _classify(
    lits: Sequence[str], failure: Sequence[str], success: Sequence[str]
) -> tuple[tuple[str, ...], str] | None:
    fail = sorted({a for a in failure for s in lits if a in s})
    matched = {s for s in lits if any(a in s for a in failure)}
    succ = sorted({a for a in success for s in lits if s not in matched and a in s})
    if not fail and not succ:
        return None
    bearing = "BOTH" if fail and succ else "FAILURE" if fail else "SUCCESS"
    return tuple(fail + succ), bearing


def artifact_readers(
    paths: Sequence[str], failure: Sequence[str], success: Sequence[str]
) -> Readers:
    """Return the files that read a build artifact, with the unread files.

    Returns:
        one row per file naming an artifact, sorted, with the skipped files.

    Raises:
        ValueError: if either vocabulary is empty.

    """
    if not failure or not success:
        msg = "artifact_readers needs a non-empty failure and success vocabulary"
        raise ValueError(msg)
    out = Readers()
    for path in paths:
        got = _read(path)
        if isinstance(got, Skip):
            out.skipped.append(got)
            continue
        verdict = _classify(got, failure, success)
        if verdict is not None:
            out.rows.append(Reader(path, *verdict))
    out.rows.sort()
    return out
