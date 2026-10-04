# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `wheel`: the wheel names exactly the planted package, and install copies it."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from mikemol.pkgbuild import wheel

_PYPROJECT = """\
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "demo-dist"
version = "0.0.1"

[tool.setuptools]
packages = ["demo"]
"""


def _plant(root: Path) -> Path:
    """Write the tiny source tree under `root`.

    Returns:
        The planted pyproject.toml path.

    """
    (root / "demo").mkdir(parents=True)
    (root / "demo" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "ignored.py").write_text("NOT_PACKAGED = 1\n", encoding="utf-8")
    pyproject = root / "pyproject.toml"
    pyproject.write_text(_PYPROJECT, encoding="utf-8")
    return pyproject


def _built(tmp_path: Path) -> Path:
    """Build the planted project's wheel.

    Returns:
        The wheel's path.

    """
    pyproject = _plant(tmp_path / "src")
    out = tmp_path / "out.whl"
    wheel.build(str(out), str(pyproject))
    return out


def test_build_wheel_names_the_planted_package_and_its_dist_info(tmp_path: Path) -> None:
    """The built wheel carries the declared package and one dist-info, and nothing else."""
    with zipfile.ZipFile(_built(tmp_path)) as z:
        names = set(z.namelist())
    assert "demo/__init__.py" in names
    assert "demo_dist-0.0.1.dist-info/METADATA" in names
    assert "demo_dist-0.0.1.dist-info/WHEEL" in names
    assert not any(n.startswith("ignored") for n in names)
    assert {n.split("/")[0] for n in names} == {"demo", "demo_dist-0.0.1.dist-info"}


def test_build_leaves_no_build_dir_and_restores_the_cwd(tmp_path: Path) -> None:
    """The build removes setuptools' `build/` at both ends and puts the cwd back."""
    before = Path.cwd()
    _built(tmp_path)
    assert Path.cwd() == before
    assert not (tmp_path / "src" / "build").exists()


def test_build_removes_a_stale_build_dir_so_a_removed_package_cannot_ride_along(
    tmp_path: Path,
) -> None:
    """A `build/lib` left from an earlier build does not leak into the next wheel."""
    pyproject = _plant(tmp_path / "src")
    stale = tmp_path / "src" / "build" / "lib" / "ghost"
    stale.mkdir(parents=True)
    (stale / "__init__.py").write_text("", encoding="utf-8")
    out = tmp_path / "out.whl"
    wheel.build(str(out), str(pyproject))
    with zipfile.ZipFile(out) as z:
        assert not any(n.startswith("ghost") for n in z.namelist())


def test_install_copies_the_wheel_into_a_venv_and_marks_it_complete(tmp_path: Path) -> None:
    """Install extracts real files into site-packages and returns the venv's python path."""
    whl = _built(tmp_path)
    venv_dir = tmp_path / "cellvenv"
    python = wheel.install(str(venv_dir), str(whl))
    assert python == str(venv_dir.resolve() / "bin" / "python")
    assert (venv_dir / ".pk-complete").is_file()
    sites = list(venv_dir.glob("lib/python*/site-packages"))
    assert len(sites) == 1
    installed = sites[0] / "demo" / "__init__.py"
    assert installed.read_text(encoding="utf-8") == "VALUE = 1\n"
    assert not installed.is_symlink()


def test_install_reuses_a_complete_venv_instead_of_rebuilding_it(tmp_path: Path) -> None:
    """A second install over a complete venv leaves the first one's files untouched."""
    whl = _built(tmp_path)
    venv_dir = tmp_path / "cellvenv"
    wheel.install(str(venv_dir), str(whl))
    sentinel = venv_dir / "sentinel"
    sentinel.write_text("kept", encoding="utf-8")
    wheel.install(str(venv_dir), str(whl))
    assert sentinel.read_text(encoding="utf-8") == "kept"


def test_install_names_each_staged_dependency_root_once_in_a_pth(tmp_path: Path) -> None:
    """Dependency paths under `/site-packages/` become one root each in `_pydeps.pth`."""
    whl = _built(tmp_path)
    dep = tmp_path / "hub" / "pkg" / "site-packages"
    dep.mkdir(parents=True)
    venv_dir = tmp_path / "cellvenv"
    wheel.install(
        str(venv_dir),
        str(whl),
        str(dep / "alpha" / "__init__.py"),
        str(dep / "beta" / "__init__.py"),
        str(tmp_path / "not-a-staged-root.py"),
    )
    pth = next(venv_dir.glob("lib/python*/site-packages/_pydeps.pth"))
    assert pth.read_text(encoding="utf-8") == f"{dep.resolve()}\n"


def test_main_build_writes_the_wheel(tmp_path: Path) -> None:
    """`main(["build", out, pyproject])` is the CLI spelling of `build` and returns 0."""
    pyproject = _plant(tmp_path / "src")
    out = tmp_path / "cli.whl"
    assert wheel.main(["build", str(out), str(pyproject)]) == 0
    assert zipfile.is_zipfile(out)


def test_main_install_prints_the_python_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`main(["install", ...])` writes the venv's python path and a newline to stdout."""
    whl = _built(tmp_path)
    venv_dir = tmp_path / "cellvenv"
    assert wheel.main(["install", str(venv_dir), str(whl)]) == 0
    assert capsys.readouterr().out == f"{venv_dir.resolve() / 'bin' / 'python'}\n"


@pytest.mark.parametrize(
    "argv",
    [[], ["build"], ["build", "only-one"], ["install", "only-one"], ["frobnicate", "a", "b"]],
)
def test_main_refuses_arguments_that_fit_no_command(argv: list[str]) -> None:
    """Wrong or missing arguments end in SystemExit carrying the usage text."""
    with pytest.raises(SystemExit) as refused:
        wheel.main(argv)
    assert "Usage:" in str(refused.value)
