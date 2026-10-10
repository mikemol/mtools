# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run one paperkit gate over a project, with the engine at a pinned commit (mtools:W843).

    paperkit_gate_main.py --engine=ENGINE/paperkit/gate.py --project=PROJECT/paper.toml [FLAGS...]

Both paths are runfiles paths a bazel rule names with `$(rootpath ...)`. The engine is the files of
a `pinned_files` repository, so the verdict is about THAT commit and never about a sibling's working
tree; the project is the caller's own named files.

⚑⚑ THE ENGINE'S PACKAGE DIRECTORY IS THE WORKING DIRECTORY, NEVER ON PYTHONPATH. `python -m` puts
the working directory first, which is how the engine still finds its flat siblings until
paperkit:W296 removes them. The environment itself (PYTHONPATH of the checkout above the package,
PAPERKIT_ENGINE, the scratch) is `engine_env.engine_env` (mtools:W895), shared with the stage
runner.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from engine_env import engine_env, take

_ENGINE = "--engine="
_PROJECT = "--project="
_REFUSED = 2


def main(argv: list[str]) -> int:
    """Run `python -m paperkit.gate FLAGS PROJECT` from the engine's directory.

    Returns:
        the gate's exit code; 2 when the engine or the project is not among the declared inputs.

    """
    engine_arg, rest = take(argv, _ENGINE)
    project_arg, flags = take(rest, _PROJECT)
    if engine_arg is None or project_arg is None:
        sys.stderr.write("paperkit_gate_main: --engine= and --project= are both required\n")
        return _REFUSED
    engine = Path(engine_arg).resolve()
    project = Path(project_arg).resolve().parent
    if not engine.is_file() or not project.is_dir():
        sys.stderr.write(f"paperkit_gate_main: {engine} or {project} is not a declared input\n")
        return _REFUSED
    env = engine_env(engine, os.environ)
    cmd = [sys.executable, "-m", "paperkit.gate", *flags, str(project)]
    return subprocess.run(cmd, cwd=engine.parent, env=env, check=False).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
