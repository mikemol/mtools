# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-pycheck --ratchet ROOT --write` and `--init`: the baselines only ever record progress.

W1794. `--write` lowers both committed baselines to today's counts, and refuses (exit 4, nothing
written) when any count would rise, so the file can only fall. `--init` writes the first baselines
and refuses (exit 1, nothing written) when either exists, so a baseline is never replaced by
accident with whatever the tree measures today.

⚑ BOTH FILES OR NEITHER. A refusal on either tool writes neither baseline, so the two never record
different moments of the tree.

⚑ THE WRITER IS A SEAM, like the tools in `pycheck_ratchet`: the decision is tested without a disk,
and the console wiring supplies `Path.write_text`.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from mikemol.hooks import baselinedir, pyratchet
from mikemol.hooks.pycheck_ratchet import (
    EXIT_NOT_CHECKED,
    MYPY_BASELINE,
    NO_BASELINE,
    RUFF_BASELINE,
    Tools,
    baseline,
)

EXIT_FAILED = 1
EXISTS = "pycheck --ratchet --init: a baseline exists; use --write\n"

type Write = Callable[[Path, str], None]
type Measured = tuple[pyratchet.Counts, pyratchet.Counts]


def encode(counts: pyratchet.Counts) -> str:
    """Serialise one baseline.

    Returns:
        the counts as sorted, indented JSON ending in a newline.

    """
    return json.dumps(counts, indent=1, sort_keys=True) + "\n"


def _measure(root: Path, tools: Tools) -> Measured:
    ruff = pyratchet.ruff_counts(tools.ruff(root), root)
    mypy = pyratchet.mypy_counts(tools.mypy(root).splitlines(), root)
    return ruff, mypy


def _save(root: Path, counts: Measured, write: Write) -> None:
    write(root / RUFF_BASELINE, encode(counts[0]))
    # ⚑ W2191: A BASELINE KEPT PER MODULE IS LOWERED PART BY PART. The reader takes the directory
    # before the single file (W2190), so the single file is never written beside one, and only
    # the parts whose counts changed are rewritten.
    split = root / baselinedir.DIR
    if split.is_dir():
        for name, part in baselinedir.lowered(baselinedir.parts(split) or [], counts[1]).items():
            write(split / name, encode(part))
        return
    write(root / MYPY_BASELINE, encode(counts[1]))


def lower(root: Path, tools: Tools, write: Write, out: TextIO, err: TextIO) -> int:
    """Lower both baselines to the current counts.

    Returns:
        0 when written, `EXIT_RISE` when a count would rise (nothing written), or
        `EXIT_NOT_CHECKED` when a baseline is missing or unreadable (nothing run).

    """
    ruff_base = baseline(tools.read(root / RUFF_BASELINE))
    mypy_base = baseline(tools.read(root / MYPY_BASELINE))
    if ruff_base is None or mypy_base is None:
        err.write(NO_BASELINE)
        return EXIT_NOT_CHECKED
    now = _measure(root, tools)
    judged = [
        pyratchet.verdict("ruff", now[0], ruff_base),
        pyratchet.verdict("mypy", now[1], mypy_base),
    ]
    if any(status for status, _lines in judged):
        err.writelines("\n".join(lines) + "\n" for _status, lines in judged)
        return pyratchet.EXIT_RISE
    _save(root, now, write)
    out.writelines(f"{lines[0]}\n" for _status, lines in judged)
    return 0


def initial(root: Path, tools: Tools, write: Write, out: TextIO, err: TextIO) -> int:
    """Write the first baselines.

    Returns:
        0 when written, `EXIT_FAILED` when either baseline already exists (nothing written).

    """
    existing = (tools.read(root / RUFF_BASELINE), tools.read(root / MYPY_BASELINE))
    if any(text is not None for text in existing):
        err.write(EXISTS)
        return EXIT_FAILED
    now = _measure(root, tools)
    _save(root, now, write)
    out.write(f"pycheck --ratchet --init: baselines of {pyratchet.total(now[0])} ruff and ")
    out.write(f"{pyratchet.total(now[1])} mypy findings written\n")
    return 0
