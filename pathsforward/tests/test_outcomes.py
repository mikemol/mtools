# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W533: declared ledger-outcome sets are refused at write, and off by default."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli, outcomes, store

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_OK = cli.EXIT_OK
_REFUSED = cli.EXIT_REFUSED
_DECLARED = {"advance": ["landed"], "other": ["idle"]}


def _state(tmp_path: Path, **top: object) -> Path:
    """Write a minimal state file with the given top-level fields.

    Returns:
        the state path.

    """
    doc: dict[str, object] = {
        "counter": 1,
        "project_root": str(tmp_path),
        "waypoints": [],
        "residue": [],
    }
    doc.update(top)
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _run(path: Path, *args: str) -> int:
    """Run the CLI on a state file.

    Returns:
        the exit code.

    """
    return cli.main(["--state", str(path), *args])


def _doc(path: Path) -> dict[str, object]:
    """Read the state document back.

    Returns:
        the parsed document.

    """
    return cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8")))


def _ledger_bytes(path: Path) -> bytes:
    """Read the ledger beside the state file, empty when absent.

    Returns:
        the ledger's bytes.

    """
    ledger = store.sibling(path, store.LEDGER)
    return ledger.read_bytes() if ledger.is_file() else b""


def _tick(path: Path, outcome: str, *extra: str) -> int:
    """Ledger a queue-level line.

    Returns:
        the exit code.

    """
    return _run(path, "--ledger", "-", outcome, "m", "n", *extra)


def test_unlisted_tick_word_refused_naming_both_sets(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A declared queue refuses an unlisted tick OUTCOME and names both sets."""
    path = _state(tmp_path, ledger_outcomes=_DECLARED)
    assert _tick(path, "filed") == _REFUSED
    err = capsys.readouterr().err
    assert "filed" in err
    assert "landed" in err
    assert "idle" in err


def test_listed_words_accepted(tmp_path: Path) -> None:
    """A listed advance word and a listed other word are both written."""
    path = _state(tmp_path, ledger_outcomes=_DECLARED)
    assert _tick(path, "landed") == _OK
    assert _tick(path, "idle") == _OK
    assert _ledger_bytes(path).count(b"\n") == len(_DECLARED)


def test_interrupt_kind_is_gated_too(tmp_path: Path) -> None:
    """An interrupt line with an unlisted word is refused."""
    path = _state(tmp_path, ledger_outcomes=_DECLARED)
    assert _tick(path, "filed", "--kind", "interrupt") == _REFUSED


def test_other_kinds_stay_free(tmp_path: Path) -> None:
    """A non-tick kind accepts an unlisted word even when sets are declared."""
    path = _state(tmp_path, ledger_outcomes=_DECLARED)
    assert _tick(path, "filed", "--kind", "msg") == _OK
    assert _tick(path, "filed", "--kind", "note") == _OK


def test_no_field_means_any_word_accepted(tmp_path: Path) -> None:
    """Without the field any tick word is accepted and the state is untouched."""
    path = _state(tmp_path)
    before = path.read_bytes()
    assert _tick(path, "filed") == _OK
    assert _tick(path, "whatever-else") == _OK
    assert path.read_bytes() == before
    assert b"filed" in _ledger_bytes(path)
    assert "ledger_outcomes" not in _doc(path)


def test_refused_ledger_leaves_file_byte_identical(tmp_path: Path) -> None:
    """A refused --ledger writes nothing: ledger and state bytes are unchanged."""
    path = _state(tmp_path, ledger_outcomes=_DECLARED)
    assert _tick(path, "landed") == _OK
    ledger_before = _ledger_bytes(path)
    state_before = path.read_bytes()
    assert _tick(path, "filed") == _REFUSED
    assert _ledger_bytes(path) == ledger_before
    assert path.read_bytes() == state_before


def test_outcomes_set_stores_and_ledgers(tmp_path: Path) -> None:
    """--outcomes-set stores the field and ledgers its own action."""
    path = _state(tmp_path)
    assert _run(path, "--outcomes-set", "landed, minted", "idle") == _OK
    assert _doc(path)["ledger_outcomes"] == {"advance": ["landed", "minted"], "other": ["idle"]}
    assert b"outcomes" in _ledger_bytes(path)


def test_outcomes_set_refusals(tmp_path: Path) -> None:
    """--outcomes-set refuses a whitespace word, an empty advance set and an overlap."""
    path = _state(tmp_path)
    assert _run(path, "--outcomes-set", "two\twords", "idle") == _REFUSED
    assert _run(path, "--outcomes-set", "", "idle") == _REFUSED
    assert _run(path, "--outcomes-set", "a,b", "b,c") == _REFUSED
    assert "ledger_outcomes" not in _doc(path)


def test_outcomes_clear_removes_the_field(tmp_path: Path) -> None:
    """--outcomes-clear removes the field entirely, never leaving an empty object."""
    path = _state(tmp_path, ledger_outcomes=_DECLARED)
    assert _run(path, "--outcomes-clear") == _OK
    assert "ledger_outcomes" not in _doc(path)
    assert _tick(path, "filed") == _OK


def test_problems_name_each_malformed_shape() -> None:
    """A non-object, non-list, whitespace-word and overlapping field each yield a finding."""
    bad: list[object] = [
        "text",
        {"advance": "x", "other": []},
        {"advance": ["a b"], "other": []},
        {"advance": ["a"], "other": ["a"]},
    ]
    for raw in bad:
        assert outcomes.problems(raw)
    assert not outcomes.problems(_DECLARED)


def test_check_mode_names_a_malformed_field(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The --check mode exits refused and names ledger_outcomes for a malformed field."""
    path = _state(tmp_path, ledger_outcomes={"advance": ["a"], "other": ["a"]})
    assert _run(path, "--check") == _REFUSED
    captured = capsys.readouterr()
    assert "ledger_outcomes" in captured.out + captured.err
