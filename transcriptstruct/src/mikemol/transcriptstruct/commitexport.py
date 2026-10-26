# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The fleet's commitments, as one document a host timer can publish (W2048, W1933).

`commitledger` resolves one transcript's commitments against one queue. A timer needs the whole
fleet at once: every repository that has a transcript directory and a queue, each resolved against
its own queue, as `{as_of, rows}` written whole or not at all.

⚑ THE ROW IS CUT TO THE KEYS THE EXPORT TREE WAS RULED FOR (luthen-observability:W1684): `repo`,
`session`, `at`, `names`, `state`, `layer` and `resolved_by`. The assistant's own sentence (`text`)
and the pointer into a private transcript (`uuid`, `line`) never leave. A key outside this set is a
defect here, because the egress gate removes the whole file on a key it was not built for.
⚑ THE REPOSITORY IS THE PROJECT DIRECTORY'S NAME WITHOUT THE ROOT'S PREFIX, not its last word:
`-home-mikemol-github-luthen-observability` is `luthen-observability`. A directory that is not
under the root, or whose repository has no queue, is skipped, never guessed.
⚑ ONE UNREADABLE QUEUE OR TRANSCRIPT DOES NOT HIDE THE REST, and it is NOT passed over silently:
`unread` names each skipped file, so a caller can say the document is partial.
"""

import json
import os
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from mikemol.transcriptstruct import commitledger
from mikemol.transcriptstruct.commitments import extract as extract_commitments
from mikemol.transcriptstruct.records import read_path

EXPORT_KEYS = ("repo", "session", "at", "names", "state", "layer", "resolved_by")
QUEUE = (".claude", "paths-forward.json")


def cards_of(queue: Path) -> list[dict[str, object]]:
    """Read the waypoint cards of a paths-forward queue file.

    Returns:
        the cards that are objects, in file order.

    """
    doc: object = json.loads(queue.read_text(encoding="utf-8"))
    listed = cast("dict[str, object]", doc).get("waypoints") if isinstance(doc, dict) else None
    items = cast("list[object]", listed) if isinstance(listed, list) else []
    return [cast("dict[str, object]", item) for item in items if isinstance(item, dict)]


def repo_of(project: str, root: Path) -> str | None:
    """Name the repository a project directory stands for.

    Returns:
        the directory's name after the root's own prefix (`/home/m/github` gives
        `-home-m-github-`), or None when the directory is not under the root or names nothing.

    """
    prefix = str(root).replace("/", "-") + "-"
    name = project.removeprefix(prefix) if project.startswith(prefix) else ""
    return name or None


def exported(record: dict[str, object]) -> dict[str, object]:
    """Cut a ledger record to the exported keys.

    Returns:
        the record with only `EXPORT_KEYS`, in that order.

    """
    return {key: record[key] for key in EXPORT_KEYS}


def export(projects: Path, root: Path, as_of: str) -> tuple[dict[str, object], list[str]]:
    """Resolve every repository's transcripts against its own queue.

    Returns:
        the document `{as_of, rows}` and the files that could not be read (transcripts and
        queues), each as `<project>/<name>`, so a partial document says so.

    """
    rows: list[dict[str, object]] = []
    unread: list[str] = []
    for project in sorted(p for p in projects.iterdir() if p.is_dir()):
        repo = repo_of(project.name, root)
        queue = root.joinpath(repo or "", *QUEUE)
        if repo is None or not queue.is_file():
            continue
        try:
            cards = cards_of(queue)
        except (OSError, ValueError):
            unread.append(f"{project.name}/{QUEUE[-1]}")
            continue
        for transcript in sorted(project.glob("*.jsonl")):
            try:
                found = extract_commitments(read_path(transcript), transcript.stem, repo)
            except (OSError, ValueError):
                unread.append(f"{project.name}/{transcript.name}")
                continue
            rows.extend(
                exported(commitledger.record(row)) for row in commitledger.resolve(found, cards)
            )
    return {"as_of": as_of, "rows": rows}, unread


def write_whole(target: Path, document: dict[str, object]) -> None:
    """Write the document so a reader sees all of it or the file as it was.

    The file is made beside its target and renamed over it, so a reader never meets half a
    document, and a failure leaves the old file in place.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(document) + "\n")
        Path(name).replace(target)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise


def summary(document: dict[str, object], unread: Sequence[str]) -> str:
    """Say how many rows the document holds and how many files were not read.

    Returns:
        one line.

    """
    rows = cast("list[object]", document["rows"])
    return f"{len(rows)} row(s); {len(unread)} unread"
