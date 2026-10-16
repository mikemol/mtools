# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Dry-run privacy audit of one dist's tracked tree and history, judged by the Rego sets (W1144).

    OPA_BIN=<opa> mikemol-privacy-audit [--history] REPO DIST

reads the files `git ls-files` names under DIST (W1192), or with `--history` every line that any
commit ever ADDED under DIST (W1193), hands the paths and lines to the pinned opa in ONE evaluation
of `data.mtools.publish_privacy.findings`, and prints one JSON line per finding:
`{"kind", "rule", "path", "line"}` (and `"commit"` in history), then one summary line. It writes
nothing and changes nothing.

⚑ A FINDING NAMES THE RULE, THE FILE AND THE LINE, NEVER THE MATCHED TEXT: this output goes to logs
and cards, so echoing a secret would publish it a second time.

⚑ THE POLICY IS THE ONLY JUDGE. No pattern lives in this module; a rule is added in
`hooks/policy/publish_privacy.rego` with its witness and control, and this reader needs no edit.

⚑ NO LINK IS READ THROUGH. A tracked symlink is counted as skipped, never opened, and a binary file
(a NUL in its first 8 KiB) is counted as skipped, not decoded.

⚑ HISTORY IS THE CASE THE TREE CANNOT SEE: a key added and then deleted is gone from `ls-files` and
is still in every clone. A history entry is one (commit, path) with the lines that commit added,
placed at their NEW line numbers (the rest empty), so a finding's line is the line in that commit.

CONSUMED BY: the publish preflight (W1150).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import cast

QUERY = "data.mtools.publish_privacy.findings"
SNIFF = 8192
ARGC = 2
HISTORY_FLAG = "--history"
COMMIT_MARK = "commit\t"
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")
POLICY = Path(__file__).parents[3] / "policy" / "publish_privacy.rego"
POLICY_ENV = "MIKEMOL_PRIVACY_POLICY"
NO_JUDGE = 2
Finding = dict[str, object]


def policy_path() -> Path:
    """Find the Rego policy: the one the environment names, else the one beside this checkout.

    ⚑ AN INSTALLED COPY HAS NO `policy/` BESIDE IT (W1211): the wheel carries the module, not the
    repository's policy directory, so the first real run through the installed script died on a
    missing file. `MIKEMOL_PRIVACY_POLICY` names it until the policy ships as package data (W1212).

    Returns:
        the policy file's path.

    """
    named = os.environ.get(POLICY_ENV, "")
    return Path(named) if named else POLICY


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


def git_out(root: Path, *args: str) -> str:
    """Run git in `root` and return its standard output.

    Returns:
        git's standard output.

    Raises:
        OSError: when git is not installed or refuses.

    """
    git = shutil.which("git")
    if git is None:
        msg = "git is not installed"
        raise OSError(msg)
    status, out, err = run_command([git, "-C", str(root), *args])
    if status != 0:
        msg = f"git {args[0]} exited {status}: {err.strip()[:200]}"
        raise OSError(msg)
    return out


def tracked(root: Path, dist: str) -> list[str]:
    """Name the files git tracks under `dist`, as repo-relative paths.

    Returns:
        the paths in git's order.

    """
    return [p for p in git_out(root, "ls-files", "-z", "--", dist).split("\0") if p]


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


def added_lines(log: str) -> list[Finding]:
    """Parse `git log -p -U0` text into (commit, path) entries of the lines each commit added.

    Returns:
        one entry per commit and path, its lines at their new line numbers, the rest empty.

    """
    entries: list[Finding] = []
    commit = ""
    lines: list[str] | None = None
    at = 0
    for row in log.splitlines():
        if row.startswith(COMMIT_MARK):
            commit = row.removeprefix(COMMIT_MARK)
            lines = None
        elif row.startswith("+++ "):
            target = row.removeprefix("+++ ").split("\t")[0]
            lines = None
            if target.startswith("b/"):
                lines = []
                path = target.removeprefix("b/")
                entries.append({"commit": commit, "path": path, "lines": lines})
        elif lines is not None and (hunk := HUNK.match(row)):
            at = int(hunk.group(1)) - 1
        elif lines is not None and row.startswith("+"):
            lines.extend([""] * (at - len(lines)))
            lines.append(row.removeprefix("+"))
            at += 1
    return entries


def history_of(root: Path, dist: str) -> list[Finding]:
    """Read every line any commit added under `dist`, across all history.

    Returns:
        the `files` input of the bulk rule, one entry per (commit, path).

    """
    args = ("log", "--all", "-p", "-U0", "--no-color", "--no-ext-diff", "--format=commit\t%H")
    return added_lines(git_out(root, *args, "--", dist))


def order(finding: Finding) -> tuple[str, int, str, str]:
    """Sort key: path, then line, then rule, then commit.

    Returns:
        the finding's key.

    """
    return (
        str(finding["path"]),
        int(cast("int", finding["line"])),
        str(finding["rule"]),
        str(finding.get("commit", "")),
    )


def judge(opa: str, policy: Path, files: list[Finding]) -> list[Finding]:
    """Evaluate the bulk rule over `files` with one opa run.

    Returns:
        the findings, sorted by path, line, rule and commit.

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
    """Run `[--history] REPO DIST`: finding lines, then a summary line; exit 1 on any deny.

    Returns:
        0 when no deny was found, 1 when one was, 2 for a usage error or a missing judge.

    """
    opa = os.environ.get("OPA_BIN", "")
    history = HISTORY_FLAG in args
    words = [a for a in args if a != HISTORY_FLAG]
    if len(words) < ARGC or not opa:
        sys.stderr.write("usage: OPA_BIN=<opa> mikemol-privacy-audit [--history] REPO DIST...\n")
        return 2
    root = Path(words[0])
    total = 0
    for dist in words[1:]:
        try:
            if history:
                files, skipped = history_of(root, dist), 0
            else:
                files, skipped = files_of(root, tracked(root, dist))
            findings = judge(opa, policy_path(), files)
        except Exception as exc:
            if not isinstance(exc, (OSError, RuntimeError)):
                raise
            sys.stderr.write(f"mikemol-privacy-audit: cannot judge {dist}: {exc}\n")
            return NO_JUDGE
        sys.stdout.writelines(json.dumps(f, sort_keys=True) + "\n" for f in findings)
        denies = sum(1 for f in findings if f["kind"] == "deny")
        summary: Finding = {
            "dist": dist,
            "mode": "history" if history else "tree",
            "files": len(files),
            "skipped": skipped,
            "deny": denies,
            "withheld": len(findings) - denies,
        }
        sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
        total += denies
    return 1 if total else 0


def main() -> None:
    """Console entry: exit with `run`'s status."""
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
