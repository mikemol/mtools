# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Ask a package index whether each dist's project name is free (W1149, goal W1143).

    mikemol-wheel names ROOT [--index URL]

Every dist is a top-level directory of ROOT holding a `pyproject.toml`; its `[project].name` is
normalized the way an index does (PEP 503: lower case, runs of `-_.` become one `-`) and asked
for at `<index>/<name>/json`. A 404 is `free`; a 200 is `taken` (someone has the name: ours if we
published it, else a collision to settle BEFORE the first upload); anything else is `error` with
the status.

⚑ A READ, NEVER A WRITE: this only issues GET requests, and prints what the index said, one JSON
line per dist. It registers nothing, and a `free` name is not reserved by having been asked.

⚑ THE INDEX IS A PARAMETER (`--index`, default PyPI), so TestPyPI is the same command and the
network is a seam a test replaces. A symlinked directory is not a dist (as in `licenses`).

CONSUMED BY: `mikemol-wheel names`, the naming preflight of the publish (W1149, W1195).
"""

from __future__ import annotations

import http.client
import json
import re
import sys
import tomllib
import urllib.parse
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_INDEX = "https://pypi.org/pypi"
INDEX_FLAG = "--index"
RUNS = re.compile(r"[-_.]+")
FREE = 404
TAKEN = 200
USAGE = 2
Fetch = Callable[[str], int]
Row = dict[str, object]


def normalized(name: str) -> str:
    """Normalize a project name the way an index does (PEP 503).

    Returns:
        the lower-case name with each run of `-`, `_` and `.` as one `-`.

    """
    return RUNS.sub("-", name).lower()


def http_status(url: str) -> int:
    """GET `url` and return the status, reading nothing of the body.

    ⚑ NO WALL-CLOCK TIMEOUT (operator, standing): a request that never answers is a hang to see,
    not a number of seconds to guess.

    Returns:
        the HTTP status.

    """
    parts = urllib.parse.urlsplit(url)
    secure = parts.scheme == "https"
    connection = (
        http.client.HTTPSConnection(parts.netloc)
        if secure
        else http.client.HTTPConnection(parts.netloc)
    )
    try:
        connection.request("GET", parts.path, headers={"Accept": "application/json"})
        response = connection.getresponse()
        response.read()
        return response.status
    finally:
        connection.close()


def project_name(dist: Path) -> str | None:
    """Read `[project].name` from a dist's pyproject.

    Returns:
        the name, or None when the file has none or cannot be read.

    """
    try:
        text = (dist / "pyproject.toml").read_text(encoding="utf-8")
        table = cast("dict[str, object]", tomllib.loads(text))
    except (OSError, ValueError):
        return None
    project = table.get("project")
    name = cast("dict[str, object]", project).get("name") if isinstance(project, dict) else None
    return name if isinstance(name, str) else None


def state_of(name: str, index: str, fetch: Fetch) -> str:
    """Ask the index about one normalized name.

    Returns:
        `free`, `taken`, or `error: <why>`.

    """
    try:
        status = fetch(f"{index.rstrip('/')}/{name}/json")
    except OSError as exc:
        return f"error: {type(exc).__name__}: {exc}"
    if status == FREE:
        return "free"
    return "taken" if status == TAKEN else f"error: HTTP {status}"


def run(args: Sequence[str], fetch: Fetch = http_status) -> int:
    """Run `ROOT [--index URL]`: one JSON line per dist.

    Returns:
        0 when every name is free, 1 when one is taken or could not be asked, 2 for a usage error.

    """
    words = list(args)
    index = DEFAULT_INDEX
    if INDEX_FLAG in words:
        place = words.index(INDEX_FLAG)
        if place + 1 >= len(words):
            sys.stderr.write("usage: mikemol-wheel names ROOT [--index URL]\n")
            return USAGE
        index = words[place + 1]
        del words[place : place + 2]
    if len(words) != 1 or not Path(words[0]).is_dir():
        sys.stderr.write("usage: mikemol-wheel names ROOT [--index URL]\n")
        return USAGE
    pending = 0
    for pyproject in sorted(Path(words[0]).glob("*/pyproject.toml")):
        dist = pyproject.parent
        if dist.is_symlink():
            continue
        declared = project_name(dist)
        name = normalized(declared) if declared else None
        state = state_of(name, index, fetch) if name else "error: no [project].name"
        row: Row = {"dist": dist.name, "name": name, "state": state}
        sys.stdout.write(json.dumps(row, sort_keys=True) + "\n")
        pending += int(state != "free")
    return 1 if pending else 0
