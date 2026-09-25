# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The consumer-side launcher: `hooks/adopt/tools-hook`, run as an adopting repo would run it.

⚑ Each arm builds a fake mtools checkout in `tmp_path` and executes the real script with a crafted
harness payload on stdin. The fake venv's `python3` is a tiny script echoing a marker, so the
exec arm is observed rather than inferred.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

_DIST = Path(__file__).parent.parent
_LAUNCHER = _DIST / "adopt" / "tools-hook"
_ENTRY = "mikemol-hook-structural-query"
_MARKER = "FAKE-VENV-RAN"
_VENV_REL = Path("bazel-bin") / "hooks" / ".venv"
_REPAIR_NOTICE = "ALLOWING the build that repairs it"
_TRAVERSAL = "../../x"
_TIMEOUT_S = 30
_EXECUTABLE = 0o755


def _root(tmp_path: Path, *, venv: bool) -> Path:
    """Write a fake mtools checkout, optionally with a built venv.

    Returns:
        the fake MTOOLS_ROOT.

    """
    root = tmp_path / "mtools"
    (root / "hooks").mkdir(parents=True)
    (root / "hooks" / "BUILD.bazel").write_text("# fake\n", encoding="utf-8")
    if venv:
        bindir = root / _VENV_REL / "bin"
        bindir.mkdir(parents=True)
        python = bindir / "python3"
        python.write_text(f'#!/bin/sh\necho {_MARKER} "$@"\n', encoding="utf-8")
        python.chmod(_EXECUTABLE)
        (bindir / _ENTRY).write_text("# entry\n", encoding="utf-8")
    return root


def _install(target: Path) -> Path:
    """Copy the launcher under test to `target`, executable.

    Returns:
        the copy.

    """
    target.write_bytes(_LAUNCHER.read_bytes())
    target.chmod(_EXECUTABLE)
    return target


def _payload(command: str) -> str:
    """Build a PreToolUse Bash payload as the harness serialises it.

    Returns:
        the JSON text.

    """
    tool_input: dict[str, str] = {"command": command}
    record: dict[str, object] = {"tool_name": "Bash", "tool_input": tool_input}
    return json.dumps(record)


def _run(
    launcher: Path,
    entry: str,
    stdin: str,
    root: Path | None,
) -> subprocess.CompletedProcess[str]:
    """Execute the launcher with only PATH and, if given, MTOOLS_ROOT in its environment.

    Returns:
        the finished process.

    """
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    if root is not None:
        env["MTOOLS_ROOT"] = str(root)
    return subprocess.run(
        [str(launcher), entry],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=_TIMEOUT_S,
    )


def _decision(proc: subprocess.CompletedProcess[str]) -> str:
    """Read the harness decision a run emitted, or an empty string when it emitted none.

    Returns:
        the permissionDecision string.

    """
    if not proc.stdout.strip():
        return ""
    parsed: object = json.loads(proc.stdout)
    assert isinstance(parsed, dict)
    inner: object = parsed.get("hookSpecificOutput")
    assert isinstance(inner, dict)
    decision: object = inner.get("permissionDecision")
    assert isinstance(decision, str)
    return decision


def test_a_built_venv_execs_the_entry(tmp_path: Path) -> None:
    """Venv present: the entry is exec'd through the venv's python3."""
    root = _root(tmp_path, venv=True)
    proc = _run(_LAUNCHER, _ENTRY, _payload("ls"), root)
    assert proc.returncode == 0
    assert proc.stdout.startswith(_MARKER), proc.stdout
    assert proc.stdout.rstrip().endswith(f"/bin/{_ENTRY}"), proc.stdout


def test_an_absent_venv_denies(tmp_path: Path) -> None:
    """Venv absent: an ordinary command gets an explicit deny, never a silent exit 0."""
    root = _root(tmp_path, venv=False)
    proc = _run(_LAUNCHER, _ENTRY, _payload("ls"), root)
    assert proc.returncode == 0
    assert _decision(proc) == "deny"
    assert f"env -C {root} bazel build //hooks:.venv" in proc.stdout


def test_the_exact_repair_is_admitted_with_a_notice(tmp_path: Path) -> None:
    """Venv absent: `env -C <root> bazel build //hooks:.venv`, bare or quoted, is admitted."""
    root = _root(tmp_path, venv=False)
    for command in (
        f"env -C {root} bazel build //hooks:.venv",
        f'env -C "{root}" bazel build //hooks:.venv',
    ):
        proc = _run(_LAUNCHER, _ENTRY, _payload(command), root)
        assert proc.returncode == 0
        assert not _decision(proc), (command, proc.stdout)
        assert _REPAIR_NOTICE in proc.stderr


def test_a_consumer_local_build_is_still_denied(tmp_path: Path) -> None:
    """Venv absent: a local build, a wrong root, or a tail appended to the repair is denied."""
    root = _root(tmp_path, venv=False)
    for command in (
        "bazel build //hooks:.venv",
        f"env -C {root} bazel build //hooks:.venv && rm -rf /",
        f"env -C {tmp_path} bazel build //hooks:.venv",
    ):
        proc = _run(_LAUNCHER, _ENTRY, _payload(command), root)
        assert _decision(proc) == "deny", command
        assert _REPAIR_NOTICE not in proc.stderr


def test_an_unusable_root_denies(tmp_path: Path) -> None:
    """MTOOLS_ROOT unset on a copied launcher, or naming a non-checkout, denies naming the fix."""
    copy = _install(tmp_path / "tools-hook")
    for root in (None, tmp_path / "nowhere"):
        proc = _run(copy, _ENTRY, _payload("ls"), root)
        assert proc.returncode == 0
        assert _decision(proc) == "deny", root
        assert "MTOOLS_ROOT" in proc.stdout


def test_a_symlinked_launcher_derives_its_root(tmp_path: Path) -> None:
    """MTOOLS_ROOT unset: a symlink to `<root>/hooks/adopt/tools-hook` resolves that root."""
    root = _root(tmp_path, venv=True)
    (root / "hooks" / "adopt").mkdir()
    shipped = _install(root / "hooks" / "adopt" / "tools-hook")
    link = tmp_path / "consumer-hook"
    link.symlink_to(shipped)
    proc = _run(link, _ENTRY, _payload("ls"), None)
    assert proc.stdout.startswith(_MARKER), proc.stdout


def test_a_traversal_entry_is_refused(tmp_path: Path) -> None:
    """An entry that is not `mikemol-hook-<name>` is denied before it reaches a path."""
    root = _root(tmp_path, venv=True)
    for entry in (_TRAVERSAL, "", "mikemol-hook-x/../../y"):
        proc = _run(_LAUNCHER, entry, _payload("ls"), root)
        assert _decision(proc) == "deny", entry
        assert _MARKER not in proc.stdout
