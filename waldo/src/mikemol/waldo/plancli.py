# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The plan-admission command line: plan, verify, apply, and the one apply line it prints (W1856).

Ported from luthen's `checks/opa_plan.py` (lines 483-537, 574-615, 353-360 and 163-175), behind
`Seams`. A consumer's console script builds its `Seams` and calls `main(argv, seams, command)`,
where `command` is how the consumer's own tool is invoked (what an operator is told to type).

⚑ THE ONLY APPLY LINE PRINTED IS THE VERIFIED ONE, `<command> [--root R] --apply-plan PLANFILE`,
never a bare `tofu apply`, and `--apply-plan` refuses a planfile with no valid verdict. A
root-planned root's line starts with `sudo`, since its planfile is root-owned (luthen, measured
2026-09-24).

⚑ AN EXISTING PLAN IS NEVER OVERWRITTEN: `--planfile P` over an operator's -target plan once
replaced it with an UNTARGETED one that was then applied (luthen W115), so a planfile that already
holds a plan is refused and a new name is asked for. A fresh temp file is empty and fine.

⚑ A DROPPED SSH MUST NOT CUT AN APPLY: `hangup_ignored` ignores SIGHUP for this process and any
child started inside it, then restores it; an ignored disposition is inherited across exec, so
tofu survives too (luthen W353). The consumer passes it as `Seams.guard`.
"""

import argparse
import signal
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

from mikemol.waldo.planconfig import PlanConfig
from mikemol.waldo.planflow import (
    EXIT_OK,
    EXIT_STOPPED,
    Seams,
    confirm_and_apply,
    judge,
    preflight,
)
from mikemol.waldo.planverdict import load_verdict

SURVIVE_HINT = (
    "run it under `screen` or `systemd-run --user --scope` so a dropped ssh cannot cut the apply"
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser, every flag the operator's muscle memory uses.

    Returns:
        the parser.

    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--planfile", type=Path)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--root", default="", help="a sub-root under the terraform directory")
    parser.add_argument("--apply", action="store_true", help="plan, verify, confirm, apply")
    parser.add_argument("--apply-plan", type=Path, help="apply an already admitted planfile")
    parser.add_argument("--yes", action="store_true", help="do not ask; the verdict still gates")
    parser.add_argument(
        "--replace", action="append", default=None, help="resource address to replace (repeatable)"
    )
    parser.add_argument(
        "--target", action="append", default=None, help="resource address to plan (repeatable)"
    )
    return parser


@contextmanager
def hangup_ignored() -> Iterator[None]:
    """Ignore SIGHUP for this process and any child started inside, then restore it.

    Yields:
        nothing; the previous disposition comes back on every exit path.

    """
    before = signal.signal(signal.SIGHUP, signal.SIG_IGN)
    try:
        yield
    finally:
        signal.signal(signal.SIGHUP, before)


def pick_planfile(config: PlanConfig, given: Path | None) -> Path | str:
    """Choose the planfile to write; an existing plan is never overwritten.

    Returns:
        the path, or why not.

    """
    if given is None:
        return Path(tempfile.mkstemp(prefix=config.temp_prefix, suffix=".tfplan")[1])
    if given.is_file() and given.stat().st_size > 0:
        return f"{given} already holds a plan; refusing to overwrite it (name a new --planfile)"
    return given


def apply_line(config: PlanConfig, root: Path, planfile: Path, command: str) -> str:
    """Spell the ONE apply command this tool prints: the verified form.

    Returns:
        `[sudo ]<command>[ --root R] --apply-plan PLANFILE`, with sudo for a root-planned root.

    """
    sudo = "sudo " if (config.root_custody and root.name in config.root_planned) else ""
    sub = f" --root {root.name}" if root != config.terraform else ""
    return f"{sudo}{command}{sub} --apply-plan {planfile}"


def verify(seams: Seams, planfile: Path) -> int:
    """Admit only a planfile whose recorded verdict was 0 and whose bytes match.

    Returns:
        OK when admitted, STOPPED with the reason otherwise.

    """
    doc = load_verdict(seams.config, planfile, seams.declarations)
    if isinstance(doc, str):
        seams.out(f"opa_plan --verify: {doc}\n")
        return EXIT_STOPPED
    seams.out(f"opa_plan --verify: {planfile} admitted and unchanged\n")
    return EXIT_OK


def plan_flow(seams: Seams, args: argparse.Namespace, root: Path, command: str) -> int:
    """Plan, evaluate, record the verdict, print the apply line, and apply when asked.

    Returns:
        the exit code.

    """
    pre = preflight(seams, root)
    if isinstance(pre, int):
        return pre
    planfile = pick_planfile(seams.config, cast("Path | None", args.planfile))
    if isinstance(planfile, str):
        seams.out(f"opa_plan S: REFUSED -- {planfile}\n")
        return EXIT_STOPPED
    replace = tuple(cast("list[str] | None", args.replace) or ())
    targets = tuple(cast("list[str] | None", args.target) or ())
    code = judge(seams, pre, root, planfile, (replace, targets))
    if code != EXIT_OK:
        return code
    seams.out("opa_plan: ADMITTED -- apply exactly this plan:\n")
    seams.out(f"  {apply_line(seams.config, root, planfile, command)}\n")
    seams.out(f"  {SURVIVE_HINT}\n")
    if cast("bool", args.apply):
        return confirm_and_apply(seams, pre[0], root, planfile, assume_yes=cast("bool", args.yes))
    return code


def apply_existing(seams: Seams, args: argparse.Namespace, root: Path) -> int:
    """Apply a planfile admitted earlier, after the same checks `--apply` makes.

    Returns:
        the exit code.

    """
    tools = preflight(seams, root)
    if isinstance(tools, int):
        return tools
    return confirm_and_apply(
        seams, tools[0], root, cast("Path", args.apply_plan), assume_yes=cast("bool", args.yes)
    )


def main(argv: list[str] | None, seams: Seams, command: str) -> int:
    """Run one command: verify, apply an admitted plan, or plan (and apply with `--apply`).

    Returns:
        the exit code of whichever ran.

    """
    args = build_parser().parse_args(argv)
    config = seams.config
    name = cast("str", args.root)
    root = config.terraform / name if name else config.terraform
    to_verify = cast("Path | None", args.verify)
    if to_verify is not None:
        return verify(seams, to_verify)
    if cast("Path | None", args.apply_plan) is not None:
        return apply_existing(seams, args, root)
    return plan_flow(seams, args, root, command)
