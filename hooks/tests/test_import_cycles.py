# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Every module of mikemol.hooks imports first, alone, in a fresh interpreter (mtools:W1280).

⚑ AN IMPORT CYCLE DEPENDS ON WHICH MODULE IS ENTERED FIRST, so one interpreter importing them all
(or a suite whose earlier tests already loaded the chain) cannot see it. `revendor_cli` failed with
`cannot import name 'run_revendor'` for any consumer that imported it before `repin_cli`, and
nothing here noticed for weeks: the console script entered through `repin_cli`, which works.
Summit's witness imports every module of the installed package and found it. So each module gets its
own interpreter, started with nothing imported, and must import without an error.

⚑ THE CONTROL IS A PLANTED CYCLE: two temporary modules that import each other's names must FAIL
this same check, so a green result is a statement about the modules and not about a check that
passes everything.
"""

from __future__ import annotations

import os
import pkgutil
import subprocess
import sys
from typing import TYPE_CHECKING

import mikemol.hooks as hooks_package

if TYPE_CHECKING:
    from pathlib import Path

_MINIMUM = 50


def _modules() -> list[str]:
    return sorted(
        f"mikemol.hooks.{found.name}" for found in pkgutil.iter_modules(hooks_package.__path__)
    )


def _fresh(name: str, extra: Path | None = None) -> tuple[int, str]:
    """Import `name` in a new interpreter that has imported nothing else of the package.

    Returns:
        the exit code and standard error of that import.

    """
    paths = [*sys.path, *([str(extra)] if extra is not None else [])]
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(paths), "PYTHONDONTWRITEBYTECODE": "1"}
    done = subprocess.run(
        [sys.executable, "-c", f"import {name}"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return done.returncode, done.stderr


def test_every_module_of_the_package_imports_first_in_a_fresh_interpreter() -> None:
    """No module fails to import when it is the first one entered."""
    modules = _modules()
    assert len(modules) > _MINIMUM
    results = {name: _fresh(name) for name in modules}
    failed = {name: err.strip().splitlines()[-1:] for name, (code, err) in results.items() if code}
    assert not failed


def test_a_planted_import_cycle_fails_the_same_check(tmp_path: Path) -> None:
    """The control: a imports a name from b and b one from a; entering either first fails."""
    (tmp_path / "cyc_a.py").write_text("from cyc_b import b_name\na_name = 1\n", encoding="utf-8")
    (tmp_path / "cyc_b.py").write_text("from cyc_a import a_name\nb_name = 2\n", encoding="utf-8")
    code, err = _fresh("cyc_a", tmp_path)
    assert code != 0
    assert "circular import" in err
    clean = tmp_path / "plain.py"
    clean.write_text("value = 1\n", encoding="utf-8")
    assert _fresh("plain", tmp_path)[0] == 0
