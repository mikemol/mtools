# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the pinned engine's environment and the gate runner that uses it (mtools:W895).

⚑ `paperkit_gate_main` had no test at all while peers' gates ran through it, so extracting the
environment into one function had nothing to hold the behaviour still. These arms pin it first:
the runner against a STAND-IN engine tree (a `paperkit/gate.py` that records what it was given),
then the function on its own.
"""

from __future__ import annotations

import os
from pathlib import Path

import paperkit_gate_main
from engine_env import ENGINE, SCRATCH, TEMP, engine_env

_RECORD = "ENGINE_PROBE_RECORD"
_GATE = (
    "import os, sys\n"
    "lines = [os.getcwd(), os.environ.get('PAPERKIT_ENGINE', ''),\n"
    "         os.environ.get('PYTHONPATH', ''), *sys.argv[1:]]\n"
    "with open(os.environ['ENGINE_PROBE_RECORD'], 'w', encoding='utf-8') as out:\n"
    "    out.write('\\n'.join(lines))\n"
    "raise SystemExit(int(os.environ.get('ENGINE_PROBE_EXIT', '0')))\n"
)
_REFUSED = 2
_RED = 3


def _tree(tmp_path: Path) -> tuple[Path, Path]:
    """Build a stand-in engine checkout and a project; return the engine's gate.py and the toml.

    Returns:
        the paths of `<checkout>/paperkit/gate.py` and `<project>/paper.toml`.

    """
    package = tmp_path / "checkout" / "paperkit"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "gate.py").write_text(_GATE, encoding="utf-8")
    project = tmp_path / "proj"
    project.mkdir()
    toml = project / "paper.toml"
    toml.write_text("[paper]\n", encoding="utf-8")
    return package / "gate.py", toml


def test_pythonpath_is_the_checkout_above_the_package_never_the_package() -> None:
    """The package directory on the path would shadow a check's own config, layout and bib."""
    env = engine_env(Path("/e/checkout/paperkit/gate.py"), {})
    assert env["PYTHONPATH"] == "/e/checkout"
    assert env[ENGINE] == "/e/checkout/paperkit"


def test_the_scratch_is_the_tests_temporary_directory_unless_one_is_given() -> None:
    """TEST_TMPDIR becomes PAPERKIT_SCRATCH; an explicit scratch is kept; none without a source."""
    gate = Path("/e/paperkit/gate.py")
    assert engine_env(gate, {TEMP: "/t"})[SCRATCH] == "/t"
    assert engine_env(gate, {TEMP: "/t", SCRATCH: "/mine"})[SCRATCH] == "/mine"
    assert SCRATCH not in engine_env(gate, {})


def test_the_caller_environment_is_copied_not_changed() -> None:
    """Other variables pass through, and the mapping handed in is left as it was."""
    given = {"KEEP": "1"}
    env = engine_env(Path("/e/paperkit/gate.py"), given)
    assert env["KEEP"] == "1"
    assert given == {"KEEP": "1"}


def test_the_runner_runs_the_gate_from_the_package_with_the_engine_environment(
    tmp_path: Path,
) -> None:
    """The stand-in gate sees the flags, the project directory, the package as cwd and the env."""
    gate, toml = _tree(tmp_path)
    record = tmp_path / "record.txt"
    os.environ[_RECORD] = str(record)
    try:
        code = paperkit_gate_main.main([f"--engine={gate}", f"--project={toml}", "--safe"])
    finally:
        del os.environ[_RECORD]
    cwd, engine, pythonpath, *argv = record.read_text(encoding="utf-8").split("\n")
    assert code == 0
    assert argv == ["--safe", str(toml.parent)]
    assert cwd == str(gate.parent)
    assert engine == str(gate.parent)
    assert pythonpath == str(gate.parent.parent)


def test_the_runners_exit_code_is_the_gates(tmp_path: Path) -> None:
    """A red gate is a red test: the code passes through."""
    gate, toml = _tree(tmp_path)
    os.environ[_RECORD] = str(tmp_path / "record.txt")
    os.environ["ENGINE_PROBE_EXIT"] = str(_RED)
    try:
        code = paperkit_gate_main.main([f"--engine={gate}", f"--project={toml}"])
    finally:
        del os.environ[_RECORD]
        del os.environ["ENGINE_PROBE_EXIT"]
    assert code == _RED


def test_a_missing_flag_or_an_undeclared_input_is_a_refusal(tmp_path: Path) -> None:
    """Exit 2 and nothing run, when an input is absent."""
    gate, toml = _tree(tmp_path)
    assert paperkit_gate_main.main([f"--engine={gate}"]) == _REFUSED
    assert paperkit_gate_main.main([f"--project={toml}"]) == _REFUSED
    missing = tmp_path / "nowhere" / "gate.py"
    assert paperkit_gate_main.main([f"--engine={missing}", f"--project={toml}"]) == _REFUSED
