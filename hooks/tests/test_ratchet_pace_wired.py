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

from mikemol.hooks import admission, ratchet_pace, runproc, stacksnap
from mikemol.hooks.stackfreeze import SNAP_ENV
from mikemol.hooks.stackrun import Item

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


def _landing(path: str, blob: str) -> list[Item]:
    """Make the one item being landed: W1 taking `path` frozen at `blob`.

    Returns:
        the items, as the landing paths hold them.

    """
    return [Item("W1", "s", "", (path,), (stacksnap.Frozen(path, _MODE, blob),))]


def test_the_trailer_names_the_row_only_when_the_pace_needed_it_and_the_row_matches(
    tmp_path: Path,
) -> None:
    """W2312: needed and matched gives the id; a paydown, another blob and no row give None."""
    root, env = _repo(tmp_path)
    row = admission.Row(repo="r", card="W1", blobs={"hooks/x.py": _BLOB})
    now = datetime.now(UTC)
    assert (
        ratchet_pace.admitted_ident(root, _landing("hooks/x.py", _BLOB), env, [row], now) == "r/W1"
    )
    assert (
        ratchet_pace.admitted_ident(root, _landing("hooks/x.py", _OTHER), env, [row], now) is None
    )
    assert ratchet_pace.admitted_ident(root, _landing("hooks/x.py", _BLOB), env, [], now) is None


def test_a_stack_the_pace_would_admit_anyway_never_spends_a_row(tmp_path: Path) -> None:
    """A paydown and a queue-state stack answer None even when a row matches them exactly."""
    root, env = _repo(tmp_path)
    now = datetime.now(UTC)
    paying = admission.Row(repo="r", card="W1", blobs={_RATCHET: _BLOB})
    assert ratchet_pace.admitted_ident(root, _landing(_RATCHET, _BLOB), env, [paying], now) is None
    queue = admission.Row(repo="r", card="W1", blobs={".claude/paths-forward.json": _BLOB})
    landing = _landing(".claude/paths-forward.json", _BLOB)
    assert ratchet_pace.admitted_ident(root, landing, env, [queue], now) is None


def test_an_item_that_was_not_frozen_is_never_admitted(tmp_path: Path) -> None:
    """No frozen files means no blobs to match: a row cannot admit what it cannot read."""
    root, env = _repo(tmp_path)
    row = admission.Row(repo="r", card="W1", blobs={"hooks/x.py": _BLOB})
    unfrozen = [Item("W1", "s", "", ("hooks/x.py",))]
    assert ratchet_pace.admitted_ident(root, unfrozen, env, [row], datetime.now(UTC)) is None


_BIRTH_FILE = "codon-edges-baseline.json"
_RECORD = "bde02714-1533-475a-b934-d2ce58024a15:104181"


def _git(root: Path, *args: str, text: str | None = None) -> str:
    done = runproc.run(["git", "-C", str(root), *args], stdin_text=text)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _entry(record: str) -> str:
    row: dict[str, object] = {
        "ratchet": _BIRTH_FILE,
        "old": 0,
        "new": 3,
        "reason": "birth",
        "warrant": record,
    }
    body: dict[str, object] = {"rebaselines": [row]}
    return json.dumps(body)


def _birth(root: Path, record: str) -> tuple[admission.Row, list[stacksnap.Frozen]]:
    """Make a git repo with one commit, a birth row, and the stack's frozen files.

    Returns:
        the row and the frozen files, the rebaselines blob really stored in the repository.

    """
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "first")
    stored = _git(root, "hash-object", "-w", "--stdin", text=_entry(record))
    files = [
        stacksnap.Frozen(_BIRTH_FILE, _MODE, _BLOB),
        stacksnap.Frozen("rebaselines.json", _MODE, stored),
    ]
    row = admission.Row(
        repo="r",
        card="W1",
        blobs={_BIRTH_FILE: _BLOB, "rebaselines.json": stored},
        kind=admission.BIRTH,
        ratchet=_BIRTH_FILE,
        old=0,
        new=3,
        record=_RECORD,
    )
    return row, files


def test_a_birth_row_admits_only_when_its_accident_checks_pass(tmp_path: Path) -> None:
    """The control, then each accident: another record, and a ratchet file already at HEAD."""
    root, env = _repo(tmp_path)
    row, files = _birth(root, _RECORD)
    landing = [Item("W1", "s", "", (_BIRTH_FILE, "rebaselines.json"), tuple(files))]
    now = datetime.now(UTC)
    assert ratchet_pace.admitted_ident(root, landing, env, [row], now) == "r/W1"
    wrong = _git(root, "hash-object", "-w", "--stdin", text=_entry(_RECORD.replace("1041", "9999")))
    tampered = [files[0], stacksnap.Frozen("rebaselines.json", _MODE, wrong)]
    swapped = admission.Row(
        repo="r",
        card="W1",
        blobs={_BIRTH_FILE: _BLOB, "rebaselines.json": wrong},
        kind=admission.BIRTH,
        ratchet=_BIRTH_FILE,
        old=0,
        new=3,
        record=_RECORD,
    )
    other = [Item("W1", "s", "", (_BIRTH_FILE, "rebaselines.json"), tuple(tampered))]
    assert ratchet_pace.admitted_ident(root, other, env, [swapped], now) is None
    (root / _BIRTH_FILE).write_text("{}", encoding="utf-8")
    _git(root, "add", _BIRTH_FILE)
    _git(root, "commit", "-q", "-m", "second")
    assert ratchet_pace.admitted_ident(root, landing, env, [row], now) is None


def test_a_birth_row_is_judged_at_submit_too_and_never_admitted_without_git(
    tmp_path: Path,
) -> None:
    """The submit refusal asks the accident checks; a root git cannot read admits nothing."""
    root, env = _repo(tmp_path)
    row, files = _birth(root, _RECORD)
    paths = (_BIRTH_FILE, "rebaselines.json")
    stack = _stack(tmp_path, *paths)
    snap = tmp_path / "snapshot.json"
    stacksnap.dump(snap, [files])
    submit_env = {**env, SNAP_ENV: str(snap)}
    assert ratchet_pace.refusal(root, stack, submit_env, [row]) is None
    (root / _BIRTH_FILE).write_text("{}", encoding="utf-8")
    _git(root, "add", _BIRTH_FILE)
    _git(root, "commit", "-q", "-m", "second")
    assert ratchet_pace.refusal(root, stack, submit_env, [row]) is not None
    bare = tmp_path / "bare" / "r"
    (bare / ".claude").mkdir(parents=True)
    (bare / ".claude" / "paths-forward.json").write_text('{"waypoints": []}', encoding="utf-8")
    landing = [Item("W1", "s", "", paths, tuple(files))]
    assert ratchet_pace.admitted_ident(bare, landing, env, [row], datetime.now(UTC)) is None
