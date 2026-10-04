# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The OPEN operator: ask a suite whether it notices ONE NAMED defect, not only a body-to-raise.

The closed grammar of `mikemol.mutation.mutate` asks "does the suite reach this def". A `RegexSpec`
asks "would the suite notice THIS edit": the CALLER declares a name, a regex over source text and a
replacement, optionally confined to one def or a line range. No default mutators ship here; the
patterns are the caller's data.

`judge` runs the spec against a caller-supplied suite with a REQUIRED positive control: the
unmutated source must pass first, and a regex that matches nothing is UNAPPLIED, never read as
killed or survived. Nothing is loaded in-process and nothing is written beside the source.
"""

from __future__ import annotations

import ast
import enum
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.mutation.mutate import def_sites

if TYPE_CHECKING:
    from collections.abc import Callable


class UnappliedError(KeyError):
    """A regex spec matched nothing in its scope: the defect cannot be planted there.

    A KeyError, like every other miss in the grid, so it is never a silent no-op; its own type,
    so a caller can report UNAPPLIED instead of reading the miss as killed or survived.
    """


class Verdict(enum.StrEnum):
    """What asking a suite about ONE named defect can answer."""

    KILLED = "killed"  # the unmutated source passes and the mutant fails: the suite notices
    SURVIVED = "survived"  # both pass: the suite is blind to this defect
    UNAPPLIED = "unapplied"  # the regex matched nothing: no question was asked
    CONTROL_FAILED = "control-failed"  # the unmutated source fails: the suite cannot judge


@dataclass(frozen=True)
class RegexSpec:
    """An open operator declared by the caller: one named defect as a regex rewrite.

    `pattern` is a multi-line regex over source text; `replacement` is an `re.sub` template.
    The rewrite is confined to the def named `def_name` (a qualname) or to the 1-based inclusive
    `lines` range; with neither it spans the whole file. Naming both is refused.
    """

    name: str
    pattern: str
    replacement: str
    def_name: str | None = None
    lines: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        """Refuse a scope that names both a def and a range, or an empty range.

        Raises:
            ValueError: when the scope is contradictory or the range is not 1 <= first <= last.

        """
        if self.def_name is not None and self.lines is not None:
            msg = f"regex spec '{self.name}': give a def or a line range, not both"
            raise ValueError(msg)
        if self.lines is not None and not 1 <= self.lines[0] <= self.lines[1]:
            msg = f"regex spec '{self.name}': lines must satisfy 1 <= first <= last"
            raise ValueError(msg)


def _scope_span(text: str, spec: RegexSpec, total: int) -> tuple[int, int]:
    """Return the 1-based inclusive line span a regex spec is confined to.

    Returns:
        The first and last line.

    Raises:
        KeyError: when the named def does not exist or the range starts past the end of the file.

    """
    if spec.def_name is not None:
        for qn, node in def_sites(text):
            if qn == spec.def_name:
                return node.lineno, node.end_lineno or node.lineno
        msg = f"mutant: regex '{spec.name}' names '{spec.def_name}', not a def-site in the module"
        raise KeyError(msg)
    if spec.lines is not None:
        if spec.lines[0] > total:
            msg = f"mutant: regex '{spec.name}' lines start past the end of the module"
            raise KeyError(msg)
        return spec.lines[0], min(spec.lines[1], total)
    return 1, max(total, 1)


def apply_regex(text: str, spec: RegexSpec) -> str:
    """Return the source with the spec's rewrite applied inside its scope, the rest byte-identical.

    Returns:
        The perturbed source.

    Raises:
        UnappliedError: when the pattern matches nothing in the scope.
        ValueError: when the rewrite leaves source that no longer parses.

    """
    lines = text.splitlines(keepends=True)
    first, last = _scope_span(text, spec, len(lines))
    scope = "".join(lines[first - 1 : last])
    rewritten, count = re.subn(spec.pattern, spec.replacement, scope, flags=re.MULTILINE)
    if count == 0:
        msg = f"mutant: regex '{spec.name}' matched nothing in lines {first}-{last}"
        raise UnappliedError(msg)
    out = "".join(lines[: first - 1]) + rewritten + "".join(lines[last:])
    try:
        ast.parse(out)
    except SyntaxError as err:
        msg = f"regex spec '{spec.name}' leaves source that does not parse: {err.msg}"
        raise ValueError(msg) from err
    return out


def judge(text: str, spec: RegexSpec, passes: Callable[[str], bool]) -> Verdict:
    """Ask a suite whether it notices the one defect `spec` names.

    `passes` is the CALLER's suite: it takes a module source and says whether the suite is green
    on it. The POSITIVE CONTROL is mandatory and runs first: if the unmutated source does not
    pass, nothing can be concluded.

    Returns:
        CONTROL_FAILED, UNAPPLIED, SURVIVED (the mutant passes) or KILLED (the mutant fails).

    """
    if not passes(text):
        return Verdict.CONTROL_FAILED
    try:
        mutant = apply_regex(text, spec)
    except UnappliedError:
        return Verdict.UNAPPLIED
    return Verdict.SURVIVED if passes(mutant) else Verdict.KILLED
