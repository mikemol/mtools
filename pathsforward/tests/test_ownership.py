# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a write keeps the mode, owner and group of what it replaces. W955.

⚑ NO TEST RUNS AS ROOT. The privileged branch is exercised by making `privileged()` answer True and
recording what `shutil.chown` is asked, with a reference file claiming another owner; the mode is
real. The unprivileged run is the control: the same write must not call chown at all.
"""

from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING

from mikemol.pathsforward import ledger, ownership, store

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_OTHER_UID = 12345
_OTHER_GID = 54321
_PRIVATE = 0o640


def _claim_other_owner(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, int, int]]:
    """Pretend to be root, report every file as owned by someone else, and record chowns.

    Returns:
        the list every `shutil.chown` call is appended to, as (file name, uid, gid).

    """
    calls: list[tuple[str, int, int]] = []

    def fake_chown(path: Path, user: int, group: int) -> None:
        calls.append((path.name, user, group))

    def other(path: Path) -> os.stat_result:
        mode = (path if path.exists() else path.parent).stat().st_mode
        return os.stat_result((mode, 0, 0, 1, _OTHER_UID, _OTHER_GID, 0, 0, 0, 0))

    monkeypatch.setattr(ownership, "privileged", lambda: True)
    monkeypatch.setattr(ownership, "reference", other)
    monkeypatch.setattr("shutil.chown", fake_chown)
    return calls


def test_a_replaced_file_keeps_its_mode(tmp_path: Path) -> None:
    """The control for the mode: 0640 stays 0640, where a bare tempfile would leave 0600."""
    target = tmp_path / "q.json"
    target.write_text("{}\n", encoding="utf-8")
    target.chmod(_PRIVATE)
    store.write_atomic(target, "{}\n")
    assert stat.S_IMODE(target.stat().st_mode) == _PRIVATE


def test_a_new_file_gets_the_default_mode(tmp_path: Path) -> None:
    """Readable by the group and others, as the files this writer makes always were."""
    target = tmp_path / "q.json"
    store.write_atomic(target, "{}\n")
    assert stat.S_IMODE(target.stat().st_mode) == ownership.NEW_MODE


def test_an_unprivileged_write_never_asks_to_change_an_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control for the owner: without privilege, chown is not called."""
    calls = _claim_other_owner(monkeypatch)
    monkeypatch.setattr(ownership, "privileged", lambda: False)
    store.write_atomic(tmp_path / "q.json", "{}\n")
    assert calls == []


def test_a_privileged_write_gives_the_replacement_the_owner_it_replaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A root run hands the staged file to the existing owner and group before the rename."""
    calls = _claim_other_owner(monkeypatch)
    target = tmp_path / "q.json"
    target.write_text("{}\n", encoding="utf-8")
    store.write_atomic(target, "{}\n")
    [(name, user, group)] = calls
    assert name.startswith(".q.json.")
    assert (user, group) == (_OTHER_UID, _OTHER_GID)


def test_a_privileged_append_creates_the_file_as_its_directory_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new ledger takes its directory's owner and group; an existing one is left alone."""
    calls = _claim_other_owner(monkeypatch)
    path = tmp_path / "q.ledger"
    ledger.append(path, "first")
    ledger.append(path, "second")
    assert calls == [("q.ledger", _OTHER_UID, _OTHER_GID)]
    assert path.read_text(encoding="utf-8") == "first\nsecond\n"


def test_the_flock_sidecar_is_made_as_its_directory_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The lock file a root run creates must not become root-only."""
    calls = _claim_other_owner(monkeypatch)
    with store.exclusive(tmp_path / "q.json"):
        pass
    assert [name for name, _, _ in calls] == [store.sibling(tmp_path / "q.json", store.FLOCK).name]
