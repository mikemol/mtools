# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A leader joins the queued stacks behind it, runs one train and leaves each follower a verdict.

⚑ REAL GIT, A REAL GATE HOOK AND THE REAL LEDGER: the followers are made by `stackfreeze.at_submit`
and marked queued in the live-commit map, the pre-commit counts its own runs (so 'one gate for
three stacks' is read from a file the gate wrote), and the verdict files are read back. The
controls are the off switch, a queue with nobody behind the leader, and a bad follower. The span
send is replaced by a recorder, so each train's counts are read as a panel would read them.
"""

from __future__ import annotations

import io
import json
import os
from typing import TYPE_CHECKING

from mikemol.hooks import commit_counts, stackfreeze, stackrun, trainlead, traintel, trainverdict
from mikemol.hooks import commit_kata as ck
from mikemol.hooks.trainjoin import Follower

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    import pytest

_EXECUTABLE = 0o755
_GATE = (
    '#!/bin/sh\necho run >> "$MIKEMOL_REAL_ROOT/runs"\n'
    'if grep -rq bad --exclude-dir=.git .; then echo "found bad" >&2; exit 1; fi\n'
)
_PUSH = "#!/bin/sh\ngit push origin HEAD:main\n"
_LEADER_FILE = "a.txt"
_FOLLOWER_FILES = ("b.txt", "c.txt")
_LEADER, _SECOND, _THIRD = "100", "200", "300"
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
    names = (_LEADER_FILE, *_FOLLOWER_FILES)
    for name in names:
        (root / name).write_text("original\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    _git(root, "remote", "add", "origin", str(remote))
    _git(root, "push", "--quiet", "origin", "HEAD:main")
    for hook_name, text in (("pre-commit", _GATE), ("post-commit", _PUSH)):
        hook = root / ".git" / "hooks" / hook_name
        hook.write_text(text, encoding="utf-8")
        hook.chmod(_EXECUTABLE)
    for name in names:
        (root / name).write_text("bad\n" if name == bad else f"edited {name}\n", encoding="utf-8")
    return root


def _ledger(root: Path) -> Path:
    found = ck.ledger_of(root)
    assert found is not None
    return found


def _queue(root: Path, tmp_path: Path, keys: tuple[str, ...]) -> None:
    """Submit one stack per key (b.txt, c.txt) and mark each queued in the live map."""
    ledger = _ledger(root)
    for key, name in zip(keys, _FOLLOWER_FILES, strict=False):
        entries = [{"waypoint": f"W{key}", "subject": f"card {key}", "paths": [name]}]
        stack = tmp_path / f"stack-{key}.json"
        stack.write_text(json.dumps(entries), encoding="utf-8")
        assert stackfreeze.at_submit(root, stack, ledger, key, ck.run_git_in)
        commit_counts.transition(ledger / "commit.counts", key, commit_counts.QUEUED)


def _lead(root: Path, tmp_path: Path, env: dict[str, str] | None = None) -> tuple[int | None, str]:
    seams = stackrun.Seams(
        run=ck.run_git_in,
        namespace=tmp_path / "gate",
        message_of=lambda item: f"{item.subject}\n\nWaypoint: {item.waypoint}\n",
        published=lambda _sha: "PUSHED",
    )
    own = Follower(_LEADER, (stackrun.Item("W100", "card 100", "", (_LEADER_FILE,)),))
    out = io.StringIO()
    code = trainlead.lead(root, _ledger(root), own, (seams, env or {}), out)
    return code, out.getvalue()


def _recorded(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    """Replace the span send with a recorder of each train's fields.

    Returns:
        the list each recorded train's fields are appended to.

    """
    seen: list[dict[str, str]] = []

    def record(
        repo: str, stats: traintel.Stats, _window: tuple[int, int], _env: Mapping[str, str]
    ) -> bool:
        seen.append({"repo": repo, **stats.fields()})
        return True

    monkeypatch.setattr(traintel, "emit", record)
    return seen


def test_a_leader_joins_two_queued_stacks_and_runs_one_gate_for_all_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One gate run, three commits on HEAD, a code 0 verdict file for each follower."""
    root = _repo(tmp_path, monkeypatch)
    _queue(root, tmp_path, (_SECOND, _THIRD))
    code, text = _lead(root, tmp_path)
    assert code == 0
    assert "COMMITTED repo" in text
    assert len((root / "runs").read_text(encoding="utf-8").splitlines()) == 1
    assert _git(root, "log", "--format=%s").splitlines()[:_THREE] == [
        "card 300",
        "card 200",
        "card 100",
    ]
    for key in (_SECOND, _THIRD):
        verdict = trainverdict.read(_ledger(root), key)
        assert verdict is not None
        assert verdict.code == 0


def test_a_bad_follower_is_refused_in_its_verdict_and_the_leader_still_lands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The follower with b.txt bad gets a REFUSED verdict; the leader and the third land."""
    root = _repo(tmp_path, monkeypatch, bad="b.txt")
    _queue(root, tmp_path, (_SECOND, _THIRD))
    code, _text = _lead(root, tmp_path)
    assert code == 0
    refused = trainverdict.read(_ledger(root), _SECOND)
    landed = trainverdict.read(_ledger(root), _THIRD)
    assert refused is not None
    assert refused.code != 0
    assert "REFUSED repo" in refused.text
    assert landed is not None
    assert landed.code == 0


def test_the_stack_command_runs_the_train_when_stacks_are_queued_behind_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Through `mikemol-commit --stack`: one gate, three commits, and verdict files left behind."""
    root = _repo(tmp_path, monkeypatch)
    _queue(root, tmp_path, (_SECOND, _THIRD))
    for name, value in (
        (ck.HELD_ENV, "1"),
        (ck.ISOLATED_ENV, "1"),
        ("MIKEMOL_COMMIT_SUBMITTED_NS", _LEADER),
        ("MIKEMOL_SNAPSHOT_ROOT", str(tmp_path / "gate")),
    ):
        monkeypatch.setenv(name, value)
    entries = [{"waypoint": "W100", "subject": "card 100", "paths": [_LEADER_FILE]}]
    stack = tmp_path / "stack-100.json"
    stack.write_text(json.dumps(entries), encoding="utf-8")
    assert ck.main([str(root), "--stack", str(stack)]) == 0
    assert len((root / "runs").read_text(encoding="utf-8").splitlines()) == 1
    assert _git(root, "log", "--format=%s").splitlines()[:_THREE] == [
        "card 300",
        "card 200",
        "card 100",
    ]
    verdict = trainverdict.read(_ledger(root), _THIRD)
    assert verdict is not None
    assert verdict.code == 0


def test_a_green_train_records_one_span_of_three_stacks_one_gate_and_no_bisecting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The panel's saving: joined 3, gates 1, bisect steps 0, landed 3."""
    seen = _recorded(monkeypatch)
    root = _repo(tmp_path, monkeypatch)
    _queue(root, tmp_path, (_SECOND, _THIRD))
    _lead(root, tmp_path)
    assert seen == [
        {
            "repo": "repo",
            "joined": "3",
            "gates": "1",
            "bisect_steps": "0",
            "rounds": "1",
            "landed": "3",
            "refused": "0",
            "dropped": "0",
        }
    ]


def test_a_train_that_bisects_records_its_steps_rounds_and_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bad middle stack: 4 gates, 2 bisect steps, 2 rounds, 2 landed, 1 refused."""
    seen = _recorded(monkeypatch)
    root = _repo(tmp_path, monkeypatch, bad="b.txt")
    _queue(root, tmp_path, (_SECOND, _THIRD))
    _lead(root, tmp_path)
    (fields,) = seen
    assert (fields["gates"], fields["bisect_steps"], fields["rounds"]) == ("4", "2", "2")
    assert (fields["landed"], fields["refused"]) == ("2", "1")


def test_every_stack_run_ticks_the_considered_counter_with_the_followers_it_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nobody behind ticks 0, the switch off ticks 0, two behind ticks 2: never a dark producer."""
    ticks: list[tuple[str, int]] = []

    def consider(repo: str, followers: int, _env: Mapping[str, str]) -> bool:
        ticks.append((repo, followers))
        return True

    monkeypatch.setattr(traintel, "consider", consider)
    _recorded(monkeypatch)
    root = _repo(tmp_path, monkeypatch)
    _lead(root, tmp_path)
    _queue(root, tmp_path, (_SECOND, _THIRD))
    _lead(root, tmp_path, {trainlead.TRAIN_ENV: trainlead.OFF})
    _lead(root, tmp_path)
    assert ticks == [("repo", 0), ("repo", 0), ("repo", 2)]


def test_nobody_behind_or_the_switch_off_is_no_train(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """None means the caller runs its stack as before, and nothing is committed here."""
    root = _repo(tmp_path, monkeypatch)
    start = _git(root, "rev-parse", "HEAD").strip()
    assert _lead(root, tmp_path)[0] is None
    _queue(root, tmp_path, (_SECOND, _THIRD))
    assert _lead(root, tmp_path, {trainlead.TRAIN_ENV: trainlead.OFF})[0] is None
    assert _git(root, "rev-parse", "HEAD").strip() == start
