# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--warrant`: a PROV-O warrant is attached only after the cited record is read.

mtools:W1384. ⚑ THE CONTROLS ARE THE REFUSALS: a reader that refuses the record, a reader that is
missing, a reader that prints nothing parseable, and an incomplete citation each leave the card
exactly as it was. The one accepted citation proves the check can say yes, and a second attach of
the same record changes nothing.
"""

from __future__ import annotations

import json
import stat
import sys
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.pathsforward import cli, warrant
from mikemol.pathsforward.model import RefusedError, State

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

Rec = dict[str, object]

_OK = cli.EXIT_OK
_REFUSED = cli.EXIT_REFUSED
UUID = "0f3c-uuid"
STAMP = "2026-10-16T14:02:11.000Z"
GOOD = {"ok": True, "reason": "", "line": 7, "timestamp": STAMP, "kind": "human"}
BAD = {"ok": False, "reason": "claimed operator, but the record is peer, not human"}


def _stub(code: int, verdict: Rec | str) -> warrant.Run:
    # A reader that answers with a fixed exit and output, recording nothing else.
    out = verdict if isinstance(verdict, str) else json.dumps(verdict)

    def run(argv: Sequence[str]) -> tuple[int, str]:
        del argv
        return code, out + "\n"

    return run


def _cited(tmp_path: Path) -> warrant.Citation:
    return warrant.Citation(tmp_path / "s.jsonl", UUID, claim="operator", line=7)


def test_an_accepted_record_returns_its_verdict_and_the_exact_command(tmp_path: Path) -> None:
    """The control: ok verdict back, with the claim and the line on the command it ran."""
    got, argv = warrant.read(_cited(tmp_path), run=_stub(0, GOOD))
    assert got["timestamp"] == STAMP
    assert argv == [
        warrant.READER,
        str(tmp_path / "s.jsonl"),
        "--verify",
        UUID,
        "--claim",
        "operator",
        "--line",
        "7",
    ]


def test_a_refused_record_raises_with_the_readers_own_reason(tmp_path: Path) -> None:
    """The forgery: the reader exits 1 and says why; the refusal carries that sentence."""
    with pytest.raises(RefusedError, match="not human"):
        warrant.read(_cited(tmp_path), run=_stub(1, BAD))


def test_an_unrunnable_reader_and_an_unparseable_answer_are_refused(tmp_path: Path) -> None:
    """A missing reader and a reader that printed prose are not a pass."""

    def missing(argv: Sequence[str]) -> tuple[int, str]:
        del argv
        raise FileNotFoundError

    with pytest.raises(RefusedError, match="could not run"):
        warrant.read(_cited(tmp_path), run=missing)
    with pytest.raises(RefusedError, match="printed no verdict"):
        warrant.read(_cited(tmp_path), run=_stub(0, "all good"))


def test_the_built_warrant_is_the_prov_shape_nemik_publishes(tmp_path: Path) -> None:
    """The card derives from a record with time, agent and activity; a human is the operator."""
    built = warrant.build("urn:nemik:r/W1", _cited(tmp_path), GOOD, ["reader", "x"])
    record = cast("Rec", built["prov:wasDerivedFrom"])
    assert built["@id"] == "urn:nemik:r/W1"
    assert record["@id"] == f"urn:claude:transcript:{tmp_path.name}/s#{UUID}"
    assert cast("Rec", record["prov:wasAttributedTo"])["@id"] == warrant.OPERATOR_AGENT
    assert cast("Rec", record["prov:generatedAtTime"])["@type"] == "xsd:dateTime"
    assert cast("Rec", record["prov:wasGeneratedBy"])["@type"] == "prov:Activity"
    assert record["mtools:reader"] == "reader x"


def test_a_peer_record_is_attributed_to_a_speaker_not_the_operator(tmp_path: Path) -> None:
    """The agent follows the record's kind, so a peer never reads as the operator."""
    peer = {**GOOD, "kind": "peer"}
    built = warrant.build("urn:nemik:r/W1", _cited(tmp_path), peer, ["reader"])
    agent = cast("Rec", cast("Rec", built["prov:wasDerivedFrom"])["prov:wasAttributedTo"])
    assert agent["@id"] == "urn:nemik:speaker/peer"


def _checkout_reader(root: Path) -> Path:
    # The reader as the fleet root's mtools checkout holds it.
    path = root / "mtools" / "transcriptstruct" / ".venv" / "bin" / warrant.READER
    path.parent.mkdir(parents=True)
    path.write_text("", encoding="utf-8")
    return path


def test_the_reader_is_found_in_the_order_named_env_path_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each rung wins over the ones below it; the checkout is the last resort."""
    monkeypatch.setenv("PATH", "")
    checkout = _checkout_reader(tmp_path)
    assert warrant.resolve(None, tmp_path, {}) == str(checkout)
    on_path = tmp_path / "bin"
    on_path.mkdir()
    (on_path / warrant.READER).write_text("", encoding="utf-8")
    (on_path / warrant.READER).chmod(0o755)
    monkeypatch.setenv("PATH", str(on_path))
    assert warrant.resolve(None, tmp_path, {}) == str(on_path / warrant.READER)
    assert warrant.resolve(None, tmp_path, {warrant.READER_ENV: "from-env"}) == "from-env"
    assert warrant.resolve("named", tmp_path, {warrant.READER_ENV: "from-env"}) == "named"


def test_no_reader_anywhere_is_a_refusal_naming_the_variable_and_the_checkout_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first-run trap, made legible: the message says every place that was looked at."""
    monkeypatch.setenv("PATH", "")
    with pytest.raises(RefusedError, match=warrant.READER_ENV) as raised:
        warrant.resolve(None, tmp_path, {})
    assert str(tmp_path / "mtools") in str(raised.value)


def _card(symbol: str) -> Rec:
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": "ready",
        "enables": [],
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": None,
        "evidence": "",
        "ticks_blocked": 0,
    }


def test_attach_is_idempotent_per_record_and_refuses_an_unknown_card(tmp_path: Path) -> None:
    """The second attach of one record changes nothing; a symbol outside the queue is refused."""
    cards = [_card("W1")]
    state = State({"waypoints": cards}, cards, [], 1)
    built = warrant.build("urn:nemik:r/W1", _cited(tmp_path), GOOD, ["reader"])
    assert warrant.attach(state, "W1", built)
    assert not warrant.attach(state, "W1", built)
    assert len(cast("list[Rec]", state.waypoints[0]["warrants"])) == 1
    with pytest.raises(RefusedError, match="W9"):
        warrant.attach(state, "W9", built)


def _reader_script(tmp_path: Path, verdict: Rec, code: int) -> Path:
    # A real executable reader, so the CLI path through subprocess is exercised once.
    path = tmp_path / "reader.py"
    path.write_text(
        f"#!{sys.executable}\nimport sys\nprint({json.dumps(json.dumps(verdict))})\n"
        f"sys.exit({code})\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _state(tmp_path: Path) -> Path:
    doc: Rec = {"counter": 1, "project_root": str(tmp_path), "waypoints": [_card("W1")]}
    path = tmp_path / ".claude" / "paths-forward.json"
    path.parent.mkdir()
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _run(path: Path, reader: Path, *extra: str) -> int:
    args = ["--warrant", "W1", "--transcript", str(path.parent / "s.jsonl"), "--uuid", UUID]
    return cli.main(["--state", str(path), *args, "--reader", str(reader), *extra])


def _warrants(path: Path) -> list[Rec]:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    card = cast("list[Rec]", doc["waypoints"])[0]
    return cast("list[Rec]", card.get("warrants", []))


def test_the_cli_attaches_a_verified_warrant_once_and_check_stays_green(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Through a real reader process: attached, then 'already on', and --check passes."""
    path = _state(tmp_path)
    reader = _reader_script(tmp_path, GOOD, 0)
    assert _run(path, reader, "--claim", "operator") == _OK
    assert "WARRANT attached to W1" in capsys.readouterr().out
    assert _run(path, reader, "--claim", "operator") == _OK
    assert "WARRANT already on W1" in capsys.readouterr().out
    assert len(_warrants(path)) == 1
    assert cli.main(["--state", str(path), "--check"]) == _OK


def test_the_cli_leaves_the_card_alone_when_the_reader_refuses_or_the_citation_is_short(
    tmp_path: Path,
) -> None:
    """A refusing reader and a missing --uuid each exit refused with no warrant written."""
    path = _state(tmp_path)
    refusing = _reader_script(tmp_path, BAD, 1)
    assert _run(path, refusing, "--claim", "operator") == _REFUSED
    assert not _warrants(path)
    short = cli.main(["--state", str(path), "--warrant", "W1", "--transcript", "x"])
    assert short == _REFUSED
    assert not _warrants(path)
