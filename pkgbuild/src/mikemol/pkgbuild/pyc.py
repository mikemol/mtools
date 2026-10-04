# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Compile one .py to its .pyc BUILD ARTIFACT, the bytecode Python executes (like .cc to .o).

Ported from paperkit's `tools/pyc.py` (paperkit:W142), behaviour unchanged.

Compilation is a build step, not an import-time side effect. The .pyc is written with PEP 552
UNCHECKED_HASH invalidation: it records a CONTENT hash of the source (not its mtime) and the
runtime NEVER rechecks the source, so the artifact is reproducible (no mtime, so
byte-deterministic and cacheable) and authoritative (the build graph owns compilation; a mutated
.pyc over an unchanged .py runs the mutation).

Usage:  mikemol-pyc <src.py> <out.pyc>
"""

from __future__ import annotations

import py_compile
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Compile `src` to `out` as an UNCHECKED_HASH .pyc; `argv` is exactly `[src, out]`.

    Returns:
        0 on success; a compile error raises `py_compile.PyCompileError`.

    """
    src, out = sys.argv[1:] if argv is None else argv
    py_compile.compile(
        src,
        cfile=out,
        doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
