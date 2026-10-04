# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The OBSERVATION store (`mem.sqlite`) behind the reservation ladder.

Ported from paperkit's `tools/mem_db.py` (paperkit:W142), behaviour unchanged.

WHY A TABLE AND NOT A JSON OF BUCKETS. `mem.json` stores the CONCLUSION (`{"file": 256}`) and
discards the evidence, so it cannot say where 256 came from, over how many cells, measured when,
or which cell was the outlier. The store keeps one row per OBSERVATION; a manifest is then a QUERY
over it, so the bucketing is a projection rather than a baked-in loss: re-bucketing for a
different ladder or safety factor is a different SELECT, not a re-measurement.

CONCURRENCY IS THE OTHER REASON. Warm-up means many cells depositing peaks as a side effect of
work that runs anyway. `INSERT ... ON CONFLICT DO UPDATE SET bytes = max(...)` is one statement the
database serialises; the JSON equivalent is a read-modify-write across concurrent writers.

Usage:  python -m mikemol.memres.mem_db <db> {manifest|provenance} <project>
"""

from __future__ import annotations

import json
import sqlite3
import sys
import time
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.memres.mem_learn import BYTES_PER_MB, Manifest, pow2

if TYPE_CHECKING:
    from collections.abc import Sequence

type Row = tuple[str, str, str, str, int]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS peak (
  project    TEXT NOT NULL,
  resolution TEXT NOT NULL,          -- 'file' | 'def'
  claim      TEXT NOT NULL,
  cell       TEXT NOT NULL,          -- the action name; a def claim has many
  bytes      INTEGER NOT NULL,
  run        TEXT NOT NULL DEFAULT '',
  at         INTEGER NOT NULL,
  PRIMARY KEY (project, resolution, claim, cell)
);
CREATE INDEX IF NOT EXISTS peak_by_claim ON peak (project, resolution, claim);
"""

_TIMEOUT_S = 30
_ARGC = 3
_MB_DIGITS = 1


def connect(db: Path) -> sqlite3.Connection:
    """Open `db` (creating its directory and schema) in WAL mode.

    Returns:
        An open connection the caller must close.

    """
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db), timeout=_TIMEOUT_S)
    conn.execute("PRAGMA journal_mode=WAL")  # concurrent readers during a harvest
    conn.executescript(_SCHEMA)
    return conn


def record(conn: sqlite3.Connection, rows: Sequence[Row], run: str = "") -> int:
    """Insert observations. MONOTONE per cell: a re-measure may RAISE a peak, never lower it.

    A harvest sees only the cells that happened to run, and a smaller reading is not evidence a
    cell got cheaper. The `max` in the upsert is that rule, enforced by the database.

    Returns:
        The number of rows offered (not the number that changed a stored value).

    """
    now = int(time.time())
    conn.executemany(
        "INSERT INTO peak (project,resolution,claim,cell,bytes,run,at) VALUES (?,?,?,?,?,?,?) "
        "ON CONFLICT(project,resolution,claim,cell) DO UPDATE SET "
        "  bytes = max(bytes, excluded.bytes), run = excluded.run, at = excluded.at "
        "WHERE excluded.bytes > peak.bytes",
        [(p, r, cl, ce, b, run, now) for p, r, cl, ce, b in rows],
    )
    conn.commit()
    return len(rows)


def manifest(conn: sqlite3.Connection, project: str) -> Manifest:
    """Query the reservation manifest, in the shape `mem.json` always had.

    A claim's reservation is the MAX over its cells: a def grid's cells run concurrently and each
    must fit, so the worst cell is the number, not the typical one.

    Returns:
        `{"claims": {}}` when `project` has no rows; else one pow2 default per resolution and
        `claims` holding each claim whose bucket differs from its resolution's default.

    """
    per_claim = cast(
        "list[tuple[str, str, int]]",
        conn.execute(
            "SELECT resolution, claim, max(bytes) FROM peak WHERE project=? "
            "GROUP BY resolution, claim",
            (project,),
        ).fetchall(),
    )
    by_res: dict[str, list[tuple[str, int]]] = {}
    for res, claim, peak_bytes in per_claim:
        by_res.setdefault(res, []).append((claim, pow2(peak_bytes / BYTES_PER_MB)))
    defaults: dict[str, int] = {}
    claims: dict[str, int] = {}
    for res, rows in by_res.items():
        defaults[res] = max(bucket for _, bucket in rows)
        claims.update({claim: bucket for claim, bucket in rows if bucket != defaults[res]})
    return {**defaults, "claims": claims}


def provenance(conn: sqlite3.Connection, project: str) -> dict[str, float | int | None]:
    """Report what a bucket RESTS ON: the question a JSON of conclusions cannot answer.

    Returns:
        `cells`, `min_mb`, `max_mb`, `measured_at` (latest) and `runs` (distinct run ids).

    """
    cells, low, high, at, runs = cast(
        "tuple[int, int | None, int | None, int | None, int]",
        conn.execute(
            "SELECT count(*), min(bytes), max(bytes), max(at), count(DISTINCT run) "
            "FROM peak WHERE project=?",
            (project,),
        ).fetchone(),
    )
    return {
        "cells": cells,
        "min_mb": round((low or 0) / BYTES_PER_MB, _MB_DIGITS),
        "max_mb": round((high or 0) / BYTES_PER_MB, _MB_DIGITS),
        "measured_at": at,
        "runs": runs,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Print the `manifest` or the `provenance` of one project in `<db>` as JSON.

    Returns:
        0 on success; 2 when fewer than `<db> <verb> <project>` were given.

    """
    args = sys.argv[1:] if argv is None else argv
    if len(args) < _ARGC:
        sys.stderr.write("usage: mem_db.py <db> {manifest|provenance} <project>\n")
        return 2
    db, verb, project = Path(args[0]), args[1], args[2]
    with closing(connect(db)) as conn:
        result = manifest(conn, project) if verb == "manifest" else provenance(conn, project)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
