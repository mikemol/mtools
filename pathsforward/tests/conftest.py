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

from mikemol.pathsforward.ledger import SESSION_ENV

os.environ.pop(SESSION_ENV, None)
