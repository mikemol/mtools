# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""A distribution's DECLARED defect classes: the file format, and planting one (W629).

The def-site grid asks "does the suite reach this def". A `RegexSpec` asks "would the suite notice
THIS edit", and its patterns are the caller's data. This module is how a distribution DECLARES them:
a `mutants.regex` file beside its `pyproject.toml`, read by the `:mutants` runner, which plants each
declared defect in a temp copy and runs the distribution's own suite against it.

⚑⚑ NONE BY DEFAULT. No declaration ships here and a distribution with no file is asked nothing.
The patterns name defects the distribution actually shipped or fears, so they live beside it.

The file is one declaration per line, `<module>|<name>|<pattern>|<replacement>|<scope>`: the module
is a path relative to the distribution (forward slashes, `.py`, never absolute or `..`), and the
other four fields are `regexop.parse_regex_spec`'s own (`%7C` is a literal `|`, `%25` a literal `%`,
the scope empty, `def=<qualname>` or `lines=<a>-<b>`). A blank line and a line starting with `#`
are ignored; a name may repeat across modules and never within one.

⚑⚑ A STALE DECLARATION IS NOT A PASS. A spec whose pattern matches nothing in its scope plants no
defect, so `plant` answers `None` and the runner reports UNAPPLIED and fails: a declaration the code
has moved away from would otherwise read as a suite that notices a defect nobody can write.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from mikemol.mutation.regexop import RegexSpec, apply_regex, parse_regex_spec

DECLARATION_FILE = "mutants.regex"


@dataclass(frozen=True)
class Declared:
    """One declared defect: the module it is planted in and the spec that plants it."""

    module: str
    spec: RegexSpec

    @property
    def label(self) -> str:
        """Name the declaration as `<module>::<name>`, the address a report gives it."""
        return f"{self.module}::{self.spec.name}"


def _module(field: str, number: int) -> str:
    """Check that a declaration's module is a relative `.py` path inside the distribution.

    Returns:
        the module path as written.

    Raises:
        ValueError: when it is empty, absolute, climbs out with `..`, or is not a `.py` file.

    """
    path = PurePosixPath(field)
    if not field or path.is_absolute() or ".." in path.parts or path.suffix != ".py":
        msg = f"line {number}: module '{field}' must be a relative .py path inside the distribution"
        raise ValueError(msg)
    return field


def _declaration(raw: str, number: int) -> Declared:
    """Parse one non-blank, non-comment line into a declaration.

    Returns:
        the declaration.

    Raises:
        ValueError: on a line without a module field, or any field `parse_regex_spec` or the
            regex compiler refuses; the message carries the line number.

    """
    module, bar, rest = raw.partition("|")
    if not bar:
        msg = f"line {number}: want <module>|<name>|<pattern>|<replacement>|<scope>"
        raise ValueError(msg)
    try:
        spec = parse_regex_spec(rest)
        re.compile(spec.pattern)
    except (ValueError, re.error) as exc:
        msg = f"line {number}: {exc}"
        raise ValueError(msg) from exc
    return Declared(_module(module, number), spec)


def read_declarations(text: str) -> list[Declared]:
    """Read a `mutants.regex` file's declarations, in file order.

    Returns:
        the declarations; an empty or comment-only file declares none.

    Raises:
        ValueError: when a line is malformed, or a module repeats a name (the message names the
            line); nothing is guessed and no line is skipped for being wrong.

    """
    found: list[Declared] = []
    seen: set[tuple[str, str]] = set()
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        declared = _declaration(raw, number)
        key = (declared.module, declared.spec.name)
        if key in seen:
            msg = f"line {number}: '{declared.spec.name}' is declared twice for {declared.module}"
            raise ValueError(msg)
        seen.add(key)
        found.append(declared)
    return found


def plant(source: str, spec: RegexSpec) -> str | None:
    """Plant a declared defect in a module's source.

    A pattern that matches nothing in its scope, or a scope naming a def or lines the module does
    not have, plants nothing. A rewrite that leaves source which no longer parses is a bad
    declaration and `apply_regex`'s `ValueError` is left to propagate.

    Returns:
        the source with the defect planted, or None when nothing could be planted.

    """
    try:
        return apply_regex(source, spec)
    except KeyError:
        return None
