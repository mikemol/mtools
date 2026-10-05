# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-debtplan`: plan a per-file debt ledger's pay-down, or mint it into a queue.

    mikemol-debtplan plan --root REPO --ledger LEDGER.json [--exclude NAME ...] [--no-universe]
    mikemol-debtplan mint --root REPO --ledger LEDGER.json [--state STATE] [--prefix PREFIX]

`plan` prints the rows (ready files first) and the import names it could not settle, as JSON; an
unsettled name is a blocker, never a guess, and `--resolutions` declares what one means. `mint`
syncs the repository's paths-forward queue to the plan through `mikemol-paths-forward`, under its
tick lock. The closure runs through the whole tree's Python files (the universe) unless
`--no-universe` asks for the narrower reading; what the walk skipped is printed, never silent.

Exit codes: 0 done, 2 cannot (an unreadable or malformed ledger, a git refusal, a refused card).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pathwalk.walk import WorktreeRefusedError

from mikemol.debtplan.ledger import read_ledger
from mikemol.debtplan.mint import HOW, TOUCHES, VECTOR, MintRefusedError, Style, mint
from mikemol.debtplan.plan import Plan, plan
from mikemol.debtplan.queue import Queue
from mikemol.debtplan.resolutions import read_resolutions
from mikemol.debtplan.universe import Universe, python_files

if TYPE_CHECKING:
    from collections.abc import Sequence

EXIT_OK = 0
EXIT_CANNOT = 2


def _declared(path: Path | None) -> dict[str, str] | None:
    """Read the declared resolutions when a file names them.

    Returns:
        The declared name to path mapping, or None when no file was given.

    """
    return read_resolutions(path) if path else None


class Args(argparse.Namespace):
    """The parsed command line, with the types argparse's own namespace does not carry.

    A list option left off the command line is None, not an empty list: argparse types a default as
    `Any`, and the real default is applied where the option is read.
    """

    command: str
    root: Path
    ledger: Path
    exclude: list[str] | None
    no_universe: bool
    resolutions: Path | None
    state: Path | None
    prefix: str | None
    how: str
    touches: list[str] | None
    vector: str


def _parser() -> argparse.ArgumentParser:
    """Build the command line: a shared set of operands, and the two commands.

    Returns:
        The parser.

    """
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", type=Path, required=True, help="the repository the paths are in")
    common.add_argument(
        "--ledger", type=Path, required=True, help="JSON object of file path to finding count"
    )
    common.add_argument(
        "--exclude",
        action="append",
        metavar="NAME",
        help="a directory name (a glob) to leave out of the universe; there is no default list",
    )
    common.add_argument(
        "--no-universe",
        action="store_true",
        help="derive imports among the ledger's own files only, not through clean modules",
    )
    common.add_argument(
        "--resolutions",
        type=Path,
        help="JSON object of an ambiguous import name to the file it means; honoured only when "
        "that file is one of the name's candidates",
    )
    parser = argparse.ArgumentParser(prog="mikemol-debtplan", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", parents=[common], help="print the plan as JSON")
    minting = commands.add_parser("mint", parents=[common], help="sync the queue to the plan")
    minting.add_argument("--state", type=Path, help="default: ROOT/.claude/paths-forward.json")
    minting.add_argument("--prefix", help="the card title prefix; default: '<repo> debt: '")
    minting.add_argument("--how", default=HOW, help="how a ready card says its file is cleared")
    minting.add_argument("--touches", nargs="+", help="the tags a card carries; default: debt")
    minting.add_argument("--vector", default=VECTOR, help="the WV:1 vector a card carries")
    return parser


def _plan_for(args: Args) -> tuple[Plan, Universe | None]:
    """Read the ledger and plan it, over the tree's files unless told not to.

    Returns:
        The plan, and the walk's counts (None when no universe was walked).

    """
    ledger = read_ledger(args.ledger)
    declared = _declared(args.resolutions)
    if args.no_universe:
        return plan(ledger, args.root, (), declared), None
    universe = python_files(args.root, args.exclude or ())
    return plan(ledger, args.root, universe.files, declared), universe


def _skipped(universe: Universe) -> str:
    """Say what the walk left out, so a short universe is never a silent one.

    Returns:
        One line: the files read and the worktrees, virtualenvs, symlinks and named directories
        skipped.

    """
    return (
        f"mikemol-debtplan: universe {len(universe.files)} file(s); skipped "
        f"{universe.worktrees} worktree(s), {universe.virtualenvs} virtualenv(s), "
        f"{universe.links} symlink(s), {universe.excluded} excluded director(ies)\n"
    )


def _render(planned: Plan) -> str:
    """Render the plan as JSON.

    Returns:
        The rows in pay-down order, and the names that could not be settled.

    """
    rows = [
        {
            "file": row.file,
            "count": row.count,
            "ready": row.ready,
            "waits_on": list(row.waits_on),
            "waited_by": list(row.waited_by),
            "unsettled": list(row.unsettled),
        }
        for row in planned.rows
    ]
    ambiguous = {
        path: [{"name": item.name, "candidates": list(item.candidates)} for item in items]
        for path, items in planned.ambiguous.items()
    }
    document: dict[str, object] = {"rows": rows, "ambiguous": ambiguous}
    return json.dumps(document, indent=1)


def _mint(args: Args, planned: Plan) -> int:
    """Sync the repository's queue to the plan and say what changed.

    Returns:
        0 after the sync.

    """
    state = args.state or args.root / ".claude" / "paths-forward.json"
    prefix = args.prefix or f"{args.root.resolve().name} debt: "
    touches = tuple(args.touches) if args.touches else TOUCHES
    done = mint(planned, Queue(state), Style(prefix, args.how, touches, args.vector))
    sys.stdout.write(
        f"mikemol-debtplan: added {done.added}, rewrote {done.updated}, retired {done.retired}\n"
    )
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Plan a debt ledger, or mint it into the repository's queue.

    Returns:
        0 after printing or syncing, 2 when the ledger, the walk or the writer refuses.

    """
    args = _parser().parse_args(sys.argv[1:] if argv is None else argv, namespace=Args())
    try:
        planned, universe = _plan_for(args)
        if universe is not None:
            sys.stderr.write(_skipped(universe))
        if args.command == "mint":
            return _mint(args, planned)
    except (OSError, ValueError, MintRefusedError, WorktreeRefusedError) as exc:
        sys.stderr.write(f"mikemol-debtplan: {exc}\n")
        return EXIT_CANNOT
    sys.stdout.write(_render(planned) + "\n")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
