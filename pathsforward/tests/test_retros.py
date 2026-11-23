# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A retro record is a node beside the waypoints, and a finding commits to something (W1918)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.pathsforward import cli, retros

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json

_HANDOFF: Json = {"instrument": "i", "channel": "c", "operator": "self"}
_CORPUS = Path(__file__).parent / "corpus"
_PINNED = {
    "retro-handoff-blocks.json": "8f6948d6192289116a9076b7ed9249734a3428af27ff4010bed5d50ccbaa04b3",
    "retro-supersession.json": "f4818250ab98b3df67d108d862fefcc903411b3f38d96aa7bee194dbe5575bcb",
}


def _fixture(name: str) -> Json:
    # A shared fixture, read only when it is the bytes nemik pinned (a copy that differs fails).
    raw = (_CORPUS / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == _PINNED[name], name
    return cast("Json", json.loads(raw))


_CARD: Json = {
    "finding_card": "mtools:W1",
    "finding_owner": "mtools-ad",
    "due": "2026-10-31",
    "finding_witness": "input.git_ref",
}


def test_render_full_prints_every_field_and_finding_and_names_an_unknown_id() -> None:
    """W2088: a record with findings prints each finding; an unknown Rn is named, not guessed."""
    doc: Json = {"retros": []}
    retro: Json = {"title": "t", "root": "the root", "findings": [_CARD, {"certify_change": "ok"}]}
    ident = retros.add_retro(doc, "mtools", retro)
    lines, unknown = retros.render_full(doc, [])
    assert unknown == []
    assert lines[0] == ident
    assert "  root: the root" in lines
    assert "    finding_owner: mtools-ad" in lines
    assert "    certify_change: ok" in lines
    assert retros.render_full(doc, ["R1"])[0] == lines
    assert retros.render_full(doc, ["R9"]) == ([], ["R9"])


def test_a_card_finding_needs_its_owner_its_due_date_and_its_witness() -> None:
    """The G7 rule: a card without the other three is an intention, not a commitment."""
    assert retros.finding_refusals(_CARD) == []
    for key in retros.CARD_FINDING_FIELDS:
        partial = {k: v for k, v in _CARD.items() if k != key}
        assert retros.finding_refusals(partial) == [f"a card-finding has no {key}"]


def test_a_certify_change_alone_stands_and_a_finding_with_neither_is_refused() -> None:
    """A verdict change needs no card; nothing at all is theater."""
    assert retros.finding_refusals({"certify_change": "re-ran the adversarial case"}) == []
    assert retros.finding_refusals({}) == [
        "a finding names neither a finding_card nor a certify_change"
    ]
    assert retros.finding_refusals({"finding_owner": "x"}) != []


def test_the_layer_and_the_handoff_operator_are_held_to_their_vocabularies() -> None:
    """The layers run memory to gate; the handoff operator is self or other."""
    cause: Json = {"trigger": "a gate stalled", "root": "a leaked descriptor", "findings": []}
    good: Json = {"enforcement_layer": "gate", "handoff": {"operator": "self"}, **cause}
    assert retros.retro_refusals(good) == []
    both: Json = {"enforcement_layer": "vibes", "handoff": {"operator": "us"}, **cause}
    assert len(retros.retro_refusals(both)) == len(["layer", "operator"])


def test_a_reviewed_retro_needs_a_trigger_and_a_root_that_differ() -> None:
    """W1935: a layer marks a finished review; it must name trigger and root, and not the same."""
    base: Json = {"enforcement_layer": "gate", "findings": []}
    assert len(retros.retro_refusals(base)) == len(["trigger", "root"])
    host: Json = {**base, "cause": "x"}
    assert len(retros.retro_refusals(host)) == len(["cause is unknown", "trigger", "root"])
    [blank] = retros.retro_refusals({**base, "trigger": "t", "root": "  "})
    assert "no root" in blank
    [same] = retros.retro_refusals({**base, "trigger": "t", "root": "t"})
    assert "root equals trigger" in same


def test_a_scaffold_with_no_layer_is_not_held_to_trigger_and_root() -> None:
    """The negative control: a scaffold (no enforcement_layer) still passes with neither."""
    assert retros.retro_refusals({"findings": []}) == []


def test_a_retro_with_no_findings_list_or_an_unknown_key_is_refused() -> None:
    """W2088: G7 that never ran, and a misspelled key, are refused; an empty list is a claim."""
    assert retros.retro_refusals({"trigger": "t", "findings": []}) == []
    [missing] = retros.retro_refusals({"trigger": "t"})
    assert "no findings list" in missing
    [unknown] = retros.retro_refusals({"findings": [], "triger": "t", "extra": 1})
    assert "extra, triger" in unknown


def test_the_record_form_fields_frozen_timeline_recurring_and_one_off_are_accepted() -> None:
    """W2268 (nemik-6f, W982 owner): mtools adds the doc's three fields; the flags are booleans."""
    doc_form: Json = {
        "trigger": "t",
        "frozen_timeline": "sha256:abc",
        "recurring": True,
        "one_off": False,
        "findings": [],
    }
    assert retros.retro_refusals(doc_form) == []
    for key in ("frozen_timeline", "recurring", "one_off"):
        assert key in retros.RETRO_FIELDS
    [string] = retros.retro_refusals({"findings": [], "recurring": "false"})
    assert "recurring must be true or false" in string
    both = retros.retro_refusals({"findings": [], "recurring": 1, "one_off": "no"})
    assert len(both) == len(["recurring", "one_off"])


def test_adding_a_retro_mints_the_next_id_and_a_refused_one_changes_nothing() -> None:
    """The counter only rises; an old document with no list or counter starts at R1."""
    doc: Json = {"waypoints": []}
    first = retros.add_retro(doc, "mtools", {"trigger": "t", "findings": [_CARD]})
    second = retros.add_retro(doc, "mtools", {"trigger": "u", "findings": []})
    assert (first, second) == ("mtools:R1", "mtools:R2")
    assert doc["retro_counter"] == len(["R1", "R2"])
    before = dict(doc)
    with pytest.raises(ValueError, match="neither"):
        retros.add_retro(doc, "mtools", {"findings": [{}]})
    assert doc == before


def test_a_superseding_row_names_a_retro_of_its_own_repo_and_leaves_it_untouched() -> None:
    """W2888: supersedes adds a row and never relabels one: the older row is byte for byte."""
    doc: Json = {"waypoints": []}
    first = retros.add_retro(doc, "mtools", {"trigger": "t", "findings": [_CARD]})
    old = json.dumps(doc["retros"], sort_keys=True)
    row: Json = {"supersedes": first, "handoff": _HANDOFF, "findings": []}
    assert retros.add_retro(doc, "mtools", row) == "mtools:R2"
    rows = cast("list[Json]", doc["retros"])
    assert rows[1]["supersedes"] == first
    assert json.dumps(rows[:1], sort_keys=True) == old


def test_a_supersedes_naming_an_unknown_foreign_or_already_superseded_retro_is_refused() -> None:
    """W2888: one live row per chain, in the same repository, naming a retro that exists."""
    doc: Json = {"waypoints": []}
    first = retros.add_retro(doc, "mtools", {"trigger": "t", "findings": []})
    retros.add_retro(doc, "mtools", {"supersedes": first, "handoff": _HANDOFF, "findings": []})
    before = json.dumps(doc, sort_keys=True)
    for named, why in (
        ("mtools:R99", "no such retro"),
        ("nemik:R1", "is not a retro id of mtools"),
        (first, "already superseded by mtools:R2"),
    ):
        row: Json = {"supersedes": named, "handoff": _HANDOFF, "findings": []}
        with pytest.raises(ValueError, match=why):
            retros.add_retro(doc, "mtools", row)
    assert json.dumps(doc, sort_keys=True) == before


def test_every_case_of_the_shared_handoff_fixture_gets_the_verdict_nemik_pins() -> None:
    """W2888: nemik:W2488's cases, byte for byte: valid exactly when nothing is refused."""
    cases = cast("list[Json]", _fixture("retro-handoff-blocks.json")["cases"])
    assert {case["valid"] for case in cases} == {True, False}
    for case in cases:
        refused = retros.handoff_refusals(cast("Json", case["handoff"]))
        assert (not refused) is case["valid"], case["name"]


def test_a_superseding_row_failing_the_handoff_shape_is_refused_and_changes_nothing() -> None:
    """W2888: the superseding row must carry the complete handoff the older row lacked."""
    doc: Json = {"waypoints": []}
    first = retros.add_retro(doc, "mtools", {"trigger": "t", "findings": []})
    before = json.dumps(doc, sort_keys=True)
    bare: Json = {"supersedes": first, "findings": []}
    with pytest.raises(ValueError, match="no handoff block"):
        retros.add_retro(doc, "mtools", bare)
    weak: Json = {"supersedes": first, "handoff": {**_HANDOFF, "operator": "other"}, "findings": []}
    with pytest.raises(ValueError, match="needs self_probe"):
        retros.add_retro(doc, "mtools", weak)
    assert json.dumps(doc, sort_keys=True) == before


def test_the_shared_supersession_pair_replays_through_the_writer() -> None:
    """W2888: nemik R3 lacks instrument and channel, R9 supersedes it with the complete handoff."""
    old, new = cast("list[Json]", _fixture("retro-supersession.json")["retros"])
    doc: Json = {"retros": [old], "retro_counter": 8}
    row = {**{key: value for key, value in new.items() if key != "id"}, "findings": []}
    assert retros.add_retro(doc, "nemik", row) == new["id"]
    assert cast("list[Json]", doc["retros"])[0] == old


def _project(tmp_path: Path) -> Path:
    queue = tmp_path / ".claude" / "paths-forward.json"
    queue.parent.mkdir()
    empty: Json = {"counter": 0, "residue": [], "waypoints": []}
    queue.write_text(json.dumps(empty), encoding="utf-8")
    return queue


def _saved(queue: Path) -> Json:
    return cast("Json", json.loads(queue.read_text(encoding="utf-8")))


def _file(tmp_path: Path, name: str, record: Json) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def test_the_command_adds_a_retro_from_a_file_and_refuses_a_bad_finding(tmp_path: Path) -> None:
    """--add-retro FILE stores the record under its new id; a refusal leaves the queue as it was."""
    queue = _project(tmp_path)
    good = _file(tmp_path, "good.json", {"trigger": "t", "findings": [_CARD]})
    assert cli.main(["--state", str(queue), "--add-retro", str(good)]) == cli.EXIT_OK
    saved = _saved(queue)
    assert saved["retro_counter"] == 1
    [stored] = cast("list[Json]", saved["retros"])
    assert stored["id"] == f"{tmp_path.name}:R1"
    bad = _file(tmp_path, "bad.json", {"findings": [{"finding_card": "x"}]})
    assert cli.main(["--state", str(queue), "--add-retro", str(bad)]) == cli.EXIT_REFUSED
    assert _saved(queue) == saved


def test_the_retros_command_prints_all_or_the_named_and_refuses_an_unknown_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2088: --retros prints a stored record in full; an unknown Rn is refused and named."""
    queue = _project(tmp_path)
    good = _file(tmp_path, "good.json", {"trigger": "t", "findings": [_CARD]})
    assert cli.main(["--state", str(queue), "--add-retro", str(good)]) == cli.EXIT_OK
    capsys.readouterr()
    assert cli.main(["--state", str(queue), "--retros"]) == cli.EXIT_OK
    assert "    finding_owner: mtools-ad" in capsys.readouterr().out
    assert cli.main(["--state", str(queue), "--retros", "R1"]) == cli.EXIT_OK
    capsys.readouterr()
    assert cli.main(["--state", str(queue), "--retros", "R7"]) == cli.EXIT_REFUSED
    assert "R7: no retro with that id" in capsys.readouterr().err


def test_the_in_place_cause_to_root_rename_is_gone_not_left_callable() -> None:
    """W2888: the operator ruled a pure rename a meaning change, so nothing may still call it."""
    assert not any(hasattr(retros, name) for name in ("migrate", "_migrated", "UNSPLIT"))


def _flat(ident: str) -> Json:
    # An older row whose handoff values sit as flat keys beside its real content: the handoff moves
    # into the block, the content is carried verbatim, and nothing is derived.
    return {
        "id": ident,
        "trigger": "the proximate cause",
        "root": "the root",
        "precommit": "what was expected",
        "delta": "what happened",
        "findings": [_CARD],
        "instrument": "i",
        "channel": "c",
        "operator": "self",
    }


def test_the_superseding_row_is_the_older_row_with_only_id_supersedes_and_handoff_changed() -> None:
    """W2888: superseding must not erase the retro's content from a reader of the live row."""
    old = _flat("r:R2")
    [(ident, row, refused)] = retros.scaffolds({"retros": [old]}, "r")
    assert (ident, refused) == ("r:R2", [])
    flat = {"instrument", "channel", "operator"}
    assert {k: v for k, v in row.items() if k not in {"supersedes", "handoff"}} == {
        k: v for k, v in old.items() if k not in {"id", *flat}
    }
    assert row["supersedes"] == "r:R2"
    assert row["handoff"] == _HANDOFF


def test_an_older_row_with_no_findings_list_is_not_given_an_empty_one() -> None:
    """W2888: absent means G7 never ran, so the scaffold invents no [] and lists a reviewer."""
    old = {key: value for key, value in _flat("r:R2").items() if key != "findings"}
    [(_, row, refused)] = retros.scaffolds({"retros": [old]}, "r")
    assert "findings" not in row
    assert any("no findings list" in line for line in refused)


def test_a_scaffold_copies_only_stated_handoff_values_and_never_derives_a_cause() -> None:
    """W2888: a complete copy is writable, a gap stays empty and listed, nothing is derived."""
    shaped: Json = {"id": "r:R1", "handoff": _HANDOFF, "findings": []}
    partial: Json = {"id": "r:R3", "handoff": {"operator": "other"}, "findings": []}
    bare: Json = {"id": "r:R4", "cause": "why", "findings": []}
    done: Json = {"id": "r:R5", "handoff": {"operator": "other"}, "findings": []}
    later: Json = {"id": "r:R6", "supersedes": "r:R5", "handoff": _HANDOFF, "findings": []}
    doc: Json = {"retros": [shaped, _flat("r:R2"), partial, bare, done, later]}
    found = {old: (row, refused) for old, row, refused in retros.scaffolds(doc, "r")}
    assert sorted(found) == ["r:R2", "r:R3", "r:R4"]
    assert not found["r:R2"][1]
    assert found["r:R3"][1]
    assert found["r:R4"][1]
    assert found["r:R4"][0]["handoff"] == {}
    assert found["r:R4"][0]["cause"] == "why"


def test_migrate_retros_lists_then_writes_exactly_the_set_it_listed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2888: WOULD WRITE equals what --write writes; a row add_retro would refuse is listed."""
    queue = _project(tmp_path)
    repo = tmp_path.name
    doc = _saved(queue)
    refuse: Json = {"id": f"{repo}:R3", "cause": "why", "findings": []}
    doc["retros"] = [_flat(f"{repo}:R1"), _flat(f"{repo}:R2"), refuse]
    doc["retro_counter"] = 3
    queue.write_text(json.dumps(doc), encoding="utf-8")
    before = _saved(queue)
    assert cli.main(["--state", str(queue), "--migrate-retros"]) == cli.EXIT_OK
    listed = capsys.readouterr().out
    assert f"WOULD WRITE {repo}:R1" in listed
    assert f"WOULD WRITE {repo}:R2" in listed
    assert f"NEEDS A REVIEWER {repo}:R3" in listed
    assert _saved(queue) == before
    assert cli.main(["--state", str(queue), "--migrate-retros", "--write"]) == cli.EXIT_OK
    wrote = capsys.readouterr().out
    assert f"WROTE {repo}:R4 superseding {repo}:R1" in wrote
    assert f"WROTE {repo}:R5 superseding {repo}:R2" in wrote
    assert f"superseding {repo}:R3" not in wrote
    after = cast("list[Json]", _saved(queue)["retros"])
    assert after[:3] == before["retros"]
    assert [row.get("supersedes") for row in after[3:]] == [f"{repo}:R1", f"{repo}:R2"]


def test_self_reproach_in_delta_or_cause_is_refused_naming_field_and_phrase() -> None:
    """W2162: 'should have caught' and 'my mistake' are affect, not a cause; each hit is named."""
    shaped: Json = {"findings": []}
    [delta] = retros.retro_refusals({**shaped, "delta": "I should have caught the stale lock"})
    assert "delta" in delta
    assert "should have caught" in delta
    [root] = retros.retro_refusals({**shaped, "root": "That was MY MISTAKE, the lock was stale"})
    assert "root" in root
    assert "my mistake" in root
    both = retros.retro_refusals({**shaped, "delta": "my fault", "root": "i forgot to look"})
    assert len(both) == len(["delta", "root"])


def test_a_causal_statement_without_blame_is_accepted() -> None:
    """The negative control: the same facts stated as what let it happen pass."""
    cause = "the lock file was left by a process that exited without releasing it"
    fine: Json = {"findings": [], "delta": "the close now releases the lock", "root": cause}
    assert retros.retro_refusals(fine) == []
