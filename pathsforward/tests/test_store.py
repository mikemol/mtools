# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the store: refusal of a bad file, atomic replace, and a flock that excludes.

⚑ THE EXCLUSION AND TORN-READ ARMS USE REAL PROCESSES and bounded waits: the survey's torn read
was a second process decoding a file the first was truncate-writing.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from mikemol import pathsforward
from mikemol.pathsforward import store
from mikemol.pathsforward.model import validate

_BLOCKED_S = 1.0
_WAIT_S = 60.0
_WRITES = 200
_PAD = 20000
_OK = 0

_WRITER = """
import json, sys
from pathlib import Path
from mikemol.pathsforward import store
path, writes, pad = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
for i in range(writes):
    doc = {"counter": 0, "waypoints": [], "residue": [], "pad": str(i % 10) * pad}
    store.write_atomic(path, json.dumps(doc))
"""


def _env() -> dict[str, str]:
    """Build a child environment that imports THIS copy of the package first.

    Returns:
        the environment.

    """
    src = str(Path(pathsforward.__file__).resolve().parents[2])
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (src, env.get("PYTHONPATH", "")) if p)
    return env


def _write(path: Path, doc: dict[str, object]) -> Path:
    """Write a document as JSON.

    Returns:
        the path.

    """
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _doc() -> dict[str, object]:
    """Build a minimal document with a key the tool does not know and non-ASCII text.

    Returns:
        the document.

    """
    return {"counter": 1, "goal": "café", "waypoints": [{"symbol": "W1"}], "residue": []}


def test_a_missing_file_is_refused(tmp_path: Path) -> None:
    """A missing state file is refused, naming the path."""
    with pytest.raises(store.UnreadableStateError, match="REFUSED"):
        store.load(tmp_path / "absent.json")


def test_an_unparseable_file_is_refused(tmp_path: Path) -> None:
    """An unparseable state file is refused."""
    path = tmp_path / "s.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(store.UnreadableStateError, match="REFUSED"):
        store.load(path)


def test_a_malformed_file_is_refused(tmp_path: Path) -> None:
    """A structurally malformed state file is refused."""
    with pytest.raises(store.UnreadableStateError, match="not a list"):
        store.load(_write(tmp_path / "s.json", {"counter": 1, "waypoints": "x"}))


def test_a_save_round_trips_every_key(tmp_path: Path) -> None:
    """A save keeps keys the tool does not know, and writes UTF-8 rather than escapes."""
    path = _write(tmp_path / "s.json", _doc())
    store.save(path, store.load(path))
    assert (store.load(path).doc, "café" in path.read_text(encoding="utf-8")) == (_doc(), True)


def test_a_write_replaces_rather_than_truncates(tmp_path: Path) -> None:
    """A write lands as a new inode (temp then replace) and leaves no temp file behind."""
    path = _write(tmp_path / "s.json", _doc())
    before = path.stat().st_ino
    store.save(path, validate(_doc()))
    assert (path.stat().st_ino != before, sorted(p.name for p in tmp_path.iterdir())) == (
        True,
        ["s.json"],
    )


def test_the_siblings_follow_the_state_path(tmp_path: Path) -> None:
    """The mirror, ledger and flock sidecar sit beside the state file."""
    path = tmp_path / "paths-forward.json"
    got = [store.sibling(path, s).name for s in (store.MIRROR, store.LEDGER, store.FLOCK)]
    assert got == ["paths-forward.md", "paths-forward.ledger", "paths-forward.flock"]


def test_the_flock_excludes_another_process(tmp_path: Path) -> None:
    """While the flock is held a locker in another process waits; on release it proceeds."""
    path = _write(tmp_path / "paths-forward.json", {"counter": 0, "waypoints": []})
    with store.exclusive(path):
        child = subprocess.Popen(
            [sys.executable, "-m", "mikemol.pathsforward", "--state", str(path), "--lock", "B"],
            env=_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with pytest.raises(subprocess.TimeoutExpired):
            child.wait(timeout=_BLOCKED_S)
    assert child.wait(timeout=_WAIT_S) == _OK


def test_a_reader_never_sees_a_torn_write(tmp_path: Path) -> None:
    """A reader racing a writer decodes every read; the count of reads is the positive control."""
    path = _write(tmp_path / "s.json", {"counter": 0, "waypoints": [], "residue": []})
    writer = subprocess.Popen(
        [sys.executable, "-c", _WRITER, str(path), str(_WRITES), str(_PAD)], env=_env()
    )
    reads, torn = 0, 0
    while writer.poll() is None:
        try:
            store.load(path)
        except store.UnreadableStateError:
            torn += 1
        reads += 1
    assert (writer.wait(timeout=_WAIT_S), torn, reads > 0) == (_OK, 0, True)
