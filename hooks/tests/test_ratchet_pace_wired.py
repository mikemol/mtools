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

from mikemol.hooks import ratchet_pace

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
