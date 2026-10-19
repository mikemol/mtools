# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`observe` runs a command under the Observer and writes the document `annotate` reads."""

from __future__ import annotations

import importlib.util
import json
from typing import TYPE_CHECKING, cast

from mikemol.pycodemod import cli_observe
from mikemol.pycodemod.observed import Signature

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_SOURCE = "def add(a, b):\n    return a + b\n"
_RED = 1


def _caller(root: Path, code: int) -> cli_observe.Run:
    # A stand-in for pytest: import the project's module, call a function, return `code`.
    def run(_args: Sequence[str]) -> int:
        spec = importlib.util.spec_from_file_location("observed_mod", root / "mod.py")
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.add(1, 2)
        return code

    return run


def _project(tmp_path: Path) -> Path:
    (tmp_path / "mod.py").write_text(_SOURCE, encoding="utf-8")
    return tmp_path


def _read(path: Path) -> dict[str, object]:
    return cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8")))


def test_the_document_names_each_function_relative_to_the_root(tmp_path: Path) -> None:
    """Keys are `file::qualname` under the root, types sorted, ready for `annotate --seen`."""
    root = _project(tmp_path)
    out = tmp_path / "seen.json"
    assert cli_observe.observe_run(root, out, [], _caller(root, 0)) == 0
    expected = {"params": {"a": ["int"], "b": ["int"]}, "returns": ["int"]}
    assert _read(out)["mod.py::add"] == expected


def test_a_red_run_still_writes_what_ran_and_returns_its_code(tmp_path: Path) -> None:
    """The types the passing calls showed are kept, and the exit code is the run's own."""
    root = _project(tmp_path)
    out = tmp_path / "seen.json"
    assert cli_observe.observe_run(root, out, [], _caller(root, _RED)) == _RED
    assert "mod.py::add" in _read(out)


def test_a_file_outside_the_root_is_left_out(tmp_path: Path) -> None:
    """An observation from elsewhere would never match a path annotate was given."""
    root = tmp_path / "project"
    root.mkdir()
    document = cli_observe.seen_document({f"{tmp_path}/other.py::f": Signature({}, {"int"})}, root)
    assert document == {}


def test_the_command_line_splits_options_from_the_runner_arguments(tmp_path: Path) -> None:
    """Everything after `--` goes to the runner; a missing option or root is exit 2."""
    root = _project(tmp_path)
    out = tmp_path / "seen.json"
    seen: list[Sequence[str]] = []

    def run(args: Sequence[str]) -> int:
        seen.append(args)
        return 0

    argv = ["--root", str(root), "--out", str(out), "--", "tests/", "-q"]
    assert cli_observe.main(argv, run) == 0
    assert seen == [["tests/", "-q"]]
    assert cli_observe.main(["--out", str(out)], run) == cli_observe.EXIT_USAGE
    missing = ["--root", str(tmp_path / "gone"), "--out", str(out), "--"]
    assert cli_observe.main(missing, run) == cli_observe.EXIT_USAGE
