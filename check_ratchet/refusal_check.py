# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Check one distribution's ratchet REFUSES a new finding.

A lowering that refuses nothing is a deletion wearing a paydown's name.

W388, ported from hooks/tests/test_bar_fires.py's test_every_emptied_baseline_arms_a_refusal,
which looped over every distribution from the repo root. A copy of the distribution gets a planted
module carrying a preview finding (a comparison to an empty string, and a docstring with no
Returns section), and the ratchet must exit nonzero naming it.

The original checked only EMPTIED baselines, to avoid a planted finding colliding with a
baselined one. A baseline key is path-qualified and the plant is a new file, so its findings
cannot match any key: the property holds for every baseline, emptied or not, and this checks it
in every distribution (all 14 baselines were empty when this was written).

    refusal_check.py RATCHET RUFF PYPROJECT

Exit 0 when the ratchet refuses the plant; 1 when it tolerates it or the copy is unusable; 2 on
usage.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

_USAGE = "usage: refusal_check.py RATCHET RUFF PYPROJECT"
_ARGS = 3
_TIMEOUT_S = 300
_PROBE = "_probe.py"
_PLANT = (
    "# SPDX-License-Identifier: Apache-2.0\n"
    "# Copyright (c) 2026 Mike Mol\n"
    '"""A planted finding: a baseline must refuse it, not tolerate it."""\n'
    "\n\n"
    "def f(s: str) -> bool:\n"
    '    """Compare to an empty string."""\n'
    '    return s == ""\n'
)
# Build residue holds pre-paydown copies of the sources; copied, it hands the census findings
# from files that are not the distribution (measured in the original arm's F-arm).
_IGNORE = (".venv", ".mypy_cache", ".ruff_cache", ".pytest_cache", "__pycache__", "build", "dist")

type Ratchet = Callable[[Path], tuple[int, str]]


def ratchet_runner(ratchet: str, ruff: str) -> Ratchet:
    """Run the ratchet CLI over a directory with the pinned ruff.

    Returns:
        a runner giving the ratchet's exit status and its combined output.

    """

    def run(dist: Path) -> tuple[int, str]:
        proc = subprocess.run(
            [ratchet, str(dist)],
            capture_output=True,
            text=True,
            check=False,
            timeout=_TIMEOUT_S,
            env={**os.environ, "RUFF_BIN": ruff},
        )
        return proc.returncode, proc.stdout + proc.stderr

    return run


def check(dist: Path, run: Ratchet) -> list[str]:
    """Plant a finding in a copy of `dist` and require the ratchet to refuse it by name.

    Returns:
        one finding when the ratchet tolerates the plant or the copy has no package; else empty.

    """
    # ⚑ DECLARED AT THE EDGE: ignore_patterns is typed with Any, which disallow_any_expr refuses.
    ignore: Callable[[str, list[str]], set[str]] = shutil.ignore_patterns(*_IGNORE)
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / dist.name
        shutil.copytree(dist, probe, symlinks=False, ignore=ignore)
        packages = sorted(p for p in (probe / "src" / "mikemol").glob("*") if p.is_dir())
        if len(packages) != 1:
            return [f"{dist}: expected one package under src/mikemol, found {len(packages)}"]
        (packages[0] / _PROBE).write_text(_PLANT, encoding="utf-8")
        status, output = run(probe)
    if status == 0 or _PROBE not in output:
        return [
            (
                f"{dist}: the ratchet TOLERATED a planted finding (rc={status}); a baseline "
                f"that refuses nothing is a deletion wearing a paydown's name: "
                f"{output.strip()[:300]}"
            )
        ]
    return []


def main(argv: list[str]) -> int:
    """Check the distribution whose pyproject.toml is named on the command line.

    Returns:
        0 when the ratchet refuses the plant, 1 when it does not, 2 on a usage error.

    """
    if len(argv) != _ARGS:
        sys.stderr.write(_USAGE + "\n")
        return 2
    ratchet, ruff = (str(Path(a).absolute()) for a in argv[:2])
    config = Path(argv[2])
    if not config.is_file():
        sys.stderr.write(f"refusal_check: {config} was not staged; refusing\n")
        return 1
    findings = check(config.absolute().parent, ratchet_runner(ratchet, ruff))
    for finding in findings:
        sys.stderr.write(finding + "\n")
    if not findings:
        sys.stdout.write(f"refusal_check: the ratchet refused the planted finding in {config}\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
