# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run each dist's OWN tests from its built sdist in a clean venv, off this host (W1147, W1143).

    mikemol-wheel sdist-tests OUT [DIST...]

OUT is a `release-check` output directory: one folder per dist holding its sdist and its wheel. For
each dist (or only the named ones) this extracts the sdist into a scratch directory, makes a fresh
venv, installs the dist's built WHEEL plus the test runner there, and runs the extracted tree's
tests. A package published to an index must pass its own tests with nothing from this host: no
bazel, no checkout path, no sibling checkout.

⚑ SIBLINGS COME FROM THE BUILT WHEELS: a dist that depends on another (`mikemol-atomicwrite`) finds
it through `--find-links` over every wheel under OUT, the same artifacts the index will serve after
the first upload; a third-party dependency comes from the public index.

⚑ THE TEST RUNNER IS THE ONLY EXTRA: dev tools a test needs (mypy, ruff) are NOT installed, so a
test that shells out to one fails here and is reported with its tail, not skipped.

⚑ NO WALL-CLOCK TIMEOUT (operator, standing): a hang is seen as a hang. pytest's own
`faulthandler_timeout` dumps stacks and kills nothing.

CONSUMED BY: `mikemol-wheel sdist-tests`, the off-host test preflight (W1147).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

USAGE = 2
NOT_FOUND = 127
COUNTS = re.compile(r"(\d+) (passed|failed|error|skipped)")
TAIL = 600
Row = dict[str, object]
Runner = Callable[[Sequence[str], Path], tuple[int, str]]


def run_command(argv: Sequence[str], cwd: Path) -> tuple[int, str]:
    """Run a command in `cwd` and read both streams.

    Returns:
        its exit status and its combined output; (127, why) when it cannot start.

    """
    try:
        done = subprocess.run(list(argv), cwd=cwd, capture_output=True, text=True, check=False)
    except OSError as exc:
        return NOT_FOUND, f"{type(exc).__name__}: {exc}"
    return done.returncode, done.stdout + done.stderr


def counts_of(output: str) -> dict[str, int]:
    """Read pytest's summary counts from its last lines.

    Returns:
        the number of passed, failed, error and skipped tests it names (absent ones omitted).

    """
    found: dict[str, int] = {}
    for line in output.strip().splitlines()[-3:]:
        for match in COUNTS.finditer(line):
            found[str(match.group(2))] = int(match.group(1))
    return found


def dists_in(out: Path, wanted: Sequence[str]) -> list[Path]:
    """List the dist folders of OUT, or only the named ones.

    Returns:
        their directories, in name order.

    """
    folders = sorted(p for p in out.iterdir() if p.is_dir() and not p.is_symlink())
    return [p for p in folders if not wanted or p.name in wanted]


def install(home: Path, wheel: Path, links: Path, runner: Runner) -> str | None:
    """Make the venv and install the wheel and the test runner into it.

    Returns:
        None when it worked, else the tail of the output of the step that failed.

    """
    python = home / "venv" / "bin" / "python"
    pip = [str(python), "-m", "pip", "install", "--quiet", "--find-links", str(links)]
    for argv in ([sys.executable, "-m", "venv", str(home / "venv")], [*pip, str(wheel), "pytest"]):
        status, said = runner(argv, home)
        if status != 0:
            return said[-TAIL:]
    return None


def check_dist(folder: Path, links: Path, runner: Runner) -> Row:
    """Install one dist's wheel in a fresh venv and run the extracted sdist's tests.

    Returns:
        the row: `dist`, `ok`, the pytest counts, and on a failure the tail of the output.

    """
    sdists, wheels = sorted(folder.glob("*.tar.gz")), sorted(folder.glob("*.whl"))
    if len(sdists) != 1 or len(wheels) != 1:
        return {"dist": folder.name, "ok": False, "detail": "expected one sdist and one wheel"}
    with tempfile.TemporaryDirectory() as scratch:
        home = Path(scratch)
        with tarfile.open(sdists[0]) as archive:
            archive.extractall(home / "src", filter="data")
        tree = next((home / "src").iterdir())
        if not (tree / "tests").is_dir():
            return {"dist": folder.name, "ok": True, "detail": "no tests directory"}
        failure = install(home, wheels[0], links, runner)
        if failure is not None:
            return {"dist": folder.name, "ok": False, "stage": "install", "detail": failure}
        python = str(home / "venv" / "bin" / "python")
        argv = [python, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"]
        status, said = runner([*argv, "-o", "faulthandler_timeout=60"], tree)
    row: Row = {"dist": folder.name, "ok": status == 0, **counts_of(said)}
    if status != 0:
        row["detail"] = said[-TAIL:]
    return row


def run(args: Sequence[str], runner: Runner = run_command) -> int:
    """Run `OUT [DIST...]`: one JSON line per dist.

    Returns:
        0 when every dist's tests passed, 1 when one did not, 2 for a usage error.

    """
    if not args or not Path(args[0]).is_dir():
        sys.stderr.write("usage: mikemol-wheel sdist-tests OUT [DIST...]\n")
        return USAGE
    out = Path(args[0]).resolve()
    folders = dists_in(out, args[1:])
    if not folders:
        sys.stderr.write("sdist-tests: no dist folder found\n")
        return USAGE
    failed = 0
    with tempfile.TemporaryDirectory() as flat:
        links = Path(flat)
        for wheel in out.glob("*/*.whl"):
            shutil.copy2(wheel, links / wheel.name)
        for folder in folders:
            row = check_dist(folder, links, runner)
            sys.stdout.write(json.dumps(row, sort_keys=True) + "\n")
            sys.stdout.flush()
            failed += int(row["ok"] is not True)
    return 1 if failed else 0
