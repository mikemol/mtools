# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run one paperkit gate over a project, with the engine at a pinned commit (mtools:W843).

    paperkit_gate_main.py --engine=ENGINE/paperkit/gate.py --project=PROJECT/paper.toml [FLAGS...]

Both paths are runfiles paths a bazel rule names with `$(rootpath ...)`. The engine is the files of
a `pinned_files` repository, so the verdict is about THAT commit and never about a sibling's working
tree; the project is the caller's own named files.

⚑⚑ THE ENGINE'S PACKAGE DIRECTORY IS THE WORKING DIRECTORY, NEVER ON PYTHONPATH. Every check the
engine runs inherits the environment, and the engine's `config`, `layout` and `bib` would shadow
the checks' own (measured 2026-10-06: three claims red in the gate and green on replay). `python -m`
puts the working directory first, which is how the engine still finds its flat siblings until
paperkit:W296 removes them. Only the checkout above it is exported, for `import paperkit`.

⚑ THE ENGINE'S SCRATCH IS THE TEST'S OWN TEMPORARY DIRECTORY (`TEST_TMPDIR`), so a hermetic sandbox
that forbids writing elsewhere still lets the engine copy its Δ sandboxes.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_ENGINE = "--engine="
_PROJECT = "--project="
_SCRATCH = "PAPERKIT_SCRATCH"
_TEMP = "TEST_TMPDIR"
_REFUSED = 2


def _take(argv: list[str], flag: str) -> tuple[str | None, list[str]]:
    """Split `argv` into the value of `flag` and the rest.

    Returns:
        the flag's value or None, and the arguments without it.

    """
    value = next((a[len(flag) :] for a in argv if a.startswith(flag)), None)
    return value, [a for a in argv if not a.startswith(flag)]


def main(argv: list[str]) -> int:
    """Run `python -m paperkit.gate FLAGS PROJECT` from the engine's directory.

    Returns:
        the gate's exit code; 2 when the engine or the project is not among the declared inputs.

    """
    engine_arg, rest = _take(argv, _ENGINE)
    project_arg, flags = _take(rest, _PROJECT)
    if engine_arg is None or project_arg is None:
        sys.stderr.write("paperkit_gate_main: --engine= and --project= are both required\n")
        return _REFUSED
    engine = Path(engine_arg).resolve()
    project = Path(project_arg).resolve().parent
    if not engine.is_file() or not project.is_dir():
        sys.stderr.write(f"paperkit_gate_main: {engine} or {project} is not a declared input\n")
        return _REFUSED
    package_dir = engine.parent
    env = dict(os.environ)
    env["PYTHONPATH"] = str(package_dir.parent)
    # ⚑ A CONSUMER'S WITNESSES NAME THE ENGINE THE WAY ITS OWN WRAPPER DID: `scripts/paperkit.sh`
    # exported PAPERKIT_ENGINE, which paperkit's clean_env carries into every check, and a witness
    # that finds the engine through it (resumes' grounding:) otherwise falls back to the live
    # ~/github/paperkit, which a hermetic sandbox does not have and a gate must not read.
    env["PAPERKIT_ENGINE"] = str(package_dir)
    if _TEMP in env:
        env.setdefault(_SCRATCH, env[_TEMP])
    cmd = [sys.executable, "-m", "paperkit.gate", *flags, str(project)]
    return subprocess.run(cmd, cwd=package_dir, env=env, check=False).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
