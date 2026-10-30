# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read the first FAILED or TIMEOUT test summary of a gate from its build event file (W2107).

⚑ THE READING IS THE EVENT, NOT THE END OF THE RUN: stack 36's BEP held 589 PASSED and ONE FAILED
`//hooks:graph_fresh`, and W1746's held 1188 PASSED and ONE TIMEOUT `//hooks:test_worktreereap_save`
about four hours before the gate ended. A reader that names the first red test the moment its
summary event is written is what a first-failure stop for a train tip (github-8f R80) needs, and
what a session needs to say "this gate is already red" without waiting for the suite.

⚑ THE SHAPE IS MEASURED (`/var/tmp/mtools-staged/.bep.json`, one JSON object per line): the id is
`{"testSummary": {"label": "//dist:target", ...}}` and the summary carries `overallStatus` and
`lastStopTime` (an ISO `...Z` stamp). A line that is not JSON, or carries no test summary, is
skipped; events are in the order bazel wrote them, so the first match is the first test to finish
red.

CONSUMED BY: nothing yet (the first-failure stop in the train drive, and the pre-commit order).
"""

import json

from mikemol.hooks.payload import as_record, text_of

RED = ("FAILED", "TIMEOUT")


def first_failure(bep_text: str) -> tuple[str, str, str] | None:
    """Find the first test whose summary event reads FAILED or TIMEOUT.

    Returns:
        (label, status, last stop time) of that test, or None when no summary is red.

    """
    for line in bep_text.splitlines():
        try:
            event: object = json.loads(line)
        except ValueError:
            continue
        record = as_record(event)
        summary = as_record(record.get("testSummary"))
        status = text_of(summary.get("overallStatus"))
        if status in RED:
            label = text_of(as_record(as_record(record.get("id")).get("testSummary")).get("label"))
            return label, status, text_of(summary.get("lastStopTime"))
    return None
