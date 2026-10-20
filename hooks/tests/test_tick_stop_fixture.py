# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The tick-stop reader reads nemik's shared queue fixture and the lock field it uses (W1625).

⚑ ONE OF THE THREE READERS THAT PARSE THE QUEUE (nemik:W519, read 2026-10-18): `tick_stop` asks
`host_lock` who holds the queue's tick lock. Run against the vendored fixture (pinned by blob hash
in W1620), a change to the lock's shape fails here at once instead of reading as 'nobody holds it'
and letting a session end with its lock held.
"""

import json
import shutil
from pathlib import Path
from typing import cast

from mikemol.hooks import host_facts

FIXTURE = Path(__file__).parent / "fixtures" / "queue" / "alpha" / "paths-forward.json"


def _queue(tmp_path: Path) -> Path:
    queue = tmp_path / "paths-forward.json"
    shutil.copyfile(FIXTURE, queue)
    return queue


def _edit(queue: Path, change: dict[str, object]) -> None:
    document = cast("dict[str, object]", json.loads(queue.read_text(encoding="utf-8")))
    document.update(change)
    queue.write_text(json.dumps(document), encoding="utf-8")


def test_the_fixture_has_a_readable_lock_that_nobody_holds(tmp_path: Path) -> None:
    """The positive control: the reader answers a lock, not None, for a queue it can read."""
    lock = host_facts.host_lock(_queue(tmp_path))
    assert lock is not None
    assert not lock.held()


def test_a_lock_record_is_read_with_its_holder_and_time(tmp_path: Path) -> None:
    """The field is read: plant a holder and a taken_at in the fixture's lock."""
    queue = _queue(tmp_path)
    _edit(queue, {"lock": {"holder": "agent-3", "taken_at": "2026-09-19T14:45:02Z"}})
    lock = host_facts.host_lock(queue)
    assert lock is not None
    assert (lock.holder, lock.taken_at) == ("agent-3", "2026-09-19T14:45:02Z")
    assert lock.held()


def test_a_lock_with_no_holder_is_not_held(tmp_path: Path) -> None:
    """A record that names nobody is a lock nobody holds, not a held lock with an empty name."""
    queue = _queue(tmp_path)
    _edit(queue, {"lock": {"taken_at": "2026-09-19T14:45:02Z"}})
    lock = host_facts.host_lock(queue)
    assert lock is not None
    assert not lock.held()


def test_an_unreadable_queue_is_unknown_rather_than_unheld(tmp_path: Path) -> None:
    """None is a different fact from 'nobody holds it': the caller must not read it as free."""
    queue = tmp_path / "paths-forward.json"
    queue.write_text("not json", encoding="utf-8")
    assert host_facts.host_lock(queue) is None
