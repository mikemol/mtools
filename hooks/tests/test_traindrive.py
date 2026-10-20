# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The merge train gates the joined tip once, bisects a red, lands the green, refuses the bad.

⚑ REAL GIT AND A REAL GATE HOOK: the pre-commit counts its own runs into the real checkout and
refuses when any file in the tree it was handed contains the word `bad`, so "one gate for three
stacks" and "about log2(n) gates for a red" are read from a file the gate wrote, not from the
module. ⚑ THE LOG IS READ BACK: what landed shows as commits on HEAD, and a refused stack as a
commit that is not there.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks import stackrun, traindrive
from mikemol.hooks.trainjoin import Follower

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from mikemol.hooks import trainround

_EXECUTABLE = 0o755
_GATE = (
    '#!/bin/sh\necho run >> "$MIKEMOL_REAL_ROOT/runs"\n'
    'if grep -rq bad --exclude-dir=.git .; then echo "found bad" >&2; exit 1; fi\n'
)
_PUSH = "#!/bin/sh\ngit push origin HEAD:main\n"
_NAMES = ("a.txt", "b.txt", "c.txt")
_THREE = 3


def _git(root: Path, *args: str) -> str:
    return ck.run_git_in(list(args), {}, root).stdout


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, bad: str = "") -> Path:
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
    root.mkdir()
    _git(root, "init", "--quiet", "-b", "main")
    for name in _NAMES:
        (root / name).write_text("original\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    _git(root, "remote", "add", "origin", str(remote))
    _git(root, "push", "--quiet", "origin", "HEAD:main")
    for hook_name, text in (("pre-commit", _GATE), ("post-commit", _PUSH)):
        hook = root / ".git" / "hooks" / hook_name
        hook.write_text(text, encoding="utf-8")
        hook.chmod(_EXECUTABLE)
    for name in _NAMES:
        text = "bad\n" if name == bad else f"edited {name}\n"
        (root / name).write_text(text, encoding="utf-8")
    return root


def _drive(
    root: Path,
    tmp_path: Path,
    paths: tuple[str, ...] = _NAMES,
    rounds: list[trainround.RoundRecord] | None = None,
) -> dict[str, traindrive.Verdict]:
    groups = [
        Follower(key, (stackrun.Item(f"W{key}", f"card {key}", "", (path,)),))
        for key, path in zip(("1", "2", "3"), paths, strict=True)
    ]
    seams = stackrun.Seams(
        run=ck.run_git_in,
        namespace=tmp_path / "gate",
        message_of=lambda item: f"{item.subject}\n\nWaypoint: {item.waypoint}\n",
        published=lambda _sha: "PUSHED",
    )
    on_round = rounds.append if rounds is not None else None
    return {v.key: v for v in traindrive.drive(root, groups, seams, None, on_round)}


def _runs(root: Path) -> int:
    return len((root / "runs").read_text(encoding="utf-8").splitlines())


def _subjects(root: Path) -> list[str]:
    return _git(root, "log", "--format=%s").splitlines()


def test_a_green_queue_is_one_gate_and_every_stack_lands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Three stacks, one gate run, three COMMITTED verdicts, HEAD three commits ahead."""
    root = _repo(tmp_path, monkeypatch)
    got = _drive(root, tmp_path)
    assert _runs(root) == 1
    assert [got[k].code for k in ("1", "2", "3")] == [0, 0, 0]
    assert all("COMMITTED repo" in v.text for v in got.values())
    assert _subjects(root)[:_THREE] == ["card 3", "card 2", "card 1"]


def test_a_bad_middle_stack_is_refused_and_the_rest_land_in_four_gates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tip red, two probes find stack 2, then stacks 1 and 3 land: 1 + 2 + 1 gate runs."""
    root = _repo(tmp_path, monkeypatch, bad="b.txt")
    got = _drive(root, tmp_path)
    assert got["1"].code == 0
    assert got["2"].code != 0
    assert got["3"].code == 0
    assert "found bad" in got["2"].text
    assert "REFUSED repo" in got["2"].text
    assert _runs(root) == len(("tip", "probe", "probe", "rest"))
    assert _subjects(root)[:_THREE] == ["card 3", "card 1", "first"]


def test_a_first_stack_that_fails_alone_is_refused_and_the_others_land(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty prefix: nothing lands before it, the stacks behind it are judged anew."""
    root = _repo(tmp_path, monkeypatch, bad="a.txt")
    got = _drive(root, tmp_path)
    assert got["1"].code != 0
    assert got["2"].code == 0
    assert got["3"].code == 0
    assert _subjects(root)[:_THREE] == ["card 3", "card 2", "first"]


def test_a_stack_that_cannot_be_built_is_not_committed_and_the_rest_go_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A path that is not there drops its stack with NOT COMMITTED; the queue is not refused."""
    root = _repo(tmp_path, monkeypatch)
    got = _drive(root, tmp_path, ("a.txt", "missing.txt", "c.txt"))
    assert got["2"].code != 0
    assert "NOT COMMITTED repo" in got["2"].text
    assert got["1"].code == 0
    assert got["3"].code == 0
    assert _runs(root) == 1


_SUMMARY_GATE = (
    '#!/bin/sh\necho run >> "$MIKEMOL_REAL_ROOT/runs"\n'
    'echo "gate jobs=2 cores=24 load1=39.4 floor=2 (held at the floor)"\n'
    "if grep -rq bad --exclude-dir=.git .; then\n"
    '  echo "pre-commit: REFUSED \u2014 the following check(s) failed:" >&2\n'
    '  echo "  - check_x" >&2\n  exit 1\nfi\n'
)


def _summary_gate(root: Path) -> None:
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text(_SUMMARY_GATE, encoding="utf-8")
    hook.chmod(_EXECUTABLE)


def test_a_green_train_records_one_round_with_the_throttle_the_gate_was_held_to(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W1715: one round, three members, one gate, and the admission line read from its output."""
    root = _repo(tmp_path, monkeypatch)
    _summary_gate(root)
    rounds: list[trainround.RoundRecord] = []
    _drive(root, tmp_path, rounds=rounds)
    [only] = rounds
    assert (only.number, only.members, only.verdict, only.gates) == (1, _THREE, "green", 1)
    assert (only.facts.jobs, only.facts.cores, only.facts.load1) == ("2", "24", "39.4")
    assert not only.failed
    assert only.window[0] <= only.window[1]


def test_a_refusal_records_a_red_round_naming_the_failed_check_then_a_green_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tip red and two probes in round one, with the gate's own summary; the rest land in two."""
    root = _repo(tmp_path, monkeypatch, bad="b.txt")
    _summary_gate(root)
    rounds: list[trainround.RoundRecord] = []
    _drive(root, tmp_path, rounds=rounds)
    shape = [(r.number, r.members, r.verdict, r.gates) for r in rounds]
    assert shape == [(1, _THREE, "red", _THREE), (2, 1, "green", 1)]
    assert rounds[0].failed == "check_x"
    assert not rounds[1].failed


def test_an_unbuildable_stack_is_an_unbuilt_round_and_the_next_round_is_green(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The build fails before any gate: no gates, no facts, then the rest go on."""
    root = _repo(tmp_path, monkeypatch)
    _summary_gate(root)
    rounds: list[trainround.RoundRecord] = []
    _drive(root, tmp_path, ("a.txt", "missing.txt", "c.txt"), rounds)
    assert [(r.verdict, r.gates) for r in rounds] == [("unbuilt", 0), ("green", 1)]
    assert not rounds[0].facts.jobs
