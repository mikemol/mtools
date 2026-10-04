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

from mikemol.mutation import mutate

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


_FIELDS = 4
_PERCENT_ESCAPES = {"7C": "|", "25": "%"}


def _unescape(field: str) -> str:
    """Decode one field: `%7C` is `|`, `%25` is `%`, any other `%` is refused.

    Returns:
        The field with its escapes decoded.

    Raises:
        ValueError: on a `%` that is not one of the two escapes.

    """
    parts = field.split("%")
    out = [parts[0]]
    for part in parts[1:]:
        decoded = _PERCENT_ESCAPES.get(part[:2])
        if decoded is None:
            msg = f"regex spec: bad escape '%{part[:2]}' (only %7C and %25 exist)"
            raise ValueError(msg)
        out.append(decoded + part[2:])
    return "".join(out)


def _parse_scope(scope: str) -> tuple[str | None, tuple[int, int] | None]:
    """Parse the scope field: empty, `def=<qualname>` or `lines=<a>-<b>`.

    Returns:
        The def name and the line range, at most one of them set.

    Raises:
        ValueError: on any other form or a range that is not two decimal integers.

    """
    text = _unescape(scope)
    if not text:
        return None, None
    key, _, value = text.partition("=")
    if key == "def" and value:
        return value, None
    first, dash, last = value.partition("-")
    digits = dash and first.isascii() and first.isdecimal() and last.isascii() and last.isdecimal()
    if key == "lines" and digits:
        return None, (int(first), int(last))
    msg = f"regex spec: bad scope '{text}' (want empty, def=<qualname> or lines=<a>-<b>)"
    raise ValueError(msg)


def parse_regex_spec(text: str) -> RegexSpec:
    """Parse `<name>|<pattern>|<replacement>|<scope>` into a RegexSpec, refusing anything else.

    `|` separates exactly four fields; within a field `%7C` is a literal `|` and `%25` a literal
    `%`. The scope is empty, `def=<qualname>` or `lines=<a>-<b>`. Nothing is guessed.

    Returns:
        The spec.

    Raises:
        ValueError: on a wrong field count, an empty name, a bad escape, scope or range.

    """
    fields = text.split("|")
    if len(fields) != _FIELDS:
        msg = f"regex spec: want {_FIELDS} fields separated by '|', got {len(fields)}"
        raise ValueError(msg)
    name, pattern, replacement, scope = fields
    if not name:
        msg = "regex spec: the name is empty"
        raise ValueError(msg)
    def_name, lines = _parse_scope(scope)
    return RegexSpec(
        _unescape(name), _unescape(pattern), _unescape(replacement), def_name=def_name, lines=lines
    )


def _scope_span(text: str, spec: RegexSpec, total: int) -> tuple[int, int]:
    """Return the 1-based inclusive line span a regex spec is confined to.

    Returns:
        The first and last line.

    Raises:
        KeyError: when the named def does not exist or the range starts past the end of the file.

    """
    if spec.def_name is not None:
        for qn, node in mutate.def_sites(text):
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
