# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The submit refusal reads the stack file and the named pace file (W1920).

⚑ THE CONTROLS: a stack that lowers nothing is refused, one of queue files alone and one that
touches the owed ratchet are admitted, and a stack file that cannot be read refuses nothing.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mikemol.hooks import admission, ratchet_pace, stacksnap
from mikemol.hooks.stackfreeze import SNAP_ENV

if TYPE_CHECKING:
    from pathlib import Path

_RATCHET = "corpus/exit-baseline.txt"


def _repo(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """Build a repository `r` owing one payable ratchet, its pace file named in an env map.

    Returns:
        the repository root and the environment naming the pace file.

    """
    root = tmp_path / "r"
    (root / ".claude").mkdir(parents=True)
    (root / "corpus").mkdir()
    (root / _RATCHET).write_text("a 1\nb 2\n", encoding="utf-8")
    (root / ".claude" / "paths-forward.json").write_text('{"waypoints": []}', encoding="utf-8")
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = {
        "repo": "r",
        "ratchet": _RATCHET,
        "state": "behind",
        "observed": "0",
        "required": "1",
    }
    head = f'{{"as_of": "{stamp}", "window": "10"}}'
    pace = tmp_path / "pace.json"
    pace.write_text(f"{head}\n{json.dumps(row)}\n", encoding="utf-8")
    return root, {ratchet_pace.ENV: str(pace)}


def _stack(tmp_path: Path, *paths: str) -> Path:
    path = tmp_path / "stack.json"
    entry: dict[str, object] = {"waypoint": "W1", "subject": "s", "paths": list(paths)}
    entries: list[dict[str, object]] = [entry]
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def test_a_stack_that_lowers_nothing_is_refused_and_one_touching_the_ratchet_is_not(
    tmp_path: Path,
) -> None:
    """The stack file's paths are what is judged, against the pace file the env names."""
    root, env = _repo(tmp_path)
    plain = _stack(tmp_path, "hooks/x.py")
    assert ratchet_pace.refusal(root, plain, env) is not None
    paying = _stack(tmp_path, "hooks/x.py", _RATCHET)
    assert ratchet_pace.refusal(root, paying, env) is None


def test_queue_only_and_an_unreadable_stack_file_refuse_nothing(tmp_path: Path) -> None:
    """Queue-state commits are admitted; a missing or torn stack file cannot be judged."""
    root, env = _repo(tmp_path)
    queue = _stack(tmp_path, ".claude/paths-forward.json", ".claude/paths-forward.ledger")
    assert ratchet_pace.refusal(root, queue, env) is None
    assert ratchet_pace.refusal(root, tmp_path / "absent.json", env) is None


_BLOB = "d" * 40
_OTHER = "e" * 40
_MODE = "100644"


def _admitted_stack(tmp_path: Path, blob: str) -> tuple[Path, dict[str, str]]:
    """Write a one-entry stack of hooks/x.py for W1 and its frozen snapshot at `blob`.

    Returns:
        the stack file and the environment naming the snapshot.

    """
    stack = _stack(tmp_path, "hooks/x.py")
    snap = tmp_path / "snapshot.json"
    stacksnap.dump(snap, [[stacksnap.Frozen("hooks/x.py", _MODE, blob)]])
    return stack, {SNAP_ENV: str(snap)}


def test_a_pinned_row_admits_exactly_its_change_on_the_frozen_snapshot(tmp_path: Path) -> None:
    """The control: the row's blob admits; another blob, no row, and no snapshot all refuse."""
    root, env = _repo(tmp_path)
    row = admission.Row(repo="r", card="W1", blobs={"hooks/x.py": _BLOB})
    stack, snap_env = _admitted_stack(tmp_path, _BLOB)
    assert ratchet_pace.refusal(root, stack, {**env, **snap_env}, [row]) is None
    assert ratchet_pace.refusal(root, stack, {**env, **snap_env}) is not None
    assert ratchet_pace.refusal(root, stack, env, [row]) is not None
    other, other_env = _admitted_stack(tmp_path, _OTHER)
    assert ratchet_pace.refusal(root, other, {**env, **other_env}, [row]) is not None


def test_an_unreadable_snapshot_never_admits(tmp_path: Path) -> None:
    """A snapshot the env names that is not there or not a snapshot is no admission."""
    root, env = _repo(tmp_path)
    row = admission.Row(repo="r", card="W1", blobs={"hooks/x.py": _BLOB})
    stack = _stack(tmp_path, "hooks/x.py")
    absent = {**env, SNAP_ENV: str(tmp_path / "absent.json")}
    assert ratchet_pace.refusal(root, stack, absent, [row]) is not None
    torn = tmp_path / "torn.json"
    torn.write_text("{", encoding="utf-8")
    assert ratchet_pace.refusal(root, stack, {**env, SNAP_ENV: str(torn)}, [row]) is not None


def test_the_rows_are_asked_only_for_a_stack_that_would_be_refused(tmp_path: Path) -> None:
    """A paydown or a queue-state stack is admitted without consulting a row."""
    root, _env = _repo(tmp_path)
    pace = tmp_path / "pace.json"
    asked: list[bool] = []

    def spy() -> bool:
        asked.append(True)
        return False

    now = datetime.now(UTC)
    assert ratchet_pace.stack_reason(root, [_RATCHET], now, pace, spy) is None
    queue = [".claude/paths-forward.json"]
    assert ratchet_pace.stack_reason(root, queue, now, pace, spy) is None
    assert not asked
    assert ratchet_pace.stack_reason(root, ["hooks/x.py"], now, pace, spy) is not None
    assert asked == [True]
