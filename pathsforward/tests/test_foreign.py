# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--prune-landed --root`: a landed foreign blocker is pruned, others named."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli, foreign

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

Rec = dict[str, object]
_COUNTER = 3


def _wp(sym: str, status: str = "ready", on: list[str] | None = None) -> Rec:
    """Build a waypoint, blocked on `on` when given.

    Returns:
        the waypoint.

    """
    return {
        "symbol": sym,
        "title": f"t{sym}",
        "status": "blocked" if on else status,
        "blocked_on": on or [],
        "blocked_kind": "agent" if on else None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 4 if on else 0,
    }


def _queue(root: Path, repo: str, waypoints: list[Rec], residue: list[Rec] | None = None) -> Path:
    """Write `repo`'s queue file under `root`.

    Returns:
        the state path.

    """
    path = root / repo / ".claude" / "paths-forward.json"
    path.parent.mkdir(parents=True)
    doc: Rec = {
        "counter": _COUNTER,
        "project_root": str(root / repo),
        "state_path": str(path),
        "waypoints": waypoints,
        "residue": residue or [],
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _prune(path: Path, root: Path) -> int:
    """Run `--prune-landed --root` on a queue.

    Returns:
        the exit code.

    """
    return cli.main(["--state", str(path), "--prune-landed", "--root", str(root)])


def _cards(path: Path) -> dict[str, Rec]:
    """Read a queue's waypoints back, by symbol.

    Returns:
        each waypoint keyed by its symbol.

    """
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    return {str(w["symbol"]): w for w in cast("list[Rec]", doc["waypoints"])}


def _two_repos(root: Path) -> tuple[Path, Path]:
    """Plant A (W1 done, W2 open, W3 residue) and B (cards blocked on each of them).

    Returns:
        the state paths of A and B.

    """
    a = _queue(
        root,
        "A",
        [_wp("W1", "done"), _wp("W2", "ready")],
        [{"symbol": "W3", "reason": "why"}],
    )
    b = _queue(
        root,
        "B",
        [
            _wp("W1", on=["A:W1"]),
            _wp("W2", on=["A:W2"]),
            _wp("W3", on=["A:W3"]),
            _wp("W4", on=["A:W1", "A:W2"]),
        ],
    )
    return a, b


def test_a_landed_foreign_blocker_frees_the_card_and_an_open_one_is_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """B's card on a done A:W1 or a residue A:W3 goes ready; one on an open A:W2 stays, named."""
    _, b = _two_repos(tmp_path)
    assert _prune(b, tmp_path) == cli.EXIT_OK
    cards = _cards(b)
    out = capsys.readouterr().out
    assert (cards["W1"]["status"], cards["W1"]["blocked_on"]) == ("ready", [])
    assert (cards["W3"]["status"], cards["W3"]["blocked_kind"]) == ("ready", None)
    assert (cards["W2"]["status"], cards["W2"]["blocked_on"]) == ("blocked", ["A:W2"])
    assert "UNBLOCKED W1" in out
    assert "KEPT W2 blocked on A:W2: W2 is ready" in out


def test_a_shrinking_list_restarts_ticks_and_stays_blocked(tmp_path: Path) -> None:
    """A card blocked on a landed and an open foreign symbol keeps the open one, ticks reset."""
    _, b = _two_repos(tmp_path)
    assert _prune(b, tmp_path) == cli.EXIT_OK
    card = _cards(b)["W4"]
    assert (card["status"], card["blocked_on"], card["ticks_blocked"]) == ("blocked", ["A:W2"], 0)


def test_the_peer_queue_is_not_written(tmp_path: Path) -> None:
    """Reading A's queue leaves its bytes, and any lock sidecar, untouched."""
    a, b = _two_repos(tmp_path)
    before = a.read_bytes()
    assert _prune(b, tmp_path) == cli.EXIT_OK
    assert (a.read_bytes(), sorted(p.name for p in a.parent.iterdir())) == (
        before,
        ["paths-forward.json"],
    )


def test_every_unresolvable_foreign_blocker_is_kept_and_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing repo, a non-JSON queue, an unknown symbol and an escaping name are all named."""
    _queue(tmp_path, "bad", [])
    (tmp_path / "bad" / ".claude" / "paths-forward.json").write_text("not json", encoding="utf-8")
    _queue(tmp_path, "A", [_wp("W1", "done")])
    refs = ["nope:W1", "bad:W1", "A:W9", "../x:W1", "a/../b:W1", "a/b:W1"]
    b = _queue(tmp_path, "B", [_wp("W1", on=refs)])
    assert _prune(b, tmp_path) == cli.EXIT_OK
    out = capsys.readouterr().out.splitlines()
    assert _cards(b)["W1"]["blocked_on"] == refs
    assert len(out) == len(refs)
    assert "has no queue file" in out[0]
    assert "unreadable" in out[1]
    assert "A:W9: W9 is not in" in out[2]
    assert all("refused" in line for line in out[3:5])
    assert "has no queue file" in out[5]


def test_a_linked_repo_is_refused_as_data(tmp_path: Path) -> None:
    """A queue file reached through a link is not read; the check names it."""
    real = tmp_path / "real"
    real.mkdir()
    ok, why = foreign.landed(tmp_path, "gone", "W1")
    assert (ok, "no queue file" in why) == (False, True)
    link = tmp_path / "L"
    link.symlink_to(real)
    ok, why = foreign.landed(tmp_path, "L", "W1")
    assert (ok, "link" in why) == (False, True)


def test_with_no_foreign_blocker_nothing_changes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A queue with only local blockers prunes as before, prints no KEPT line, ignores --root."""
    waypoints = [_wp("W1", "done"), _wp("W2", on=["W1"]), _wp("W3", on=["operator"])]
    one = _queue(tmp_path, "one", waypoints)
    assert _prune(one, tmp_path / "missing-root") == cli.EXIT_OK
    out = capsys.readouterr().out
    cards = _cards(one)
    assert out == "UNBLOCKED W2 (every local blocker is done)\n"
    assert (cards["W2"]["status"], cards["W3"]["blocked_on"]) == ("ready", ["operator"])


def test_the_default_root_comes_from_the_home_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no --root the repos are read from ~/github, resolved at runtime."""
    monkeypatch.setenv("HOME", str(tmp_path))
    assert foreign.default_root() == tmp_path / "github"


def test_root_is_refused_by_a_mode_that_does_not_read_it(tmp_path: Path) -> None:
    """`--root` on another mode is a stray flag, refused rather than accepted in silence."""
    one = _queue(tmp_path, "one", [_wp("W1")])
    assert cli.main(["--state", str(one), "--bump-blocked", "--root", str(tmp_path)]) == (
        cli.EXIT_REFUSED
    )
