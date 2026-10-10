# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The environment a pinned paperkit engine runs in, built once (mtools:W895).

`paperkit_gate_main` ran the gate under it, and a `gate_stages` stage that imports the engine
(gcalculus:W222) needs the same thing, so it is one function and both runners call it.

⚑⚑ THE ENGINE'S PACKAGE DIRECTORY IS NEVER ON PYTHONPATH. Every check the engine runs inherits the
environment, and the engine's flat `config`, `layout` and `bib` would shadow the checks' own
(measured 2026-10-06: three claims red in the gate and green on replay). Only the checkout ABOVE
the package is exported, for `import paperkit`.

⚑ A CONSUMER'S WITNESSES NAME THE ENGINE THE WAY ITS OWN WRAPPER DID: `scripts/paperkit.sh` exported
PAPERKIT_ENGINE, which paperkit's clean_env carries into every check, and a witness that finds the
engine through it otherwise falls back to the live ~/github/paperkit, which a hermetic sandbox does
not have and a gate must not read.

⚑ THE ENGINE'S SCRATCH IS THE TEST'S OWN TEMPORARY DIRECTORY (`TEST_TMPDIR`), so a sandbox that
forbids writing elsewhere still lets the engine copy its sandboxes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

ENGINE = "PAPERKIT_ENGINE"
SCRATCH = "PAPERKIT_SCRATCH"
TEMP = "TEST_TMPDIR"


def engine_env(engine: Path, environ: Mapping[str, str]) -> dict[str, str]:
    """Build the environment for running anything under the engine whose `gate.py` is `engine`.

    Returns:
        a copy of `environ` with PYTHONPATH set to the checkout above the engine package,
        PAPERKIT_ENGINE to the package directory, and PAPERKIT_SCRATCH to TEST_TMPDIR when that is
        set and the scratch is not.

    """
    package_dir = engine.parent
    env = dict(environ)
    env["PYTHONPATH"] = str(package_dir.parent)
    env[ENGINE] = str(package_dir)
    if TEMP in env:
        env.setdefault(SCRATCH, env[TEMP])
    return env


def take(argv: list[str], flag: str) -> tuple[str | None, list[str]]:
    """Split `argv` into the value of a `--flag=` and the rest.

    Returns:
        the flag's value or None, and the arguments without it.

    """
    value = next((a[len(flag) :] for a in argv if a.startswith(flag)), None)
    return value, [a for a in argv if not a.startswith(flag)]
