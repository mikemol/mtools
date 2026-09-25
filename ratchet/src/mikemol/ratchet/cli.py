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
from typing import cast

from mikemol.ratchet.census import CensusUnavailableError, run_ruff
from mikemol.ratchet.core import ratchet, read_baseline, write_baseline
from mikemol.ratchet.keys import RUFF, SCHEMA_NAMES, MalformedKeyError, parse_all, schema_named
from mikemol.ratchet.remap import __doc__ as remap_doc
from mikemol.ratchet.remap import remap_guard
from mikemol.ratchet.state import BaselineState

_BASELINE = Path("ratchet-preview.txt")

# ⚑⚑ "COULD NOT LOOK" IS NOT "LOOKED AND REFUSED", AND THE STATUS SAYS WHICH. 2 matches
# `remap.UNREADABLE` and argparse's own usage status: in all three the gate did not run. Every
# consumer measured (`.githooks/pre-commit`, `preflight.sh`, `hooks/tests/test_bar_fires.py`)
# tests only for nonzero, so each still refuses; only the reason becomes readable from the status.
CANNOT_CENSUS = 2


_REMAP = "remap"


def _remap_main(argv: list[str]) -> int:
    """Run `mikemol-ratchet remap DIST FILE... [--rev REV] [--write]`.

    ⚑ A SUBCOMMAND, NOT A FLAG ON THE CENSUS: it shares neither ruff nor `ratchet-preview.txt`
    with it, and as a flag `--write` meant two different things. `--rev` exists only here.

    Returns:
        remap.CLEAN, remap.REFUSED or remap.UNREADABLE.

    """
    parser = argparse.ArgumentParser(prog=f"mikemol-ratchet {_REMAP}", description=remap_doc)
    parser.add_argument("dist", type=Path, help="a git work tree; FILEs are relative to it")
    parser.add_argument("files", nargs="+", metavar="FILE", help="JSON baselines to guard")
    parser.add_argument("--rev", default="HEAD", help="the revision to compare against")
    parser.add_argument(
        "--write",
        action="store_true",
        help="rewrite every file to its path-only projection (all or nothing)",
    )
    opts: dict[str, object] = vars(parser.parse_args(argv))
    code, lines = remap_guard(
        Path(str(opts["dist"])),
        [str(f) for f in cast("list[str]", opts["files"])],
        rev=str(opts["rev"]),
        write=bool(opts["write"]),
    )
    for line in lines:
        sys.stdout.write(f"{line}\n")
    return code


def main(argv: list[str] | None = None) -> int:
    """Run the ratchet for one distribution; 0 on pass, 1 on refusal, 2 when it cannot census.

    ⚑ `remap` AS THE FIRST ARGUMENT SELECTS THE SUBCOMMAND. A distribution directory literally
    named `remap` is reached as `./remap`.

    ⚑⚑ `--key-schema` IS DECLARED BY THE CALLER, NEVER GUESSED FROM THE KEYS. This package reads
    no per-distribution config, so the flag is the declaration; a schema inferred from key shape
    would read a malformed key as whichever schema it happened to fit. A census key the declared
    schema cannot parse refuses by name, and `--init-absent` mints nothing.

    Returns:
        0 on pass, 1 on refusal, CANNOT_CENSUS when ruff could not produce a census (the remap
        subcommand returns its own codes).

    """
    args_in = sys.argv[1:] if argv is None else argv
    if args_in[:1] == [_REMAP]:
        return _remap_main(args_in[1:])
    parser = argparse.ArgumentParser(
        prog="mikemol-ratchet",
        description=__doc__,
        epilog=f"subcommand: mikemol-ratchet {_REMAP} DIST FILE... [--rev REV] [--write]",
    )
    parser.add_argument("dist", type=Path, help="the distribution root to census")
    parser.add_argument(
        "--init-absent",
        action="store_true",
        help="mint a baseline that does not exist yet (the birth move)",
    )
    parser.add_argument(
        "--write", action="store_true", help="lower the baseline when the census pays debt down"
    )
    parser.add_argument(
        "--key-schema",
        choices=SCHEMA_NAMES,
        default=RUFF,
        help="the declared grammar of a baseline key (default: ruff path:rule)",
    )
    args = parser.parse_args(args_in)

    # ⚑⚑ argparse's `Namespace` is untyped, so `args.dist` is `Any` and poisons the expression
    # it lands in under `disallow_any_expr` — and the poison is at the ATTRIBUTE ACCESS, so
    # wrapping it in `str()` narrows the result while the access itself is still a finding. The
    # boundary is `vars()`, which is a plain `dict[str, Any]`: reading through it and narrowing
    # each value once is the repair the rule exists to force. Silencing it would push the `Any`
    # downstream into `run_ruff` and the baseline path, which is exactly what hooks'
    # `mikemol.hooks.payload` exists to prevent for hook payloads.
    opts: dict[str, object] = vars(args)
    dist = Path(str(opts["dist"]))
    init_absent = bool(opts["init_absent"])
    write = bool(opts["write"])
    schema = str(opts["key_schema"])
    path = dist / _BASELINE
    try:
        census = run_ruff(dist, preview=True)
    except CensusUnavailableError as exc:
        sys.stderr.write(f"{exc}\n")
        return CANNOT_CENSUS

    if init_absent:
        state, _keys = read_baseline(path)
        if state is not BaselineState.ABSENT:
            sys.stderr.write(f"{path} is {state}, not ABSENT — refusing to re-mint\n")
            return 1
        try:
            parse_all(schema_named(schema), census)
        except MalformedKeyError as exc:
            sys.stderr.write(f"key schema {schema!r} refused: {exc} — minting nothing\n")
            return 1
        write_baseline(path, census, write=True)
        sys.stdout.write(f"{path}: minted {len(census)} key(s)\n")
        return 0

    code, lines = ratchet(census, path, write=write, schema=schema)
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
