# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Find another distribution's console script by one fixed order, for hooks that shell out to it.

The hooks distribution depends on no other mtools package, so a hook that needs another tool
(`mikemol-debtplan`, `mikemol-buildlog`, `mikemol-paths-forward`) runs its console script as a
subprocess. The order is the same each time, and this is the one place it is written (W818 had it
inline for debtplan; W829 is the second caller): an environment variable naming the binary, then
the project's own venv, then PATH.

⚑ A TOOL THAT IS NOT FOUND IS NONE, NEVER A GUESS: the caller says so or stays silent; it does not
fall back to a different tool.

CONSUMED BY: `pycheck_closure` and `build_failure`.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


def find(name: str, env_var: str, root: Path, env: Mapping[str, str]) -> Path | None:
    """Find the console script `name`: the env override, the project's venv, then PATH.

    Returns:
        the first candidate that is a file, or None.

    """
    named = env.get(env_var)
    candidates = [Path(named)] if named else []
    candidates.append(root / ".venv" / "bin" / name)
    on_path = shutil.which(name)
    if on_path:
        candidates.append(Path(on_path))
    return next((each for each in candidates if each.is_file()), None)
