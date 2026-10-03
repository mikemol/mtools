# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W513: the rule-8 Stop launcher, run end to end.

The decision logic and its fixtures live with the transcript reader
(`transcriptstruct/tests/test_standing_stop.py`); these arms prove the launcher reaches it, and
that a launcher which cannot run fails OPEN with a visible message rather than trapping the turn.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import cast

_DIST = Path(__file__).parent.parent
_ROOT = _DIST.parent
_LAUNCHER = _DIST / "bin" / "mikemol-hook-standing-stop"
_HOLD = "mikemol-paths-forward --update W7 --status blocked --blocked-kind human --next n"


def _payload(tmp_path: Path) -> str:
    rows = [
        {"type": "user", "message": {"role": "user", "content": "go"}},
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "t", "name": "Bash", "input": {"command": _HOLD}}
                ],
            },
        },
    ]
    path = tmp_path / "t.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    body = {"hook_event_name": "Stop", "transcript_path": str(path), "stop_hook_active": False}
    return json.dumps(body)


def _launch(stdin: str, python: str) -> subprocess.CompletedProcess[str]:
    env = {"CLAUDE_PROJECT_DIR": str(_ROOT), "STANDING_PYTHON": python, "PATH": "/usr/bin:/bin"}
    bash = shutil.which("bash") or "/bin/bash"
    return subprocess.run(
        [bash, str(_LAUNCHER)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_the_launcher_blocks_an_unpaired_hold_end_to_end(tmp_path: Path) -> None:
    """The launcher, run on a payload, prints the harness's block JSON naming the card."""
    proc = _launch(_payload(tmp_path), sys.executable)
    out = cast("dict[str, str]", json.loads(proc.stdout))
    assert (proc.returncode, out["decision"], "W7" in out["reason"]) == (0, "block", True)


def test_a_launcher_that_cannot_run_blocks_once(tmp_path: Path) -> None:
    """No interpreter, not yet active: the launcher alone blocks, naming why."""
    proc = _launch(_payload(tmp_path), str(tmp_path / "no-python"))
    out = cast("dict[str, str]", json.loads(proc.stdout))
    assert (proc.returncode, out["decision"], "not checked" in out["reason"]) == (0, "block", True)


def test_a_launcher_that_cannot_run_when_active_ends_the_turn(tmp_path: Path) -> None:
    """No interpreter while already continuing: exit 0, no decision, the reason on stderr."""
    stdin = _payload(tmp_path).replace('"stop_hook_active": false', '"stop_hook_active": true')
    proc = _launch(stdin, str(tmp_path / "no-python"))
    assert (proc.returncode, proc.stdout, "not checked" in proc.stderr) == (0, "", True)
