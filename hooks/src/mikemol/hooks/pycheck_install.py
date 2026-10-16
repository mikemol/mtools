# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-pycheck --install SRC DEST`: place a draft only if the edit gate admits it (W1087).

The edit gate refuses any single Edit that leaves a file unformatted, half-imported or type-dirty,
so a multi-region change, or a new module and the import that uses it, cannot land one region at a
time. The route four repos found (paperkit, mtools, nemik, gcalculus) is a scratch draft that is
formatted, checked and then copied into place by hand; nemik's `tools/pyfmt.sh` is its 20-line seed.
The hand `cp` skips the edit gate, which the fleet's rule forbids, so this is also a rail.

⚑ DEST IS WRITTEN LAST AND ONLY WHEN CLEAN. The draft is formatted for the place it is going (the
project's own ruff, config and width, found from DEST and not from SRC), then judged by the SAME
`pycheck.analyze` the hook calls, as if it were DEST's content. A refused draft prints the whole
unclipped report and leaves DEST byte-for-byte untouched (nemik's script wrote first and checked
after, leaving a dirty file). The write is a rename of a temporary file in DEST's directory.

⚑ A NON-PYTHON FILE IS PLACED WITHOUT A GATE, and says so: the edit gate judges Python only, so
refusing a `.toml` or `.md` would be a refusal with nothing behind it. It is still written by rename
and still refuses a link.

⚑ "NOT CHECKED" IS NEVER "CLEAN". No governing project, an unreadable draft or no formatter is exit
3 and nothing is written; exit 4 is a refusal; exit 0 is installed.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from mikemol.hooks.verdict import Verdict

EXIT_INSTALLED = 0
EXIT_REFUSED = 4
EXIT_NOT_CHECKED = 3
PYTHON = ".py"


@dataclass(frozen=True)
class Gate:
    """The two judgements an install needs, injected: the edit gate and the project's formatter."""

    analyze: Callable[[str, str], Verdict]
    format_text: Callable[[Path, str, TextIO], str | None]


def _place(dest: Path, text: str) -> None:
    """Write `text` to `dest` by renaming a temporary file in its directory over it."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_name(f".{dest.name}.{os.getpid()}.install")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(dest)


def _prepare(src: Path, dest: Path, gate: Gate, err: TextIO) -> str | None:
    """Read the draft and, for Python, format it for the place it is going.

    Returns:
        the text to judge and place, or None (the reason on `err`) when a path is a link, the draft
        cannot be read, or no formatter could run.

    """
    for path in (src, dest, dest.parent):
        if path.is_symlink():
            err.write(f"mikemol-pycheck: {path} is a link; nothing installed\n")
            return None
    try:
        draft = src.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as problem:
        err.write(f"mikemol-pycheck: {src}: cannot be read ({problem}); nothing installed\n")
        return None
    return draft if dest.suffix != PYTHON else gate.format_text(dest, draft, err)


def install(src: Path, dest: Path, gate: Gate, out: TextIO, err: TextIO) -> int:
    """Install the draft at `src` as `dest` if the edit gate would admit it.

    Returns:
        EXIT_INSTALLED when `dest` now holds the formatted draft, EXIT_REFUSED when the gate would
        refuse it (the whole report on `out`, `dest` untouched), EXIT_NOT_CHECKED when no verdict
        could be rendered or a path is a link or the draft cannot be read (the reason on `err`).

    """
    text = _prepare(src, dest, gate, err)
    if text is None:
        return EXIT_NOT_CHECKED
    if dest.suffix != PYTHON:
        _place(dest, text)
        out.write(f"mikemol-pycheck: {dest}: installed (not Python, so not gated)\n")
        return EXIT_INSTALLED
    ok, report = gate.analyze(text, str(dest))
    if ok is None:
        err.write(f"mikemol-pycheck: {dest}: no verdict could be rendered: {report}\n")
        return EXIT_NOT_CHECKED
    if not ok:
        out.write(f"{report}\n")
        return EXIT_REFUSED
    _place(dest, text)
    out.write(f"mikemol-pycheck: {dest}: installed (formatted, and admitted by the edit gate)\n")
    return EXIT_INSTALLED
