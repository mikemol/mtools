# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Compare two capture files row by row, with run-to-run noise normalized (W475).

`compare_captures.py A.jsonl B.jsonl` prints the row counts and every differing row number, and
exits 1 when any row differs. Two captures of one origin are never byte-identical, for three
reasons this normalizes away — and nothing else:
  - mkdtemp names: each fixture tree is a fresh directory under the temp root, renamed `<tmpN>`
    in order of first appearance within its row (the root is READ from tempfile, as capture.py
    reads it, so both agree on what a fixture tree is);
  - repr addresses: `<... at 0x7f...>` becomes `at 0xADDR`;
  - set order: the elements of a `frozenset({...})` or `{...}` repr of plain strings are sorted,
    since hash randomization reorders them per process.
W472 used this (as a scratchpad script) to show capture.py reproduces W128-capture.py's rows.
"""

import re
import sys
import tempfile
from pathlib import Path

TMPROOT = str(Path(tempfile.gettempdir()).resolve()) + "/"
TMP = re.compile(re.escape(TMPROOT) + r"""[^/'"\\]+""")
ADDR = re.compile(r" at 0x[0-9a-f]+")
STRING_SET = re.compile(r"(frozenset\()?\{('[^'{}]*'(?:, '[^'{}]*')*)\}")


def _sorted_set(match: re.Match[str]) -> str:
    prefix = str(match.group(1) or "")
    members = ", ".join(sorted(str(match.group(2)).split(", ")))
    return f"{prefix}{{{members}}}"


def normalize(line: str) -> str:
    """Remove the three kinds of run-to-run noise from one capture row.

    Returns:
        the row with temp names, addresses and string-set order made canonical.

    """
    seen: dict[str, str] = {}

    def rename(match: re.Match[str]) -> str:
        return seen.setdefault(str(match.group(0)), f"<tmp{len(seen)}>")

    line = TMP.sub(rename, line)
    line = ADDR.sub(" at 0xADDR", line)
    return STRING_SET.sub(_sorted_set, line)


def rows(path: Path) -> list[str]:
    """Read and normalize every row of a capture file.

    Returns:
        the normalized rows, in order.

    """
    return [normalize(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main(left: Path, right: Path) -> int:
    """Print the row counts and the differing row numbers.

    Returns:
        0 when every row matches and the counts agree, else 1.

    """
    a, b = rows(left), rows(right)
    differ = [i + 1 for i, (x, y) in enumerate(zip(a, b, strict=False)) if x != y]
    sys.stdout.write(f"rows {len(a)} {len(b)}\ndiffering {len(differ)} {differ}\n")
    return 0 if len(a) == len(b) and not differ else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
