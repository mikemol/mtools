# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A stack's own tests run in the sandbox before it can queue, and a failing one refuses it (W2055).

⚑ THE CONTROLS: a stack that names no test file runs nothing, no snapshot tool refuses nothing, a
passing run refuses nothing, and only a test file `<dist>/tests/test_*.py` becomes a target.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import testgate

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

_TARGET = "//hooks:test_x"
_SNAPSHOT = Path("/x/mikemol-snapshot")


def _stack(tmp_path: Path, name: str, *paths: str) -> Path:
    path = tmp_path / name
    entry: dict[str, object] = {"waypoint": "W1", "subject": "s", "paths": list(paths)}
    entries: list[dict[str, object]] = [entry]
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def _find(_root: Path, _env: Mapping[str, str]) -> Path:
    return _SNAPSHOT


def _no_tool(_root: Path, _env: Mapping[str, str]) -> None:
    return None


class _Runs:
    """A recording runner that answers with a fixed status and output."""

    def __init__(self, status: int, out: str = "") -> None:
        self.status = status
        self.out = out
        self.argvs: list[list[str]] = []

    def __call__(self, argv: Sequence[str], _env: Mapping[str, str], _cwd: Path) -> tuple[int, str]:
        self.argvs.append(list(argv))
        return self.status, self.out


def test_only_test_files_become_targets_once_and_in_order() -> None:
    """A test file of a dist is its bazel target; sources, dot-directories and repeats are not."""
    paths = [
        "hooks/src/mikemol/hooks/x.py",
        "hooks/tests/test_x.py",
        "hooks/tests/test_x.py",
        "pathsforward/tests/test_y.py",
        ".claude/tests/test_z.py",
        "hooks/tests/conftest.py",
    ]
    assert testgate.targets_of(paths) == [_TARGET, "//pathsforward:test_y"]


def test_a_failing_target_refuses_with_its_tail_and_the_reproduce_command(tmp_path: Path) -> None:
    """The reason carries bazel's last lines and the one command that reproduces only the run."""
    run = _Runs(3, "one\ntwo\nFAILED //hooks:test_x\n")
    stack = _stack(tmp_path, "tests.json", "hooks/tests/test_x.py")
    reason = testgate.refusal(tmp_path, stack, {}, run, _find)
    assert reason is not None
    assert "FAILED //hooks:test_x" in reason
    assert f"reproduce: bazel test {_TARGET}" in reason
    assert _TARGET in run.argvs[0]


def test_a_snapshot_that_could_not_be_taken_is_not_a_failing_test(tmp_path: Path) -> None:
    """The first real run died in `git add -A` (a scratch file vanished) and refused the stack."""
    stack = _stack(tmp_path, "tests.json", "hooks/tests/test_x.py")
    said = "mikemol-snapshot: /repo: git add -A returned non-zero exit status 128."
    assert testgate.refusal(tmp_path, stack, {}, _Runs(3, said), _find) is None
    assert testgate.refusal(tmp_path, stack, {}, _Runs(3, "FAILED //hooks:test_x"), _find)


def test_a_passing_run_no_test_and_no_snapshot_tool_refuse_nothing(tmp_path: Path) -> None:
    """Quiet in every way the check cannot or need not judge."""
    stack = _stack(tmp_path, "tests.json", "hooks/tests/test_x.py")
    assert testgate.refusal(tmp_path, stack, {}, _Runs(0), _find) is None
    untested = _Runs(1)
    source = _stack(tmp_path, "source.json", "hooks/src/a.py")
    assert testgate.refusal(tmp_path, source, {}, untested, _find) is None
    assert untested.argvs == []
    assert testgate.refusal(tmp_path, stack, {}, untested, _no_tool) is None
    assert untested.argvs == []
