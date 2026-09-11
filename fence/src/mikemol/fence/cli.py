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
    """One human line: what it cost, and what bound it.

    Returns:
        A single line carrying the exit code, duration, peak memory and the binding constraint.
        ⚑ ONE LINE, BECAUSE THE RATCHET PRINTS ONE PER CAP: a multi-line rendering would make a
        sweep unreadable at exactly the moment the sweep is the point, and the caps are meant to
        be compared down a column.

    """
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
    """Construct the argument parser.

    Returns:
        The parser, fully configured. ⚑ BUILT IN ITS OWN FUNCTION SO THE TESTS CAN EXERCISE THE
        ARGUMENT CONTRACTS WITHOUT RUNNING A PAYLOAD — the refusals (`--observe` with a cap, a
        missing command) are decisions this parser makes, and checking them through a real fenced
        run would need a delegated cgroup subtree to assert something that never reaches one.

    """
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
        """Parse `argv` and narrow every field to its declared type.

        Returns:
            The parsed arguments as a TYPED record. ⚑⚑ THE NARROWING IS THE WHOLE FUNCTION:
            argparse's `Namespace` types every attribute as `Any`, so under this distribution's
            `disallow_any_expr` a caller reading `ns.mem` would be reading an expression the type
            checker cannot see — and the tests asserting against it would check nothing. Each
            `cast` here is the one place a claim about a flag's type is made, where it can be
            read and argued with.

        """
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


def _report_ratchet(results: list[core.Result], *, json_out: bool) -> int:
    """Render a ratchet sweep and name the binding constraint, if there was one.

    ⚑⚑⚑ EXTRACTED SO THE `try` CAN GUARD WHAT IT ACTUALLY CATCHES. This code used to sit INSIDE a
    `try/except FenceUnavailableError` together with the `core.ratchet` call it reports on —
    thirteen statements under a handler that only one of them can trigger. An IndexError or a
    KeyError in this rendering would have been caught and reported as *the fence is unavailable*,
    returning `EXIT_HARNESS`: a bug in the reporter made indistinguishable from a missing cgroup
    subtree, which is precisely the confusion this tool exists to prevent one layer down.
    ⚑⚑ `too-many-statements-in-try-clause` NAMED IT, and the finding is structural rather than
    stylistic — narrowing the try is the repair, and moving the body out is what narrows it.

    Args:
        results: one `Result` per cap tried, in the order they were tried.
        json_out: emit the machine-readable payload on stdout instead of prose on stderr.

    Returns:
        Always 0. ⚑ A RATCHET SWEEP THAT COMPLETES HAS SUCCEEDED EVEN WHEN EVERY CAP BOUND — the
        binding cap is the ANSWER, not a failure, so reporting it through a nonzero code would
        conflate *I measured the constraint you asked for* with *I could not measure*.

    """
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
    if json_out:
        payload: list[core.ResultJSON] = [r.as_dict() for r in results]
        _emit(json.dumps(payload))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse, run, report.

    Returns:
        The payload's own exit code when the command ran, or a HARNESS code when it could not —
        `EXIT_HARNESS` for an unavailable fence, 1 when the payload's code is unknown. ⚑ THE
        SEPARATION IS THE POINT: a caller must be able to tell *your command failed* from *I
        could not fence it*, and a single nonzero would merge them.

    """
    ap = build_parser()
    args = _Args.parse(ap, argv)
    cmd = args.cmd
    if not cmd:
        ap.error("give a command after --")

    caps = Caps(mem=args.mem, swap=args.swap, pids=args.pids, io=args.io)
    if args.observe and (not caps.observe_only or args.ratchet):
        ap.error("--observe imposes no cap, so it cannot be combined with --mem/--swap/--pids/"
                 "--io/--ratchet; drop --observe to cap, or drop the caps to observe")

    # ⚑⚑⚑ THE `try` GUARDS THE CALLS INTO `core`, NOT THE REPORTING. It used to wrap thirteen
    # statements — the ratchet call AND every line that renders its result — and
    # `too-many-statements-in-try-clause` is right that this is a defect rather than a style
    # preference: only `core.ratchet` and `core.run_once` raise `FenceUnavailableError`, so a
    # KeyError or an IndexError in the rendering below would have been caught by a handler that
    # reports *the fence is unavailable* and returns `EXIT_HARNESS`. A bug in the reporter would
    # have been indistinguishable from a missing cgroup subtree.
    # ⚑⚑ NARROWED RATHER THAN SUPPRESSED, and the narrowing is what makes the handler honest: the
    # rendering now runs OUTSIDE the try, so an error there crashes loudly with its own traceback
    # instead of being relabelled as an environment problem.
    if args.ratchet:
        try:
            results = core.ratchet(cmd, args.ratchet.split(","), caps)
        except FenceUnavailableError as e:
            _note(f"mikemol-fence: {e}")
            return core.EXIT_HARNESS
        return _report_ratchet(results, json_out=args.json)

    try:
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
