# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Hooks' own venv is CLOSED: a package outside its declared closure does not import.

⚑⚑ THE PER-DISTRIBUTION ARMS THAT LIVED HERE MOVED (W337). They asserted what venv_from_hub
builds, but each swept every distribution from the repo root, which a repository of its own
cannot do (W317). They are now @mikemol_rules_py's venv_check, which each distribution runs over
its own `.venv` as `//<dist>:venv`: the interpreter link and its PYTHONHOME note, the interpreter
running, the distribution's own package importing, its console scripts running as Python, and its
suite collecting. The population control that guarded those sweeps against an empty glob went with
them.

What stays is hooks' own: its venv must refuse a package its closure does not declare.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# ⚑⚑ NOT `Path(__file__).resolve()`: that follows a runfiles symlink back out to the source tree,
# the escape `test_bar_fires` refuses. The root comes from the working directory, and this arm reads
# a built artifact under `bazel-bin`, so it skips wherever that is absent.
_REPO = Path.cwd()
if not (_REPO / "MODULE.bazel").is_file():
    # Under the gate, pytest runs from the distribution directory rather than the repo root.
    _REPO = _REPO.parent
_HOOKS_PY = _REPO / "bazel-bin" / "hooks" / ".venv" / "bin" / "python3"


def test_a_package_outside_the_declared_closure_does_not_import() -> None:
    """⚑⚑ THE F-ARM, AND THE OBVIOUS VERSION OF IT IS VACUOUS.

    Importing a DECLARED dependency to show the venv does not leak proves nothing — a pass is what
    a correct venv does. Measured, and corrected: the control must be a package the AMBIENT
    interpreter can import and the closure does not carry. `panflute` is mdstruct's dependency and
    is absent from hooks' closure, so hooks' venv must refuse it.

    ⚑ AND WHEN AN F-ARM FIRES, CHECK WHERE IT RESOLVED. An earlier run flagged `pip` as a leak
    until `__file__` showed the hermetic toolchain's own bundled copy rather than the host's.
    """
    if not _HOOKS_PY.is_symlink() and not _HOOKS_PY.is_file():
        pytest.skip("hooks venv is not built in this checkout")

    # ⚑ POSITIVE CONTROL FIRST: a declared package must import, or a refusal below means the
    # interpreter is broken rather than the closure being closed.
    ctrl = subprocess.run(
        [str(_HOOKS_PY), "-c", "import pytest"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert ctrl.returncode == 0, (
        f"control failed: hooks' venv cannot import its declared pytest — "
        f"{ctrl.stderr.strip()[:200]}"
    )

    proc = subprocess.run(
        [str(_HOOKS_PY), "-c", "import panflute"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0, (
        "hooks' venv imported `panflute`, which is mdstruct's dependency and is not in hooks' "
        "declared closure — the venv is reaching outside what MODULE.bazel declares"
    )
