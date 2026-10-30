# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A scratch restore keeps what a queued stack carries for a file; HEAD's restore drops it (W2099).

⚑ A REAL GIT AND A REAL LEDGER: the blob is written with `git hash-object -w`, the snapshot with
`stacksnap.dump` and the live map with `commit_counts.transition`, the readings `mikemol-commit`
itself makes. The control is the same path restored from HEAD, which gives the bytes the stack
changed away.
"""

from pathlib import Path

import pytest

from mikemol.hooks import commit_counts, scratch, scratch_cli, scratch_restore, stacksnap
from mikemol.hooks.stacksnap import Frozen

_KEY = "1000"
_MODE = "100644"
_FILE = "tests/x.py"
_IDENT = ("-c", "user.name=t", "-c", "user.email=t@example.invalid")


def _git(repo: Path, *argv: str) -> str:
    code, text = scratch.git_out(["git", *_IDENT, "-C", str(repo), *argv])
    assert code == 0, text
    return text.strip()


def _repo(tmp_path: Path) -> tuple[Path, Path, str]:
    # A repo whose HEAD holds `head`, plus a live stack that froze `stack` for the same file.
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    (repo / _FILE).write_text("head\n", encoding="utf-8")
    _git(repo, "add", _FILE)
    _git(repo, "commit", "-q", "-m", "one")
    (repo / _FILE).write_text("stack\n", encoding="utf-8")
    blob = _git(repo, "hash-object", "-w", _FILE)
    _git(repo, "checkout", "--", _FILE)
    ledger = repo / ".git" / "mtools"
    ledger.mkdir()
    stacksnap.dump(ledger / f"stack-{_KEY}.snap", [[Frozen(_FILE, _MODE, blob)]])
    commit_counts.transition(ledger / "commit.counts", _KEY, commit_counts.QUEUED)
    return repo, ledger, blob


def test_the_frozen_bytes_come_back_where_a_head_restore_gives_the_old_ones(tmp_path: Path) -> None:
    """The stack changed x.py to `stack`; HEAD holds `head`; the restore must give `stack`."""
    repo, ledger, blob = _repo(tmp_path)
    where = tmp_path / "tree"
    where.mkdir()
    assert scratch_restore.frozen_blob(ledger, _KEY, _FILE) == blob
    line = scratch_restore.restore(where, repo, _FILE, blob, scratch.git_out)
    assert (where / _FILE).read_text(encoding="utf-8") == "stack\n"
    assert (repo / _FILE).read_text(encoding="utf-8") == "head\n"
    assert line.startswith(f"restored {_FILE} (blob ")


def test_a_dead_key_a_file_the_stack_never_froze_and_a_deletion_are_refused(
    tmp_path: Path,
) -> None:
    """Nothing to restore from: no such live key, a path outside the snapshot, a blob-less entry."""
    ledger = _repo(tmp_path)[1]
    with pytest.raises(scratch.ScratchError, match="not a live submission"):
        scratch_restore.frozen_blob(ledger, "9999", _FILE)
    with pytest.raises(scratch.ScratchError, match="holds no bytes"):
        scratch_restore.frozen_blob(ledger, _KEY, "tests/other.py")
    stacksnap.dump(ledger / f"stack-{_KEY}.snap", [[Frozen(_FILE, _MODE, "")]])
    with pytest.raises(scratch.ScratchError, match="holds no bytes"):
        scratch_restore.frozen_blob(ledger, _KEY, _FILE)


def test_the_last_entry_of_a_stack_wins_a_file_carried_twice(tmp_path: Path) -> None:
    """A stack of two entries touching one file lands the later entry's bytes."""
    made = _repo(tmp_path)
    ledger, blob = made[1], made[2]
    first = Frozen(_FILE, _MODE, "0" * len(blob))
    stacksnap.dump(ledger / f"stack-{_KEY}.snap", [[first], [Frozen(_FILE, _MODE, blob)]])
    assert scratch_restore.frozen_blob(ledger, _KEY, _FILE) == blob


def test_the_command_restores_into_the_symbols_worktree_and_refuses_a_missing_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`mikemol-scratch restore W5 --as-of-stack KEY --file PATH` writes into the opened tree."""
    repo = _repo(tmp_path)[0]
    environ = {scratch.ROOT_ENV: str(tmp_path / "scratch")}
    args = ["restore", "W5", "--repo", str(repo), "--as-of-stack", _KEY, "--file", _FILE]
    assert scratch_cli.main(args, environ) == scratch_cli.EXIT_REFUSED
    assert "open the scratch tree first" in capsys.readouterr().err
    where = scratch.path_for(tmp_path / "scratch", repo, "W5")
    where.mkdir(parents=True)
    assert scratch_cli.main(args, environ) == scratch_cli.EXIT_OK
    assert (where / _FILE).read_text(encoding="utf-8") == "stack\n"
    assert f"of stack {_KEY}" in capsys.readouterr().out
    bare = ["restore", "W5", "--repo", str(repo)]
    assert scratch_cli.main(bare, environ) == scratch_cli.EXIT_REFUSED
    assert "needs --as-of-stack" in capsys.readouterr().err
