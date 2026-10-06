# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the pre-commit's `build_failure_cause`: the cause printed, and never a refusal."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

GATE = Path(__file__).parent.parent.parent / ".githooks" / "pre-commit"
BASH = shutil.which("bash") or "bash"
START = "build_failure_cause() {"
SHOWN_LINES = 60
SCRIPT = (
    "set -euo pipefail\n"
    'say() { printf "pre-commit: %s\\n" "$1" >&2; }\n'
    'root="$1"\n'
    "{function}\n"
    'build_failure_cause "$2"\n'
    'echo "after: rc=$?"\n'
)


def _function() -> str:
    """Slice `build_failure_cause` out of the pre-commit, from its header to its closing brace.

    Returns:
        the function's text.

    """
    text = GATE.read_text(encoding="utf-8")
    head = text.index(START)
    return text[head : text.index("\n}\n", head) + 2]


def _run(root: Path, log: Path) -> subprocess.CompletedProcess[str]:
    """Run the function under bash, as the gate's `set -euo pipefail` shell would.

    Returns:
        the finished process, both streams captured.

    """
    script = SCRIPT.replace("{function}", _function())
    return subprocess.run(
        [BASH, "-c", script, "bash", str(root), str(log)],
        capture_output=True,
        text=True,
        check=False,
    )


def _tool(root: Path, body: str) -> None:
    """Install a stub `mikemol-build-failure` that runs `body`."""
    tool = root / "bazel-bin" / "hooks" / ".venv" / "bin" / "mikemol-build-failure"
    tool.parent.mkdir(parents=True)
    tool.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    tool.chmod(0o755)


def test_the_cause_is_printed_indented_and_the_function_returns_zero(tmp_path: Path) -> None:
    """A tool that answers has its output shown, and the gate's shell carries on."""
    _tool(tmp_path, 'echo "resolves out of the runfiles tree"')
    log = tmp_path / "suite.log"
    log.write_text("INFO: invocation/x\n", encoding="utf-8")
    done = _run(tmp_path, log)
    assert "bazel's own account of the failure" in done.stderr
    assert "    resolves out of the runfiles tree" in done.stderr
    assert "after: rc=0" in done.stdout


def test_a_tool_that_finds_no_cause_says_so_and_names_the_command(tmp_path: Path) -> None:
    """An empty answer is stated, never silent, and still returns zero."""
    _tool(tmp_path, "exit 1")
    log = tmp_path / "suite.log"
    log.write_text("no build here\n", encoding="utf-8")
    done = _run(tmp_path, log)
    assert "no BuildBuddy invocation" in done.stderr
    assert "mikemol-buildlog <id> --failures" in done.stderr
    assert "after: rc=0" in done.stdout


def test_a_tool_that_is_not_built_is_said_and_never_stops_the_gate(tmp_path: Path) -> None:
    """With no tool the function names the missing path and returns zero."""
    log = tmp_path / "suite.log"
    log.write_text("", encoding="utf-8")
    done = _run(tmp_path, log)
    assert "is not built" in done.stderr
    assert "after: rc=0" in done.stdout


def test_the_cause_is_bounded_to_sixty_lines(tmp_path: Path) -> None:
    """A tool that answers a thousand lines shows sixty, so the summary is never buried."""
    _tool(tmp_path, "i=0; while [ $i -lt 1000 ]; do echo line-$i; i=$((i+1)); done")
    log = tmp_path / "suite.log"
    log.write_text("x\n", encoding="utf-8")
    done = _run(tmp_path, log)
    shown = [line for line in done.stderr.splitlines() if line.startswith("    line-")]
    assert len(shown) == SHOWN_LINES
    assert "after: rc=0" in done.stdout
