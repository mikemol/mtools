# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The perturbation-site enumerator, driven on planted engine modules and through real children."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

from mikemol.mutantcell import sites

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_ENGINE_MODULE = (
    "import beta\n"
    "\n"
    'MODE = {"a": 1, "b": 2}\n'
    'KINDS = {"x", "y"}\n'
    "\n"
    "\n"
    "def f(v):\n"
    "    if v:\n"
    "        return 1\n"
    '    return MODE["a"]\n'
)
_EXPECTED = [
    "f",
    "branch:f#0",
    "flip:f#0",
    "data-:MODE#0",
    "dflip:MODE#0",
    "data-:MODE#1",
    "dflip:MODE#1",
    "data-:KINDS#0",
    "data-:KINDS#1",
    "import+:alpha",
]


def _plant(tmp_path: Path, name: str = "mod", text: str = _ENGINE_MODULE) -> Path:
    path = tmp_path / f"{name}.py"
    path.write_text(text, encoding="utf-8")
    return path


def test_every_kind_of_site_is_emitted_in_the_documented_order(tmp_path: Path) -> None:
    """Def, branch, flip, data and import-inject specs come out in that order."""
    path = _plant(tmp_path)
    assert list(sites.sites(path, {"mod", "alpha", "beta"})) == _EXPECTED


def test_a_set_element_has_a_drop_but_no_value_perturbation(tmp_path: Path) -> None:
    """A set contributes a data- spec per element and no dflip."""
    path = _plant(tmp_path)
    out = list(sites.sites(str(path), {"mod"}))
    assert [s for s in out if "KINDS" in s] == ["data-:KINDS#0", "data-:KINDS#1"]


def test_an_already_imported_module_and_the_module_itself_are_not_injected(tmp_path: Path) -> None:
    """Only the engine modules neither imported flat nor equal to the target are injected."""
    path = _plant(tmp_path)
    out = [s for s in sites.sites(path, {"mod", "alpha", "beta", "gamma"}) if "import" in s]
    assert out == ["import+:alpha", "import+:gamma"]


def test_a_module_that_does_not_parse_yields_only_the_injects(tmp_path: Path) -> None:
    """No site can be read from a broken source; every other engine name is still injectable."""
    path = _plant(tmp_path, "broken", "def (:\n")
    assert list(sites.sites(path, {"broken", "other"})) == ["import+:other"]


def test_main_prints_one_tab_separated_line_per_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The line is the path as named, a tab, then the spec; the names are the files' stems."""
    first = _plant(tmp_path, "one", "def g():\n    return 1\n")
    second = _plant(tmp_path, "two", "def h():\n    return 2\n")
    assert sites.main([str(first), str(second)]) == 0
    assert capsys.readouterr().out == (
        f"{first}\tg\n{first}\timport+:two\n{second}\th\n{second}\timport+:one\n"
    )


def test_main_reads_the_process_arguments_when_none_are_given(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without an argv the command line of the process is the input."""
    path = _plant(tmp_path, "solo", "def g():\n    return 1\n")
    monkeypatch.setattr(sys, "argv", ["mikemol-sites", str(path)])
    assert sites.main() == 0
    assert capsys.readouterr().out == f"{path}\tg\n"


def test_the_module_runs_as_a_real_child_and_its_specs_drive_the_mutator(tmp_path: Path) -> None:
    """A child interpreter prints the specs, and the sibling mutator accepts one by module path."""
    path = _plant(tmp_path)
    listed = subprocess.run(
        [sys.executable, "-m", "mikemol.mutantcell.sites", str(path)],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert listed.stdout.splitlines()[0] == f"{path}\tf"
    mutated = subprocess.run(
        [sys.executable, "-m", "mikemol.mutation.mutate", str(path), "flip:f#0"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert "if not (v):" in mutated.stdout
