# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-commit REPO --stack FILE` refuses a build file naming a source nothing carries (W1604).

⚑ THE ENTRY POINT IS THE UNDER-TEST, as in `test_commit_stack`: `commit_kata.main` is called with
the argument form and the submit-time refusal is read from what it prints and returns. The lease
is NOT held here (no HELD_ENV), because the refusal sits on the path of a submit that has not yet
taken its turn. ⚑ THE CONTROL: the same stack with the source carried by its own entry is not
refused at submit, so the refusal is the finding and not the stack.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks.snapshot import NAMESPACE_ENV

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_BUILD = 'py_test(name = "t", srcs = ["gone.py"])\n'


def _git(root: Path, *args: str) -> str:
    return ck.run_git_in(list(args), {}, root).stdout


def _no_claim(*_args: object, **_kwargs: object) -> str:
    """Stand in for the fence claim: the lease is neither taken nor refused here (W1696).

    Returns:
        the empty reason, which `main` reads as a lease already held.

    """
    return ""


def _repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, carry_source: bool
) -> tuple[Path, Path]:
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", ck.HELD_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(ck, "claim_of", _no_claim)
    for key, value in {
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(tmp_path),
        NAMESPACE_ENV: str(tmp_path / "gate"),
        ck.ISOLATED_ENV: "1",
    }.items():
        monkeypatch.setenv(key, value)
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet", "-b", "main")
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    (root / "BUILD.bazel").write_text(_BUILD, encoding="utf-8")
    paths = ["BUILD.bazel"]
    if carry_source:
        (root / "gone.py").write_text("x = 1\n", encoding="utf-8")
        paths.append("gone.py")
    stack = tmp_path / "stack.json"
    entries = [{"waypoint": "W1", "subject": "build file", "paths": paths}]
    stack.write_text(json.dumps(entries), encoding="utf-8")
    return root, stack


def test_a_build_file_naming_a_source_no_entry_carries_is_refused_at_submit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit not-committed, the finding names the file and the source, and HEAD does not move."""
    root, stack = _repo(tmp_path, monkeypatch, carry_source=False)
    start = _git(root, "rev-parse", "HEAD").strip()
    assert ck.main([str(root), "--stack", str(stack)]) == ck.EXIT_NOT_COMMITTED
    out = capsys.readouterr().out
    assert "BUILD.bazel names gone.py" in out
    assert _git(root, "rev-parse", "HEAD").strip() == start


def test_the_same_stack_with_its_source_carried_is_not_refused_at_submit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: the build file and its source in one entry pass the submit-time check."""
    root, stack = _repo(tmp_path, monkeypatch, carry_source=True)
    ck.main([str(root), "--stack", str(stack)])
    assert "names gone.py" not in capsys.readouterr().out
