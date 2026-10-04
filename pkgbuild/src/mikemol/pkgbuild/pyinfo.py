# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Print the interpreter that runs this: its `sys.executable` and its version.

Ported from paperkit's `tools/pyinfo.py` (paperkit:W142), output unchanged.
"""

from __future__ import annotations

import sys


def main() -> int:
    """Write the executable and the version number, one `key: value` line each.

    Returns:
        0 always.

    """
    sys.stdout.write(f"executable: {sys.executable!r}\n")
    sys.stdout.write(f"version: {sys.version.split()[0]}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
