# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`hooks/bin/mikemol-commit`: a stable path to the commit kata, or a refusal naming the repair.

⚑ Each arm runs the real launcher with `MIKEMOL_ROOT` naming a fake checkout in `tmp_path`. The
fake venv's `python3` is a script that prints its argument count and each argument, so what the exec
received is observed rather than inferred (mtools:W796).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

_LAUNCHER = Path(__file__).parent.parent / "bin" / "mikemol-commit"
_EXECUTABLE = 0o755
_TIMEOUT_S = 30
_STUB = '#!/bin/sh\necho "ARGC=$#"\nfor a in "$@"; do echo "ARG=$a"; done\n'
_REFUSED = 1
_ARGS = ("fx", "--waypoint", "W9", "--subject", "a subject")


def _project(tmp_path: Path, *, venv: bool) -> Path:
    """Write a fake checkout, optionally with a built venv whose python3 echoes its argv.

    Returns:
        the fake project directory.

    """
    root = tmp_path / "project"
    root.mkdir()
    if venv:
        bindir = root / "bazel-bin" / "hooks" / ".venv" / "bin"
        bindir.mkdir(parents=True)
        python = bindir / "python3"
        python.write_text(_STUB, encoding="utf-8")
        python.chmod(_EXECUTABLE)
        (bindir / "mikemol-commit").write_text("# entry\n", encoding="utf-8")
    return root


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the real launcher with only PATH and MIKEMOL_ROOT in its environment.

    Returns:
        the finished process.

    """
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "MIKEMOL_ROOT": str(root)}
    return subprocess.run(
        [str(_LAUNCHER), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=_TIMEOUT_S,
    )


def test_every_argument_reaches_the_console_script(tmp_path: Path) -> None:
    """The exec'd script gets the entry path then each argument, none dropped or re-split."""
    proc = _run(_project(tmp_path, venv=True), *_ARGS)
    lines = proc.stdout.splitlines()
    assert lines[0] == f"ARGC={len(_ARGS) + 1}", proc.stdout
    assert lines[1].endswith("/bin/mikemol-commit"), proc.stdout
    assert lines[2:] == [f"ARG={a}" for a in _ARGS], proc.stdout


def test_an_absent_venv_refuses_and_names_the_repair(tmp_path: Path) -> None:
    """No built venv is a NOT COMMITTED line on stderr and exit 1, never a silent success."""
    proc = _run(_project(tmp_path, venv=False), *_ARGS)
    assert proc.returncode == _REFUSED
    assert not proc.stdout
    assert "NOT COMMITTED" in proc.stderr
    assert "bazel build //hooks:.venv" in proc.stderr


def test_a_venv_without_the_console_script_refuses(tmp_path: Path) -> None:
    """A venv built before the script existed (the dev venv's state) is refused the same way."""
    root = _project(tmp_path, venv=True)
    (root / "bazel-bin" / "hooks" / ".venv" / "bin" / "mikemol-commit").unlink()
    proc = _run(root, *_ARGS)
    assert proc.returncode == _REFUSED
    assert "NOT COMMITTED" in proc.stderr
