# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the stage runner: a gate stage imports the pinned engine (mtools:W896).

⚑ gcalculus:W222: five of its gcalc leaves import paperkit's `labelmap`, which only the engine's
environment provides. The stage script must run UNCHANGED under that environment, with its own
arguments and exit status, and an input that is not declared is a refusal, never a lookup.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import engine_stage_main

if TYPE_CHECKING:
    from pathlib import Path

_RECORD = "STAGE_PROBE_RECORD"
_SCRIPT = (
    "import os, sys\n"
    "lines = [os.environ.get('PAPERKIT_ENGINE', ''), os.environ.get('PYTHONPATH', ''),\n"
    "         *sys.argv[1:]]\n"
    "with open(os.environ['STAGE_PROBE_RECORD'], 'w', encoding='utf-8') as out:\n"
    "    out.write('\\n'.join(lines))\n"
    "raise SystemExit(int(os.environ.get('STAGE_PROBE_EXIT', '0')))\n"
)
_REFUSED = 2
_RED = 5


def _tree(tmp_path: Path) -> tuple[Path, Path]:
    """Build a stand-in engine and a stage script; return the engine's gate.py and the script.

    Returns:
        the paths of `<checkout>/paperkit/gate.py` and the stage script.

    """
    package = tmp_path / "checkout" / "paperkit"
    package.mkdir(parents=True)
    (package / "gate.py").write_text("", encoding="utf-8")
    script = tmp_path / "stage.py"
    script.write_text(_SCRIPT, encoding="utf-8")
    return package / "gate.py", script


def _run(argv: list[str], record: Path, code: int = 0) -> int:
    os.environ[_RECORD] = str(record)
    os.environ["STAGE_PROBE_EXIT"] = str(code)
    try:
        return engine_stage_main.main(argv)
    finally:
        del os.environ[_RECORD]
        del os.environ["STAGE_PROBE_EXIT"]


def test_the_script_runs_with_the_engine_environment_and_its_own_arguments(
    tmp_path: Path,
) -> None:
    """The arguments after `--` reach the script verbatim, under the engine's variables."""
    gate, script = _tree(tmp_path)
    record = tmp_path / "record.txt"
    code = _run([f"--engine={gate}", f"--script={script}", "--", "--quiet", "x y"], record)
    engine, pythonpath, *argv = record.read_text(encoding="utf-8").split("\n")
    assert code == 0
    assert argv == ["--quiet", "x y"]
    assert engine == str(gate.parent)
    assert pythonpath == str(gate.parent.parent)


def test_the_scripts_exit_status_passes_through(tmp_path: Path) -> None:
    """A red stage is a red test."""
    gate, script = _tree(tmp_path)
    argv = [f"--engine={gate}", f"--script={script}"]
    assert _run(argv, tmp_path / "record.txt", _RED) == _RED


def test_no_arguments_after_the_separator_is_fine(tmp_path: Path) -> None:
    """A stage with no args of its own runs with an empty argv."""
    gate, script = _tree(tmp_path)
    record = tmp_path / "record.txt"
    assert _run([f"--engine={gate}", f"--script={script}"], record) == 0
    assert record.read_text(encoding="utf-8").split("\n")[2:] == []


def test_a_missing_flag_or_an_undeclared_input_is_a_refusal(tmp_path: Path) -> None:
    """Exit 2 and nothing run, when either input is absent."""
    gate, script = _tree(tmp_path)
    assert engine_stage_main.main([f"--engine={gate}"]) == _REFUSED
    assert engine_stage_main.main([f"--script={script}"]) == _REFUSED
    missing = tmp_path / "nowhere.py"
    assert engine_stage_main.main([f"--engine={gate}", f"--script={missing}"]) == _REFUSED
    assert engine_stage_main.main([f"--engine={missing}", f"--script={script}"]) == _REFUSED
