# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pre-commit gate's suite paths, run in bash rather than read: W184, W361, W502, W509.

Each arm lifts one piece out of `.githooks/pre-commit` by name and RUNS it under the gate's own
`set -euo pipefail`, because both defects were invisible to reading: the W184 line looked like an
assignment and killed the gate, and stale bytecode looks like source until a test imports it.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

_DIST = Path(__file__).parent.parent
_GATE = _DIST.parent / ".githooks" / "pre-commit"
_TARGETS_LINE = re.compile(r"^\s*(failed_targets=\$\(.*)$", re.MULTILINE)
_INFRA_LINE = re.compile(r"^\s*(suite_infra=\$\(.*)$", re.MULTILINE)
_CLEAR_FN = re.compile(r"^clear_bytecode\(\) \{.*?^\}\n", re.DOTALL | re.MULTILINE)
_HOST_PYTEST = re.compile(
    r"^\s*git_scrubbed env -C \"\$root/\$dist\" .*-m pytest -q( .*)?$", re.MULTILINE
)
_CLEAR_CALL = 'clear_bytecode "$root/$dist"'
# A stand-in for `.venv/bin/python3 -m pytest`: it collects `tests/test_*.py` less every
# `--ignore=`, and is red when a collected file raises. Hermetic under bazel, where the
# sandbox's interpreter has no pytest to hand a child process.
_FAKE_PYTEST = (
    "#!/bin/sh\n"
    "for f in tests/test_*.py; do\n"
    '  case " $* " in *"/d/$f "*) continue ;; esac\n'
    '  if grep -q AssertionError "$f"; then echo "FAILED $f"; exit 1; fi\n'
    "done\n"
)
_HOST_BLOCK = re.compile(
    r'^[ ]*clear_bytecode "\$root/\$dist"\n.*?(?=^done$)', re.DOTALL | re.MULTILINE
)
_STUBS = (
    "say() { printf '%s\\n' \"$1\" >&2; }\n"
    'git_scrubbed() { "$@"; }\n'
    'run_checked() { shift; if "$@" >&2; then :; else fail=1; fi; }\n'
)
_SURVIVED = "survived"


def _bash(script: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", "-c", "set -euo pipefail\n" + script],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    )


def _targets_line() -> str:
    match = _TARGETS_LINE.search(_GATE.read_text(encoding="utf-8"))
    assert match, f"{_GATE.name}: no `failed_targets=$(...)` line in the suite refusal"
    return match.group(1)


def test_suite_refusal_naming_no_target_reaches_the_record(tmp_path: Path) -> None:
    """A red suite whose log names no `//target` (0 tests executed) survives to record_refusal."""
    (tmp_path / ".suite.log").write_text(
        "ERROR: analysis of target failed\nExecuted 0 out of 0 tests\n", encoding="utf-8"
    )
    script = f'staged="$PWD"\n{_targets_line()}\nprintf "{_SURVIVED}:[%s]" "$failed_targets"\n'
    proc = _bash(script, tmp_path)
    assert proc.returncode == 0, f"the gate died before its record (rc={proc.returncode})"
    assert proc.stdout == f"{_SURVIVED}:[]"


def test_suite_refusal_still_names_its_failing_target(tmp_path: Path) -> None:
    """The other arm: a log naming `//pkg:t FAILED` still yields that label for the refusal."""
    (tmp_path / ".suite.log").write_text("//pkg:t   FAILED in 1.0s\n", encoding="utf-8")
    script = f'staged="$PWD"\n{_targets_line()}\nprintf "%s" "$failed_targets"\n'
    proc = _bash(script, tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "//pkg:t"


_IO_LOG = (
    "ERROR: /x/hooks/BUILD.bazel:47:12: Testing //hooks:test_cmdparse failed: I/O exception "
    "during sandboxed execution: input dependency /x/y.py was modified during execution\n"
    "ERROR: Build did NOT complete successfully\n"
    "Executed 3 out of 4 tests: 3 tests pass.\n"
)


def test_suite_refusal_names_the_target_of_an_error_line(tmp_path: Path) -> None:
    """W507: an ERROR line naming `//t` with no FAILED summary row still names `//t`."""
    (tmp_path / ".suite.log").write_text(_IO_LOG, encoding="utf-8")
    match = _INFRA_LINE.search(_GATE.read_text(encoding="utf-8"))
    assert match, f"{_GATE.name}: no `suite_infra=$(...)` line in the suite refusal"
    script = (
        f'staged="$PWD"\n{_targets_line()}\n{match.group(1)}\n'
        'printf "%s|%s" "$failed_targets" "$suite_infra"\n'
    )
    proc = _bash(script, tmp_path)
    assert proc.returncode == 0, proc.stderr
    targets, infra = proc.stdout.split("|")
    assert targets.strip() == "//hooks:test_cmdparse"
    assert "infrastructure fault" in infra
    assert "retry" in infra


def test_bytecode_is_cleared_and_the_venv_is_kept(tmp_path: Path) -> None:
    """clear_bytecode removes a distribution's __pycache__ and leaves its .venv's alone."""
    fn = _CLEAR_FN.search(_GATE.read_text(encoding="utf-8"))
    assert fn, f"{_GATE.name}: no clear_bytecode() function"
    stale = tmp_path / "src" / "pkg" / "__pycache__" / "mod.cpython-314.pyc"
    kept = tmp_path / ".venv" / "lib" / "__pycache__" / "dep.cpython-314.pyc"
    for pyc in (stale, kept):
        pyc.parent.mkdir(parents=True)
        pyc.write_bytes(b"stale")
    proc = _bash(f'{fn.group(0)}clear_bytecode "$PWD"\n', tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert not stale.parent.exists(), "the distribution's stale bytecode survived"
    assert kept.is_file(), "the venv's bytecode was removed with the distribution's"


def test_host_pytest_runs_after_the_bytecode_is_cleared() -> None:
    """In the per-distribution loop, the clear comes before the host pytest it protects."""
    gate = _GATE.read_text(encoding="utf-8")
    launch = _HOST_PYTEST.search(gate)
    assert launch, f"{_GATE.name}: the host pytest launch is not where this arm looks"
    clear = gate.rfind(_CLEAR_CALL, 0, launch.start())
    assert clear != -1, f"no `{_CLEAR_CALL}` before the host pytest"
    loop = gate.rfind("\nfor dist in ", 0, launch.start())
    assert loop < clear, "the clear is outside the loop that runs the host pytest"


def test_an_untracked_test_file_does_not_decide_the_commit(tmp_path: Path) -> None:
    """W502: the host pytest leaves out a test file the index does not hold, and names it."""
    gate = _GATE.read_text(encoding="utf-8")
    fn = _CLEAR_FN.search(gate)
    block = _HOST_BLOCK.search(gate)
    assert fn, f"{_GATE.name}: no clear_bytecode() function"
    assert block, f"{_GATE.name}: no host-pytest block from the clear to its loop's end"
    tests = tmp_path / "d" / "tests"
    tests.mkdir(parents=True)
    (tests / "test_staged.py").write_text("def test_ok() -> None:\n    pass\n", encoding="utf-8")
    (tests / "test_untracked.py").write_text(
        "def test_red() -> None:\n    raise AssertionError\n", encoding="utf-8"
    )
    venv_py = tmp_path / "d" / ".venv" / "bin" / "python3"
    venv_py.parent.mkdir(parents=True)
    venv_py.write_text(_FAKE_PYTEST, encoding="utf-8")
    venv_py.chmod(0o755)
    git = shutil.which("git")
    assert git, "no git on PATH"
    for argv in (["init", "-q"], ["add", "d/tests/test_staged.py"]):
        subprocess.run([git, *argv], cwd=tmp_path, check=True, capture_output=True)
    script = (
        f'{_STUBS}{fn.group(0)}fail=0\nroot="$PWD"\ntools="$PWD"\ndist=d\n{block.group(0)}'
        'printf "fail=%s" "$fail"\n'
    )
    proc = _bash(script, tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "fail=0", f"an untracked test decided the commit: {proc.stderr}"
    assert "d/tests/test_untracked.py" in proc.stderr, "the left-out file was not named"


def test_a_tracked_test_with_unstaged_edits_refuses_the_commit(tmp_path: Path) -> None:
    """W509: a staged-red test made green only in the working tree refuses, and is named."""
    gate = _GATE.read_text(encoding="utf-8")
    fn = _CLEAR_FN.search(gate)
    block = _HOST_BLOCK.search(gate)
    assert fn, f"{_GATE.name}: no clear_bytecode() function"
    assert block, f"{_GATE.name}: no host-pytest block from the clear to its loop's end"
    tests = tmp_path / "d" / "tests"
    tests.mkdir(parents=True)
    edited = tests / "test_edited.py"
    edited.write_text("def test_red() -> None:\n    raise AssertionError\n", encoding="utf-8")
    venv_py = tmp_path / "d" / ".venv" / "bin" / "python3"
    venv_py.parent.mkdir(parents=True)
    venv_py.write_text(_FAKE_PYTEST, encoding="utf-8")
    venv_py.chmod(0o755)
    git = shutil.which("git")
    assert git, "no git on PATH"
    for argv in (["init", "-q"], ["add", "d/tests/test_edited.py"]):
        subprocess.run([git, *argv], cwd=tmp_path, check=True, capture_output=True)
    edited.write_text("def test_ok() -> None:\n    pass\n", encoding="utf-8")
    script = (
        f'{_STUBS}{fn.group(0)}fail=0\nroot="$PWD"\ntools="$PWD"\ndist=d\n{block.group(0)}'
        'printf "fail=%s" "$fail"\n'
    )
    proc = _bash(script, tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "fail=1", f"the working tree's copy decided the commit: {proc.stderr}"
    assert "d/tests/test_edited.py" in proc.stderr, "the unstaged test was not named"
