# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the inbound census: peer cards waiting on this repo, claimed or not (W577)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pathsforward import cli, inbound, store
from mikemol.pathsforward import payload as pl
from mikemol.pathsforward.model import validate

if TYPE_CHECKING:
    import pytest

    from mikemol.pathsforward.model import State

Rec = dict[str, object]
_COUNTER = 3
_KNOWN = frozenset({"A", "me"})
_NOW = "2026-10-04T00:00:00Z"
_STAMP = re.compile(r"generated_at=\S+")
_COPY = Path("/scratch/copy/paths-forward.json")
_MANY_DONE = 100
_SWEEP = range(300, 4000, 250)


def _wp(sym: str, status: str = "ready", on: list[str] | None = None, **extra: object) -> Rec:
    """Build a waypoint; `on` makes it blocked unless it is done or a status was forced.

    Returns:
        the waypoint.

    """
    w: Rec = {
        "symbol": sym,
        "title": f"t{sym}",
        "status": "blocked" if on and status == "ready" else status,
        "blocked_on": on or [],
        "blocked_kind": "agent" if on else None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 4 if on else 0,
    }
    w.update(extra)
    return w


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


def _scan(root: Path, me: Path, repos: list[str] | None = None) -> inbound.Census:
    """Run the census for the repo whose state file is `me`.

    Returns:
        the census.

    """
    return inbound.census(root, inbound.repo_name(me), store.load(me), repos)


def _claims(found: inbound.Census) -> list[tuple[str, str, tuple[str, ...]]]:
    """Reduce a census to (peer, card, claimed_by) rows.

    Returns:
        one tuple per ask.

    """
    return [(a.peer, a.symbol, a.claimed_by) for a in found.asks]


def _fixture(root: Path) -> Path:
    """Plant `me` with one claimed and one unclaimed peer ask.

    Returns:
        me's state path.

    """
    me = _queue(root, "me", [_wp("W1", enables=["A:W1"])])
    _queue(root, "A", [_wp("W1", on=["me"], title="claimed ask"), _wp("W2", on=["me"])])
    return me


def _run(args: list[str]) -> int:
    """Run the CLI.

    Returns:
        the exit code.

    """
    return cli.main(args)


def test_resolve_reads_each_blocked_on_shape() -> None:
    """A foreign card, a repo, a prose head and a session name resolve; the rest do not."""
    curly = f"A{chr(0x2019)}s thing"
    got = [
        inbound.resolve(who, _KNOWN)
        for who in ("W5", "A:W3", "B:W3", "A", "A: prose", "A's thing", curly, "A-0f", "A-zz")
    ]
    assert got == [None, ("A", "W3"), None, *[("A", "")] * 5, None]
    assert [inbound.resolve(who, _KNOWN) for who in ("operator", "", "  A:W7  ")] == [
        None,
        None,
        ("A", "W7"),
    ]


def test_a_card_blocked_on_this_repo_with_no_claim_is_unclaimed(tmp_path: Path) -> None:
    """A:W1 waits on the repo as a whole; with no local claim the row is UNCLAIMED."""
    me = _queue(tmp_path, "me", [_wp("W1")])
    _queue(tmp_path, "A", [_wp("W1", on=["me"]), _wp("W2")])
    found = _scan(tmp_path, me)
    assert _claims(found) == [("A", "W1", ())]
    assert [a.title for a in inbound.unclaimed(found)] == ["tW1"]
    assert found.unreadable == ()


def test_a_local_waypoint_that_enables_the_peer_card_claims_it(tmp_path: Path) -> None:
    """me:W1 enabling A:W1 claims the row; an enables of another card or a local W1 does not."""
    me = _queue(
        tmp_path,
        "me",
        [_wp("W1", enables=["A:W1"]), _wp("W2", enables=["A:W2", "W1"]), _wp("W3")],
    )
    _queue(tmp_path, "A", [_wp("W1", on=["me"]), _wp("W3", on=["me"])])
    got = _claims(_scan(tmp_path, me))
    assert got == [("A", "W1", ("me:W1",)), ("A", "W3", ())]


def test_caused_by_the_peer_card_also_claims_it(tmp_path: Path) -> None:
    """A local waypoint whose caused_by is A:W1 claims the row, in any status."""
    me = _queue(tmp_path, "me", [_wp("W1", "done", caused_by="A:W1"), _wp("W2", caused_by="W1")])
    _queue(tmp_path, "A", [_wp("W1", on=["me"])])
    assert _claims(_scan(tmp_path, me)) == [("A", "W1", ("me:W1",))]


def test_a_done_peer_card_is_ignored_and_a_ready_one_with_blockers_counts(tmp_path: Path) -> None:
    """Only done leaves the census: a ready card still carrying blocked_on is waiting."""
    me = _queue(tmp_path, "me", [_wp("W1")])
    _queue(
        tmp_path,
        "A",
        [
            _wp("W1", "done", on=["me"]),
            _wp("W2", "ready", blocked_on=["me"]),
            _wp("W3", "working", blocked_on=["me"]),
        ],
    )
    assert [a.symbol for a in _scan(tmp_path, me).asks] == ["W2", "W3"]


def test_a_peer_blocked_on_a_different_repo_is_ignored(tmp_path: Path) -> None:
    """A card blocked on B, on the operator, or on its own W1 says nothing about me."""
    me = _queue(tmp_path, "me", [_wp("W1")])
    _queue(tmp_path, "A", [_wp("W1", on=["B"]), _wp("W2", on=["operator"]), _wp("W3", on=["W1"])])
    _queue(tmp_path, "B", [_wp("W1", on=["A:W1"])])
    assert _scan(tmp_path, me).asks == ()


def test_a_named_card_that_exists_claims_itself_and_one_that_does_not_is_skipped(
    tmp_path: Path,
) -> None:
    """A:W1 names me:W1 (live), A:W2 names me:W7 (residue), A:W3 names me:W99 (nowhere)."""
    me = _queue(tmp_path, "me", [_wp("W1")], [{"symbol": "W7", "reason": "gone"}])
    _queue(
        tmp_path,
        "A",
        [_wp("W1", on=["me:W1"]), _wp("W2", on=["me:W7"]), _wp("W3", on=["me:W99"])],
    )
    assert _claims(_scan(tmp_path, me)) == [("A", "W1", ("me:W1",)), ("A", "W2", ("me:W7",))]


def test_two_entries_naming_the_same_target_make_one_row(tmp_path: Path) -> None:
    """A repo named twice, or by its session name, is one row; a different card is another."""
    me = _queue(tmp_path, "me", [_wp("W1"), _wp("W2")])
    _queue(tmp_path, "A", [_wp("W1", on=["me", "me: prose", "me-0f", "me:W1", "me:W2"])])
    assert _claims(_scan(tmp_path, me)) == [
        ("A", "W1", ()),
        ("A", "W1", ("me:W1",)),
        ("A", "W1", ("me:W2",)),
    ]


def test_this_repos_own_cards_are_not_its_inbound(tmp_path: Path) -> None:
    """A card of the repo itself blocked on its own name is not a peer's ask."""
    me = _queue(tmp_path, "me", [_wp("W1", on=["me"])])
    assert _scan(tmp_path, me).asks == ()


def test_an_unreadable_peer_is_named_with_its_reason(tmp_path: Path) -> None:
    """A peer queue that is not JSON is listed by name; the readable peer still counts."""
    me = _queue(tmp_path, "me", [_wp("W1")])
    bad = _queue(tmp_path, "bad", [])
    bad.write_text("not json", encoding="utf-8")
    _queue(tmp_path, "A", [_wp("W1", on=["me"])])
    found = _scan(tmp_path, me)
    assert len(found.unreadable) == 1
    assert found.unreadable[0].startswith("bad: queue file unreadable")
    assert _claims(found) == [("A", "W1", ())]


def test_an_escaping_name_and_a_link_are_refused_as_data(tmp_path: Path) -> None:
    """A name with a `..` segment, and a linked repo, are named and never read.

    A nested name (`a/b`) is a path now (W882), so it is looked up and, absent, reads as no queue.
    """
    me = _queue(tmp_path, "me", [_wp("W1")])
    _queue(tmp_path, "real", [_wp("W1", on=["me"])])
    (tmp_path / "L").symlink_to(tmp_path / "real")
    found = _scan(tmp_path, me, ["../x", "a/../b", "a/b", "L", "gone"])
    assert _claims(found) == []
    why = dict(entry.split(": ", 1) for entry in found.unreadable)
    assert sorted(why) == ["../x", "L", "a/../b", "a/b", "gone"]
    assert "refused" in why["../x"]
    assert "refused" in why["a/../b"]
    assert "no queue file" in why["a/b"]
    assert "link" in why["L"]
    assert "no queue file" in why["gone"]


def test_the_scan_lists_repos_with_a_queue_and_skips_dot_directories(tmp_path: Path) -> None:
    """known_repos reads the directory listing: queue holders only, no dot-named worktree."""
    _queue(tmp_path, "b", [])
    _queue(tmp_path, "a", [])
    _queue(tmp_path, ".a-gate-wt", [])
    (tmp_path / "empty").mkdir()
    assert inbound.known_repos(tmp_path) == ["a", "b"]
    assert inbound.known_repos(tmp_path / "missing") == []


def test_the_census_does_not_write_a_peer_queue(tmp_path: Path) -> None:
    """Scanning leaves the peer's bytes, and its directory, untouched."""
    me = _queue(tmp_path, "me", [_wp("W1")])
    a = _queue(tmp_path, "A", [_wp("W1", on=["me"])])
    before = (a.read_bytes(), sorted(p.name for p in a.parent.iterdir()))
    assert len(_scan(tmp_path, me).asks) == 1
    assert (a.read_bytes(), sorted(p.name for p in a.parent.iterdir())) == before


def test_repo_name_and_ref_spell_the_citation() -> None:
    """The repo is the directory above .claude; a reference is repo:W<n>."""
    assert inbound.repo_name(Path("/x/github/me/.claude/paths-forward.json")) == "me"
    assert inbound.ref("A", "W3") == "A:W3"


def test_clip_keeps_the_first_line_to_the_limit() -> None:
    """A title is cut to TITLE_CLIP on its first line; an empty one stays empty."""
    assert inbound.clip("x" * (inbound.TITLE_CLIP + 5)) == "x" * inbound.TITLE_CLIP
    assert inbound.clip("one\ntwo") == "one"
    assert not inbound.clip("")


def test_the_claim_command_cites_the_card_in_enables_and_caused_by(tmp_path: Path) -> None:
    """The command is the exact --add that claims, with the title quoted for a shell."""
    ask = inbound.Ask("A", "W7", "it's a title", "")
    state = tmp_path / "my repo" / ".claude" / "paths-forward.json"
    assert inbound.claim_command(state, ask) == (
        f"mikemol-paths-forward --state '{state}' "
        "--add 'Answer A:W7: it'\"'\"'s a title' --enables A:W7 --caused-by A:W7"
    )


def test_ask_line_is_unclaimed_with_a_command_or_claimed_with_by_whom(tmp_path: Path) -> None:
    """UNCLAIMED rows end in their claim command; CLAIMED rows say by which waypoint."""
    state = tmp_path / "paths-forward.json"
    open_ask = inbound.Ask("A", "W7", "title", "")
    shut_ask = inbound.Ask("A", "W8", "other", "", ("me:W1", "me:W2"))
    assert inbound.ask_line(state, open_ask) == (
        f"UNCLAIMED A:W7 :: title :: {inbound.claim_command(state, open_ask)}"
    )
    assert inbound.ask_line(state, shut_ask) == "CLAIMED A:W8 by me:W1,me:W2 :: other"


def test_payload_lines_are_empty_for_a_quiet_census_and_name_rows_and_unreadable() -> None:
    """Nothing to say gives (); rows and unreadable peers each get an indented line."""
    quiet = inbound.Census((inbound.Ask("A", "W1", "t", "", ("me:W1",)),), ())
    assert inbound.payload_lines(quiet) == ()
    busy = inbound.Census(
        (inbound.Ask("A", "W2", "wants you", ""),),
        ("bad: queue file unreadable: x",),
    )
    lines = inbound.payload_lines(busy)
    assert lines[0].startswith("inbound: 1 peer ask(s) wait on this repo with no claiming")
    assert lines[1:] == ("  A:W2 :: wants you", "  unreadable: bad: queue file unreadable: x")
    only_bad = inbound.Census((), ("bad: why",))
    assert inbound.payload_lines(only_bad)[0].startswith("inbound: 0 peer ask(s)")
    assert inbound.payload_lines(only_bad)[1:] == ("  unreadable: bad: why",)


def test_inbound_mode_prints_one_greppable_line_per_unclaimed_row(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--inbound prints UNCLAIMED rows only, with the claim command, and exits 0."""
    me = _fixture(tmp_path)
    assert _run(["--state", str(me), "--inbound", "--root", str(tmp_path)]) == cli.EXIT_OK
    out = capsys.readouterr().out.splitlines()
    assert out == [
        f"UNCLAIMED A:W2 :: tW2 :: {inbound.claim_command(me, inbound.Ask('A', 'W2', 'tW2', ''))}"
    ]


def test_inbound_all_adds_the_claimed_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--all prints the CLAIMED row as well, in census order."""
    me = _fixture(tmp_path)
    assert _run(["--state", str(me), "--inbound", "--all", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert [line.split(" ", 2)[:2] for line in out] == [["CLAIMED", "A:W1"], ["UNCLAIMED", "A:W2"]]
    assert out[0] == "CLAIMED A:W1 by me:W1 :: claimed ask"


def test_inbound_mode_is_silent_and_exit_zero_when_everything_is_claimed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A quiet repo prints nothing and still exits 0."""
    me = _queue(tmp_path, "me", [_wp("W1", enables=["A:W1"])])
    _queue(tmp_path, "A", [_wp("W1", on=["me"])])
    assert _run(["--state", str(me), "--inbound", "--root", str(tmp_path)]) == cli.EXIT_OK
    assert not capsys.readouterr().out


def test_inbound_mode_names_an_unreadable_peer(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A peer whose queue cannot be read is an UNREADABLE line, exit still 0."""
    me = _queue(tmp_path, "me", [_wp("W1")])
    _queue(tmp_path, "bad", []).write_text("not json", encoding="utf-8")
    assert _run(["--state", str(me), "--inbound", "--root", str(tmp_path)]) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert out.startswith("UNREADABLE bad: queue file unreadable")


def test_all_is_refused_by_a_mode_that_does_not_read_it(tmp_path: Path) -> None:
    """`--all` on --payload is a stray flag, refused rather than accepted in silence."""
    me = _queue(tmp_path, "me", [_wp("W1")])
    assert _run(["--state", str(me), "--payload", "--all"]) == cli.EXIT_REFUSED


def _payload(me: Path, root: Path, capsys: pytest.CaptureFixture[str]) -> str:
    """Run --payload and strip the clock.

    Returns:
        the payload, generated_at blanked.

    """
    assert _run(["--state", str(me), "--payload", "--root", str(root)]) == cli.EXIT_OK
    return _STAMP.sub("generated_at=-", capsys.readouterr().out)


def test_a_quiet_repos_payload_is_byte_identical_to_the_payload_without_the_section(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With only claimed asks, the payload equals one built with no inbound lines at all."""
    me = _queue(tmp_path, "me", [_wp("W1", enables=["A:W1"])])
    _queue(tmp_path, "A", [_wp("W1", on=["me"])])
    got = _payload(me, tmp_path, capsys)
    request = pl.Request(store.load(me), me, "-", command=pl.script_command())
    plain = _STAMP.sub("generated_at=-", pl.build(request))
    assert got == plain + "\n"
    assert "\ninbound:" not in got


def test_payload_carries_the_unclaimed_rows_between_the_rules_and_the_waypoints(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The section is after the header and rules and before `waypoints:`, rows then unreadable."""
    me = _fixture(tmp_path)
    _queue(tmp_path, "bad", []).write_text("not json", encoding="utf-8")
    lines = _payload(me, tmp_path, capsys).splitlines()
    at = next(i for i, ln in enumerate(lines) if ln.startswith("inbound: 1 peer ask(s)"))
    assert lines[at + 1] == "  A:W2 :: tW2"
    assert lines[at + 2].startswith("  unreadable: bad: queue file unreadable")
    assert lines[at + 3] == "waypoints:"
    assert all(not ln.startswith("  A:W1") for ln in lines)


def _state_with_done(count: int) -> State:
    """Build a state whose done list is the heaviest part of the payload.

    Returns:
        the state.

    """
    waypoints = [_wp("W1"), *(_wp(f"W{n}", "done") for n in range(2, count + 2))]
    doc: Rec = {
        "counter": count + 2,
        "project_root": "/proj",
        "waypoints": waypoints,
        "residue": [],
    }
    return validate(doc)


def test_an_over_budget_payload_drops_the_inbound_rows_last_and_says_so() -> None:
    """Rows go only after the done list is gone; the heading stays, and the marker names it."""
    rows = tuple(f"  peer:W{n} :: a title that is a fair bit long to read {n}" for n in range(8))
    lines = ("inbound: 8 peer ask(s) heading", *rows)
    state = _state_with_done(_MANY_DONE)
    outs: list[str] = []
    for budget in _SWEEP:
        try:
            outs.append(pl.build(pl.Request(state, _COPY, _NOW, budget, "x", inbound=lines)))
        except pl.PayloadOverBudgetError:
            continue
    dropped_rows = [o for o in outs if "inbound-rows" in o.splitlines()[-1]]
    assert dropped_rows
    for out in dropped_rows:
        assert "inbound: 8 peer ask(s) heading" in out
        assert "peer:W0" not in out
        assert "done-list" in out.splitlines()[-1]
    kept = [o for o in outs if "peer:W7 ::" in o]
    assert kept
    assert all("inbound-rows" not in o for o in kept)
    assert any("done-list" in o.splitlines()[-1] for o in kept)


def test_the_ladder_gains_an_inbound_rung_only_when_asked() -> None:
    """has_inbound appends one last rung that collapses the rows; without it nothing changes."""
    plain = pl.ladder(3, has_host=False)
    more = pl.ladder(3, has_host=False, has_inbound=True)
    assert more[:-1] == plain
    assert (more[-1].inbound, more[-1].dropped[-1]) == (False, "inbound-rows")
    assert all(rung.inbound for rung in plain)
