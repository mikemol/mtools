# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The first red test summary of a gate is named from its build event lines (W2107).

⚑ THE FIXTURES ARE THE MEASURED SHAPES: a PASSED summary, then a FAILED one (stack 36's case) or a
TIMEOUT one (W1746's), with the id carrying the label and the summary the status and stop time.
"""

import json

from mikemol.hooks import gatefirst

Event = dict[str, object]


def _summary(label: str, status: str, stopped: str) -> str:
    event: Event = {
        "id": {"testSummary": {"label": label}},
        "testSummary": {"overallStatus": status, "lastStopTime": stopped},
    }
    return json.dumps(event)


def test_the_first_failed_summary_is_named_with_its_label_status_and_stop_time() -> None:
    """Passed summaries are skipped; the first FAILED one is the answer, a later one is not."""
    first = _summary("//hooks:a", "PASSED", "2026-10-28T01:00:00.000Z")
    red = _summary("//hooks:graph_fresh", "FAILED", "2026-10-28T01:05:00.000Z")
    later = _summary("//hooks:b", "TIMEOUT", "2026-10-28T01:09:00.000Z")
    found = gatefirst.first_failure(f"{first}\n{red}\n{later}")
    assert found == ("//hooks:graph_fresh", "FAILED", "2026-10-28T01:05:00.000Z")


def test_a_timeout_is_red_and_an_all_green_or_unreadable_file_names_nothing() -> None:
    """TIMEOUT counts; torn lines and events with no summary are skipped; green gives None."""
    timeout = _summary("//hooks:test_worktreereap_save", "TIMEOUT", "2026-10-28T02:19:00.000Z")
    torn = '{"id": {"testSummary": '
    started: Event = {"id": {"started": {}}}
    found = gatefirst.first_failure(f"{torn}\n{json.dumps(started)}\n{timeout}")
    assert found == ("//hooks:test_worktreereap_save", "TIMEOUT", "2026-10-28T02:19:00.000Z")
    assert gatefirst.first_failure(_summary("//hooks:a", "PASSED", "2026-10-28T01:00:00Z")) is None
    assert gatefirst.first_failure("") is None
    assert gatefirst.first_failure("not json at all") is None
