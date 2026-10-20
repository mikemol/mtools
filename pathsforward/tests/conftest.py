# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Keep the host session's id out of every test (W1546).

⚑ A LEDGER LINE NOW CARRIES `session=<uuid>` WHEN THE ENVIRONMENT NAMES ONE, and a test run from a
Claude session inherits `CLAUDE_CODE_SESSION_ID`, so every test that compares a ledger line to an
exact string would pass on a bare host and fail under a session. The variable is removed once when
the run starts (a fixture marked autouse is refused by the lint); a test that wants a session sets
it itself with `monkeypatch.setenv`.
"""

import os
from collections.abc import Sequence
from unittest import mock

from mikemol.pathsforward import refusal_record
from mikemol.pathsforward.ledger import SESSION_ENV

os.environ.pop(SESSION_ENV, None)


def _not_started(_argv: Sequence[str], _line: str) -> None:
    """Stand in for the detached `mikemol-otlp` start, so a test run never ships to a real store."""


# ⚑ NO TEST STARTS A REAL TELEMETRY CHILD (W1742): every saved edit now ships its events, and a run
# on a host with a store would push each fixture mutation into it. A test that wants the start
# patches this again and reads what it was handed.
mock.patch.object(refusal_record, "spawn", _not_started).start()
