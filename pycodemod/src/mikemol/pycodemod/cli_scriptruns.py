# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`by-path-runs`: report, and with --write rewrite, the scripts run by path instead of by package.

⚑ A WRITE IS VERIFIED BY ITS OWN CENSUS: after it, the same scan runs over the files as written,
and any run still found fails the command. Mentions are printed either way and never rewritten.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod import report, scriptruns

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class RunFlags:
    """What `by-path-runs` was asked: the packages whose scripts it knows, and write or not."""

    packages: tuple[str, ...]
    write: bool


def _say(line: str) -> None:
    sys.stdout.write(f"{line}\n")


def print_runs(paths: Sequence[str], flags: RunFlags) -> int:
    """Print every run and mention of a package script, and rewrite the runs when asked.

    Returns:
        0 when no run remains after the write (or none was asked for), 1 when a run is left,
        2 when a file could not be read.

    """
    found = scriptruns.scan(paths, flags.packages)
    for run in found.runs:
        _say(f"run {run.script} {run.path}:{run.line}:{run.column}")
    for mention in found.mentions:
        _say(f"mention {mention.script} {mention.path}:{mention.line}:{mention.column}")
    left = 0
    if flags.write:
        for path, text in sorted(found.texts.items()):
            Path(path).write_text(text, encoding="utf-8")
        left = len(scriptruns.scan(sorted(found.texts), flags.packages).runs)
        _say(f"by-path-runs wrote {len(found.texts)} files, {left} runs remain")
    lines, code = report.incomplete([(s.why, s.error) for s in found.skipped], len(paths))
    for text in lines:
        report.note(f"{text}\n")
    return code or (1 if left else 0)
