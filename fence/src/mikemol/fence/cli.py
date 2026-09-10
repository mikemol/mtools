# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The `mikemol-fence` command line.

⚑ THE EXIT CODE IS THE PAYLOAD'S, so the fence is transparent to a caller that only cares
whether its command worked. The three harness codes (125 cannot-fence, 126 not-executable,
127 not-found) are the shell's own conventions, and 125 is reserved for "the harness could not
run" — never mixed with a payload result.

⚑⚑ `--observe` EXISTS AS AN EXPLICIT FLAG EVEN THOUGH PASSING NO CAPS DOES THE SAME THING.
An undeclared capability is one nobody can depend on: a caller reading `--help` could not tell
whether the no-caps case was supported or degenerate, which is exactly why a workspace census
had to read the source to find that this tool was the only unfused observer in ten repos. The
flag costs one line and turns an accident into a contract. It REFUSES to combine with a cap
rather than silently winning, because "observe" and "cap this" is an incoherent instruction and
guessing which the caller meant is how a fence ends up not fencing.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import cast

from mikemol.fence import core
from mikemol.fence.cgroup import FenceUnavailableError
from mikemol.fence.core import Caps


def _render(r: core.Result) -> str:
    """One human line: what it cost, and what bound it."""
    what = ("BOUND BY " + "; ".join(r.bound_by)) if r.bound_by else "completed within caps"
    return (f"mikemol-fence: rc={r.exit_code} dur={r.duration_s}s "
            f"peak_mem={r.memory_peak_bytes} {what}")


def _note(msg: str) -> None:
    """Write one human-facing line to stderr.

    ⚑ THE STREAM SPLIT IS THE CONTRACT: narration goes to stderr so that `--json` on stdout is
    machine-readable even while the human rendering is on screen. A caller piping stdout into a
    parser gets JSON and nothing else.
    """
    sys.stderr.write(msg + "\n")


def _emit(payload: str) -> None:
    """Write the machine-readable result to stdout."""
    sys.stdout.write(payload + "\n")


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser (separate so the tests can exercise it without running)."""
    ap = argparse.ArgumentParser(
        prog="mikemol-fence",
        description="Run a command inside a cgroup; report what it consumed and which cap bound.")
    ap.add_argument("--mem", help="memory.max, e.g. 2G / 512M / max")
    ap.add_argument("--swap", help="memory.swap.max, e.g. 0 / 512M / max "
                                   "(0 = no swap, so mem is a kill boundary not a throttle)")
    ap.add_argument("--pids", type=int, help="pids.max (concurrent task ceiling)")
    ap.add_argument("--io", help='io.max, e.g. "259:0 wbps=10485760"')
    ap.add_argument("--ratchet", help="comma-sep mem caps, tightest last (4G,2G,1G,512M) — "
                                      "runs until one BINDS and reports the binding constraint")
    ap.add_argument("--observe", action="store_true",
                    help="measure only: impose no cap at all (the default when no cap is given, "
                         "named so it can be relied on)")
    ap.add_argument("--json", action="store_true", help="emit the result as JSON")
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    return ap


@dataclass(frozen=True)
class _Args:
    """The parsed command line, narrowed once at the boundary.

    ⚑⚑ argparse HANDS BACK `Any` AND THAT FANS OUT. A `Namespace` attribute is untyped, so under
    `disallow_any_expr` every read of `args.mem` is an error — and without that setting it would
    be SILENT, with the whole CLI typing as `Any` while looking checked. Narrowing here means the
    dynamic values are converted exactly once, at the edge where they arrive, and every consumer
    downstream gets a real type. This is the same discipline the sibling `ratchet` distribution
    applies to its `Census`: state the sum type where it is CREATED, not at each reader.
    """

    mem: str | None
    swap: str | None
    pids: int | None
    io: str | None
    ratchet: str | None
    observe: bool
    json: bool
    cmd: tuple[str, ...]

    @classmethod
    def parse(cls, ap: argparse.ArgumentParser, argv: list[str] | None) -> _Args:
        """Parse `argv` and narrow every field to its declared type."""
        ns = ap.parse_args(argv)
        raw: list[str] = list(cast("list[str]", ns.cmd))
        cmd = raw[1:] if raw and raw[0] == "--" else raw
        pids = cast("int | None", ns.pids)
        return cls(
            mem=cast("str | None", ns.mem),
            swap=cast("str | None", ns.swap),
            pids=pids,
            io=cast("str | None", ns.io),
            ratchet=cast("str | None", ns.ratchet),
            observe=bool(cast("bool", ns.observe)),
            json=bool(cast("bool", ns.json)),
            cmd=tuple(cmd),
        )


def main(argv: list[str] | None = None) -> int:
    """Parse, run, report. Returns the payload's exit code, or a harness code."""
    ap = build_parser()
    args = _Args.parse(ap, argv)
    cmd = args.cmd
    if not cmd:
        ap.error("give a command after --")

    caps = Caps(mem=args.mem, swap=args.swap, pids=args.pids, io=args.io)
    if args.observe and (not caps.observe_only or args.ratchet):
        ap.error("--observe imposes no cap, so it cannot be combined with --mem/--swap/--pids/"
                 "--io/--ratchet; drop --observe to cap, or drop the caps to observe")

    try:
        if args.ratchet:
            results = core.ratchet(cmd, args.ratchet.split(","), caps)
            for r in results:
                _note(f"── mikemol-fence ratchet: mem={r.caps.mem} ──")
                _note(_render(r))
            last = results[-1]
            if last.bound_by:
                _note(f"── BINDING CONSTRAINT at mem={last.caps.mem}: "
                      f"{'; '.join(last.bound_by)} — it completed at every looser cap and bound "
                      f"here, so this is the scale of the resource the command needs ──")
            else:
                _note(f"── completed within ALL caps down to {last.caps.mem} — no binding "
                      f"constraint in the tried range (either it is frugal, or the mechanism is "
                      f"not the resource you ratcheted) ──")
            if args.json:
                payload: list[core.ResultJSON] = [r.as_dict() for r in results]
                _emit(json.dumps(payload))
            return 0

        r = core.run_once(cmd, caps)
    except FenceUnavailableError as e:
        _note(f"mikemol-fence: {e}")
        return core.EXIT_HARNESS

    if args.json:
        _emit(json.dumps(r.as_dict()))
    else:
        _note(_render(r))
    return r.exit_code if r.exit_code is not None else 1


if __name__ == "__main__":
    sys.exit(main())
