# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run one command in a directory: the leaf the re-vendor chain and the wheel builder share (W1280).

⚑ A LEAF ON PURPOSE. `run_process` lived in `repin_cli`, and `wheel` imported `repin_cli` for it,
while `repin_cli` imports the re-vendor chain that imports `wheel`. Importing `revendor_cli` first
therefore walked revendor_cli, revendor_apply, wheel, repin_cli and back into the half-built
revendor_cli: `cannot import name 'run_revendor'`. Entering through `repin_cli` first hid it from
the console script and the suite, and a consumer that imports every module (summit's witness) found
it. A module this one imports nothing of the package, so no module can reach it through a cycle.
"""

import subprocess
from collections.abc import Sequence
from pathlib import Path


def run_process(argv: Sequence[str], cwd: Path) -> tuple[int, str]:
    """Run a command in a directory.

    Returns:
        its exit code and standard output; 127 and empty when the program is missing.

    """
    try:
        done = subprocess.run(list(argv), cwd=cwd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return 127, ""
    return done.returncode, done.stdout


def run_with_stdin(argv: Sequence[str], text: str) -> tuple[int, str]:
    """Run a command to completion with `text` on its standard input.

    ⚑ IT WAITS (W1828, luthen-observability 2026-10-23): a detached child that a oneshot unit's
    cgroup ends when the main process exits sends nothing, and the pass reported exit 0. Waiting is
    what lets the caller see the child fail.

    Returns:
        its exit code and standard error; 127 and a note when the program is missing.

    """
    try:
        done = subprocess.run(list(argv), input=text, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return 127, f"{argv[0]}: not found"
    return done.returncode, done.stderr
