# W232 — requirements.txt pins vs uv.lock (2026-09-28)

Instrument: `python3 .claude/design/W10-sync.py` (PIN regex `name==ver`; uv.lock via tomllib).
Denominator: 11 distributions with a requirements.txt; all 11 have a uv.lock.

| dist | pins | agree | delta |
|---|---|---|---|
| hooks | 7 | 6 | **1: ast-serialize requirements 0.9.0 vs uv.lock 0.11.1** |
| mdstruct | 3 | 3 | 0 |
| pycodemod | 2 | 2 | 0 |
| pytestspec | 5 | 5 | 0 |
| corpus, fence, ledger, pathsforward, ratchet, transcriptstruct, witness | 0 | — | — |

Zero-pin rows are genuinely empty: fence/requirements.txt is the uv header only (no runtime deps).
Positive control: the same parser read 7 pins from hooks.

The hooks delta is W10's original split, surviving on the `_deps` side after the `_dev` hubs moved
to uv.lock: `hooks_deps` (bazel runtime) still resolves ast-serialize 0.9.0.
