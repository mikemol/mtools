# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The fleet's commitments are exported as one document of the ruled keys, whole (W2048).

⚑ THE CONTROLS: the sentence, uuid and line never leave; a hyphenated repository keeps its whole
name; a directory outside the root or a repository without a queue is skipped; an unreadable queue
is NAMED, not hidden; and the write leaves the old file or the new one, never a stray temp file.
"""

import io
import json
from pathlib import Path
from typing import cast

from mikemol.transcriptstruct import commitexport
from mikemol.transcriptstruct.cli import main

_SENTENCE = "I still need to attach the warrant, W1931 and keep SENTINEL-WORDS-9d2."
_REPO = "luthen-observability"
_ROWS = 1


def _assistant() -> str:
    message: dict[str, object] = {
        "role": "assistant",
        "model": "claude",
        "content": [{"type": "text", "text": _SENTENCE}],
    }
    envelope: dict[str, object] = {
        "type": "assistant",
        "uuid": "u1",
        "timestamp": "2026-10-26T12:00:00Z",
        "isSidechain": False,
        "message": message,
    }
    return json.dumps(envelope)


def _tree(tmp_path: Path, queue: str | None = '{"waypoints": []}') -> tuple[Path, Path]:
    """Build a root with one repository, its queue and a projects directory with one transcript.

    Returns:
        the projects directory and the root.

    """
    root = tmp_path / "github"
    (root / _REPO / ".claude").mkdir(parents=True)
    if queue is not None:
        (root / _REPO / ".claude" / "paths-forward.json").write_text(queue, encoding="utf-8")
    projects = tmp_path / "projects"
    project = projects / (str(root).replace("/", "-") + "-" + _REPO)
    project.mkdir(parents=True)
    (project / "abc.jsonl").write_text(_assistant() + "\n", encoding="utf-8")
    return projects, root


def test_the_export_holds_only_the_ruled_keys_and_none_of_the_sentence(tmp_path: Path) -> None:
    """A hyphenated repository keeps its name, and the sentence, uuid and line are gone."""
    projects, root = _tree(tmp_path)
    document, unread = commitexport.export(projects, root, "2026-10-26T12:00:00Z")
    rows = cast("list[dict[str, object]]", document["rows"])
    assert unread == []
    assert len(rows) == _ROWS
    assert tuple(rows[0]) == commitexport.EXPORT_KEYS
    assert rows[0]["repo"] == _REPO
    assert rows[0]["session"] == "abc"
    assert "SENTINEL-WORDS" not in json.dumps(document)
    assert document["as_of"] == "2026-10-26T12:00:00Z"


def test_a_directory_outside_the_root_or_without_a_queue_is_skipped_and_a_bad_queue_named(
    tmp_path: Path,
) -> None:
    """Skipped quietly are the strangers; an unreadable queue is listed as unread."""
    projects, root = _tree(tmp_path, queue=None)
    assert commitexport.export(projects, root, "t")[0]["rows"] == []
    (projects / "-elsewhere-x").mkdir()
    assert commitexport.repo_of("-elsewhere-x", root) is None
    projects, root = _tree(tmp_path / "again", queue="{not json")
    document, unread = commitexport.export(projects, root, "t")
    assert document["rows"] == []
    assert unread == [f"{str(root).replace('/', '-')}-{_REPO}/paths-forward.json"]


def test_the_mode_writes_whole_and_leaves_no_temp_file(tmp_path: Path) -> None:
    """`--out` holds the document, its directory holds nothing else, and stdout says the count."""
    projects, root = _tree(tmp_path)
    target = tmp_path / "export" / "commitments.json"
    out = io.StringIO()
    args = [str(projects), "--commitments-tree", "--root", str(root), "--out", str(target)]
    assert main(args, out) == 0
    assert out.getvalue() == "# 1 row(s); 0 unread\n"
    written = cast("dict[str, list[dict[str, object]]]", json.loads(target.read_text("utf-8")))
    assert written["rows"][0]["repo"] == _REPO
    assert [p.name for p in target.parent.iterdir()] == ["commitments.json"]
