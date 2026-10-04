# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Run a gate target under the repo's OWN resource budget.

Ported from paperkit's `tools/rungate.py` (paperkit:W142). Two changes: the repo root is the
current directory (paperkit derived it from the module's own path), and the two subprocesses go
through injectable seams, `capture_output` and `run_passthrough`, so a suite can drive `main`
without bazel.

⚑ THE FLAGS ARE LOAD-BEARING AND WERE BEING RE-DERIVED BY HAND EVERY TIME. `.githooks/pre-commit`
says it outright: *Bare `bazel test //:hook` is not the same command as this line.* Running the
hook target WITHOUT the budget put 23 sandboxes on a 15GB box and produced ZERO artifacts in 60
minutes, load 55 with no throughput.

So "which flags does a gate need" is a question about the BUILD's structure, owned by
`tools/sweep_budget.py` and the hook, not something to reconstruct in a shell each turn. Writing
it out by hand also forces a `$(...)` substitution into the command line, which is exactly the
composed shape the no-chaining and shellcheck guards refuse.

The argv-to-record conversion follows `tools/cellargs.py`: argparse still owns parsing, and each
field is read from the Namespace exactly once under an explicit annotation, which is what
confines the `Any` instead of letting it fan out through every caller.

    python3 -m mikemol.gatecheck.rungate @paperkit_boundaries//:gate
    python3 -m mikemol.gatecheck.rungate //:hook --keep-going
    python3 -m mikemol.gatecheck.rungate @paperkit_render//:gate --dry-run
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    type Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]

# Where, under the repo root, the owner of the sweep's RAM bound lives.
_SWEEP_BUDGET = Path("tools") / "sweep_budget.py"


@dataclass(frozen=True)
class GateArgs:
    """What this invocation was asked to run."""

    target: str
    keep_going: bool
    dry_run: bool


def parse(argv: Sequence[str]) -> GateArgs:
    """Parse `argv` into a typed record.

    Returns:
        the target and the two flags.

    """
    ap = argparse.ArgumentParser(description="Run a gate under the repo's sweep budget.")
    ap.add_argument("target", help="a bazel test target, e.g. @paperkit_boundaries//:gate")
    ap.add_argument(
        "--keep-going",
        action="store_true",
        help="keep building after a failure (default: stop at the first)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print the command line and exit without running it",
    )
    ns = ap.parse_args(argv)
    target: str = ns.target
    keep_going: bool = ns.keep_going
    dry_run: bool = ns.dry_run
    return GateArgs(target=target, keep_going=keep_going, dry_run=dry_run)


def capture_output(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run `cmd` in `cwd`, collecting its output as text.

    Returns:
        the completed process; its status is read by the caller, never raised here.

    """
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def run_passthrough(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run `cmd` in `cwd` with the terminal's own stdout and stderr.

    Returns:
        the completed process; its exit code is the gate's verdict.

    """
    return subprocess.run(cmd, cwd=cwd, check=False, text=True)


def budget(root: Path, capture: Runner = capture_output) -> str:
    """Ask the owner (sweep_budget.py) for the sweep's RAM bound, in MB.

    Returns:
        the owner's stdout, stripped.

    """
    exe = sys.executable or "python3"
    proc = capture([exe, str(root / _SWEEP_BUDGET)], root)
    proc.check_returncode()
    return proc.stdout.strip()


def argv_for(args: GateArgs, ram: str) -> list[str]:
    """Build the full bazel command line, the one the pre-commit hook runs.

    Returns:
        the argv.

    """
    return [
        "mise",
        "exec",
        "--",
        "bazel",
        "test",
        args.target,
        "--config=mutant",
        f"--local_resources=memory={ram}",
        "--keep_going" if args.keep_going else "--notest_keep_going",
    ]


def main(
    argv: Sequence[str] | None = None,
    *,
    root: Path | None = None,
    capture: Runner = capture_output,
    run: Runner = run_passthrough,
) -> int:
    """Resolve the budget, then run the gate and pass its exit code through.

    `root` is the repo root (default: the current directory); `capture` and `run` are the seams
    for the budget query and the gate run.

    Returns:
        0 for a dry run, otherwise the gate's own exit code.

    """
    args = parse(sys.argv[1:] if argv is None else argv)
    where = Path.cwd() if root is None else root
    ram = budget(where, capture)
    cmd = argv_for(args, ram)

    sys.stdout.write(f"  budget: {ram} MB (tools/sweep_budget.py)\n")
    sys.stdout.write(f"  {' '.join(cmd)}\n\n")
    sys.stdout.flush()

    if args.dry_run:
        return 0
    return run(cmd, where).returncode


if __name__ == "__main__":
    raise SystemExit(main())
