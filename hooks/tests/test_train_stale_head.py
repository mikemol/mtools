# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A train judges a group that needs an admission on the HEAD the groups before it landed (W2335).

The real pace, the real landing refusal and real git, through `traindrive.drive`: no seam supplies
the landed HEAD, the groups before the one under test actually land it. These are github-14's
witnesses a, b and c of the eca6bf2b review, with the assertions the fix makes true.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mikemol.hooks import admission, ratchet_pace, stackrun, stacksnap, traindrive
from mikemol.hooks import commit_kata as ck
from mikemol.hooks.trainjoin import Follower

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_EXECUTABLE = 0o755
_GATE = "#!/bin/sh\nexit 0\n"
_PUSH = "#!/bin/sh\ngit push origin HEAD:main\n"
_MODE = "100644"
_QUEUE = ".claude/paths-forward.json"
_BORN = "born.json"
_RB = "rebaselines.json"
_RECORD = "11111111-1111-1111-1111-111111111111:1041"
_PY = 'dependencies = ["mikemol_x-1.0.0+gaaaaaaa-py3-none-any.whl"]\n'
_LINE = 'extra = "real change"\n'
_TOML = "pyproject.toml"
_RATCHET = "a.txt"
_NEW_SHA = "bbbbbbb"


def _git(root: Path, *args: str) -> str:
    return ck.run_git_in(list(args), {}, root).stdout


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    for key, value in {
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(tmp_path),
    }.items():
        monkeypatch.setenv(key, value)
    remote = tmp_path / "origin.git"
    remote.mkdir()
    _git(remote, "init", "--quiet", "--bare", "-b", "main")
    root = tmp_path / "repo"
    (root / ".claude").mkdir(parents=True)
    _git(root, "init", "--quiet", "-b", "main")
    (root / _QUEUE).write_text('{"waypoints": []}', encoding="utf-8")
    (root / _TOML).write_text(_PY, encoding="utf-8")
    (root / _RATCHET).write_text("original\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    _git(root, "remote", "add", "origin", str(remote))
    _git(root, "push", "--quiet", "origin", "HEAD:main")
    for hook_name, text in (("pre-commit", _GATE), ("post-commit", _PUSH)):
        hook = root / ".git" / "hooks" / hook_name
        hook.write_text(text, encoding="utf-8")
        hook.chmod(_EXECUTABLE)
    return root


def _env(tmp_path: Path) -> dict[str, str]:
    # A pace owing the ratchet file `a.txt`: only a stack touching it is a paydown.
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = {
        "repo": "repo",
        "ratchet": _RATCHET,
        "state": "behind",
        "observed": "0",
        "required": "1",
    }
    pace = tmp_path / "pace.json"
    head: dict[str, object] = {"as_of": stamp, "window": "10"}
    pace.write_text(f"{json.dumps(head)}\n{json.dumps(row)}\n", encoding="utf-8")
    return {ratchet_pace.ENV: str(pace)}


def _seams(
    root: Path, env: dict[str, str], rows: list[admission.Row] | None = None
) -> stackrun.Seams:
    held = rows or []
    return stackrun.Seams(
        run=ck.run_git_in,
        namespace=root.parent / "gate",
        message_of=lambda item: f"{item.subject}\n\nWaypoint: {item.waypoint}\n",
        published=lambda _sha: "PUSHED",
        admission=lambda planned: ratchet_pace.admitted_ident(root, planned, env, held),
        landing_refusal=lambda planned: ratchet_pace.landing_refusal(root, planned, env, held),
        needs_admission=lambda planned: ratchet_pace.needs_admission(root, planned, env),
    )


def _freeze(root: Path, path: str, text: str) -> stacksnap.Frozen:
    target = root / path
    keep = target.read_text(encoding="utf-8") if target.exists() else None
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    blob = _git(root, "hash-object", "-w", path).strip()
    if keep is None:
        target.unlink()
    else:
        target.write_text(keep, encoding="utf-8")
    return stacksnap.Frozen(path, _MODE, blob)


def _birth(root: Path) -> tuple[admission.Row, stackrun.Item]:
    entry: dict[str, object] = {
        "ratchet": _BORN,
        "old": 0,
        "new": 3,
        "reason": "birth",
        "warrant": _RECORD,
    }
    body: dict[str, object] = {"rebaselines": [entry]}
    born = _freeze(root, _BORN, "{}\n")
    stored = _freeze(root, _RB, json.dumps(body))
    row = admission.Row(
        repo="repo",
        card="WB",
        review="r",
        kind=admission.BIRTH,
        blobs={_BORN: born.blob, _RB: stored.blob},
        ratchet=_BORN,
        old=0,
        new=3,
        record=_RECORD,
    )
    return row, stackrun.Item("WB", "birth", "", (_BORN, _RB), (born, stored))


def _paydown(root: Path, other: tuple[str, str]) -> Follower:
    # Group 1: pays the owed ratchet down and also writes the other file it is given.
    files = (_freeze(root, _RATCHET, "paid\n"), _freeze(root, other[0], other[1]))
    return Follower("1", (stackrun.Item("W1", "paydown", "", (_RATCHET, other[0]), files),))


def _repin(root: Path, text: str) -> Follower:
    # A repin brings the wheel its text names (D3), so the new sha is carried by a wheel too.
    wheel = f"vendor/wheels/mikemol_x-1.0.0+g{_NEW_SHA}-py3-none-any.whl"
    files = (_freeze(root, _TOML, text), _freeze(root, wheel, "new wheel\n"))
    return Follower("2", (stackrun.Item("W2", "repin", "", (_TOML, wheel), files),))


def _verdicts(got: list[traindrive.Verdict]) -> dict[str, traindrive.Verdict]:
    return {v.key: v for v in got}


def test_a_birth_does_not_land_over_a_file_the_group_before_it_landed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """a: group 1 lands born.json; the birth is judged on that HEAD and refused, not landed."""
    root = _repo(tmp_path, monkeypatch)
    env = _env(tmp_path)
    row, birth = _birth(root)
    one = _paydown(root, (_BORN, "PEER\n"))
    train = [one, Follower("2", (birth,))]
    got = _verdicts(traindrive.drive(root, train, _seams(root, env, [row])))
    assert got["1"].code == 0
    assert got["2"].code != 0
    assert "already exists at HEAD" in got["2"].text
    assert _git(root, "show", f"HEAD:{_BORN}") == "PEER\n"


def test_a_repin_does_not_undo_the_line_the_group_before_it_landed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """b: a repin frozen from the old file would drop group 1's line; judged on HEAD, it refuses."""
    root = _repo(tmp_path, monkeypatch)
    env = _env(tmp_path)
    one = _paydown(root, (_TOML, _PY + _LINE))
    two = _repin(root, _PY.replace("gaaaaaaa", "gbbbbbbb"))
    got = _verdicts(traindrive.drive(root, [one, two], _seams(root, env)))
    assert got["1"].code == 0
    assert got["2"].code != 0
    assert "real change" in _git(root, "show", f"HEAD:{_TOML}")


def test_a_clean_repin_of_the_text_the_group_before_it_landed_is_admitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """c: a repin frozen on group 1's text is a clean repin of the landed HEAD, not a refusal."""
    root = _repo(tmp_path, monkeypatch)
    env = _env(tmp_path)
    one = _paydown(root, (_TOML, _PY + _LINE))
    two = _repin(root, (_PY + _LINE).replace("gaaaaaaa", "gbbbbbbb"))
    got = _verdicts(traindrive.drive(root, [one, two], _seams(root, env)))
    assert got["1"].code == 0
    assert got["2"].code == 0
    assert "gbbbbbbb" in _git(root, "show", f"HEAD:{_TOML}")


def test_the_stack_seams_the_commit_builds_carry_the_pace_questions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N-A: a seam left out of the commit's construction restores the stale-HEAD landing."""
    root = _repo(tmp_path, monkeypatch)
    seams = ck.stack_seams(root, _env(tmp_path), ck.DEFAULT_TRAILER)
    plain = [stackrun.Item("W9", "plain", "", ("b.txt",))]
    paying = [stackrun.Item("W9", "pays", "", (_RATCHET,))]
    assert seams.needs_admission(plain)
    assert not seams.needs_admission(paying)
    assert seams.landing_refusal(plain) is not None
    assert seams.landing_refusal(paying) is None
