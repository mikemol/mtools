# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Dry-run privacy audit of one dist's tracked tree, judged by the Rego sets (W1192, W1144).

    OPA_BIN=<opa> mikemol-privacy-audit REPO DIST

reads the files `git ls-files` names under DIST, hands the paths and lines to the pinned opa in ONE
evaluation of `data.mtools.publish_privacy.findings`, and prints one JSON line per finding:
`{"kind", "rule", "path", "line"}`, then one summary line. It writes nothing and changes nothing.

⚑ A FINDING NAMES THE RULE, THE FILE AND THE LINE, NEVER THE MATCHED TEXT: this output goes to logs
and cards, so echoing a secret would publish it a second time.

⚑ THE POLICY IS THE ONLY JUDGE. No pattern lives in this module; a rule is added in
`hooks/policy/publish_privacy.rego` with its witness and control, and this reader needs no edit.

⚑ NO LINK IS READ THROUGH. A tracked symlink is counted as skipped, never opened, and a binary file
(a NUL in its first 8 KiB) is counted as skipped, not decoded.

CONSUMED BY: the publish preflight (W1150) and the history pass (W1193).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Sequence

QUERY = "data.mtools.publish_privacy.findings"
SNIFF = 8192
ARGC = 2
POLICY = Path(__file__).parents[3] / "policy" / "publish_privacy.rego"
Finding = dict[str, object]


def run_command(argv: Sequence[str]) -> tuple[int, str, str]:
    """Run a command with no timeout.

    Returns:
        its exit status, standard output and standard error; (127, "", why) when it cannot start.

    """
    try:
        done = subprocess.run(list(argv), capture_output=True, text=True, check=False)
    except OSError as exc:
        return 127, "", f"{type(exc).__name__}: {exc}"
    return done.returncode, done.stdout, done.stderr


def tracked(root: Path, dist: str) -> list[str]:
    """Name the files git tracks under `dist`, as repo-relative paths.

    Returns:
        the paths in git's order.

    Raises:
        OSError: when git is not installed or refuses.

    """
    git = shutil.which("git")
    if git is None:
        msg = "git is not installed"
        raise OSError(msg)
    status, out, err = run_command([git, "-C", str(root), "ls-files", "-z", "--", dist])
    if status != 0:
        msg = f"git ls-files exited {status}: {err.strip()[:200]}"
        raise OSError(msg)
    return [p for p in out.split("\0") if p]


def files_of(root: Path, paths: Sequence[str]) -> tuple[list[Finding], int]:
    """Read each tracked path as lines of text, skipping links, binaries and unreadable files.

    Returns:
        the `files` input of the bulk rule and the number of paths skipped.

    """
    files: list[Finding] = []
    skipped = 0
    for path in paths:
        full = root / path
        if full.is_symlink() or not full.is_file():
            skipped += 1
            continue
        raw = full.read_bytes()
        if b"\0" in raw[:SNIFF]:
            files.append({"path": path, "lines": []})
            skipped += 1
            continue
        files.append({"path": path, "lines": raw.decode("utf-8", "replace").splitlines()})
    return files, skipped


def order(finding: Finding) -> tuple[str, int, str]:
    """Sort key: path, then line, then rule.

    Returns:
        the finding's key.

    """
    return str(finding["path"]), int(cast("int", finding["line"])), str(finding["rule"])


def judge(opa: str, policy: Path, files: list[Finding]) -> list[Finding]:
    """Evaluate the bulk rule over `files` with one opa run.

    Returns:
        the findings, sorted by path, line and rule.

    Raises:
        RuntimeError: when opa fails, so a broken judge is never read as a clean tree.

    """
    document: Finding = {"files": files}
    with tempfile.TemporaryDirectory() as scratch:
        source = Path(scratch) / "input.json"
        source.write_text(json.dumps(document), encoding="utf-8")
        argv = [opa, "eval", "--format", "json", "-i", str(source), "-d", str(policy), QUERY]
        status, out, err = run_command(argv)
    if status != 0:
        msg = f"opa exited {status}: {err.strip()[:200]}"
        raise RuntimeError(msg)
    body = cast("dict[str, list[dict[str, list[dict[str, object]]]]]", json.loads(out))
    found = body["result"][0]["expressions"][0]["value"] if body.get("result") else []
    return sorted(cast("list[Finding]", found), key=order)


def run(args: Sequence[str]) -> int:
    """Run `REPO DIST`: finding lines, then a summary line; exit 1 if any finding is a deny.

    Returns:
        0 when no deny was found, 1 when one was, 2 for a usage error or a missing judge.

    """
    opa = os.environ.get("OPA_BIN", "")
    if len(args) != ARGC or not opa:
        sys.stderr.write("usage: OPA_BIN=<opa> mikemol-privacy-audit REPO DIST\n")
        return 2
    root = Path(args[0])
    files, skipped = files_of(root, tracked(root, args[1]))
    findings = judge(opa, POLICY, files)
    sys.stdout.writelines(json.dumps(f, sort_keys=True) + "\n" for f in findings)
    denies = sum(1 for f in findings if f["kind"] == "deny")
    summary: Finding = {
        "dist": args[1],
        "files": len(files),
        "skipped": skipped,
        "deny": denies,
        "withheld": len(findings) - denies,
    }
    sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
    return 1 if denies else 0


def main() -> None:
    """Console entry: exit with `run`'s status."""
    sys.exit(run(sys.argv[1:]))
