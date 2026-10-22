# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The gate history is read from the trace store; no answer is None, never empty (W1721).

⚑ NONE IS NOT EMPTY: an empty history would classify every failing step as a regression, so each
way of getting no answer (no emitter, no store, a failed query, a reply with no round of the
repository) is checked to be None, with a reading that does answer as the control.
"""

import json
from pathlib import Path

from mikemol.hooks import commit_span, historyfetch

_ENV = {commit_span.BIN_ENV: "/opt/mikemol-otlp", commit_span.ENDPOINTS_ENV: "/host/e.json"}
_STEP = "hooks: pytest - every case passes"


def _span(start: int, verdict: str, failed: str, repo: str = "mtools") -> str:
    fields = {"verdict": verdict, "failed": failed, "repo": repo}
    record: dict[str, object] = {"name": "train.round", "start_us": start, "fields": fields}
    return json.dumps(record)


def _answer(text: str, status: int = 0) -> historyfetch.Run:
    def run(_argv: list[str], _cwd: Path) -> tuple[int, str]:
        return status, text

    return run


def test_the_rounds_of_the_repository_become_each_steps_record() -> None:
    """Two red rounds and a green one: the step's record is newest first, True where it failed."""
    spans = [
        _span(1, "red", _STEP),
        _span(2, "green", "-"),
        _span(3, "red", _STEP),
        _span(4, "green", "-", "other"),
    ]
    got = historyfetch.fetch("mtools", _ENV, _answer("\n".join(spans)))
    assert got == {_STEP: (True, False, True)}


def test_the_query_names_the_service_the_span_and_a_limit() -> None:
    """The emitter is asked for the train's round spans, at most `LIMIT` of them."""
    seen: list[list[str]] = []

    def run(argv: list[str], _cwd: Path) -> tuple[int, str]:
        seen.append(argv)
        return 0, _span(1, "red", _STEP)

    historyfetch.fetch("mtools", _ENV, run)
    argv = seen[0]
    assert argv[:2] == ["/opt/mikemol-otlp", "query-traces"]
    assert argv[argv.index("--service") + 1] == historyfetch.SERVICE
    assert argv[argv.index("--name") + 1] == historyfetch.NAME
    assert argv[argv.index("--limit") + 1] == str(historyfetch.LIMIT)


def test_no_emitter_no_store_a_failed_query_or_no_round_is_none() -> None:
    """Each way of getting no answer is None; an empty history is never returned."""
    reply = _span(1, "red", _STEP)
    assert historyfetch.fetch("mtools", {commit_span.BIN_ENV: "/o"}, _answer(reply)) is None
    assert historyfetch.fetch("mtools", _ENV, _answer(reply, status=3)) is None
    assert historyfetch.fetch("mtools", _ENV, _answer("")) is None
    assert historyfetch.fetch("nemik", _ENV, _answer(reply)) is None
