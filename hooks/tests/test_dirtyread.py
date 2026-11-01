# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-scratch dirty-map` reads the dirty paths and what carries them (W2104).

⚑ THE CONTROLS: a stack that is not live carries nothing, a scratch tree outside the scratch root is
not a carrier, a git that refuses raises instead of printing a clean map, and a path nothing
carries is counted as only in main.
"""

import json
import os
from collections.abc import Sequence
from pathlib import Path

import pytest

from mikemol.hooks import commit_counts, dirtyread, scratch, scratch_cli, stacksnap
from mikemol.hooks.stacksnap import Frozen

Entry = dict[str, object]

_BLOB = "b" * 40
_MODE = "100644"
_ROOT = Path("/scratch")
_REPO = Path("/repo")
_LISTING = (
    "worktree /repo\nHEAD abc\nbranch refs/heads/main\n\n"
    "worktree /scratch/w9\nHEAD abc\n\n"
    "worktree /elsewhere/w1\nHEAD abc\n\n"
)


def test_only_worktrees_directly_under_the_scratch_root_are_carriers() -> None:
    """The main tree and a tree elsewhere are not scratch trees; w9 is."""
    assert dirtyread.worktrees_under(_LISTING, _ROOT) == {"w9": Path("/scratch/w9")}


def test_a_live_stacks_frozen_paths_are_read_and_a_missing_snapshot_carries_nothing(
    tmp_path: Path,
) -> None:
    """Key 1 froze two files across two entries; key 2 has no snapshot."""
    entries = [[Frozen("a.py", _MODE, _BLOB)], [Frozen("b.py", _MODE, _BLOB)]]
    stacksnap.dump(tmp_path / "stack-1.snap", entries)
    assert dirtyread.stack_paths(tmp_path, ["1", "2"]) == {"1": frozenset({"a.py", "b.py"})}


def test_the_live_keys_are_the_alive_entries_of_the_commit_map(tmp_path: Path) -> None:
    """An entry whose pid runs with its recorded start is live; a stale start is not."""
    me = os.getpid()
    alive: Entry = {"state": "inflight", "pid": me, "start": commit_counts.proc_start(me)}
    stale: Entry = {"state": "queued", "pid": me, "start": "0"}
    mapping: dict[str, Entry] = {"111": alive, "222": stale}
    (tmp_path / "commit.counts").write_text(json.dumps(mapping), encoding="utf-8")
    assert dirtyread.live_keys(tmp_path) == ["111"]
    assert not dirtyread.live_keys(tmp_path / "absent")


class _Git:
    """A canned git: the repository's directory, its worktrees and each tree's status."""

    def __init__(self, gitdir: Path, status: dict[str, str], fail: str = "") -> None:
        self.gitdir = gitdir
        self.status = status
        self.fail = fail

    def __call__(self, argv: Sequence[str]) -> tuple[int, str]:
        verb = argv[3]
        if verb == self.fail:
            return 1, ""
        if verb == "rev-parse":
            return 0, f"{self.gitdir}\n"
        if verb == "worktree":
            return 0, _LISTING
        return 0, self.status[argv[2]]


def _keys(_ledger: Path) -> list[str]:
    return ["1"]


def test_the_map_names_the_stack_the_scratch_tree_and_the_path_only_in_main(
    tmp_path: Path,
) -> None:
    """a.py is in stack 1, c.py in scratch w9, loose.py nowhere, the queue file is excepted."""
    ledger = tmp_path / "mtools"
    ledger.mkdir()
    stacksnap.dump(ledger / "stack-1.snap", [[Frozen("a.py", _MODE, _BLOB)]])
    status = {
        "/repo": " M a.py\n M c.py\n?? loose.py\n M .claude/paths-forward.json\n",
        "/scratch/w9": " M c.py\n",
    }
    out = _Git(tmp_path, status)
    assert dirtyread.dirty_map(_REPO, _ROOT, out, _keys) == [
        "a.py carrier=stack:1",
        "c.py carrier=scratch:w9",
        "loose.py carrier=NONE",
        ".claude/paths-forward.json carrier=excepted:queue",
        "# 4 dirty, 2 carried, 1 excepted, 1 only in main",
    ]


def test_a_git_that_refuses_raises_rather_than_printing_a_clean_map(tmp_path: Path) -> None:
    """A failing status is a ScratchError naming the verb."""
    out = _Git(tmp_path, {"/repo": "", "/scratch/w9": ""}, fail="status")
    with pytest.raises(scratch.ScratchError, match="git status exited 1"):
        dirtyread.dirty_map(_REPO, _ROOT, out, _keys)


def test_the_verb_prints_the_map_and_needs_no_card(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`dirty-map` takes no symbol and prints the rows then the count line."""
    (tmp_path / "mtools").mkdir()
    out = _Git(tmp_path, {"/repo": "?? loose.py\n", "/scratch/w9": ""})
    environ = {scratch.ROOT_ENV: str(_ROOT)}
    argv = ["dirty-map", "--repo", str(_REPO)]
    assert scratch_cli.main(argv, environ, scratch.run_git, out) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[-1] == "# 1 dirty, 0 carried, 0 excepted, 1 only in main"
    assert "loose.py carrier=NONE" in lines
