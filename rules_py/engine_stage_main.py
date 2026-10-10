# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run one `gate_stages` script under the pinned engine's environment (mtools:W896).

    engine_stage_main.py --engine=ENGINE/paperkit/gate.py --script=SCRIPT [-- ARGS...]

A stage that imports the engine (gcalculus:W222: five gcalc leaves import paperkit's `labelmap`)
needs what `paperkit_gate` gives its gate: PYTHONPATH of the pinned checkout, PAPERKIT_ENGINE, and
a scratch directory. The environment is `engine_env.engine_env`, the same function
`paperkit_gate_main` calls, so the two cannot drift. The script itself runs unchanged, as a
subprocess of this interpreter, from the working directory a py_test gives it.

Both paths are runfiles paths a bazel rule names with `$(rootpath ...)`; a path that is not among
the declared inputs is a refusal (exit 2), never a lookup in the live tree.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from engine_env import engine_env, take

_ENGINE = "--engine="
_SCRIPT = "--script="
_END = "--"
_REFUSED = 2


def main(argv: list[str]) -> int:
    """Run `python SCRIPT ARGS` with the engine environment.

    Returns:
        the script's exit code; 2 when the engine or the script is not among the declared inputs.

    """
    flags = argv[: argv.index(_END)] if _END in argv else argv
    args = argv[argv.index(_END) + 1 :] if _END in argv else []
    engine_arg, rest = take(flags, _ENGINE)
    script_arg, _ = take(rest, _SCRIPT)
    if engine_arg is None or script_arg is None:
        sys.stderr.write("engine_stage_main: --engine= and --script= are both required\n")
        return _REFUSED
    engine = Path(engine_arg).resolve()
    script = Path(script_arg).resolve()
    if not engine.is_file() or not script.is_file():
        sys.stderr.write(f"engine_stage_main: {engine} or {script} is not a declared input\n")
        return _REFUSED
    env = engine_env(engine, os.environ)
    return subprocess.run([sys.executable, str(script), *args], env=env, check=False).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
