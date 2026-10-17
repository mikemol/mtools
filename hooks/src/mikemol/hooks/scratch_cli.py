# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-scratch open|close|land W<n> [--repo PATH]`: the command around `scratch` (W1378).

    mikemol-scratch open W1378 [--repo PATH] [--dist NAME]    prints the new worktree's path
    mikemol-scratch close W1378 [--repo PATH]                 removes it (git refuses a dirty one)
    mikemol-scratch land W1378 [--repo PATH]                  copies its change into the main tree

The scratch root is `MIKEMOL_SCRATCH_ROOT` (no default). With `--dist NAME`, `open` also prints the
recipe that tests that dist's WORKTREE source with the main tree's interpreter. `land` copies files
and prints each as `<letter> <path>`; it stages and commits nothing, and refuses (copying nothing)
when the main tree already holds any of those paths dirty (W1379). Exit 0 done, 4 a refusal with
its reason on stderr, 2 a usage refusal.
"""

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from mikemol.hooks import scratch, scratch_land
from mikemol.hooks.scratch import Run
from mikemol.hooks.scratch_land import Out

EXIT_OK = 0
EXIT_REFUSED = 4


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mikemol-scratch")
    parser.add_argument("verb", choices=("open", "close", "land"))
    parser.add_argument("symbol")
    parser.add_argument("--repo", default=".", help="the checkout to cut the worktree from")
    parser.add_argument("--dist", help="open: also print the pytest recipe for this dist")
    return parser


def _act(opts: dict[str, object], environ: Mapping[str, str], run: Run, out: Out) -> list[str]:
    # Do the verb and return the lines to print; a ScratchError carries any refusal.
    repo = Path(str(opts["repo"])).resolve()
    root = scratch.root_of(environ)
    symbol = str(opts["symbol"])
    if opts["verb"] == "land":
        return scratch_land.land(repo, root, symbol, out)
    if opts["verb"] != "open":
        return [f"removed {scratch.close_worktree(repo, root, symbol, run)}"]
    where = scratch.open_worktree(repo, root, symbol, run)
    dist = opts.get("dist")
    if not dist:
        return [str(where)]
    python = repo / str(dist) / ".venv" / "bin" / "python"
    return [str(where), scratch.hint(where, cast("str", dist), python)]


def main(
    argv: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
    run: Run = scratch.run_git,
    out: Out = scratch.git_out,
) -> int:
    """Open, close or land a scratch worktree.

    Returns:
        0 when done, 4 when refused (reason on stderr).

    """
    opts: dict[str, object] = vars(_parser().parse_args(sys.argv[1:] if argv is None else argv))
    try:
        lines = _act(opts, os.environ if environ is None else environ, run, out)
    except scratch.ScratchError as refused:
        sys.stderr.write(f"mikemol-scratch: {refused}\n")
        return EXIT_REFUSED
    sys.stdout.write("".join(f"{line}\n" for line in lines))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
