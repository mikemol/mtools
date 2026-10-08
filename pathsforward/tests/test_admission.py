# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for --admit and the marks ledger: save, judge, mark; only a bare drop is refused."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.pathsforward import admission, cli, marks, opa_eval, store
from mikemol.pathsforward.model import RefusedError

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_NOW = "2026-10-08T12:00:00Z"
_ARM = "host:luthen"
_BOUND = 4
_DROP = ["--drop", "W2", "a cycle", "--admit", "--gate", "reachable", "--reference-arm", _ARM]
_WAYPOINT: Rec = {
    "symbol": "W1",
    "title": "one bounded thing",
    "status": "ready",
    "blocked_on": [],
    "blocked_kind": None,
    "next_bounded_step": "run it",
    "evidence": "it printed OK",
    "ticks_blocked": 0,
    "population": {"source": "the files under src/", "bound": _BOUND},
}


def _queue(tmp_path: Path) -> Path:
    """Write `<tmp>/home/.claude/paths-forward.json` holding W1 and W2.

    Returns:
        the queue's path.

    """
    path = tmp_path / "home" / ".claude" / "paths-forward.json"
    path.parent.mkdir(parents=True)
    doc: Rec = {
        "counter": 2,
        "waypoints": [_WAYPOINT, {**_WAYPOINT, "symbol": "W2"}],
        "residue": [],
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _run(path: Path, root: Path, *args: str) -> int:
    """Run the CLI on a queue.

    Returns:
        the exit code.

    """
    return cli.main(["--state", str(path), *args, "--root", str(root)])


def _marks(path: Path) -> list[Rec]:
    """Read the marks file beside a queue.

    Returns:
        each record, in order; empty when there is no file.

    """
    where = store.sibling(path, marks.MARKS)
    if not where.exists():
        return []
    return [cast("Rec", json.loads(ln)) for ln in where.read_text("utf-8").splitlines()]


def _residue(path: Path) -> list[Rec]:
    """Read the residue array of a queue.

    Returns:
        its entries.

    """
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    return cast("list[Rec]", doc["residue"])


def test_the_policy_version_is_the_hash_of_the_policy_file() -> None:
    """A mark names the exact policy that judged it, so a changed policy is a changed version."""
    expected = hashlib.sha256(opa_eval.POLICY.read_bytes()).hexdigest()
    assert marks.policy_version() == expected


def test_the_input_digest_ignores_key_order_and_sees_a_changed_value() -> None:
    """The canonical form sorts keys, so only content moves the digest."""
    one: Rec = {"a": 1, "b": [1, 2]}
    assert marks.input_digest(one) == marks.input_digest({"b": [1, 2], "a": 1})
    assert marks.input_digest(one) != marks.input_digest({"a": 1, "b": [2, 1]})


def test_a_judged_mark_carries_who_what_when_and_the_verdict() -> None:
    """The record has the clock, the op, the symbol, both hashes and the verdict as given."""
    item: Rec = {"waypoint": {"symbol": "W7"}}
    verdict: Rec = {"level": "none", "residue": []}
    got = marks.judged("add", _NOW, item, verdict)
    assert got == {
        "as_of": _NOW,
        "op": "add",
        "symbol": "W7",
        "policy_version": marks.policy_version(),
        "input_digest": marks.input_digest(item),
        "verdict": verdict,
    }


def test_a_drop_mark_says_where_it_died_and_has_no_verdict() -> None:
    """Nothing is left to judge after a drop, so the mark holds the account instead."""
    got = marks.dropped(_NOW, "W7", "reachable", _ARM, "a cycle")
    assert got == {
        "as_of": _NOW,
        "op": "drop",
        "symbol": "W7",
        "drop": {"gate": "reachable", "reference_arm": _ARM, "reason": "a cycle"},
    }


def test_append_adds_one_line_per_record_and_never_rewrites(tmp_path: Path) -> None:
    """Two appends are two lines, the first untouched."""
    path = tmp_path / "m.jsonl"
    marks.append(path, {"n": 1})
    marks.append(path, {"n": 2})
    assert path.read_text(encoding="utf-8").splitlines() == ['{"n": 1}', '{"n": 2}']


@pytest.mark.parametrize(
    ("gate", "arm", "reason", "match"),
    [
        (None, _ARM, "why", "needs --gate"),
        ("waived", _ARM, "why", "needs --gate"),
        ("reachable", None, "why", "reference arm"),
        ("reachable", "  ", "why", "reference arm"),
        ("reachable", _ARM, " ", "reason"),
    ],
)
def test_a_drop_must_say_the_gate_the_arm_and_why(
    gate: str | None, arm: str | None, reason: str, match: str
) -> None:
    """The one refusal: a drop with no account of where the waypoint died."""
    with pytest.raises(RefusedError, match=match):
        admission.died(gate, arm, reason)


def test_a_complete_account_is_the_gate_and_the_arm() -> None:
    """What is stored on the residue entry is exactly the gate and the arm."""
    assert admission.died("reachable", _ARM, "why") == {"gate": "reachable", "reference_arm": _ARM}


def test_add_with_admit_saves_judges_and_marks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The waypoint is minted, its coordinate printed, and one add mark appended."""
    path = _queue(tmp_path)
    assert _run(path, tmp_path, "--add", "a new claim", "--admit") == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "W3 added" in out
    assert "admit: W3 none," in out
    (mark,) = _marks(path)
    assert (mark["op"], mark["symbol"]) == ("add", "W3")
    assert str(mark["as_of"]).endswith("Z")
    assert cast("Rec", mark["verdict"])["level"] == "none"


def test_update_with_admit_marks_the_judged_coordinate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A fully declared waypoint judged after an update is runtime-valid, and the mark says so."""
    path = _queue(tmp_path)
    args = ["--update", "W1", "--reference-arm", _ARM, "--admit"]
    assert _run(path, tmp_path, *args) == cli.EXIT_OK
    assert "admit: W1 coverable, 0 residue" in capsys.readouterr().out
    (mark,) = _marks(path)
    assert (mark["op"], mark["symbol"]) == ("update", "W1")


def test_without_admit_nothing_is_judged_or_marked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The flag is opt-in: an ordinary write leaves no mark and prints no coordinate."""
    path = _queue(tmp_path)
    assert _run(path, tmp_path, "--update", "W1", "--reference-arm", _ARM) == cli.EXIT_OK
    assert "admit" not in capsys.readouterr().out
    assert not _marks(path)


def test_a_policy_that_cannot_run_never_blocks_the_write(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """No pinned opa: the claim is still saved, the line says it was not judged, no mark."""
    path = _queue(tmp_path)
    monkeypatch.setenv(opa_eval.OPA_ENV, str(tmp_path / "absent"))
    assert _run(path, tmp_path, "--add", "still minted", "--admit") == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "W3 added" in out
    assert "not judged" in out
    assert not _marks(path)
    assert "still minted" in path.read_text(encoding="utf-8")


def test_a_bare_drop_under_admit_is_refused_and_the_waypoint_stays_live(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No gate and arm: exit 2, nothing moved, nothing marked."""
    path = _queue(tmp_path)
    assert _run(path, tmp_path, "--drop", "W2", "not needed", "--admit") == cli.EXIT_REFUSED
    assert "needs --gate" in capsys.readouterr().err
    assert not _residue(path)
    assert not _marks(path)


def test_a_complete_drop_stores_the_account_on_the_residue_and_marks_it(tmp_path: Path) -> None:
    """The residue entry carries gate and arm beside the reason, and a drop mark is appended."""
    path = _queue(tmp_path)
    assert _run(path, tmp_path, *_DROP) == cli.EXIT_OK
    (entry,) = _residue(path)
    assert (entry["gate"], entry["reference_arm"]) == ("reachable", _ARM)
    assert entry["reason"] == "a cycle"
    (mark,) = _marks(path)
    assert mark["drop"] == {"gate": "reachable", "reference_arm": _ARM, "reason": "a cycle"}


def test_a_plain_drop_without_admit_is_unchanged(tmp_path: Path) -> None:
    """The two-operand drop still works and stores no gate or arm."""
    path = _queue(tmp_path)
    assert _run(path, tmp_path, "--drop", "W2", "not needed") == cli.EXIT_OK
    (entry,) = _residue(path)
    assert "gate" not in entry
    assert not _marks(path)


def test_gate_is_a_drop_flag_and_is_refused_elsewhere(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A flag a mode does not read is a stray, never silently accepted."""
    path = _queue(tmp_path)
    assert _run(path, tmp_path, "--update", "W1", "--gate", "reachable") == cli.EXIT_REFUSED
    assert "--gate" in capsys.readouterr().err
