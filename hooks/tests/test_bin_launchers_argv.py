# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The `hooks/bin` launchers hand their own arguments to the hook they exec (W635).

⚑ Each arm runs the real launcher with `CLAUDE_PROJECT_DIR` naming a fake checkout in `tmp_path`.
The fake venv's `python3` is a script that prints its argument count and each argument, so what the
exec received is observed rather than inferred. The repository's real settings are never read.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

_BIN = Path(__file__).parent.parent / "bin"
_VENV_REL = Path("bazel-bin") / "hooks" / ".venv"
_EXECUTABLE = 0o755
_TIMEOUT_S = 30
_STUB = '#!/bin/sh\necho "ARGC=$#"\nfor a in "$@"; do echo "ARG=$a"; done\n'
_CONTEXT_ONLY: tuple[str, ...] = ("mikemol-hook-inbound-asks", "mikemol-hook-nemik-check")
_GATES: tuple[str, ...] = (
    "mikemol-hook-no-chaining",
    "mikemol-hook-no-verify",
    "mikemol-hook-pycheck",
    "mikemol-hook-shellcheck",
    "mikemol-hook-structural-query",
)
_ALL: tuple[str, ...] = (*_CONTEXT_ONLY, *_GATES)
_FLAG = "--check"
_PAYLOAD = '{"tool_name": "Bash", "tool_input": {"command": "ls"}}'


def _project(tmp_path: Path, entry: str, *, venv: bool) -> Path:
    """Write a fake checkout, optionally with a built venv whose python3 echoes its argv.

    Returns:
        the fake project directory.

    """
    root = tmp_path / "project"
    root.mkdir()
    if venv:
        bindir = root / _VENV_REL / "bin"
        bindir.mkdir(parents=True)
        python = bindir / "python3"
        python.write_text(_STUB, encoding="utf-8")
        python.chmod(_EXECUTABLE)
        (bindir / entry).write_text("# entry\n", encoding="utf-8")
    return root


def _run(entry: str, root: Path, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    """Run the real launcher `entry` with only PATH and CLAUDE_PROJECT_DIR in its environment.

    Returns:
        the finished process.

    """
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "CLAUDE_PROJECT_DIR": str(root)}
    return subprocess.run(
        [str(_BIN / entry), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=_TIMEOUT_S,
    )


def _decision(stdout: str) -> str:
    """Read the harness decision a gate emitted.

    Returns:
        the permissionDecision string.

    """
    parsed: object = json.loads(stdout)
    assert isinstance(parsed, dict)
    inner: object = parsed.get("hookSpecificOutput")
    assert isinstance(inner, dict)
    decision: object = inner.get("permissionDecision")
    assert isinstance(decision, str)
    return decision


@pytest.mark.parametrize("entry", _ALL)
def test_no_arguments_reach_the_hook_when_the_harness_passes_none(
    tmp_path: Path, entry: str
) -> None:
    """Called as the harness calls it, the exec'd hook receives no argument at all."""
    root = _project(tmp_path, entry, venv=True)
    proc = _run(entry, root)
    lines = proc.stdout.splitlines()
    assert lines[0] == "ARGC=1", proc.stdout
    assert lines[1].endswith(f"/bin/{entry}"), proc.stdout


@pytest.mark.parametrize("entry", _ALL)
def test_an_argument_reaches_the_hook(tmp_path: Path, entry: str) -> None:
    """`--check` is passed through after the entry path, so the hook's own argv contract sees it."""
    root = _project(tmp_path, entry, venv=True)
    proc = _run(entry, root, _FLAG)
    lines = proc.stdout.splitlines()
    assert lines[0] == "ARGC=2", proc.stdout
    assert lines[2] == f"ARG={_FLAG}", proc.stdout


@pytest.mark.parametrize("entry", _CONTEXT_ONLY)
def test_an_absent_venv_says_so_on_stderr_and_proceeds(tmp_path: Path, entry: str) -> None:
    """A context hook with no venv exits 0 and says so; it never denies, with or without args."""
    root = _project(tmp_path, entry, venv=False)
    for args in ((), (_FLAG,)):
        proc = _run(entry, root, *args)
        assert proc.returncode == 0
        assert not proc.stdout
        assert "venv is not built" in proc.stderr


@pytest.mark.parametrize("entry", _GATES)
def test_an_absent_venv_denies_a_gate(tmp_path: Path, entry: str) -> None:
    """A gate with no venv answers with an explicit deny, identical with and without args."""
    root = _project(tmp_path, entry, venv=False)
    for args in ((), (_FLAG,)):
        proc = _run(entry, root, *args, stdin=_PAYLOAD)
        assert proc.returncode == 0
        assert _decision(proc.stdout) == "deny"
