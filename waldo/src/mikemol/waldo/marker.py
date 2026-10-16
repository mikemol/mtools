# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A durable phase marker: the recipe's current gate state, a file it writes and reads back (W1064).

From cassian's vault-apply recipe, where `write_tfvars` records the five gate variables and `tfvar`
reads one back: the marker IS the phase, observable and not inferred, and each phase begins by
asserting the standing flags it needs (`assert_deploy_renewer_true`) and refusing when the marker
disagrees.

The format is `key = value`, one per line, `#` for comments, so a human can read it, a diff shows a
phase moving, and a Terraform-style consumer could read it as it is.

⚑ A MARKER THAT IS AMBIGUOUS IS REFUSED, NOT GUESSED AT. A repeated key, a line that is not
`key = value`, a key that is not an identifier, or a value that spans lines raises `MarkerError`
naming the line; a half-readable marker read as the phase would run the wrong phase.

⚑ WRITTEN BY RENAME. The text goes to a temporary file in the same directory and replaces the
marker, so a reader sees the old phase or the new one, never half of one. A link is refused for the
file and its directory (no-symlinks ruling).

⚑ `require_standing` NAMES EVERY MISMATCH AT ONCE, so one refusal tells the operator everything the
marker disagrees about and not just the first thing.
"""

import os
import re
from collections.abc import Mapping
from pathlib import Path

KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
LINE = re.compile(r"\s*([^=\s]+)\s*=\s*(.*?)\s*")


class MarkerError(ValueError):
    """A marker file, or a value to put in one, is not a valid marker."""


def render(values: Mapping[str, str], header: str = "") -> str:
    """Give the marker text for `values`, in their order.

    Returns:
        the text: `# ` header lines, then one `key = value` line per entry.

    Raises:
        MarkerError: when a key is not an identifier or a value spans lines.

    """
    lines = [f"# {line}".rstrip() for line in header.splitlines()]
    for key, value in values.items():
        if KEY.fullmatch(key) is None:
            msg = f"{key!r} is not a valid marker key"
            raise MarkerError(msg)
        if "\n" in value or "\r" in value:
            msg = f"the value of {key} spans lines"
            raise MarkerError(msg)
        lines.append(f"{key} = {value}")
    return "\n".join(lines) + "\n"


def parse(text: str) -> dict[str, str]:
    """Read marker text back into its values.

    Returns:
        the values by key; comments and blank lines are skipped.

    Raises:
        MarkerError: on a line that is not `key = value`, a bad key, or a repeated key.

    """
    values: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        found = LINE.fullmatch(line)
        if found is None or KEY.fullmatch(found.group(1)) is None:
            msg = f"line {number}: not `key = value`: {line!r}"
            raise MarkerError(msg)
        key, value = found.group(1), found.group(2)
        if key in values:
            msg = f"line {number}: {key} is set twice"
            raise MarkerError(msg)
        values[key] = value
    return values


def _refuse_link(path: Path) -> None:
    """Refuse a path that is a link.

    Raises:
        MarkerError: when it is.

    """
    if path.is_symlink():
        msg = f"{path} is a link; a marker is never written or read through one"
        raise MarkerError(msg)


def write(path: Path, values: Mapping[str, str], header: str = "") -> None:
    """Write the marker, replacing any earlier one atomically."""
    _refuse_link(path)
    _refuse_link(path.parent)
    text = render(values, header)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def read(path: Path) -> dict[str, str] | None:
    """Read the marker.

    Returns:
        the values, or None when there is no marker yet (a fresh start, which is not an empty one).

    """
    _refuse_link(path)
    _refuse_link(path.parent)
    if not path.is_file():
        return None
    return parse(path.read_text(encoding="utf-8"))


def mismatches(marker: Mapping[str, str] | None, expected: Mapping[str, str]) -> list[str]:
    """List how the marker disagrees with what a phase needs.

    Returns:
        one line per key that is absent or holds another value; no marker at all is one line.

    """
    if marker is None:
        return ["no marker: the recipe has not recorded a phase yet"]
    found = [
        f"{key}: expected {want!r}, the marker has {marker[key]!r}"
        for key, want in expected.items()
        if key in marker and marker[key] != want
    ]
    lacking = [
        f"{key}: expected {want!r}, the marker lacks it"
        for key, want in expected.items()
        if key not in marker
    ]
    return found + lacking


def require_standing(marker: Mapping[str, str] | None, expected: Mapping[str, str]) -> None:
    """Refuse unless the marker holds every standing flag the phase needs.

    Raises:
        MarkerError: naming every mismatch at once.

    """
    problems = mismatches(marker, expected)
    if problems:
        msg = "the marker disagrees with this phase: " + "; ".join(problems)
        raise MarkerError(msg)
