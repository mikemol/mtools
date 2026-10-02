# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pre-commit gate's suite paths, run in bash rather than read: W184 and W361.

Each arm lifts one piece out of `.githooks/pre-commit` by name and RUNS it under the gate's own
`set -euo pipefail`, because both defects were invisible to reading: the W184 line looked like an
assignment and killed the gate, and stale bytecode looks like source until a test imports it.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

_DIST = Path(__file__).parent.parent
_GATE = _DIST.parent / ".githooks" / "pre-commit"
_TARGETS_LINE = re.compile(r"^\s*(failed_targets=\$\(.*)$", re.MULTILINE)
_CLEAR_FN = re.compile(r"^clear_bytecode\(\) \{.*?^\}\n", re.DOTALL | re.MULTILINE)
_HOST_PYTEST = re.compile(
    r"^\s*git_scrubbed env -C \"\$root/\$dist\" .*-m pytest -q$", re.MULTILINE
)
_CLEAR_CALL = 'clear_bytecode "$root/$dist"'
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
