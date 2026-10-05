# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A split module BEHAVES as the original: the entry still exposes every public name (W645).

Losslessness (`split.verify`) says the statements survived byte for byte; it does not say the entry
module still answers to the original's names. This applies a split to a small synthetic module under
`tmp_path`, then imports the entry in a FRESH interpreter and compares what the original and the
split entry print. A subprocess, because `getattr` on a dynamically imported module is `Any`, which
the type checker here forbids.
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

from mikemol.pycodemod import split

if TYPE_CHECKING:
    from pathlib import Path

_LIVE = (
    "_BASE = 10\n"
    "def _scale(x):\n"
    "    return x * _BASE\n"
    "def helper():\n"
    "    return 3\n"
    "def total():\n"
    "    return _scale(2) + helper()\n"
    "TABLE = {'k': total}\n"
)

_PUBLIC = ("TABLE", "helper", "total")

_PROBE = (
    "import live\n"
    f"print(all(hasattr(live, n) for n in {_PUBLIC!r}))\n"
    "print(repr(live.total()))\n"
    "print(repr(live.TABLE['k']()))\n"
    "print(repr((live.helper(), sorted(live.TABLE))))\n"
)


async def _printed(script: Path) -> str:
    # A fresh interpreter, so the entry module is imported from disk and nothing is cached.
    # ⚑ PYTHONPATH IS NAMED, NOT INHERITED: under bazel's interpreter the script's own directory is
    # not put on sys.path (a safe-path bootstrap), so `import live` failed hermetically with
    # ModuleNotFoundError while plain pytest passed. The environment is replaced whole, so the
    # safe-path switch cannot leak in either.
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-B",
        script.name,
        cwd=script.parent,
        env={"PYTHONPATH": str(script.parent)},
        stdout=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    assert proc.returncode == 0
    return out.decode("utf-8")


def test_a_split_entry_module_behaves_as_the_original_in_a_fresh_interpreter(
    tmp_path: Path,
) -> None:
    """Apply a split, import the entry in a subprocess, and print what it computes.

    The original and the split entry must print the same reprs, and every public name must still
    be an attribute of the entry.
    """
    path = tmp_path / "live.py"
    path.write_text(_LIVE, encoding="utf-8")
    probe = tmp_path / "probe.py"
    probe.write_text(_PROBE, encoding="utf-8")
    before = asyncio.run(_printed(probe))
    p = split.plan(str(path), split.Options(max_defs=1))
    assert len(p.parts) > 1
    split.apply(p, write=True)
    assert (tmp_path / "live_00.py").exists()
    after = asyncio.run(_printed(probe))
    assert before.splitlines()[0] == "True"
    assert after == before
