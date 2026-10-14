# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-vlog`: ship JSON lines to VictoriaLogs as structured fields (W1179).

    tool | mikemol-vlog --stream tool=commit --stream repo=mtools
    mikemol-vlog --stream tool=gate -- some-tool --its --args       (exit status is the tool's)
    mikemol-vlog --stream tool=app --from-file app.log --state app.state    (once, from an offset)
    mikemol-vlog --drain                                    (send what is spooled, in front)

⚑ THE CALLER'S WORK IS A LOCAL FILE APPEND. Lines become records (`vlogrecord`), are appended to a
spool (`vlogship.ship`), and then a DETACHED drainer is started and not waited for (`vlogdetach`).
A stalled or refusing endpoint can only grow the spool, never the caller's wait. No wall-clock
timeout exists anywhere in this path; the bounds are lines and bytes.

⚑ THE EXIT STATUS IS THE PRODUCER'S. A pipe cannot see it, so the wrapper form runs the command and
returns its status; the stdin and file forms return 0 once the lines are spooled (2: usage).

⚑ THE FILE FORM SAVES EXACTLY THE CHUNK IT SPOOLED. Re-reading the file to find the offset would
commit past a line appended in between, and that line would be lost; the chunk read is the chunk
committed, after its lines are in the spool.

CONSUMED BY: the `mikemol-vlog` console script.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import TextIO

from mikemol.hooks import vlogconfig, vlogdetach, vlogforms, vlogrecord, vlogship

EXIT_USAGE = 2
BATCH = 200
UNITS = ("s", "ms", "us", "ns")
Spawn = Callable[[Sequence[str]], None]


class Args(argparse.Namespace):
    """The parsed command line, typed so nothing downstream is `Any`."""

    stream: list[str] | None
    service: str | None
    resolver_arg: list[str] | None
    spool_dir: Path | None
    max_lines: int | None
    max_bytes: int | None
    message_key: str
    time_key: str | None
    unit: str
    from_file: Path | None
    state: Path | None
    drain: bool
    no_drain: bool
    config: Path
    command: list[str]


def _now() -> str:
    return vlogrecord.stamp(dt.datetime.now(dt.UTC))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mikemol-vlog")
    parser.add_argument("--stream", action="append", metavar="KEY=VALUE")
    parser.add_argument("--service", help="the service NAME the host's resolver is asked for")
    parser.add_argument("--resolver-arg", action="append", metavar="ARG")
    parser.add_argument("--spool-dir", type=Path)
    parser.add_argument("--max-lines", type=int)
    parser.add_argument("--max-bytes", type=int)
    parser.add_argument("--message-key", default=vlogrecord.DEFAULT_MESSAGE_KEY)
    parser.add_argument("--time-key")
    parser.add_argument("--unit", default="s", choices=UNITS)
    parser.add_argument("--from-file", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--drain", action="store_true", help="send the spool now, in front")
    parser.add_argument("--no-drain", action="store_true", help="spool only; start no drainer")
    parser.add_argument("--config", type=Path, default=vlogconfig.CONFIG_PATH)
    parser.add_argument("command", nargs="*", help="after --: a command to run and ship")
    return parser


def _config_of(args: Args) -> vlogship.Config:
    flags = vlogconfig.Flags(
        args.service, args.resolver_arg, args.spool_dir, args.max_lines, args.max_bytes
    )
    return vlogconfig.build(vlogconfig.read_toml(args.config), flags)


def _state_of(args: Args) -> Path | None:
    """Name the offset state file of the file form.

    Returns:
        `--state`, else `<file>.vlogstate` beside the file; None when no file form was asked for.

    """
    if args.from_file is None:
        return None
    return args.state or args.from_file.with_name(args.from_file.name + ".vlogstate")


def _stdin_lines(stdin: TextIO | None) -> Iterable[str]:
    return sys.stdin if stdin is None else stdin


def _produce(
    args: Args, stdin: TextIO | None, take: Callable[[str], None]
) -> tuple[int, vlogforms.Chunk | None]:
    """Feed lines to `take` from the chosen form.

    Returns:
        the producer's status in the wrapper form (else 0), and the chunk read in the file form.

    """
    state = _state_of(args)
    if args.command:
        return vlogforms.run_wrapped(args.command, take), None
    if args.from_file is not None and state is not None:
        chunk = vlogforms.read_from_offset(args.from_file, state)
        for line in chunk.lines:
            take(line)
        return 0, chunk
    for line in _stdin_lines(stdin):
        take(line)
    return 0, None


def _drain_now(config: vlogship.Config) -> int:
    """Send the spool in front and print what happened.

    Returns:
        0 when nothing is left, else 1.

    """
    done = vlogship.drain_all(config)
    report: dict[str, object] = {"sent": done.sent, "left": done.left, "reason": done.reason}
    sys.stdout.write(json.dumps(report) + "\n")
    return 0 if done.left == 0 else 1


def main(
    argv: Sequence[str] | None = None,
    stdin: TextIO | None = None,
    spawn: Spawn = vlogdetach.spawn_detached,
) -> int:
    """Run `mikemol-vlog`.

    Returns:
        the producer's status in the wrapper form; 0 once lines are spooled; 1 when `--drain` left
        lines behind; 2 for a usage error.

    """
    args = _parser().parse_args(list(sys.argv[1:] if argv is None else argv), namespace=Args())
    streams = vlogconfig.streams_of(args.stream or [])
    if streams is None:
        sys.stderr.write("mikemol-vlog: --stream wants KEY=VALUE\n")
        return EXIT_USAGE
    config = _config_of(args)
    if args.drain:
        return _drain_now(config)
    how = vlogrecord.FieldMap(args.message_key, args.time_key, args.unit)
    pending: list[str] = []

    def flush() -> None:
        if pending:
            vlogship.ship(pending, streams, how, config, _now)
            pending.clear()

    def take(line: str) -> None:
        pending.append(line)
        if len(pending) >= BATCH:
            flush()

    code, chunk = _produce(args, stdin, take)
    flush()
    state = _state_of(args)
    if chunk is not None and state is not None:
        vlogforms.commit(state, chunk)
    if not args.no_drain:
        spawn(vlogdetach.drain_argv(config))
    return code
