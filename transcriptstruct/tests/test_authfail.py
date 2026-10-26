# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A session whose turns fail authentication is counted from record metadata alone (W2040).

⚑ THE CONTROLS ARE THE WAYS THIS COUNT CAN LIE OR LEAK: a failed turn followed by a good one is a
recovery and not a tail run, a lookalike without the synthetic model is not a failure, a sentinel
sentence in the content never reaches the output (luthen-observability:W1681: the transcripts hold
the operator's words), and the output names a session and a project, never a path.
"""

import io
import json
from pathlib import Path
from typing import cast

from mikemol.transcriptstruct.cli import main

_SENTINEL = "SENTINEL-OPERATOR-WORDS-7f3a"
_SESSION = "11111111-2222-3333-4444-555555555555"
_PROJECT = "-home-example-project"
_SECOND = 2


def _message(model: str) -> dict[str, object]:
    return {"role": "assistant", "model": model, "content": [{"type": "text", "text": _SENTINEL}]}


def _failed(stamp: str, *, model: str = "<synthetic>") -> str:
    envelope: dict[str, object] = {
        "type": "assistant",
        "uuid": f"u{stamp}",
        "timestamp": stamp,
        "sessionId": _SESSION,
        "error": "authentication_failed",
        "isApiErrorMessage": True,
        "message": _message(model),
    }
    return json.dumps(envelope)


def _good(stamp: str) -> str:
    envelope: dict[str, object] = {
        "type": "assistant",
        "uuid": f"g{stamp}",
        "timestamp": stamp,
        "sessionId": _SESSION,
        "message": _message("claude"),
    }
    return json.dumps(envelope)


def _run(tmp_path: Path, *lines: str) -> tuple[dict[str, object], str]:
    directory = tmp_path / _PROJECT
    directory.mkdir()
    log = directory / "abc.jsonl"
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = io.StringIO()
    assert main([str(log), "--auth-failed"], out) == 0
    return cast("dict[str, object]", json.loads(out.getvalue())), out.getvalue()


def test_two_failed_turns_at_the_tail_are_a_run_labelled_by_session_and_project(
    tmp_path: Path,
) -> None:
    """Two failed turns: failed 2, a run of 2, the newest stamp, a session id and a project."""
    body, text = _run(tmp_path, _good("t0"), _failed("t1"), _failed("t2"))
    assert body == {
        "session": _SESSION,
        "project": _PROJECT,
        "failed": _SECOND,
        "tail_run": _SECOND,
        "newest": "t2",
    }
    assert str(tmp_path) not in text
    assert _SENTINEL not in text


def test_a_recovery_is_not_a_tail_run_and_a_lookalike_is_not_a_failure(tmp_path: Path) -> None:
    """A failed turn then a good one has a run of 0; the same error on a real model is no count."""
    body, _ = _run(tmp_path, _failed("t1"), _good("t2"), _failed("t3", model="claude"))
    assert body["failed"] == 1
    assert body["tail_run"] == 0
