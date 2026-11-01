# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The repin reader takes a stack's pins from its frozen snapshot and moves them (W2075, slice 1).

⚑ THE CONTROL IS THE UNTOUCHED LINES: a pyproject that carries ANOTHER CARD'S HUNK comes back with
the pins moved and every other line exactly as frozen, which a reader of the working tree could not
promise. The git runner is a stand-in that serves blobs from a dict, so nothing here reads a tree.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks import repinonto
from mikemol.hooks.stacksnap import DELETION, Frozen, dump

_OLD = "03749d56d55741840da13d86533e7e8d698e3be8"
_NEW = "6868dd2e0b7f4a9c1d2e3f405162738495a6b7c8"
_REPO = "https://github.com/mikemol/mtools.git"
_HUNK = '[tool.ruff.lint.per-file-ignores]\n"tests/*" = ["assert"]\n'
_PYPROJECT = (
    f'dependencies = [\n    "mikemol-hooks @ git+{_REPO}@{_OLD}#subdirectory=hooks",\n]\n\n{_HUNK}'
)
_MODE = "100644"
_FAILED = 128


@dataclass
class _Done:
    returncode: int
    stdout: str
    stderr: str = ""


class _Runner:
    """Serve `git cat-file blob ID` from a dict and remember what was asked, and where."""

    def __init__(self, blobs: Mapping[str, str]) -> None:
        self.blobs = dict(blobs)
        self.calls: list[list[str]] = []
        self.cwds: set[Path] = set()
        self.envs: list[Mapping[str, str]] = []

    def __call__(self, args: Sequence[str], env: Mapping[str, str], cwd: Path) -> _Done:
        self.calls.append(list(args))
        self.cwds.add(cwd)
        self.envs.append(env)
        blob = self.blobs.get(args[-1])
        return _Done(_FAILED, "") if blob is None else _Done(0, blob)


def _snapshot(tmp_path: Path, entries: list[list[Frozen]]) -> Path:
    snap = tmp_path / "stack-1.snap"
    dump(snap, entries)
    return snap


def test_a_frozen_pyproject_is_read_by_entry_and_other_files_are_skipped(tmp_path: Path) -> None:
    """Only pyproject.toml blobs are fetched; a deletion and a source file are never asked for."""
    snap = _snapshot(
        tmp_path,
        [
            [Frozen("a/pyproject.toml", _MODE, "b1"), Frozen("a/src/x.py", _MODE, "b2")],
            [Frozen("b/pyproject.toml", _MODE, DELETION)],
            [Frozen("pyproject.toml", _MODE, "b3")],
        ],
    )
    run = _Runner({"b1": "one", "b2": "two", "b3": "three"})
    got = repinonto.pins_in_snapshot(snap, tmp_path, run)
    assert got == {0: {"a/pyproject.toml": "one"}, 2: {"pyproject.toml": "three"}}
    assert run.calls == [["cat-file", "blob", "b1"], ["cat-file", "blob", "b3"]]
    assert run.cwds == {tmp_path}
    assert run.envs == [{}, {}]


def test_an_unreadable_snapshot_or_blob_reads_as_none_not_empty(tmp_path: Path) -> None:
    """A missing snapshot and a blob git cannot find are failures, never 'no pins'."""
    run = _Runner({})
    assert repinonto.pins_in_snapshot(tmp_path / "absent.snap", tmp_path, run) is None
    snap = _snapshot(tmp_path, [[Frozen("pyproject.toml", _MODE, "gone")]])
    assert repinonto.pins_in_snapshot(snap, tmp_path, run) is None


def test_onto_moves_the_pins_and_keeps_every_other_line_of_the_frozen_text() -> None:
    """Another card's hunk in the same file survives byte for byte beside the moved pin."""
    moved = repinonto.onto({0: {"pyproject.toml": _PYPROJECT}}, _NEW)
    assert moved == {0: {"pyproject.toml": _PYPROJECT.replace(_OLD, _NEW)}}
    assert _HUNK in moved[0]["pyproject.toml"]


def test_onto_reports_only_the_files_whose_pins_changed() -> None:
    """A file already at the target, and one with no pins, are left out."""
    at_target = _PYPROJECT.replace(_OLD, _NEW)
    frozen = {0: {"a/pyproject.toml": at_target, "b/pyproject.toml": _HUNK}}
    assert repinonto.onto(frozen, _NEW) == {}


def test_onto_honours_the_chosen_dists() -> None:
    """A dist not named keeps its pin."""
    assert repinonto.onto({0: {"pyproject.toml": _PYPROJECT}}, _NEW, frozenset({"other"})) == {}


def test_a_key_that_is_not_alive_is_refused_and_a_live_one_is_not() -> None:
    """A finished run's snapshot is never repinned onto."""
    assert "111" in str(repinonto.refusal("111", ["222", "333"]))
    assert repinonto.refusal("222", iter(["111", "222"])) is None
