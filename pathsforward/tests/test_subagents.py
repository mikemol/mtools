# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A subagent is running when its transcript is fresh and does not end its turn (W2038).

⚑ THE RECORDS ARE THE MEASURED ONES: `<session>/subagents/agent-<id>.jsonl`, a finished agent's last
record carrying `toolEndsTurn` true; and `--reviewing` is honoured only for a name listed there.
"""

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from mikemol.pathsforward import cli, model, store, subagents

Rec = dict[str, object]


def _agent(session: Path, name: str, records: list[Rec], age_s: float) -> None:
    folder = session.with_suffix("") / "subagents"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"agent-{name}.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    then = time.time() - age_s
    os.utime(path, (then, then))


def test_a_fresh_unfinished_agent_is_running_and_an_ended_or_stale_one_is_not(
    tmp_path: Path,
) -> None:
    """Only the agent whose last record lacks the end mark and whose file is fresh is listed."""
    session = tmp_path / "s1.jsonl"
    _agent(session, "live", [{"type": "assistant"}], 10)
    _agent(session, "done", [{"toolEndsTurn": True}], 10)
    _agent(session, "dead", [{"type": "assistant"}], subagents.LIVE_S + 60)
    assert subagents.running(session, time.time()) == ["agent-live"]
    assert subagents.running(tmp_path / "none.jsonl", time.time()) == []


def _ctx(tmp_path: Path, opts: Rec) -> cli.Ctx:
    return cli.Ctx(opts=opts, path=tmp_path / "paths-forward.json", now=datetime.now(UTC))


def _ready_state() -> model.State:
    card: Rec = {
        "symbol": "W1",
        "title": "t",
        "status": "ready",
        "enables": [],
        "touches": [],
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }
    doc: Rec = {"counter": 1, "project_root": "/x", "waypoints": [card], "residue": []}
    return model.validate(doc)


def test_a_close_idles_for_a_reviewer_only_when_the_transcript_lists_it_as_running(
    tmp_path: Path,
) -> None:
    """A listed reviewer accepts the refused close; an unlisted one or no transcript does not."""
    state = _ready_state()
    refused = cli.CLOSE_JUDGE(state, None, None, "W1", store.sibling(tmp_path / "x", store.LEDGER))
    assert refused.refused
    session = tmp_path / "s1.jsonl"
    _agent(session, "rev", [{"type": "assistant"}], 1)
    opts: Rec = {"reviewing": "agent-rev", "transcript": str(session)}
    accepted = cli.review_wait(_ctx(tmp_path, opts), state, refused)
    assert not accepted.refused
    assert accepted.note == "reviewing agent-rev"
    other: Rec = {"reviewing": "agent-zzz", "transcript": str(session)}
    assert cli.review_wait(_ctx(tmp_path, other), state, refused).refused
    bare: Rec = {"reviewing": "agent-rev"}
    assert cli.review_wait(_ctx(tmp_path, bare), state, refused).refused
    unnamed: Rec = {"transcript": str(session)}
    assert cli.review_wait(_ctx(tmp_path, unnamed), state, refused).refused
