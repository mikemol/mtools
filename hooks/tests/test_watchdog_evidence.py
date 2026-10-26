# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The watchdog's exit carries what it saw, so a false wake and a real one read differently (W2043).

⚑ THE CONTROLS: the evidence names the last beat's tool and age and the gaps before it; with no
heartbeat it says none was read, and an exit 7 (which watched nothing) carries none.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.hooks import heartbeat, watchdog

if TYPE_CHECKING:
    from pathlib import Path

_S = 1_000_000_000
_RESTART = "restart-command"


def _text(git_dir: Path) -> str:
    body = cast(
        "dict[str, object]",
        json.loads((git_dir / "mtools" / watchdog.LAST_NAME).read_text(encoding="utf-8")),
    )
    return str(body["text"])


def test_the_wake_names_the_last_beat_its_age_and_the_gaps_before_it(tmp_path: Path) -> None:
    """Beats 10 s and 30 s apart, then 900 s of quiet: the text says so."""
    start = 1_000 * _S
    heartbeat.beat(tmp_path, "hook:Read", start)
    heartbeat.beat(tmp_path, "hook:Edit", start + 10 * _S)
    heartbeat.beat(tmp_path, "mikemol-commit", start + 40 * _S)
    now = start + 940 * _S
    seen = watchdog.evidence_of(tmp_path, start + 20 * _S, now)
    assert "This watch began 920s ago." in seen
    assert "The last beat was mikemol-commit, 900s ago" in seen
    assert "newest last: 10, 30." in seen


def test_no_heartbeat_is_said_and_an_exit_seven_carries_no_evidence(tmp_path: Path) -> None:
    """A repo with no beat file says none was read; the cannot-run exit watched nothing."""
    assert watchdog.evidence_of(tmp_path, None, 5 * _S) == "No heartbeat was read."
    heartbeat.beat(tmp_path, "hook:Bash", 1 * _S)
    watchdog.remember_exit(tmp_path, watchdog.EXIT_CANNOT_RUN, _RESTART, 0)
    assert "The last beat" not in _text(tmp_path)
    watchdog.remember_exit(tmp_path, watchdog.EXIT_IDLE, _RESTART, 0)
    assert "The last beat was hook:Bash" in _text(tmp_path)
