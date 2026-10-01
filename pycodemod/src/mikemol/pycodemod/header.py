# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The licence header: check it, or write the lines a file is missing (W306, el-openglo:W119).

One mode from the two implementations in the fleet, compared line by line in
`.claude/design/W306-header-mode.md`: el-openglo's `check_license.py` (`with_header`, the
coding-line rule, the wrong-id report) and linux-sources' `codemod_header.py` (both lines, the
shebang report). Standard library only.

⚑ THE HEADER LIVES IN THE LEADING COMMENT BLOCK, read as TEXT: the lines before the first line
that is not a comment. Position there is unambiguous. libcst's split between `module.header` and
the first statement's leading lines is what made linux-sources refuse a partial header, and that
refusal would have refused every one of el-openglo's 152 files (SPDX, no copyright).

⚑ THE SHEBANG AND A PEP 263 CODING LINE STAY FIRST. Python reads a coding declaration only on
line 1 or 2, so the header goes after both. A writer that inserts above it silently changes how the
file decodes. That was linux-sources' defect, unmeasured there, fixed as linux-sources:W101.

⚑ A WRONG ID IS REPORTED, NEVER REWRITTEN. Changing a file's licence is a decision, not a codemod,
so `--write` refuses it and names the file.

⚑ THE SHEBANG SET IS HANDED OVER, NOT ANSWERED. A shebang on a non-executable file is EXE001, a mode
bit only the filesystem holds. `--write` lists the rewritten files that carry one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SPDX_KEY = "SPDX-License-Identifier:"
_COPYRIGHT = "# Copyright"
# PEP 263's own pattern, applied to lines 1 and 2 only.
_CODING = re.compile(r"^[ \t\f]*#.*?coding[:=][ \t]*[-_.a-zA-Z0-9]+")
_CODING_LINES = 2

COMPLETE = "complete"
MISSING = "missing"
PARTIAL = "partial"
WRONG = "wrong"


@dataclass(frozen=True, slots=True)
class Plan:
    """What one file's header is, the text it should become, and whether it has a shebang."""

    state: str
    detail: str
    text: str
    shebang: bool


def _block(lines: list[str]) -> int:
    """Measure the leading comment block.

    Returns:
        how many leading lines are comments.

    """
    count = 0
    for line in lines:
        if not line.lstrip().startswith("#"):
            break
        count += 1
    return count


def _after_prelude(lines: list[str]) -> int:
    """Find where a header may start: after a line-1 shebang and a line-1-or-2 coding line.

    Returns:
        the index the header lines go at.

    """
    at = 1 if lines and lines[0].startswith("#!") else 0
    if at < len(lines) and at < _CODING_LINES and _CODING.match(lines[at]):
        at += 1
    return at


def _spdx_id(line: str) -> str:
    """Read the id an SPDX line declares.

    Returns:
        the id, or "" when the line names none.

    """
    return line.split(SPDX_KEY, 1)[1].strip()


def plan(text: str, *, spdx: str, holder: str | None, year: int) -> Plan:
    """Decide one file's header, and the text it should become.

    `holder` given: the header is SPDX plus `# Copyright (c) <year> <holder>`. Absent: SPDX only.
    An existing copyright line is never rewritten.

    Returns:
        the plan. `text` is unchanged for a complete or a wrong header.

    """
    lines = text.splitlines(keepends=True)
    newline = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
    shebang = bool(lines) and lines[0].startswith("#!")
    head = lines[: _block(lines)]
    spdx_at = next((i for i, line in enumerate(head) if SPDX_KEY in line), None)
    copy_at = next((i for i, line in enumerate(head) if line.startswith(_COPYRIGHT)), None)
    spdx_line = f"# {SPDX_KEY} {spdx}{newline}"
    copy_line = f"{_COPYRIGHT} (c) {year} {holder}{newline}" if holder else ""
    if spdx_at is not None and _spdx_id(head[spdx_at]) != spdx:
        found = _spdx_id(head[spdx_at]) or "nothing"
        return Plan(WRONG, f"declares {found}, not {spdx}", text, shebang)
    if spdx_at is not None and (copy_at is not None or not holder):
        return Plan(COMPLETE, "", text, shebang)
    if spdx_at is not None:
        new = [*lines[: spdx_at + 1], copy_line, *lines[spdx_at + 1 :]]
        return Plan(PARTIAL, "adds the copyright line", "".join(new), shebang)
    if copy_at is not None:
        new = [*lines[:copy_at], spdx_line, *lines[copy_at:]]
        return Plan(PARTIAL, "adds the SPDX line", "".join(new), shebang)
    at = _after_prelude(lines)
    if lines and at == len(lines) and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += newline  # a prelude with no final newline still ends its own line
    new = [*lines[:at], spdx_line, copy_line, *lines[at:]]
    added = "SPDX and copyright lines" if holder else "the SPDX line"
    return Plan(MISSING, f"adds {added}", "".join(new), shebang)
