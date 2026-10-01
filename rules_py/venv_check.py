# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Check one distribution's built venv: the properties venv.bzl promises, run, not inspected.

W341: these were tests in hooks/tests/test_venv_artifact.py, each sweeping every distribution from
the repo root. Here they are one check a distribution runs over its own `.venv`, so each repo after
the split (W317) carries it without needing the others' trees.

    venv_check.py VENV DIST [SUITE_DIR]

Exit 0 when every check holds; 1 with one line per finding otherwise. Each check RUNS the thing it
claims, because venv.bzl's first draft built a well-formed link to nothing and the target was green.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# A direct run that reached the shell or the wrong interpreter must fail, not hang.
_TIMEOUT_S = 60
_USAGE = "usage: venv_check.py VENV DIST [SUITE_DIR]"
_MIN_ARGS = 2
_MAX_ARGS = 3


def _run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    stdin: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
        timeout=_TIMEOUT_S,
        cwd=cwd,
        input=stdin,
        env=env,
    )


def check_link(venv: Path) -> list[str]:
    """Check the interpreter and the PYTHONHOME note beside it.

    Under `bazel-bin` the interpreter is a symlink, and it must be ABSOLUTE: a relative one is
    valid at one depth only and dangled inside a runfiles tree (measured 2026-09-19). Under a
    sandbox bazel hardlinks the resolved file instead, so a regular file is accepted, and either
    form needs `pythonhome.runfiles`, the repo name the checker sets PYTHONHOME from.

    Returns:
        one finding per failed property; empty when all hold.

    """
    py = venv / "bin" / "python3"
    if not py.is_symlink() and not py.is_file():
        return [f"{py}: no interpreter (does the BUILD call venv_from_hub?)"]
    note = venv / "pythonhome.runfiles"
    if not note.is_file():
        return [f"{note}: missing; a sandboxed run has no PYTHONHOME to set"]
    repo = note.read_text(encoding="utf-8").strip()
    if not repo or "/" in repo:
        return [f"{note}: holds {repo!r}, not a repo name"]
    if not py.is_symlink():
        return []
    target = str(py.readlink())
    findings = []
    if not target.startswith("/"):
        findings.append(f"{py}: relative link {target!r}; it dangles at another depth")
    if f"/{repo}/bin/python3" not in target:
        findings.append(f"{py}: links to {target!r}, but the note names {repo!r}")
    return findings


def check_runs(venv: Path, dist: str) -> list[str]:
    """Check the interpreter starts, and imports the distribution's own package.

    A venv built from `deps` alone holds the dependencies but not the project; `srcs` supplies it,
    and this is where that substitution is shown to have worked.

    Returns:
        one finding per failed property; empty when both hold.

    """
    py = str(venv / "bin" / "python3")
    version = _run([py, "-c", "import sys; print(sys.version.split()[0])"])
    if version.returncode != 0 or not version.stdout.startswith("3."):
        return [f"{py}: did not run (rc={version.returncode}): {version.stderr.strip()[:200]}"]
    own = _run([py, "-c", f"import mikemol.{dist}"])
    if own.returncode != 0:
        last = own.stderr.strip().splitlines()[-1:]
        return [f"{py}: cannot import mikemol.{dist} (does venv_from_hub pass srcs?) {last}"]
    return []


def check_entries(venv: Path, dist: str) -> list[str]:
    """Check every console script runs under Python, through a shell, as a person types it.

    A shebang-less entry is run by the shell as a script (`import: command not found`, measured
    2026-09-23). `PYTHONPROFILEIMPORTTIME` makes a CPython write `import time:` to stderr, which
    proves an interpreter ran the file and shows whether it reached the distribution's package.

    Returns:
        one finding per failing entry; empty when every entry holds, or there are none.

    """
    findings = []
    for script in sorted((venv / "bin").glob("*")):
        if script.name == "python3" or script.is_symlink():
            continue
        proc = _run(
            ["/bin/sh", "-c", 'exec "$0"', str(script)],
            stdin="{}",
            env={"PATH": "/usr/bin:/bin", "PYTHONPROFILEIMPORTTIME": "1"},
        )
        if "command not found" in proc.stderr or "import time:" not in proc.stderr:
            findings.append(f"{script}: no Python interpreter ran it: {proc.stderr.strip()[:200]}")
        elif f"mikemol.{dist}" not in proc.stderr:
            findings.append(f"{script}: ran, but never imported mikemol.{dist}")
    return findings


def check_suite(venv: Path, suite: Path) -> list[str]:
    """Check the venv collects the distribution's own suite, as the host venv would.

    Returns:
        one finding when collection fails; empty when it succeeds.

    """
    py = str(venv / "bin" / "python3")
    proc = _run(
        [py, "-m", "pytest", "tests/", "-q", "--no-header", "-p", "no:cacheprovider", "--co"],
        cwd=suite,
    )
    if proc.returncode != 0 or "tests collected" not in proc.stdout:
        return [f"{py}: could not collect {suite}/tests (rc={proc.returncode})"]
    return []


def check(venv: Path, dist: str, suite: Path | None = None) -> list[str]:
    """Run every check on one distribution's venv.

    Returns:
        every finding, in check order; empty when the venv holds all of them.

    """
    findings = check_link(venv)
    if findings:
        return findings
    findings = check_runs(venv, dist)
    if findings:
        return findings
    findings = check_entries(venv, dist)
    if suite is not None:
        findings += check_suite(venv, suite)
    return findings


def main(argv: list[str]) -> int:
    """Check the venv named on the command line.

    Returns:
        0 when every check holds, 1 on findings, 2 on a usage error.

    """
    if not _MIN_ARGS <= len(argv) <= _MAX_ARGS:
        sys.stderr.write(_USAGE + "\n")
        return 2
    suite = Path(argv[2]) if len(argv) == _MAX_ARGS else None
    findings = check(Path(argv[0]), argv[1], suite)
    for finding in findings:
        sys.stderr.write(finding + "\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
