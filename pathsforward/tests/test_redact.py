# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for W185's redaction: a literal leaves one waypoint's text, and a scan confirms it."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward import cli, redact
from mikemol.pathsforward.ops import RefusedError

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

# A documentation-range address (RFC 5737), standing in for the literal a caller must remove.
_LITERAL = "192.0.2.17"
_TWICE = 2


def _wp(sym: str = "W1") -> Rec:
    """Build a waypoint whose evidence and next step each hold the literal once.

    Returns:
        the waypoint.

    """
    return {
        "symbol": sym,
        "title": f"t{sym}",
        "status": "ready",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": f"scrape {_LITERAL}:9428",
        "evidence": f"2026-09-27: applied, endpoint {_LITERAL}",
        "ticks_blocked": 0,
    }


def _file(tmp_path: Path) -> Path:
    """Write a state with W1 live, W2 clean, W3 in residue.

    Returns:
        the state path.

    """
    doc: Rec = {
        "counter": 3,
        "project_root": str(tmp_path),
        "waypoints": [_wp("W1"), {**_wp("W2"), "next_bounded_step": "s", "evidence": ""}],
        "residue": [{"symbol": "W3", "reason": "why"}],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _run(path: Path, *args: str) -> int:
    """Run the CLI on a state copy.

    Returns:
        the exit code.

    """
    return cli.main(["--state", str(path), *args])


# --- the pure operation ---


def test_redact_replaces_every_occurrence_across_the_free_text_fields() -> None:
    """Both occurrences leave, one in evidence and one in the next step, and the count says two."""
    w = _wp()
    assert redact.redact(w, _LITERAL, "the Service") == _TWICE
    assert _LITERAL not in json.dumps(w)
    assert "the Service" in str(w["evidence"])


def test_a_pattern_that_matches_nothing_is_refused_and_changes_nothing() -> None:
    """A typo is a refusal, not a silent no-op.

    ⚑ THE CONTROL: the record is byte-identical after.
    """
    w = _wp()
    before = json.dumps(w)
    with pytest.raises(RefusedError, match="matches nothing"):
        redact.redact(w, "192.0.2.99", "x")
    assert json.dumps(w) == before


def test_a_replacement_holding_the_pattern_is_refused() -> None:
    """A replacement that contains the pattern would leave it in place; refused, not accepted."""
    with pytest.raises(RefusedError, match="contains the pattern"):
        redact.redact(_wp(), _LITERAL, f"was {_LITERAL}")


def test_the_refusal_names_the_pattern_by_hash_never_by_value() -> None:
    """The pattern is the disclosure: a refusal message carries its digest, not its text."""
    with pytest.raises(RefusedError) as err:
        redact.redact(_wp(), "10.43.0.1", "x")
    assert "10.43.0.1" not in str(err.value)
    assert redact.digest("10.43.0.1") in str(err.value)


def test_scan_reports_where_and_how_many_across_records_and_ledger() -> None:
    """A hit in a record field, a list field and a ledger line each shows; clean input none."""
    records: list[Rec] = [_wp("W1"), {"symbol": "W2", "touches": [f"file:{_LITERAL}"]}]
    hits = redact.scan(records, ["clean line", f"note {_LITERAL}"], _LITERAL)
    assert hits == [
        "W1 next_bounded_step n=1",
        "W1 evidence n=1",
        "W2 touches n=1",
        "ledger line 2 n=1",
    ]
    assert redact.scan([{"symbol": "W9", "evidence": "clean"}], [], _LITERAL) == []


# --- the CLI ---


def test_the_cli_redacts_ledgers_the_hash_and_the_scan_then_comes_back_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scan exits 1 on a hit; redact; the ledger holds the hash and count; render; scan exits 0.

    ⚑ BOTH ARMS OF THE SCAN ARE RUN, so a scan that always says clean cannot pass this.
    """
    path = _file(tmp_path)
    assert _run(path, "--scan-literal", _LITERAL) == cli.EXIT_FAILED
    assert _run(path, "--update", "W1", "--evidence-redact", _LITERAL) == cli.EXIT_OK
    ledger = (tmp_path / "paths-forward.ledger").read_text(encoding="utf-8")
    assert f"{redact.digest(_LITERAL)} n={_TWICE}" in ledger
    assert _LITERAL not in ledger
    assert _run(path, "--render") == cli.EXIT_OK
    capsys.readouterr()
    assert _run(path, "--scan-literal", _LITERAL) == cli.EXIT_OK
    assert _LITERAL not in capsys.readouterr().out
    assert _run(path, "--check") == cli.EXIT_OK


def test_a_refused_redaction_writes_neither_state_nor_ledger(tmp_path: Path) -> None:
    """A zero-match pattern exits refused, and the state file and ledger are untouched."""
    path = _file(tmp_path)
    before = path.read_bytes()
    assert _run(path, "--update", "W1", "--evidence-redact", "192.0.2.99") == cli.EXIT_REFUSED
    assert path.read_bytes() == before
    assert not (tmp_path / "paths-forward.ledger").exists()


@pytest.mark.parametrize(
    "args",
    [
        ("--evidence-redact", _LITERAL, "--status", "done"),
        ("--replacement", "x"),
    ],
    ids=["combined-with-another-field", "replacement-alone"],
)
def test_a_redaction_is_its_own_write(tmp_path: Path, args: tuple[str, ...]) -> None:
    """Combined with another field, or given only a replacement, the update is refused whole."""
    path = _file(tmp_path)
    before = path.read_bytes()
    assert _run(path, "--update", "W1", *args) == cli.EXIT_REFUSED
    assert path.read_bytes() == before
