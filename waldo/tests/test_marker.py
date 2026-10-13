# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the phase marker: it round-trips, refuses the ambiguous, and names every mismatch.

W1064. ⚑ THE ROUND TRIP IS THE POSITIVE CONTROL: what `write` records, `read` returns exactly and in
order, so the refusals of a repeated key, a malformed line, a bad key, a multi-line value and a
link are refusals of the thing and not of the format. No link is created; the guard is told of one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mikemol.waldo import marker
from mikemol.waldo.marker import MarkerError

_STATE = {"deploy_renewer": "true", "run_custodian_config": "false", "tpm_unseal_enabled": "true"}


def test_what_is_written_is_read_back_exactly_and_in_order(tmp_path: Path) -> None:
    """The positive control: the same values, in the same order, with the header as comments."""
    path = tmp_path / "state" / "phase.marker"
    marker.write(path, _STATE, "gate state\nedited by the recipe")
    assert marker.read(path) == _STATE
    assert list(marker.read(path) or {}) == list(_STATE)
    assert path.read_text(encoding="utf-8").startswith("# gate state\n# edited by the recipe\n")


def test_no_marker_reads_as_none_not_as_empty(tmp_path: Path) -> None:
    """A fresh start is not an empty marker: absence and emptiness mean different phases."""
    assert marker.read(tmp_path / "phase.marker") is None
    (tmp_path / "empty.marker").write_text("", encoding="utf-8")
    assert marker.read(tmp_path / "empty.marker") == {}


def test_a_rewrite_replaces_whole_and_leaves_no_temporary_file(tmp_path: Path) -> None:
    """The rename swaps the phase; only the marker remains in the directory."""
    path = tmp_path / "phase.marker"
    marker.write(path, {"a": "1"})
    marker.write(path, {"a": "2", "b": "3"})
    assert marker.read(path) == {"a": "2", "b": "3"}
    assert [p.name for p in tmp_path.iterdir()] == ["phase.marker"]


def test_comments_blank_lines_and_spacing_are_tolerated() -> None:
    """Hand-reading aids do not change the values; surrounding spaces are trimmed."""
    text = "# note\n\n  a = 1 \nb=two words\n   # indented comment\n"
    assert marker.parse(text) == {"a": "1", "b": "two words"}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("a = 1\na = 2\n", "a is set twice"),
        ("just words\n", "not `key = value`"),
        ("1bad = 1\n", "not `key = value`"),
        ("a b = 1\n", "not `key = value`"),
        ("= 1\n", "not `key = value`"),
    ],
)
def test_an_ambiguous_marker_is_refused_naming_the_line(text: str, message: str) -> None:
    """A repeated key and a malformed line raise instead of being read as a phase."""
    with pytest.raises(MarkerError, match=message):
        marker.parse(text)


def test_render_refuses_a_bad_key_and_a_value_that_spans_lines() -> None:
    """Writing what could not be read back is refused at the write."""
    with pytest.raises(MarkerError, match="not a valid marker key"):
        marker.render({"has space": "1"})
    with pytest.raises(MarkerError, match="spans lines"):
        marker.render({"a": "one\ntwo"})
    with pytest.raises(MarkerError, match="spans lines"):
        marker.render({"a": "one\rtwo"})


def test_a_link_is_refused_for_the_file_and_its_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard refuses a path it is told is a link; none is created to test it."""
    linked = tmp_path / "linked"

    def only_linked(self: Path) -> bool:
        return self.name == "linked"

    monkeypatch.setattr(Path, "is_symlink", only_linked)
    with pytest.raises(MarkerError, match="is a link"):
        marker.write(linked, _STATE)
    with pytest.raises(MarkerError, match="is a link"):
        marker.read(linked)
    with pytest.raises(MarkerError, match="is a link"):
        marker.write(linked / "phase.marker", _STATE)


def test_a_marker_that_holds_the_standing_flags_is_required_quietly() -> None:
    """The control: every expected flag present and equal means no refusal."""
    marker.require_standing(_STATE, {"deploy_renewer": "true", "tpm_unseal_enabled": "true"})
    assert not marker.mismatches(_STATE, {})


def test_every_mismatch_is_named_at_once() -> None:
    """A wrong value and a missing key both appear in the one refusal, wrong values first."""
    expected = {"deploy_renewer": "false", "revoke_custodian_root": "true"}
    assert marker.mismatches(_STATE, expected) == [
        "deploy_renewer: expected 'false', the marker has 'true'",
        "revoke_custodian_root: expected 'true', the marker lacks it",
    ]
    with pytest.raises(MarkerError, match=r"deploy_renewer.*revoke_custodian_root"):
        marker.require_standing(_STATE, expected)


def test_no_marker_at_all_is_one_mismatch() -> None:
    """A phase that needs flags cannot start from nothing."""
    assert marker.mismatches(None, _STATE) == ["no marker: the recipe has not recorded a phase yet"]
    with pytest.raises(MarkerError, match="has not recorded a phase"):
        marker.require_standing(None, _STATE)
