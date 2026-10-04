# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mem_db`: a real sqlite store of cell peaks, raise-never-lower, queried back."""

from __future__ import annotations

import json
import time
from contextlib import closing
from typing import TYPE_CHECKING, cast

from mikemol.memres import mem_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    import pytest

_MB = 1024 * 1024
_USAGE = 2


def _store(tmp_path: Path, rows: list[mem_db.Row], run: str = "") -> Path:
    """Build a store under a not-yet-existing directory and record `rows` into it.

    Returns:
        The database path.

    """
    db = tmp_path / "nested" / "mem.sqlite"
    with closing(mem_db.connect(db)) as conn:
        mem_db.record(conn, rows, run=run)
    return db


def _scalar(conn: sqlite3.Connection, sql: str) -> object:
    """Run a one-value query.

    Returns:
        The first column of the first row.

    """
    return cast("tuple[object]", conn.execute(sql).fetchone())[0]


def test_connect_creates_the_directory_the_schema_and_wal_mode(tmp_path: Path) -> None:
    """The store appears with its `peak` table, in WAL mode, under a directory made on demand."""
    db = tmp_path / "a" / "b" / "mem.sqlite"
    with closing(mem_db.connect(db)) as conn:
        assert _scalar(conn, "SELECT name FROM sqlite_master WHERE type='table'") == "peak"
        assert _scalar(conn, "PRAGMA journal_mode") == "wal"
        assert _scalar(conn, "SELECT count(*) FROM peak") == 0
    assert db.is_file()


def test_record_returns_the_rows_offered_and_stores_them(tmp_path: Path) -> None:
    """The count is the rows offered; each lands under its project, resolution, claim and cell."""
    db = tmp_path / "mem.sqlite"
    rows: list[mem_db.Row] = [
        ("p", "file", "a", "a__calc", 10 * _MB),
        ("p", "def", "a", "a__s1", 20 * _MB),
    ]
    with closing(mem_db.connect(db)) as conn:
        assert mem_db.record(conn, rows, run="r1") == len(rows)
        assert _scalar(conn, "SELECT count(*) FROM peak WHERE run='r1'") == len(rows)
        assert _scalar(conn, "SELECT bytes FROM peak WHERE cell='a__s1'") == 20 * _MB


def test_record_raises_a_peak_but_never_lowers_it(tmp_path: Path) -> None:
    """A re-measure that is higher replaces the peak and its run; a lower one changes nothing."""
    db = tmp_path / "mem.sqlite"
    cell: mem_db.Row = ("p", "file", "a", "a__calc", 100 * _MB)
    with closing(mem_db.connect(db)) as conn:
        mem_db.record(conn, [cell], run="r1")
        mem_db.record(conn, [("p", "file", "a", "a__calc", 50 * _MB)], run="r2")
        assert _scalar(conn, "SELECT bytes FROM peak") == 100 * _MB
        assert _scalar(conn, "SELECT run FROM peak") == "r1"
        mem_db.record(conn, [("p", "file", "a", "a__calc", 200 * _MB)], run="r3")
        assert _scalar(conn, "SELECT bytes FROM peak") == 200 * _MB
        assert _scalar(conn, "SELECT run FROM peak") == "r3"
        assert _scalar(conn, "SELECT count(*) FROM peak") == 1


def test_manifest_is_the_pow2_default_per_resolution_plus_the_overrides(tmp_path: Path) -> None:
    """A claim's worst cell is its number; the resolution default is the max over its claims."""
    db = _store(
        tmp_path,
        [
            ("p", "file", "a", "a__calc", 100 * _MB),
            ("p", "file", "b", "b__calc", 10 * _MB),
            ("p", "def", "c", "c__s1", 1000 * _MB),
            ("p", "def", "c", "c__s2", 3000 * _MB),
            ("other", "file", "z", "z__calc", 4000 * _MB),
        ],
    )
    with closing(mem_db.connect(db)) as conn:
        assert mem_db.manifest(conn, "p") == {"file": 128, "def": 4096, "claims": {"b": 16}}
        assert mem_db.manifest(conn, "other") == {"file": 4096, "claims": {}}


def test_manifest_of_a_project_with_no_observations_has_empty_claims(tmp_path: Path) -> None:
    """No rows means exactly a claims object that is itself empty."""
    db = _store(tmp_path, [("p", "file", "a", "a__calc", _MB)])
    with closing(mem_db.connect(db)) as conn:
        assert mem_db.manifest(conn, "nobody") == {"claims": {}}


def test_provenance_says_what_the_bucket_rests_on(tmp_path: Path) -> None:
    """Cell count, extremes in MB, latest time and distinct runs are reported."""
    before = int(time.time())
    db = _store(
        tmp_path,
        [("p", "file", "a", "a__calc", 10 * _MB), ("p", "file", "b", "b__calc", 30 * _MB)],
        run="r1",
    )
    with closing(mem_db.connect(db)) as conn:
        mem_db.record(conn, [("p", "def", "c", "c__s1", 5 * _MB + _MB // 2)], run="r2")
        found = mem_db.provenance(conn, "p")
    measured_at = found.pop("measured_at")
    assert found == {"cells": 3, "min_mb": 5.5, "max_mb": 30.0, "runs": 2}
    assert isinstance(measured_at, int)
    assert before <= measured_at <= int(time.time())


def test_provenance_of_an_unknown_project_is_all_zero_and_unmeasured(tmp_path: Path) -> None:
    """With no rows the counts are 0 and `measured_at` is None, never a fabricated time."""
    db = _store(tmp_path, [])
    with closing(mem_db.connect(db)) as conn:
        assert mem_db.provenance(conn, "p") == {
            "cells": 0,
            "min_mb": 0.0,
            "max_mb": 0.0,
            "measured_at": None,
            "runs": 0,
        }


def test_main_prints_the_manifest_or_the_provenance_as_sorted_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`manifest` prints the manifest; any other verb prints the provenance."""
    db = _store(tmp_path, [("p", "file", "a", "a__calc", 100 * _MB)], run="r1")
    assert mem_db.main([str(db), "manifest", "p"]) == 0
    expected: dict[str, object] = {"claims": {}, "file": 128}
    assert capsys.readouterr().out == json.dumps(expected, indent=2, sort_keys=True) + "\n"
    assert mem_db.main([str(db), "provenance", "p"]) == 0
    printed = capsys.readouterr().out
    assert '"cells": 1' in printed
    assert '"max_mb": 100.0' in printed
    assert '"runs": 1' in printed


def test_main_refuses_too_few_arguments_with_a_usage_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Fewer than `<db> <verb> <project>` is exit 2 with usage on stderr and nothing on stdout."""
    assert mem_db.main([]) == _USAGE
    assert mem_db.main(["only-a-db"]) == _USAGE
    captured = capsys.readouterr()
    assert not captured.out
    assert captured.err.count("usage: mem_db.py <db> {manifest|provenance} <project>") == _USAGE
