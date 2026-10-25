# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A new file is judged under its real module name, so a mypy override applies to it (W1628).

⚑ THE CONTROLS RUN THE REAL MYPY on a scratch `src` layout whose parent `ns` is a PEP 420 namespace
(no `__init__.py`), as the dists in this tree are: a new file with an override is clean, the same
bytes under a module with NO override still fail, and a sibling import resolves through MYPYPATH
and through nothing else (the same file fails without it).
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

from mikemol.hooks import mypy_mirror

if TYPE_CHECKING:
    from pathlib import Path

CONFIG = (
    '[tool.mypy]\nmypy_path = "src"\nexplicit_package_bases = true\nnamespace_packages = true\n\n'
    '[[tool.mypy.overrides]]\nmodule = "ns.pkg.quiet"\nignore_errors = true\n'
)
BAD = "X: int = 'not an int'\n"
SIBLING = "from ns.pkg import other\n\nZ: int = other.Y\n"


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    (project / "src" / "ns" / "pkg").mkdir(parents=True)
    (project / "src" / "ns" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (project / "src" / "ns" / "pkg" / "other.py").write_text("Y: int = 1\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(CONFIG, encoding="utf-8")
    return project


def _run(project: Path, name: str, content: str, *, with_path: bool = True) -> int:
    new = project / "src" / "ns" / "pkg" / name
    with mypy_mirror.mirrored(str(new), content, project / "pyproject.toml") as mirror:
        assert mirror is not None
        env = {**os.environ}
        env.pop("MYPYPATH", None)
        if with_path:
            env["MYPYPATH"] = mirror.mypy_path
        argv = [sys.executable, "-m", "mypy", "--config-file", str(project / "pyproject.toml")]
        done = subprocess.run(
            [*argv, "--no-error-summary", mirror.subject],
            cwd=mirror.root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    return done.returncode


def test_only_a_new_file_under_a_config_with_overrides_needs_a_mirror(tmp_path: Path) -> None:
    """The house path is unchanged: an existing file or a config with no overrides is skipped."""
    project = _project(tmp_path)
    config = project / "pyproject.toml"
    new = str(project / "src" / "ns" / "pkg" / "quiet.py")
    assert mypy_mirror.needed(new, config)
    assert not mypy_mirror.needed(str(project / "src" / "ns" / "pkg" / "other.py"), config)
    config.write_text("[tool.mypy]\nstrict = true\n", encoding="utf-8")
    assert not mypy_mirror.needed(new, config)
    assert not mypy_mirror.needed(new, project / "missing.toml")


def test_the_mirror_copies_the_projects_shape_and_is_removed(tmp_path: Path) -> None:
    """Bytes at the real relative path, an __init__ only where the project has one, gone after."""
    project = _project(tmp_path)
    new = str(project / "src" / "ns" / "pkg" / "quiet.py")
    with mypy_mirror.mirrored(new, BAD, project / "pyproject.toml") as mirror:
        assert mirror is not None
        base = mirror.root / "src" / "ns" / "pkg"
        assert (base / "quiet.py").read_text(encoding="utf-8") == BAD
        assert (base / "__init__.py").is_file()
        assert not (mirror.root / "src" / "ns" / "__init__.py").exists()
        assert mirror.subject == "src/ns/pkg/quiet.py"
        assert mirror.mypy_path.split(os.pathsep) == [
            str(project.resolve()),
            str(project.resolve() / "src"),
        ]
        root = mirror.root
    assert not root.exists()


def test_a_path_outside_the_project_has_no_mirror(tmp_path: Path) -> None:
    """The caller falls back to the old staged copy rather than guessing a place."""
    project = _project(tmp_path)
    outside = str(tmp_path / "elsewhere.py")
    with mypy_mirror.mirrored(outside, BAD, project / "pyproject.toml") as mirror:
        assert mirror is None


def test_the_override_applies_to_the_new_file_and_only_to_it(tmp_path: Path) -> None:
    """The quiet file is clean, the same bytes as loud are refused, a sibling import resolves."""
    project = _project(tmp_path)
    assert _run(project, "quiet.py", BAD) == 0
    assert _run(project, "loud.py", BAD) == 1
    assert _run(project, "uses.py", SIBLING) == 0
    assert _run(project, "uses.py", SIBLING, with_path=False) == 1


def test_judged_changes_nothing_for_an_existing_file_or_a_config_without_overrides(
    tmp_path: Path,
) -> None:
    """The house path: the same command, the same directory, and no subject to rewrite."""
    project = _project(tmp_path)
    config = project / "pyproject.toml"
    command = ["python", "-m", "mypy", "x.py"]
    existing = str(project / "src" / "ns" / "pkg" / "other.py")
    with mypy_mirror.judged(command, tmp_path, existing, BAD, config) as got:
        assert got == (command, tmp_path, "")
    new = str(project / "src" / "ns" / "pkg" / "quiet.py")
    with mypy_mirror.judged(command, tmp_path, new, BAD, None) as got:
        assert got == (command, tmp_path, "")


def test_judged_runs_a_new_file_from_the_mirror_with_mypypath_in_front(tmp_path: Path) -> None:
    """The subject becomes the real relative path, run from the mirror, wrapped in env."""
    project = _project(tmp_path)
    new = str(project / "src" / "ns" / "pkg" / "quiet.py")
    command = ["python", "-m", "mypy", "--pretty", str(tmp_path / "staged.py")]
    with mypy_mirror.judged(command, tmp_path, new, BAD, project / "pyproject.toml") as got:
        wrapped, cwd, shown = got
        assert wrapped[0] == "env"
        assert wrapped[1].startswith("MYPYPATH=")
        assert wrapped[2:-1] == command[:-1]
        assert wrapped[-1] == shown == "src/ns/pkg/quiet.py"
        assert (cwd / shown).read_text(encoding="utf-8") == BAD
        mirror_root = cwd
    assert not mirror_root.exists()
