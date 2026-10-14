# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the dry-run privacy audit of a dist's tracked tree (W1192).

⚑ THE PLANTED FILES ARE BUILT AT TEST TIME from fragments, so this file does not itself match the
rules it plants against. ⚑ THE JUDGE IS THE REAL opa (`OPA_BIN`, pinned by bazel) over the real
policy; nothing here re-implements a rule. ⚑ THE CONTROLS ARE AN UNTRACKED SECRET AND A CLEAN DIST:
an untracked file is not published, and a clean tree must exit 0.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.hooks import privacy_audit

if TYPE_CHECKING:
    from pathlib import Path

_OPA = os.environ.get("OPA_BIN") or shutil.which("opa") or ""
pytestmark = pytest.mark.skipif(not _OPA, reason="no opa to judge with")
_TWO = 2
_THREE = 3
Row = dict[str, object]


def _git(root: Path, *args: str) -> None:
    git = shutil.which("git")
    assert git is not None
    ident = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run([git, "-C", str(root), *ident, *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "demo").mkdir(parents=True)
    (root / "demo" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    home = "see /ho" + "me/someone/work for more\n"
    (root / "demo" / "notes.md").write_text("fine\n" + home, encoding="utf-8")
    key = "KEY = 'AKIA" + "ABCDEFGHIJKLMNOP'\n"
    (root / "demo" / "settings.py").write_text(key, encoding="utf-8")
    (root / "demo" / "blob.bin").write_bytes(b"\0\1\2AKIA" + b"ABCDEFGHIJKLMNOP")
    (root / "demo" / "link.txt").symlink_to("mod.py")
    (root / "demo" / ".env").write_text("A=1\n", encoding="utf-8")
    (root / "other").mkdir()
    (root / "other" / "ok.py").write_text("y = 2\n", encoding="utf-8")
    (root / "demo" / "untracked.pem").write_text("never added\n", encoding="utf-8")
    _git(root, "init", "--quiet", "-b", "main")
    _git(root, "add", "demo/mod.py", "demo/notes.md", "demo/settings.py", "demo/blob.bin")
    _git(root, "add", "demo/link.txt", "demo/.env", "other/ok.py")
    _git(root, "commit", "--quiet", "-m", "x")
    return root


def _audit(
    root: Path,
    dist: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[int, list[Row], str]:
    monkeypatch.setenv("OPA_BIN", _OPA)
    status = privacy_audit.run([str(root), dist])
    out = capsys.readouterr().out
    return status, [cast("Row", json.loads(line)) for line in out.splitlines()], out


def test_planted_secrets_are_found_by_rule_path_and_line_and_the_exit_is_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The env file, the key line and the home path are findings; a deny makes the exit 1."""
    status, lines, _ = _audit(_repo(tmp_path), "demo", capsys, monkeypatch)
    findings = {(f["kind"], f["rule"], f["path"], f["line"]) for f in lines[:-1]}
    assert findings == {
        ("deny", "env-file", "demo/.env", 0),
        ("deny", "aws-access-key", "demo/settings.py", 1),
        ("withheld", "home-path", "demo/notes.md", _TWO),
    }
    assert status == 1


def test_the_output_never_carries_the_matched_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control for the whole mode: neither the key nor the home directory name is printed."""
    _, _, out = _audit(_repo(tmp_path), "demo", capsys, monkeypatch)
    assert "ABCDEFGHIJKLMNOP" not in out
    assert "someone" not in out


def test_an_untracked_secret_a_link_and_a_binary_are_not_findings_and_are_counted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`untracked.pem` is unpublished, the link is not read through, the NUL file is not decoded."""
    _, lines, _ = _audit(_repo(tmp_path), "demo", capsys, monkeypatch)
    paths = {f["path"] for f in lines[:-1]}
    assert not paths & {"demo/untracked.pem", "demo/link.txt", "demo/blob.bin"}
    summary = lines[-1]
    assert summary["skipped"] == _TWO
    assert summary["deny"] == _TWO
    assert summary["withheld"] == 1


def test_a_clean_dist_has_no_findings_and_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other dist holds one clean file: the summary only, and the exit is 0."""
    status, lines, _ = _audit(_repo(tmp_path), "other", capsys, monkeypatch)
    assert status == 0
    assert lines == [
        {"deny": 0, "dist": "other", "files": 1, "mode": "tree", "skipped": 0, "withheld": 0}
    ]


def test_several_dists_are_each_audited_with_a_summary_and_one_deny_fails_the_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`other` is clean and listed after the dirty `demo`: both get a summary, the exit is 1."""
    root = _repo(tmp_path)
    monkeypatch.setenv("OPA_BIN", _OPA)
    status = privacy_audit.run([str(root), "demo", "other"])
    rows = [cast("Row", json.loads(x)) for x in capsys.readouterr().out.splitlines()]
    summaries = [r for r in rows if "mode" in r]
    assert [(s["dist"], s["deny"]) for s in summaries] == [("demo", _TWO), ("other", 0)]
    assert status == 1


def _history_repo(tmp_path: Path) -> tuple[Path, str]:
    """Build a repo whose only secret was added in one commit and deleted in the next.

    Returns:
        the repository's root and the sha of the commit that added the secret.

    """
    root = tmp_path / "hist"
    (root / "demo").mkdir(parents=True)
    _git(root, "init", "--quiet", "-b", "main")
    (root / "demo" / "mod.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
    _git(root, "add", "demo/mod.py")
    _git(root, "commit", "--quiet", "-m", "one")
    key = "a = 1\nb = 2\nKEY = 'AKIA" + "ABCDEFGHIJKLMNOP'\n"
    (root / "demo" / "mod.py").write_text(key, encoding="utf-8")
    _git(root, "commit", "--quiet", "-am", "two")
    added = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    (root / "demo" / "mod.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
    _git(root, "commit", "--quiet", "-am", "three")
    return root, added


def test_a_secret_added_and_later_deleted_is_in_history_and_not_in_the_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The case the tree cannot see: the tree audit is clean, the history audit names the commit."""
    root, added = _history_repo(tmp_path)
    tree_status, tree, _ = _audit(root, "demo", capsys, monkeypatch)
    assert tree_status == 0
    assert tree[-1]["deny"] == 0
    monkeypatch.setenv("OPA_BIN", _OPA)
    status = privacy_audit.run(["--history", str(root), "demo"])
    out = capsys.readouterr().out
    rows = [cast("Row", json.loads(line)) for line in out.splitlines()]
    assert rows[:-1] == [
        {
            "commit": added,
            "kind": "deny",
            "line": _THREE,
            "path": "demo/mod.py",
            "rule": "aws-access-key",
        }
    ]
    assert rows[-1]["mode"] == "history"
    assert status == 1
    assert "ABCDEFGHIJKLMNOP" not in out


def test_a_failing_judge_is_an_error_and_never_a_clean_tree() -> None:
    """A broken opa raises, so no reader mistakes a dead judge for an empty finding list."""
    with pytest.raises(RuntimeError, match="opa exited"):
        privacy_audit.judge("false", privacy_audit.POLICY, [])


def test_the_wrong_arguments_or_no_judge_is_a_usage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """No `OPA_BIN` and a missing DIST each exit 2, and nothing is read."""
    monkeypatch.delenv("OPA_BIN", raising=False)
    assert privacy_audit.run(["repo", "demo"]) == _TWO
    monkeypatch.setenv("OPA_BIN", "opa")
    assert privacy_audit.run(["repo"]) == _TWO
