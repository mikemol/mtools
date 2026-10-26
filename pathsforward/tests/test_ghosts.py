# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A ready card leading a landed commit's subject is LISTED with its markers, never closed (W2033).

⚑ THE CONTROLS: a commit that only mentions a symbol later in its subject is not a candidate, a
card that is not ready is not listed, a subject with no marker is still listed (marked as such),
and a log that could not be read is a refusal and never "no ghosts".
"""

import json
from pathlib import Path

import pytest

from mikemol.pathsforward import cli, ghosts, store
from mikemol.pathsforward.model import RefusedError
from mikemol.pathsforward.reconcile import Commit

_SHA = "0123456789abcdef"
_SHOWN = 100
_LINES = 3


def _commit(subject: str, sha: str = _SHA) -> Commit:
    return Commit(sha, "2026-10-26T00:00:00Z", f"{subject}\n\nbody\n")


def _state(tmp_path: Path) -> Path:
    path = tmp_path / "repo" / ".claude" / "paths-forward.json"
    path.parent.mkdir(parents=True)
    cards = [
        {"symbol": "W1", "status": "ready"},
        {"symbol": "W2", "status": "working"},
        {"symbol": "W3", "status": "ready"},
    ]
    doc: dict[str, object] = {"counter": 3, "waypoints": cards, "project_root": str(tmp_path)}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_the_open_markers_a_subject_uses_are_named_in_table_order() -> None:
    """`NOT DONE` and `first part` are found without regard to case; a plain subject has none."""
    assert ghosts.markers_in("W9 (first part): x. NOT DONE: y") == ("NOT DONE", "first part")
    assert ghosts.markers_in("W9 (STEP ONE) landed") == ("step one",)
    assert ghosts.markers_in("W9: the whole thing") == ()


def test_only_a_commit_that_leads_with_the_symbol_of_a_ready_card_is_a_candidate() -> None:
    """A later mention, a card that is not ready and a longer symbol (W10 for W1) are not."""
    commits = [
        _commit("W1 step one: a"),
        _commit("W7: see W1 for the rest"),
        _commit("W2: not ready"),
        _commit("W10: a longer symbol"),
    ]
    found = ghosts.candidates(["W1", "W3"], commits)
    assert [g.symbol for g in found] == ["W1"]
    assert found[0].markers == ("step one",)


def test_a_subject_with_no_marker_is_listed_and_says_so() -> None:
    """The reader decides: no marker is still a candidate, rendered as such with a short sha."""
    found = ghosts.candidates(["W1"], [_commit("W1: done in full")])
    assert [ghosts.line(g) for g in found] == [f"W1  {_SHA[:7]}  [no marker]  W1: done in full"]


def test_a_long_subject_is_cut_for_the_reader() -> None:
    """One line per candidate, not a whole commit message."""
    found = ghosts.candidates(["W1"], [_commit("W1 " + "x" * 500)])
    assert len(ghosts.line(found[0]).split("  ", 3)[3]) == _SHOWN


def test_the_report_counts_the_ready_cards_that_lead_a_commit_and_changes_nothing(
    tmp_path: Path,
) -> None:
    """Two commits for W1 and none for W3 count one card of two ready; the queue is untouched."""
    path = _state(tmp_path)
    before = path.read_text(encoding="utf-8")
    raw = "".join(
        f"{sha}\x1f2026-10-26T00:00:00Z\x1f{subject}\x1e"
        for sha, subject in (("a" * 8, "W1 step one"), ("b" * 8, "W1 step two"), ("c" * 8, "W9: x"))
    )
    lines = ghosts.report(store.load(path), tmp_path, log=lambda _root: raw)
    assert len(lines) == _LINES
    assert lines[-1].startswith("1 of 2 ready card(s) lead")
    assert path.read_text(encoding="utf-8") == before


def test_a_log_that_could_not_be_read_is_a_refusal_never_no_ghosts(tmp_path: Path) -> None:
    """No answer is not an empty list."""
    with pytest.raises(RefusedError):
        ghosts.report(store.load(_state(tmp_path)), tmp_path, log=lambda _root: None)


def test_the_mode_is_wired_and_ends_with_the_count_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--ghosts` ends with the count line whether or not git could be read; it never raises."""
    code = cli.main(["--state", str(_state(tmp_path)), "--ghosts"])
    said = capsys.readouterr()
    assert code in {cli.EXIT_OK, cli.EXIT_REFUSED}
    assert "ready card(s) lead" in said.out or "REFUSED" in said.err
