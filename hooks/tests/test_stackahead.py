# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The files frozen by the stacks queued AHEAD of a submission (W1746).

⚑ A REAL LEDGER, NO FAKE: snapshots are written with `stacksnap.dump` and the live map with
`commit_counts.transition`, so "ahead" is the same reading `mikemol-commit` makes. The controls are
the ways a snapshot is NOT ahead: a later key, a key that is no longer live, this stack's own, a
deletion, and a torn file.
"""

from pathlib import Path

from mikemol.hooks import commit_counts, stackahead, stacksnap
from mikemol.hooks.stacksnap import Frozen

_MODE = "100644"
_EARLIER = "1000"
_MINE = "2000"
_LATER = "3000"


def _snap(
    ledger: Path,
    key: str,
    *paths: str,
    live: bool = True,
    gone: tuple[str, ...] = (),
    blob: str = "b1",
) -> str:
    # Write `stack-<key>.snap` carrying `paths` as `blob` (and deletions `gone`); `live` puts it in
    # the map.
    entries = [[Frozen(p, _MODE, blob) for p in paths] + [Frozen(g, _MODE, "") for g in gone]]
    snap = ledger / f"stack-{key}.snap"
    stacksnap.dump(snap, entries)
    if live:
        commit_counts.transition(ledger / "commit.counts", key, commit_counts.QUEUED)
    return str(snap)


def test_a_live_stack_with_a_smaller_key_is_ahead_and_a_later_one_is_not(tmp_path: Path) -> None:
    """The witness: the earlier stack's files are named; the later stack's and my own are not."""
    _snap(tmp_path, _EARLIER, "hooks/src/a.py", "hooks/tests/test_a.py")
    mine = _snap(tmp_path, _MINE, "hooks/src/mine.py")
    _snap(tmp_path, _LATER, "hooks/src/later.py")
    assert stackahead.paths(mine) == {"hooks/src/a.py", "hooks/tests/test_a.py"}


def test_a_stack_no_longer_live_a_deletion_or_a_torn_snapshot_names_nothing(
    tmp_path: Path,
) -> None:
    """A finished or withdrawn stack, a removed file and an unreadable snapshot are not ahead."""
    _snap(tmp_path, "0500", "hooks/src/finished.py", live=False)
    _snap(tmp_path, "0600", "hooks/src/kept.py", gone=("hooks/src/removed.py",))
    (tmp_path / "stack-0700.snap").write_text("{not json", encoding="utf-8")
    commit_counts.transition(tmp_path / "commit.counts", "0700", commit_counts.QUEUED)
    mine = _snap(tmp_path, _MINE, "hooks/src/mine.py")
    assert stackahead.paths(mine) == {"hooks/src/kept.py"}


def test_a_shared_file_with_other_bytes_than_the_stack_ahead_is_named(tmp_path: Path) -> None:
    """W2078: built on HEAD's copy, the registry would revert the stack ahead; it is named.

    The control is the same path carrying the stack ahead's own blob (built on its tree), a path
    nobody else holds, and a disjoint stack: none of them is named.
    """
    _snap(tmp_path, _EARLIER, "hooks/mutants.regex", "hooks/src/a.py", blob="theirs")
    mine = _snap(tmp_path, _MINE, "hooks/mutants.regex", "hooks/src/a.py", blob="head")
    assert stackahead.unbuilt_on(mine) == ["hooks/mutants.regex", "hooks/src/a.py"]


def test_a_shared_file_with_the_stack_aheads_own_bytes_is_built_on_it(tmp_path: Path) -> None:
    """Equal blobs mean the stack was built on the ahead stack's tree: nothing is refused."""
    _snap(tmp_path, _EARLIER, "hooks/mutants.regex", blob="theirs")
    same = _snap(tmp_path, _MINE, "hooks/mutants.regex", "hooks/src/mine.py", blob="theirs")
    assert stackahead.unbuilt_on(same) == []


def test_a_disjoint_stack_and_the_newest_of_two_ahead_are_judged_right(tmp_path: Path) -> None:
    """No overlap names nothing; with two stacks ahead the LATER one's blob is the one to match."""
    _snap(tmp_path, "0500", "hooks/graph.json", blob="old")
    _snap(tmp_path, _EARLIER, "hooks/graph.json", blob="new")
    onto_old = _snap(tmp_path, _MINE, "hooks/graph.json", blob="old", live=False)
    assert stackahead.unbuilt_on(onto_old) == ["hooks/graph.json"]
    onto_new = _snap(tmp_path, "2500", "hooks/graph.json", blob="new")
    assert stackahead.unbuilt_on(onto_new) == []
    disjoint = _snap(tmp_path, "2600", "hooks/src/elsewhere.py")
    assert stackahead.unbuilt_on(disjoint) == []


def test_no_snapshot_or_a_file_that_is_not_one_names_nothing(tmp_path: Path) -> None:
    """The empty cases: no snapshot at all, and a name that is not `stack-<digits>`."""
    assert stackahead.paths("") == frozenset()
    assert stackahead.paths(str(tmp_path / "notes.snap")) == frozenset()
    assert stackahead.paths(str(tmp_path / "stack-abc.snap")) == frozenset()
