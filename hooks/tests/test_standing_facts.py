# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W238: the facts the standing policy's (b) rules read, gathered before opa runs.

Each fact has a witness (a fixture where it must appear with a known value) and a control (a
fixture where it must be absent), and the launcher is run end to end so a fact gathered here is
proven to reach the policy rather than merely to be computed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import standing_facts
from mikemol.hooks.standing_facts import (
    baseline_lines,
    embargoes,
    gather,
    held_symbols,
    staged_paths,
)

if TYPE_CHECKING:
    import pytest

_DIST = Path(__file__).parent.parent
_LAUNCHER = _DIST / "bin" / "mikemol-hook-standing"
_POLICY = _DIST / "policy" / "standing.rego"
_SRC = Path(standing_facts.__file__).parent.parent.parent


def _queue(path: Path, rows: list[dict[str, str | None]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc: dict[str, list[dict[str, str | None]]] = {"waypoints": rows}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _git(repo: Path, *args: str) -> str:
    git = shutil.which("git") or "git"
    proc = subprocess.run(
        [git, "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "staged.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "loose.py").write_text("y = 1\n", encoding="utf-8")
    _git(repo, "add", "staged.py")
    return repo


def test_held_symbols_are_the_blocked_human_rows(tmp_path: Path) -> None:
    """Only a row blocked on a human is held; agent-blocked and ready rows are not."""
    state = _queue(
        tmp_path / "q.json",
        [
            {"symbol": "W1", "status": "blocked", "blocked_kind": "human"},
            {"symbol": "W2", "status": "blocked", "blocked_kind": "agent"},
            {"symbol": "W3", "status": "ready", "blocked_kind": None},
        ],
    )
    assert held_symbols(state) == ["W1"]


def test_an_unreadable_queue_is_no_fact(tmp_path: Path) -> None:
    """A missing or malformed queue yields no fact rather than an empty hold list."""
    assert held_symbols(tmp_path / "absent.json") is None
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    assert held_symbols(bad) is None


def test_staged_paths_are_absolute_and_exclude_unstaged_files(tmp_path: Path) -> None:
    """The staged fact names the index's files as absolute paths, and not an untracked one."""
    repo = _repo(tmp_path)
    top = _git(repo, "rev-parse", "--show-toplevel").strip()
    assert staged_paths(repo) == [f"{top}/staged.py"]


def test_outside_a_repository_there_is_no_staged_fact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cwd in no git repository yields no staged fact, not an empty one."""
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    assert staged_paths(plain) is None


def test_gather_reads_the_payload_cwd_and_the_project_queue(tmp_path: Path) -> None:
    """Facts come from the payload's cwd (git) and the project's own queue file."""
    repo = _repo(tmp_path)
    project = tmp_path / "project"
    state = _queue(
        project / ".claude" / "paths-forward.json",
        [{"symbol": "W9", "status": "blocked", "blocked_kind": "human"}],
    )
    facts = gather({"cwd": str(repo)}, project)
    assert facts["queue"] == {"path": str(state), "held": ["W9"]}
    staged = facts["staged"]
    assert isinstance(staged, list)
    assert [Path(str(p)).name for p in staged] == ["staged.py"]


def test_a_baseline_write_carries_the_files_current_size(tmp_path: Path) -> None:
    """A Write to the ratchet baseline gathers its non-blank line count; another file does not."""
    baseline = tmp_path / "ratchet-preview.txt"
    keys = ["a:1", "b:2"]
    baseline.write_text("\n\n".join(keys) + "\n", encoding="utf-8")
    write: dict[str, object] = {"tool_name": "Write", "tool_input": {"file_path": str(baseline)}}
    assert gather(write, tmp_path)["target_lines"] == len(keys)
    rubric = str(tmp_path / "rubric.tsv")
    other: dict[str, object] = {"tool_name": "Write", "tool_input": {"file_path": rubric}}
    assert "target_lines" not in gather(other, tmp_path)
    edit: dict[str, object] = {"tool_name": "Edit", "tool_input": {"file_path": str(baseline)}}
    assert "target_lines" not in gather(edit, tmp_path)


def test_an_unwritten_baseline_has_size_zero(tmp_path: Path) -> None:
    """A baseline that does not exist yet measures 0, so any first content is growth."""
    assert baseline_lines(tmp_path / "ratchet-preview.txt") == 0


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "hooks" / "policy").mkdir(parents=True)
    shutil.copyfile(_POLICY, project / "hooks" / "policy" / "standing.rego")
    return project


def _launch(stdin: str, project: Path) -> str:
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(project),
        "STANDING_PYTHON": sys.executable,
        "PYTHONPATH": str(_SRC),
        "OPA_BIN": os.environ.get("OPA_BIN") or shutil.which("opa") or "opa",
    }
    bash = shutil.which("bash") or "bash"
    proc = subprocess.run(
        [bash, str(_LAUNCHER)],
        input=stdin,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout


def _checkout(path: str, repo: Path) -> str:
    command = f"git checkout -- {path}"
    payload: dict[str, str | dict[str, str]] = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(repo),
    }
    return json.dumps(payload)


def test_launcher_feeds_gathered_facts_to_the_policy(tmp_path: Path) -> None:
    """End to end: a staged file's checkout is denied, an unstaged file's is not."""
    repo = _repo(tmp_path)
    project = _project(tmp_path)
    assert "standing 9:" in _launch(_checkout("staged.py", repo), project)
    assert "standing 9:" not in _launch(_checkout("loose.py", repo), project)


def test_launcher_refuses_when_facts_cannot_be_gathered(tmp_path: Path) -> None:
    """A payload the facts step cannot parse is refused, never allowed by an empty decision."""
    out = _launch("not json", _project(tmp_path))
    assert '"permissionDecision": "deny"' in out
    assert "facts" in out


_EMBARGOED = "findings/CENSUS-deps-build-ANALYSIS.md"


def _embargo_queue(project: Path, embargoes: object) -> Path:
    state = project / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    doc: dict[str, object] = {"waypoints": [], "embargoes": embargoes}
    state.write_text(json.dumps(doc), encoding="utf-8")
    return state


def test_embargoes_are_read_from_the_queue_field_as_absolute_paths(tmp_path: Path) -> None:
    """W511: each `embargoes` record reaches the facts with its path made absolute."""
    _embargo_queue(tmp_path, [{"path": _EMBARGOED, "reason": "freeze held", "since": "t"}])
    assert gather({"cwd": str(tmp_path)}, tmp_path)["embargoes"] == [
        {"path": f"{tmp_path}/{_EMBARGOED}", "rel": _EMBARGOED, "reason": "freeze held"}
    ]


def test_a_queue_without_the_field_reads_as_no_embargo(tmp_path: Path) -> None:
    """W511: a readable queue with no `embargoes` is a reading of none: an empty list."""
    _queue(tmp_path / ".claude" / "paths-forward.json", [])
    assert embargoes(tmp_path / ".claude" / "paths-forward.json", tmp_path) == []


def test_an_unreadable_queue_or_malformed_field_is_no_embargo_fact(tmp_path: Path) -> None:
    """W511: a missing queue, or a field that is not a list of records, is absent, not empty."""
    assert "embargoes" not in gather({"cwd": str(tmp_path)}, tmp_path)
    state = _embargo_queue(tmp_path, "findings/x.md")
    assert embargoes(state, tmp_path) is None
    _embargo_queue(tmp_path, [{"path": "", "reason": "r"}])
    assert embargoes(state, tmp_path) is None


def test_launcher_denies_an_edit_to_an_embargoed_path(tmp_path: Path) -> None:
    """W511 end to end: the queue's embargo reaches rule 6; another file is not denied."""
    project = _project(tmp_path)
    _embargo_queue(project, [{"path": _EMBARGOED, "reason": "freeze held", "since": "t"}])

    def edit(name: str) -> str:
        payload: dict[str, object] = {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(project / name)},
            "cwd": str(project),
        }
        return json.dumps(payload)

    assert "standing 6:" in _launch(edit(_EMBARGOED), project)
    assert "standing 6:" not in _launch(edit("findings/other.md"), project)
