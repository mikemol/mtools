# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The invalidation-probe protocol, mechanized.

An INSTRUMENT, not a gate: re-verify its number each use, [[instrument-vs-gate]].

Ported from paperkit's `tools/probe.py` (paperkit:W142); behaviour unchanged except as listed in
the README (the marker names this module; the revert is verified after the `finally` rather than
inside it, since a `return` in a `finally` swallows the exception it is unwinding). `bazel` is run
through `proc.stream`, and the hook runner and marker source are parameters of `main`.

Measures what editing ONE file re-executes: append a semantically-null marker line, re-run
//:hook under --config=mutant, read the executed-action count, revert, and RE-SYNC the build
state.  Each step is a banked probe-hygiene rule made structural:

  1. the marker is VERIFIED present before the build runs - a silent no-match (the sed that
     missed) otherwise fakes a near-zero "win" out of pure cache hits;
  2. the count is read from bazel's own process line, never inferred;
  3. the revert is VERIFIED gone, and runs in a finally: a crashed probe never strands a
     marker in the tree;
  4. the build state is RE-SYNCED after the revert (a probe build records the marker-hash
     into MODULE.bazel.lock; reverting only the FILE leaves lock != tree, which stalls the
     next pre-commit - revert the BUILD STATE, not just the file).

    python -m mikemol.buildtel.probe paperkit/grade.py
    python -m mikemol.buildtel.probe paperkit/coherence.py --no-resync   # skip step 4
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.buildtel import proc

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

_LINE = re.compile(r"INFO: (\d+) processes: (.*)\.")
HOOK_ARGV = ("bazel", "test", "//:hook", "--config=mutant")
EXIT_NO_FILE = 2
MARKER_BYTES = 4


def hook(label: str, stream: proc.Streamer = proc.stream) -> tuple[int, str]:
    """Run //:hook --config=mutant, streaming stderr live.

    Returns:
        `(exit status, bazel's last processes line)`; the line is "" when bazel printed none.

    """
    sys.stdout.write(f"probe: {label} — bazel test //:hook --config=mutant …\n")
    sys.stdout.flush()
    seen: list[str] = []

    def on_line(line: str) -> None:
        sys.stderr.write(line)
        if _LINE.search(line):
            seen.append(line.strip())

    status = stream(HOOK_ARGV, on_line)
    return status, seen[-1] if seen else ""


def executed(line: str) -> int | None:
    """Count the EXECUTED actions in bazel's process line.

    Everything that is not a cache hit and not internal: the number every measured payoff in the
    plan is quoted in.

    Returns:
        the count, or None when `line` is not a processes line.

    """
    m = _LINE.search(line)
    if not m:
        return None
    breakdown: object = m.group(2)
    total = 0
    for raw in str(breakdown).split(","):
        part = raw.strip()
        n = int(part.split()[0])
        if "action cache hit" not in part and "internal" not in part:
            total += n
    return total


def new_marker() -> str:
    """Make a fresh semantically-null marker line.

    Returns:
        a comment line, newline included, carrying 8 random hex digits.

    """
    tag = os.urandom(MARKER_BYTES).hex()
    return f"# PROBE-MARKER {tag} (mikemol.buildtel.probe - semantically null; auto-reverted)\n"


def main(
    argv: Sequence[str] | None = None,
    *,
    run_hook: Callable[[str], tuple[int, str]] = hook,
    make_marker: Callable[[], str] = new_marker,
) -> int:
    """Null-edit one file, measure what the hook re-executes, and put everything back.

    Returns:
        0 when the probe build was green; 1 when it was not, the marker did not land, the revert
        or the resync failed; 2 when the file does not exist.

    """
    ap = argparse.ArgumentParser(description="The invalidation-probe protocol, mechanized.")
    ap.add_argument("file", help="the tracked .py (or any text) file to null-edit")
    ap.add_argument(
        "--no-resync",
        action="store_true",
        help="skip the post-revert build-state resync (chained probes only; the LAST must resync)",
    )
    a = ap.parse_args(list(sys.argv[1:] if argv is None else argv))
    target: str = a.file
    no_resync: bool = a.no_resync

    f = Path(target)
    if not f.is_file():
        sys.stderr.write(f"probe: no such file {f}\n")
        return EXIT_NO_FILE
    marker = make_marker()
    orig = f.read_text(encoding="utf-8")

    f.write_text(orig + marker, encoding="utf-8")
    if f.read_text(encoding="utf-8").count(marker) != 1:  # rule 1: verify the edit LANDED
        f.write_text(orig, encoding="utf-8")
        sys.stderr.write("probe: marker failed to land — aborted, file restored\n")
        return 1
    sys.stdout.write(f"probe: marker verified in {f}\n")

    try:
        rc, line = run_hook("marker build")
    finally:
        f.write_text(orig, encoding="utf-8")  # rule 3: revert in a finally
    if f.read_text(encoding="utf-8") != orig:
        sys.stderr.write(f"probe: REVERT FAILED — restore {f} by hand!\n")
        return 1
    sys.stdout.write(f"probe: marker reverted from {f}\n")
    n = executed(line)

    if rc != 0:
        sys.stderr.write(
            f"probe: hook FAILED under the marker (rc={rc}) — "
            "the count below is not a clean probe\n"
        )

    if not no_resync:  # rule 4: revert the BUILD STATE too
        rc2, _line2 = run_hook("build-state resync")
        if rc2 != 0:
            sys.stderr.write(f"probe: resync hook FAILED (rc={rc2})\n")
            return 1

    sys.stdout.write(f"\nprobe: {f} → EXECUTED {n if n is not None else '?'} actions\n")
    sys.stdout.write(f"probe:   {line}\n")
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
