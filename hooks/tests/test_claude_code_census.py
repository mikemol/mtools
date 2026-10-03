# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.hooks.claude_code_census` (W464): no untracked code under `.claude/`.

⚑ Every GIT_* variable is removed before the decoy is built, so nothing inherited (the pre-commit
gate exports GIT_INDEX_FILE) can point a probe at a real repository.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import claude_code_census

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_untracked_python_under_claude_is_an_offender() -> None:
    """An untracked `.claude/design/probe.py` is reported."""
    assert claude_code_census.offenders([".claude/design/probe.py"]) == [".claude/design/probe.py"]


def test_untracked_rego_and_shell_under_claude_are_offenders() -> None:
    """`.rego` and `.sh` under `.claude/` are code too."""
    paths = [".claude/x.rego", ".claude/swarm3/run.sh"]
    assert claude_code_census.offenders(paths) == paths


def test_a_worktree_checkout_is_not_an_offender() -> None:
    """The harness's `.claude/worktrees/<name>/` is a checkout of the repo, not `.claude/` code."""
    assert claude_code_census.offenders([".claude/worktrees/wf_1/hooks/src/x.py"]) == []


def test_a_worktrees_own_claude_dir_is_an_offender() -> None:
    """A worktree's own `.claude/tool.py` is still code under `.claude/`."""
    path = ".claude/worktrees/wf_1/.claude/tool.py"
    assert claude_code_census.offenders([path]) == [path]


def test_notes_and_code_outside_claude_are_not_offenders() -> None:
    """Notes under `.claude/` and code elsewhere pass."""
    paths = [".claude/design/notes.md", "hooks/src/claude.py", "not.claude/x.py"]
    assert claude_code_census.offenders(paths) == []


def test_report_refuses_and_names_each_offender(capsys: pytest.CaptureFixture[str]) -> None:
    """The report exits 1 and names the offender, not the note beside it."""
    assert claude_code_census.report([".claude/p.py", ".claude/n.md"]) == 1
    err = capsys.readouterr().err
    assert ".claude/p.py" in err
    assert ".claude/n.md" not in err


def test_report_passes_on_a_clean_census() -> None:
    """The report exits 0 when nothing under `.claude/` is code."""
    assert claude_code_census.report([".claude/n.md"]) == 0


def test_untracked_lists_ignored_and_unignored_files_but_not_tracked_ones(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The census population is every untracked `.claude/` file, gitignored or not."""
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    git = shutil.which("git")
    assert git is not None
    repo = tmp_path / "decoy"
    subprocess.run([git, "init", "--quiet", str(repo)], check=True)
    claude = repo / ".claude"
    (claude / "design").mkdir(parents=True)
    (repo / ".gitignore").write_text(".claude/design/\n", encoding="utf-8")
    for rel in ("design/hidden.py", "loose.sh", "kept.py"):
        (claude / rel).write_text("", encoding="utf-8")
    (repo / "outside.py").write_text("", encoding="utf-8")
    subprocess.run([git, "-C", str(repo), "add", ".claude/kept.py"], check=True)
    assert sorted(claude_code_census.untracked(str(repo))) == [
        ".claude/design/hidden.py",
        ".claude/loose.sh",
    ]
