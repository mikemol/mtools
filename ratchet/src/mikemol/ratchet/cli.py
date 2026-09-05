# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run the ratchet over a distribution's preview-rule census.

⚑⚑ THE BARE INVOCATION IS THE CHEAP READ, AND EXECUTION IS OPTED INTO. A sibling repo's
`findings.py --list` did not list keys — it EXECUTED every registered witness as a
subprocess and blew a two-minute timeout, and its `--times` re-ran rather than reading
recorded times. The tell is not in the name, and the expensive reading was the default one.
Here the default reports; `--init-absent` and `--write` are the flags that mutate.

⚑ `--init-absent` IS THE BIRTH MOVE AND IT IS DELIBERATELY NOT AUTOMATIC. A baseline that
creates itself on first run grandfathers whatever happened to be present at that moment,
and nobody chose that set. ABSENT must be converted to a recorded set by someone saying so.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mikemol.ratchet.census import run_ruff
from mikemol.ratchet.core import ratchet, read_baseline, write_baseline
from mikemol.ratchet.state import BaselineState

_BASELINE = Path("ratchet-preview.txt")


def main(argv: list[str] | None = None) -> int:
    """Run the ratchet for one distribution; return 0 on pass, 1 on refusal."""
    parser = argparse.ArgumentParser(prog="mikemol-ratchet", description=__doc__)
    parser.add_argument("dist", type=Path, help="the distribution root to census")
    parser.add_argument("--init-absent", action="store_true",
                        help="mint a baseline that does not exist yet (the birth move)")
    parser.add_argument("--write", action="store_true",
                        help="lower the baseline when the census pays debt down")
    args = parser.parse_args(argv)

    # ⚑⚑ argparse's `Namespace` is untyped, so `args.dist` is `Any` and poisons the expression
    # it lands in under `disallow_any_expr` — and the poison is at the ATTRIBUTE ACCESS, so
    # wrapping it in `str()` narrows the result while the access itself is still a finding. The
    # boundary is `vars()`, which is a plain `dict[str, Any]`: reading through it and narrowing
    # each value once is the repair the rule exists to force. Silencing it would push the `Any`
    # downstream into `run_ruff` and the baseline path, which is exactly what payload.py exists
    # to prevent one layer over.
    opts: dict[str, object] = vars(args)
    dist = Path(str(opts["dist"]))
    init_absent = bool(opts["init_absent"])
    write = bool(opts["write"])
    path = dist / _BASELINE
    census = run_ruff(dist, preview=True)

    if init_absent:
        state, _keys = read_baseline(path)
        if state is not BaselineState.ABSENT:
            sys.stderr.write(f"{path} is {state}, not ABSENT — refusing to re-mint\n")
            return 1
        write_baseline(path, census, write=True)
        sys.stdout.write(f"{path}: minted {len(census)} key(s)\n")
        return 0

    code, lines = ratchet(census, path, write=write)
    for line in lines:
        sys.stdout.write(f"{line}\n")
    return code


# ⚑⚑ WITHOUT THIS GUARD THE MODULE DEFINES `main` AND NEVER CALLS IT. The console script installed
# by `[project.scripts]` calls it by name, so the venv path worked and hid the gap — but a
# `py_binary` naming this file as `main` RUNS IT AS A SCRIPT, and a script whose entry point is
# never invoked exits 0 having done nothing. Measured: the bazel target reported PASS with an
# empty transcript, which is why the caller now refuses on empty output.
if __name__ == "__main__":
    sys.exit(main())
